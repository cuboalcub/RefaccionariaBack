from django.db.models import Case, ExpressionWrapper, F, IntegerField, Sum, Value, When

from repository.base_repository import BaseRepository
from inventario.models import DetalleInventario, MovimientoInventario


class DetalleInventarioRepository(BaseRepository):
    def __init__(self):
        super().__init__(DetalleInventario)

    def get_stock(self, producto_id, inventario_id=None):
        qs = self.model_class.objects.filter(id_producto_id=producto_id)
        if inventario_id is not None:
            qs = qs.filter(id_inventario_id=inventario_id)

        qs = qs.annotate(
            signo=Case(
                When(id_movimiento__tipo=MovimientoInventario.TipoMovimiento.ENTRADA, then=Value(1)),
                default=Value(-1),
                output_field=IntegerField(),
            )
        )
        expresion = ExpressionWrapper(F("signo") * F("cantidad"), output_field=IntegerField())
        return qs.aggregate(stock=Sum(expresion))["stock"] or 0

    def get_by_detalle_venta(self, detalle_venta_id):
        return self.model_class.objects.filter(id_detalle_venta_id=detalle_venta_id).first()

    def get_stock_map_por_sucursal(self, sucursal_id):
        """Devuelve dict {producto_id: stock} para productos con stock >0 en la sucursal."""
        qs = self.model_class.objects.filter(id_inventario__id_sucursal_id=sucursal_id)
        qs = qs.annotate(
            signo=Case(
                When(id_movimiento__tipo=MovimientoInventario.TipoMovimiento.ENTRADA, then=Value(1)),
                default=Value(-1),
                output_field=IntegerField(),
            )
        )
        expresion = ExpressionWrapper(F("signo") * F("cantidad"), output_field=IntegerField())
        # Agrupa por producto y suma stock neto
        grouped = qs.values('id_producto_id').annotate(stock=Sum(expresion))
        # Solo productos con stock >0
        return {row['id_producto_id']: row['stock'] for row in grouped if (row['stock'] or 0) > 0}
