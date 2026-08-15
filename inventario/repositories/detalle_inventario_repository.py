from repository.base_repository import BaseRepository
from inventario.models import DetalleInventario


class DetalleInventarioRepository(BaseRepository):
    def __init__(self):
        super().__init__(DetalleInventario)
