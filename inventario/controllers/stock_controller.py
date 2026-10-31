from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from repository.permissions import entero_o_none, es_staff, exigir_permiso, sucursal_de_usuario

from inventario.repositories.stock_repository import StockRepository

PERM_INVENTARIO_VER = "inventario.ver"
PERM_INVENTARIO_ESCRIBIR = "inventario.escribir"
MSG_SIN_SUCURSAL = "El usuario no tiene una sucursal asignada"


def _fila_a_dict(fila):
    return {
        "id": fila.id,
        "id_sucursal": fila.id_sucursal_id,
        "id_producto": fila.id_producto_id,
        "cantidad": fila.cantidad,
    }


class StockListView(APIView):
    """GET /api/stock/?sucursal_id= — balance por (sucursal, producto).

    Solo lectura: los ajustes se operan vía movimientos.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        exigir_permiso(request.user, PERM_INVENTARIO_VER)
        repo = StockRepository()
        if not es_staff(request.user):
            user_suc = sucursal_de_usuario(request.user)
            if user_suc is None:
                return Response(
                    {"error": MSG_SIN_SUCURSAL},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            filas = repo.filter({"id_sucursal_id": user_suc})
        else:
            filtros = {}
            param = request.query_params.get("sucursal_id")
            if param is not None:
                suc_id = entero_o_none(param)
                if suc_id is None:
                    return Response(
                        {"error": "sucursal_id debe ser entero"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                filtros["id_sucursal_id"] = suc_id
            filas = repo.filter(filtros)
        return Response([_fila_a_dict(f) for f in filas], status=status.HTTP_200_OK)
