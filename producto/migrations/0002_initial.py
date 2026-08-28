from django.db import migrations, models


def drop_min_stock(apps, schema_editor):
    """Drop the min_stock column that was added by a now-deleted migration."""
    schema_editor.execute(
        "ALTER TABLE producto_producto DROP COLUMN IF EXISTS min_stock"
    )


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
