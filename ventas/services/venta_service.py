from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from producto.repositories.producto_repository import ProductoRepository
from repository.base_service import BaseService
from repository.exceptions import NotFoundError
from usuario.repositories.usuario_repository import UserRepository
from ventas.models import Venta
from ventas.repositories.metodo_pago_repository import MetodoPagoRepository
from ventas.repositories.venta_repository import VentaRepository
from ventas.services.venta_cabecera import VentaCabeceraResolver
from ventas.services.venta_detalles import (
    ERRORES_EN_DETALLES_PREFIJO,
    normalizar_detalles,
)
from ventas.services.iva import calcular_iva
from ventas.services.venta_query import VentaQueryService, venta_to_dict
from ventas.services.venta_stock import (
    bloquear_productos,
    errores_de_stock,
    revertir_salidas,
)


class VentaService(BaseService):
    def __init__(self, venta_repo=None, user_repo=None, metodo_pago_repo=None, producto_repo=None):
        super().__init__(model=Venta, repository=venta_repo or VentaRepository())
        self.user_repo = user_repo or UserRepository()
        self.metodo_pago_repo = metodo_pago_repo or MetodoPagoRepository()
        self.producto_repo = producto_repo or ProductoRepository()
        self.cabecera = VentaCabeceraResolver(self.user_repo, self.metodo_pago_repo)
        self.query = VentaQueryService(self.repository, to_dict=self._to_dict)

    def _to_dict(self, instance):
        return venta_to_dict(instance)

    def get_all(self, page: int = None, page_size: int = 10, sucursal_id: int = None):
        return self.query.get_all(
            page=page, page_size=page_size, sucursal_id=sucursal_id
        )

    def _sucursal_del_usuario(self, user):
        return self.cabecera.sucursal_del_usuario(user)

    def _resolver_cabecera(self, data, user=None):
        return self.cabecera.resolver_cabecera(data, user=user)

    def create(self, data, user=None):
        user, metodo_pago, sucursal_id = self._resolver_cabecera(data, user=user)
        venta_data = {
            "id_usuario": user,
            "id_metodo_pago": metodo_pago,
            "id_sucursal_id": sucursal_id,
            "id_cliente": self.cabecera.cliente_validado(data),
            "estado": "completada",
            "iva": 0,
            "total": 0
        }
        venta = super().create(venta_data)

        return venta

    @transaction.atomic
    def crear_venta_completa(self, data, user=None):
        """Crea cabecera + detalles en una sola transacción (todo o nada).

        Acepta ``detalles`` como lista de ``{"producto"|"id_producto", "cantidad"}``.
        Bloquea productos en orden determinista (evita deadlocks), valida
        TODO antes de escribir y devuelve errores por línea. Si cualquier
        detalle falla no queda venta huérfana, ni detalles, ni movimientos.
        """
        from decimal import Decimal as _Decimal

        from inventario.services.movimiento_inventario_service import (
            MovimientoInventarioService as _InvService,
        )
        from inventario.services.precio_sucursal_service import (
            PrecioSucursalService as _PrecioService,
        )
        from ventas.models import DetalleVenta as _DetalleVenta

        detalles_raw = data.get("detalles", None)
        if not isinstance(detalles_raw, list) or not detalles_raw:
            raise ValueError("Faltan campos obligatorios: detalles (lista no vacía)")

        user_obj, metodo_pago, sucursal_id = self._resolver_cabecera(data, user=user)
        inv_service = _InvService()

        # Normalizar líneas: índice + producto + cantidad.
        lineas, errores = normalizar_detalles(detalles_raw)
        if errores:
            raise ValueError(ERRORES_EN_DETALLES_PREFIJO + "; ".join(errores))

        ids_ordenados, productos = bloquear_productos(lineas, sucursal_id)
        for ln in lineas:
            if ln["producto_id"] not in productos:
                errores.append(
                    f"Línea {ln['indice']} (producto {ln['producto_id']}): no existe"
                )
        if errores:
            raise ValueError(ERRORES_EN_DETALLES_PREFIJO + "; ".join(errores))

        # Nota sucursal: la sucursal viene derivada del perfil del
        # usuario (no-staff) o del override explícito de staff en
        # _resolver_cabecera, y el stock se mide en esa sucursal, por lo
        # que un cross-sucursal es imposible en este camino. No se duplica
        # el chequeo del flujo por detalle.
        stocks = {
            pid: inv_service.get_stock(pid, sucursal_id) for pid in ids_ordenados
        }
        errores = errores_de_stock(lineas, stocks, productos, sucursal_id)
        if errores:
            raise ValueError(ERRORES_EN_DETALLES_PREFIJO + "; ".join(errores))

        # Escritura: una venta + N detalles + N SALIDA, total en un save.
        venta_obj = Venta.objects.create(
            id_usuario=user_obj,
            id_metodo_pago=metodo_pago,
            id_sucursal_id=sucursal_id,
            id_cliente=self.cabecera.cliente_validado(data),
            estado="completada",
            total=_Decimal("0"),
        )
        total = _Decimal("0")
        detalles_out = []
        for ln in lineas:
            producto = productos[ln["producto_id"]]
            precio = _PrecioService.resolver_precio_venta(producto, sucursal_id)
            subtotal = (_Decimal(precio) * ln["cantidad"]).quantize(_Decimal("0.01"))
            det = _DetalleVenta.objects.create(
                id_venta=venta_obj,
                id_producto=producto,
                cantidad=ln["cantidad"],
                subtotal=subtotal,
            )
            inv_service.crear_salida_por_venta(
                det, producto, sucursal_id, ln["cantidad"], user=user_obj
            )
            total += subtotal
            detalles_out.append(
                {
                    "id": det.id,
                    "id_producto": producto.id,
                    "cantidad": ln["cantidad"],
                    "subtotal": str(subtotal),
                }
            )
        iva = calcular_iva(total)
        venta_obj.iva = iva
        venta_obj.total = (total + iva).quantize(_Decimal("0.01"))
        venta_obj.save(update_fields=["iva", "total"])
        resultado = self._to_dict(venta_obj)
        resultado["detalles"] = detalles_out
        return resultado

    def update(self, entity_id: int, data, user=None):
        """Actualiza una venta. Campos mutables: ``id_metodo_pago``,
        ``id_cliente`` y ``estado``; ``total`` se recalcula desde los
        detalles y ``id_sucursal``/``id_usuario``/``fecha`` se ignoran.

        ``estado='cancelada'`` devuelve el stock y elimina los detalles:
        una venta cancelada no debe seguir contando.
        """
        data = dict(data)
        for campo in ("total", "id_inventario", "id_sucursal", "id_usuario", "fecha"):
            data.pop(campo, None)
        estado = data.get("estado")
        if estado is not None and estado not in ("completada", "cancelada"):
            raise ValueError("estado inválido: use 'completada' o 'cancelada'")
        if "id_metodo_pago" in data and data["id_metodo_pago"] is not None:
            mp_val = data["id_metodo_pago"]
            try:
                mp = self.metodo_pago_repo.get_by_id(
                    mp_val.id if hasattr(mp_val, "id") else mp_val
                )
            except Exception:
                mp = None
            if not mp:
                raise ValueError(f"Metodo de pago con id {mp_val} no encontrado")
            data["id_metodo_pago"] = mp
        if "id_cliente" in data:
            data["id_cliente"] = self.cabecera.cliente_validado(data)
        with transaction.atomic():
            try:
                venta = Venta.objects.select_for_update().get(id=entity_id)
            except (Venta.DoesNotExist, ObjectDoesNotExist):
                raise NotFoundError(
                    f"venta con id {entity_id} no encontrado"
                )
            if estado == "cancelada":
                if venta.estado == "completada":
                    revertir_salidas(venta)
                else:
                    # Ya cancelada: idempotente, no se vuelve a revertir.
                    data.pop("estado", None)
            elif estado == "completada" and venta.estado == "cancelada":
                raise ValueError("No se puede reactivar una venta cancelada")
        return super().update(entity_id, data)

    def delete(self, entity_id: int, user=None):
        """Cancela una venta (soft delete) devolviendo su stock.

        Sin la reversión, los movimientos SALIDA quedarían apuntando a una
        venta desactivada y el stock nunca se restauraría. Todo se ejecuta
        en un único ``transaction.atomic`` con bloqueo de la venta e
        ``idempotente``: cancelar dos veces no toca nada la segunda vez.
        """
        with transaction.atomic():
            try:
                venta = Venta.objects.select_for_update().get(id=entity_id)
            except (Venta.DoesNotExist, ObjectDoesNotExist):
                raise NotFoundError(
                    f"venta con id {entity_id} no encontrado"
                )
            if venta.estado == "cancelada":
                return {
                    "message": "venta ya estaba cancelada",
                    "id": venta.id,
                    "estado": venta.estado,
                }
            revertir_salidas(venta)
            venta.estado = "cancelada"
            venta.save(update_fields=["estado"])
            return {
                "message": "venta cancelada exitosamente",
                "id": venta.id,
                "estado": venta.estado,
            }
