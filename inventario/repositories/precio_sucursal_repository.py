from repository.base_repository import BaseRepository
from inventario.models import PrecioSucursal


class PrecioSucursalRepository(BaseRepository):
    def __init__(self):
        super().__init__(PrecioSucursal)

    def get_activo(self, producto_id, sucursal_id):
        return self.model_class.objects.filter(
            id_producto_id=producto_id, id_sucursal_id=sucursal_id, activo=True
        ).first()

    def get_historial(self, producto_id, sucursal_id):
        return list(
            self.model_class.objects.filter(
                id_producto_id=producto_id, id_sucursal_id=sucursal_id
            ).order_by('-vigente_desde', '-id')
        )

    def get_by_producto(self, producto_id):
        return list(
            self.model_class.objects.filter(id_producto_id=producto_id).order_by('-activo', '-vigente_desde')
        )

    def get_by_sucursal(self, sucursal_id):
        return list(
            self.model_class.objects.filter(id_sucursal_id=sucursal_id).order_by('-activo', '-vigente_desde')
        )
