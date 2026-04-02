from rest_framework import status
from rest_framework.response import Response

from producto.services.producto_service import ProductoService
from repository.base_controller import BaseDetailController, BaseListController


class ProductoListCreateView(BaseListController):
    def __init__(self):
        super().__init__(ProductoService)

    def get(self, request):
        categoria = request.query_params.get("categoria")
        page_param = request.query_params.get("page")
        page_size = int(request.query_params.get("page_size", 10))
        page = int(page_param) if page_param is not None else None

        if categoria:
            data = self.service.get_by_categoria(categoria, page=page, page_size=page_size)
            if data is not None:
                return Response(data, status=status.HTTP_200_OK)
            return Response(
                {"error": "Categoria no encontrada o sin productos"}, status=status.HTTP_404_NOT_FOUND
            )

        data = self.service.get_all(page=page, page_size=page_size)
        return Response(data, status=status.HTTP_200_OK)


    def get_by_codigo_barras(self, request):
        codigo_barras = request.query_params.get("codigo_barras")
        producto = self.service.get_by_codigo_barras(codigo_barras)
        if producto:
            return Response(producto, status=status.HTTP_200_OK)
        return Response(
            {"error": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND
        )

    def get_by_categoria(self, request):
        categoria = request.query_params.get("categoria")
        page_param = request.query_params.get("page")
        page_size = int(request.query_params.get("page_size", 10))
        page = int(page_param) if page_param is not None else None

        producto = self.service.get_by_categoria(categoria, page=page, page_size=page_size)
        if producto:
            return Response(producto, status=status.HTTP_200_OK)
        return Response(
            {"error": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND
        )



class ProductoDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(ProductoService)
