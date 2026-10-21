from ventas.models import MetodoPago
from repository.base_repository import BaseRepository

class MetodoPagoRepository(BaseRepository):
    def __init__(self):
        super().__init__(MetodoPago)
