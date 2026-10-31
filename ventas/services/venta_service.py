from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from ventas.models import Venta
from ventas.repositories.venta_repository import VentaRepository
from usuario.repositories.usuario_repository import UserRepository
from ventas.repositories.metodo_pago_repository import MetodoPagoRepository
from repository.base_service import BaseService
from repository.exceptions import NotFoundError
from repository.permissions import es_staff
from producto.repositories.producto_repository import ProductoRepository
from sucursales.models import Sucursal
from clientes.models import Cliente

ERRORES_EN_DETALLES_PREFIJO = "Errores en detalles: "

class VentaService(BaseService):
    def __init__(self, venta_repo=None, user_repo=None, metodo_pago_repo=None, producto_repo=None):
        super().__init__(model=Venta, repository=venta_repo or VentaRepository())
        self.user_repo = user_repo or UserRepository()
        self.metodo_pago_repo = metodo_pago_repo or MetodoPagoRepository()
        self.producto_repo = producto_repo or ProductoRepository()

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_usuario": instance.id_usuario.id if instance.id_usuario else None,
            "id_metodo_pago": instance.id_metodo_pago.id if instance.id_metodo_pago else None,
            "id_sucursal": instance.id_sucursal_id,
            "id_cliente": instance.id_cliente_id,
            "estado": instance.estado,
            "total": str(instance.total),
            "fecha": instance.fecha.isoformat() if instance.fecha else None
        }

    def _validar_paginacion(self, page, page_size):
        try:
            page = int(page)
            page_size = int(page_size)
        except (TypeError, ValueError):
            raise ValueError("page y page_size deben ser enteros")
        if page < 1 or page_size < 1:
            raise ValueError("page y page_size deben ser >= 1")
        return page, page_size

    def _validar_sucursal_filtro(self, sucursal_id):
        try:
            sucursal_id = int(sucursal_id)
        except (TypeError, ValueError):
            raise ValueError("sucursal_id debe ser entero")
        from sucursales.models import Sucursal
        if not Sucursal.objects.filter(id=sucursal_id).exists():
            raise ValueError(f"Sucursal con id {sucursal_id} no encontrada")
        return sucursal_id

    def get_all(self, page: int = None, page_size: int = 10, sucursal_id: int = None):
        """Devuelve ventas divididas por sucursal con paginación opcional.

        - Filtra por ``sucursal_id`` vía ``id_sucursal_id``.
        - Si ``page`` es None devuelve lista plana (compatibilidad).
        - Si ``page`` se indica devuelve dict {total, page, page_size, total_pages, results}.
        """
        try:
            import math

            if page is not None:
                page, page_size = self._validar_paginacion(page, page_size)

            if sucursal_id is not None:
                sucursal_id = self._validar_sucursal_filtro(sucursal_id)

            qs = Venta.objects.all().select_related(
                'id_usuario', 'id_metodo_pago', 'id_sucursal'
            ).order_by('-fecha', '-id')

            if sucursal_id is not None:
                qs = qs.filter(id_sucursal_id=sucursal_id)

            if page is None:
                return [self._to_dict(v) for v in qs]

            total = qs.count()
            total_pages = math.ceil(total / page_size) if total else 0
            start = (page - 1) * page_size
            end = start + page_size
            instances = list(qs[start:end])
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "sucursal_id": sucursal_id,
                "results": [self._to_dict(v) for v in instances],
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error al obtener ventas: {str(e)}") from e

    def _sucursal_del_usuario(self, user):
        """Resuelve el id de Sucursal a partir del Perfil.sucursal del usuario autenticado."""
        perfil = getattr(user, 'perfil', None)
        user_sucursal_id = None
        if perfil is not None:
            try:
                user_sucursal_id = getattr(perfil, 'id_sucursal_id', None)
            except Exception:
                user_sucursal_id = None
        # Fallback: fetch fresco si no se obtuvo (perfil no cacheado o DoesNotExist)
        if user_sucursal_id is None:
            try:
                from usuario.models import Perfil
                p = Perfil.objects.filter(usuario_id=user.id).first()
                if p:
                    user_sucursal_id = p.id_sucursal_id
            except Exception:
                user_sucursal_id = None
        if user_sucursal_id is None:
            raise ValueError("El usuario no tiene una sucursal asignada. Asigne una sucursal al perfil")
        return user_sucursal_id

    def _usuario_autenticado(self, data, user):
        via_jwt = user is not None and getattr(user, "is_authenticated", False)
        if via_jwt:
            return user, True
        if "id_usuario" in data and data["id_usuario"] is not None:
            usuario = self.user_repo.get_by_id(data['id_usuario'])
            if not usuario:
                raise ValueError(f"Usuario con id {data['id_usuario']} no encontrado")
            return usuario, False
        if "id_metodo_pago" not in data:
            raise ValueError("Faltan campos obligatorios: id_usuario, id_metodo_pago")
        raise ValueError("Faltan campos obligatorios: id_usuario (autenticación requerida)")

    def _metodo_pago_resuelto(self, data):
        if "id_metodo_pago" not in data or data["id_metodo_pago"] is None:
            raise ValueError("Faltan campos obligatorios: id_metodo_pago")
        metodo_pago = self.metodo_pago_repo.get_by_id(data['id_metodo_pago'])
        if not metodo_pago:
            raise ValueError(f"Metodo de pago con id {data['id_metodo_pago']} no encontrado")
        return metodo_pago

    def _cliente_validado(self, data):
        """Normaliza id_cliente ausente/'' a None y valida existencia."""
        if "id_cliente" not in data or data["id_cliente"] in (None, "", 0):
            return None
        cliente = Cliente.objects.filter(id=data["id_cliente"]).first()
        if not cliente:
            raise ValueError(f"Cliente con id {data['id_cliente']} no encontrado")
        return cliente

    def _sucursal_override_staff(self, data):
        try:
            suc_id = int(data["sucursal_id"])
        except (TypeError, ValueError):
            raise ValueError("sucursal_id debe ser entero")
        if not Sucursal.objects.filter(id=suc_id).exists():
            raise ValueError(f"Sucursal con id {suc_id} no encontrada")
        return suc_id

    def _sucursal_legacy(self, data):
        """Sin JWT: exige id_sucursal explícito."""
        suc_id = data.get("id_sucursal")
        if suc_id is None:
            raise ValueError("Faltan campos obligatorios: id_sucursal")
        if not Sucursal.objects.filter(id=suc_id).exists():
            raise ValueError(f"Sucursal con id {suc_id} no encontrada")
        return suc_id

    def _sucursal_via_jwt(self, data, user, is_staff):
        """JWT: el usuario ancla la venta a su sucursal. Staff puede enviar
        ``sucursal_id`` explícito como override."""
        if is_staff and data.get("sucursal_id") is not None:
            return self._sucursal_override_staff(data)
        try:
            return self._sucursal_del_usuario(user)
        except ValueError as e:
            if is_staff:
                raise ValueError(str(e) + " (staff: envíe sucursal_id explícito)")
            raise

    def _resolver_cabecera(self, data, user=None):
        """Resuelve (usuario, método de pago, sucursal_id) con las mismas
        reglas que :meth:`create` (JWT vs legacy, staff override)."""
        usuario, via_jwt = self._usuario_autenticado(data, user)
        metodo_pago = self._metodo_pago_resuelto(data)
        if via_jwt:
            sucursal_id = self._sucursal_via_jwt(data, usuario, es_staff(usuario))
        else:
            sucursal_id = self._sucursal_legacy(data)
        return usuario, metodo_pago, sucursal_id

    def create(self, data, user=None):
        user, metodo_pago, sucursal_id = self._resolver_cabecera(data, user=user)
        venta_data = {
            "id_usuario": user,
            "id_metodo_pago": metodo_pago,
            "id_sucursal_id": sucursal_id,
            "id_cliente": self._cliente_validado(data),
            "estado": "completada",
            "total": 0
        }
        venta = super().create(venta_data)

        return venta

    def _validar_linea_detalle(self, indice, detalle):
        if not isinstance(detalle, dict):
            return f"Línea {indice}: formato inválido, se esperaba objeto", None, None
        pid = detalle.get("id_producto", detalle.get("producto", None))
        cant = detalle.get("cantidad", None)
        if pid is None:
            return f"Línea {indice}: falta id_producto/producto", None, None
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            return f"Línea {indice} (producto {detalle.get('id_producto', detalle.get('producto'))}): id inválido", None, None
        if isinstance(cant, bool) or not isinstance(cant, int):
            return f"Línea {indice} (producto {pid}): cantidad debe ser entero positivo", None, None
        if cant <= 0:
            return f"Línea {indice} (producto {pid}): cantidad debe ser mayor a cero", None, None
        return None, pid, cant

    def _normalizar_detalles(self, detalles_raw, errores):
        lineas = []
        for i, d in enumerate(detalles_raw):
            error, pid, cant = self._validar_linea_detalle(i, d)
            if error:
                errores.append(error)
                continue
            lineas.append({"indice": i, "producto_id": pid, "cantidad": cant})
        return lineas

    def _bloquear_productos(self, lineas, sucursal_id):
        from inventario.models import Stock as _Stock
        from producto.models import Producto as _Producto

        # Bloqueo determinista: ordena IDs para evitar deadlocks entre
        # transacciones concurrentes.
        ids_ordenados = sorted({ln["producto_id"] for ln in lineas})
        productos_qs = list(
            _Producto.objects.select_for_update().filter(id__in=ids_ordenados)
        )
        productos = {p.id: p for p in productos_qs}
        # Serializar también las filas de stock de la sucursal para que dos
        # ventas concurrentes no lean el mismo stock a la vez.
        list(
            _Stock.objects.select_for_update().filter(
                id_producto_id__in=ids_ordenados,
                id_sucursal_id=sucursal_id,
            )
        )
        return ids_ordenados, productos

    def _errores_de_stock(self, lineas, ids_ordenados, productos, sucursal_id, inv_service):
        errores = []
        # Validación de sucursal/stock. Acumula cantidades por producto para
        # detectar el caso de producto repetido que excede el stock en total.
        stocks = {}
        for pid in ids_ordenados:
            stocks[pid] = inv_service.get_stock(pid, sucursal_id)
        acumulado = {}
        for ln in lineas:
            acumulado[ln["producto_id"]] = acumulado.get(ln["producto_id"], 0) + ln["cantidad"]
        for ln in lineas:
            pid = ln["producto_id"]
            if stocks.get(pid, 0) == 0:
                nombre = productos[pid].nombre
                errores.append(
                    f"Línea {ln['indice']} (producto {pid} '{nombre}'): "
                    f"no disponible en la sucursal {sucursal_id} - stock 0"
                )
        for pid, total_pid in acumulado.items():
            if total_pid > stocks.get(pid, 0):
                indices = [str(ln["indice"]) for ln in lineas if ln["producto_id"] == pid]
                errores.append(
                    f"Producto {pid} (líneas {', '.join(indices)}): "
                    f"stock insuficiente: disponible {stocks.get(pid, 0)}, "
                    f"solicitado {total_pid}"
                )
        return errores

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
        errores = []
        lineas = self._normalizar_detalles(detalles_raw, errores)
        if errores:
            raise ValueError(ERRORES_EN_DETALLES_PREFIJO + "; ".join(errores))

        ids_ordenados, productos = self._bloquear_productos(lineas, sucursal_id)
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
        errores = self._errores_de_stock(
            lineas, ids_ordenados, productos, sucursal_id, inv_service
        )
        if errores:
            raise ValueError(ERRORES_EN_DETALLES_PREFIJO + "; ".join(errores))

        # Escritura: una venta + N detalles + N SALIDA, total en un save.
        venta_obj = Venta.objects.create(
            id_usuario=user_obj,
            id_metodo_pago=metodo_pago,
            id_sucursal_id=sucursal_id,
            id_cliente=self._cliente_validado(data),
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
        venta_obj.total = total.quantize(_Decimal("0.01"))
        venta_obj.save(update_fields=["total"])
        resultado = self._to_dict(venta_obj)
        resultado["detalles"] = detalles_out
        return resultado

    def _revertir_salidas(self, venta):
        """Devuelve el stock de todos los detalles de una venta (por cancelación)."""
        from ventas.models import DetalleVenta
        from inventario.services.movimiento_inventario_service import (
            MovimientoInventarioService,
        )
        detalles = list(
            DetalleVenta.objects.select_for_update().filter(
                id_venta_id=venta.id
            )
        )
        inventario_service = MovimientoInventarioService()
        for detalle in detalles:
            inventario_service.revertir_salida_por_venta(detalle)

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
            data["id_cliente"] = self._cliente_validado(data)
        with transaction.atomic():
            try:
                venta = Venta.objects.select_for_update().get(id=entity_id)
            except (Venta.DoesNotExist, ObjectDoesNotExist):
                raise NotFoundError(
                    f"venta con id {entity_id} no encontrado"
                )
            if estado == "cancelada":
                if venta.estado == "completada":
                    self._revertir_salidas(venta)
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
            self._revertir_salidas(venta)
            venta.estado = "cancelada"
            venta.save(update_fields=["estado"])
            return {
                "message": "venta cancelada exitosamente",
                "id": venta.id,
                "estado": venta.estado,
            }
