# users/services/user_service.py

from usuario.repositories.usuario_repositorie import UserRepository
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken



class UserService:

    @staticmethod
    def login(username, password):
        """
        Autentica al usuario y devuelve un JWT (access + refresh).
        """
        user = UserRepository.get_by_username(username)
        if user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "isadmin": user.is_superuser,
                    "isstaff": user.is_staff,
                }
        }
        return None
 
    @staticmethod
    def create_user(user_data):
        """
        Lógica para crear un nuevo usuario.
        user_data debería ser un diccionario con los campos necesarios.
        """
        if 'username' not in user_data or 'password' not in user_data:
            raise ValueError("Faltan campos obligatorios: username y password")
        existing_user = UserRepository.get_by_username(user_data['username'])
        if existing_user:
            raise ValueError("El nombre de usuario ya existe")
        user = UserRepository.create(user_data)
        return UserService._to_dict(user)
    
    @staticmethod
    def get_all_users():
        """
        Devuelve una lista de todos los usuarios.
        """
        users = UserRepository.get_all()
        return [UserService._to_dict(user) for user in users]
    # ----------------------
    # Helpers privados
    # ----------------------
    @staticmethod
    def _to_dict(user):
        """
        Convierte un modelo User en dict serializable.
        """
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
        }
