from rest_framework import status
from rest_framework.response import Response

from ventas.services.ventas_services import VentaService
from repository.base_controller import BaseListController, BaseDetailController


class VentasListController(BaseListController):
    def __init__(self):
        super().__init__(VentaService)

    def post(self, request) -> Response:
        try:
            # ignora id_usuario e id_inventario del payload: se toman del JWT/perfil
            # staff/superuser puede enviar id_inventario como override explícito
            data = dict(request.data)
            data.pop("id_usuario", None)
            is_staff = getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False)
            if not is_staff:
                data.pop("id_inventario", None)
            item = self.service.create(data, user=request.user)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VentasDetailController(BaseDetailController):
    def __init__(self):
        super().__init__(VentaService)


