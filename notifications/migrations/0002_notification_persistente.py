# Reemplaza el modelo histórico Notification (BAJO_STOCK/AGOTADO, solo
# producto, sin destinatario) por el modelo persistente de notificaciones
# personales (tipo compatible con el frontend, destinatario, leída,
# referencia a producto/sucursal/inventario y ciclo activa/resuelta).
#
# - Instalación nueva: 0001 crea la tabla vieja y esta migración la
#   sustituye; el esquema final es el del modelo actual.
# - Base con 0001 ya aplicada: la primera operación respalda las filas
#   viejas en notifications_notification_legacy y luego se sustituye la
#   tabla. El respaldo NUNCA se elimina automáticamente: si ya existe,
#   la migración aborta antes de tocar nada; al revertir, las filas se
#   restauran en la tabla vieja y el respaldo se conserva.
# No modifica ninguna migración histórica.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

TABLA_VIEJA = "notifications_notification"
TABLA_RESPALDO = "notifications_notification_legacy"
# Columnas de la tabla vieja (orden del SELECT del respaldo y del restore).
COLUMNAS_VIEJAS = '"id", "tipo", "mensaje", "leido", "creado_en", "producto_id"'


def respaldar_notificaciones_historicas(apps, schema_editor):
    """Copia las filas viejas al respaldo antes del DROP.

    Aborta sin tocar nada si el respaldo ya existe (podría ser una copia
    válida anterior: no se sobrescribe, no se duplica, no se salta en
    silencio). Si la tabla vieja está vacía, no se crea ninguna tabla
    legacy vacía. Si la tabla vieja falta, falla a gritos en vez de
    ocultar el estado anómalo. Sintaxis válida en PostgreSQL y SQLite.
    """
    with schema_editor.connection.cursor() as cursor:
        tablas = schema_editor.connection.introspection.table_names(cursor)
    if TABLA_RESPALDO in tablas:
        raise RuntimeError(
            f"{TABLA_RESPALDO} ya existe: posible respaldo previo. "
            "Renómbrela o elimínela manualmente tras verificar su contenido "
            "y reintente; no se modificó nada."
        )
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) FROM "{TABLA_VIEJA}"')
        (total,) = cursor.fetchone()
    if total == 0:
        return
    schema_editor.execute(
        f'CREATE TABLE "{TABLA_RESPALDO}" AS SELECT * FROM "{TABLA_VIEJA}"'
    )


def restaurar_respaldo(apps, schema_editor):
    """Reversa: devuelve las filas a la tabla vieja recreada por Django.

    Se ejecuta después de que Django recrea la tabla vieja (vacía). El
    respaldo se CONSERVA a propósito: nunca se elimina automáticamente.
    Si el respaldo falta, no hay nada que restaurar y se continúa.
    """
    with schema_editor.connection.cursor() as cursor:
        tablas = schema_editor.connection.introspection.table_names(cursor)
    if TABLA_RESPALDO not in tablas:
        return
    schema_editor.execute(
        f'INSERT INTO "{TABLA_VIEJA}" ({COLUMNAS_VIEJAS}) '
        f'SELECT {COLUMNAS_VIEJAS} FROM "{TABLA_RESPALDO}"'
    )


class Migration(migrations.Migration):

    dependencies = [
        # Desacoplada (Alt-1a): solo migraciones iniciales ya aplicadas en
        # producción. No arrastra producto.0004/merge, inventario.0002-0006,
        # sucursales.0002/0003 ni ventas.0002.
        ("notifications", "0001_initial"),
        ("producto", "0001_initial"),
        ("inventario", "0001_initial"),
        ("sucursales", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(
            respaldar_notificaciones_historicas,
            reverse_code=restaurar_respaldo,
        ),
        migrations.DeleteModel(
            name="Notification",
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "destinatario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("warning", "Stock bajo"),
                            ("error", "Agotado"),
                            ("info", "Informativa"),
                            ("success", "Éxito"),
                        ],
                        max_length=10,
                    ),
                ),
                ("titulo", models.CharField(max_length=120)),
                ("mensaje", models.CharField(max_length=255)),
                ("leida", models.BooleanField(default=False)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("resuelta_en", models.DateTimeField(blank=True, null=True)),
                (
                    "ref_producto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notifications",
                        to="producto.producto",
                    ),
                ),
                (
                    "ref_sucursal",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notifications",
                        to="sucursales.sucursal",
                    ),
                ),
                (
                    "ref_inventario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notifications",
                        to="inventario.inventario",
                    ),
                ),
                ("stock", models.IntegerField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-creada_en", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.UniqueConstraint(
                condition=models.Q(resuelta_en__isnull=True),
                fields=("destinatario", "tipo", "ref_producto", "ref_sucursal"),
                name="uniq_notif_activa",
            ),
        ),
    ]
