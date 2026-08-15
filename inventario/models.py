from django.db import models

from sucursales.models import Sucursal
from producto.models import Producto, Proveedor


class Inventario(models.Model):
    id = models.AutoField(primary_key=True)
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='inventarios')
    descripcion = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.descripcion} ({self.id_sucursal})"


class MovimientoInventario(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SALIDA = 'SALIDA', 'Salida'

    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=10, choices=TipoMovimiento.choices)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    razon = models.CharField(max_length=200)
    observaciones = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.tipo} - {self.cantidad}"


class DetalleInventario(models.Model):
    id = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='detalles_inventario')
    id_inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name='detalles')
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, related_name='detalles_inventario')
    id_movimiento = models.ForeignKey(MovimientoInventario, on_delete=models.CASCADE, related_name='detalles')
    cantidad = models.IntegerField()
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id_producto} - {self.cantidad}"
