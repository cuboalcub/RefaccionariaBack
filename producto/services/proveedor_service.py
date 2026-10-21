from producto.models import Proveedor
from repository.base_service import BaseService
from producto.repositories.proveedor_repository import ProveedorRepository


class ProveedorService(BaseService):
    def __init__(self):
        super().__init__(model=Proveedor, repository=ProveedorRepository())
    
    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "nombre": instance.nombre,
            "direccion": instance.direccion,
            "telefono": instance.telefono,
            "correo": instance.correo
        }