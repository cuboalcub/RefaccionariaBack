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

        user_repository = UserRepository()
        user = user_repository.get_by_id(data['id_usuario'])

        metodoPago_repository = MetodoPagoRepository()
        metodoPago = metodoPago_repository.get_by_id(data['id_metodoPago'])
        
        venta_data = {
            "id_usuario": user,
            "id_metodoPago": metodoPago,
            "total": data.get('total', 0)
        }
        venta = super().create(venta_data)
        
        return venta