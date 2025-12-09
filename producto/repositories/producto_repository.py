from producto.models import Producto
from repository.base_repository import BaseRepository

class ProductoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Producto)
