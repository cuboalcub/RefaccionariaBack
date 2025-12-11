from repository.base_controller import BaseDetailController, BaseListController
from ventas.services.detalleventa_service import DetalleVentaService    

class DetalleVentaListCreate(BaseListController):
    def __init__(self):
        super().__init__(DetalleVentaService)

class DetalleVentaDetail(BaseDetailController):
    def __init__(self):
        super().__init__(DetalleVentaService)   