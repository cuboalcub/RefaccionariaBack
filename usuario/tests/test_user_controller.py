from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status
from unittest.mock import patch
from usuario.controllers.usuario_controller import (
    UserLoginView,
    UserListCreateView,
    UserDetailView,
)


class UserControllerTestCase(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    # ---------------- LOGIN ----------------

    @patch("usuario.services.usuario_services.UserService.login")
    def test_login_success(self, mock_login):

        """Prueba que login con credenciales válidas devuelve 200"""
        mock_login.return_value = {"id": 1, "username": "testuser"}

        request = self.factory.post("/login/", {"username": "testuser", "password": "123"})
        response = UserLoginView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")

    @patch("usuario.services.usuario_services.UserService.login")
    def test_login_invalid_credentials(self, mock_login):

        """Prueba que login con credenciales inválidas devuelve 401"""
        mock_login.return_value = None

        request = self.factory.post("/login/", {"username": "baduser", "password": "wrong"})
        response = UserLoginView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)

    # ---------------- LISTAR / CREAR ----------------

    @patch("usuario.services.usuario_services.UserService.get_all_users")
    def test_get_users_success(self, mock_get_all):

        """Prueba que GET devuelve la lista de usuarios"""

        mock_get_all.return_value = [{"id": 1, "username": "user1"}]

        request = self.factory.get("/usuarios/")
        response = UserListCreateView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch("usuario.services.usuario_services.UserService.create_user")
    def test_create_user_success(self, mock_create_user):

        """Prueba que POST crea un usuario y devuelve 201"""

        mock_create_user.return_value = {"id": 1, "username": "nuevo"}

        request = self.factory.post("/usuarios/", {"username": "nuevo", "password": "123"})
        response = UserListCreateView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "nuevo")

    @patch("usuario.services.usuario_services.UserService.create_user")
    def test_create_user_bad_request(self, mock_create_user):

        """Prueba que POST devuelve 400 si ocurre un ValueError"""

        mock_create_user.side_effect = ValueError("Datos inválidos")

        request = self.factory.post("/usuarios/", {"username": ""})
        response = UserListCreateView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    # ---------------- DETALLE ----------------

    @patch("usuario.services.usuario_services.UserService.get_user_by_id")
    def test_get_user_detail_success(self, mock_get_user):

        """Prueba que GET por ID devuelve usuario correcto"""

        mock_get_user.return_value = {"id": 1, "username": "testuser"}

        request = self.factory.get("/usuarios/1/")
        response = UserDetailView.as_view()(request, user_id=1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")

    @patch("usuario.services.usuario_services.UserService.get_user_by_id")
    def test_get_user_detail_not_found(self, mock_get_user):

        """Prueba que GET por ID inexistente devuelve 404"""

        mock_get_user.return_value = None

        request = self.factory.get("/usuarios/99/")
        response = UserDetailView.as_view()(request, user_id=99)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    # ---------------- UPDATE ----------------
    @patch("usuario.services.usuario_services.UserService.update_user")
    def test_update_user_success(self, mock_update):

        """Prueba que PUT actualiza usuario correctamente"""

        mock_update.return_value = {"id": 1, "username": "modificado"}

        request = self.factory.put("/usuarios/1/", {"username": "modificado"})
        response = UserDetailView.as_view()(request, user_id=1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "modificado")

    @patch("usuario.services.usuario_services.UserService.update_user")
    def test_update_user_bad_request(self, mock_update):

        """Prueba que PUT devuelve 400 si ocurre un ValueError"""

        mock_update.side_effect = ValueError("Error al actualizar")

        request = self.factory.put("/usuarios/1/", {"username": ""})
        response = UserDetailView.as_view()(request, user_id=1)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    # ---------------- DELETE ----------------
    @patch("usuario.services.usuario_services.UserService.delete_user")
    def test_delete_user_success(self, mock_delete):
        """Prueba que DELETE elimina usuario correctamente"""
        mock_delete.return_value = True

        request = self.factory.delete("/usuarios/1/")
        response = UserDetailView.as_view()(request, user_id=1)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch("usuario.services.usuario_services.UserService.delete_user")
    def test_delete_user_not_found(self, mock_delete):
        """Prueba que DELETE de usuario inexistente devuelve 404"""
        mock_delete.return_value = False

        request = self.factory.delete("/usuarios/99/")
        response = UserDetailView.as_view()(request, user_id=99)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)