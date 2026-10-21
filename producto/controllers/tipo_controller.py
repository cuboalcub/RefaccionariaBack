from repository.base_controller import BaseListController, BaseDetailController

from producto.services.tipo_service import TipoService


class TipoListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = "catalogos.crear"

    def __init__(self):
        super().__init__(TipoService)


class TipoDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = "catalogos.escribir"
    permiso_delete = "catalogos.escribir"

    def __init__(self):
        super().__init__(TipoService)

