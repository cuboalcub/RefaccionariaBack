from repository.base_controller import BaseListController, BaseDetailController

from inventario.services.detalle_inventario_service import DetalleInventarioService


class DetalleInventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(DetalleInventarioService)


class DetalleInventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(DetalleInventarioService)
