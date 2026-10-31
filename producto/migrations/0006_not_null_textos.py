from django.db import migrations, models


class Migration(migrations.Migration):
    # Postgres rechaza ALTER TABLE con triggers de FK pendientes de la
    # misma transacción cuando antes se hace UPDATE de esas filas.
    atomic = False

    dependencies = [
        ("producto", "0005_merge_20261011_1415"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
UPDATE producto_producto SET descripcion = '' WHERE descripcion IS NULL;
UPDATE producto_producto SET "codigoSAT" = '' WHERE "codigoSAT" IS NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="producto",
            name="descripcion",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="producto",
            name="codigoSAT",
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
