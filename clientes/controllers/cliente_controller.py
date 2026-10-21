from repository.base_controller import BaseListController, BaseDetailController

from clientes.services.cliente_service import ClienteService


class ClienteListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = "catalogos.crear"

    def __init__(self):
        super().__init__(ClienteService)


class ClienteDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = "catalogos.escribir"
    permiso_delete = "catalogos.escribir"

    def __init__(self):
        super().__init__(ClienteService)
