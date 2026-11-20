from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from repository.base_service import BaseService
from sucursales.models import Sucursal
from sucursales.repositories.sucursal_repository import SucursalRepository


class SucursalService(BaseService):
    def __init__(self):
        super().__init__(model=Sucursal, repository=SucursalRepository())

    def _validar(self, data, entity_id=None):
        if "nombre_sucursal" in data or entity_id is None:
            nombre = str(data.get("nombre_sucursal") or "").strip()
            if not nombre:
                raise ValueError("nombre_sucursal es obligatorio")
            qs = Sucursal.objects.filter(nombre_sucursal__iexact=nombre)
            if entity_id is not None:
                qs = qs.exclude(id=entity_id)
            if qs.exists():
                raise ValueError("Ya existe una sucursal con ese nombre")
            data["nombre_sucursal"] = nombre

        if "correo_electronico" in data:
            correo = str(data.get("correo_electronico") or "").strip()
            if correo:
                try:
                    validate_email(correo)
                except ValidationError:
                    raise ValueError("correo_electronico inválido") from None
            data["correo_electronico"] = correo

    def create(self, data):
        data = dict(data)
        self._validar(data)
        return super().create(data)

    def update(self, id, data):
        data = dict(data)
        self._validar(data, entity_id=id)
        return super().update(id, data)

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "nombre_sucursal": instance.nombre_sucursal,
            "codigo_sucursal": instance.codigo_sucursal,
            "ubicacion": instance.ubicacion,
            "codigo_postal": instance.codigo_postal,
            "numero_telefono": instance.numero_telefono,
            "correo_electronico": instance.correo_electronico,
        }
