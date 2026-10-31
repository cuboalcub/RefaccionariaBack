from rest_framework import status
from rest_framework.response import Response

from repository.base_controller import BaseDetailController, BaseListController
from repository.exceptions import NotFoundError
from repository.permissions import exigir_misma_sucursal, exigir_permiso
from ventas.models import DetalleVenta
from ventas.services.detalle_venta_service import DetalleVentaService


class DetalleVentaListCreate(BaseListController):
    permiso_get = "ventas.vender"

    def __init__(self):
        super().__init__(DetalleVentaService)

    def post(self, request) -> Response:
        # Creación deprecada (Fase 3): la venta parcial por pasos dejaba
        # totales inconsistentes y permitía oversell. Crear siempre con
        # POST /api/ventas/ {"detalles": [...]} (todo o nada).
        # GET/PUT/DELETE por unidad siguen vigentes.
        return Response(
            {"error": "Crear detalles por separado está deprecado. Use POST /api/ventas/ con 'detalles'."},
            status=status.HTTP_410_GONE,
        )


class DetalleVentaDetail(BaseDetailController):
    def __init__(self):
        super().__init__(DetalleVentaService)

    def _check_sucursal(self, request, pk):
        """403 si un usuario no-staff opera un detalle de otra sucursal."""
        det = DetalleVenta.objects.select_related(
            "id_venta__id_sucursal"
        ).filter(id=pk).first()
        if det is None:
            return
        sucursal_id = (
            det.id_venta.id_sucursal_id if det.id_venta else None
        )
        exigir_misma_sucursal(request.user, sucursal_id, "detalles")

    def _autorizado_o_error(self, request, pk, accion):
        try:
            exigir_permiso(request.user, accion)
            self._check_sucursal(request, pk)
            return None
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, "ventas.vender")
        if err is not None:
            return err
        return super().get(request, pk)

    def put(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, "ventas.anular")
        if err is not None:
            return err
        try:
            item = self.service.update(pk, request.data, user=request.user)
            return Response(item, status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, "ventas.anular")
        if err is not None:
            return err
        return super().delete(request, pk)