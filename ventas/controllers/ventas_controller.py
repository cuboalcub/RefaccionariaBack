from rest_framework import status
from rest_framework.response import Response

from ventas.services.ventas_services import VentaService
from repository.base_controller import BaseListController, BaseDetailController


class VentasListController(BaseListController):
    def __init__(self):
        super().__init__(VentaService)

    def get(self, request) -> Response:
        try:
            page_param = request.query_params.get("page")
            page_size_param = request.query_params.get("page_size", 10)
            sucursal_param = request.query_params.get("sucursal_id")
            inventario_param = request.query_params.get("id_inventario")

            is_staff = getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False)

            sucursal_id = None
            if sucursal_param is not None:
                try:
                    sucursal_id = int(sucursal_param)
                except ValueError:
                    return Response({"error": "sucursal_id debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)

            if not is_staff:
                # Usuario normal: forzar su propia sucursal (seguridad: no ve otras sucursales)
                try:
                    perfil = getattr(request.user, "perfil", None)
                    user_sucursal_id = getattr(perfil, "id_sucursal_id", None) if perfil is not None else None
                    if user_sucursal_id is None:
                        from usuario.models import Perfil
                        p = Perfil.objects.filter(usuario_id=request.user.id).first()
                        if p:
                            user_sucursal_id = p.id_sucursal_id
                    if user_sucursal_id is None:
                        return Response(
                            {"error": "El usuario no tiene una sucursal asignada"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    sucursal_id = user_sucursal_id
                except Exception as e:
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            id_inventario = None
            if inventario_param is not None:
                try:
                    id_inventario = int(inventario_param)
                except ValueError:
                    return Response({"error": "id_inventario debe ser entero"}, status=status.HTTP_400_BAD_REQUEST)

            if page_param is not None:
                try:
                    page = int(page_param)
                    page_size = int(page_size_param)
                except ValueError:
                    return Response({"error": "page y page_size deben ser enteros"}, status=status.HTTP_400_BAD_REQUEST)
                data = self.service.get_all(
                    page=page, page_size=page_size,
                    sucursal_id=sucursal_id, id_inventario=id_inventario,
                )
            else:
                data = self.service.get_all(sucursal_id=sucursal_id, id_inventario=id_inventario)
            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request) -> Response:
        try:
            # ignora id_usuario e id_inventario del payload: se toman del JWT/perfil
            # staff/superuser puede enviar id_inventario como override explícito
            data = dict(request.data)
            data.pop("id_usuario", None)
            is_staff = getattr(request.user, "is_staff", False) or getattr(request.user, "is_superuser", False)
            if not is_staff:
                data.pop("id_inventario", None)
            item = self.service.create(data, user=request.user)
            return Response(item, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VentasDetailController(BaseDetailController):
    def __init__(self):
        super().__init__(VentaService)


