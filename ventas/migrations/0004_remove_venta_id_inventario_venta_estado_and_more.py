import django.db.models.deletion
from django.db import migrations, models


def copiar_sucursal_desde_inventario(apps, schema_editor):
    """Copia de datos: id_sucursal = id_inventario -> inventario.id_sucursal.

    Ventas sin id_inventario quedan con id_sucursal NULL (mismo estado de
    incertidumbre que ya tenían)."""
    Venta = apps.get_model('ventas', 'Venta')
    Inventario = apps.get_model('inventario', 'Inventario')
    inventarios = {inv.id: inv.id_sucursal_id for inv in Inventario.objects.only('id', 'id_sucursal')}
    for venta in Venta.objects.filter(id_inventario__isnull=False).only('id', 'id_inventario_id'):
        venta.id_sucursal_id = inventarios.get(venta.id_inventario_id)
        venta.save(update_fields=['id_sucursal'])


def deshacer_copia(apps, schema_editor):
    # No reversible: la columna id_inventario ya no existiría al volver.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0007_alter_detalleinventario_id_detalle_venta'),
        ('clientes', '0002_not_null_textos'),
        ('sucursales', '0003_sucursal_optional_fields'),
        ('ventas', '0003_rename_id_metodopago_venta_id_metodo_pago'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='estado',
            field=models.CharField(choices=[('completada', 'Completada'), ('cancelada', 'Cancelada')], default='completada', max_length=10),
        ),
        migrations.AddField(
            model_name='venta',
            name='id_cliente',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ventas', to='clientes.cliente'),
        ),
        migrations.AddField(
            model_name='venta',
            name='id_sucursal',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ventas', to='sucursales.sucursal'),
        ),
        # Copia id_inventario -> id_sucursal antes de tirar la columna.
        migrations.RunPython(copiar_sucursal_desde_inventario, deshacer_copia),
        migrations.RemoveField(
            model_name='venta',
            name='id_inventario',
        ),
    ]
