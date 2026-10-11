from repository.base_controller import BaseListController, BaseDetailController

from sucursales.services.sucursal_service import SucursalService


class SucursalListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = "sucursales.admin"

    def __init__(self):
        super().__init__(SucursalService)


class SucursalDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = "sucursales.admin"
    permiso_delete = "sucursales.admin"

    def __init__(self):
        super().__init__(SucursalService)
