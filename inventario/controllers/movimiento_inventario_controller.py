from repository.base_controller import BaseListController, BaseDetailController

from inventario.services.movimiento_inventario_service import MovimientoInventarioService

PERM_MOVIMIENTO_VER = "inventario.ver"
PERM_MOVIMIENTO_ESCRIBIR = "inventario.escribir"


class MovimientoInventarioListCreateView(BaseListController):
    permiso_get = PERM_MOVIMIENTO_VER
    permiso_post = PERM_MOVIMIENTO_ESCRIBIR

    def __init__(self):
        super().__init__(MovimientoInventarioService)


class MovimientoInventarioDetailView(BaseDetailController):
    permiso_get = PERM_MOVIMIENTO_VER
    permiso_put = PERM_MOVIMIENTO_ESCRIBIR
    permiso_delete = PERM_MOVIMIENTO_ESCRIBIR

    def __init__(self):
        super().__init__(MovimientoInventarioService)
