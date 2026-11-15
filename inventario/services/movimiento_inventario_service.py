from django.db import transaction

from inventario.models import MovimientoInventario
from inventario.repositories.movimiento_inventario_repository import (
    MovimientoInventarioRepository,
)
from inventario.services.inventario_query_service import InventarioQueryService
from inventario.services.movimiento_bulk_service import MovimientoBulkService
from inventario.services.movimiento_utils import (
    movimiento_to_dict,
    programar_alerta,
    signo,
)
from inventario.services.salida_venta_service import SalidaVentaService
from inventario.services.stock_service import StockService
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


class MovimientoInventarioService(BaseService):
    """Registro de ENTRADAS/SALIDAS: cada movimiento lleva producto,
    sucursal, usuario y (en ventas) el detalle que lo generó; sobre esa
    base ajusta la fila cacheada de Stock por (sucursal, producto)."""

    def __init__(self, stock_service=None, salida_service=None):
        super().__init__(
            model=MovimientoInventario,
            repository=MovimientoInventarioRepository(),
        )
        self.stock_service = stock_service or StockService()
        self.salida_service = salida_service or SalidaVentaService(
            stock_service=self.stock_service
        )
        self.query_service = InventarioQueryService()

    def _to_dict(self, instance):
        return movimiento_to_dict(instance)

    def get_stock(self, producto_id, sucursal_id):
        return self.stock_service.get_stock(producto_id, sucursal_id)

    def validar_salida(self, producto_id, sucursal_id, cantidad):
        return self.stock_service.validar_salida(producto_id, sucursal_id, cantidad)

    def get_stock_map_por_sucursal(self, sucursal_id):
        return self.stock_service.get_stock_map_por_sucursal(sucursal_id)

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
        fila = self.stock_service.fila_stock(data["id_producto"], data["id_sucursal"])
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
        self.stock_service.aplicar_delta(
            data["id_producto"], data["id_sucursal"], signo(tipo) * data["cantidad"]
        )
        programar_alerta(data["id_producto"], data["id_sucursal"])
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

        delta_viejo = signo(movimiento.tipo) * movimiento.cantidad
        delta_nuevo = signo(nuevo_tipo) * nueva_cantidad
        mismo_par = (
            nuevo_producto_id == movimiento.id_producto_id
            and nueva_sucursal_id == movimiento.id_sucursal_id
        )
        if nuevo_tipo == MovimientoInventario.TipoMovimiento.SALIDA:
            fila = self.stock_service.fila_stock(nuevo_producto_id, nueva_sucursal_id)
            stock_sin_este = fila.cantidad - (delta_viejo if mismo_par else 0)
            if stock_sin_este < nueva_cantidad:
                raise ValueError(
                    f"Stock insuficiente: disponible {stock_sin_este}, solicitado {nueva_cantidad}"
                )

        if mismo_par:
            self.stock_service.aplicar_delta(
                movimiento.id_producto_id,
                movimiento.id_sucursal_id,
                delta_nuevo - delta_viejo,
            )
            pares_alerta = [(nuevo_producto_id, nueva_sucursal_id)]
        else:
            self.stock_service.aplicar_delta(
                movimiento.id_producto_id, movimiento.id_sucursal_id, -delta_viejo
            )
            self.stock_service.aplicar_delta(
                nuevo_producto_id, nueva_sucursal_id, delta_nuevo
            )
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
            programar_alerta(pid, sid)
        return self._to_dict(movimiento)

    @transaction.atomic
    def delete(self, entity_id, user=None):
        movimiento = self.repository.get_by_id(entity_id)
        if not movimiento:
            raise NotFoundError(
                f"{self.model.__name__} con id {entity_id} no encontrado"
            )
        delta = signo(movimiento.tipo) * movimiento.cantidad
        self.stock_service.aplicar_delta(
            movimiento.id_producto_id, movimiento.id_sucursal_id, -delta
        )
        programar_alerta(movimiento.id_producto_id, movimiento.id_sucursal_id)
        movimiento.delete()
        return {"message": f"{self.model.__name__} eliminado exitosamente"}

    # ---- flujos de venta ----

    def crear_salida_por_venta(
        self, detalle_venta, producto, sucursal_id, cantidad, user=None
    ):
        return self.salida_service.crear_salida_por_venta(
            detalle_venta, producto, sucursal_id, cantidad, user=user
        )

    def ajustar_salida_por_venta(
        self, detalle_venta, nueva_cantidad, producto=None, sucursal_id=None
    ):
        return self.salida_service.ajustar_salida_por_venta(
            detalle_venta,
            nueva_cantidad,
            producto=producto,
            sucursal_id=sucursal_id,
        )

    def revertir_salida_por_venta(self, detalle_venta):
        return self.salida_service.revertir_salida_por_venta(detalle_venta)

    # ---- consultas ----

    def get_inventario_por_sucursal(self, sucursal_id):
        return self.query_service.get_inventario_por_sucursal(sucursal_id)

    # ---- bulk ----

    @transaction.atomic
    def bulk_create(self, data, user=None):
        return MovimientoBulkService(self.create).bulk_create(data, user=user)
