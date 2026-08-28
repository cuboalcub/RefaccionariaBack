from repository.base_controller import BaseListController, BaseDetailController

from clientes.services.cliente_service import ClienteService


class ClienteListCreateView(BaseListController):
    def __init__(self):
        super().__init__(ClienteService)


class ClienteDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(ClienteService)
