from inventario.models import MovimientoInventario
from inventario.repositories.movimiento_inventario_repository import MovimientoInventarioRepository
from repository.base_service import BaseService


class MovimientoInventarioService(BaseService):
    def __init__(self):
        super().__init__(model=MovimientoInventario, repository=MovimientoInventarioRepository())

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "tipo": instance.tipo,
            "cantidad": instance.cantidad,
            "fecha": instance.fecha.isoformat() if instance.fecha else None,
            "razon": instance.razon,
            "observaciones": instance.observaciones,
        }
