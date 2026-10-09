"""Regresión Bug A: DELETE venta debe restaurar stock y no dejar huérfanos.

Cubre solo el punto 1: override de VentaService.delete con atomic +
reversión de inventario.
"""

import pytest
from decimal import Decimal

from inventario.models import DetalleInventario, MovimientoInventario
from inventario.services.detalle_inventario_service import DetalleInventarioService
from repository.exceptions import NotFoundError
from ventas.models import detalleVenta, venta
from ventas.services.detalleventa_service import DetalleVentaService
from ventas.services.ventas_services import VentaService
from tests.factories import (
    InventarioFactory,
    MetodoPagoFactory,
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil


def _setup_venta_con_stock(cantidad_entrada=10, cantidad_venta=2):
    suc = SucursalFactory()
    inv = InventarioFactory(id_sucursal=suc)
    prod = ProductoFactory(precio_venta=Decimal("100.00"))
    DetalleInventarioService().create(
        {
            "id_producto": prod.id,
            "id_inventario": inv.id,
            "cantidad": cantidad_entrada,
            "tipo_movimiento": "ENTRADA",
            "razon": "Compra",
        }
    )
    u = UserFactory()
    Perfil.objects.create(usuario=u, id_sucursal=suc)
    mp = MetodoPagoFactory()
    v = VentaService().create(
        {
            "id_usuario": u.id,
            "id_inventario": inv.id,
            "id_metodoPago": mp.id,
        }
    )
    DetalleVentaService().create(
        {"id_producto": prod.id, "id_venta": v["id"], "cantidad": cantidad_venta},
        user=u,
    )
    return suc, inv, prod, u, v


@pytest.mark.django_db
class TestDeleteVentaRestauraStock:
    def test_delete_un_detalle_restaura_stock(self):
        suc, inv, prod, u, v = _setup_venta_con_stock(
            cantidad_entrada=10, cantidad_venta=2
        )
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 8

        res = VentaService().delete(v["id"])
        assert "eliminado" in res["message"].lower()

        assert venta.objects.filter(id=v["id"]).count() == 0
        assert detalleVenta.objects.filter(id_venta_id=v["id"]).count() == 0
        # Stock restaurado y sin movimientos SALIDA huérfanos.
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 10
        assert (
            MovimientoInventario.objects.filter(
                tipo=MovimientoInventario.TipoMovimiento.SALIDA
            ).count()
            == 0
        )
        # Sin SALIDA huérfana: ningún DetalleInventario de tipo SALIDA
        # debe sobrevivir (la ENTRADA inicial sí tiene id_detalle_venta NULL
        # por diseño).
        assert DetalleInventario.objects.filter(
            id_movimiento__tipo=MovimientoInventario.TipoMovimiento.SALIDA
        ).count() == 0

    def test_delete_varios_detalles_restaura_todo(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod_a = ProductoFactory(precio_venta=Decimal("50.00"))
        prod_b = ProductoFactory(precio_venta=Decimal("30.00"))
        for prod in (prod_a, prod_b):
            DetalleInventarioService().create(
                {
                    "id_producto": prod.id,
                    "id_inventario": inv.id,
                    "cantidad": 10,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Compra",
                }
            )
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        mp = MetodoPagoFactory()
        v = VentaService().create(
            {
                "id_usuario": u.id,
                "id_inventario": inv.id,
                "id_metodoPago": mp.id,
            }
        )
        DetalleVentaService().create(
            {"id_producto": prod_a.id, "id_venta": v["id"], "cantidad": 2},
            user=u,
        )
        DetalleVentaService().create(
            {"id_producto": prod_b.id, "id_venta": v["id"], "cantidad": 3},
            user=u,
        )
        assert DetalleInventarioService().get_stock(prod_a.id, inv.id) == 8
        assert DetalleInventarioService().get_stock(prod_b.id, inv.id) == 7

        VentaService().delete(v["id"])

        assert DetalleInventarioService().get_stock(prod_a.id, inv.id) == 10
        assert DetalleInventarioService().get_stock(prod_b.id, inv.id) == 10
        assert detalleVenta.objects.filter(id_venta_id=v["id"]).count() == 0

    def test_delete_venta_sin_detalles_no_falla(self):
        u = UserFactory()
        inv = InventarioFactory()
        mp = MetodoPagoFactory()
        v = VentaService().create(
            {
                "id_usuario": u.id,
                "id_inventario": inv.id,
                "id_metodoPago": mp.id,
            }
        )
        res = VentaService().delete(v["id"])
        assert "eliminado" in res["message"].lower()
        assert venta.objects.filter(id=v["id"]).count() == 0

    def test_delete_venta_inexistente_404(self):
        with pytest.raises(NotFoundError):
            VentaService().delete(999999)

    def test_delete_es_atomico_si_falla_reversion(self, monkeypatch):
        """Si revertir un detalle falla, la venta NO debe borrarse parcial."""
        suc, inv, prod, u, v = _setup_venta_con_stock()

        def _boom(self, detalle):
            raise RuntimeError("fallo simulado de inventario")

        monkeypatch.setattr(
            DetalleInventarioService, "revertir_salida_por_venta", _boom
        )
        with pytest.raises(RuntimeError, match="fallo simulado"):
            VentaService().delete(v["id"])

        # Rollback completo: venta, detalle y descuento siguen intactos.
        assert venta.objects.filter(id=v["id"]).count() == 1
        assert detalleVenta.objects.filter(id_venta_id=v["id"]).count() == 1
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 8

    def test_api_delete_venta_restaura_stock(
        self, auth_client, user, inventario, perfil
    ):
        from tests.factories import ProductoFactory

        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        DetalleInventarioService().create(
            {
                "id_producto": prod.id,
                "id_inventario": inventario.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        mp = MetodoPagoFactory()
        resp = auth_client.post(
            "/api/ventas/", {"id_metodoPago": mp.id}, format="json"
        )
        assert resp.status_code == 201
        venta_id = resp.data["id"]
        d = auth_client.post(
            "/api/detalleventa/",
            {"id_producto": prod.id, "id_venta": venta_id, "cantidad": 2},
            format="json",
        )
        assert d.status_code == 201
        assert DetalleInventarioService().get_stock(prod.id, inventario.id) == 8

        dele = auth_client.delete(f"/api/ventas/{venta_id}/")
        assert dele.status_code == 200
        assert DetalleInventarioService().get_stock(prod.id, inventario.id) == 10
        assert auth_client.delete("/api/ventas/999999/").status_code == 404
