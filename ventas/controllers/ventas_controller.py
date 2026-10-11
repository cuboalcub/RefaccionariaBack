from rest_framework import status
from rest_framework.response import Response

from repository.exceptions import NotFoundError
from repository.permissions import (
    es_staff,
    exigir_misma_sucursal,
    exigir_permiso,
    sucursal_de_usuario,
)
from ventas.services.ventas_services import VentaService
from repository.base_controller import BaseListController, BaseDetailController


class VentasListController(BaseListController):
    def __init__(self):
        super().__init__(VentaService)

    def get(self, request) -> Response:
        try:
            exigir_permiso(request.user, "ventas.vender")
            page_param = request.query_params.get("page")
            page_size_param = request.query_params.get("page_size", 10)
            sucursal_param = request.query_params.get("sucursal_id")

            staff = es_staff(request.user)

            sucursal_id = None
            if sucursal_param is not None:
                try:
                    sucursal_id = int(sucursal_param)
                except ValueError:
                    return Response({"error": "sucursal_id debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)

            if not staff:
                # Usuario normal: forzar su propia sucursal (seguridad: no ve otras sucursales)
                try:
                    user_sucursal_id = sucursal_de_usuario(request.user)
                    if user_sucursal_id is None:
                        return Response(
                            {"error": "El usuario no tiene una sucursal asignada"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    sucursal_id = user_sucursal_id
                except Exception as e:
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            if page_param is not None:
                try:
                    page = int(page_param)
                    page_size = int(page_size_param)
                except ValueError:
                    return Response({"error": "page y page_size deben ser enteros"}, status=status.HTTP_400_BAD_REQUEST)
                data = self.service.get_all(
                    page=page, page_size=page_size,
                    sucursal_id=sucursal_id,
                )
            else:
                data = self.service.get_all(sucursal_id=sucursal_id)
            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request) -> Response:
        try:
            # id_usuario e id_inventario nunca vienen del cliente: el usuario
            # sale del JWT y el inventario se resuelve server-side.
            # staff/superuser puede enviar sucursal_id como override explícito.
            exigir_permiso(request.user, "ventas.vender")
            data = dict(request.data)
            data.pop("id_usuario", None)
            data.pop("id_inventario", None)
            if not es_staff(request.user):
                data.pop("sucursal_id", None)
            # Camino atómico (Bug B): si trae "detalles", cabecera + líneas
            # en una sola transacción todo-o-nada. Camino legacy sin cambios.
            # Los errores por línea llegan como ValueError -> 400 con detalle.
            if isinstance(data.get("detalles"), list) and data["detalles"]:
                item = self.service.crear_venta_completa(data, user=request.user)
                return Response(item, status=status.HTTP_201_CREATED)
            item = self.service.create(data, user=request.user)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VentasDetailController(BaseDetailController):
    def __init__(self):
        super().__init__(VentaService)

    def _check_sucursal(self, request, pk):
        """403 si un usuario no-staff opera una venta de otra sucursal."""
        item = self.service.get_by_id(pk)
        exigir_misma_sucursal(request.user, item.get("id_sucursal"), "ventas")

    def _autorizado_o_error(self, request, pk, accion):
        try:
            exigir_permiso(request.user, accion)
            self._check_sucursal(request, pk)
            return None
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
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
        return super().put(request, pk)

    def delete(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, "ventas.anular")
        if err is not None:
            return err
        return super().delete(request, pk)


