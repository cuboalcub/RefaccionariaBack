from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clientes", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
UPDATE clientes_cliente SET apellido_materno = '' WHERE apellido_materno IS NULL;
UPDATE clientes_cliente SET direccion = '' WHERE direccion IS NULL;
UPDATE clientes_cliente SET rfc = '' WHERE rfc IS NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="cliente",
            name="apellido_materno",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="direccion",
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="rfc",
            field=models.CharField(blank=True, max_length=13),
        ),
    ]
