from inventario.models import Stock
from producto.models import Producto
from ventas.models import DetalleVenta


def bloquear_productos(lineas, sucursal_id):
    """Bloquea productos y filas de stock en orden determinista (anti-deadlock)."""
    # Bloqueo determinista: ordena IDs para evitar deadlocks entre
    # transacciones concurrentes.
    ids_ordenados = sorted({ln["producto_id"] for ln in lineas})
    productos_qs = list(
        Producto.objects.select_for_update().filter(id__in=ids_ordenados)
    )
    productos = {p.id: p for p in productos_qs}
    # Serializar también las filas de stock de la sucursal para que dos
    # ventas concurrentes no lean el mismo stock a la vez.
    list(
        Stock.objects.select_for_update().filter(
            id_producto_id__in=ids_ordenados,
            id_sucursal_id=sucursal_id,
        )
    )
    return ids_ordenados, productos


def errores_de_stock(lineas, stocks, productos, sucursal_id):
    """Errores legibles por línea/por producto repetido que excede el stock."""
    errores = []
    # Acumula cantidades por producto para detectar el caso de producto
    # repetido que excede el stock en total.
    acumulado = {}
    for ln in lineas:
        acumulado[ln["producto_id"]] = acumulado.get(ln["producto_id"], 0) + ln["cantidad"]
    for ln in lineas:
        pid = ln["producto_id"]
        if stocks.get(pid, 0) == 0:
            nombre = productos[pid].nombre
            errores.append(
                f"Línea {ln['indice']} (producto {pid} '{nombre}'): "
                f"no disponible en la sucursal {sucursal_id} - stock 0"
            )
    for pid, total_pid in acumulado.items():
        if total_pid > stocks.get(pid, 0):
            indices = [str(ln["indice"]) for ln in lineas if ln["producto_id"] == pid]
            errores.append(
                f"Producto {pid} (líneas {', '.join(indices)}): "
                f"stock insuficiente: disponible {stocks.get(pid, 0)}, "
                f"solicitado {total_pid}"
            )
    return errores


def revertir_salidas(venta):
    """Devuelve el stock de todos los detalles de una venta (por cancelación)."""
    from inventario.services.movimiento_inventario_service import (
        MovimientoInventarioService,
    )

    detalles = list(
        DetalleVenta.objects.select_for_update().filter(
            id_venta_id=venta.id
        )
    )
    inventario_service = MovimientoInventarioService()
    for detalle in detalles:
        inventario_service.revertir_salida_por_venta(detalle)
