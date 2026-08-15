# repositories/base_repository.py
from typing import Any
from typing import List, Optional, Type, Dict
from django.db import models
from interfaces.repository import IRepository
from django.core.exceptions import ObjectDoesNotExist


class BaseRepository(IRepository[models.Model]):
    """Implementación base para repositorios Django"""     
    
    def __init__(self, model_class: Type[models.Model]):
        self.model_class = model_class

    def get_by_id(self, id: int) -> Optional[models.Model]:
        try:
            return self.model_class.objects.get(id=id)
        except ObjectDoesNotExist:
            return None

    def get_all(self) -> List[models.Model]:
        return list(self.model_class.objects.all())

    def create(self, data: Dict[str, Any]) -> models.Model:
        return self.model_class.objects.create(**data)

    def update(self, entity: models.Model, data: Dict[str, Any]):
        for key, value in data.items():
            setattr(entity, key, value)
        entity.save()
        return entity

    def delete(self, entity: models.Model) -> bool:
        if not self.get_by_id(entity.pk):
            return False
        entity.delete()
        return True

    def filter(self,    data: Dict[str, Any]) -> List[models.Model]:
        return list(self.model_class.objects.filter(**data))