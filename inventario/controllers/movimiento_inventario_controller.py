from repository.base_controller import BaseListController, BaseDetailController

from inventario.services.movimiento_inventario_service import MovimientoInventarioService


class MovimientoInventarioListCreateView(BaseListController):
    def __init__(self):
        super().__init__(MovimientoInventarioService)


class MovimientoInventarioDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(MovimientoInventarioService)
