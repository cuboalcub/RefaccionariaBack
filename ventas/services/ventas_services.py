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
        return {
            "id": instance.id,
            "id_usuario": instance.id_usuario.id if instance.id_usuario else None,
            "id_metodoPago": instance.id_metodoPago.id if instance.id_metodoPago else None,
            "id_inventario": instance.id_inventario.id if instance.id_inventario else None,
            "total": str(instance.total),
            "fecha": instance.fecha.isoformat() if instance.fecha else None
        }

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
