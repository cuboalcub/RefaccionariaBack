from decimal import Decimal
from ventas.services.detalleventa_service import DetalleVentaService
from ventas.models import venta
from ventas.repositories.ventas_repository import VentaRepository
from usuario.repositories.usuario_repositorie import UserRepository
from ventas.repositories.metodopago_repository import MetodoPagoRepository
from repository.base_service import BaseService
from producto.repositories.producto_repository import ProductoRepository
from inventario.models import Inventario

class VentaService(BaseService):
    def __init__(self, venta_repo=None, user_repo=None, metodopago_repo=None, producto_repo=None):
        super().__init__(model=venta, repository=venta_repo or VentaRepository())
        self.user_repo = user_repo or UserRepository()
        self.metodopago_repo = metodopago_repo or MetodoPagoRepository()
        self.producto_repo = producto_repo or ProductoRepository()

    def _to_dict(self, instance):
        id_inventario = instance.id_inventario.id if instance.id_inventario else None
        id_sucursal = None
        try:
            if instance.id_inventario is not None:
                id_sucursal = instance.id_inventario.id_sucursal_id
        except Exception:
            id_sucursal = None
        return {
            "id": instance.id,
            "id_usuario": instance.id_usuario.id if instance.id_usuario else None,
            "id_metodoPago": instance.id_metodoPago.id if instance.id_metodoPago else None,
            "id_inventario": id_inventario,
            "id_sucursal": id_sucursal,
            "total": str(instance.total),
            "fecha": instance.fecha.isoformat() if instance.fecha else None
        }

    def get_all(self, page: int = None, page_size: int = 10, sucursal_id: int = None,
                id_inventario: int = None):
        """Devuelve ventas divididas por sucursal con paginación opcional.

        - Filtra por ``sucursal_id`` vía ``id_inventario__id_sucursal_id``.
        - Filtra por ``id_inventario`` si se indica (más específico).
        - Si ``page`` es None devuelve lista plana (compatibilidad).
        - Si ``page`` se indica devuelve dict {total, page, page_size, total_pages, results}.
        """
        try:
            import math

            if page is not None:
                try:
                    page = int(page)
                    page_size = int(page_size)
                except (TypeError, ValueError):
                    raise ValueError("page y page_size deben ser enteros")
                if page < 1 or page_size < 1:
                    raise ValueError("page y page_size deben ser >= 1")

            if sucursal_id is not None:
                try:
                    sucursal_id = int(sucursal_id)
                except (TypeError, ValueError):
                    raise ValueError("sucursal_id debe ser entero")
                from sucursales.models import Sucursal
                if not Sucursal.objects.filter(id=sucursal_id).exists():
                    raise ValueError(f"Sucursal con id {sucursal_id} no encontrada")

            if id_inventario is not None:
                try:
                    id_inventario = int(id_inventario)
                except (TypeError, ValueError):
                    raise ValueError("id_inventario debe ser entero")

            qs = venta.objects.all().select_related(
                'id_usuario', 'id_metodoPago', 'id_inventario__id_sucursal'
            ).order_by('-fecha', '-id')

            if sucursal_id is not None:
                qs = qs.filter(id_inventario__id_sucursal_id=sucursal_id)
            if id_inventario is not None:
                qs = qs.filter(id_inventario_id=id_inventario)

            if page is None:
                return [self._to_dict(v) for v in qs]

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
                "results": [self._to_dict(v) for v in instances],
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error al obtener ventas: {str(e)}") from e

    def _resolve_inventario_for_user(self, user):
        """Resuelve el Inventario a partir del Perfil.sucursal del usuario autenticado.
        - 1 sucursal -> 1..N inventarios: toma el primero por id (determinístico).
        - Lanza ValueError si el usuario no tiene sucursal o la sucursal no tiene inventario.
        """
        # Intentar obtener id_sucursal_id sin query extra si perfil está cacheado
        perfil = getattr(user, 'perfil', None)
        user_sucursal_id = None
        if perfil is not None:
            try:
                user_sucursal_id = getattr(perfil, 'id_sucursal_id', None)
            except Exception:
                user_sucursal_id = None
        # Fallback: fetch fresco si no se obtuvo (perfil no cacheado o DoesNotExist)
        if user_sucursal_id is None:
            try:
                from usuario.models import Perfil
                p = Perfil.objects.filter(usuario_id=user.id).first()
                if p:
                    user_sucursal_id = p.id_sucursal_id
            except Exception:
                user_sucursal_id = None
        if user_sucursal_id is None:
            raise ValueError("El usuario no tiene una sucursal asignada. Asigne una sucursal al perfil")
        qs = Inventario.objects.filter(id_sucursal_id=user_sucursal_id).order_by('id')
        inventario = qs.first()
        if not inventario:
            raise ValueError(f"La sucursal {user_sucursal_id} no tiene un inventario asignado")
        return inventario

    def create(self, data, user=None):
        # Distinguir flujo JWT (user pasado por controlador) vs legacy/tests (id_usuario en payload)
        via_jwt = user is not None and getattr(user, "is_authenticated", False)
        if via_jwt:
            # usuario autenticado: ignora id_usuario si viene en payload
            auth_user = user
        elif "id_usuario" in data and data["id_usuario"] is not None:
            auth_user = self.user_repo.get_by_id(data['id_usuario'])
            if not auth_user:
                raise ValueError(f"Usuario con id {data['id_usuario']} no encontrado")
        else:
            # sin user y sin id_usuario -> error (mantiene compatibilidad con tests)
            if "id_metodoPago" not in data:
                raise ValueError("Faltan campos obligatorios: id_usuario, id_metodoPago")
            raise ValueError("Faltan campos obligatorios: id_usuario (autenticación requerida)")

        if "id_metodoPago" not in data or data["id_metodoPago"] is None:
            raise ValueError("Faltan campos obligatorios: id_metodoPago")

        user = auth_user
        metodoPago = self.metodopago_repo.get_by_id(data['id_metodoPago'])
        if not metodoPago:
            raise ValueError(f"Metodo de pago con id {data['id_metodoPago']} no encontrado")

        # Resolver id_inventario server-side a partir del JWT/perfil.
        # - via_jwt + usuario normal: se ignora cualquier id_inventario enviado y se deriva de su sucursal.
        # - via_jwt + staff/superuser: se permite override explícito de id_inventario (para soporte multi-sucursal/admin).
        # - legacy (sin via_jwt, tests): se respeta id_inventario del payload para compatibilidad.
        is_staff = getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)
        inventario = None
        if via_jwt:
            if is_staff and "id_inventario" in data and data["id_inventario"] is not None:
                inventario = Inventario.objects.filter(id=data['id_inventario']).first()
                if not inventario:
                    raise ValueError(f"Inventario con id {data['id_inventario']} no encontrado")
            else:
                try:
                    inventario = self._resolve_inventario_for_user(user)
                except ValueError as e:
                    if is_staff:
                        raise ValueError(str(e) + " (staff: envíe id_inventario explícito)")
                    raise
        else:
            # Flujo sin autenticación (tests/compatibilidad): exigir id_inventario en payload
            if "id_inventario" not in data or data["id_inventario"] is None:
                raise ValueError("Faltan campos obligatorios: id_inventario")
            inventario = Inventario.objects.filter(id=data['id_inventario']).first()
            if not inventario:
                raise ValueError(f"Inventario con id {data['id_inventario']} no encontrado")

        venta_data = {
            "id_usuario": user,
            "id_metodoPago": metodoPago,
            "id_inventario": inventario,
            "total": 0
        }
        venta = super().create(venta_data)

        return venta
