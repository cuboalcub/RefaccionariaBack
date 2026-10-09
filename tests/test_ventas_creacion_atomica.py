"""Regresión Bug B: creación atómica venta + detalles (todo o nada)."""

import pytest
from decimal import Decimal

from inventario.models import MovimientoInventario
from inventario.services.detalle_inventario_service import DetalleInventarioService
from ventas.models import detalleVenta, venta
from ventas.services.ventas_services import VentaService
from tests.factories import (
    InventarioFactory,
    MetodoPagoFactory,
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil


def _stock(suc=None, inv=None, prod=None, cantidad=10):
    suc = suc or SucursalFactory()
    inv = inv or InventarioFactory(id_sucursal=suc)
    prod = prod or ProductoFactory(precio_venta=Decimal("100.00"))
    DetalleInventarioService().create(
        {
            "id_producto": prod.id,
            "id_inventario": inv.id,
            "cantidad": cantidad,
            "tipo_movimiento": "ENTRADA",
            "razon": "Compra",
        }
    )
    return suc, inv, prod


def _user_en(suc):
    u = UserFactory()
    Perfil.objects.create(usuario=u, id_sucursal=suc)
    return u


@pytest.mark.django_db
class TestCrearVentaCompleta:
    def test_exito_descuenta_todo_y_total(self):
        suc, inv, prod_a = _stock(cantidad=10)
        _, _, prod_b = _stock(suc=suc, inv=inv, cantidad=10)
        prod_b.precio_venta = Decimal("30.00")
        prod_b.save(update_fields=["precio_venta"])
        u = _user_en(suc)
        mp = MetodoPagoFactory()

        res = VentaService().crear_venta_completa(
            {
                "id_usuario": u.id,
                "id_inventario": inv.id,
                "id_metodoPago": mp.id,
                "detalles": [
                    {"producto": prod_a.id, "cantidad": 2},
                    {"id_producto": prod_b.id, "cantidad": 1},
                ],
            }
        )
        assert Decimal(res["total"]) == Decimal("230.00")
        assert len(res["detalles"]) == 2
        assert DetalleInventarioService().get_stock(prod_a.id, inv.id) == 8
        assert DetalleInventarioService().get_stock(prod_b.id, inv.id) == 9
        assert detalleVenta.objects.filter(id_venta_id=res["id"]).count() == 2
        assert (
            MovimientoInventario.objects.filter(
                tipo=MovimientoInventario.TipoMovimiento.SALIDA
            ).count()
            == 2
        )

    def test_fallo_segunda_linea_hace_rollback_total(self):
        suc, inv, prod_a = _stock(cantidad=10)
        _, _, prod_b = _stock(suc=suc, inv=inv, cantidad=0)
        # prod_b con stock 0: la entrada de cantidad 0 existe pero no suma.
        u = _user_en(suc)
        mp = MetodoPagoFactory()
        n_ventas = venta.objects.count()

        with pytest.raises(ValueError, match="Línea 1"):
            VentaService().crear_venta_completa(
                {
                    "id_usuario": u.id,
                    "id_inventario": inv.id,
                    "id_metodoPago": mp.id,
                    "detalles": [
                        {"producto": prod_a.id, "cantidad": 2},
                        {"producto": prod_b.id, "cantidad": 1},
                    ],
                }
            )
        # Nada escrito: sin venta huérfana, sin detalles, stock intacto.
        assert venta.objects.count() == n_ventas
        assert detalleVenta.objects.count() == 0
        assert DetalleInventarioService().get_stock(prod_a.id, inv.id) == 10
        assert (
            MovimientoInventario.objects.filter(
                tipo=MovimientoInventario.TipoMovimiento.SALIDA
            ).count()
            == 0
        )

    def test_producto_inexistente_error_por_linea_y_rollback(self):
        suc, inv, prod = _stock(cantidad=10)
        u = _user_en(suc)
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="Línea 1.*no existe"):
            VentaService().crear_venta_completa(
                {
                    "id_usuario": u.id,
                    "id_inventario": inv.id,
                    "id_metodoPago": mp.id,
                    "detalles": [
                        {"producto": prod.id, "cantidad": 1},
                        {"producto": 999999, "cantidad": 1},
                    ],
                }
            )
        assert venta.objects.count() == 0
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 10

    def test_cantidad_cero_y_negativa_rechazadas(self):
        suc, inv, prod = _stock(cantidad=10)
        u = _user_en(suc)
        mp = MetodoPagoFactory()
        base = {
            "id_usuario": u.id,
            "id_inventario": inv.id,
            "id_metodoPago": mp.id,
        }
        with pytest.raises(ValueError, match="mayor a cero"):
            VentaService().crear_venta_completa(
                {**base, "detalles": [{"producto": prod.id, "cantidad": 0}]}
            )
        with pytest.raises(ValueError, match="mayor a cero"):
            VentaService().crear_venta_completa(
                {**base, "detalles": [{"producto": prod.id, "cantidad": -2}]}
            )
        with pytest.raises(ValueError, match="entero positivo"):
            VentaService().crear_venta_completa(
                {**base, "detalles": [{"producto": prod.id, "cantidad": "2"}]}
            )
        assert venta.objects.count() == 0
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 10

    def test_producto_repetido_que_excede_stock_falla(self):
        suc, inv, prod = _stock(cantidad=3)
        u = _user_en(suc)
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="stock insuficiente"):
            VentaService().crear_venta_completa(
                {
                    "id_usuario": u.id,
                    "id_inventario": inv.id,
                    "id_metodoPago": mp.id,
                    "detalles": [
                        {"producto": prod.id, "cantidad": 2},
                        {"producto": prod.id, "cantidad": 2},
                    ],
                }
            )
        assert venta.objects.count() == 0
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 3

    def test_lineas_malformadas_error_por_linea(self):
        suc, inv, prod = _stock(cantidad=10)
        u = _user_en(suc)
        mp = MetodoPagoFactory()
        base = {
            "id_usuario": u.id,
            "id_inventario": inv.id,
            "id_metodoPago": mp.id,
        }
        with pytest.raises(ValueError, match="Línea 0.*formato inválido"):
            VentaService().crear_venta_completa(
                {**base, "detalles": ["no-un-dict"]}
            )
        with pytest.raises(ValueError, match="Línea 0.*falta id_producto"):
            VentaService().crear_venta_completa(
                {**base, "detalles": [{"cantidad": 2}]}
            )
        with pytest.raises(ValueError, match="Línea 0.*id inválido"):
            VentaService().crear_venta_completa(
                {**base, "detalles": [{"producto": "abc", "cantidad": 2}]}
            )
        assert venta.objects.count() == 0
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 10

    def test_sin_detalles_falla(self):
        suc, inv, prod = _stock()
        u = _user_en(suc)
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="detalles"):
            VentaService().crear_venta_completa(
                {
                    "id_usuario": u.id,
                    "id_inventario": inv.id,
                    "id_metodoPago": mp.id,
                    "detalles": [],
                }
            )

    def test_api_post_con_detalles_atomico(self, auth_client, user, inventario, perfil):
        prod_a = ProductoFactory(precio_venta=Decimal("100.00"))
        prod_b = ProductoFactory(precio_venta=Decimal("50.00"))
        for p, c in ((prod_a, 10), (prod_b, 1)):
            DetalleInventarioService().create(
                {
                    "id_producto": p.id,
                    "id_inventario": inventario.id,
                    "cantidad": c,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Compra",
                }
            )
        mp = MetodoPagoFactory()
        ok = auth_client.post(
            "/api/ventas/",
            {
                "id_metodoPago": mp.id,
                "detalles": [
                    {"producto": prod_a.id, "cantidad": 2},
                    {"producto": prod_b.id, "cantidad": 1},
                ],
            },
            format="json",
        )
        assert ok.status_code == 201
        assert Decimal(ok.data["total"]) == Decimal("250.00")
        assert len(ok.data["detalles"]) == 2

        n_ventas = venta.objects.count()
        bad = auth_client.post(
            "/api/ventas/",
            {
                "id_metodoPago": mp.id,
                "detalles": [
                    {"producto": prod_a.id, "cantidad": 1},
                    {"producto": prod_b.id, "cantidad": 5},
                ],
            },
            format="json",
        )
        assert bad.status_code == 400
        assert venta.objects.count() == n_ventas
        assert DetalleInventarioService().get_stock(prod_a.id, inventario.id) == 8

    def test_api_legacy_sin_detalles_sigue_igual(self, auth_client, user, inventario, perfil):
        mp = MetodoPagoFactory()
        resp = auth_client.post(
            "/api/ventas/", {"id_metodoPago": mp.id}, format="json"
        )
        assert resp.status_code == 201
        assert Decimal(resp.data["total"]) == Decimal("0.00")
        assert "detalles" not in resp.data
