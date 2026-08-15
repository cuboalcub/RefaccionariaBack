from repository.base_controller import BaseListController, BaseDetailController

from inventario.services.inventario_service import InventarioService


class InventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(InventarioService)


class InventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(InventarioService)
