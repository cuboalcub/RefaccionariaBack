from ventas.models import MetodoPago
from repository.base_service import BaseService
from ventas.repositories.metodo_pago_repository import MetodoPagoRepository
class MetodoPagoService(BaseService):
    def __init__(self):
        super().__init__(model=MetodoPago, repository=MetodoPagoRepository())    
    
    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "tipo": instance.tipo,
            "descripcion": instance.descripcion
        }