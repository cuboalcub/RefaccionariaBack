from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
from django.db import models

T = TypeVar('T', bound=models.Model)

class IRepository(Generic[T], ABC):
    """Interfaz base para repositorios"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """
        Retrieve an item by its primary key.
        """
    @abstractmethod
    def get_all(self) -> List[T]:
        """
        Retrieve a list of all items.
        """
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new item.
        """
    
    @abstractmethod
    def update(self, entity: T, data: Dict[str, Any]) -> T | None:
        """
        Update an existing item.
        """
    
    @abstractmethod
    def delete(self, entity: T) -> bool:
        """
        Delete an item.
        """
    
    @abstractmethod
    def filter(self, data: Dict[str, Any]) -> List[T]:
        """
        Filter items based on a dictionary of criteria.
        """

