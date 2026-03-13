from producto.models import Producto
from repository.base_repository import BaseRepository

class ProductoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Producto)

    def get_by_codigo_barras(self, codigo_barras):
        return self.model.objects.filter(codigo_barras=codigo_barras).first()