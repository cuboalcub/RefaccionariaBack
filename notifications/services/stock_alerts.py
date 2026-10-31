"""Evaluación de alertas LOW_STOCK / OUT_OF_STOCK por producto y sucursal.

Reglas del ciclo de alertas:
- El stock de la sucursal vive en la tabla Stock (balance consolidado).
- OUT_OF_STOCK si stock == 0; LOW_STOCK si 0 < stock < umbral; nada si
  stock >= umbral.
- Nunca hay dos alertas activas (resuelta_en IS NULL) para el mismo
  (destinatario, tipo, producto, sucursal): la restricción parcial
  uniq_notif_activa lo garantiza incluso ante carreras.
- Transición bajo -> agotado (o viceversa): se resuelve la anterior y se
  crea la nueva. Recuperación: se resuelve sin borrar. Reincidencia: la
  fila resuelta queda como historial y se permite crear otra.
"""

import logging

from django.db import transaction
from django.utils import timezone

from inventario.repositories.stock_repository import StockRepository
from notifications.models import Notification
from notifications.services.thresholds import get_low_stock_threshold
from producto.models import Producto
from sucursales.models import Sucursal
from usuario.models import Perfil

logger = logging.getLogger(__name__)


def programar_evaluacion(producto_id: int, sucursal_id: int) -> None:
    """Registra la evaluación para después del commit.

    Los fallos de notificaciones nunca deben revertir una operación de
    inventario ya confirmada: la evaluación corre fuera de la transacción
    original y cualquier excepción solo queda en el log.
    """

    def _run():
        try:
            evaluar_stock(producto_id, sucursal_id)
        except Exception:
            logger.exception(
                "notifications: no se pudo evaluar alerta producto=%s sucursal=%s",
                producto_id,
                sucursal_id,
            )

    transaction.on_commit(_run)


def evaluar_stock(producto_id: int, sucursal_id: int):
    sucursal = Sucursal.objects.filter(id=sucursal_id).first()
    if sucursal is None:
        return None
    umbral = get_low_stock_threshold()
    stock = StockRepository().get_stock(producto_id, sucursal_id)
    if stock == 0:
        deseado = Notification.Tipo.OUT_OF_STOCK
    elif stock < umbral:
        deseado = Notification.Tipo.LOW_STOCK
    else:
        deseado = None

    ahora = timezone.now()
    with transaction.atomic():
        activas = list(
            Notification.objects.filter(
                ref_producto_id=producto_id,
                ref_sucursal_id=sucursal.id,
                resuelta_en__isnull=True,
            )
        )
        resueltas = 0
        for alerta in activas:
            if alerta.tipo != deseado:
                alerta.resuelta_en = ahora
                alerta.save(update_fields=["resuelta_en"])
                resueltas += 1
        creadas = 0
        if deseado is not None and not any(a.tipo == deseado for a in activas):
            creadas = _crear_para_sucursal(deseado, producto_id, sucursal, stock, umbral)
    return {
        "producto_id": producto_id,
        "sucursal_id": sucursal.id,
        "stock": stock,
        "tipo": deseado,
        "creadas": creadas,
        "resueltas": resueltas,
    }


def _crear_para_sucursal(tipo, producto_id, sucursal, stock, umbral):
    user_ids = list(
        Perfil.objects.filter(id_sucursal_id=sucursal.id).values_list(
            "usuario_id", flat=True
        )
    )
    if not user_ids:
        return 0
    producto = Producto.objects.filter(id=producto_id).first()
    nombre_producto = producto.nombre
    nombre_sucursal = sucursal.nombre_sucursal or sucursal.ubicacion
    if tipo == Notification.Tipo.OUT_OF_STOCK:
        titulo = "Producto agotado"
        mensaje = f"{nombre_producto} se agotó en {nombre_sucursal}."
    else:
        titulo = "Stock bajo"
        mensaje = (
            f"{nombre_producto}: quedan {stock} unidades en {nombre_sucursal} "
            f"(mínimo {umbral})."
        )
    avisos = [
        Notification(
            destinatario_id=user_id,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            ref_producto_id=producto_id,
            ref_sucursal_id=sucursal.id,
            stock=stock,
        )
        for user_id in user_ids
    ]
    # ignore_conflicts: si otra transacción creó la alerta activa entre la
    # lectura y la escritura, la restricción uniq_notif_activa la descarta.
    Notification.objects.bulk_create(avisos, ignore_conflicts=True)
    return len(user_ids)
