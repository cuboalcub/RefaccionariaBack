from repository.base_controller import BaseDetailController
from repository.base_controller import BaseListController
from producto.services.proveedor_service import ProveedorService

class ProveedorListCreateView(BaseListController):
    permiso_get = "catalogos.leer"
    permiso_post = "catalogos.crear"

    def __init__(self):
        super().__init__(ProveedorService)


class ProveedorDetailView(BaseDetailController):
    permiso_get = "catalogos.leer"
    permiso_put = "catalogos.escribir"
    permiso_delete = "catalogos.escribir"

    def __init__(self):
        super().__init__(ProveedorService)

