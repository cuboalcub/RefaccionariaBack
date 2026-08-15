from repository.base_controller import BaseListController, BaseDetailController

from sucursales.services.sucursal_service import SucursalService


class SucursalListCreateView(BaseListController):
    def __init__(self):
        super().__init__(SucursalService)


class SucursalDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(SucursalService)
