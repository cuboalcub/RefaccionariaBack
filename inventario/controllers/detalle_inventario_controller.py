from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from repository.base_controller import BaseListController, BaseDetailController

from inventario.services.detalle_inventario_service import DetalleInventarioService


class DetalleInventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(DetalleInventarioService)


class DetalleInventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(DetalleInventarioService)


class DetalleInventarioBulkCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            service = DetalleInventarioService()
            # Soporta lista plana o dict con items/detalles
            data = request.data
            resultados = service.bulk_create(data)
            return Response(resultados, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
