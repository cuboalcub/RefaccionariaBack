from producto.repositories.producto_repository import ProductoRepository
from producto.models import Producto
from repository.base_service import BaseService
from producto.repositories.tipo_repository import TipoRepository
from producto.repositories.proveedor_repository import ProveedorRepository
from producto.repositories.movimiento_repository import MovimientoRepository

class ProductoService(BaseService):
    def __init__(self):
        super().__init__(model=Producto, repository=ProductoRepository())
    

    def create(self, data):
        tipo = TipoRepository().get_by_id(data["id_tipo"])
        proveedor = ProveedorRepository().get_by_id(data["id_proveedor"])
        movimiento = MovimientoRepository().get_by_id(data["id_movimientos"])
        data["id_tipo"] = tipo
        data["id_proveedor"] = proveedor
        data["id_movimientos"] = movimiento
        return super().create(data)

    def update(self, instance, data):
        tipo = TipoRepository().get_by_id(data["id_tipo"])
        proveedor = ProveedorRepository().get_by_id(data["id_proveedor"])
        movimiento = MovimientoRepository().get_by_id(data["id_movimientos"])
        data["id_tipo"] = tipo
        data["id_proveedor"] = proveedor
        data["id_movimientos"] = movimiento
        return super().update(instance, data)




    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_tipo": instance.id_tipo.id if instance.id_tipo else None,
            "id_proveedor": instance.id_proveedor.id if instance.id_proveedor else None,
            "id_movimientos": instance.id_movimientos.id if instance.id_movimientos else None,
            "clave": instance.clave,
            "nombre": instance.nombre,
            "descripcion": instance.descripcion,
            "codigo_barras": instance.codigo_barras,
            "precio_venta": str(instance.precio_venta),
            "marca": instance.marca,
            "existencia": instance.existencia,
            "costo": str(instance.costo)
        }
