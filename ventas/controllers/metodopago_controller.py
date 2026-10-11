from repository.base_controller import BaseListController, BaseDetailController
from ventas.services.metodopago_service import MetodoPagoService

class MetodoPagoListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = "catalogos.escribir"

    def __init__(self):
        super().__init__(MetodoPagoService)

class MetodoPagoDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = "catalogos.escribir"
    permiso_delete = "catalogos.escribir"

    def __init__(self):
        super().__init__(MetodoPagoService)