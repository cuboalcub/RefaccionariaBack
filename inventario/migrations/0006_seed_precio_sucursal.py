from django.db import migrations
from django.utils import timezone


def seed_precios(apps, schema_editor):
    Producto = apps.get_model('producto', 'Producto')
    Sucursal = apps.get_model('sucursales', 'Sucursal')
    PrecioSucursal = apps.get_model('inventario', 'PrecioSucursal')
    productos = list(Producto.objects.all())
    sucursales = list(Sucursal.objects.all())
    if not productos or not sucursales:
        return
    now = timezone.now()
    objs = []
    for prod in productos:
        for suc in sucursales:
            # evitar duplicado si ya existe
            if PrecioSucursal.objects.filter(id_producto_id=prod.id, id_sucursal_id=suc.id, activo=True).exists():
                continue
            objs.append(PrecioSucursal(
                id_producto_id=prod.id,
                id_sucursal_id=suc.id,
                precio_venta=prod.precio_venta,
                vigente_desde=now,
                activo=True,
            ))
    if objs:
        PrecioSucursal.objects.bulk_create(objs)


def reverse_seed(apps, schema_editor):
    PrecioSucursal = apps.get_model('inventario', 'PrecioSucursal')
    PrecioSucursal.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0005_precio_sucursal'),
    ]

    operations = [
        migrations.RunPython(seed_precios, reverse_seed),
    ]
