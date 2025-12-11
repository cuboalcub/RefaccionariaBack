from ventas.models import detalleVenta
from repository.base_repository import BaseRepository

class DetalleVentaRepository(BaseRepository):
    def __init__(self):
        super().__init__(detalleVenta)

