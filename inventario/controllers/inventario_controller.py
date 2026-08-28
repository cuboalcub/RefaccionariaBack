from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from repository.base_controller import BaseListController, BaseDetailController

from inventario.services.inventario_service import InventarioService
from inventario.services.detalle_inventario_service import DetalleInventarioService


class InventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(InventarioService)


class InventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(InventarioService)


class InventarioPorSucursalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        perfil = getattr(request.user, "perfil", None)
        if not perfil or not perfil.id_sucursal_id:
            return Response(
                {"error": "El usuario no tiene una sucursal asignada"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = DetalleInventarioService().get_inventario_por_sucursal(perfil.id_sucursal_id)
        return Response(data, status=status.HTTP_200_OK)
