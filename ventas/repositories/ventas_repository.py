from ventas.models import venta
from repository.base_repository import BaseRepository

class VentaRepository(BaseRepository):
    def __init__(self):
        super().__init__(venta)