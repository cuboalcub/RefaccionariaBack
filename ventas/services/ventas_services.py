from ventas.services.detalleventa_service import DetalleVentaService
from ventas.models import venta
from ventas.repositories.ventas_repository import VentaRepository
from usuario.repositories.usuario_repositorie import UserRepository
from ventas.repositories.metodopago_repository import MetodoPagoRepository
from repository.base_service import BaseService
from producto.repositories.producto_repository import ProductoRepository    

class VentaService(BaseService):
    def __init__(self):
        super().__init__(model=venta, repository=VentaRepository())
    
    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_usuario": instance.id_usuario.id if instance.id_usuario else None,
            "id_metodoPago": instance.id_metodoPago.id if instance.id_metodoPago else None,
            "total": str(instance.total),
            "fecha": instance.fecha.isoformat() if instance.fecha else None
        }
    
    def create(self, data):
        # Repositorios y servicios necesarios
        user_repository = UserRepository()
        metodo_pago_repository = MetodoPagoRepository()
        producto_repository = ProductoRepository()
        detalle_venta_service = DetalleVentaService()

        # Obtener instancias de usuario y método de pago para la venta
        user = user_repository.get_by_id(data['id_usuario'])
        metodo_pago = metodo_pago_repository.get_by_id(data['id_metodoPago'])
        
        # Primero calculamos el total recorriendo los productos
        total = 0
        for item in data['productos']:
            producto_db = producto_repository.get_by_id(item['id'])
            if producto_db.existencia < item['cantidad']:
                raise ValueError("No hay suficiente stock para la venta")
            existencia = producto_db.existencia - item['cantidad']
            producto_repository.update(producto_db, {"existencia": existencia})
            total += producto_db.precio_venta * item['cantidad']

        # Preparamos los datos para crear la venta
        venta_data = {
            "id_usuario": user,
            "id_metodoPago": metodo_pago,
            "total": total
        }
        
        # Creamos la venta primero para obtener su ID
        # super().create retorna un diccionario con los datos de la venta creada
        venta_dict = super().create(venta_data)
        venta_id = venta_dict['id']

        # Ahora creamos los detalles de la venta usando el ID de la venta recién creada
        for item in data['productos']:
            detalle_venta_service.create({
                "id_producto": item['id'],
                "id_venta": venta_id,
                "cantidad": item['cantidad']
            })
        
        return venta_dict