from inventario.models import PrecioSucursal, Stock


class InventarioQueryService:
    """Consultas de catálogo de inventario por sucursal."""

    def get_inventario_por_sucursal(self, sucursal_id):
        """Catálogo agrupado por producto: {id_sucursal, detalles} con
        la misma forma de item que la versión anterior (Stock + precio
        activo por sucursal)."""
        precio_map = {
            ps.id_producto_id: ps
            for ps in PrecioSucursal.objects.filter(
                id_sucursal_id=sucursal_id, activo=True
            )
        }
        detalles = []
        for fila in Stock.objects.select_related("id_producto").filter(
            id_sucursal_id=sucursal_id
        ):
            producto = fila.id_producto
            ps = precio_map.get(producto.id)
            detalles.append(
                {
                    "id": fila.id,
                    "id_producto": producto.id,
                    "nombre": producto.nombre,
                    "clave": producto.clave,
                    "marca": producto.marca,
                    "codigo_barras": producto.codigo_barras,
                    "precio_venta": str(producto.precio_venta),
                    "precio_sucursal": str(ps.precio_venta) if ps else None,
                    "vigente_desde": ps.vigente_desde.isoformat() if ps and ps.vigente_desde else None,
                    "precio_base": str(producto.precio_venta),
                    "costo": str(producto.costo),
                    "cantidad": fila.cantidad,
                }
            )
        detalles.sort(key=lambda p: p["nombre"])
        return {"id_sucursal": sucursal_id, "detalles": detalles}
