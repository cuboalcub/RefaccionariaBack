from repository.base_repository import BaseRepository
from sucursales.models import Sucursal


class SucursalRepository(BaseRepository):
    def __init__(self):
        super().__init__(Sucursal)
