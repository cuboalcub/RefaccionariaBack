from django.core.exceptions import ValidationError
from django.db import transaction

from inventario.services.movimiento_inventario_service import (
    MovimientoInventarioService,
)
from producto.models import Producto
from producto.repositories.producto_repository import ProductoRepository
from repository.base_service import BaseService
from repository.exceptions import NotFoundError
from ventas.models import DetalleVenta, Venta
from ventas.repositories.detalle_venta_repository import DetalleVentaRepository
from ventas.repositories.venta_repository import VentaRepository
from ventas.services.detalle_venta_calculo import DetalleVentaCalculo
from ventas.services.detalle_venta_validacion import DetalleVentaValidacion
from ventas.services.venta_stock import bloquear_producto, bloquear_stock


class DetalleVentaService(BaseService):
    def __init__(self, detalle_repo=None, producto_repo=None, venta_repo=None):
        super().__init__(model=DetalleVenta, repository=detalle_repo or DetalleVentaRepository())
        self.producto_repo = producto_repo or ProductoRepository()
        self.venta_repo = venta_repo or VentaRepository()
        self.movimiento_service = MovimientoInventarioService()
        self.calculo = DetalleVentaCalculo(self.repository, self.venta_repo)
        self.validacion = DetalleVentaValidacion(self.movimiento_service.stock_service)

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_producto": instance.id_producto.id if instance.id_producto else None,
            "id_venta": instance.id_venta.id if instance.id_venta else None,
            "cantidad": instance.cantidad,
            "subtotal": str(instance.subtotal) if instance.subtotal else "0.00",
        }

    def _calcular_subtotal(self, precio_venta, cantidad):
        return self.calculo.calcular_subtotal(precio_venta, cantidad)

    def _precio_aplicable(self, producto, venta):
        return self.calculo.precio_aplicable(producto, venta)

    def _recalcular_total(self, venta_id):
        return self.calculo.recalcular_total(venta_id)

    def _validar_venta_operable(self, venta):
        return self.validacion.validar_venta_operable(venta)

    def _validar_cantidad(self, cantidad):
        return self.validacion.validar_cantidad(cantidad)

    def _validar_producto_en_inventario_sucursal(self, producto, venta, user=None):
        return self.validacion.validar_producto_en_inventario_sucursal(
            producto, venta, user=user
        )

    def create(self, data, user=None):
        if "id_producto" not in data or "id_venta" not in data or "cantidad" not in data:
            raise ValueError("Faltan campos obligatorios: id_producto, id_venta, cantidad")
        self._validar_cantidad(data["cantidad"])
        with transaction.atomic():
            venta = self.venta_repo.get_by_id(data["id_venta"])
            if not venta:
                raise NotFoundError(f"Venta con id {data['id_venta']} no encontrado")
            self._validar_venta_operable(venta)
            try:
                producto = bloquear_producto(data["id_producto"])
            except (Producto.DoesNotExist, ValidationError, ValueError, TypeError):
                raise NotFoundError(f"Producto con id {data['id_producto']} no encontrado")
            # Serializa la fila de stock de la venta para que dos ajustes
            # concurrentes no lean el mismo stock a la vez.
            bloquear_stock(producto.id, venta.id_sucursal_id)

            self._validar_producto_en_inventario_sucursal(producto, venta, user=user)
            self.movimiento_service.validar_salida(
                producto.id, venta.id_sucursal_id, data["cantidad"]
            )

            data["id_venta"] = venta
            data["id_producto"] = producto
            precio = self._precio_aplicable(producto, venta)
            data["subtotal"] = self._calcular_subtotal(precio, data["cantidad"])

            resultado = super().create(data)

            detalle = self.repository.get_by_id(resultado["id"])
            self.movimiento_service.crear_salida_por_venta(
                detalle, producto, venta.id_sucursal_id, data["cantidad"], user=user
            )
            self._recalcular_total(venta.id)
            return resultado

    def update(self, id, data, user=None):
        with transaction.atomic():
            detalle = self.repository.get_by_id(id)
            if not detalle:
                raise NotFoundError(f"{self.model.__name__} con id {id} no encontrado")
            # Bloqueos espejando el camino atómico: la venta y las filas de
            # stock, para que dos ajustes concurrentes no lean el mismo stock.
            try:
                Venta.objects.select_for_update().get(id=detalle.id_venta_id)
            except Venta.DoesNotExist:
                raise NotFoundError(f"Venta con id {detalle.id_venta_id} no encontrado")
            venta = self.venta_repo.get_by_id(detalle.id_venta_id)
            if not venta:
                raise NotFoundError(f"Venta con id {detalle.id_venta_id} no encontrado")
            self._validar_venta_operable(venta)

            nueva_cantidad = data.get("cantidad", detalle.cantidad)
            self._validar_cantidad(nueva_cantidad)
            nuevo_producto_id = data.get("id_producto", detalle.id_producto_id)
            try:
                nuevo_producto = bloquear_producto(nuevo_producto_id)
            except Producto.DoesNotExist:
                raise NotFoundError(f"Producto con id {nuevo_producto_id} no encontrado")
            bloquear_stock(nuevo_producto_id, venta.id_sucursal_id)

            # Si cambia producto, validar que el nuevo producto esté en el stock de la sucursal
            if nuevo_producto_id != detalle.id_producto_id:
                self._validar_producto_en_inventario_sucursal(nuevo_producto, venta, user=user)

            self.movimiento_service.ajustar_salida_por_venta(
                detalle,
                nueva_cantidad,
                producto=nuevo_producto,
                sucursal_id=venta.id_sucursal_id,
            )

            data["id_producto"] = nuevo_producto
            precio = self._precio_aplicable(nuevo_producto, venta)
            data["subtotal"] = self._calcular_subtotal(precio, nueva_cantidad)

            resultado = super().update(id, data)
            self._recalcular_total(venta.id)
            return resultado

    def delete(self, id, user=None):
        with transaction.atomic():
            detalle = self.repository.get_by_id(id)
            if not detalle:
                raise NotFoundError(f"{self.model.__name__} con id {id} no encontrado")
            venta = self.venta_repo.get_by_id(detalle.id_venta_id)
            if venta:
                self._validar_venta_operable(venta)
            venta_id = detalle.id_venta_id

            self.movimiento_service.revertir_salida_por_venta(detalle)

            super().delete(id, user)
            self._recalcular_total(venta_id)
            return {"message": f"{self.model.__name__} eliminado exitosamente"}
