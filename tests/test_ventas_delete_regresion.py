"""Regresión Bug A: DELETE venta = cancelación suave.

El override de VentaService.delete con atomic + reversión de inventario
ahora deja la venta con estado 'cancelada' (sin borrarla) y el stock
restaurado, idempotente si se repite.
"""

import pytest
from decimal import Decimal

from inventario.models import MovimientoInventario
from inventario.services.movimiento_inventario_service import MovimientoInventarioService
from repository.exceptions import NotFoundError
from ventas.models import DetalleVenta, Venta
from ventas.services.detalle_venta_service import DetalleVentaService
from ventas.services.venta_service import VentaService
from tests.factories import (
    MetodoPagoFactory,
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil


def _setup_venta_con_stock(cantidad_entrada=10, cantidad_venta=2):
    suc = SucursalFactory()
    inv = suc
    prod = ProductoFactory(precio_venta=Decimal("100.00"))
    MovimientoInventarioService().create(
        {
            "id_producto": prod.id,
            "id_sucursal": inv.id,
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
            "id_sucursal": inv.id,
            "id_metodo_pago": mp.id,
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
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 8

        res = VentaService().delete(v["id"])
        assert "cancelada" in res["message"].lower()

        # La venta sobrevive con estado cancelada (historial intacto).
        venta = Venta.objects.get(id=v["id"])
        assert venta.estado == "cancelada"
        assert DetalleVenta.objects.filter(id_venta_id=v["id"]).count() == 1
        # Stock restaurado y sin movimientos SALIDA huérfanos.
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 10
        assert (
            MovimientoInventario.objects.filter(
                tipo=MovimientoInventario.TipoMovimiento.SALIDA
            ).count()
            == 0
        )

    def test_delete_varios_detalles_restaura_todo(self):
        suc = SucursalFactory()
        inv = suc
        prod_a = ProductoFactory(precio_venta=Decimal("50.00"))
        prod_b = ProductoFactory(precio_venta=Decimal("30.00"))
        for prod in (prod_a, prod_b):
            MovimientoInventarioService().create(
                {
                    "id_producto": prod.id,
                    "id_sucursal": inv.id,
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
                "id_sucursal": inv.id,
                "id_metodo_pago": mp.id,
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
        assert MovimientoInventarioService().get_stock(prod_a.id, inv.id) == 8
        assert MovimientoInventarioService().get_stock(prod_b.id, inv.id) == 7

        VentaService().delete(v["id"])

        assert MovimientoInventarioService().get_stock(prod_a.id, inv.id) == 10
        assert MovimientoInventarioService().get_stock(prod_b.id, inv.id) == 10
        assert Venta.objects.get(id=v["id"]).estado == "cancelada"

    def test_delete_es_idempotente(self):
        suc, inv, prod, u, v = _setup_venta_con_stock()
        VentaService().delete(v["id"])
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 10

        # Segunda cancelación no vuelve a revertir ni lanza.
        res = VentaService().delete(v["id"])
        assert "ya estaba cancelada" in res["message"]
        assert Venta.objects.get(id=v["id"]).estado == "cancelada"
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 10

    def test_delete_venta_sin_detalles_no_falla(self):
        u = UserFactory()
        inv = SucursalFactory()
        mp = MetodoPagoFactory()
        v = VentaService().create(
            {
                "id_usuario": u.id,
                "id_sucursal": inv.id,
                "id_metodo_pago": mp.id,
            }
        )
        res = VentaService().delete(v["id"])
        assert "cancelada" in res["message"].lower()
        assert Venta.objects.get(id=v["id"]).estado == "cancelada"

    def test_delete_venta_inexistente_404(self):
        with pytest.raises(NotFoundError):
            VentaService().delete(999999)

    def test_delete_es_atomico_si_falla_reversion(self, monkeypatch):
        """Si revertir un detalle falla, la venta NO debe borrarse parcial."""
        suc, inv, prod, u, v = _setup_venta_con_stock()

        def _boom(self, detalle):
            raise RuntimeError("fallo simulado de inventario")

        monkeypatch.setattr(
            MovimientoInventarioService, "revertir_salida_por_venta", _boom
        )
        with pytest.raises(RuntimeError, match="fallo simulado"):
            VentaService().delete(v["id"])

        # Rollback completo: venta completada, detalle y descuento intactos.
        assert Venta.objects.get(id=v["id"]).estado == "completada"
        assert DetalleVenta.objects.filter(id_venta_id=v["id"]).count() == 1
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 8

    def test_api_delete_venta_restaura_stock(
        self, auth_client, user, sucursal, perfil
    ):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])
        from tests.factories import ProductoFactory

        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        MovimientoInventarioService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": sucursal.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        mp = MetodoPagoFactory()
        resp = auth_client.post(
            "/api/ventas/",
            {
                "id_metodo_pago": mp.id,
                "detalles": [{"producto": prod.id, "cantidad": 2}],
            },
            format="json",
        )
        assert resp.status_code == 201
        venta_id = resp.data["id"]
        assert MovimientoInventarioService().get_stock(prod.id, sucursal.id) == 8

        dele = auth_client.delete(f"/api/ventas/{venta_id}/")
        assert dele.status_code == 200
        assert MovimientoInventarioService().get_stock(prod.id, sucursal.id) == 10
        assert Venta.objects.get(id=venta_id).estado == "cancelada"
        # Segundo DELETE: idempotente (200, sin doble reversión).
        assert auth_client.delete(f"/api/ventas/{venta_id}/").status_code == 200
        assert MovimientoInventarioService().get_stock(prod.id, sucursal.id) == 10
        assert auth_client.delete("/api/ventas/999999/").status_code == 404
