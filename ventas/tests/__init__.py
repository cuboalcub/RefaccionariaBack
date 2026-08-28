from django.contrib.auth.models import User
from django.test import TestCase

from producto.models import Producto, Tipo, Proveedor
from ventas.models import venta, metodoPago, detalleVenta
from ventas.services.detalleventa_service import DetalleVentaService
from ventas.services.ventas_services import VentaService
from inventario.models import Inventario, MovimientoInventario
from inventario.services.detalle_inventario_service import DetalleInventarioService
from sucursales.models import Sucursal


class DetalleVentaServiceTestCase(TestCase):

    def setUp(self):
        self.sucursal = Sucursal.objects.create(ubicacion="Centro CDMX")
        self.inventario = Inventario.objects.create(
            id_sucursal=self.sucursal, descripcion="Inventario general"
        )
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
            costo="90.00",
        )
        self.usuario = User.objects.create_user(username="vendedor", password="pass12345")
        self.metodo = metodoPago.objects.create(tipo="Efectivo", descripcion="Efectivo")
        self.venta = venta.objects.create(
            id_usuario=self.usuario,
            id_metodoPago=self.metodo,
            id_inventario=self.inventario,
            total="150.00",
        )
        self.entrada = MovimientoInventario.objects.create(
            tipo="ENTRADA", cantidad=1, razon="Compra"
        )
        self.inv_service = DetalleInventarioService()
        self.inv_service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 10,
        })
        self.service = DetalleVentaService()

    def test_create_descuenta_stock_del_inventario(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
        })

        self.assertEqual(self.inv_service.get_stock(self.producto.id, self.inventario.id), 8)
        self.assertEqual(detalleVenta.objects.count(), 1)
        self.assertEqual(MovimientoInventario.objects.filter(tipo="SALIDA").count(), 1)

    def test_stock_insuficiente_lanza_value_error_y_rollback(self):
        with self.assertRaises(ValueError):
            self.service.create({
                "id_producto": self.producto.id,
                "id_venta": self.venta.id,
                "cantidad": 100,
            })

        self.assertEqual(self.inv_service.get_stock(self.producto.id, self.inventario.id), 10)
        self.assertEqual(detalleVenta.objects.count(), 0)
        self.assertEqual(MovimientoInventario.objects.filter(tipo="SALIDA").count(), 0)

    def test_create_requiere_campos_obligatorios(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_producto": self.producto.id})

    def test_venta_inexistente_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({
                "id_producto": self.producto.id,
                "id_venta": 9999,
                "cantidad": 1,
            })

    def test_total_venta_se_recalcula_al_crear_detalles(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
        })
        self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 1,
        })

        self.venta.refresh_from_db()
        self.assertEqual(str(self.venta.total), "450.00")

    def test_total_venta_se_recalcula_al_actualizar_detalle(self):
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
        })["id"]

        self.service.update(detalle_id, {"cantidad": 4})

        self.venta.refresh_from_db()
        self.assertEqual(str(self.venta.total), "600.00")

    def test_total_venta_se_recalcula_al_borrar_detalle(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
        })
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 1,
        })["id"]

        self.service.delete(detalle_id)

        self.venta.refresh_from_db()
        self.assertEqual(str(self.venta.total), "300.00")

    def test_borrar_detalle_restituye_stock(self):
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
        })["id"]

        self.service.delete(detalle_id)

        self.assertEqual(self.inv_service.get_stock(self.producto.id, self.inventario.id), 10)
        self.assertEqual(MovimientoInventario.objects.filter(tipo="SALIDA").count(), 0)

    def test_update_detalle_ajusta_stock_al_cambiar_producto(self):
        self.producto2 = Producto.objects.create(
            id_tipo=self.tipo,
            id_proveedor=self.proveedor,
            clave="CLV-002",
            nombre="Filtro de aire",
            codigo_barras="75010002",
            precio_venta="200.00",
            marca="Bosch",
            costo="120.00",
        )
        self.inv_service.create({
            "id_producto": self.producto2.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
        })["id"]

        self.service.update(detalle_id, {"id_producto": self.producto2.id})

        self.assertEqual(self.inv_service.get_stock(self.producto.id, self.inventario.id), 10)
        self.assertEqual(self.inv_service.get_stock(self.producto2.id, self.inventario.id), 3)

    def test_create_calcula_subtotal_desde_precio_venta(self):
        resultado = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 3,
        })

        detalle = detalleVenta.objects.get(id=resultado["id"])
        self.assertEqual(str(detalle.subtotal), "450.00")

    def test_create_ignora_subtotal_del_cliente(self):
        resultado = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
            "subtotal": "999.99",
        })

        detalle = detalleVenta.objects.get(id=resultado["id"])
        self.assertEqual(str(detalle.subtotal), "300.00")

    def test_update_calcula_subtotal_al_cambiar_cantidad(self):
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
        })["id"]

        self.service.update(detalle_id, {"cantidad": 4})

        detalle = detalleVenta.objects.get(id=detalle_id)
        self.assertEqual(str(detalle.subtotal), "600.00")

    def test_update_calcula_subtotal_al_cambiar_producto(self):
        self.producto2 = Producto.objects.create(
            id_tipo=self.tipo,
            id_proveedor=self.proveedor,
            clave="CLV-002",
            nombre="Filtro de aire",
            codigo_barras="75010002",
            precio_venta="200.00",
            marca="Bosch",
            costo="120.00",
        )
        self.inv_service.create({
            "id_producto": self.producto2.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })
        detalle_id = self.service.create({
            "id_producto": self.producto.id,
            "id_venta": self.venta.id,
            "cantidad": 2,
        })["id"]

        self.service.update(detalle_id, {"id_producto": self.producto2.id})

        detalle = detalleVenta.objects.get(id=detalle_id)
        self.assertEqual(str(detalle.subtotal), "400.00")

    def test_create_redondea_subtotal_decimal(self):
        self.producto_decimal = Producto.objects.create(
            id_tipo=self.tipo,
            id_proveedor=self.proveedor,
            clave="CLV-003",
            nombre="Filtro premium",
            codigo_barras="75010003",
            precio_venta="150.33",
            marca="Bosch",
            costo="90.00",
        )
        self.inv_service.create({
            "id_producto": self.producto_decimal.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 10,
        })
        resultado = self.service.create({
            "id_producto": self.producto_decimal.id,
            "id_venta": self.venta.id,
            "cantidad": 3,
        })

        detalle = detalleVenta.objects.get(id=resultado["id"])
        self.assertEqual(str(detalle.subtotal), "450.99")


class VentaServiceTestCase(TestCase):

    def setUp(self):
        self.sucursal = Sucursal.objects.create(ubicacion="Centro CDMX")
        self.inventario = Inventario.objects.create(
            id_sucursal=self.sucursal, descripcion="Inventario general"
        )
        self.usuario = User.objects.create_user(username="vendedor", password="pass12345")
        self.metodo = metodoPago.objects.create(tipo="Efectivo", descripcion="Efectivo")
        self.service = VentaService()

    def test_create_requiere_id_usuario(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_metodoPago": self.metodo.id, "id_inventario": self.inventario.id})

    def test_create_requiere_id_metodo_pago(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_usuario": self.usuario.id, "id_inventario": self.inventario.id})

    def test_create_requiere_id_inventario(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_usuario": self.usuario.id, "id_metodoPago": self.metodo.id})

    def test_usuario_inexistente_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_usuario": 9999, "id_metodoPago": self.metodo.id, "id_inventario": self.inventario.id})

    def test_metodo_inexistente_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_usuario": self.usuario.id, "id_metodoPago": 9999, "id_inventario": self.inventario.id})

    def test_inventario_inexistente_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({"id_usuario": self.usuario.id, "id_metodoPago": self.metodo.id, "id_inventario": 9999})

    def test_create_exitoso(self):
        resultado = self.service.create({
            "id_usuario": self.usuario.id,
            "id_metodoPago": self.metodo.id,
            "id_inventario": self.inventario.id,
        })

        self.assertIsNotNone(resultado["id"])
        self.assertEqual(str(resultado["total"]), "0")
        self.assertEqual(resultado["id_inventario"], self.inventario.id)