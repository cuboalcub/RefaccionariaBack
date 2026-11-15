from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations, models

IVA_TASA = Decimal("0.16")
CENTAVOS = Decimal("0.01")


def aplicar_iva(apps, schema_editor):
    """Sube el total de las ventas existentes en 16% y guarda el IVA."""
    Venta = apps.get_model("ventas", "Venta")
    for venta in Venta.objects.all().iterator():
        base = venta.total or Decimal(0)
        iva = (base * IVA_TASA).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
        venta.iva = iva
        venta.total = base + iva
        venta.save(update_fields=["iva", "total"])


def quitar_iva(apps, schema_editor):
    Venta = apps.get_model("ventas", "Venta")
    for venta in Venta.objects.all().iterator():
        venta.total = (venta.total or Decimal(0)) - (venta.iva or Decimal(0))
        venta.iva = Decimal(0)
        venta.save(update_fields=["iva", "total"])


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0004_remove_venta_id_inventario_venta_estado_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="venta",
            name="iva",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.RunPython(aplicar_iva, quitar_iva),
    ]
