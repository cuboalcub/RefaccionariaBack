# users/controllers/user_controller.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from usuario.services.usuario_services import UserService


class UserLoginView(APIView):
    """
    Controlador para manejar el login de usuarios.
    """

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = UserService.login(username, password)
        if user:
            return Response(user, status=status.HTTP_200_OK)
        return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

class UserListCreateView(APIView):
    """
    Controlador para listar usuarios o crear uno nuevo.
    """

    def get(self, request):
        users = UserService.get_all_users()
        return Response(users, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            user_data = request.data
            user = UserService.create_user(user_data)
            return Response(user, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    """
    Controlador para obtener, actualizar o eliminar un usuario por ID.
    """

    def get(self, request, user_id):
        user = UserService.get_user_by_id(user_id)
        if user:
            return Response(user, status=status.HTTP_200_OK)
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, user_id):
        try:
            updated_user = UserService.update_user(user_id, request.data)
            return Response(updated_user, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        deleted = UserService.delete_user(user_id)
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
