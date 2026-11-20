from repository.base_service import BaseService
from sucursales.models import Sucursal
from sucursales.repositories.sucursal_repository import SucursalRepository


class SucursalService(BaseService):
    def __init__(self):
        super().__init__(model=Sucursal, repository=SucursalRepository())

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "nombre_sucursal": instance.nombre_sucursal,
            "codigo_sucursal": instance.codigo_sucursal,
            "ubicacion": instance.ubicacion,
            "codigo_postal": instance.codigo_postal,
            "numero_telefono": instance.numero_telefono,
            "correo_electronico": instance.correo_electronico,
        }
