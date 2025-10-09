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
    id = models.AutoField(primary_key=True)
    tipo = models.TextChoices('ENTRADA',' SALIDA')
    cantidad = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    razon = models.CharField(max_length=200)
    observacion = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    id = models.AutoField(primary_key=True)
    id_tipo = models.ForeignKey(Tipo, on_delete=models.CASCADE)
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    id_movimientos = models.ManyToManyField(Movimiento, blank=True)
    clave = models.CharField(unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    codigo_barras = models.CharField()  
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.CharField(max_length=100)
    existencia = models.IntegerField()
    costo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nombre