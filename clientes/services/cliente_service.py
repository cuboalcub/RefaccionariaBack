from repository.base_service import BaseService
from clientes.models import Cliente
from clientes.repositories.cliente_repository import ClienteRepository
from sucursales.models import Sucursal


class ClienteService(BaseService):
    def __init__(self):
        super().__init__(model=Cliente, repository=ClienteRepository())

    def get_all(self, sucursal_id=None):
        if sucursal_id is None:
            return super().get_all()
        return self.get_by_filters({"id_sucursal_id": sucursal_id})

    def _validar(self, data):
        if "id_sucursal" not in data or data["id_sucursal"] is None:
            raise ValueError("Faltan campos obligatorios: id_sucursal")
        if not Sucursal.objects.filter(id=data["id_sucursal"]).exists():
            raise ValueError("La sucursal indicada no existe")

    @staticmethod
    def _validar_longitudes(data):
        for field in Cliente._meta.fields:
            maximo = getattr(field, "max_length", None)
            valor = data.get(field.name)
            if maximo and isinstance(valor, str) and len(valor) > maximo:
                raise ValueError(
                    f"{field.name} no puede exceder {maximo} caracteres"
                )

    def create(self, data):
        self._validar(data)
        self._validar_longitudes(data)
        data["id_sucursal"] = Sucursal.objects.get(id=data["id_sucursal"])
        return super().create(data)

    def update(self, id, data):
        self._validar_longitudes(data)
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
            "nombre": instance.nombre,
            "apellido_paterno": instance.apellido_paterno,
            "apellido_materno": instance.apellido_materno,
            "telefono": instance.telefono,
            "correo": instance.correo,
            "direccion": instance.direccion,
            "rfc": instance.rfc,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
        }
