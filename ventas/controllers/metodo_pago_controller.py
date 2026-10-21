from repository.base_controller import BaseListController, BaseDetailController
from ventas.services.metodo_pago_service import MetodoPagoService

PERM_CATALOGOS_ESCRIBIR = "catalogos.escribir"

class MetodoPagoListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = PERM_CATALOGOS_ESCRIBIR

    def __init__(self):
        super().__init__(MetodoPagoService)

class MetodoPagoDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = PERM_CATALOGOS_ESCRIBIR
    permiso_delete = PERM_CATALOGOS_ESCRIBIR

    def __init__(self):
        super().__init__(MetodoPagoService)