from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from producto.services.tipo_service import TipoService

class TipoListCreateView(APIView):
    """
    Controlador para listar tipos o crear uno nuevo.
    Requiere token de autenticación.
    """
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        tipos = TipoService.get_all_tipos()
        return Response(tipos, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            tipo_data = request.data
            tipo = TipoService.create_tipo(tipo_data)
            return Response(tipo, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TipoDetailView(APIView):
    """
    Controlador para obtener, actualizar o eliminar un tipo por ID.
    Requiere token de autenticación.
    """
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, tipo_id):
        tipo = TipoService.get_tipo_by_id(tipo_id)
        if tipo:
            return Response(tipo, status=status.HTTP_200_OK)
        return Response({"error": "Tipo no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, tipo_id):
        try:
            updated_tipo = TipoService.update_tipo(tipo_id, request.data)
            return Response(updated_tipo, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, tipo_id):
        deleted = TipoService.delete_tipo(tipo_id)
        if deleted:
            return Response({"message": "Tipo eliminado"}, status=status.HTTP_200_OK)
        return Response({"error": "Tipo no encontrado"}, status=status.HTTP_404_NOT_FOUND)