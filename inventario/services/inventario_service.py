from inventario.models import Inventario
from inventario.repositories.inventario_repository import InventarioRepository
from repository.base_service import BaseService
from sucursales.models import Sucursal


class InventarioService(BaseService):
    def __init__(self):
        super().__init__(model=Inventario, repository=InventarioRepository())

    def _validar(self, data):
        if "id_sucursal" not in data or data["id_sucursal"] is None:
            raise ValueError("Faltan campos obligatorios: id_sucursal")
        if not Sucursal.objects.filter(id=data["id_sucursal"]).exists():
            raise ValueError("La sucursal indicada no existe")

    def create(self, data):
        self._validar(data)
        data["id_sucursal"] = Sucursal.objects.get(id=data["id_sucursal"])
        return super().create(data)

    def update(self, id, data):
        if "id_sucursal" in data and data["id_sucursal"] is not None:
            if not Sucursal.objects.filter(id=data["id_sucursal"]).exists():
                raise ValueError("La sucursal indicada no existe")
            data["id_sucursal"] = Sucursal.objects.get(id=data["id_sucursal"])
        return super().update(id, data)

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "id_sucursal": instance.id_sucursal_id,
            "descripcion": instance.descripcion,
        }
