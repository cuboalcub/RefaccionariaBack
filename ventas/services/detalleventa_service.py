from django.db import transaction

from ventas.models import detalleVenta
from ventas.repositories.detalleventa_repository import DetalleVentaRepository
from producto.models import Producto
from producto.repositories.producto_repository import ProductoRepository
from ventas.repositories.ventas_repository import VentaRepository
from repository.base_service import BaseService

class DetalleVentaService(BaseService):
    def __init__(self, detalle_repo=None, producto_repo=None, venta_repo=None):
        super().__init__(model=detalleVenta, repository=detalle_repo or DetalleVentaRepository())
        self.producto_repo = producto_repo or ProductoRepository()
        self.venta_repo = venta_repo or VentaRepository()

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_producto": instance.id_producto.id if instance.id_producto else None,
            "id_venta": instance.id_venta.id if instance.id_venta else None,
            "subtotal": str(instance.subtotal),
            "cantidad": instance.cantidad
        }

    def _recalcular_total(self, venta_id):
        total = self.repository.sum_subtotales(venta_id)
        venta = self.venta_repo.get_by_id(venta_id)
        if venta:
            venta.total = total
            venta.save(update_fields=["total"])
        return total

    def create(self, data):
        if "id_producto" not in data or "id_venta" not in data or "cantidad" not in data:
            raise ValueError("Faltan campos obligatorios: id_producto, id_venta, cantidad")

        with transaction.atomic():
            producto = Producto.objects.select_for_update().get(id=data["id_producto"])
            if producto.existencia < data["cantidad"]:
                raise ValueError(f"Stock insuficiente: disponible {producto.existencia}, solicitado {data['cantidad']}")
            venta = self.venta_repo.get_by_id(data["id_venta"])
            if not venta:
                raise ValueError(f"Venta con id {data['id_venta']} no encontrado")
            data["id_venta"] = venta
            data["id_producto"] = producto
            producto.existencia -= data["cantidad"]
            producto.save(update_fields=["existencia"])

            resultado = super().create(data)
            self._recalcular_total(venta.id)
            return resultado

    def update(self, id, data):
        with transaction.atomic():
            detalle = self.repository.get_by_id(id)
            if not detalle:
                raise ValueError(f"{self.model.__name__} con id {id} no encontrado")
            venta_id = detalle.id_venta_id
            nueva_cantidad = data.get("cantidad", detalle.cantidad)
            nuevo_producto_id = data.get("id_producto", detalle.id_producto_id)

            if nuevo_producto_id != detalle.id_producto_id:
                old_producto = Producto.objects.select_for_update().get(id=detalle.id_producto_id)
                old_producto.existencia += detalle.cantidad
                old_producto.save(update_fields=["existencia"])

                nuevo_producto = Producto.objects.select_for_update().get(id=nuevo_producto_id)
                if nuevo_producto.existencia < nueva_cantidad:
                    raise ValueError(f"Stock insuficiente: disponible {nuevo_producto.existencia}, solicitado {nueva_cantidad}")
                nuevo_producto.existencia -= nueva_cantidad
                nuevo_producto.save(update_fields=["existencia"])
                data["id_producto"] = nuevo_producto
            else:
                if "id_producto" in data:
                    data["id_producto"] = Producto.objects.get(id=detalle.id_producto_id)
                if nueva_cantidad != detalle.cantidad:
                    producto = Producto.objects.select_for_update().get(id=detalle.id_producto_id)
                    delta = nueva_cantidad - detalle.cantidad
                    if producto.existencia - delta < 0:
                        raise ValueError(f"Stock insuficiente: disponible {producto.existencia}, solicitado {nueva_cantidad}")
                    producto.existencia -= delta
                    producto.save(update_fields=["existencia"])

            resultado = super().update(id, data)
            self._recalcular_total(venta_id)
            return resultado

    def delete(self, id):
        with transaction.atomic():
            detalle = self.repository.get_by_id(id)
            if not detalle:
                raise ValueError(f"{self.model.__name__} con id {id} no encontrado")
            venta_id = detalle.id_venta_id

            producto = Producto.objects.select_for_update().get(id=detalle.id_producto_id)
            producto.existencia += detalle.cantidad
            producto.save(update_fields=["existencia"])

            super().delete(id)
            self._recalcular_total(venta_id)
            return {"message": f"{self.model.__name__} eliminado exitosamente"}
