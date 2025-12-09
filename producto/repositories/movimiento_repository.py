from producto.models import Movimiento
from repository.base_repository import BaseRepository


class MovimientoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Movimiento)
