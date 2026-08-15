from typing import List, Optional, Type
from interfaces.controller import ListCreateControllerInterface, DetailControllerInterface
from interfaces.service import IService 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

class BaseListController(APIView, ListCreateControllerInterface):
    permission_classes = [IsAuthenticated]

    def __init__(self, service: Type[IService], **kwargs):
        super().__init__(**kwargs)
        self.service = service()

    def get(self, request) -> Response:
        items = self.service.get_all()
        return Response(items, status=status.HTTP_200_OK)

    def post(self, request) -> Response:
        try:
            self.service.create(request.data)
            return Response({"message": "Creado exitosamente"}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class BaseDetailController(APIView, DetailControllerInterface):
    permission_classes = [IsAuthenticated]

    def __init__(self, service: Type[IService], **kwargs):
        super().__init__(**kwargs)
        self.service = service()

    def get(self, request, pk: int) -> Response:
        try:
            item = self.service.get_by_id(pk)
            return Response(item, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk: int) -> Response:
        try:
            self.service.update(pk, request.data)
            return Response({"message": "Actualizado exitosamente"}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk: int) -> Response:
        try:
            self.service.delete(pk)
            return Response({"message": "Eliminado exitosamente"}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
