from django.db import models

# Create your models here.
class Tipo(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    def __str__(self):
        return self.nombre  

class Proveedor(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    correo = models.EmailField()
    direccion = models.CharField(max_length=200)
    def __str__(self):
        return self.nombre
    
class Movimiento(models.Model):
    class TipoMovimiento(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SALIDA = 'SALIDA', 'Salida'

    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=10, choices=TipoMovimiento.choices)
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    razon = models.CharField(max_length=200)
    observacion = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.tipo} - {self.cantidad}"

class Producto(models.Model):
    id = models.AutoField(primary_key=True)
    id_tipo = models.ForeignKey(Tipo, on_delete=models.SET_NULL, blank=True, null=True)
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True)
    id_movimientos = models.ForeignKey(Movimiento,on_delete=models.SET_NULL, blank=True, null=True)
    clave = models.CharField(unique=True, max_length=50)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=100)  
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.CharField(max_length=100)
    existencia = models.IntegerField()
    min_stock = models.IntegerField(default=5, blank=True, null=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    codigoSAT = models.CharField( blank=True, null=True)
    def __str__(self):
        return self.nombre


