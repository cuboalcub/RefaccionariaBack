from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

from repository.permissions import exigir_permiso
from usuario.services.usuario_service import UserService


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_service = UserService()

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = self.user_service.login(username, password)
        if user:
            return Response(user, status=status.HTTP_200_OK)
        return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)


class UserListCreateView(APIView):
    # Registro cerrado: alta solo por encargado (su sucursal) o staff.
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_service = UserService()

    def get(self, request):
        exigir_permiso(request.user, "usuarios.gestionar")
        users = self.user_service.get_all_users(actor=request.user)
        return Response(users, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            exigir_permiso(request.user, "usuarios.gestionar")
            user_data = dict(request.data)
            user = self.user_service.create_user(user_data, actor=request.user)
            return Response(user, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_service = UserService()

    def get(self, request, user_id):
        exigir_permiso(request.user, "usuarios.gestionar")
        user = self.user_service.get_user_by_id(user_id, actor=request.user)
        if user:
            return Response(user, status=status.HTTP_200_OK)
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, user_id):
        try:
            exigir_permiso(request.user, "usuarios.gestionar")
            updated_user = self.user_service.update_user(user_id, request.data, actor=request.user)
            if updated_user:
                return Response(updated_user, status=status.HTTP_200_OK)
            return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        if not IsAdminUser().has_permission(request, self):
            return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
        deleted = self.user_service.delete_user(user_id)
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
