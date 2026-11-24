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

from clientes.services.adeudo_service import AdeudoService
from clientes.services.abono_adeudo_service import AbonoAdeudoService
from clientes.services.cliente_service import ClienteService

MSG_SIN_SUCURSAL = "El usuario no tiene una sucursal asignada"


def _sucursal_del_cliente(cliente_id):
    cliente = ClienteService().get_by_id(cliente_id)
    return cliente.get("id_sucursal")


class AdeudoListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = "catalogos.crear"

    def __init__(self):
        super().__init__(AdeudoService)

    def get(self, request):
        exigir_permiso(request.user, self.permiso_get)

        sucursal_id = None
        param_sucursal = request.query_params.get("sucursal_id")
        if param_sucursal is not None:
            sucursal_id = entero_o_none(param_sucursal)
            if sucursal_id is None:
                return Response(
                    {"error": "sucursal_id debe ser entero"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        cliente_id = None
        param_cliente = request.query_params.get("cliente_id")
        if param_cliente is not None:
            cliente_id = entero_o_none(param_cliente)
            if cliente_id is None:
                return Response(
                    {"error": "cliente_id debe ser entero"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not es_staff(request.user):
            sucursal_id = sucursal_de_usuario(request.user)
            if sucursal_id is None:
                return Response(
                    {"error": MSG_SIN_SUCURSAL}, status=status.HTTP_400_BAD_REQUEST
                )

        estado = request.query_params.get("estado")
        return Response(
            self.service.get_all(
                sucursal_id=sucursal_id, cliente_id=cliente_id, estado=estado
            ),
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        try:
            exigir_permiso(request.user, self.permiso_post)
            data = dict(request.data)
            if not es_staff(request.user):
                cliente_id = entero_o_none(data.get("id_cliente"))
                if cliente_id is None:
                    return Response(
                        {"error": "id_cliente debe ser entero"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                exigir_misma_sucursal(
                    request.user, _sucursal_del_cliente(cliente_id), "clientes"
                )
            item = self.service.create(data)
            return Response(item, status=status.HTTP_201_CREATED)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdeudoDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = "catalogos.escribir"
    permiso_delete = "catalogos.escribir"

    def __init__(self):
        super().__init__(AdeudoService)

    def _check_sucursal(self, request, pk):
        item = self.service.get_by_id(pk)
        exigir_misma_sucursal(
            request.user, _sucursal_del_cliente(item.get("id_cliente")), "adeudos"
        )

    def _autorizado_o_error(self, request, pk, accion):
        try:
            exigir_permiso(request.user, accion)
            self._check_sucursal(request, pk)
            return None
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk):
        err = self._autorizado_o_error(request, pk, self.permiso_get)
        if err is not None:
            return err
        return super().get(request, pk)

    def put(self, request, pk):
        err = self._autorizado_o_error(request, pk, self.permiso_put)
        if err is not None:
            return err
        return super().put(request, pk)

    def delete(self, request, pk):
        try:
            exigir_permiso(request.user, self.permiso_delete)
            self._check_sucursal(request, pk)
            return Response(self.service.delete(pk), status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AbonoAdeudoListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = "catalogos.crear"

    def __init__(self):
        super().__init__(AbonoAdeudoService)

    def _check_adeudo(self, request, pk):
        adeudo = AdeudoService().get_by_id(pk)
        exigir_misma_sucursal(
            request.user, _sucursal_del_cliente(adeudo.get("id_cliente")), "adeudos"
        )
        return adeudo

    def get(self, request, pk):
        try:
            exigir_permiso(request.user, self.permiso_get)
            self._check_adeudo(request, pk)
            return Response(self.service.get_all(pk), status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, pk):
        try:
            exigir_permiso(request.user, self.permiso_post)
            self._check_adeudo(request, pk)
            data = dict(request.data)
            data["id_adeudo"] = pk
            item = self.service.create(data, user=request.user)
            return Response(item, status=status.HTTP_201_CREATED)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
