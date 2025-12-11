from repository.base_controller import BaseListController, BaseDetailController
from ventas.services.metodopago_service import MetodoPagoService

class MetodoPagoListCreateView(BaseListController):
    def __init__(self):
        super().__init__(MetodoPagoService)

class MetodoPagoDetailView(BaseDetailController):
    def __init__(self):
        super().__init__(MetodoPagoService)