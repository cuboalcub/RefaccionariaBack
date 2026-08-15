from django.db import models


class Sucursal(models.Model):
    id = models.AutoField(primary_key=True)
    ubicacion = models.CharField(max_length=200)

    def __str__(self):
        return self.ubicacion
