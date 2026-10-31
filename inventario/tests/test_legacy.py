"""Comportamiento histórico del inventario: movs de entrada/salida + catálogo."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from inventario.models import MovimientoInventario
from inventario.services.movimiento_inventario_service import MovimientoInventarioService
from producto.models import Producto, Tipo, Proveedor
from sucursales.models import Sucursal
from usuario.models import Perfil


class MovimientoInventarioServiceTestCase(TestCase):

    def setUp(self):
        self.sucursal = Sucursal.objects.create(ubicacion="Centro CDMX")
        self.proveedor = Proveedor.objects.create(
            nombre="Proveedor A", telefono="123", correo="a@a.com", direccion="Calle 1"
        )
        self.tipo = Tipo.objects.create(nombre="Filtro")
        self.producto = Producto.objects.create(
            id_tipo=self.tipo,
            id_proveedor=self.proveedor,
            clave="CLV-001",
            nombre="Filtro de aceite",
            codigo_barras="75010001",
            precio_venta="150.00",
            marca="Bosch",
            costo="90.00",
        )
        self.service = MovimientoInventarioService()

    def _entrada(self, cantidad, razon="Compra"):
        return self.service.create({
            "id_producto": self.producto.id,
            "id_sucursal": self.sucursal.id,
            "id_proveedor": self.proveedor.id,
            "tipo_movimiento": "ENTRADA",
            "razon": razon,
            "cantidad": cantidad,
        }, user=self.usuario if hasattr(self, "usuario") else None)

    def _salida(self, cantidad, razon="Venta"):
        return self.service.create({
            "id_producto": self.producto.id,
            "id_sucursal": self.sucursal.id,
            "tipo_movimiento": "SALIDA",
            "razon": razon,
            "cantidad": cantidad,
        })

    def test_entrada_aumenta_stock(self):
        self._entrada(5)
        self.assertEqual(self.service.get_stock(self.producto.id, self.sucursal.id), 5)

    def test_salida_disminuye_stock(self):
        self._entrada(10)
        self._salida(3)
        self.assertEqual(self.service.get_stock(self.producto.id, self.sucursal.id), 7)

    def test_salida_sin_stock_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self._salida(100)
        self.assertEqual(self.service.get_stock(self.producto.id, self.sucursal.id), 0)
        self.assertEqual(MovimientoInventario.objects.count(), 0)

    def test_delete_quita_registro_entrada(self):
        movimiento = self._entrada(5)
        self.service.delete(movimiento["id"])
        self.assertEqual(self.service.get_stock(self.producto.id, self.sucursal.id), 0)

    def test_update_ajusta_stock(self):
        movimiento = self._entrada(5)
        self.service.update(movimiento["id"], {"cantidad": 8})
        self.assertEqual(self.service.get_stock(self.producto.id, self.sucursal.id), 8)
        mov = MovimientoInventario.objects.get(id=movimiento["id"])
        self.assertEqual(mov.cantidad, 8)


class InventarioPorSucursalTestCase(TestCase):

    def setUp(self):
        self.sucursal = Sucursal.objects.create(ubicacion="Centro CDMX")
        self.otra_sucursal = Sucursal.objects.create(ubicacion="Norte")
        self.proveedor = Proveedor.objects.create(
            nombre="Proveedor A", telefono="123", correo="a@a.com", direccion="Calle 1"
        )
        self.tipo = Tipo.objects.create(nombre="Filtro")
        self.producto = Producto.objects.create(
            id_tipo=self.tipo,
            id_proveedor=self.proveedor,
            clave="CLV-001",
            nombre="Filtro de aceite",
            codigo_barras="75010001",
            precio_venta="150.00",
            marca="Bosch",
            costo="90.00",
        )
        self.usuario = User.objects.create_user(username="vendedor", password="pass123")
        Perfil.objects.create(usuario=self.usuario, id_sucursal=self.sucursal)
        self.usuario_sin_sucursal = User.objects.create_user(username="sin_sucursal", password="pass123")
        self.service = MovimientoInventarioService()
        self.client = APIClient()

    def test_servicio_devuelve_inventario_agrupado(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_sucursal": self.sucursal.id,
            "id_proveedor": self.proveedor.id,
            "cantidad": 5,
        })
        self.service.create({
            "id_producto": self.producto.id,
            "id_sucursal": self.sucursal.id,
            "id_proveedor": self.proveedor.id,
            "cantidad": 3,
        })

        resultado = self.service.get_inventario_por_sucursal(self.sucursal.id)

        self.assertEqual(resultado["id_sucursal"], self.sucursal.id)
        self.assertEqual(len(resultado["detalles"]), 1)
        detalle = resultado["detalles"][0]
        self.assertEqual(detalle["id_producto"], self.producto.id)
        self.assertEqual(detalle["nombre"], "Filtro de aceite")
        self.assertEqual(detalle["cantidad"], 8)

    def test_servicio_devuelve_vacio_sin_stock(self):
        resultado = self.service.get_inventario_por_sucursal(self.otra_sucursal.id)
        self.assertEqual(resultado, {"id_sucursal": self.otra_sucursal.id, "detalles": []})

    def test_endpoint_devuelve_inventario_del_usuario(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.get("/api/inventarios/mi-sucursal/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id_sucursal"], self.sucursal.id)

    def test_endpoint_400_sin_sucursal(self):
        self.client.force_authenticate(user=self.usuario_sin_sucursal)
        response = self.client.get("/api/inventarios/mi-sucursal/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_endpoint_401_sin_autenticacion(self):
        response = self.client.get("/api/inventarios/mi-sucursal/")
        self.assertEqual(response.status_code, 401)
