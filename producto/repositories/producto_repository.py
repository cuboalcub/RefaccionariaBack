from producto.models import Producto
from repository.base_repository import BaseRepository


class ProductoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Producto)

    def get_by_codigo_barras(self, codigo_barras):
        return Producto.objects.filter(codigo_barras=codigo_barras).first()

    def get_by_categoria(self, categoria: str):
        return Producto.objects.filter(id_tipo__nombre=categoria).all()

    def search(self, query: str):
        return Producto.objects.filter(
            Q(nombre__icontains=query) | Q(clave__icontains=query)
        ).all()
