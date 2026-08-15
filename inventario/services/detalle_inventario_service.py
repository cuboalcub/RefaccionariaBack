from django.db import transaction

from inventario.models import DetalleInventario, Inventario, MovimientoInventario
from inventario.repositories.detalle_inventario_repository import DetalleInventarioRepository
from producto.models import Producto, Proveedor
from repository.base_service import BaseService


class DetalleInventarioService(BaseService):
    def __init__(self):
        super().__init__(model=DetalleInventario, repository=DetalleInventarioRepository())

    def _validar(self, data):
        if "id_producto" not in data or data["id_producto"] is None:
            raise ValueError("Faltan campos obligatorios: id_producto")
        if "id_inventario" not in data or data["id_inventario"] is None:
            raise ValueError("Faltan campos obligatorios: id_inventario")
        if "id_movimiento" not in data or data["id_movimiento"] is None:
            raise ValueError("Faltan campos obligatorios: id_movimiento")
        if "cantidad" not in data or data["cantidad"] is None:
            raise ValueError("Faltan campos obligatorios: cantidad")
        if not Producto.objects.filter(id=data["id_producto"]).exists():
            raise ValueError("El producto indicado no existe")
        if not Inventario.objects.filter(id=data["id_inventario"]).exists():
            raise ValueError("El inventario indicado no existe")
        if not MovimientoInventario.objects.filter(id=data["id_movimiento"]).exists():
            raise ValueError("El movimiento indicado no existe")
        if data["cantidad"] < 0:
            raise ValueError("La cantidad no puede ser negativa")

    def _aplicar_stock(self, producto, tipo, cantidad_original, cantidad_nueva):
        if tipo == MovimientoInventario.TipoMovimiento.ENTRADA:
            producto.existencia += cantidad_nueva - cantidad_original
        elif tipo == MovimientoInventario.TipoMovimiento.SALIDA:
            producto.existencia -= cantidad_nueva - cantidad_original

    def _validar_salida(self, producto, cantidad):
        if producto.existencia < cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {producto.existencia}, solicitado {cantidad}"
            )

    def create(self, data):
        self._validar(data)
        movimiento = MovimientoInventario.objects.get(id=data["id_movimiento"])

        with transaction.atomic():
            producto = Producto.objects.select_for_update().get(id=data["id_producto"])
            if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
                self._validar_salida(producto, data["cantidad"])

            data["id_producto"] = producto
            data["id_inventario"] = Inventario.objects.get(id=data["id_inventario"])
            data["id_movimiento"] = movimiento
            if "id_proveedor" in data and data["id_proveedor"]:
                if not Proveedor.objects.filter(id=data["id_proveedor"]).exists():
                    raise ValueError("El proveedor indicado no existe")
                data["id_proveedor"] = Proveedor.objects.get(id=data["id_proveedor"])
            else:
                data.pop("id_proveedor", None)

            resultado = super().create(data)

            self._aplicar_stock(producto, movimiento.tipo, 0, data["cantidad"])
            producto.save(update_fields=["existencia"])

        return resultado

    def update(self, id, data):
        with transaction.atomic():
            detalle = self.repository.get_by_id(id)
            if not detalle:
                raise ValueError(f"{self.model.__name__} con id {id} no encontrado")

            movimiento_id = data.get("id_movimiento", detalle.id_movimiento_id)
            movimiento = MovimientoInventario.objects.get(id=movimiento_id)
            nueva_cantidad = data.get("cantidad", detalle.cantidad)
            if nueva_cantidad < 0:
                raise ValueError("La cantidad no puede ser negativa")

            producto = Producto.objects.select_for_update().get(id=detalle.id_producto_id)

            if data.get("id_producto", detalle.id_producto_id) != detalle.id_producto_id:
                nuevo_producto = Producto.objects.select_for_update().get(id=data["id_producto"])
                self._aplicar_stock(producto, detalle.id_movimiento.tipo, detalle.cantidad, 0)
                if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
                    self._validar_salida(nuevo_producto, nueva_cantidad)
                self._aplicar_stock(nuevo_producto, movimiento.tipo, 0, nueva_cantidad)
                nuevo_producto.save(update_fields=["existencia"])
                data["id_producto"] = nuevo_producto
            else:
                self._aplicar_stock(producto, detalle.id_movimiento.tipo, detalle.cantidad, 0)
                if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
                    self._validar_salida(producto, nueva_cantidad)
                self._aplicar_stock(producto, movimiento.tipo, 0, nueva_cantidad)
                producto.save(update_fields=["existencia"])

            if "id_inventario" in data and data["id_inventario"]:
                if not Inventario.objects.filter(id=data["id_inventario"]).exists():
                    raise ValueError("El inventario indicado no existe")
                data["id_inventario"] = Inventario.objects.get(id=data["id_inventario"])
            data["id_movimiento"] = movimiento

            if "id_proveedor" in data:
                if not data["id_proveedor"]:
                    data["id_proveedor"] = None
                elif not Proveedor.objects.filter(id=data["id_proveedor"]).exists():
                    raise ValueError("El proveedor indicado no existe")
                else:
                    data["id_proveedor"] = Proveedor.objects.get(id=data["id_proveedor"])

            return super().update(id, data)

    def delete(self, id, user=None):
        with transaction.atomic():
            detalle = self.repository.get_by_id(id)
            if not detalle:
                raise ValueError(f"{self.model.__name__} con id {id} no encontrado")

            producto = Producto.objects.select_for_update().get(id=detalle.id_producto_id)
            movimiento = detalle.id_movimiento

            if movimiento.tipo == MovimientoInventario.TipoMovimiento.ENTRADA:
                if producto.existencia - detalle.cantidad < 0:
                    raise ValueError(
                        f"No se puede revertir: stock insuficiente (disponible {producto.existencia})"
                    )
                producto.existencia -= detalle.cantidad
            elif movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
                producto.existencia += detalle.cantidad
            producto.save(update_fields=["existencia"])

            return super().delete(id, user)

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "id_producto": instance.id_producto_id,
            "id_inventario": instance.id_inventario_id,
            "id_proveedor": instance.id_proveedor_id,
            "id_movimiento": instance.id_movimiento_id,
            "cantidad": instance.cantidad,
            "update_at": instance.update_at.isoformat() if instance.update_at else None,
        }
