from decimal import Decimal

from inventario.services.precio_sucursal_service import PrecioSucursalService
from ventas.repositories.detalle_venta_repository import DetalleVentaRepository
from ventas.repositories.venta_repository import VentaRepository
from ventas.services.iva import calcular_iva


class DetalleVentaCalculo:
    """Precio por sucursal, subtotal y recálculo del total de la venta."""

    def __init__(self, detalle_repo=None, venta_repo=None):
        self.repository = detalle_repo or DetalleVentaRepository()
        self.venta_repo = venta_repo or VentaRepository()

    @staticmethod
    def calcular_subtotal(precio_venta, cantidad):
        return (Decimal(precio_venta) * cantidad).quantize(Decimal("0.01"))

    @staticmethod
    def precio_aplicable(producto, venta):
        """Resuelve precio por sucursal si existe, sino fallback a Producto.precio_venta."""
        sucursal_id = venta.id_sucursal_id if venta else None
        precio = PrecioSucursalService.resolver_precio_venta(producto, sucursal_id)
        return precio if precio is not None else producto.precio_venta

    def recalcular_total(self, venta_id):
        base = self.repository.sum_subtotales(venta_id)
        iva = calcular_iva(base)
        total = base + iva
        venta = self.venta_repo.get_by_id(venta_id)
        if venta:
            venta.iva = iva
            venta.total = total
            venta.save(update_fields=["iva", "total"])
        return total
