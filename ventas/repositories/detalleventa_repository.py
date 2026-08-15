from django.db.models import Sum

from ventas.models import detalleVenta
from repository.base_repository import BaseRepository

class DetalleVentaRepository(BaseRepository):
    def __init__(self):
        super().__init__(detalleVenta)

    def sum_subtotales(self, venta_id):
        return (
            self.model_class.objects
            .filter(id_venta_id=venta_id)
            .aggregate(total=Sum('subtotal'))['total'] or 0
        )