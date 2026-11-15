from inventario.services.stock_service import StockService
from repository.permissions import es_staff, sucursal_de_usuario


class DetalleVentaValidacion:
    """Validaciones de alcance y disponibilidad para operar un detalle."""

    def __init__(self, stock_service=None):
        self.stock_service = stock_service or StockService()

    @staticmethod
    def validar_cantidad(cantidad):
        if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad <= 0:
            raise ValueError("La cantidad debe ser un entero mayor a cero")

    @staticmethod
    def validar_venta_operable(venta):
        """Las operaciones por detalle exigen venta completada y con sucursal."""
        if getattr(venta, 'estado', None) == 'cancelada':
            raise ValueError(f"La venta {venta.id} está cancelada y no admite cambios")
        if getattr(venta, 'id_sucursal_id', None) is None:
            raise ValueError("La venta no tiene sucursal asignada")

    @staticmethod
    def sucursal_id_de_venta(venta):
        return getattr(venta, 'id_sucursal_id', None)

    def validar_cross_sucursal(self, user, venta):
        user_sucursal_id = sucursal_de_usuario(user)
        # Si el usuario es staff/superuser, bypass (operador global)
        if user_sucursal_id is not None and not es_staff(user):
            sucursal_venta_id = self.sucursal_id_de_venta(venta)
            if sucursal_venta_id is not None and user_sucursal_id != sucursal_venta_id:
                raise ValueError(
                    f"La venta pertenece a la sucursal {sucursal_venta_id} y no puede ser operada por el usuario de la sucursal {user_sucursal_id}"
                )

    def validar_producto_en_inventario_sucursal(self, producto, venta, user=None):
        """Valida que el producto tenga stock >0 en la sucursal de la venta
        y que el usuario pertenezca a la misma sucursal (si tiene perfil)."""
        # Bloqueo cross-sucursal: si el usuario tiene perfil con sucursal, debe coincidir con la sucursal de la venta
        if user is not None:
            self.validar_cross_sucursal(user, venta)

        # Validación producto en sucursal: stock >0
        sucursal_id = self.sucursal_id_de_venta(venta)
        stock = self.stock_service.get_stock(producto.id, sucursal_id)
        if stock == 0:
            raise ValueError(
                f"El producto '{producto.nombre}' no está disponible en la sucursal {sucursal_id} - stock 0"
            )
