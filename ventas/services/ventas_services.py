from ventas.services.detalleventa_service import DetalleVentaService
from ventas.models import venta
from ventas.repositories.ventas_repository import VentaRepository
from usuario.repositories.usuario_repositorie import UserRepository
from ventas.repositories.metodopago_repository import MetodoPagoRepository
from repository.base_service import BaseService
from producto.repositories.producto_repository import ProductoRepository
from inventario.models import Inventario

class VentaService(BaseService):
    def __init__(self, venta_repo=None, user_repo=None, metodopago_repo=None, producto_repo=None):
        super().__init__(model=venta, repository=venta_repo or VentaRepository())
        self.user_repo = user_repo or UserRepository()
        self.metodopago_repo = metodopago_repo or MetodoPagoRepository()
        self.producto_repo = producto_repo or ProductoRepository()

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_usuario": instance.id_usuario.id if instance.id_usuario else None,
            "id_metodoPago": instance.id_metodoPago.id if instance.id_metodoPago else None,
            "id_inventario": instance.id_inventario.id if instance.id_inventario else None,
            "total": str(instance.total),
            "fecha": instance.fecha.isoformat() if instance.fecha else None
        }

    def create(self, data):
        if "id_usuario" not in data or "id_metodoPago" not in data:
            raise ValueError("Faltan campos obligatorios: id_usuario, id_metodoPago")
        if "id_inventario" not in data or data["id_inventario"] is None:
            raise ValueError("Faltan campos obligatorios: id_inventario")

        user = self.user_repo.get_by_id(data['id_usuario'])
        if not user:
            raise ValueError(f"Usuario con id {data['id_usuario']} no encontrado")
        metodoPago = self.metodopago_repo.get_by_id(data['id_metodoPago'])
        if not metodoPago:
            raise ValueError(f"Metodo de pago con id {data['id_metodoPago']} no encontrado")
        inventario = Inventario.objects.filter(id=data['id_inventario']).first()
        if not inventario:
            raise ValueError(f"Inventario con id {data['id_inventario']} no encontrado")

        venta_data = {
            "id_usuario": user,
            "id_metodoPago": metodoPago,
            "id_inventario": inventario,
            "total": 0
        }
        venta = super().create(venta_data)

        return venta
