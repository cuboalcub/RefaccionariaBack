from ventas.models import metodoPago
from repository.base_service import BaseService
from ventas.repositories.metodopago_repository import MetodoPagoRepository
class MetodoPagoService(BaseService):
    def __init__(self):
        super().__init__(model=metodoPago, repository=MetodoPagoRepository())    
    
    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "tipo": instance.tipo,
            "descripcion": instance.descripcion
        }