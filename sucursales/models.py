from django.db import models


import uuid

from django.db import models


def _gen_codigo_sucursal():
    return f"SUC-{uuid.uuid4().hex[:6].upper()}"


class Sucursal(models.Model):
    id = models.AutoField(primary_key=True)
    nombre_sucursal = models.CharField(max_length=100, blank=True, default='')
    codigo_sucursal = models.CharField(max_length=50, unique=True, blank=True, default=_gen_codigo_sucursal)
    ubicacion = models.CharField(max_length=200)
    codigo_postal = models.CharField(max_length=10, blank=True, default='')
    numero_telefono = models.CharField(max_length=15, blank=True, default='')
    correo_electronico = models.EmailField(blank=True, default='')

    def __str__(self):
        return self.ubicacion
