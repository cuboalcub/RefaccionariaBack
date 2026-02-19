from ventas.models import venta
from repository.base_repository import BaseRepository

class VentaRepository(BaseRepository):
    def __init__(self):
        super().__init__(venta)

    def get_ventas_por_rango(self, fecha_inicio, fecha_fin):

        return (
            self.model_class.objects
            .filter(fecha__range=(fecha_inicio, fecha_fin))
            .select_related('id_usuario', 'id_metodoPago')
            .prefetch_related('detalleventa_set__id_producto')
            .order_by('fecha')
        )