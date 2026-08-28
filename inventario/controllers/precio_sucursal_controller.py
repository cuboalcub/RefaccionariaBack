from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inventario.services.precio_sucursal_service import PrecioSucursalService
from repository.base_controller import BaseDetailController, BaseListController
from repository.exceptions import NotFoundError


class PrecioSucursalListCreateView(BaseListController):
    def __init__(self):
        super().__init__(PrecioSucursalService)


class PrecioSucursalDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(PrecioSucursalService)


class PrecioActivoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        producto_id = request.query_params.get('id_producto') or request.query_params.get('producto_id')
        sucursal_id = request.query_params.get('id_sucursal') or request.query_params.get('sucursal_id')
        if not producto_id or not sucursal_id:
            return Response({"error": "Debe enviar id_producto y id_sucursal"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            producto_id = int(producto_id)
            sucursal_id = int(sucursal_id)
        except ValueError:
            return Response({"error": "id_producto y id_sucursal deben ser enteros"}, status=status.HTTP_400_BAD_REQUEST)
        service = PrecioSucursalService()
        data = service.get_precio_activo(producto_id, sucursal_id)
        if not data:
            return Response({"error": "Precio no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response(data, status=status.HTTP_200_OK)


class HistorialPrecioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        producto_id = request.query_params.get('id_producto') or request.query_params.get('producto_id')
        sucursal_id = request.query_params.get('id_sucursal') or request.query_params.get('sucursal_id')
        if not producto_id or not sucursal_id:
            return Response({"error": "Debe enviar id_producto y id_sucursal"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            producto_id = int(producto_id)
            sucursal_id = int(sucursal_id)
        except ValueError:
            return Response({"error": "id_producto y id_sucursal deben ser enteros"}, status=status.HTTP_400_BAD_REQUEST)
        service = PrecioSucursalService()
        data = service.get_historial(producto_id, sucursal_id)
        return Response(data, status=status.HTTP_200_OK)
