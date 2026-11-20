from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from repository.base_controller import BaseListController, BaseDetailController
from repository.exceptions import NotFoundError
from repository.permissions import (
    entero_o_none,
    es_staff,
    exigir_misma_sucursal,
    exigir_permiso,
    resolver_id_sucursal,
    sucursal_de_usuario,
)

from inventario.services.movimiento_inventario_service import MovimientoInventarioService

PERM_INVENTARIO_ESCRIBIR = "inventario.escribir"
MSG_SIN_SUCURSAL = "El usuario no tiene una sucursal asignada"


def _sucursales_en_bulk(data):
    """Ids de sucursal mencionados en un payload bulk (común + por línea)."""
    if isinstance(data, list):
        items, comun = data, None
    elif isinstance(data, dict):
        items = data.get("items") or data.get("detalles") or []
        comun = data.get("id_sucursal")
    else:
        return set()
    ids = set()
    if comun is not None:
        ids.add(comun)
    for it in items:
        if isinstance(it, dict) and it.get("id_sucursal") is not None:
            ids.add(it["id_sucursal"])
    return ids


def _derivar_sucursal_bulk(data, user_suc):
    """Copia el payload bulk y rellena con la sucursal del perfil donde falte."""
    if isinstance(data, dict):
        data = dict(data)
        for key in ("items", "detalles"):
            if isinstance(data.get(key), list):
                data[key] = [
                    {**it, "id_sucursal": user_suc}
                    if isinstance(it, dict) and it.get("id_sucursal") is None
                    else it
                    for it in data[key]
                ]
        if data.get("id_sucursal") is None:
            data["id_sucursal"] = user_suc
        return data
    if isinstance(data, list):
        return [
            {**it, "id_sucursal": user_suc}
            if isinstance(it, dict) and it.get("id_sucursal") is None
            else it
            for it in data
        ]
    return data


class DetalleInventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(MovimientoInventarioService)

    def get(self, request) -> Response:
        exigir_permiso(request.user, "inventario.ver")
        if es_staff(request.user):
            return super().get(request)
        user_suc = sucursal_de_usuario(request.user)
        if user_suc is None:
            return Response(
                {"error": MSG_SIN_SUCURSAL},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            self.service.get_by_filters({"id_sucursal_id": user_suc}),
            status=status.HTTP_200_OK,
        )

    def post(self, request) -> Response:
        try:
            exigir_permiso(request.user, PERM_INVENTARIO_ESCRIBIR)
            data = dict(request.data)
            suc_id = resolver_id_sucursal(request.user, data)
            if suc_id is not None:
                data["id_sucursal"] = suc_id
            item = self.service.create(data, user=request.user)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DetalleInventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(MovimientoInventarioService)

    def _check_sucursal(self, request, pk):
        item = self.service.get_by_id(pk)
        exigir_misma_sucursal(
            request.user,
            item.get("id_sucursal"),
            "detalle de inventario",
        )

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
        err = self._autorizado_o_error(request, pk, "inventario.ver")
        if err is not None:
            return err
        return super().get(request, pk)

    def put(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, PERM_INVENTARIO_ESCRIBIR)
        if err is not None:
            return err
        try:
            data = dict(request.data)
            if not es_staff(request.user):
                # No mover movimientos entre sucursales.
                data.pop("id_sucursal", None)
            item = self.service.update(pk, data)
            return Response(item, status=status.HTTP_200_OK)
        except ValueError as e:
            # El 404 lo cubre el wrapper previo (get_by_id); aquí solo 400.
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, PERM_INVENTARIO_ESCRIBIR)
        if err is not None:
            return err
        return super().delete(request, pk)


class DetalleInventarioBulkCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            exigir_permiso(request.user, PERM_INVENTARIO_ESCRIBIR)
            service = MovimientoInventarioService()
            data = request.data
            if not es_staff(request.user):
                user_suc = sucursal_de_usuario(request.user)
                if user_suc is None:
                    return Response(
                        {"error": MSG_SIN_SUCURSAL},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                data = _derivar_sucursal_bulk(data, user_suc)
                # Validación línea por línea vía sucursales mencionadas.
                for suc_id in _sucursales_en_bulk(data):
                    ent = entero_o_none(suc_id)
                    if ent is None:
                        return Response(
                            {"error": "id_sucursal debe ser entero"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    exigir_misma_sucursal(request.user, ent, "inventario")
            resultados = service.bulk_create(data, user=request.user)
            return Response(resultados, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
