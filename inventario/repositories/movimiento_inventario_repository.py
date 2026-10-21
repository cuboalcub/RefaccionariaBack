from repository.base_repository import BaseRepository
from inventario.models import MovimientoInventario


class MovimientoInventarioRepository(BaseRepository):
    def __init__(self):
        super().__init__(MovimientoInventario)
