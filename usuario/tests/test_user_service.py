from django.contrib.auth.models import User
from django.test import TestCase
from unittest.mock import patch, MagicMock
from usuario.services.usuario_service import UserService
from usuario.models import Perfil, SesionActiva
from sucursales.models import Sucursal


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

    def test_login_success(self):
        """Test para que el login funcione correctamente"""
        user = User.objects.create_user(username="miguel", password="eldenring")

        result = self.service.login("miguel", "eldenring")
        self.assertIsNotNone(result)
        self.assertIn("refresh", result)
        self.assertIn("access", result)
        self.assertEqual(result["user"]["id"], user.id)
        self.assertTrue(
            SesionActiva.objects.filter(
                usuario=user, session_jti__isnull=False
            ).exists()
        )

    @patch("usuario.services.usuario_service.UserRepository.get_by_username")
    def test_login_wrong_password_returns_none(self, mock_get_by_username):
        """Testea que si la contraseña es incorrecta el login devuelve none"""
        user_mock = MagicMock()
        user_mock.check_password.return_value = False
        mock_get_by_username.return_value = user_mock

        result = self.service.login("miguel", "wrongpass")
        self.assertIsNone(result)

    def test_create_user_success(self):
        """Testea que se cree un usuario con su perfil de sucursal"""
        sucursal = Sucursal.objects.create(ubicacion="Centro")

        result = self.service.create_user({
            "username": "miguel",
            "password": "eldenring",
            "id_sucursal": sucursal.id,
        })

        self.assertEqual(result["username"], "miguel")
        self.assertEqual(result["id_sucursal"], sucursal.id)
        self.assertEqual(result["rol"], "cajero")
        self.assertTrue(Perfil.objects.filter(usuario__username="miguel").exists())

    def test_create_user_staff_hereda_su_sucursal(self):
        sucursal = Sucursal.objects.create(ubicacion="Centro")
        actor = User.objects.create_user(username="staff", password="x", is_staff=True)
        Perfil.objects.create(usuario=actor, id_sucursal=sucursal, rol="encargado")

        result = self.service.create_user(
            {"username": "nuevo", "password": "x"}, actor=actor
        )

        perfil = Perfil.objects.get(usuario__username="nuevo")
        self.assertEqual(perfil.id_sucursal_id, sucursal.id)
        self.assertEqual(perfil.rol, "cajero")
        self.assertEqual(result["id_sucursal"], sucursal.id)

    def test_create_user_staff_sin_sucursal_raises(self):
        actor = User.objects.create_user(username="staff2", password="x", is_staff=True)
        with self.assertRaises(ValueError):
            self.service.create_user({"username": "nuevo2", "password": "x"}, actor=actor)

    def test_update_user_staff_asigna_sucursal_y_rol(self):
        sucursal = Sucursal.objects.create(ubicacion="Centro")
        actor = User.objects.create_user(username="staff3", password="x", is_staff=True)
        target = User.objects.create_user(username="target", password="x")

        result = self.service.update_user(
            target.id, {"id_sucursal": sucursal.id, "rol": "encargado"}, actor=actor
        )

        perfil = Perfil.objects.get(usuario=target)
        self.assertEqual((perfil.id_sucursal_id, perfil.rol), (sucursal.id, "encargado"))
        self.assertEqual(result["id_sucursal"], sucursal.id)
        self.assertEqual(result["rol"], "encargado")

    def test_update_user_no_staff_ignora_asignacion(self):
        sucursal = Sucursal.objects.create(ubicacion="Centro")
        otra = Sucursal.objects.create(ubicacion="Norte")
        actor = User.objects.create_user(username="enc", password="x")
        Perfil.objects.create(usuario=actor, id_sucursal=sucursal, rol="encargado")
        target = User.objects.create_user(username="caj", password="x")
        Perfil.objects.create(usuario=target, id_sucursal=sucursal, rol="cajero")

        self.service.update_user(
            target.id, {"id_sucursal": otra.id, "rol": "admin"}, actor=actor
        )

        perfil = Perfil.objects.get(usuario=target)
        self.assertEqual((perfil.id_sucursal_id, perfil.rol), (sucursal.id, "cajero"))

    def test_update_user_asignacion_vacia_no_cambia(self):
        target = User.objects.create_user(username="target2", password="x")

        result = self.service.update_user(target.id, {"id_sucursal": "", "rol": ""})

        self.assertFalse(Perfil.objects.filter(usuario=target).exists())
        self.assertIsNone(result["id_sucursal"])
        self.assertEqual(result["rol"], "cajero")

    def test_update_user_solo_rol_crea_perfil_sin_sucursal(self):
        target = User.objects.create_user(username="target3", password="x")

        self.service.update_user(target.id, {"rol": "encargado"})

        perfil = Perfil.objects.get(usuario=target)
        self.assertIsNone(perfil.id_sucursal_id)
        self.assertEqual(perfil.rol, "encargado")

    def test_update_user_rol_invalido_raises(self):
        target = User.objects.create_user(username="target4", password="x")
        with self.assertRaises(ValueError):
            self.service.update_user(target.id, {"rol": "jefe"})

    def test_update_user_sucursal_invalida_raises(self):
        target = User.objects.create_user(username="target5", password="x")
        with self.assertRaises(ValueError):
            self.service.update_user(target.id, {"id_sucursal": 99999})

    @patch("usuario.services.usuario_service.UserRepository.get_by_username")
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

    @patch("usuario.services.usuario_service.UserRepository.get_by_username")
    def test_create_user_crea_perfil_con_sucursal(self, mock_get_by_username):
        """Testea que al registrarse con id_sucursal se cree el Perfil"""
        mock_get_by_username.return_value = None
        sucursal = Sucursal.objects.create(ubicacion="Centro")

        result = self.service.create_user({
            "username": "miguel",
            "password": "eldenring",
            "id_sucursal": sucursal.id,
        })

        perfil = Perfil.objects.get(usuario__username="miguel")
        self.assertEqual(perfil.id_sucursal_id, sucursal.id)
        self.assertEqual(result["username"], "miguel")

    @patch("usuario.services.usuario_service.UserRepository.get_by_username")
    def test_create_user_sucursal_inexistente_elimina_usuario(self, mock_get_by_username):
        """Testea que si la sucursal no existe se revierta la creación"""
        mock_get_by_username.return_value = None

        with self.assertRaises(ValueError) as cm:
            self.service.create_user({
                "username": "miguel",
                "password": "eldenring",
                "id_sucursal": 9999,
            })
        self.assertEqual(str(cm.exception), "La sucursal indicada no existe")

    @patch("usuario.services.usuario_service.UserRepository.get_all")
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

    @patch("usuario.services.usuario_service.UserRepository.get_by_id")
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

    @patch("usuario.services.usuario_service.UserRepository.get_by_id")
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

    def test_login_inactive_returns_none(self):
        User.objects.create_user(
            username="inactivo", password="x", is_active=False
        )
        self.assertIsNone(self.service.login("inactivo", "x"))

    def _sucursal(self):
        return Sucursal.objects.create(ubicacion="Centro")

    def test_create_user_email_duplicado(self):
        suc = self._sucursal()
        User.objects.create_user(
            username="existente", email="dup@mail.com", password="x"
        )
        with self.assertRaises(ValueError) as cm:
            self.service.create_user(
                {
                    "username": "nuevo",
                    "password": "x",
                    "email": "dup@mail.com",
                    "id_sucursal": suc.id,
                }
            )
        self.assertEqual(str(cm.exception), "El correo ya está registrado")

    def test_create_user_email_duplicado_case_insensitive(self):
        suc = self._sucursal()
        User.objects.create_user(
            username="existente2", email="dup@mail.com", password="x"
        )
        with self.assertRaises(ValueError):
            self.service.create_user(
                {
                    "username": "nuevo2",
                    "password": "x",
                    "email": "DUP@Mail.com",
                    "id_sucursal": suc.id,
                }
            )

    def test_create_user_email_vacio_repetido_se_permite(self):
        suc = self._sucursal()
        self.service.create_user(
            {"username": "sincorreo1", "password": "x", "id_sucursal": suc.id}
        )
        self.service.create_user(
            {"username": "sincorreo2", "password": "x", "id_sucursal": suc.id}
        )
        self.assertEqual(User.objects.filter(email="").count(), 2)

    def test_create_user_ignora_campos_privilegiados(self):
        suc = self._sucursal()
        self.service.create_user(
            {
                "username": "casiadmin",
                "password": "x",
                "id_sucursal": suc.id,
                "is_staff": True,
                "is_superuser": True,
                "is_active": False,
            }
        )
        user = User.objects.get(username="casiadmin")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_update_user_email_duplicado(self):
        User.objects.create_user(username="a", email="a@mail.com", password="x")
        target = User.objects.create_user(
            username="b", email="b@mail.com", password="x"
        )
        with self.assertRaises(ValueError) as cm:
            self.service.update_user(target.id, {"email": "a@mail.com"})
        self.assertEqual(str(cm.exception), "El correo ya está registrado")

    def test_update_user_mismo_email_se_permite(self):
        target = User.objects.create_user(
            username="c", email="c@mail.com", password="x"
        )
        out = self.service.update_user(target.id, {"email": "c@mail.com"})
        self.assertEqual(out["email"], "c@mail.com")

    def test_update_user_email_vacio_se_permite(self):
        target = User.objects.create_user(
            username="d", email="d@mail.com", password="x"
        )
        out = self.service.update_user(target.id, {"email": "  "})
        self.assertEqual(out["email"], "")
