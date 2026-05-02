from django.test import TestCase, Client
from producto.models import Tipo, Proveedor, Movimiento, Producto
from notifications.models import Notification
from producto.services.producto_service import ProductoService
from ventas.services.detalleventa_service import DetalleVentaService
from ventas.models import venta


class NotificationTests(TestCase):
    def setUp(self):
        self.tipo = Tipo.objects.create(nombre='Test')
        self.proveedor = Proveedor.objects.create(
            nombre='Proveedor Test', telefono='1234567890', correo='test@example.com', direccion='Calle 1'
        )
        self.movimiento = Movimiento.objects.create(
            tipo=Movimiento.TipoMovimiento.ENTRADA,
            cantidad=1,
            razon='Inicial',
            observacion=''
        )
        self.producto_data = {
            'id_tipo': self.tipo.id,
            'id_proveedor': self.proveedor.id,
            'id_movimientos': self.movimiento.id,
            'clave': 'P001',
            'nombre': 'Producto Test',
            'descripcion': 'Desc',
            'codigo_barras': '123456',
            'precio_venta': '10.00',
            'marca': 'Marca',
            'existencia': 5,
            'costo': '5.00',
        }
        self.service = ProductoService()
        self.client = Client()

    def test_create_product_with_low_stock_generates_notification(self):
        self.producto_data['existencia'] = 3
        producto = self.service.create(self.producto_data)
        notification = Notification.objects.filter(
            producto_id=producto['id'], tipo=Notification.NotificationType.LOW_STOCK, leido=False
        ).first()
        self.assertIsNotNone(notification)
        self.assertIn('stock bajo', notification.mensaje)

    def test_create_product_with_zero_stock_generates_notification(self):
        self.producto_data['existencia'] = 0
        producto = self.service.create(self.producto_data)
        notification = Notification.objects.filter(
            producto_id=producto['id'], tipo=Notification.NotificationType.OUT_OF_STOCK, leido=False
        ).first()
        self.assertIsNotNone(notification)
        self.assertIn('agotado', notification.mensaje)

    def test_sale_reduces_stock_and_creates_notification(self):
        producto = self.service.create(self.producto_data)
        venta_obj = venta.objects.create(id_usuario=None, id_metodoPago=None, total='0.00')
        detalle_data = {
            'id_producto': producto['id'],
            'id_venta': venta_obj.id,
            'subtotal': '0.00',
            'cantidad': 3,
        }
        DetalleVentaService().create(detalle_data)
        notification = Notification.objects.filter(
            producto_id=producto['id'], tipo=Notification.NotificationType.LOW_STOCK, leido=False
        ).first()
        self.assertIsNotNone(notification)

    def test_mark_notification_as_read_endpoint(self):
        self.producto_data['existencia'] = 0
        producto = self.service.create(self.producto_data)
        notification = Notification.objects.filter(producto_id=producto['id']).first()
        response = self.client.patch(f'/api/notificaciones/{notification.id}/')
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.leido)
