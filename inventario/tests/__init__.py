from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from inventario.models import Inventario, MovimientoInventario, DetalleInventario
from inventario.services.detalle_inventario_service import DetalleInventarioService
from producto.models import Producto, Tipo, Proveedor
from sucursales.models import Sucursal
from usuario.models import Perfil


class DetalleInventarioServiceTestCase(TestCase):

    def setUp(self):
        self.sucursal = Sucursal.objects.create(ubicacion="Centro CDMX")
        self.inventario = Inventario.objects.create(
            id_sucursal=self.sucursal, descripcion="Inventario general"
        )
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
        self.entrada = MovimientoInventario.objects.create(
            tipo="ENTRADA", cantidad=1, razon="Compra"
        )
        self.salida = MovimientoInventario.objects.create(
            tipo="SALIDA", cantidad=1, razon="Venta"
        )
        self.service = DetalleInventarioService()

    def test_entrada_aumenta_stock(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })

        self.assertEqual(self.service.get_stock(self.producto.id, self.inventario.id), 5)

    def test_salida_disminuye_stock(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 10,
        })
        self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.salida.id,
            "cantidad": 3,
        })

        self.assertEqual(self.service.get_stock(self.producto.id, self.inventario.id), 7)

    def test_salida_sin_stock_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({
                "id_producto": self.producto.id,
                "id_inventario": self.inventario.id,
                "id_proveedor": self.proveedor.id,
                "id_movimiento": self.salida.id,
                "cantidad": 100,
            })

        self.assertEqual(self.service.get_stock(self.producto.id, self.inventario.id), 0)
        self.assertEqual(DetalleInventario.objects.count(), 0)

    def test_delete_quita_registro_entrada(self):
        detalle = self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })

        self.service.delete(detalle["id"])

        self.assertEqual(self.service.get_stock(self.producto.id, self.inventario.id), 0)

    def test_update_ajusta_stock(self):
        detalle = self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })

        self.service.update(detalle["id"], {"cantidad": 8})

        self.assertEqual(self.service.get_stock(self.producto.id, self.inventario.id), 8)


class InventarioPorSucursalTestCase(TestCase):

    def setUp(self):
        self.sucursal = Sucursal.objects.create(ubicacion="Centro CDMX")
        self.otra_sucursal = Sucursal.objects.create(ubicacion="Norte")
        self.inventario = Inventario.objects.create(
            id_sucursal=self.sucursal, descripcion="Inventario general"
        )
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
        self.entrada = MovimientoInventario.objects.create(
            tipo="ENTRADA", cantidad=1, razon="Compra"
        )
        self.usuario = User.objects.create_user(username="vendedor", password="pass123")
        Perfil.objects.create(usuario=self.usuario, id_sucursal=self.sucursal)
        self.usuario_sin_sucursal = User.objects.create_user(username="sin_sucursal", password="pass123")
        self.service = DetalleInventarioService()
        self.client = APIClient()

    def test_servicio_devuelve_inventario_agrupado(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })
        self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 3,
        })

        resultado = self.service.get_inventario_por_sucursal(self.sucursal.id)

        self.assertEqual(len(resultado), 1)
        inventario = resultado[0]
        self.assertEqual(inventario["id_inventario"], self.inventario.id)
        self.assertEqual(len(inventario["detalles"]), 1)
        detalle = inventario["detalles"][0]
        self.assertEqual(detalle["id_producto"], self.producto.id)
        self.assertEqual(detalle["nombre"], "Filtro de aceite")
        self.assertEqual(detalle["cantidad"], 8)

    def test_servicio_devuelve_vacio_sin_inventario(self):
        resultado = self.service.get_inventario_por_sucursal(self.otra_sucursal.id)
        self.assertEqual(resultado, [])

    def test_endpoint_devuelve_inventario_del_usuario(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.get("/api/inventarios/mi-sucursal/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_endpoint_400_sin_sucursal(self):
        self.client.force_authenticate(user=self.usuario_sin_sucursal)
        response = self.client.get("/api/inventarios/mi-sucursal/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_endpoint_401_sin_autenticacion(self):
        response = self.client.get("/api/inventarios/mi-sucursal/")
        self.assertEqual(response.status_code, 401)