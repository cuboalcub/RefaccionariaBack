from producto.models import Tipo
from producto.repositories.tipo_repository import TipoRepository
from repository.base_service import BaseService


class TipoService(BaseService):
    def __init__(self):
        super().__init__(model=Tipo, repository=TipoRepository())

    def _validar(self, data, entity_id=None):
        if "nombre" not in data:
            return
        nombre = str(data.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("nombre no puede estar vacío")
        qs = Tipo.objects.filter(nombre__iexact=nombre)
        if entity_id is not None:
            qs = qs.exclude(id=entity_id)
        if qs.exists():
            raise ValueError("Ya existe un tipo con ese nombre")
        data["nombre"] = nombre

    def create(self, data):
        data = dict(data)
        self._validar(data)
        return super().create(data)

    def update(self, id, data):
        data = dict(data)
        self._validar(data, entity_id=id)
        return super().update(id, data)

    # Puedes sobrescribir métodos si necesitas lógica específica
    def _to_dict(self, instance):
        """Ejemplo: Personalizar cómo se serializa Tipo"""
        return {"id": instance.id, "nombre": instance.nombre}
