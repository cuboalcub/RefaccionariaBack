from django.db import models

from producto.models import Producto


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        LOW_STOCK = 'BAJO_STOCK', 'Bajo stock'
        OUT_OF_STOCK = 'AGOTADO', 'Agotado'

    id = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='notifications')
    tipo = models.CharField(max_length=20, choices=NotificationType.choices)
    mensaje = models.CharField(max_length=255)
    leido = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre}"
