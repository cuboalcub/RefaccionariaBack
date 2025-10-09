from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from producto.services.proveedor_service import ProveedorService

class ProveedorDetailView(APIView):
    """
    Controlador para obtener, actualizar o eliminar un proveedor por ID.
    """

    def get(self, request, proveedor_id):
        proveedor = ProveedorService.get_proveedor_by_id(proveedor_id)
        if proveedor:
            return Response(proveedor, status=status.HTTP_200_OK)
        return Response({"error": "Proveedor no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, proveedor_id):
        try:
            updated_proveedor = ProveedorService.update_proveedor(proveedor_id, request.data)
            return Response(updated_proveedor, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, proveedor_id):
        deleted = ProveedorService.delete_proveedor(proveedor_id)
        if deleted:
            return Response({"message": "Proveedor eliminado"}, status=status.HTTP_200_OK)
        return Response({"error": "Proveedor no encontrado"}, status=status.HTTP_404_NOT_FOUND)

class ProveedorListCreateView(APIView):
    """
    Controlador para listar proveedores o crear uno nuevo.
    """

    def get(self, request):
        proveedores = ProveedorService.get_all_proveedores()
        return Response(proveedores, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            proveedor_data = request.data
            proveedor = ProveedorService.create_proveedor(proveedor_data)
            return Response(proveedor, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
