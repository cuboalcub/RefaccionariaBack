from repository.base_repository import BaseRepository
from inventario.models import Stock


class StockRepository(BaseRepository):
    def __init__(self):
        super().__init__(Stock)

    def get_stock(self, producto_id, sucursal_id):
        fila = self.model_class.objects.filter(
            id_producto_id=producto_id, id_sucursal_id=sucursal_id
        ).first()
        return fila.cantidad if fila else 0

    def get_stock_map_por_sucursal(self, sucursal_id):
        """Devuelve dict {producto_id: stock} para productos con stock >0 en la sucursal."""
        filas = self.model_class.objects.filter(
            id_sucursal_id=sucursal_id, cantidad__gt=0
        ).values_list("id_producto_id", "cantidad")
        return {producto_id: cantidad for producto_id, cantidad in filas}
