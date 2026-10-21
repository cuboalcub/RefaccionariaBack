"""Module defining the base service interface for the application."""

from abc import abstractmethod
import abc
from typing import Generic, TypeVar, List, Dict, Any
from django.db import models

T = TypeVar('T', bound=models.Model)


class IService(Generic[T],abc.ABC):
    """Interfaz base para servicios"""

    @abstractmethod
    def create(self, data) -> Dict[str, Any]:
        """
        Create a new item.
        """


    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Retrieve a list of all items.
        """

    @abstractmethod
    def get_by_id(self, entity_id) -> Dict[str, Any]:
        """
        Retrieve an item by its primary key.
        """



    @abstractmethod
    def delete(self, entity_id) -> Dict[str, str]:
        """
        Delete an item by its primary key.
        """

    @abstractmethod
    def update(self, entity_id, data) -> Dict[str, Any]:
        """
        Update an item by its primary key.
        """