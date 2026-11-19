from django.contrib.auth.models import User
from django.test import TestCase

from sucursales.models import Sucursal
from usuario.services.perfil_service import PerfilService


class PerfilServiceTestCase(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(username="admin", password="pass123")
        self.sucursal = Sucursal.objects.create(ubicacion="Norte")
        self.service = PerfilService()

    def test_get_or_create_crea_perfil(self):
        perfil = self.service.get_or_create(self.usuario)
        self.assertEqual(perfil["id_usuario"], self.usuario.id)
        self.assertIsNone(perfil["id_sucursal"])

    def test_update_asigna_sucursal(self):
        perfil = self.service.update_by_usuario(self.usuario, {"id_sucursal": self.sucursal.id})
        self.assertEqual(perfil["id_sucursal"], self.sucursal.id)

    def test_update_sucursal_inexistente_lanza_error(self):
        with self.assertRaises(ValueError):
            self.service.update_by_usuario(self.usuario, {"id_sucursal": 9999})
