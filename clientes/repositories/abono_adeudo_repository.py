from repository.base_repository import BaseRepository
from clientes.models import AbonoAdeudo


class AbonoAdeudoRepository(BaseRepository):
    def __init__(self):
        super().__init__(AbonoAdeudo)

    def get_all(self):
        return list(self.model_class.objects.order_by('-fecha', '-id'))

    def get_by_filters(self, filters):
        return list(
            self.model_class.objects.filter(**filters).order_by('-fecha', '-id')
        )
