from clientes.models import Cliente
from repository.permissions import es_staff
from sucursales.models import Sucursal
from usuario.repositories.usuario_repository import UserRepository
from ventas.repositories.metodo_pago_repository import MetodoPagoRepository


class VentaCabeceraResolver:
    """Resuelve los datos de cabecera de una venta (usuario, método de pago,
    sucursal y cliente) a partir del JWT o del payload legacy."""

    def __init__(self, user_repo=None, metodo_pago_repo=None):
        self.user_repo = user_repo or UserRepository()
        self.metodo_pago_repo = metodo_pago_repo or MetodoPagoRepository()

    def sucursal_del_usuario(self, user):
        """Resuelve el id de Sucursal a partir del Perfil.sucursal del usuario autenticado."""
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
        return user_sucursal_id

    def usuario_autenticado(self, data, user):
        via_jwt = user is not None and getattr(user, "is_authenticated", False)
        if via_jwt:
            return user, True
        if "id_usuario" in data and data["id_usuario"] is not None:
            usuario = self.user_repo.get_by_id(data['id_usuario'])
            if not usuario:
                raise ValueError(f"Usuario con id {data['id_usuario']} no encontrado")
            return usuario, False
        if "id_metodo_pago" not in data:
            raise ValueError("Faltan campos obligatorios: id_usuario, id_metodo_pago")
        raise ValueError("Faltan campos obligatorios: id_usuario (autenticación requerida)")

    def metodo_pago_resuelto(self, data):
        if "id_metodo_pago" not in data or data["id_metodo_pago"] is None:
            raise ValueError("Faltan campos obligatorios: id_metodo_pago")
        metodo_pago = self.metodo_pago_repo.get_by_id(data['id_metodo_pago'])
        if not metodo_pago:
            raise ValueError(f"Metodo de pago con id {data['id_metodo_pago']} no encontrado")
        return metodo_pago

    def cliente_validado(self, data):
        """Normaliza id_cliente ausente/'' a None y valida existencia."""
        if "id_cliente" not in data or data["id_cliente"] in (None, "", 0):
            return None
        cliente = Cliente.objects.filter(id=data["id_cliente"]).first()
        if not cliente:
            raise ValueError(f"Cliente con id {data['id_cliente']} no encontrado")
        return cliente

    def sucursal_override_staff(self, data):
        try:
            suc_id = int(data["sucursal_id"])
        except (TypeError, ValueError):
            raise ValueError("sucursal_id debe ser entero")
        if not Sucursal.objects.filter(id=suc_id).exists():
            raise ValueError(f"Sucursal con id {suc_id} no encontrada")
        return suc_id

    def sucursal_legacy(self, data):
        """Sin JWT: exige id_sucursal explícito."""
        suc_id = data.get("id_sucursal")
        if suc_id is None:
            raise ValueError("Faltan campos obligatorios: id_sucursal")
        if not Sucursal.objects.filter(id=suc_id).exists():
            raise ValueError(f"Sucursal con id {suc_id} no encontrada")
        return suc_id

    def sucursal_via_jwt(self, data, user, is_staff):
        """JWT: el usuario ancla la venta a su sucursal. Staff puede enviar
        ``sucursal_id`` explícito como override."""
        if is_staff and data.get("sucursal_id") is not None:
            return self.sucursal_override_staff(data)
        try:
            return self.sucursal_del_usuario(user)
        except ValueError as e:
            if is_staff:
                raise ValueError(str(e) + " (staff: envíe sucursal_id explícito)")
            raise

    def resolver_cabecera(self, data, user=None):
        """Resuelve (usuario, método de pago, sucursal_id) con las mismas
        reglas que ``create`` (JWT vs legacy, staff override)."""
        usuario, via_jwt = self.usuario_autenticado(data, user)
        metodo_pago = self.metodo_pago_resuelto(data)
        if via_jwt:
            sucursal_id = self.sucursal_via_jwt(data, usuario, es_staff(usuario))
        else:
            sucursal_id = self.sucursal_legacy(data)
        return usuario, metodo_pago, sucursal_id
