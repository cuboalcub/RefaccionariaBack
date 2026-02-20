from ventas.models import detalleVenta
from ventas.repositories.detalleventa_repository import DetalleVentaRepository
from producto.repositories.producto_repository import ProductoRepository
from ventas.repositories.ventas_repository import VentaRepository
from repository.base_service import BaseService

class DetalleVentaService(BaseService):
    def __init__(self):
        super().__init__(model=detalleVenta, repository=DetalleVentaRepository())
    
    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_producto": instance.id_producto.id if instance.id_producto else None,
            "id_venta": instance.id_venta.id if instance.id_venta else None,
            "subtotal": str(instance.subtotal),
            "cantidad": instance.cantidad
        }

    def create(self, data):
        producto_repository = ProductoRepository()
        producto = producto_repository.get_by_id(data['id_producto'])
        venta_repository = VentaRepository()
        venta = venta_repository.get_by_id(data['id_venta'])
        data["id_venta"] = venta
        data["id_producto"] = producto
        data["subtotal"] = producto.precio_venta * data["cantidad"]

        return super().create(data)
