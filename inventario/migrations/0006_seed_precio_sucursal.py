from django.db import migrations
from django.utils import timezone


def seed_precios(apps, schema_editor):
    producto = apps.get_model('producto', 'Producto')
    sucursal = apps.get_model('sucursales', 'Sucursal')
    precio_sucursal = apps.get_model('inventario', 'PrecioSucursal')
    productos = list(producto.objects.all())
    sucursales = list(sucursal.objects.all())
    if not productos or not sucursales:
        return
    now = timezone.now()
    objs = []
    for prod in productos:
        for suc in sucursales:
            if precio_sucursal.objects.filter(id_producto_id=prod.id, id_sucursal_id=suc.id, activo=True).exists():
                continue
            objs.append(precio_sucursal(
                id_producto_id=prod.id,
                id_sucursal_id=suc.id,
                precio_venta=prod.precio_venta,
                vigente_desde=now,
                activo=True,
            ))
    if objs:
        precio_sucursal.objects.bulk_create(objs)


def reverse_seed(apps, schema_editor):
    precio_sucursal = apps.get_model('inventario', 'PrecioSucursal')
    precio_sucursal.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0005_precio_sucursal'),
    ]

    operations = [
        migrations.RunPython(seed_precios, reverse_seed),
    ]
