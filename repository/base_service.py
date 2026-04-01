from typing import List, Optional, Type, Dict, Any
from django.db import models
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from interfaces.service import IService


class BaseService(IService):
    def __init__(self, model=None, repository=None):
        if not model or not issubclass(model, models.Model):
            raise ValueError("Model must be a subclass of Django's models.Model")
        self.model = model
        self.repository = repository
        self.required_fields = self._get_required_fields()

    def _get_required_fields(self) -> List[str]:
        """Obtiene los campos obligatorios del modelo"""
        required_fields = []
        for field in self.model._meta.fields:
            if not field.blank and not field.null and field.name != 'id':
                required_fields.append(field.name)
        return required_fields

    def _validate_required_fields(self, data: Dict[str, Any]) -> None:
        """Valida que los campos obligatorios estén presentes"""
        for field in self.required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"Faltan campos obligatorios: {field}")

    def _to_dict(self, instance: models.Model) -> Dict[str, Any]:
        """Convierte una instancia del modelo a diccionario"""
        if not instance:
            return {}
        
        result = {}
        for field in instance._meta.fields:
            value = getattr(instance, field.name)
            result[field.name] = value
        return result

    def create(self, data):
        """Crea una nueva instancia del modelo"""
        try:
            self._validate_required_fields(data)
            instance = self.repository.create(data)
            return self._to_dict(instance)
            
        except ValidationError as e:
            raise ValueError(f"Error de validación: {e}")
        except Exception as e:
            raise ValueError(f"Error al crear: {str(e)}")

    def get_all(self) -> List[Dict[str, Any]]:
        """Devuelve todas las instancias del modelo"""
        try:
            instances = self.repository.get_all()
            
            return [self._to_dict(instance) for instance in instances]
            
        except Exception as e:
            raise ValueError(f"Error al obtener todos: {str(e)}")

    def get_by_id(self, entity_id: int) -> Dict[str, Any]:
        """Devuelve una instancia por su ID"""
        try:
            instance = self.repository.get_by_id(entity_id)
            
            if not instance:
                raise ObjectDoesNotExist(f"{self.model.__name__} con id {entity_id} no encontrado")
            
            return self._to_dict(instance)
            
        except ObjectDoesNotExist:
            raise ValueError(f"{self.model.__name__} con id {entity_id} no encontrado")
        except Exception as e:
            raise ValueError(f"Error al obtener por id: {str(e)}")

    def update(self, entity_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza una instancia existente"""
        try:
            instance = self.repository.get_by_id(entity_id)
            
            if not instance:
                raise ObjectDoesNotExist(f"{self.model.__name__} con id {entity_id} no encontrado")
            
            # Validar campos únicos si es necesario
            for key, value in data.items():
                setattr(instance, key, value)
            
            instance.save()
            return self._to_dict(instance)
            
        except ObjectDoesNotExist:
            raise ValueError(f"{self.model.__name__} con id {entity_id} no encontrado")
        except ValidationError as e:
            raise ValueError(f"Error de validación: {e}")
        except Exception as e:
            raise ValueError(f"Error al actualizar: {str(e)}")

    def delete(self, entity_id: int, user: Optional[Any] = None) -> Dict[str, str]:
        """Elimina una instancia por su ID"""
        try:
            if self.repository:
                instance = self.repository.get_by_id(entity_id)
            else:
                instance = self.model.objects.get(id=entity_id)
            
            if not instance:
                raise ObjectDoesNotExist(f"{self.model.__name__} con id {entity_id} no encontrado")
            
            # Opcional: registro de quién eliminó (si se proporciona user)
            if user:
                # Aquí podrías agregar lógica de auditoría
                pass
            
            instance.delete()
            return {"message": f"{self.model.__name__} eliminado exitosamente"}
            
        except ObjectDoesNotExist:
            raise ValueError(f"{self.model.__name__} con id {entity_id} no encontrado")
        except Exception as e:
            raise ValueError(f"Error al eliminar: {str(e)}")

    # Métodos adicionales útiles

    def get_by_filters(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Devuelve instancias que coinciden con los filtros"""
        try:
            if self.repository:
                instances = self.repository.get_by_filters(filters)
            else:
                instances = self.model.objects.filter(**filters)
            
            return [self._to_dict(instance) for instance in instances]
            
        except Exception as e:
            raise ValueError(f"Error al filtrar: {str(e)}")

    def exists(self, entity_id: int) -> bool:
        """Verifica si una instancia existe"""
        try:
            if self.repository:
                return self.repository.exists(entity_id)
            return self.model.objects.filter(id=entity_id).exists()
        except Exception as e:
            raise ValueError(f"Error al verificar existencia: {str(e)}")

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Cuenta las instancias que coinciden con los filtros"""
        try:
            if self.repository:
                return self.repository.count(filters)
            if filters:
                return self.model.objects.filter(**filters).count()
            return self.model.objects.count()
        except Exception as e:
            raise ValueError(f"Error al contar: {str(e)}")