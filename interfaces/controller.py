from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any
from rest_framework.response import Response
from django.db import models

T = TypeVar('T', bound=models.Model)

class ListCreateControllerInterface(Generic[T], ABC):
    @abstractmethod
    def get(self, request) -> Response:
        pass

    @abstractmethod
    def post(self, request) -> Response:
        pass


class DetailControllerInterface(Generic[T], ABC):
    @abstractmethod
    def get(self, request, pk: int) -> Response:
        pass

    @abstractmethod
    def put(self, request, pk: int) -> Response:
        pass

    @abstractmethod
    def delete(self, request, pk: int) -> Response:
        pass    