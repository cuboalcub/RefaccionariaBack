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
            "subtotal": str(instance.subtotal) if instance.subtotal else "0.00",
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
        ventas = VentaRepository()
        venta = ventas.get_by_id(entity_id)
        if not venta:
            return None

        detalles = self.repository.get_by_venta(venta.id)
        producto_repository = ProductoRepository()
        detalles_list = []

        for detalle in detalles:
            producto_data = None
            if detalle.id_producto:
                p = producto_repository.get_by_id(detalle.id_producto.id)
                if p:
                    producto_data = {
                        "id": p.id,
                        "nombre": p.nombre,
                        "precio_venta": str(p.precio_venta),
                        "codigo_barras": p.codigo_barras,
                    }

            detalles_list.append(
                {
                    "id": detalle.id,
                    "producto": producto_data,
                    "cantidad": detalle.cantidad,
                    "subtotal": str(detalle.subtotal) if detalle.subtotal else "0.00",
                }
            )

        return {
            "id": venta.id,
            "fecha": venta.fecha.isoformat() if venta.fecha else None,
            "total": str(venta.total),
            "detalles": detalles_list,
        }

    def get_by_venta(self, entity_id):
        detalle = self.repository.get_by_venta(entity_id)
        return detalle
