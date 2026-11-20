from rest_framework.response import Response
from repository.base_controller import BaseListController, BaseDetailController
from repository.exceptions import NotFoundError
from repository.permissions import (
    es_staff,
    exigir_misma_sucursal,
    exigir_permiso,
    resolver_id_sucursal,
    sucursal_de_usuario,
)

from inventario.services.movimiento_inventario_service import MovimientoInventarioService

PERM_MOVIMIENTO_VER = "inventario.ver"
PERM_MOVIMIENTO_ESCRIBIR = "inventario.escribir"
MSG_SIN_SUCURSAL = "El usuario no tiene una sucursal asignada"


class MovimientoInventarioListCreateView(BaseListController):
    permiso_get = PERM_MOVIMIENTO_VER
    permiso_post = PERM_MOVIMIENTO_ESCRIBIR

    def __init__(self):
        super().__init__(MovimientoInventarioService)

    def get(self, request) -> Response:
        exigir_permiso(request.user, self.permiso_get)
        if es_staff(request.user):
            return super().get(request)
        user_suc = sucursal_de_usuario(request.user)
        if user_suc is None:
            return Response({"error": MSG_SIN_SUCURSAL}, status=400)
        return Response(
            self.service.get_by_filters({"id_sucursal_id": user_suc}),
            status=200,
        )

    def post(self, request) -> Response:
        try:
            exigir_permiso(request.user, self.permiso_post)
            data = dict(request.data)
            suc_id = resolver_id_sucursal(request.user, data)
            if suc_id is not None:
                data["id_sucursal"] = suc_id
            item = self.service.create(data, user=request.user)
            return Response(item, status=201)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)


class MovimientoInventarioDetailView(BaseDetailController):
    permiso_get = PERM_MOVIMIENTO_VER
    permiso_put = PERM_MOVIMIENTO_ESCRIBIR
    permiso_delete = PERM_MOVIMIENTO_ESCRIBIR

    def __init__(self):
        super().__init__(MovimientoInventarioService)

    def _check_sucursal(self, request, pk):
        item = self.service.get_by_id(pk)
        exigir_misma_sucursal(request.user, item.get("id_sucursal"), "inventario")

    def _autorizado_o_error(self, request, pk, accion):
        try:
            exigir_permiso(request.user, accion)
            self._check_sucursal(request, pk)
            return None
        except NotFoundError as e:
            return Response({"error": str(e)}, status=404)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

    def get(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, self.permiso_get)
        if err is not None:
            return err
        return super().get(request, pk)

    def put(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, self.permiso_put)
        if err is not None:
            return err
        try:
            data = dict(request.data)
            if not es_staff(request.user):
                # No mover movimientos entre sucursales.
                data.pop("id_sucursal", None)
            item = self.service.update(pk, data, user=request.user)
            return Response(item, status=200)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

    def delete(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, self.permiso_delete)
        if err is not None:
            return err
        return super().delete(request, pk)
