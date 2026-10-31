from ventas.models import Venta
from repository.exceptions import NotFoundError


class VentaTicketService:

    def get_ticket(self, venta_id):
        venta_obj = (
            Venta.objects
            .select_related(
                "id_usuario",
                "id_metodo_pago",
                "id_sucursal",
            )
            .prefetch_related(
                "detalleventa_set__id_producto"
            )
            .filter(id=venta_id)
            .first()
        )

        if not venta_obj:
            raise NotFoundError(
                f"Venta con id {venta_id} no encontrada"
            )

        productos = []

        for detalle in venta_obj.detalleventa_set.all():
            precio_unitario = (
                detalle.subtotal / detalle.cantidad
                if detalle.cantidad > 0
                else 0
            )

            productos.append({
                "nombre": detalle.id_producto.nombre,
                "cantidad": detalle.cantidad,
                "precio_unitario": str(precio_unitario),
                "subtotal": str(detalle.subtotal),
            })

        return {
            "folio": venta_obj.id,
            "fecha": (
                venta_obj.fecha.isoformat()
                if venta_obj.fecha
                else None
            ),
            "vendedor": (
                venta_obj.id_usuario.username
                if venta_obj.id_usuario
                else None
            ),
            "metodo_pago": (
                venta_obj.id_metodo_pago.tipo
                if venta_obj.id_metodo_pago
                else None
            ),
            "sucursal": (
                str(venta_obj.id_sucursal)
                if venta_obj.id_sucursal
                else None
            ),
            "productos": productos,
            "total": str(venta_obj.total),
        }