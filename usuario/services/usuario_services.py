from django.contrib.auth.models import User

from usuario.repositories.usuario_repositorie import UserRepository
from rest_framework_simplejwt.tokens import RefreshToken
from repository.base_service import BaseService


class UserService(BaseService):

    def __init__(self, repository=None):
        super().__init__(model=User, repository=repository or UserRepository())

    def login(self, username, password):
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
                }
            }
        return None

    def create_user(self, user_data):
        if 'username' not in user_data or 'password' not in user_data:
            raise ValueError("Faltan campos obligatorios: username y password")
        existing_user = self.repository.get_by_username(user_data['username'])
        if existing_user:
            raise ValueError("El nombre de usuario ya existe")
        user = self.repository.create(user_data)
        return self._to_dict(user)

    def get_all_users(self):
        return self.get_all()

    def get_user_by_id(self, user_id):
        user = self.repository.get_by_id(user_id)
        return self._to_dict(user)

    def update_user(self, user_id, user_data):
        user = self.repository.get_by_id(user_id)
        if not user:
            return None

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