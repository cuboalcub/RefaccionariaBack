from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from repository.base_controller import BaseListController
from repository.base_controller import BaseDetailController

from producto.services.producto_service import ProductoService
from repository.permissions import exigir_permiso

PERMISO_CATALOGOS_LEER = "catalogos.leer"


class ProductoListCreateView(BaseListController):
    permiso_post = "catalogos.crear"

    def __init__(self):
        super().__init__(ProductoService)

    def get(self, request):
        exigir_permiso(request.user, PERMISO_CATALOGOS_LEER)
        params = request.query_params
        page_size = int(params.get("page_size", 10))
        kwargs, error = self._construir_kwargs(params)
        if error:
            return error
        return self._obtener(params.get("page"), page_size, kwargs)

    def _obtener(self, page_param, page_size, kwargs):
        try:
            if page_param is not None:
                data = self.service.get_all(page=int(page_param), page_size=page_size, **kwargs)
            else:
                data = self.service.get_all(**kwargs)
            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _texto(params, campo):
        valor = params.get(campo)
        return {campo: valor} if valor else {}

    @staticmethod
    def _entero(params, campo, alternativo=None):
        valor = params.get(campo)
        if alternativo is not None and valor in (None, ""):
            valor = params.get(alternativo)
        if valor is None:
            return {}, None
        try:
            return {campo: int(valor)}, None
        except ValueError:
            return None, Response({"error": f"{campo} debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)

    def _construir_kwargs(self, params):
        kwargs = {}
        for campo in ("search", "clave", "marca", "codigo_barras"):
            kwargs.update(self._texto(params, campo))
        for campo, alternativo in (
            ("sucursal_id", None),
            ("tipo_id", "id_tipo"),
            ("proveedor_id", "id_proveedor"),
        ):
            parte, error = self._entero(params, campo, alternativo)
            if error:
                return None, error
            kwargs.update(parte)
        return kwargs, None


class ProductoPorCodigoBarrasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        exigir_permiso(request.user, PERMISO_CATALOGOS_LEER)
        codigo_barras = request.query_params.get("codigo_barras")
        if not codigo_barras:
            return Response(
                {"error": "Debe enviar el parámetro codigo_barras"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        producto = ProductoService().get_by_codigo_barras(codigo_barras)
        if producto:
            return Response(producto, status=status.HTTP_200_OK)
        return Response(
            {"error": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND
        )


class ProductoDetailView(BaseDetailController):
    permiso_get = PERMISO_CATALOGOS_LEER
    permiso_put = "catalogos.escribir"
    permiso_delete = "catalogos.escribir"

    def __init__(self):
        super().__init__(ProductoService)
