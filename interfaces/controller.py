"""Module defining the base controller interface for the application."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from django.db import models
from rest_framework.response import Response

T = TypeVar("T", bound=models.Model)


class ListCreateControllerInterface(Generic[T], ABC):
    """
    Interface for controllers that handle listing and creating items.
    """

    @abstractmethod
    def get(self, request) -> Response:
        """
        Retrieve a list of items.
        """

    @abstractmethod
    def post(self, request) -> Response:
        """
        Create a new item.
        """


class DetailControllerInterface(Generic[T], ABC):
    """
    Interface for controllers that handle retrieving, updating, and deleting a single item.
    """

    @abstractmethod
    def get(self, request, pk: int) -> Response:
        """
        Retrieve a single item by its primary key.
        """

    @abstractmethod
    def put(self, request, pk: int) -> Response:
        """
        Update an existing item by its primary key.
        """

    @abstractmethod
    def delete(self, request, pk: int) -> Response:
        """
        Delete an item by its primary key.
        """
