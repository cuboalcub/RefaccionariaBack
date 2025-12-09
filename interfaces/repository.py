# interfaces/repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
from django.db import models

T = TypeVar('T', bound=models.Model)

class IRepository(Generic[T], ABC):
    """Interfaz base para repositorios"""
    
    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        pass
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> T:
        pass
    
    @abstractmethod
    def update(self, entity: T, data: Dict[str, Any]) -> T | None:
        pass
    
    @abstractmethod
    def delete(self, entity: T) -> bool:
        pass
    
    @abstractmethod
    def filter(self, data: Dict[str, Any]) -> List[T]:
        pass

