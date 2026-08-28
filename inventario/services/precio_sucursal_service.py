from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from inventario.models import PrecioSucursal
from inventario.repositories.precio_sucursal_repository import PrecioSucursalRepository
from producto.models import Producto
from repository.base_service import BaseService
from repository.exceptions import NotFoundError
from sucursales.models import Sucursal


class PrecioSucursalService(BaseService):
    def __init__(self):
        super().__init__(model=PrecioSucursal, repository=PrecioSucursalRepository())

    def _validar(self, data, partial=False):
        required = ['id_producto', 'id_sucursal', 'precio_venta']
        for f in required:
            if not partial and (f not in data or data[f] is None):
                raise ValueError(f"Faltan campos obligatorios: {f}")
        if 'precio_venta' in data and data['precio_venta'] is not None:
            try:
                pv = Decimal(str(data['precio_venta']))
            except (InvalidOperation, ValueError, TypeError):
                raise ValueError("precio_venta debe ser un número válido")
            if pv <= 0:
                raise ValueError("precio_venta debe ser mayor a 0")
        if 'id_producto' in data and data['id_producto'] is not None:
            if not Producto.objects.filter(id=data['id_producto']).exists():
                raise ValueError("El producto indicado no existe")
        if 'id_sucursal' in data and data['id_sucursal'] is not None:
            if not Sucursal.objects.filter(id=data['id_sucursal']).exists():
                raise ValueError("La sucursal indicada no existe")

    def _resolver_fks(self, data):
        if 'id_producto' in data:
            data['id_producto'] = Producto.objects.get(id=data['id_producto'])
        if 'id_sucursal' in data:
            data['id_sucursal'] = Sucursal.objects.get(id=data['id_sucursal'])
        # vigente_desde editable: si no viene, usar now
        if 'vigente_desde' not in data or not data['vigente_desde']:
            data['vigente_desde'] = timezone.now()
        # activo default True
        if 'activo' not in data:
            data['activo'] = True
        return data

    @transaction.atomic
    def create(self, data):
        data = dict(data)
        self._validar(data)
        # Si se crea activo, desactivar anterior del mismo par
        if data.get('activo', True):
            PrecioSucursal.objects.select_for_update().filter(
                id_producto_id=data['id_producto'],
                id_sucursal_id=data['id_sucursal'],
                activo=True,
            ).update(activo=False)
        data = self._resolver_fks(data)
        return super().create(data)

    @transaction.atomic
    def update(self, id, data):
        data = dict(data)
        self._validar(data, partial=True)
        instance = self.repository.get_by_id(id)
        if not instance:
            raise NotFoundError(f"{self.model.__name__} con id {id} no encontrado")

        nuevo_producto_id = data.get('id_producto', instance.id_producto_id)
        nuevo_sucursal_id = data.get('id_sucursal', instance.id_sucursal_id)
        # validar FKs si cambiaron
        if 'id_producto' in data and not Producto.objects.filter(id=nuevo_producto_id).exists():
            raise ValueError("El producto indicado no existe")
        if 'id_sucursal' in data and not Sucursal.objects.filter(id=nuevo_sucursal_id).exists():
            raise ValueError("La sucursal indicada no existe")

        # si se activa, desactivar otro activo del par destino (excluyendo self)
        activar = data.get('activo', instance.activo)
        # si cambia de par y queda activo, también desactivar en destino
        if activar:
            PrecioSucursal.objects.select_for_update().filter(
                id_producto_id=nuevo_producto_id,
                id_sucursal_id=nuevo_sucursal_id,
                activo=True,
            ).exclude(id=id).update(activo=False)

        if 'id_producto' in data:
            data['id_producto'] = Producto.objects.get(id=nuevo_producto_id)
        if 'id_sucursal' in data:
            data['id_sucursal'] = Sucursal.objects.get(id=nuevo_sucursal_id)
        if 'precio_venta' in data and data['precio_venta'] is not None:
            # validar >0 ya hecho
            pass
        return super().update(id, data)

    def get_precio_activo(self, producto_id, sucursal_id):
        obj = self.repository.get_activo(producto_id, sucursal_id)
        if not obj:
            return None
        return self._to_dict(obj)

    def get_historial(self, producto_id, sucursal_id):
        objs = self.repository.get_historial(producto_id, sucursal_id)
        return [self._to_dict(o) for o in objs]

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "id_producto": instance.id_producto_id,
            "id_sucursal": instance.id_sucursal_id,
            "precio_venta": str(instance.precio_venta),
            "vigente_desde": instance.vigente_desde.isoformat() if instance.vigente_desde else None,
            "activo": instance.activo,
        }

    @staticmethod
    def resolver_precio_venta(producto, sucursal_id=None):
        """Devuelve Decimal del precio aplicable: PrecioSucursal activo si existe, sino Producto.precio_venta."""
        if sucursal_id is not None:
            ps = PrecioSucursal.objects.filter(
                id_producto_id=producto.id if hasattr(producto, 'id') else producto,
                id_sucursal_id=sucursal_id,
                activo=True,
            ).first()
            if ps:
                return ps.precio_venta
        # fallback
        if hasattr(producto, 'precio_venta'):
            return producto.precio_venta
        # si producto es id
        prod = Producto.objects.filter(id=producto).first()
        return prod.precio_venta if prod else None
