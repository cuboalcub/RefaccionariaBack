from rest_framework import status
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from repository.base_controller import BaseListController
from repository.base_controller import BaseDetailController

from producto.services.producto_service import ProductoService
from repository.base_controller import BaseDetailController, BaseListController


class ProductoListCreateView(BaseListController):
    def __init__(self):
        super().__init__(ProductoService)

    def get(self, request):
        categoria = request.query_params.get("categoria")
        query = request.query_params.get("query")
        page_param = request.query_params.get("page")
        page_size = int(request.query_params.get("page_size", 10))
        sucursal_id = request.query_params.get("sucursal_id")
        search = request.query_params.get("search")
        clave = request.query_params.get("clave")
        marca = request.query_params.get("marca")
        codigo_barras = request.query_params.get("codigo_barras")
        tipo_id = request.query_params.get("tipo_id") or request.query_params.get("id_tipo")
        proveedor_id = request.query_params.get("proveedor_id") or request.query_params.get("id_proveedor")

        kwargs = {}
        if sucursal_id is not None:
            try:
                kwargs["sucursal_id"] = int(sucursal_id)
            except ValueError:
                return Response({"error": "sucursal_id debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)
        if search:
            kwargs["search"] = search
        if clave:
            kwargs["clave"] = clave
        if marca:
            kwargs["marca"] = marca
        if codigo_barras:
            kwargs["codigo_barras"] = codigo_barras
        if tipo_id:
            try:
                kwargs["tipo_id"] = int(tipo_id)
            except ValueError:
                return Response({"error": "tipo_id debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)
        if proveedor_id:
            try:
                kwargs["proveedor_id"] = int(proveedor_id)
            except ValueError:
                return Response({"error": "proveedor_id debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if page_param is not None:
                page = int(page_param)
                data = self.service.get_all(page=page, page_size=page_size, **kwargs)
            else:
                data = self.service.get_all(**kwargs)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data, status=status.HTTP_200_OK)


class ProductoPorCodigoBarrasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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
    def __init__(self):
        super().__init__(ProductoService)
