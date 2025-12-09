from producto.models import Tipo    
from producto.repositories.tipo_repository import TipoRepository
from usuario.repositories.usuario_repositorie import UserRepository     
from repository.base_service import BaseService

class TipoService(BaseService):
    def __init__(self):
        super().__init__(model=Tipo, repository=TipoRepository())
    
    # Puedes sobrescribir métodos si necesitas lógica específica
    def _to_dict(self, instance):
        """Ejemplo: Personalizar cómo se serializa Tipo"""
        return {
            "id": instance.id,
            "nombre": instance.nombre
        }