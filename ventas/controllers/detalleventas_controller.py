from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from repository.base_controller import BaseDetailController, BaseListController
from repository.exceptions import NotFoundError
from ventas.controllers.ventas_controller import _sucursal_de_usuario
from ventas.models import detalleVenta
from ventas.services.detalleventa_service import DetalleVentaService


class DetalleVentaListCreate(BaseListController):
    def __init__(self):
        super().__init__(DetalleVentaService)

    def post(self, request) -> Response:
        try:
            # Pasar request.user para validación de sucursal
            item = self.service.create(request.data, user=request.user)
            return Response(item, status=status.HTTP_201_CREATED)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DetalleVentaDetail(BaseDetailController):
    def __init__(self):
        super().__init__(DetalleVentaService)

    def _check_sucursal(self, request, pk):
        """403 si un usuario no-staff opera un detalle de otra sucursal."""
        if getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False):
            return
        det = detalleVenta.objects.select_related(
            "id_venta__id_inventario__id_sucursal"
        ).filter(id=pk).first()
        if det is None:
            return
        inv = det.id_venta.id_inventario if det.id_venta else None
        venta_suc = inv.id_sucursal_id if inv else None
        user_suc = _sucursal_de_usuario(request.user)
        if user_suc is None:
            raise ValueError("El usuario no tiene una sucursal asignada")
        if venta_suc is not None and venta_suc != user_suc:
            raise PermissionDenied("No tiene acceso a detalles de otra sucursal")

    def _autorizado_o_error(self, request, pk):
        try:
            self._check_sucursal(request, pk)
            return None
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk)
        if err is not None:
            return err
        return super().get(request, pk)

    def put(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk)
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
        err = self._autorizado_o_error(request, pk)
        if err is not None:
            return err
        return super().delete(request, pk)