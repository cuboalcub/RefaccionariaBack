from producto.repositories.movimiento_repository import MovimientoRepository
from producto.models import Movimiento
from repository.base_service import BaseService

class MovimientoService(BaseService):
    def __init__(self):
        super().__init__(model=Movimiento, repository=MovimientoRepository())

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "tipo": instance.tipo,
            "cantidad": instance.cantidad,
            "fecha": instance.fecha,
            "razon": instance.razon,
            "observacion": instance.observacion
        }
