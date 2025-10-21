
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from producto.services.producto_service import ProductoService

class ProductoDetailView(APIView):
    """
    Controlador para obtener, actualizar o eliminar un producto por ID.
    """

    def get(self, request, producto_id):
        producto = ProductoService.get_producto_by_id(producto_id)
        if producto:
            return Response(producto, status=status.HTTP_200_OK)
        return Response({"error": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, producto_id):
        try:
            updated_producto = ProductoService.update_producto(producto_id, request.data)
            return Response(updated_producto, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, producto_id):
        deleted = ProductoService.delete_producto(producto_id)
        if deleted:
            return Response({"message": "Producto eliminado"}, status=status.HTTP_200_OK)
        return Response({"error": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND)   

class ProductoListCreateView(APIView):
    """
    Controlador para listar productos o crear uno nuevo.
    """

    def get(self, request):
        productos = ProductoService.get_all_productos()
        return Response(productos, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            producto_data = request.data
            producto = ProductoService.create_producto(producto_data)
            return Response(producto, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)