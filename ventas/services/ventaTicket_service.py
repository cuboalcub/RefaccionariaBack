from ventas.models import venta
from repository.exceptions import NotFoundError


class VentaTicketService:

    def get_ticket(self, venta_id):
        venta_obj = venta.objects.filter(id=venta_id).first()

        if not venta_obj:
            raise NotFoundError(
                f"Venta con id {venta_id} no encontrada"
            )

        return {
            "folio": venta_obj.id,
            "fecha": venta_obj.fecha.isoformat() if venta_obj.fecha else None,
            "total": str(venta_obj.total),
        }