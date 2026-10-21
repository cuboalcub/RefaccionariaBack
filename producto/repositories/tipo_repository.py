from repository.base_repository import BaseRepository
from producto.models import Tipo

class TipoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Tipo)
