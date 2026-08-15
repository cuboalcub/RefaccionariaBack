from django.test import TestCase

from inventario.models import Inventario, MovimientoInventario, DetalleInventario
from inventario.services.detalle_inventario_service import DetalleInventarioService
from producto.models import Producto, Tipo, Proveedor
from sucursales.models import Sucursal


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
            existencia=10,
            costo="90.00",
        )
        self.entrada = MovimientoInventario.objects.create(
            tipo="ENTRADA", cantidad=1, razon="Compra"
        )
        self.salida = MovimientoInventario.objects.create(
            tipo="SALIDA", cantidad=1, razon="Venta"
        )
        self.service = DetalleInventarioService()

    def test_entrada_aumenta_existencia(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, 15)

    def test_salida_disminuye_existencia(self):
        self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.salida.id,
            "cantidad": 3,
        })

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, 7)

    def test_salida_sin_stock_lanza_value_error(self):
        with self.assertRaises(ValueError):
            self.service.create({
                "id_producto": self.producto.id,
                "id_inventario": self.inventario.id,
                "id_proveedor": self.proveedor.id,
                "id_movimiento": self.salida.id,
                "cantidad": 100,
            })

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, 10)
        self.assertEqual(DetalleInventario.objects.count(), 0)

    def test_delete_restituye_stock_entrada(self):
        detalle = self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })

        self.service.delete(detalle["id"])

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, 10)

    def test_delete_restituye_stock_salida(self):
        detalle = self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.salida.id,
            "cantidad": 3,
        })

        self.service.delete(detalle["id"])

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, 10)

    def test_update_ajusta_stock(self):
        detalle = self.service.create({
            "id_producto": self.producto.id,
            "id_inventario": self.inventario.id,
            "id_proveedor": self.proveedor.id,
            "id_movimiento": self.entrada.id,
            "cantidad": 5,
        })

        self.service.update(detalle["id"], {"cantidad": 8})

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.existencia, 18)
