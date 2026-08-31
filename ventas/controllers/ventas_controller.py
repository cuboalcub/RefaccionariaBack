from rest_framework import status
from rest_framework.response import Response

from ventas.services.ventas_services import VentaService
from repository.base_controller import BaseListController, BaseDetailController


class VentasListController(BaseListController):
    def __init__(self):
        super().__init__(VentaService)

    def post(self, request) -> Response:
        try:
            # ignora id_usuario del payload, se toma del JWT
            data = dict(request.data)
            data.pop("id_usuario", None)
            item = self.service.create(data, user=request.user)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VentasDetailController(BaseDetailController):
    def __init__(self):
        super().__init__(VentaService)


