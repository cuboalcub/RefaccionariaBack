from django.db import models
from django.contrib.auth.models import User
from producto.models import Producto
from sucursales.models import Sucursal
from clientes.models import Cliente


class MetodoPago(models.Model):
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100)


class Venta(models.Model):
    ESTADO_CHOICES = [
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    id = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    id_metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True)
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, related_name='ventas')
    id_cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='completada')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    

class DetalleVenta(models.Model):
    id = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    id_venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField()

class Reporte(models.Model):
    TIPO_CHOICES = [
        ('day', 'Diario'),
        ('week', 'Semanal'),
        ('quincena', 'Quincenal'),
        ('month', 'Mensual'),
        ('year', 'Anual'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    archivo = models.FileField(upload_to='reportes/')
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reporte {self.tipo} - {self.fecha_inicio} a {self.fecha_fin}"