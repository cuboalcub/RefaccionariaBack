from repository.base_repository import BaseRepository
from inventario.models import Inventario


class InventarioRepository(BaseRepository):
    def __init__(self):
        super().__init__(Inventario)
