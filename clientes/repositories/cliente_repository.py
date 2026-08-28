from repository.base_repository import BaseRepository
from clientes.models import Cliente


class ClienteRepository(BaseRepository):
    def __init__(self):
        super().__init__(Cliente)
