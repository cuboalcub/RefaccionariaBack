from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from usuario.services.perfil_service import PerfilService


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.perfil_service = PerfilService()

    def get(self, request):
        perfil = self.perfil_service.get_or_create(request.user)
        return Response(perfil, status=status.HTTP_200_OK)

    def put(self, request):
        try:
            perfil = self.perfil_service.update_by_usuario(request.user, request.data)
            return Response(perfil, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
