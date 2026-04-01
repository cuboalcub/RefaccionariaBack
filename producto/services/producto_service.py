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


    def get_all(self, page: int = None, page_size: int = 10):
        """Devuelve productos con paginación opcional."""
        try:
            all_instances = self.repository.get_all()
            total = len(all_instances)

            if page is not None:
                start = (page - 1) * page_size
                end = start + page_size
                instances = all_instances[start:end]
                import math
                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": math.ceil(total / page_size),
                    "results": [self._to_dict(i) for i in instances],
                }

            return [self._to_dict(i) for i in all_instances]
        except Exception as e:
            raise ValueError(f"Error al obtener productos: {str(e)}")

    def get_by_codigo_barras(self, codigo_barras):
        producto = self.repository.get_by_codigo_barras(codigo_barras)
        if producto:
            return self._to_dict(producto)
        return None

    def get_by_categoria(self, categoria):
        producto = self.repository.get_by_categoria(categoria) 
        if producto:
            return [self._to_dict(i) for i in producto]
        return None

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



