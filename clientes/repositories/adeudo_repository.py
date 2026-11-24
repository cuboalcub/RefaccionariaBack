from repository.base_repository import BaseRepository
from clientes.models import Adeudo


class AdeudoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Adeudo)

    def get_all(self):
        return list(
            self.model_class.objects.select_related('id_cliente').order_by('-fecha', '-id')
        )

    def get_by_filters(self, filters):
        return list(
            self.model_class.objects.select_related('id_cliente')
            .filter(**filters)
            .order_by('-fecha', '-id')
        )
