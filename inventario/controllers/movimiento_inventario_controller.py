from repository.base_controller import BaseListController, BaseDetailController

from inventario.services.movimiento_inventario_service import MovimientoInventarioService


class MovimientoInventarioListCreateView(BaseListController):
    permiso_get = "inventario.ver"
    permiso_post = "inventario.escribir"

    def __init__(self):
        super().__init__(MovimientoInventarioService)


class MovimientoInventarioDetailView(BaseDetailController):
    permiso_get = "inventario.ver"
    permiso_put = "inventario.escribir"
    permiso_delete = "inventario.escribir"

    def __init__(self):
        super().__init__(MovimientoInventarioService)
