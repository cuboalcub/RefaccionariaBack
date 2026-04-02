from rest_framework import status
from rest_framework.response import Response

from producto.services.producto_service import ProductoService
from repository.base_controller import BaseDetailController, BaseListController


class ProductoListCreateView(BaseListController):
    def __init__(self):
        super().__init__(ProductoService)

    def get(self, request):
        categoria = request.query_params.get("categoria")
        if categoria:
            data = self.service.get_by_categoria(categoria)
            if data is not None:
                return Response(data, status=status.HTTP_200_OK)
            return Response(
                {"error": "Categoria no encontrada"}, status=status.HTTP_404_NOT_FOUND
            )

        page_param = request.query_params.get("page")
        page_size = int(request.query_params.get("page_size", 10))
        if page_param is not None:
            page = int(page_param)
            data = self.service.get_all(page=page, page_size=page_size)
        else:
            data = self.service.get_all()
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
        producto = self.service.get_by_categoria(categoria)
        if producto:
            return Response(producto, status=status.HTTP_200_OK)
        return Response(
            {"error": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND
        )


class ProductoDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(ProductoService)
