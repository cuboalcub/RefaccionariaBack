from ventas.models import metodoPago
from repository.base_repository import BaseRepository

class MetodoPagoRepository(BaseRepository):
    def __init__(self):
        super().__init__(metodoPago)
