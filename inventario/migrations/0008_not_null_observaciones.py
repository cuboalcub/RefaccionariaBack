from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0007_alter_detalleinventario_id_detalle_venta"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
UPDATE inventario_movimientoinventario SET observaciones = '' WHERE observaciones IS NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="observaciones",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
