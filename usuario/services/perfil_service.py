from usuario.models import Perfil
from usuario.repositories.perfil_repository import PerfilRepository
from repository.base_service import BaseService
from sucursales.models import Sucursal


class PerfilService(BaseService):
    def __init__(self, repository=None):
        super().__init__(model=Perfil, repository=repository or PerfilRepository())

    def get_by_usuario(self, usuario_id):
        perfil = self.repository.get_by_usuario(usuario_id)
        return self._to_dict(perfil)

    def get_or_create(self, usuario):
        perfil = self.repository.get_by_usuario(usuario.id)
        if not perfil:
            perfil = Perfil.objects.create(usuario=usuario)
        return self._to_dict(perfil)

    def update_by_usuario(self, usuario, data):
        perfil = self.repository.get_by_usuario(usuario.id)
        if not perfil:
            perfil = Perfil.objects.create(usuario=usuario)

        if "id_sucursal" in data:
            if not data["id_sucursal"]:
                perfil.id_sucursal = None
            else:
                if not Sucursal.objects.filter(id=data["id_sucursal"]).exists():
                    raise ValueError("La sucursal indicada no existe")
                perfil.id_sucursal = Sucursal.objects.get(id=data["id_sucursal"])
        perfil.save()
        return self._to_dict(perfil)

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "id_usuario": instance.usuario_id,
            "id_sucursal": instance.id_sucursal_id,
        }
