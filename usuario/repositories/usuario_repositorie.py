# users/repositories/user_repository.py

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist


class UserRepository:
    @staticmethod
    def get_all():
        """
        Devuelve todos los usuarios como queryset.
        """
        return User.objects.all()

    @staticmethod
    def create(user_data):
        """
        Crea un usuario nuevo en la base de datos.
        user_data debería ser un diccionario.
        """
        user = User.objects.create_user(**user_data)
        return user

    @staticmethod
    def update(user_id, user_data):
        """
        Actualiza un usuario existente. Devuelve None si no existe.
        """
        try:
            user = User.objects.get(id=user_id)
            for key, value in user_data.items():
                setattr(user, key, value)
            user.save()
            return user
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def delete(user_id):
        """
        Elimina un usuario por ID. Devuelve True si lo eliminó, False si no existe.
        """
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return True
        except ObjectDoesNotExist:
            return False
        
    @staticmethod
    def get_by_username(username):
        """
        Devuelve un usuario por nombre de usuario o None si no existe.
        """
        try:
            
            return User.objects.get(username=username)
        
        except ObjectDoesNotExist:
            return None
