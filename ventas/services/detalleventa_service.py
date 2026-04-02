from producto.repositories.producto_repository import ProductoRepository
from repository.base_service import BaseService
from ventas.models import detalleVenta
from ventas.repositories.detalleventa_repository import DetalleVentaRepository
from ventas.repositories.ventas_repository import VentaRepository


class DetalleVentaService(BaseService):
    def __init__(self):
        super().__init__(model=detalleVenta, repository=DetalleVentaRepository())

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_producto": instance.id_producto.id if instance.id_producto else None,
            "id_venta": instance.id_venta.id if instance.id_venta else None,
            "cantidad": instance.cantidad,
        }

    def create(self, data):
        producto_repository = ProductoRepository()
        producto = producto_repository.get_by_id(data["id_producto"])
        venta_repository = VentaRepository()
        venta = venta_repository.get_by_id(data["id_venta"])
        data["id_venta"] = venta
        data["id_producto"] = producto
        data["subtotal"] = (
            producto.precio_venta * data["cantidad"]
            + producto.precio_venta * data["cantidad"] * 0.16
        )

        return super().create(data)

    def get_by_id(self, entity_id):
        detalle = self.repository.get_by_id(entity_id)
        if detalle:
            productos = ProductoRepository()
            producto = productos.get_by_id(detalle.id_producto.id)
            return {
                "id": detalle.id,
                "id_producto": detalle.id_producto.id if detalle.id_producto else None,
                "id_venta": detalle.id_venta.id if detalle.id_venta else None,
                "cantidad": detalle.cantidad,
                "subtotal": str(detalle.subtotal),
                "producto": {
                    "id": producto.id,
                    "nombre": producto.nombre,
                    "precio_venta": str(producto.precio_venta),
                },
            }
        return None
