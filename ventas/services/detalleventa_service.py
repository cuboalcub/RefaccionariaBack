from decimal import Decimal

from django.db import transaction

from ventas.models import detalleVenta
from ventas.repositories.detalleventa_repository import DetalleVentaRepository
from producto.models import Producto
from producto.repositories.producto_repository import ProductoRepository
from ventas.repositories.ventas_repository import VentaRepository
from inventario.services.detalle_inventario_service import DetalleInventarioService
from inventario.services.precio_sucursal_service import PrecioSucursalService
from repository.base_service import BaseService
from repository.exceptions import NotFoundError

class DetalleVentaService(BaseService):
    def __init__(self, detalle_repo=None, producto_repo=None, venta_repo=None):
        super().__init__(model=detalleVenta, repository=detalle_repo or DetalleVentaRepository())
        self.producto_repo = producto_repo or ProductoRepository()
        self.venta_repo = venta_repo or VentaRepository()
        self.inventario_service = DetalleInventarioService()

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_producto": instance.id_producto.id if instance.id_producto else None,
            "id_venta": instance.id_venta.id if instance.id_venta else None,
            "subtotal": str(instance.subtotal),
            "cantidad": instance.cantidad
        }

    def _calcular_subtotal(self, precio_venta, cantidad):
        return (Decimal(precio_venta) * cantidad).quantize(Decimal("0.01"))

    def _precio_aplicable(self, producto, venta):
        """Resuelve precio por sucursal si existe, sino fallback a Producto.precio_venta."""
        sucursal_id = None
        if venta and venta.id_inventario_id:
            # venta.id_inventario es Inventario, obtener sucursal
            # evitar query extra si ya está prefetched
            inv = venta.id_inventario
            if hasattr(inv, 'id_sucursal_id'):
                sucursal_id = inv.id_sucursal_id
            else:
                from inventario.models import Inventario
                inv_obj = Inventario.objects.filter(id=venta.id_inventario_id).first()
                sucursal_id = inv_obj.id_sucursal_id if inv_obj else None
        precio = PrecioSucursalService.resolver_precio_venta(producto, sucursal_id)
        return precio if precio is not None else producto.precio_venta

    def _recalcular_total(self, venta_id):
        total = self.repository.sum_subtotales(venta_id)
        venta = self.venta_repo.get_by_id(venta_id)
        if venta:
            venta.total = total
            venta.save(update_fields=["total"])
        return total

    def _validar_producto_en_inventario_sucursal(self, producto, venta, user=None):
        """Valida que el producto tenga stock >0 en el inventario/sucursal de la venta
        y que el usuario pertenezca a la misma sucursal (si tiene perfil)."""
        # Bloqueo cross-sucursal: si el usuario tiene perfil con sucursal, debe coincidir con la sucursal de la venta
        if user is not None:
            perfil = getattr(user, 'perfil', None)
            # Perfil puede ser RelatedObject sin cache: intentar obtener id_sucursal_id sin query extra
            user_sucursal_id = None
            if perfil is not None:
                user_sucursal_id = getattr(perfil, 'id_sucursal_id', None)
                # Si perfil no está cargado, intentar fetch
                if user_sucursal_id is None:
                    try:
                        # perfil podría ser DoesNotExist
                        user_sucursal_id = perfil.id_sucursal_id
                    except Exception:
                        user_sucursal_id = None
            # Si el usuario es staff/superuser, bypass (operador global)
            is_staff = getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
            if user_sucursal_id is not None and not is_staff:
                sucursal_venta_id = None
                try:
                    # venta.id_inventario puede ser instancia o id
                    inv = venta.id_inventario
                    if hasattr(inv, 'id_sucursal_id'):
                        sucursal_venta_id = inv.id_sucursal_id
                    else:
                        from inventario.models import Inventario
                        inv_obj = Inventario.objects.filter(id=venta.id_inventario_id).first()
                        sucursal_venta_id = inv_obj.id_sucursal_id if inv_obj else None
                except Exception:
                    sucursal_venta_id = None
                if sucursal_venta_id is not None and user_sucursal_id != sucursal_venta_id:
                    raise ValueError(
                        f"La venta pertenece al inventario {venta.id_inventario_id} (Sucursal {sucursal_venta_id}) y no puede ser operada por el usuario de la sucursal {user_sucursal_id}"
                    )

        # Validación producto en inventario/sucursal: stock >0
        stock = self.inventario_service.get_stock(producto.id, venta.id_inventario_id)
        if stock == 0:
            sucursal_id = None
            try:
                inv = venta.id_inventario
                if hasattr(inv, 'id_sucursal_id'):
                    sucursal_id = inv.id_sucursal_id
                else:
                    from inventario.models import Inventario
                    inv_obj = Inventario.objects.filter(id=venta.id_inventario_id).first()
                    sucursal_id = inv_obj.id_sucursal_id if inv_obj else None
            except Exception:
                pass
            raise ValueError(
                f"El producto '{producto.nombre}' no está disponible en el inventario {venta.id_inventario_id} (Sucursal {sucursal_id}) - stock 0"
            )

    def create(self, data, user=None):
        if "id_producto" not in data or "id_venta" not in data or "cantidad" not in data:
            raise ValueError("Faltan campos obligatorios: id_producto, id_venta, cantidad")
        with transaction.atomic():
            venta = self.venta_repo.get_by_id(data["id_venta"])
            if not venta:
                raise NotFoundError(f"Venta con id {data['id_venta']} no encontrado")
            if not venta.id_inventario:
                raise ValueError("La venta no tiene inventario asignado")
            producto = Producto.objects.select_for_update().get(id=data["id_producto"])

            self._validar_producto_en_inventario_sucursal(producto, venta, user=user)
            self.inventario_service._validar_salida(producto.id, venta.id_inventario_id, data["cantidad"])

            data["id_venta"] = venta
            data["id_producto"] = producto
            precio = self._precio_aplicable(producto, venta)
            data["subtotal"] = self._calcular_subtotal(precio, data["cantidad"])

            resultado = super().create(data)

            detalle = self.repository.get_by_id(resultado["id"])
            self.inventario_service.crear_salida_por_venta(
                detalle, producto, venta.id_inventario, data["cantidad"]
            )
            self._recalcular_total(venta.id)
            return resultado

    def update(self, id, data, user=None):
        with transaction.atomic():
            detalle = self.repository.get_by_id(id)
            if not detalle:
                raise NotFoundError(f"{self.model.__name__} con id {id} no encontrado")
            venta = self.venta_repo.get_by_id(detalle.id_venta_id)
            if not venta or not venta.id_inventario:
                raise ValueError("La venta no tiene inventario asignado")

            nueva_cantidad = data.get("cantidad", detalle.cantidad)
            nuevo_producto_id = data.get("id_producto", detalle.id_producto_id)
            nuevo_producto = Producto.objects.get(id=nuevo_producto_id)

            # Si cambia producto, validar que el nuevo producto esté en el inventario/sucursal
            if nuevo_producto_id != detalle.id_producto_id:
                self._validar_producto_en_inventario_sucursal(nuevo_producto, venta, user=user)

            self.inventario_service.ajustar_salida_por_venta(
                detalle,
                nueva_cantidad,
                producto=nuevo_producto,
                inventario=venta.id_inventario,
            )

            data["id_producto"] = nuevo_producto
            precio = self._precio_aplicable(nuevo_producto, venta)
            data["subtotal"] = self._calcular_subtotal(precio, nueva_cantidad)

            resultado = super().update(id, data)
            self._recalcular_total(venta.id)
            return resultado

    def delete(self, id):
        with transaction.atomic():
            detalle = self.repository.get_by_id(id)
            if not detalle:
                raise NotFoundError(f"{self.model.__name__} con id {id} no encontrado")
            venta_id = detalle.id_venta_id

            self.inventario_service.revertir_salida_por_venta(detalle)

            super().delete(id)
            self._recalcular_total(venta_id)
            return {"message": f"{self.model.__name__} eliminado exitosamente"}