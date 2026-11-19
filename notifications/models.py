"""Notificaciones persistentes consultables por el usuario autenticado.

Tipos compatibles con el frontend (info/warning/error/success):
- LOW_STOCK -> "warning" (0 < stock < umbral).
- OUT_OF_STOCK -> "error" (stock == 0).
"""

from django.contrib.auth.models import User
from django.db import models

from producto.models import Producto
from sucursales.models import Sucursal


class Notification(models.Model):
    class Tipo(models.TextChoices):
        LOW_STOCK = "warning", "Stock bajo"
        OUT_OF_STOCK = "error", "Agotado"
        INFO = "info", "Informativa"
        SUCCESS = "success", "Éxito"

    id = models.AutoField(primary_key=True)
    destinatario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    titulo = models.CharField(max_length=120)
    mensaje = models.CharField(max_length=255)
    leida = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)
    resuelta_en = models.DateTimeField(blank=True, null=True)
    ref_producto = models.ForeignKey(
        Producto, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="notifications",
    )
    ref_sucursal = models.ForeignKey(
        Sucursal, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="notifications",
    )
    stock = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.tipo} - {self.titulo}"

    class Meta:
        ordering = ["-creada_en", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["destinatario", "tipo", "ref_producto", "ref_sucursal"],
                condition=models.Q(resuelta_en__isnull=True),
                name="uniq_notif_activa",
            ),
        ]
