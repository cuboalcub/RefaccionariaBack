from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from usuario.repositories.usuario_repository import UserRepository
from usuario.models import Perfil
from rest_framework_simplejwt.tokens import RefreshToken
from repository.base_service import BaseService
from repository.permissions import es_staff, rol_de_usuario, sucursal_de_usuario
from sucursales.models import Sucursal

CAMPOS_ALTA_USUARIO = {"username", "email", "password", "first_name", "last_name"}


class UserService(BaseService):

    def __init__(self, repository=None):
        super().__init__(model=User, repository=repository or UserRepository())

    def login(self, username, password):
        user = self.repository.get_by_username(username)
        if user and user.is_active and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "isadmin": user.is_superuser,
                    "isstaff": user.is_staff,
                    "id_sucursal": sucursal_de_usuario(user),
                    "rol": rol_de_usuario(user),
                }
            }
        return None

    @staticmethod
    def _validar_email_unico(email, excluir_id=None):
        # shortcut: unicidad solo en app (sin índice en BD); añadir índice
        # único case-insensitive si se requiere cubrir concurrencia.
        email = (email or "").strip()
        if not email:
            return ""
        qs = User.objects.filter(email__iexact=email)
        if excluir_id is not None:
            qs = qs.exclude(pk=excluir_id)
        if qs.exists():
            raise ValueError("El correo ya está registrado")
        return email

    def create_user(self, user_data, actor=None):
        user_data = dict(user_data)
        if 'username' not in user_data or 'password' not in user_data:
            raise ValueError("Faltan campos obligatorios: username y password")
        existing_user = self.repository.get_by_username(user_data['username'])
        if existing_user:
            raise ValueError("El nombre de usuario ya existe")

        id_sucursal = user_data.pop('id_sucursal', None) or None
        rol = user_data.pop('rol', None) or None
        # Solo campos de perfil editables: nunca is_staff/is_superuser.
        user_data = {
            k: v for k, v in user_data.items() if k in CAMPOS_ALTA_USUARIO
        }
        if "email" in user_data:
            user_data["email"] = self._validar_email_unico(user_data["email"])
        if actor is not None and not es_staff(actor):
            # Encargado: solo cajeros de su propia sucursal (fail-closed).
            actor_suc = sucursal_de_usuario(actor)
            if actor_suc is None:
                raise ValueError("El usuario no tiene una sucursal asignada")
            id_sucursal = actor_suc
            rol = Perfil.Rol.CAJERO.value
        elif not id_sucursal and actor is not None:
            # Staff sin sucursal explícita: hereda la de su perfil.
            id_sucursal = sucursal_de_usuario(actor)

        if not id_sucursal:
            raise ValueError(
                "Debe indicar id_sucursal o el creador debe tener una sucursal asignada"
            )
        if rol is None:
            rol = Perfil.Rol.CAJERO.value
        if rol not in Perfil.Rol.values:
            raise ValueError(f"Rol inválido: {rol}")
        sucursal = Sucursal.objects.filter(id=id_sucursal).first()
        if not sucursal:
            raise ValueError("La sucursal indicada no existe")

        with transaction.atomic():
            user = self.repository.create(user_data)
            Perfil.objects.create(usuario=user, id_sucursal=sucursal, rol=rol)

        return self._to_dict(user)

    def get_all_users(self, actor=None):
        users = self.get_all()
        if actor is not None and not es_staff(actor):
            actor_suc = sucursal_de_usuario(actor)
            if actor_suc is None:
                return []
            ids = set(
                Perfil.objects.filter(id_sucursal_id=actor_suc).values_list(
                    "usuario_id", flat=True
                )
            )
            users = [u for u in users if u["id"] in ids]
        return users

    def get_user_by_id(self, user_id, actor=None):
        user = self.repository.get_by_id(user_id)
        if user and actor is not None and not es_staff(actor):
            obj = Perfil.objects.filter(usuario_id=user_id).first()
            obj_suc = obj.id_sucursal_id if obj else None
            actor_suc = sucursal_de_usuario(actor)
            if obj_suc is None or actor_suc is None or obj_suc != actor_suc:
                raise PermissionDenied("No tiene acceso a usuarios de otra sucursal")
        return self._to_dict(user)

    def update_user(self, user_id, user_data, actor=None):
        user = self.repository.get_by_id(user_id)
        if not user:
            return None
        if actor is not None and not es_staff(actor):
            obj = Perfil.objects.filter(usuario_id=user_id).first()
            obj_suc = obj.id_sucursal_id if obj else None
            actor_suc = sucursal_de_usuario(actor)
            if obj_suc is None or actor_suc is None or obj_suc != actor_suc:
                raise PermissionDenied("No tiene acceso a usuarios de otra sucursal")

        user_data = dict(user_data)
        if "email" in user_data:
            user_data["email"] = self._validar_email_unico(
                user_data["email"], excluir_id=user.id
            )

        puede_asignar = actor is None or es_staff(actor)
        editable_fields = {"username", "email", "first_name", "last_name", "is_active", "password"}
        with transaction.atomic():
            for key, value in user_data.items():
                if key not in editable_fields:
                    continue
                if key == "password":
                    user.set_password(value)
                else:
                    setattr(user, key, value)
            user.save()
            if puede_asignar:
                self._actualizar_perfil(user, user_data)
        return self._to_dict(user)

    def _actualizar_perfil(self, user, user_data):
        sucursal_id = user_data.get("id_sucursal")
        rol = user_data.get("rol")
        if sucursal_id == "":
            sucursal_id = None
        if rol == "":
            rol = None
        if sucursal_id is None and rol is None:
            return
        if sucursal_id is not None:
            sucursal = Sucursal.objects.filter(id=sucursal_id).first()
            if not sucursal:
                raise ValueError("La sucursal indicada no existe")
        if rol is not None and rol not in Perfil.Rol.values:
            raise ValueError(f"Rol inválido: {rol}")
        perfil = Perfil.objects.filter(usuario_id=user.id).first()
        if perfil is None:
            perfil = Perfil(usuario=user)
        if sucursal_id is not None:
            perfil.id_sucursal = sucursal
        if rol is not None:
            perfil.rol = rol
        perfil.save()

    def delete_user(self, user_id):
        user = self.repository.get_by_id(user_id)
        if not user:
            return False
        user.delete()
        return True

    def _to_dict(self, user):
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "id_sucursal": sucursal_de_usuario(user),
            "rol": rol_de_usuario(user),
        }