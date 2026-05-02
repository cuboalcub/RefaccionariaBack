from producto.repositories.producto_repository import ProductoRepository
from producto.models import Producto
from notifications.services.notification_service import NotificationService
from repository.base_service import BaseService
from producto.repositories.tipo_repository import TipoRepository
from producto.repositories.proveedor_repository import ProveedorRepository
from producto.repositories.movimiento_repository import MovimientoRepository

class ProductoService(BaseService):
    def __init__(self):
        super().__init__(model=Producto, repository=ProductoRepository())
        self.notification_service = NotificationService()
    

    def create(self, data):
        tipo = TipoRepository().get_by_id(data["id_tipo"])
        proveedor = ProveedorRepository().get_by_id(data["id_proveedor"])
        movimiento = MovimientoRepository().get_by_id(data["id_movimientos"])
        data["id_tipo"] = tipo
        data["id_proveedor"] = proveedor
        data["id_movimientos"] = movimiento
        producto_dict = super().create(data)
        producto_instance = self.repository.get_by_id(producto_dict["id"])
        self._create_stock_notification(producto_instance)
        return producto_dict

    def update(self, instance, data):
        tipo = TipoRepository().get_by_id(data["id_tipo"]) if "id_tipo" in data else instance.id_tipo
        proveedor = ProveedorRepository().get_by_id(data["id_proveedor"]) if "id_proveedor" in data else instance.id_proveedor
        movimiento = MovimientoRepository().get_by_id(data["id_movimientos"]) if "id_movimientos" in data else instance.id_movimientos

        data["id_tipo"] = tipo
        data["id_proveedor"] = proveedor
        data["id_movimientos"] = movimiento

        producto_dict = super().update(instance.id, data)

        producto_instance = self.repository.get_by_id(instance.id)

        self._create_stock_notification(producto_instance)

        return producto_dict

    def update_stock(self, producto_id, new_stock):
        producto = self.repository.get_by_id(producto_id)

        if not producto:
            return None

        updated_producto = self.repository.update(
            producto,
            {"existencia": new_stock}
        )

        if updated_producto:
            self._create_stock_notification(updated_producto)

        return updated_producto

    def _create_stock_notification(self, producto):
        if not producto:
            return None

        if producto.existencia == 0:
            mensaje = f"El producto '{producto.nombre}' está agotado."
            return self.notification_service.create_if_not_exists(producto, NotificationService.OUT_OF_STOCK, mensaje)

        if producto.existencia < producto.min_stock:
            mensaje = f"El producto '{producto.nombre}' tiene stock bajo ({producto.existencia} < {producto.min_stock})."
            return self.notification_service.create_if_not_exists(producto, NotificationService.LOW_STOCK, mensaje)

        return None


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
            "min_stock": instance.min_stock,
            "costo": str(instance.costo)
        }
