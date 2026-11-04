from inventario.models import MovimientoInventario


def signo(tipo):
    return 1 if tipo == MovimientoInventario.TipoMovimiento.ENTRADA else -1


def movimiento_to_dict(instance):
    if not instance:
        return None
    return {
        "id": instance.id,
        "tipo": instance.tipo,
        "cantidad": instance.cantidad,
        "fecha": instance.fecha.isoformat() if instance.fecha else None,
        "razon": instance.razon,
        "observaciones": instance.observaciones,
        "id_producto": instance.id_producto_id,
        "id_sucursal": instance.id_sucursal_id,
        "id_usuario": instance.id_usuario_id,
        "id_proveedor": instance.id_proveedor_id,
        "id_detalle_venta": instance.id_detalle_venta_id,
    }


def programar_alerta(producto_id, sucursal_id):
    """Programa la evaluación de alertas de stock tras el commit.

    Importación diferida para no acoplar el inventario a la app de
    notificaciones a nivel de módulo. La evaluación corre en on_commit y
    sus fallos solo quedan en el log (ver stock_alerts).
    """
    from notifications.services.stock_alerts import programar_evaluacion

    programar_evaluacion(producto_id, sucursal_id)
