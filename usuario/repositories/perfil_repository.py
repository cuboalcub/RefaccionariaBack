from django.core.exceptions import ObjectDoesNotExist

from repository.base_repository import BaseRepository
from usuario.models import Perfil


class PerfilRepository(BaseRepository):
    def __init__(self):
        super().__init__(Perfil)

    def get_by_usuario(self, usuario_id):
        try:
            return Perfil.objects.get(usuario_id=usuario_id)
        except ObjectDoesNotExist:
            return None
