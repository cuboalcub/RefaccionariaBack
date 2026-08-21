from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from clientes.models import Cliente
from sucursales.models import Sucursal


@override_settings(ALLOWED_HOSTS=['*'])
class ClienteAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.sucursal = Sucursal.objects.create(ubicacion='Sucursal Centro')
        self.cliente_data = {
            'nombre': 'Juan',
            'apellido_paterno': 'Pérez',
            'apellido_materno': 'García',
            'telefono': '5551234567',
            'correo': 'juan@email.com',
            'direccion': 'Calle Principal 123',
            'rfc': 'PEGJ800101ABC',
            'id_sucursal': self.sucursal.id,
        }

    def test_crear_cliente(self):
        response = self.client.post('/api/clientes/', self.cliente_data, format='json')
        self.assertEqual(response.status_code, 201)

    def test_listar_clientes(self):
        Cliente.objects.create(
            id_sucursal=self.sucursal,
            nombre='Ana',
            apellido_paterno='López',
            telefono='5559876543',
        )
        response = self.client.get('/api/clientes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_obtener_cliente_por_id(self):
        cliente = Cliente.objects.create(
            id_sucursal=self.sucursal,
            nombre='Carlos',
            apellido_paterno='Ruiz',
            telefono='5551112233',
        )
        response = self.client.get(f'/api/clientes/{cliente.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nombre'], 'Carlos')

    def test_actualizar_cliente(self):
        cliente = Cliente.objects.create(
            id_sucursal=self.sucursal,
            nombre='María',
            apellido_paterno='Torres',
            telefono='5554445566',
        )
        response = self.client.put(
            f'/api/clientes/{cliente.id}/',
            {'nombre': 'María', 'apellido_paterno': 'Torres', 'telefono': '5550001111', 'id_sucursal': self.sucursal.id},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

    def test_eliminar_cliente(self):
        cliente = Cliente.objects.create(
            id_sucursal=self.sucursal,
            nombre='Pedro',
            apellido_paterno='Sánchez',
            telefono='5556667788',
        )
        response = self.client.delete(f'/api/clientes/{cliente.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Cliente.objects.count(), 0)

    def test_crear_cliente_sin_auth(self):
        unauth_client = APIClient()
        response = unauth_client.post('/api/clientes/', self.cliente_data, format='json')
        self.assertEqual(response.status_code, 401)
