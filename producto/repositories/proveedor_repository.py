from producto.models import Proveedor
from repository.base_repository import BaseRepository

class ProveedorRepository(BaseRepository):
    def __init__(self):
        super().__init__(Proveedor)
