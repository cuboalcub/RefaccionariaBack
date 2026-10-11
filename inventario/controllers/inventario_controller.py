from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from repository.base_controller import BaseListController, BaseDetailController
from repository.exceptions import NotFoundError
from repository.permissions import (
    entero_o_none,
    es_staff,
    exigir_misma_sucursal,
    exigir_permiso,
    sucursal_de_usuario,
)

from inventario.services.inventario_service import InventarioService
from inventario.services.detalle_inventario_service import DetalleInventarioService


class InventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(InventarioService)

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
        return Response(
            self.service.get_by_filters({"id_sucursal_id": user_suc}),
            status=status.HTTP_200_OK,
        )

    def post(self, request) -> Response:
        try:
            exigir_permiso(request.user, "inventario.admin")
            data = dict(request.data)
            if not es_staff(request.user):
                # Crear solo en la sucursal propia; otra sucursal -> 403,
                # formato inválido -> 400, ausente -> se deriva del JWT.
                if data.get("id_sucursal") is not None:
                    suc_id = entero_o_none(data.get("id_sucursal"))
                    if suc_id is None:
                        return Response(
                            {"error": "id_sucursal debe ser entero"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    exigir_misma_sucursal(request.user, suc_id, "inventario")
                    data["id_sucursal"] = suc_id
                else:
                    user_suc = sucursal_de_usuario(request.user)
                    if user_suc is None:
                        return Response(
                            {"error": "El usuario no tiene una sucursal asignada"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    data["id_sucursal"] = user_suc
            item = self.service.create(data)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(InventarioService)

    def _check_sucursal(self, request, pk):
        item = self.service.get_by_id(pk)
        exigir_misma_sucursal(request.user, item.get("id_sucursal"), "inventario")

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
        err = self._autorizado_o_error(request, pk, "inventario.admin")
        if err is not None:
            return err
        try:
            data = dict(request.data)
            if not es_staff(request.user):
                # No mover inventarios entre sucursales.
                data.pop("id_sucursal", None)
            item = self.service.update(pk, data)
            return Response(item, status=status.HTTP_200_OK)
        except ValueError as e:
            # El 404 lo cubre el wrapper previo (get_by_id); aquí solo 400.
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, "inventario.admin")
        if err is not None:
            return err
        return super().delete(request, pk)


class InventarioPorSucursalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        exigir_permiso(request.user, "inventario.ver")
        perfil = getattr(request.user, "perfil", None)
        if not perfil or not perfil.id_sucursal_id:
            return Response(
                {"error": "El usuario no tiene una sucursal asignada"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = DetalleInventarioService().get_inventario_por_sucursal(perfil.id_sucursal_id)

        # Paginación opcional: ?page=1&page_size=10
        page_param = request.query_params.get("page")
        if page_param is not None:
            try:
                page = int(page_param)
                page_size = int(request.query_params.get("page_size", 10))
            except ValueError:
                return Response({"error": "page y page_size deben ser enteros"}, status=status.HTTP_400_BAD_REQUEST)
            if page < 1 or page_size < 1:
                return Response({"error": "page y page_size deben ser >= 1"}, status=status.HTTP_400_BAD_REQUEST)

            # Aplanar detalles para paginar si hay un solo inventario, sino paginar por inventario
            # Si hay múltiples inventarios, paginamos cada uno y retornamos estructura paginada
            if len(data) == 1:
                inv = data[0]
                total = len(inv["detalles"])
                total_pages = (total + page_size - 1) // page_size if total else 1
                if page > total_pages and total > 0:
                    return Response({"error": f"page fuera de rango (1-{total_pages})"}, status=status.HTTP_400_BAD_REQUEST)
                start = (page - 1) * page_size
                end = start + page_size
                paginated = inv["detalles"][start:end]
                return Response({
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "id_inventario": inv["id_inventario"],
                    "descripcion": inv["descripcion"],
                    "id_sucursal": inv["id_sucursal"],
                    "detalles": paginated,
                }, status=status.HTTP_200_OK)
            else:
                # Múltiples inventarios: paginar lista de inventarios
                total = len(data)
                total_pages = (total + page_size - 1) // page_size
                if page > total_pages and total > 0:
                    return Response({"error": f"page fuera de rango (1-{total_pages})"}, status=status.HTTP_400_BAD_REQUEST)
                start = (page - 1) * page_size
                end = start + page_size
                paginated_data = data[start:end]
                return Response({
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "results": paginated_data,
                }, status=status.HTTP_200_OK)

        return Response(data, status=status.HTTP_200_OK)
