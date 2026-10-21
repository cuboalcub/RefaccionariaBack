from django.test import TestCase

from sucursales.services.sucursal_service import SucursalService


class SucursalServiceTestCase(TestCase):

    def setUp(self):
        self.service = SucursalService()

    def test_crear_sucursal(self):
        resultado = self.service.create({"ubicacion": "Centro CDMX"})
        self.assertIsNotNone(resultado["id"])
        self.assertEqual(resultado["ubicacion"], "Centro CDMX")

    def test_crear_sucursal_sin_ubicacion_lanza_error(self):
        with self.assertRaises(ValueError):
            self.service.create({})
