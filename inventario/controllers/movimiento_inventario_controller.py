from rest_framework.response import Response
from repository.base_controller import BaseListController, BaseDetailController
from repository.exceptions import NotFoundError
from repository.permissions import exigir_permiso

from inventario.services.movimiento_inventario_service import MovimientoInventarioService

PERM_MOVIMIENTO_VER = "inventario.ver"
PERM_MOVIMIENTO_ESCRIBIR = "inventario.escribir"


class MovimientoInventarioListCreateView(BaseListController):
    permiso_get = PERM_MOVIMIENTO_VER
    permiso_post = PERM_MOVIMIENTO_ESCRIBIR

    def __init__(self):
        super().__init__(MovimientoInventarioService)

    def post(self, request) -> Response:
        try:
            exigir_permiso(request.user, self.permiso_post)
            item = self.service.create(request.data, user=request.user)
            return Response(item, status=201)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)


class MovimientoInventarioDetailView(BaseDetailController):
    permiso_get = PERM_MOVIMIENTO_VER
    permiso_put = PERM_MOVIMIENTO_ESCRIBIR
    permiso_delete = PERM_MOVIMIENTO_ESCRIBIR

    def __init__(self):
        super().__init__(MovimientoInventarioService)

    def put(self, request, pk: int) -> Response:
        try:
            exigir_permiso(request.user, self.permiso_put)
            item = self.service.update(pk, request.data, user=request.user)
            return Response(item, status=200)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=404)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

    def delete(self, request, pk: int) -> Response:
        try:
            exigir_permiso(request.user, self.permiso_delete)
            item = self.service.delete(pk, user=request.user)
            return Response(item, status=200)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=404)
