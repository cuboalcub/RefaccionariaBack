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
    sucursal_de_usuario,
)

from inventario.models import Inventario
from inventario.services.detalle_inventario_service import DetalleInventarioService


def _sucursal_de_inventario(inventario_id):
    """Sucursal del inventario o None si no existe."""
    inv = Inventario.objects.filter(id=inventario_id).first()
    return inv.id_sucursal_id if inv else None


def _inventarios_en_bulk(data):
    """Ids de inventario mencionados en un payload bulk (común + por línea)."""
    if isinstance(data, list):
        items, comun = data, None
    elif isinstance(data, dict):
        items = data.get("items") or data.get("detalles") or []
        comun = data.get("id_inventario")
    else:
        return set()
    ids = set()
    if comun is not None:
        ids.add(comun)
    for it in items:
        if isinstance(it, dict) and it.get("id_inventario") is not None:
            ids.add(it["id_inventario"])
    return ids


class DetalleInventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(DetalleInventarioService)

    def get(self, request) -> Response:
        exigir_permiso(request.user, "inventario.ver")
        if es_staff(request.user):
            return super().get(request)
        user_suc = sucursal_de_usuario(request.user)
        if user_suc is None:
            return Response(
                {"error": "El usuario no tiene una sucursal asignada"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        inv_ids = list(
            Inventario.objects.filter(id_sucursal_id=user_suc).values_list(
                "id", flat=True
            )
        )
        return Response(
            self.service.get_by_filters({"id_inventario_id__in": inv_ids}),
            status=status.HTTP_200_OK,
        )

    def post(self, request) -> Response:
        try:
            exigir_permiso(request.user, "inventario.escribir")
            data = dict(request.data)
            if not es_staff(request.user) and data.get("id_inventario") is not None:
                inv_id = entero_o_none(data.get("id_inventario"))
                if inv_id is None:
                    return Response(
                        {"error": "id_inventario debe ser entero"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                exigir_misma_sucursal(
                    request.user, _sucursal_de_inventario(inv_id), "inventario"
                )
                data["id_inventario"] = inv_id
            item = self.service.create(data)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DetalleInventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(DetalleInventarioService)

    def _check_sucursal(self, request, pk):
        item = self.service.get_by_id(pk)
        exigir_misma_sucursal(
            request.user,
            _sucursal_de_inventario(item.get("id_inventario")),
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
        err = self._autorizado_o_error(request, pk, "inventario.escribir")
        if err is not None:
            return err
        try:
            data = dict(request.data)
            if not es_staff(request.user):
                # No mover detalles entre inventarios.
                data.pop("id_inventario", None)
            item = self.service.update(pk, data)
            return Response(item, status=status.HTTP_200_OK)
        except ValueError as e:
            # El 404 lo cubre el wrapper previo (get_by_id); aquí solo 400.
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, "inventario.escribir")
        if err is not None:
            return err
        return super().delete(request, pk)


class DetalleInventarioBulkCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            exigir_permiso(request.user, "inventario.escribir")
            service = DetalleInventarioService()
            # Soporta lista plana o dict con items/detalles
            data = request.data
            if not es_staff(request.user):
                # Validación línea por línea vía inventarios mencionados.
                for inv_id in _inventarios_en_bulk(data):
                    ent = entero_o_none(inv_id)
                    if ent is None:
                        return Response(
                            {"error": "id_inventario debe ser entero"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    exigir_misma_sucursal(
                        request.user, _sucursal_de_inventario(ent), "inventario"
                    )
            resultados = service.bulk_create(data)
            return Response(resultados, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
