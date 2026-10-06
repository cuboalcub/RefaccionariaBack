"""Tests inventario: DetalleInventario (stock/validaciones/bulk) + PrecioSucursal."""

import pytest
from decimal import Decimal

from inventario.services.detalle_inventario_service import DetalleInventarioService
from inventario.services.precio_sucursal_service import PrecioSucursalService
from tests.factories import (
    InventarioFactory,
    ProductoFactory,
    ProveedorFactory,
    SucursalFactory,
)


@pytest.mark.django_db
class TestDetalleInventario:
    def test_entrada_aumenta_stock(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()

        svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        assert svc.get_stock(prod.id, inv.id) == 10

    def test_salida_sin_stock_falla(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()

        with pytest.raises(ValueError, match="Stock insuficiente"):
            svc.create(
                {
                    "id_producto": prod.id,
                    "id_inventario": inv.id,
                    "cantidad": 5,
                    "tipo_movimiento": "SALIDA",
                    "razon": "Venta",
                }
            )

    def test_cantidad_negativa_falla(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()

        with pytest.raises(ValueError, match="no puede ser negativa"):
            svc.create(
                {
                    "id_producto": prod.id,
                    "id_inventario": inv.id,
                    "cantidad": -1,
                }
            )

    def test_create_con_proveedor_opcional(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        prov = ProveedorFactory()
        svc = DetalleInventarioService()

        res = svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "id_proveedor": prov.id,
                "cantidad": 3,
            }
        )
        assert res["id_proveedor"] == prov.id
        assert svc.get_stock(prod.id, inv.id) == 3

    def test_bulk_create_items(self):
        inv = InventarioFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        svc = DetalleInventarioService()

        res = svc.bulk_create(
            {
                "id_inventario": inv.id,
                "tipo_movimiento": "ENTRADA",
                "razon": "Carga inicial",
                "items": [
                    {"id_producto": p1.id, "cantidad": 5},
                    {"id_producto": p2.id, "cantidad": 7},
                ],
            }
        )
        assert len(res) == 2
        assert svc.get_stock(p1.id, inv.id) == 5
        assert svc.get_stock(p2.id, inv.id) == 7

    def test_bulk_vacio_falla(self):
        svc = DetalleInventarioService()
        with pytest.raises(ValueError, match="no puede estar vacía"):
            svc.bulk_create({"id_inventario": 1, "items": []})

    def test_inventario_por_sucursal_enriquece_precio(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        DetalleInventarioService().create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 4,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        PrecioSucursalService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "precio_venta": "120.00",
            }
        )
        data = DetalleInventarioService().get_inventario_por_sucursal(suc.id)
        assert len(data) == 1
        detalle = data[0]["detalles"][0]
        assert detalle["cantidad"] == 4
        assert detalle["precio_sucursal"] == "120.00"


@pytest.mark.django_db
class TestPrecioSucursal:
    def test_create_desactiva_anterior(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = PrecioSucursalService()

        p1 = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "100.00"}
        )
        p2 = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "150.00"}
        )
        assert p2["activo"] is True
        assert svc.get_precio_activo(prod.id, suc.id)["id"] == p2["id"]
        # el anterior quedó inactivo
        assert svc.get_historial(prod.id, suc.id)[0]["id"] == p2["id"]

    def test_precio_invalido_falla(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = PrecioSucursalService()
        with pytest.raises(ValueError, match="mayor a 0"):
            svc.create(
                {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "0"}
            )

    def test_resolver_precio_fallback(self):
        prod = ProductoFactory(precio_venta=Decimal("77.50"))
        suc = SucursalFactory()
        # sin precio activo -> fallback a producto
        assert PrecioSucursalService.resolver_precio_venta(prod, suc.id) == Decimal(
            "77.50"
        )
        PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "99.99"}
        )
        assert PrecioSucursalService.resolver_precio_venta(prod, suc.id) == Decimal(
            "99.99"
        )
