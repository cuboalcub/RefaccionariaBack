from django.test import TestCase
from unittest.mock import patch, MagicMock
from usuario.services.usuario_services import UserService


class UserServiceTestCase(TestCase):

    def setUp(self):
        self.service = UserService()
        self.user_data = {
            "id": 1,
            "username": "miguel",
            "email": "miguel@gmail.com",
            "password": "eldenring",
            "is_active": True,
            "is_superuser": False,
            "is_staff": False
        }

    @patch("usuario.services.usuario_services.UserRepository.get_by_username")
    @patch("usuario.services.usuario_services.RefreshToken")
    def test_login_success(self, mock_refresh, mock_get_by_username):
        """Test para que el login funcione correctamente"""
        user_mock = MagicMock()
        user_mock.check_password.return_value = True
        user_mock.id = self.user_data["id"]
        user_mock.is_superuser = self.user_data["is_superuser"]
        user_mock.is_staff = self.user_data["is_staff"]

        mock_get_by_username.return_value = user_mock

        token_mock = MagicMock()
        token_mock.access_token = "access123"
        mock_refresh.for_user.return_value = token_mock

        result = self.service.login("miguel", "eldenring")
        self.assertIsNotNone(result)
        self.assertIn("refresh", result)
        self.assertIn("access", result)
        self.assertEqual(result["user"]["id"], 1)

    @patch("usuario.services.usuario_services.UserRepository.get_by_username")
    def test_login_wrong_password_returns_none(self, mock_get_by_username):
        """Testea que si la contraseña es incorrecta el login devuelve none"""
        user_mock = MagicMock()
        user_mock.check_password.return_value = False
        mock_get_by_username.return_value = user_mock

        result = self.service.login("miguel", "wrongpass")
        self.assertIsNone(result)

    @patch("usuario.services.usuario_services.UserRepository.get_by_username")
    @patch("usuario.services.usuario_services.UserRepository.create")
    def test_create_user_success(self, mock_create, mock_get_by_username):
        """Testea que se cree un usuario de forma correcta"""
        mock_get_by_username.return_value = None

        user_mock = MagicMock()
        user_mock.id = 1
        user_mock.username = "miguel"
        user_mock.email = "miguel@gmail.com"
        user_mock.is_active = True

        mock_create.return_value = user_mock

        result = self.service.create_user({"username": "miguel", "password": "eldenring"})
        self.assertEqual(result["username"], "miguel")
        self.assertEqual(result["id"], 1)

    @patch("usuario.services.usuario_services.UserRepository.get_by_username")
    def test_create_user_existing_username_raises(self, mock_get_by_username):
        """Testea que si el username ya existe create_user lanza ValueError"""
        user_mock = MagicMock()
        mock_get_by_username.return_value = user_mock

        with self.assertRaises(ValueError) as cm:
            self.service.create_user({"username": "miguel", "password": "eldenring"})
        self.assertEqual(str(cm.exception), "El nombre de usuario ya existe")

    def test_create_user_missing_fields_raises(self):
        """Testea que si faltan campos obligatorios create_user lanza ValueError"""
        with self.assertRaises(ValueError) as cm:
            self.service.create_user({"username": "miguel"})
        self.assertEqual(str(cm.exception), "Faltan campos obligatorios: username y password")

    @patch("usuario.services.usuario_services.UserRepository.get_all")
    def test_get_all_users(self, mock_get_all):
        """Testea que get_all_users devuelva una lista de usuarios en formato dict"""
        user_mock = MagicMock()
        user_mock.id = 1
        user_mock.username = "miguel"
        user_mock.email = "miguel@gmail.com"
        user_mock.is_active = True

        mock_get_all.return_value = [user_mock]

        result = self.service.get_all_users()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["username"], "miguel")

    @patch("usuario.services.usuario_services.UserRepository.get_by_id")
    def test_update_user_hashes_password(self, mock_get_by_id):
        """Testea que update_user use set_password y no guarde el texto plano"""
        user_mock = MagicMock()
        user_mock.id = 1
        user_mock.username = "miguel"
        user_mock.email = "miguel@gmail.com"
        user_mock.is_active = True
        mock_get_by_id.return_value = user_mock

        result = self.service.update_user(1, {"password": "nueva123"})

        user_mock.set_password.assert_called_once_with("nueva123")
        self.assertEqual(result["id"], 1)

    @patch("usuario.services.usuario_services.UserRepository.get_by_id")
    def test_update_user_ignores_privilege_fields(self, mock_get_by_id):
        """Testea que update_user ignore campos sensibles como is_superuser/is_staff"""
        user_mock = MagicMock()
        user_mock.id = 1
        user_mock.username = "miguel"
        user_mock.email = "miguel@gmail.com"
        user_mock.is_active = True
        user_mock.is_superuser = False
        user_mock.is_staff = False
        mock_get_by_id.return_value = user_mock

        self.service.update_user(1, {"is_superuser": True, "is_staff": True})

        self.assertEqual(user_mock.is_superuser, False)
        self.assertEqual(user_mock.is_staff, False)
        self.assertEqual(user_mock.set_password.call_count, 0)
