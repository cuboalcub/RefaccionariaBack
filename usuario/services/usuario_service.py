from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied

from usuario.repositories.usuario_repository import UserRepository
from usuario.models import Perfil
from rest_framework_simplejwt.tokens import RefreshToken
from repository.base_service import BaseService
from repository.permissions import es_staff, sucursal_de_usuario
from sucursales.models import Sucursal


class UserService(BaseService):

    def __init__(self, repository=None):
        super().__init__(model=User, repository=repository or UserRepository())

    def login(self, username, password):
        from repository.permissions import rol_de_usuario

        user = self.repository.get_by_username(username)
        if user and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "isadmin": user.is_superuser,
                    "isstaff": user.is_staff,
                    "rol": rol_de_usuario(user),
                }
            }
        return None

    def create_user(self, user_data, actor=None):
        if 'username' not in user_data or 'password' not in user_data:
            raise ValueError("Faltan campos obligatorios: username y password")
        existing_user = self.repository.get_by_username(user_data['username'])
        if existing_user:
            raise ValueError("El nombre de usuario ya existe")

        id_sucursal = user_data.pop('id_sucursal', None)
        rol = user_data.pop('rol', None)
        if actor is not None and not es_staff(actor):
            # Encargado: solo cajeros de su propia sucursal (fail-closed).
            actor_suc = sucursal_de_usuario(actor)
            if actor_suc is None:
                raise ValueError("El usuario no tiene una sucursal asignada")
            id_sucursal = actor_suc
            rol = Perfil.Rol.CAJERO.value
        if rol is None:
            rol = Perfil.Rol.CAJERO.value
        if rol not in Perfil.Rol.values:
            raise ValueError(f"Rol inválido: {rol}")
        user = self.repository.create(user_data)

        if id_sucursal:
            if not Sucursal.objects.filter(id=id_sucursal).exists():
                user.delete()
                raise ValueError("La sucursal indicada no existe")
            Perfil.objects.create(
                usuario=user,
                id_sucursal=Sucursal.objects.get(id=id_sucursal),
                rol=rol,
            )

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

        editable_fields = {"username", "email", "first_name", "last_name", "is_active", "password"}
        for key, value in user_data.items():
            if key not in editable_fields:
                continue
            if key == "password":
                user.set_password(value)
            else:
                setattr(user, key, value)
        user.save()
        return self._to_dict(user)

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
        }