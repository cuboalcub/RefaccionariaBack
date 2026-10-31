from django.db import transaction
from django.db.models import F

from inventario.models import MovimientoInventario, Stock
from inventario.repositories.movimiento_inventario_repository import (
    MovimientoInventarioRepository,
)
from inventario.repositories.stock_repository import StockRepository
from producto.models import Producto, Proveedor
from repository.base_service import BaseService
from repository.exceptions import NotFoundError
from sucursales.models import Sucursal

MSG_TIPO_MOVIMIENTO_INVALIDO = "tipo_movimiento debe ser ENTRADA o SALIDA"
MSG_CANTIDAD_NEGATIVA = "La cantidad no puede ser negativa"
MSG_PROVEEDOR_INEXISTENTE = "El proveedor indicado no existe"
MSG_MOVIMIENTO_EXTERNO = (
    "id_movimiento deprecado: cada movimiento lleva su propio producto/sucursal"
)
MSG_AJUSTE_MANUAL = "Ajuste manual"
CAMPOS_OBLIGATORIOS = ("id_producto", "id_sucursal", "cantidad")
CAMPOS_BULK = (
    "id_sucursal",
    "id_proveedor",
    "tipo_movimiento",
    "tipo",
    "razon",
    "razón",
    "observaciones",
    "id_movimiento",  # se propaga para que create() lo rechace como deprecado
)


def _programar_alerta(producto_id, sucursal_id):
    """Programa la evaluación de alertas de stock tras el commit.

    Importación diferida para no acoplar el inventario a la app de
    notificaciones a nivel de módulo. La evaluación corre en on_commit y
    sus fallos solo quedan en el log (ver stock_alerts).
    """
    from notifications.services.stock_alerts import programar_evaluacion

    programar_evaluacion(producto_id, sucursal_id)


def _signo(tipo):
    return 1 if tipo == MovimientoInventario.TipoMovimiento.ENTRADA else -1


class MovimientoInventarioService(BaseService):
    """Registro de ENTRADAS/SALIDAS: cada movimiento lleva producto,
    sucursal, usuario y (en ventas) el detalle que lo generó; sobre esa
    base ajusta la fila cacheada de Stock por (sucursal, producto)."""

    def __init__(self):
        super().__init__(
            model=MovimientoInventario,
            repository=MovimientoInventarioRepository(),
        )
        self.stock_repo = StockRepository()

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "tipo": instance.tipo,
            "cantidad": instance.cantidad,
            "fecha": instance.fecha.isoformat() if instance.fecha else None,
            "razon": instance.razon,
            "observaciones": instance.observaciones,
            "id_producto": instance.id_producto_id,
            "id_sucursal": instance.id_sucursal_id,
            "id_usuario": instance.id_usuario_id,
            "id_proveedor": instance.id_proveedor_id,
            "id_detalle_venta": instance.id_detalle_venta_id,
        }

    def get_stock(self, producto_id, sucursal_id):
        return self.stock_repo.get_stock(producto_id, sucursal_id)

    def _validar_salida(self, producto_id, sucursal_id, cantidad):
        disponible = self.stock_repo.get_stock(producto_id, sucursal_id)
        if disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {disponible}, solicitado {cantidad}"
            )

    def get_stock_map_por_sucursal(self, sucursal_id):
        return self.stock_repo.get_stock_map_por_sucursal(sucursal_id)

    def _fila_stock(self, producto_id, sucursal_id):
        """Fila de Stock bloqueada para escribir (se crea al vuelo si falta)."""
        return Stock.objects.select_for_update().get_or_create(
            id_producto_id=producto_id,
            id_sucursal_id=sucursal_id,
            defaults={"cantidad": 0},
        )[0]

    def _aplicar_delta(self, producto_id, sucursal_id, delta):
        fila = self._fila_stock(producto_id, sucursal_id)
        fila.cantidad = F("cantidad") + delta
        fila.save(update_fields=["cantidad"])
        fila.refresh_from_db(fields=["cantidad"])
        return fila.cantidad

    def _validar_campos_obligatorios(self, data):
        faltantes = [f for f in CAMPOS_OBLIGATORIOS if f not in data or data[f] is None]
        if faltantes:
            raise ValueError(f"Faltan campos obligatorios: {faltantes[0]}")

    def _validar(self, data):
        self._validar_campos_obligatorios(data)
        if not Producto.objects.filter(id=data["id_producto"]).exists():
            raise ValueError("El producto indicado no existe")
        if not Sucursal.objects.filter(id=data["id_sucursal"]).exists():
            raise ValueError("La sucursal indicada no existe")
        if "id_proveedor" in data and data["id_proveedor"]:
            if not Proveedor.objects.filter(id=data["id_proveedor"]).exists():
                raise ValueError(MSG_PROVEEDOR_INEXISTENTE)
        if data["cantidad"] < 0:
            raise ValueError(MSG_CANTIDAD_NEGATIVA)
        self._validar_tipo(data)

    def _validar_tipo(self, data):
        tipo = data.get("tipo_movimiento") or data.get("tipo")
        if tipo is not None and tipo not in ("ENTRADA", "SALIDA"):
            raise ValueError(MSG_TIPO_MOVIMIENTO_INVALIDO)

    @transaction.atomic
    def create(self, data, user=None):
        data = dict(data)
        if data.get("id_movimiento") is not None:
            raise ValueError(MSG_MOVIMIENTO_EXTERNO)
        self._validar(data)
        tipo = data.pop("tipo_movimiento", None) or data.pop("tipo", None) or "ENTRADA"
        razon = data.pop("razon", None) or data.pop("razón", None) or MSG_AJUSTE_MANUAL
        observaciones = data.pop("observaciones", None) or ""
        if "id_proveedor" in data and data["id_proveedor"]:
            data["id_proveedor"] = Proveedor.objects.get(id=data["id_proveedor"])
        else:
            data.pop("id_proveedor", None)
        fila = self._fila_stock(data["id_producto"], data["id_sucursal"])
        if tipo == MovimientoInventario.TipoMovimiento.SALIDA and fila.cantidad < data["cantidad"]:
            raise ValueError(
                f"Stock insuficiente: disponible {fila.cantidad}, solicitado {data['cantidad']}"
            )
        movimiento = MovimientoInventario.objects.create(
            tipo=tipo,
            cantidad=data["cantidad"],
            razon=razon,
            observaciones=observaciones,
            id_producto_id=data["id_producto"],
            id_sucursal_id=data["id_sucursal"],
            id_proveedor=data.get("id_proveedor"),
            id_usuario=user,
        )
        self._aplicar_delta(
            data["id_producto"], data["id_sucursal"], _signo(tipo) * data["cantidad"]
        )
        _programar_alerta(data["id_producto"], data["id_sucursal"])
        return self._to_dict(movimiento)

    @transaction.atomic
    def update(self, entity_id, data, user=None):
        data = dict(data)
        if data.get("id_movimiento") is not None:
            raise ValueError(MSG_MOVIMIENTO_EXTERNO)
        movimiento = self.repository.get_by_id(entity_id)
        if not movimiento:
            raise NotFoundError(
                f"{self.model.__name__} con id {entity_id} no encontrado"
            )

        if "tipo_movimiento" in data or "tipo" in data:
            nuevo_tipo = data.pop("tipo_movimiento", None) or data.pop("tipo", None)
            if nuevo_tipo not in ("ENTRADA", "SALIDA"):
                raise ValueError(MSG_TIPO_MOVIMIENTO_INVALIDO)
        else:
            nuevo_tipo = movimiento.tipo
        nueva_cantidad = data.get("cantidad", movimiento.cantidad)
        if nueva_cantidad < 0:
            raise ValueError(MSG_CANTIDAD_NEGATIVA)
        nuevo_producto_id = data.get("id_producto", movimiento.id_producto_id)
        nueva_sucursal_id = data.get("id_sucursal", movimiento.id_sucursal_id)
        if nuevo_producto_id != movimiento.id_producto_id and not Producto.objects.filter(
            id=nuevo_producto_id
        ).exists():
            raise ValueError("El producto indicado no existe")
        if nueva_sucursal_id != movimiento.id_sucursal_id and not Sucursal.objects.filter(
            id=nueva_sucursal_id
        ).exists():
            raise ValueError("La sucursal indicada no existe")
        if "id_proveedor" in data:
            if not data["id_proveedor"]:
                data["id_proveedor"] = None
            else:
                if not Proveedor.objects.filter(id=data["id_proveedor"]).exists():
                    raise ValueError(MSG_PROVEEDOR_INEXISTENTE)
                data["id_proveedor"] = Proveedor.objects.get(id=data["id_proveedor"])

        delta_viejo = _signo(movimiento.tipo) * movimiento.cantidad
        delta_nuevo = _signo(nuevo_tipo) * nueva_cantidad
        mismo_par = (
            nuevo_producto_id == movimiento.id_producto_id
            and nueva_sucursal_id == movimiento.id_sucursal_id
        )
        if nuevo_tipo == MovimientoInventario.TipoMovimiento.SALIDA:
            fila = self._fila_stock(nuevo_producto_id, nueva_sucursal_id)
            stock_sin_este = fila.cantidad - (delta_viejo if mismo_par else 0)
            if stock_sin_este < nueva_cantidad:
                raise ValueError(
                    f"Stock insuficiente: disponible {stock_sin_este}, solicitado {nueva_cantidad}"
                )

        if mismo_par:
            self._aplicar_delta(
                movimiento.id_producto_id,
                movimiento.id_sucursal_id,
                delta_nuevo - delta_viejo,
            )
            pares_alerta = [(nuevo_producto_id, nueva_sucursal_id)]
        else:
            self._aplicar_delta(movimiento.id_producto_id, movimiento.id_sucursal_id, -delta_viejo)
            self._aplicar_delta(nuevo_producto_id, nueva_sucursal_id, delta_nuevo)
            pares_alerta = [
                (movimiento.id_producto_id, movimiento.id_sucursal_id),
                (nuevo_producto_id, nueva_sucursal_id),
            ]

        movimiento.tipo = nuevo_tipo
        movimiento.cantidad = nueva_cantidad
        movimiento.id_producto_id = nuevo_producto_id
        movimiento.id_sucursal_id = nueva_sucursal_id
        if "razon" in data:
            movimiento.razon = data["razon"]
        if "observaciones" in data:
            movimiento.observaciones = data["observaciones"]
        if "id_proveedor" in data:
            movimiento.id_proveedor = data["id_proveedor"]
        movimiento.save()

        for pid, sid in pares_alerta:
            _programar_alerta(pid, sid)
        return self._to_dict(movimiento)

    @transaction.atomic
    def delete(self, entity_id, user=None):
        movimiento = self.repository.get_by_id(entity_id)
        if not movimiento:
            raise NotFoundError(
                f"{self.model.__name__} con id {entity_id} no encontrado"
            )
        delta = _signo(movimiento.tipo) * movimiento.cantidad
        self._aplicar_delta(movimiento.id_producto_id, movimiento.id_sucursal_id, -delta)
        _programar_alerta(movimiento.id_producto_id, movimiento.id_sucursal_id)
        movimiento.delete()
        return {"message": f"{self.model.__name__} eliminado exitosamente"}

    # ---- flujos de venta ----

    def crear_salida_por_venta(
        self, detalle_venta, producto, sucursal_id, cantidad, user=None
    ):
        fila = self._fila_stock(producto.id, sucursal_id)
        if fila.cantidad < cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {fila.cantidad}, solicitado {cantidad}"
            )
        movimiento = MovimientoInventario.objects.create(
            tipo=MovimientoInventario.TipoMovimiento.SALIDA,
            cantidad=cantidad,
            razon="Venta",
            observaciones=f"Venta {detalle_venta.id_venta_id}",
            id_producto=producto,
            id_sucursal_id=sucursal_id,
            id_usuario=user,
            id_detalle_venta=detalle_venta,
        )
        self._aplicar_delta(producto.id, sucursal_id, -cantidad)
        _programar_alerta(producto.id, sucursal_id)
        return self._to_dict(movimiento)

    def ajustar_salida_por_venta(
        self, detalle_venta, nueva_cantidad, producto=None, sucursal_id=None
    ):
        movimiento = self.repository.filter(
            {"id_detalle_venta_id": detalle_venta.id}
        )
        movimiento = movimiento[0] if movimiento else None
        if not movimiento:
            return None

        nuevo_producto = producto or movimiento.id_producto
        nueva_sucursal = sucursal_id or movimiento.id_sucursal_id
        misma_par = (
            nuevo_producto.id == movimiento.id_producto_id
            and nueva_sucursal == movimiento.id_sucursal_id
        )
        fila = self._fila_stock(nuevo_producto.id, nueva_sucursal)
        stock_sin_este = fila.cantidad + (
            movimiento.cantidad if misma_par else 0
        )
        if stock_sin_este < nueva_cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {stock_sin_este}, solicitado {nueva_cantidad}"
            )

        if misma_par:
            self._aplicar_delta(
                movimiento.id_producto_id,
                movimiento.id_sucursal_id,
                movimiento.cantidad - nueva_cantidad,
            )
            pares_alerta = [(nuevo_producto.id, nueva_sucursal)]
        else:
            self._aplicar_delta(
                movimiento.id_producto_id, movimiento.id_sucursal_id, movimiento.cantidad
            )
            self._aplicar_delta(nuevo_producto.id, nueva_sucursal, -nueva_cantidad)
            pares_alerta = [
                (movimiento.id_producto_id, movimiento.id_sucursal_id),
                (nuevo_producto.id, nueva_sucursal),
            ]

        movimiento.cantidad = nueva_cantidad
        movimiento.id_producto = nuevo_producto
        movimiento.id_sucursal_id = nueva_sucursal
        movimiento.save(update_fields=["id_producto", "id_sucursal", "cantidad", "tipo"])
        for pid, sid in pares_alerta:
            _programar_alerta(pid, sid)
        return self._to_dict(movimiento)

    def revertir_salida_por_venta(self, detalle_venta):
        movimiento = self.repository.filter(
            {"id_detalle_venta_id": detalle_venta.id}
        )
        movimiento = movimiento[0] if movimiento else None
        if not movimiento:
            return None
        producto_id = movimiento.id_producto_id
        sucursal_id = movimiento.id_sucursal_id
        self._aplicar_delta(producto_id, sucursal_id, movimiento.cantidad)
        _programar_alerta(producto_id, sucursal_id)
        movimiento.delete()
        return True

    # ---- consultas ----

    def get_inventario_por_sucursal(self, sucursal_id):
        """Catálogo agrupado por producto: {id_sucursal, detalles} con
        la misma forma de item que la versión anterior (Stock + precio
        activo por sucursal)."""
        from inventario.models import PrecioSucursal

        precio_map = {
            ps.id_producto_id: ps
            for ps in PrecioSucursal.objects.filter(
                id_sucursal_id=sucursal_id, activo=True
            )
        }
        detalles = []
        for fila in Stock.objects.select_related("id_producto").filter(
            id_sucursal_id=sucursal_id
        ):
            producto = fila.id_producto
            ps = precio_map.get(producto.id)
            detalles.append(
                {
                    "id": fila.id,
                    "id_producto": producto.id,
                    "nombre": producto.nombre,
                    "clave": producto.clave,
                    "marca": producto.marca,
                    "codigo_barras": producto.codigo_barras,
                    "precio_venta": str(producto.precio_venta),
                    "precio_sucursal": str(ps.precio_venta) if ps else None,
                    "vigente_desde": ps.vigente_desde.isoformat() if ps and ps.vigente_desde else None,
                    "precio_base": str(producto.precio_venta),
                    "costo": str(producto.costo),
                    "cantidad": fila.cantidad,
                }
            )
        detalles.sort(key=lambda p: p["nombre"])
        return {"id_sucursal": sucursal_id, "detalles": detalles}

    # ---- bulk ----

    @transaction.atomic
    def bulk_create(self, data, user=None):
        """Crea múltiples movimientos en una transacción (1 por línea).
        Formatos soportados:
        1) {"id_sucursal":1,"id_proveedor":1,"items":[{"id_producto":1,"cantidad":5},...]}
        2) {"id_sucursal":1,"detalles":[...]}  (alias)
        3) [{"id_producto":1,"id_sucursal":1,"cantidad":5}, ...] (lista plana)
        """
        if isinstance(data, dict) and not (
            isinstance(data.get("items"), list) or isinstance(data.get("detalles"), list)
        ):
            return [self.create(data, user=user)]

        items, comun = self._normalizar_bulk(data)
        if items is None:
            raise ValueError(
                "Formato bulk inválido. Use {'id_sucursal':1,'items':[...]} o lista de objetos"
            )
        if not items:
            raise ValueError("La lista de items no puede estar vacía")

        resultados = []
        for idx, item in enumerate(items):
            resultados.append(self._procesar_item_bulk(idx, item, comun, user))
        return resultados

    @staticmethod
    def _normalizar_bulk(data):
        if isinstance(data, list):
            return data, {}
        if isinstance(data, dict):
            for key in ("items", "detalles"):
                if isinstance(data.get(key), list):
                    return data[key], {
                        k: data[k] for k in CAMPOS_BULK if k in data
                    }
        return None, None

    def _procesar_item_bulk(self, idx, item, comun, user):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx} debe ser un objeto")
        cur = dict(item)
        for k in CAMPOS_BULK:
            if cur.get(k) is None and comun.get(k) is not None:
                cur[k] = comun[k]
        return self.create(cur, user=user)
