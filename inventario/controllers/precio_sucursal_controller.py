from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inventario.services.precio_sucursal_service import PrecioSucursalService
from repository.base_controller import BaseDetailController, BaseListController
from repository.exceptions import NotFoundError
from repository.permissions import (
    entero_o_none,
    es_staff,
    exigir_misma_sucursal,
    exigir_permiso,
    sucursal_de_usuario,
)

PERM_PRECIOS_LEER = "precios.leer"
PERM_PRECIOS_ESCRIBIR = "precios.escribir"
MSG_SIN_SUCURSAL = "El usuario no tiene una sucursal asignada"
MSG_ID_SUCURSAL_ENTERO = "id_sucursal debe ser entero"


class PrecioSucursalListCreateView(BaseListController):
    def __init__(self):
        super().__init__(PrecioSucursalService)

    def get(self, request) -> Response:
        exigir_permiso(request.user, PERM_PRECIOS_LEER)
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
            exigir_permiso(request.user, PERM_PRECIOS_ESCRIBIR)
            data = dict(request.data)
            if not es_staff(request.user):
                # Precios solo para la sucursal propia; otra -> 403,
                # formato inválido -> 400, ausente -> se deriva del JWT.
                if data.get("id_sucursal") is not None:
                    suc_id = entero_o_none(data.get("id_sucursal"))
                    if suc_id is None:
                        return Response(
                            {"error": MSG_ID_SUCURSAL_ENTERO},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    exigir_misma_sucursal(request.user, suc_id, "precios")
                    data["id_sucursal"] = suc_id
                else:
                    user_suc = sucursal_de_usuario(request.user)
                    if user_suc is None:
                        return Response(
                            {"error": MSG_SIN_SUCURSAL},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    data["id_sucursal"] = user_suc
            item = self.service.create(data)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PrecioSucursalDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(PrecioSucursalService)

    def _check_sucursal(self, request, pk):
        item = self.service.get_by_id(pk)
        exigir_misma_sucursal(request.user, item.get("id_sucursal"), "precios")

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
        err = self._autorizado_o_error(request, pk, PERM_PRECIOS_LEER)
        if err is not None:
            return err
        return super().get(request, pk)

    def put(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, PERM_PRECIOS_ESCRIBIR)
        if err is not None:
            return err
        try:
            data = dict(request.data)
            if not es_staff(request.user):
                # No mover precios entre sucursales.
                data.pop("id_sucursal", None)
            item = self.service.update(pk, data)
            return Response(item, status=status.HTTP_200_OK)
        except ValueError as e:
            # El 404 lo cubre el wrapper previo (get_by_id); aquí solo 400.
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk: int) -> Response:
        err = self._autorizado_o_error(request, pk, PERM_PRECIOS_ESCRIBIR)
        if err is not None:
            return err
        return super().delete(request, pk)


class PrecioActivoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        exigir_permiso(request.user, PERM_PRECIOS_LEER)
        producto_id = request.query_params.get('id_producto') or request.query_params.get('producto_id')
        sucursal_param = request.query_params.get('id_sucursal') or request.query_params.get('sucursal_id')
        if not es_staff(request.user):
            # Sucursal propia del JWT; el parámetro se ignora.
            user_suc = sucursal_de_usuario(request.user)
            if user_suc is None:
                return Response({"error": MSG_SIN_SUCURSAL}, status=status.HTTP_400_BAD_REQUEST)
            sucursal_id = user_suc
        else:
            if not sucursal_param:
                return Response({"error": "Debe enviar id_sucursal"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                sucursal_id = int(sucursal_param)
            except ValueError:
                return Response({"error": MSG_ID_SUCURSAL_ENTERO}, status=status.HTTP_400_BAD_REQUEST)
        if not producto_id:
            return Response({"error": "Debe enviar id_producto"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            producto_id = int(producto_id)
        except ValueError:
            return Response({"error": "id_producto debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)
        service = PrecioSucursalService()
        data = service.get_precio_activo(producto_id, sucursal_id)
        if not data:
            return Response({"error": "Precio no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response(data, status=status.HTTP_200_OK)


class HistorialPrecioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        exigir_permiso(request.user, PERM_PRECIOS_LEER)
        producto_id = request.query_params.get('id_producto') or request.query_params.get('producto_id')
        sucursal_param = request.query_params.get('id_sucursal') or request.query_params.get('sucursal_id')
        if not es_staff(request.user):
            # Sucursal propia del JWT; el parámetro se ignora.
            user_suc = sucursal_de_usuario(request.user)
            if user_suc is None:
                return Response({"error": MSG_SIN_SUCURSAL}, status=status.HTTP_400_BAD_REQUEST)
            sucursal_id = user_suc
        else:
            if not sucursal_param:
                return Response({"error": "Debe enviar id_sucursal"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                sucursal_id = int(sucursal_param)
            except ValueError:
                return Response({"error": MSG_ID_SUCURSAL_ENTERO}, status=status.HTTP_400_BAD_REQUEST)
        if not producto_id:
            return Response({"error": "Debe enviar id_producto"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            producto_id = int(producto_id)
        except ValueError:
            return Response({"error": "id_producto debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)
        service = PrecioSucursalService()
        data = service.get_historial(producto_id, sucursal_id)
        return Response(data, status=status.HTTP_200_OK)
