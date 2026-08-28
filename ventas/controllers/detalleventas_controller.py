from rest_framework import status
from rest_framework.response import Response

from repository.base_controller import BaseDetailController, BaseListController
from repository.exceptions import NotFoundError
from ventas.services.detalleventa_service import DetalleVentaService


class DetalleVentaListCreate(BaseListController):
    def __init__(self):
        super().__init__(DetalleVentaService)

    def post(self, request) -> Response:
        try:
            # Pasar request.user para validación de sucursal
            item = self.service.create(request.data, user=request.user)
            return Response(item, status=status.HTTP_201_CREATED)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DetalleVentaDetail(BaseDetailController):
    def __init__(self):
        super().__init__(DetalleVentaService)

    def put(self, request, pk: int) -> Response:
        try:
            item = self.service.update(pk, request.data, user=request.user)
            return Response(item, status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)