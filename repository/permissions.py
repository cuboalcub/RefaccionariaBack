"""Permisos centrales del negocio (Fase 1 roles).

Definición única de admin: ``is_staff`` es la bandera del negocio
(``is_superuser`` la implica y conserva los mismos poderes; solo difieren
en el Django Admin). No hay roles intermedios todavía: usuario normal
opera su sucursal, staff opera todas.
"""

from rest_framework.exceptions import PermissionDenied


def es_staff(user) -> bool:
    """True si el usuario tiene poderes globales (staff o superuser)."""
    return bool(
        getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)
    )


def sucursal_de_usuario(user):
    """Devuelve el id de sucursal del perfil del usuario (o None).

    Import diferido de Perfil para evitar ciclos entre apps.
    """
    perfil = getattr(user, "perfil", None)
    sid = getattr(perfil, "id_sucursal_id", None) if perfil is not None else None
    if sid is None:
        from usuario.models import Perfil

        p = Perfil.objects.filter(usuario_id=getattr(user, "id", None)).first()
        sid = p.id_sucursal_id if p else None
    return sid


def entero_o_none(valor):
    """int(valor) o None si no es convertible (para ids en payloads)."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def rol_de_usuario(user) -> str:
    """Rol del perfil ('cajero' por defecto si no hay perfil)."""
    perfil = getattr(user, "perfil", None)
    rol = getattr(perfil, "rol", None) if perfil is not None else None
    if rol is None:
        try:
            from usuario.models import Perfil

            p = Perfil.objects.filter(usuario_id=getattr(user, "id", None)).first()
            rol = getattr(p, "rol", None) if p else None
        except Exception:
            rol = None
    return rol or "cajero"


# Matriz rol x acción (Fase 2). El scoping por sucursal es una capa
# separada: el rol dice *qué* se puede hacer, la sucursal *dónde*.
# is_staff implica todos los permisos (ver `puede`).
PERMISOS_POR_ROL = {
    "cajero": {
        "ventas.vender",
        "inventario.ver",
        "precios.leer",
        "catalogos.leer",
        "catalogos.crear",
    },
    "encargado": {
        "ventas.vender",
        "ventas.anular",
        "inventario.ver",
        "inventario.escribir",
        "precios.leer",
        "precios.escribir",
        "reporte.ver",
        "catalogos.leer",
        "catalogos.crear",
        "catalogos.escribir",
        "usuarios.gestionar",
    },
    "admin": {
        "ventas.vender",
        "ventas.anular",
        "inventario.ver",
        "inventario.escribir",
        "inventario.admin",
        "precios.leer",
        "precios.escribir",
        "reporte.ver",
        "catalogos.leer",
        "catalogos.crear",
        "catalogos.escribir",
        "sucursales.admin",
        "usuarios.gestionar",
    },
}


def puede(user, accion: str) -> bool:
    """True si el usuario tiene la acción (staff implica todo)."""
    if es_staff(user):
        return True
    return accion in PERMISOS_POR_ROL.get(rol_de_usuario(user), set())


def exigir_permiso(user, accion: str):
    """403 si el rol no contempla la acción."""
    if not puede(user, accion):
        raise PermissionDenied(f"Requiere permiso '{accion}' (rol insuficiente)")


def exigir_misma_sucursal(user, sucursal_recurso, recurso="recurso"):
    """Autoriza si el recurso pertenece a la sucursal del usuario.

    - Staff: siempre autorizado (bypass global).
    - Sin sucursal asignada: ValueError (el controller lo mapea a 400).
    - Otra sucursal: PermissionDenied (el controller lo deja en 403).
    - Recurso sin sucursal determinable (None): se permite; la validación
      de existencia la hace el servicio (400/404).
    """
    if es_staff(user):
        return
    user_suc = sucursal_de_usuario(user)
    if user_suc is None:
        raise ValueError("El usuario no tiene una sucursal asignada")
    if sucursal_recurso is not None and sucursal_recurso != user_suc:
        raise PermissionDenied(f"No tiene acceso a {recurso} de otra sucursal")
