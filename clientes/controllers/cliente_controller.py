from rest_framework import status
from rest_framework.response import Response

from repository.base_controller import BaseListController, BaseDetailController
from repository.exceptions import NotFoundError
from repository.permissions import (
    entero_o_none,
    es_staff,
    exigir_misma_sucursal,
    exigir_permiso,
    sucursal_de_usuario,
)

from clientes.services.cliente_service import ClienteService

MSG_SIN_SUCURSAL = "El usuario no tiene una sucursal asignada"


class ClienteListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = "catalogos.crear"

    def __init__(self):
        super().__init__(ClienteService)

    def get(self, request):
        exigir_permiso(request.user, self.permiso_get)
        if not es_staff(request.user):
            sucursal_id = sucursal_de_usuario(request.user)
            if sucursal_id is None:
                return Response(
                    {"error": MSG_SIN_SUCURSAL}, status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                self.service.get_all(sucursal_id=sucursal_id),
                status=status.HTTP_200_OK,
            )

        param = request.query_params.get("sucursal_id")
        if param is None:
            return Response(self.service.get_all(), status=status.HTTP_200_OK)
        sucursal_id = entero_o_none(param)
        if sucursal_id is None:
            return Response(
                {"error": "sucursal_id debe ser entero"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            self.service.get_all(sucursal_id=sucursal_id), status=status.HTTP_200_OK
        )

    def post(self, request):
        try:
            exigir_permiso(request.user, self.permiso_post)
            data = dict(request.data)
            if not es_staff(request.user) or data.get("id_sucursal") in (None, ""):
                data["id_sucursal"] = sucursal_de_usuario(request.user)
            item = self.service.create(data)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClienteDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = "catalogos.escribir"
    permiso_delete = "catalogos.escribir"

    def __init__(self):
        super().__init__(ClienteService)

    def _check_sucursal(self, request, pk):
        item = self.service.get_by_id(pk)
        exigir_misma_sucursal(request.user, item.get("id_sucursal"), "clientes")

    def get(self, request, pk):
        try:
            self._check_sucursal(request, pk)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return super().get(request, pk)

    def put(self, request, pk):
        try:
            exigir_permiso(request.user, self.permiso_put)
            self._check_sucursal(request, pk)
            data = dict(request.data)
            if not es_staff(request.user):
                data["id_sucursal"] = sucursal_de_usuario(request.user)
            item = self.service.update(pk, data)
            return Response(item, status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            self._check_sucursal(request, pk)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return super().delete(request, pk)
