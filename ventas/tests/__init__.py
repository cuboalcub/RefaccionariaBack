from django.contrib.auth.models import User
from django.test import TestCase

from producto.models import Producto, Tipo, Proveedor
from ventas.models import venta, metodoPago, detalleVenta
from ventas.services.detalleventa_service import DetalleVentaService
from ventas.services.ventas_services import VentaService


class DetalleVentaServiceTestCase(TestCase):

    def setUp(self):
        self.tipo = Tipo.objects.create(nombre="Filtro")
        self.proveedor = Proveedor.objects.create(
            nombre="Proveedor A", telefono="123", correo="a@a.com", direccion="Calle 1"
        )
        self.producto = Producto.objects.create(
            id_tipo=self.tipo,
            id_proveedor=self.proveedor,
            clave="CLV-001",
            nombre="Filtro de aceite",
            codigo_barras="75010001",
            precio_venta="150.00",
            marca="Bosch",
            existencia=10,
            costo="90.00",
        )
        self.usuario = User.objects.create_user(username="vendedor", password="pass12345")
        self.metodo = metodoPago.objects.create(tipo="Efectivo", descripcion="Efectivo")
        self.venta = venta.objects.create(
            id_usuario=self.usuario, id_metodoPago=self.metodo, total="150.00"
        )
        self.service = DetalleVentaService()

    def test_create_descuenta_existencia(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
            "subtotal": "300.00",
        })

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, 8)
        self.assertEqual(detalleVenta.objects.count(), 1)

    def test_stock_insuficiente_lanza_value_error_y_rollback(self):
        with self.assertRaises(ValueError):
            self.service.create({
                "id_producto": self.producto.id,
                "id_venta": self.venta.id,
                "cantidad": 100,
                "subtotal": "15000.00",
            })

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, 10)
        self.assertEqual(detalleVenta.objects.count(), 0)

    def test_create_requiere_campos_obligatorios(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_producto": self.producto.id})

    def test_venta_inexistente_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({
                "id_producto": self.producto.id,
                "id_venta": 9999,
                "cantidad": 1,
                "subtotal": "150.00",
            })

    def test_total_venta_se_recalcula_al_crear_detalles(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
            "subtotal": "300.00",
        })
        self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 1,
            "subtotal": "150.00",
        })

        self.venta.refresh_from_db()
        self.assertEqual(str(self.venta.total), "450.00")

    def test_total_venta_se_recalcula_al_actualizar_detalle(self):
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
            "subtotal": "300.00",
        })["id"]

        self.service.update(detalle_id, {"cantidad": 4, "subtotal": "600.00"})

        self.venta.refresh_from_db()
        self.assertEqual(str(self.venta.total), "600.00")

    def test_total_venta_se_recalcula_al_borrar_detalle(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
            "subtotal": "300.00",
        })
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 1,
            "subtotal": "150.00",
        })["id"]

        self.service.delete(detalle_id)

        self.venta.refresh_from_db()
        self.assertEqual(str(self.venta.total), "300.00")

    def test_update_detalle_devuelve_stock_al_producto_anterior(self):
        self.producto2 = Producto.objects.create(
            id_tipo=self.tipo,
            id_proveedor=self.proveedor,
            clave="CLV-002",
            nombre="Filtro de aire",
            codigo_barras="75010002",
            precio_venta="200.00",
            marca="Bosch",
            existencia=5,
            costo="120.00",
        )
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
            "subtotal": "300.00",
        })["id"]

        self.service.update(detalle_id, {"id_producto": self.producto2.id})

        self.producto.refresh_from_db()
        self.producto2.refresh_from_db()
        self.assertEqual(self.producto.existencia, 10)
        self.assertEqual(self.producto2.existencia, 3)


class VentaServiceTestCase(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(username="vendedor", password="pass12345")
        self.metodo = metodoPago.objects.create(tipo="Efectivo", descripcion="Efectivo")
        self.service = VentaService()

    def test_create_requiere_id_usuario(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_metodoPago": self.metodo.id, "total": "100.00"})

    def test_create_requiere_id_metodo_pago(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_usuario": self.usuario.id, "total": "100.00"})

    def test_usuario_inexistente_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_usuario": 9999, "id_metodoPago": self.metodo.id})

    def test_metodo_inexistente_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_usuario": self.usuario.id, "id_metodoPago": 9999})

    def test_create_exitoso(self):
        resultado = self.service.create({
            "id_usuario": self.usuario.id,
            "id_metodoPago": self.metodo.id,
            "total": "250.00",
        })

        self.assertIsNotNone(resultado["id"])
        self.assertEqual(str(resultado["total"]), "0")
