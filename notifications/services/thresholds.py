"""Umbral de stock bajo para alertas de inventario.

LOW_STOCK aplica cuando 0 < stock < umbral; OUT_OF_STOCK cuando stock == 0.
El umbral se configura con NOTIFICATIONS_LOW_STOCK_THRESHOLD (defecto 10)
y debe ser un entero >= 2: con 1 o menos, LOW_STOCK sería inalcanzable y la
configuración casi con seguridad es un error.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

DEFAULT_THRESHOLD = 10
MIN_THRESHOLD = 2


def get_low_stock_threshold() -> int:
    raw = getattr(settings, "NOTIFICATIONS_LOW_STOCK_THRESHOLD", DEFAULT_THRESHOLD)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ImproperlyConfigured(
            "NOTIFICATIONS_LOW_STOCK_THRESHOLD debe ser un entero >= 2, "
            f"se recibió {raw!r}"
        )
    if value < MIN_THRESHOLD:
        raise ImproperlyConfigured(
            "NOTIFICATIONS_LOW_STOCK_THRESHOLD debe ser un entero >= 2, "
            f"se recibió {raw!r}"
        )
    return value
