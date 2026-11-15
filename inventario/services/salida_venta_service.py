from inventario.models import MovimientoInventario
from inventario.repositories.movimiento_inventario_repository import (
    MovimientoInventarioRepository,
)
from inventario.services.movimiento_utils import movimiento_to_dict, programar_alerta
from inventario.services.stock_service import StockService


class SalidaVentaService:
    """Movimientos SALIDA generados por el ciclo de vida de una venta."""

    def __init__(self, repository=None, stock_service=None):
        self.repository = repository or MovimientoInventarioRepository()
        self.stock_service = stock_service or StockService()

    def crear_salida_por_venta(
        self, detalle_venta, producto, sucursal_id, cantidad, user=None
    ):
        fila = self.stock_service.fila_stock(producto.id, sucursal_id)
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
        self.stock_service.aplicar_delta(producto.id, sucursal_id, -cantidad)
        programar_alerta(producto.id, sucursal_id)
        return movimiento_to_dict(movimiento)

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
        fila = self.stock_service.fila_stock(nuevo_producto.id, nueva_sucursal)
        stock_sin_este = fila.cantidad + (
            movimiento.cantidad if misma_par else 0
        )
        if stock_sin_este < nueva_cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {stock_sin_este}, solicitado {nueva_cantidad}"
            )

        if misma_par:
            self.stock_service.aplicar_delta(
                movimiento.id_producto_id,
                movimiento.id_sucursal_id,
                movimiento.cantidad - nueva_cantidad,
            )
            pares_alerta = [(nuevo_producto.id, nueva_sucursal)]
        else:
            self.stock_service.aplicar_delta(
                movimiento.id_producto_id, movimiento.id_sucursal_id, movimiento.cantidad
            )
            self.stock_service.aplicar_delta(
                nuevo_producto.id, nueva_sucursal, -nueva_cantidad
            )
            pares_alerta = [
                (movimiento.id_producto_id, movimiento.id_sucursal_id),
                (nuevo_producto.id, nueva_sucursal),
            ]

        movimiento.cantidad = nueva_cantidad
        movimiento.id_producto = nuevo_producto
        movimiento.id_sucursal_id = nueva_sucursal
        movimiento.save(update_fields=["id_producto", "id_sucursal", "cantidad", "tipo"])
        for pid, sid in pares_alerta:
            programar_alerta(pid, sid)
        return movimiento_to_dict(movimiento)

    def revertir_salida_por_venta(self, detalle_venta):
        movimiento = self.repository.filter(
            {"id_detalle_venta_id": detalle_venta.id}
        )
        movimiento = movimiento[0] if movimiento else None
        if not movimiento:
            return None
        producto_id = movimiento.id_producto_id
        sucursal_id = movimiento.id_sucursal_id
        self.stock_service.aplicar_delta(
            producto_id, sucursal_id, movimiento.cantidad
        )
        programar_alerta(producto_id, sucursal_id)
        movimiento.delete()
        return True
