import math

from sucursales.models import Sucursal
from ventas.repositories.venta_repository import VentaRepository


def venta_to_dict(instance):
    return {
        "id": instance.id,
        "id_usuario": instance.id_usuario.id if instance.id_usuario else None,
        "id_metodo_pago": instance.id_metodo_pago.id if instance.id_metodo_pago else None,
        "id_sucursal": instance.id_sucursal_id,
        "id_cliente": instance.id_cliente_id,
        "estado": instance.estado,
        "total": str(instance.total),
        "fecha": instance.fecha.isoformat() if instance.fecha else None,
    }


class VentaQueryService:
    """Consultas paginadas de ventas."""

    def __init__(self, venta_repo=None, to_dict=None):
        self.venta_repo = venta_repo or VentaRepository()
        self.to_dict = to_dict or venta_to_dict

    def _validar_paginacion(self, page, page_size):
        try:
            page = int(page)
            page_size = int(page_size)
        except (TypeError, ValueError):
            raise ValueError("page y page_size deben ser enteros")
        if page < 1 or page_size < 1:
            raise ValueError("page y page_size deben ser >= 1")
        return page, page_size

    def _validar_sucursal_filtro(self, sucursal_id):
        try:
            sucursal_id = int(sucursal_id)
        except (TypeError, ValueError):
            raise ValueError("sucursal_id debe ser entero")
        if not Sucursal.objects.filter(id=sucursal_id).exists():
            raise ValueError(f"Sucursal con id {sucursal_id} no encontrada")
        return sucursal_id

    def get_all(self, page=None, page_size=10, sucursal_id=None):
        """Devuelve ventas divididas por sucursal con paginación opcional.

        - Filtra por ``sucursal_id`` vía ``id_sucursal_id``.
        - Si ``page`` es None devuelve lista plana (compatibilidad).
        - Si ``page`` se indica devuelve dict {total, page, page_size, total_pages, results}.
        """
        try:
            if page is not None:
                page, page_size = self._validar_paginacion(page, page_size)

            if sucursal_id is not None:
                sucursal_id = self._validar_sucursal_filtro(sucursal_id)

            qs = self.venta_repo.get_ventas(sucursal_id=sucursal_id)

            if page is None:
                return [self.to_dict(v) for v in qs]

            total = qs.count()
            total_pages = math.ceil(total / page_size) if total else 0
            start = (page - 1) * page_size
            end = start + page_size
            instances = list(qs[start:end])
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "sucursal_id": sucursal_id,
                "results": [self.to_dict(v) for v in instances],
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error al obtener ventas: {str(e)}") from e
