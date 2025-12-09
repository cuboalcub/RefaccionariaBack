from repository.base_controller import BaseListController, BaseDetailController

from producto.services.tipo_service import TipoService


class TipoListCreateView(BaseListController):
    def __init__(self):
        super().__init__(TipoService)


class TipoDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(TipoService)




# class TipoListCreateView(APIView):
#     """
#     Controlador para listar tipos o crear uno nuevo.
#     """

#     def get(self, request):     
#         tipos = TipoService.get_all_tipos()
#         return Response(tipos, status=status.HTTP_200_OK)

#     def post(self, request):
#         try:
#             tipo_data = request.data
#             tipo = TipoService.create_tipo(tipo_data)
#             return Response(tipo, status=status.HTTP_201_CREATED)
#         except ValueError as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
# class TipoDetailView(APIView):
#     """
#     Controlador para obtener, actualizar o eliminar un tipo por ID.
#     """

#     def get(self, request, tipo_id):
#         tipo = TipoService.get_tipo_by_id(tipo_id)
#         if tipo:
#             return Response(tipo, status=status.HTTP_200_OK)
#         return Response({"error": "Tipo no encontrado"}, status=status.HTTP_404_NOT_FOUND)

#     def put(self, request, tipo_id):
#         try:
#             updated_tipo = TipoService.update_tipo(tipo_id, request.data)
#             return Response(updated_tipo, status=status.HTTP_200_OK)
#         except ValueError as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#     def delete(self, request, tipo_id):
#         deleted = TipoService.delete_tipo(tipo_id)
#         if deleted:
#             return Response({"message": "Tipo eliminado"}, status=status.HTTP_200_OK)
#         return Response({"error": "Tipo no encontrado"}, status=status.HTTP_404_NOT_FOUND)