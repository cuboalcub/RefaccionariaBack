from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from producto.services.movimiento_service import MovimientoService

class MovimientoListCreateView(APIView):
    """
    Controlador para listar movimientos o crear uno nuevo.
    """

    def get(self, request):
        movimientos = MovimientoService.get_all_movimientos()
        return Response(movimientos, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            movimiento_data = request.data
            movimiento = MovimientoService.create_movimiento(movimiento_data)
            return Response(movimiento, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class MovimientoDetailView(APIView):
    """
    Controlador para obtener, actualizar o eliminar un movimiento por ID.
    """

    def get(self, request, movimiento_id):
        movimiento = MovimientoService.get_movimiento_by_id(movimiento_id)
        if movimiento:
            return Response(movimiento, status=status.HTTP_200_OK)
        return Response({"error": "Movimiento no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, movimiento_id):
        try:
            updated_movimiento = MovimientoService.update_movimiento(movimiento_id, request.data)
            return Response(updated_movimiento, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, movimiento_id):
        deleted = MovimientoService.delete_movimiento(movimiento_id)
        if deleted:
            return Response({"message": "Movimiento eliminado"}, status=status.HTTP_200_OK)
        return Response({"error": "Movimiento no encontrado"}, status=status.HTTP_404_NOT_FOUND)
