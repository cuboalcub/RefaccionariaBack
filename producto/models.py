"""Modelos para representar los productos de la refaccionaria"""

from django.db import models


class Tipo(models.Model):
    """Modelo para representar los tipos de productos"""

    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    """Modelo para representar los proveedores"""

    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    correo = models.EmailField()
    direccion = models.CharField(max_length=200)
    surtir = models.DateField(blank=True, null=True)
    def __str__(self):
        return self.nombre
    
class Producto(models.Model):
    """Modelo para representar los productos"""

    id = models.AutoField(primary_key=True)
    id_tipo = models.ForeignKey(Tipo, on_delete=models.SET_NULL, blank=True, null=True)
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True)
    clave = models.CharField(unique=True, max_length=50)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=100)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.CharField(max_length=100)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    codigoSAT = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return self.nombre
