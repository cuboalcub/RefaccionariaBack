"""Restaura el nodo de migración referenciado por notifications.0001_initial.

Contexto (no modifica historia): la migración original con este nombre se
perdió del árbol (el código actual solo conserva
producto/{0001_initial, 0002_initial, 0004_*}), mientras que
notifications/migrations/0001_initial.py sigue dependiendo de
('producto', '0002_delete_notification'). Sin este nodo, Django no puede
construir el grafo en cuanto 'notifications' entra a INSTALLED_APPS.

Esta migración es intencionalmente vacía: el estado final de 'producto'
ya queda descrito por 0002_initial + 0004_remove_producto_existencia.
En bases donde la migración original ya figura como aplicada, Django la
omite por nombre y no ejecuta nada; en instalaciones nuevas solo resuelve
el grafo sin alterar el esquema.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("producto", "0001_initial"),
    ]

    operations = []
