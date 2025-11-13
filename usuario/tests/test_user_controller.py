import pytest
from django.test import RequestFactory
from rest_framework import status
from unittest.mock import patch
from usuario.controllers.usuario_controller import (
    UserLoginView,
    UserListCreateView,
    UserDetailView,
)


class TestUserController:
    
    @pytest.fixture
    def factory(self):
        return RequestFactory()

    # ---------------- LOGIN ----------------

    @pytest.mark.django_db
    @patch("usuario.services.usuario_services.UserService.login")
    def test_login_success(self, mock_login, factory):
        """Prueba que login con credenciales válidas devuelve 200"""
        mock_login.return_value = {"id": 1, "username": "testuser"}

        request = factory.post("/login/", {"username": "testuser", "password": "123"})
        response = UserLoginView.as_view()(request)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"

 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.login")
 #   def test_login_invalid_credentials(self, mock_login, factory):
 #       """Prueba que login con credenciales inválidas devuelve 401"""
 #       mock_login.return_value = None
#
 #       request = factory.post("/login/", {"username": "baduser", "password": "wrong"})
 #       response = UserLoginView.as_view()(request)
#
 #       assert response.status_code == status.HTTP_401_UNAUTHORIZED
 #       assert "error" in response.data
#
 #   # ---------------- LISTAR / CREAR ----------------
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.get_all_users")
 #   def test_get_users_success(self, mock_get_all, factory):
 #       """Prueba que GET devuelve la lista de usuarios"""
 #       mock_get_all.return_value = [{"id": 1, "username": "user1"}]
#
 #       request = factory.get("/usuarios/")
 #       response = UserListCreateView.as_view()(request)
#
 #       assert response.status_code == status.HTTP_200_OK
 #       assert len(response.data) == 1
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.create_user")
 #   def test_create_user_success(self, mock_create_user, factory):
 #       """Prueba que POST crea un usuario y devuelve 201"""
 #       mock_create_user.return_value = {"id": 1, "username": "nuevo"}
#
 #       request = factory.post("/usuarios/", {"username": "nuevo", "password": "123"})
 #       response = UserListCreateView.as_view()(request)
#
 #       assert response.status_code == status.HTTP_201_CREATED
 #       assert response.data["username"] == "nuevo"
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.create_user")
 #   def test_create_user_bad_request(self, mock_create_user, factory):
 #       """Prueba que POST devuelve 400 si ocurre un ValueError"""
 #       mock_create_user.side_effect = ValueError("Datos inválidos")
#
 #       request = factory.post("/usuarios/", {"username": ""})
 #       response = UserListCreateView.as_view()(request)
#
 #       assert response.status_code == status.HTTP_400_BAD_REQUEST
 #       assert "error" in response.data
#
 #   # ---------------- DETALLE ----------------
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.get_user_by_id")
 #   def test_get_user_detail_success(self, mock_get_user, factory):
 #       """Prueba que GET por ID devuelve usuario correcto"""
 #       mock_get_user.return_value = {"id": 1, "username": "testuser"}
#
 #       request = factory.get("/usuarios/1/")
 #       response = UserDetailView.as_view()(request, user_id=1)
#
 #       assert response.status_code == status.HTTP_200_OK
 #       assert response.data["username"] == "testuser"
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.get_user_by_id")
 #   def test_get_user_detail_not_found(self, mock_get_user, factory):
 #       """Prueba que GET por ID inexistente devuelve 404"""
 #       mock_get_user.return_value = None
#
 #       request = factory.get("/usuarios/99/")
 #       response = UserDetailView.as_view()(request, user_id=99)
#
 #       assert response.status_code == status.HTTP_404_NOT_FOUND
 #       assert "error" in response.data
#
 #   # ---------------- UPDATE ----------------
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.update_user")
 #   def test_update_user_success(self, mock_update, factory):
 #       """Prueba que PUT actualiza usuario correctamente"""
 #       mock_update.return_value = {"id": 1, "username": "modificado"}
#
 #       request = factory.put("/usuarios/1/", {"username": "modificado"})
 #       response = UserDetailView.as_view()(request, user_id=1)
#
 #       assert response.status_code == status.HTTP_200_OK
 #       assert response.data["username"] == "modificado"
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.update_user")
 #   def test_update_user_bad_request(self, mock_update, factory):
 #       """Prueba que PUT devuelve 400 si ocurre un ValueError"""
 #       mock_update.side_effect = ValueError("Error al actualizar")
#
 #       request = factory.put("/usuarios/1/", {"username": ""})
 #       response = UserDetailView.as_view()(request, user_id=1)
#
 #       assert response.status_code == status.HTTP_400_BAD_REQUEST
 #       assert "error" in response.data
#
 #   # ---------------- DELETE ----------------
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.delete_user")
 #   def test_delete_user_success(self, mock_delete, factory):
 #       """Prueba que DELETE elimina usuario correctamente"""
 #       mock_delete.return_value = True
#
 #       request = factory.delete("/usuarios/1/")
 #       response = UserDetailView.as_view()(request, user_id=1)
#
 #       assert response.status_code == status.HTTP_204_NO_CONTENT
#
 #   @pytest.mark.django_db
 #   @patch("usuario.services.usuario_services.UserService.delete_user")
 #   def test_delete_user_not_found(self, mock_delete, factory):
 #       """Prueba que DELETE de usuario inexistente devuelve 404"""
 #       mock_delete.return_value = False
#
 #       request = factory.delete("/usuarios/99/")
 #       response = UserDetailView.as_view()(request, user_id=99)
#
 #       assert response.status_code == status.HTTP_404_NOT_FOUND
 #       assert "error" in response.data