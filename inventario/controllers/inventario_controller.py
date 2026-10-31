from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from repository.permissions import exigir_permiso

from inventario.services.movimiento_inventario_service import MovimientoInventarioService

PERM_INVENTARIO_VER = "inventario.ver"
MSG_SIN_SUCURSAL = "El usuario no tiene una sucursal asignada"


class InventarioPorSucursalView(APIView):
    """GET /api/inventarios/mi-sucursal/ — catálogo del stock de la sucursal
    del usuario ({id_sucursal, detalles}) con paginación opcional."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        exigir_permiso(request.user, PERM_INVENTARIO_VER)
        perfil = getattr(request.user, "perfil", None)
        if not perfil or not perfil.id_sucursal_id:
            return Response(
                {"error": MSG_SIN_SUCURSAL},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = MovimientoInventarioService().get_inventario_por_sucursal(
            perfil.id_sucursal_id
        )
        page_param = request.query_params.get("page")
        if page_param is None:
            return Response(data, status=status.HTTP_200_OK)
        try:
            page, page_size = self._leer_paginacion(request, page_param)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return self._paginar(data, page, page_size)

    @staticmethod
    def _leer_paginacion(request, page_param):
        try:
            page = int(page_param)
            page_size = int(request.query_params.get("page_size", 10))
        except ValueError:
            raise ValueError("page y page_size deben ser enteros")
        if page < 1 or page_size < 1:
            raise ValueError("page y page_size deben ser >= 1")
        return page, page_size

    @staticmethod
    def _paginar(data, page, page_size):
        total = len(data["detalles"])
        total_pages = (total + page_size - 1) // page_size if total else 1
        if page > total_pages and total > 0:
            return Response({"error": f"page fuera de rango (1-{total_pages})"}, status=status.HTTP_400_BAD_REQUEST)
        start = (page - 1) * page_size
        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "id_sucursal": data["id_sucursal"],
            "detalles": data["detalles"][start:start + page_size],
        }, status=status.HTTP_200_OK)
