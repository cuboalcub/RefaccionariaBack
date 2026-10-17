from repository.base_controller import BaseListController, BaseDetailController

from sucursales.services.sucursal_service import SucursalService

PERMISO_SUCURSALES_ADMIN = "sucursales.admin"


class SucursalListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = PERMISO_SUCURSALES_ADMIN

    def __init__(self):
        super().__init__(SucursalService)


class SucursalDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = PERMISO_SUCURSALES_ADMIN
    permiso_delete = PERMISO_SUCURSALES_ADMIN

    def __init__(self):
        super().__init__(SucursalService)
