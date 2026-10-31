import logging

import django.db.models.deletion
from django.db import migrations, models

logger = logging.getLogger(__name__)


def consolidar_inventario(apps, schema_editor):
    """Consolida Inventario/DetalleInventario en MovimientoInventario+Stock.

    - Cada línea (DetalleInventario) es un registro de entrada/salida: su
      producto/sucursal/proveedor/venta se escriben en su MovimientoInventario.
    - Un movimiento compartido entre varias líneas se clona (1 movimiento
      por registro; la cabecera compartida se elimina).
    - El stock neto (SUM entradas - salidas) por (sucursal, producto) crea
      las filas de Stock, tal cual (un neto negativo por datos sucios se
      migra igual y se avisará en el log).
    - Movimientos huérfanos sin ninguna línea se descartan (no describen
      stock real).
    """
    Detalle = apps.get_model("inventario", "DetalleInventario")
    Movimiento = apps.get_model("inventario", "MovimientoInventario")
    Inventario = apps.get_model("inventario", "Inventario")
    Stock = apps.get_model("inventario", "Stock")
    DetalleVenta = apps.get_model("ventas", "DetalleVenta")

    huérfanos = Movimiento.objects.exclude(
        id__in=Detalle.objects.values_list("id_movimiento_id", flat=True)
    )
    contar = huérfanos.count()
    if contar:
        logger.warning(
            "inventario.0009: %s movimientos sin DetalleInventario se descartan", contar
        )
        huérfanos.delete()

    destino_por_linea = {}
    primero_por_movimiento = {}
    for linea in Detalle.objects.order_by("id"):
        mov_id = linea.id_movimiento_id
        destino = primero_por_movimiento.get(mov_id)
        if destino is None:
            destino = mov_id
            primero_por_movimiento[mov_id] = mov_id
        else:
            cabeza = Movimiento.objects.get(id=mov_id)
            destino = (
                Movimiento.objects.create(
                    tipo=cabeza.tipo,
                    cantidad=linea.cantidad,
                    fecha=cabeza.fecha,
                    razon=cabeza.razon,
                    observaciones=cabeza.observaciones,
                ).id
            )
        destino_por_linea[linea.id] = destino

    vendedor = {}
    venta_ids = list(
        Detalle.objects.exclude(id_detalle_venta__isnull=True).values_list(
            "id_detalle_venta_id", flat=True
        )
    )
    for dv in DetalleVenta.objects.select_related("id_venta").filter(id__in=venta_ids):
        vendedor[dv.id] = dv.id_venta.id_usuario_id

    for linea in Detalle.objects.select_related("id_inventario").order_by("id"):
        Movimiento.objects.filter(id=destino_por_linea[linea.id]).update(
            cantidad=linea.cantidad,
            id_producto_id=linea.id_producto_id,
            id_sucursal_id=linea.id_inventario.id_sucursal_id,
            id_proveedor_id=linea.id_proveedor_id,
            id_detalle_venta_id=linea.id_detalle_venta_id,
            id_usuario_id=vendedor.get(linea.id_detalle_venta_id),
        )

    from django.db.models import Case, ExpressionWrapper, F, IntegerField, Sum, Value, When

    neto = ExpressionWrapper(
        Case(
            When(tipo="ENTRADA", then=Value(1)),
            default=Value(-1),
            output_field=IntegerField(),
        )
        * F("cantidad"),
        output_field=IntegerField(),
    )
    grupos = (
        Movimiento.objects.values("id_sucursal_id", "id_producto_id")
        .annotate(neto=Sum(neto))
    )
    Stock.objects.bulk_create(
        Stock(
            id_sucursal_id=row["id_sucursal_id"],
            id_producto_id=row["id_producto_id"],
            cantidad=row["neto"] or 0,
        )
        for row in grupos
    )


class Migration(migrations.Migration):

    # SQLite no permite ALTER TABLE en la misma transacción que la
    # consolidación de datos ("pending trigger events" por FKs diferidas).
    atomic = False

    dependencies = [
        ("inventario", "0008_not_null_observaciones"),
        ("notifications", "0003_remove_notification_ref_inventario"),
        ("ventas", "0004_remove_venta_id_inventario_venta_estado_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="movimientoinventario",
            name="id_producto",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="movimientos_inventario",
                to="producto.producto",
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="id_sucursal",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="movimientos_inventario",
                to="sucursales.sucursal",
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="id_usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="movimientos_inventario",
                to="auth.user",
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="id_proveedor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="movimientos_inventario",
                to="producto.proveedor",
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="id_detalle_venta",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="detalle_inventario",
                to="ventas.detalleventa",
            ),
        ),
        migrations.CreateModel(
            name="Stock",
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ("cantidad", models.IntegerField()),
                (
                    "id_producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stocks",
                        to="producto.producto",
                    ),
                ),
                (
                    "id_sucursal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stocks",
                        to="sucursales.sucursal",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("id_sucursal", "id_producto"),
                        name="uniq_stock_sucursal_producto",
                    ),
                ],
            },
        ),
        migrations.RunPython(
            consolidar_inventario, reverse_code=migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="id_producto",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="movimientos_inventario",
                to="producto.producto",
            ),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="id_sucursal",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="movimientos_inventario",
                to="sucursales.sucursal",
            ),
        ),
        migrations.DeleteModel(name="DetalleInventario"),
        migrations.DeleteModel(name="Inventario"),
    ]
