from typing import List, Optional, Type
from interfaces.controller import ListCreateControllerInterface, DetailControllerInterface
from interfaces.service import IService 
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class BaseListController(APIView, ListCreateControllerInterface):
    def __init__(self, service: Type[IService], **kwargs):
        super().__init__(**kwargs)
        self.service = service()

    def get(self, request) -> Response:
        dates =  self.service.get_all()
        return Response(dates, status=status.HTTP_200_OK)

    def post(self, request) -> Response:
        try:
            self.service.create(request.data)
            return Response({"message": "Creado exitosamente"}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class BaseDetailController(APIView, DetailControllerInterface):
    def __init__(self, service: Type[IService], **kwargs):
        super().__init__(**kwargs)
        self.service = service()

    def get(self, request, pk: int) -> Response:
        try:
            date = self.service.get_by_id(pk)
            return Response(date, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"error": "No se encontro el registro"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk: int) -> Response:
        try:
            date = self.service.get_by_id(pk)
            if not date:
                return Response({"error": "No se encontro el registro"}, status=status.HTTP_404_NOT_FOUND)
            self.service.update(pk, request.data)
            return Response({"message": "Actualizado exitosamente"}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"error": "No se encontro el registro"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk: int) -> Response:
        try:
            date = self.service.get_by_id(pk)
            if not date:
                return Response({"error": "No se encontro el registro"}, status=status.HTTP_404_NOT_FOUND)
            self.service.delete(pk)
            return Response({"message": "Eliminado exitosamente"}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"error": "No se encontro el registro"}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        try:
            instance = self.service.repository.get_by_id(pk)

            if not instance:
                return Response({"error": "No encontrado"}, status=404)

            data = request.data
            result = self.service.update(instance, data)

            return Response(result, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)  
