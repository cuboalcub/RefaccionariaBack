from django.db.models import Sum

from repository.base_repository import BaseRepository
from ventas.models import Venta


class VentaRepository(BaseRepository):
    def __init__(self):
        super().__init__(Venta)

    def get_ventas(self, sucursal_id=None):
        qs = self.model_class.objects.select_related(
            'id_usuario', 'id_metodo_pago', 'id_sucursal'
        ).order_by('-fecha', '-id')
        if sucursal_id is not None:
            qs = qs.filter(id_sucursal_id=sucursal_id)
        return qs

    def get_ventas_por_rango(self, fecha_inicio, fecha_fin):

        return (
            self.model_class.objects
            .filter(fecha__range=(fecha_inicio, fecha_fin), estado='completada')
            .select_related('id_usuario', 'id_metodo_pago')
            .prefetch_related('detalleventa_set__id_producto')
            .order_by('fecha')
        )

    def get_total_ventas_por_rango(self, fecha_inicio, fecha_fin):
        return self.model_class.objects.filter(
            fecha__range=(fecha_inicio, fecha_fin), estado='completada'
        ).aggregate(total_general=Sum('total'))['total_general'] or 0