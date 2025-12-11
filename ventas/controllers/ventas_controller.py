from ventas.services.ventas_services import VentaService
from repository.base_controller import BaseListController, BaseDetailController

class VentasListController(BaseListController):
    def __init__(self):
        super().__init__(VentaService)


class VentasDetailController(BaseDetailController):
    def __init__(self):
        super().__init__(VentaService)


