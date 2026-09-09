from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from repository.base_controller import BaseListController, BaseDetailController

from inventario.services.inventario_service import InventarioService
from inventario.services.detalle_inventario_service import DetalleInventarioService


class InventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(InventarioService)


class InventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(InventarioService)


class InventarioPorSucursalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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
