from repository.base_service import BaseService
from sucursales.models import Sucursal
from sucursales.repositories.sucursal_repository import SucursalRepository


class SucursalService(BaseService):
    def __init__(self):
        super().__init__(model=Sucursal, repository=SucursalRepository())

    def _to_dict(self, instance):
        if not instance:
            return None
        return {"id": instance.id, "ubicacion": instance.ubicacion}
