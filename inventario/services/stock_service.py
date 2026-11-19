from django.db.models import F

from inventario.models import Stock
from inventario.repositories.stock_repository import StockRepository


class StockService:
    """Lectura y mutación de la fila cacheada de Stock por (sucursal, producto)."""

    def __init__(self, stock_repo=None):
        self.stock_repo = stock_repo or StockRepository()

    def get_stock(self, producto_id, sucursal_id):
        return self.stock_repo.get_stock(producto_id, sucursal_id)

    def get_stock_map_por_sucursal(self, sucursal_id):
        return self.stock_repo.get_stock_map_por_sucursal(sucursal_id)

    def validar_salida(self, producto_id, sucursal_id, cantidad):
        disponible = self.get_stock(producto_id, sucursal_id)
        if disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {disponible}, solicitado {cantidad}"
            )

    def fila_stock(self, producto_id, sucursal_id):
        """Fila de Stock bloqueada para escribir (se crea al vuelo si falta)."""
        return Stock.objects.select_for_update().get_or_create(
            id_producto_id=producto_id,
            id_sucursal_id=sucursal_id,
            defaults={"cantidad": 0},
        )[0]

    def aplicar_delta(self, producto_id, sucursal_id, delta):
        fila = self.fila_stock(producto_id, sucursal_id)
        fila.cantidad = F("cantidad") + delta
        fila.save(update_fields=["cantidad"])
        fila.refresh_from_db(fields=["cantidad"])
        return fila.cantidad
