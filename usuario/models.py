from django.db import models
from django.contrib.auth.models import User

from sucursales.models import Sucursal


class Perfil(models.Model):
    class Rol(models.TextChoices):
        CAJERO = 'cajero', 'Cajero'
        ENCARGADO = 'encargado', 'Encargado'
        ADMIN = 'admin', 'Admin'

    id = models.AutoField(primary_key=True)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, blank=True, null=True, related_name='perfiles')
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.CAJERO)

    def __str__(self):
        return f"{self.usuario.username}"
