from django.contrib.auth.models import User
from django.db import models

from sucursales.models import Sucursal


class Cliente(models.Model):
    id = models.AutoField(primary_key=True)
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, related_name='clientes')
    nombre = models.CharField(max_length=150)
    apellido_paterno = models.CharField(max_length=150)
    apellido_materno = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=15)
    correo = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=250, blank=True)
    rfc = models.CharField(max_length=13, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno}"


class Adeudo(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('cancelado', 'Cancelado'),
    ]

    id = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='adeudos')
    id_venta = models.ForeignKey(
        'ventas.Venta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adeudos',
    )
    concepto = models.CharField(max_length=250, blank=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    saldo = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    fecha = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Adeudo {self.id} - {self.id_cliente}"


class AbonoAdeudo(models.Model):
    id = models.AutoField(primary_key=True)
    id_adeudo = models.ForeignKey(Adeudo, on_delete=models.CASCADE, related_name='abonos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    id_metodo_pago = models.ForeignKey(
        'ventas.MetodoPago',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    id_usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Abono {self.id} - ${self.monto}"
