from django.db.models import Sum

from ventas.models import DetalleVenta
from repository.base_repository import BaseRepository


class DetalleVentaRepository(BaseRepository):
    def __init__(self):
        super().__init__(DetalleVenta)

    def sum_subtotales(self, venta_id):
        return (
            self.model_class.objects
            .filter(id_venta_id=venta_id)
            .aggregate(total=Sum('subtotal'))['total'] or 0
        )
    def get_by_venta(self, entity_id):
        return DetalleVenta.objects.filter(id_venta=entity_id)
