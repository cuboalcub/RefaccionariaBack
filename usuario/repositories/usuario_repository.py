from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from repository.base_repository import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(User)

    def create(self, user_data):
        return User.objects.create_user(**user_data)

    def get_by_username(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None
