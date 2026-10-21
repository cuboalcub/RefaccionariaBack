from django.db import migrations, models


def drop_min_stock(apps, schema_editor):
    """Drop the min_stock column that was added by a now-deleted migration."""
    try:
        schema_editor.execute(
            "ALTER TABLE producto_producto DROP COLUMN IF EXISTS min_stock"
        )
    except Exception:
        # Fallback for SQLite < 3.35 or if column does not exist
        try:
            # check if column exists via pragma
            cursor = schema_editor.connection.cursor()
            cursor.execute("PRAGMA table_info(producto_producto)")
            cols = [row[1] for row in cursor.fetchall()]
            if "min_stock" in cols:
                # SQLite <3.35 does not support IF EXISTS, try without it
                schema_editor.execute(
                    "ALTER TABLE producto_producto DROP COLUMN min_stock"
                )
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('producto', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='proveedor',
            name='surtir',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RemoveField(
            model_name='producto',
            name='id_movimientos',
        ),
        migrations.DeleteModel(
            name='Movimiento',
        ),
        migrations.RunPython(drop_min_stock, migrations.RunPython.noop),
    ]
