from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from sucursales.models import Sucursal
from producto.models import Producto, Proveedor


class MovimientoInventario(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SALIDA = 'SALIDA', 'Salida'

    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=10, choices=TipoMovimiento.choices)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    razon = models.CharField(max_length=200)
    observaciones = models.CharField(max_length=200, blank=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos_inventario')
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='movimientos_inventario')
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='movimientos_inventario')
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, related_name='movimientos_inventario')
    id_detalle_venta = models.OneToOneField("ventas.DetalleVenta", on_delete=models.PROTECT, blank=True, null=True, related_name='detalle_inventario')

    def __str__(self):
        return f"{self.tipo} - {self.cantidad}"


class Stock(models.Model):
    id = models.AutoField(primary_key=True)
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='stocks')
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='stocks')
    cantidad = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['id_sucursal', 'id_producto'],
                name='uniq_stock_sucursal_producto',
            ),
        ]

    def __str__(self):
        return f"{self.id_producto} @ {self.id_sucursal} = {self.cantidad}"


class PrecioSucursal(models.Model):
    id = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='precios_sucursal')
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, related_name='precios_sucursal')
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    vigente_desde = models.DateTimeField(default=timezone.now)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'precio_sucursal'
        constraints = [
            models.UniqueConstraint(
                fields=['id_producto', 'id_sucursal'],
                condition=models.Q(activo=True),
                name='uniq_precio_activo',
            ),
        ]
        indexes = [
            models.Index(fields=['id_producto', 'id_sucursal', 'activo', 'vigente_desde']),
        ]

    def __str__(self):
        return f"{self.id_producto} @ {self.id_sucursal} = {self.precio_venta}"
