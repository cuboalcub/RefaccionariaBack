"""Fase 4: flujos punta a punta (venta→ticket→reporte→reversión, gestión)."""

import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from inventario.services.movimiento_inventario_service import MovimientoInventarioService
from tests.factories import (
    MetodoPagoFactory,
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil
from ventas.services.reporte_venta_service import ReporteVentaService
from ventas.services.venta_ticket_service import VentaTicketService


def _auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _tienda(stock=10):
    suc = SucursalFactory()
    inv = suc
    prod = ProductoFactory(precio_venta=Decimal("100.00"))
    MovimientoInventarioService().create(
        {
            "id_producto": prod.id,
            "id_sucursal": inv.id,
            "cantidad": stock,
            "tipo_movimiento": "ENTRADA",
            "razon": "Compra",
        }
    )
    enc = UserFactory(username="enc_e2e")
    Perfil.objects.create(usuario=enc, id_sucursal=suc, rol="encargado")
    mp = MetodoPagoFactory()
    return suc, inv, prod, enc, mp


@pytest.mark.django_db
class TestFlujoVentaCompleta:
    def test_venta_ticket_reporte_reversion(self):
        suc, inv, prod, enc, mp = _tienda()
        c = _auth(enc)
        r = c.post(
            "/api/ventas/",
            {
                "id_metodo_pago": mp.id,
                "detalles": [{"producto": prod.id, "cantidad": 2}],
            },
            format="json",
        )
        assert r.status_code == 201
        vid = r.data["id"]
        assert r.data["total"] == "200.00"
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 8

        t = c.get(f"/api/ventas/{vid}/ticket/")
        assert t.status_code == 200
        assert t.data["total"] == "200.00"
        assert t.data["productos"][0]["cantidad"] == 2

        rep = ReporteVentaService().generar_reporte("day")
        assert vid in [x["id"] for x in rep["ventas"]]

        assert c.delete(f"/api/ventas/{vid}/").status_code == 200
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 10
        # Cancelación suave: la venta sobrevive con estado cancelada.
        detail = c.get(f"/api/ventas/{vid}/")
        assert detail.status_code == 200
        assert detail.data["estado"] == "cancelada"
        assert c.get(f"/api/ventas/{vid}/ticket/").status_code == 200
        # El reporte excluye canceladas.
        rep2 = ReporteVentaService().generar_reporte("day")
        assert vid not in [x["id"] for x in rep2["ventas"]]

    def test_venta_parcial_no_deja_rastro_via_api(self):
        suc, inv, prod, enc, mp = _tienda(stock=1)
        c = _auth(enc)
        from ventas.models import Venta

        n = Venta.objects.count()
        r = c.post(
            "/api/ventas/",
            {
                "id_metodo_pago": mp.id,
                "detalles": [
                    {"producto": prod.id, "cantidad": 1},
                    {"producto": prod.id, "cantidad": 5},
                ],
            },
            format="json",
        )
        assert r.status_code == 400
        assert Venta.objects.count() == n
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 1

    def test_ticket_directo_coincide_con_venta(self):
        from ventas.services.venta_service import VentaService

        _, _, prod, enc, mp = _tienda()
        res = VentaService().crear_venta_completa(
            {
                "id_metodo_pago": mp.id,
                "detalles": [{"producto": prod.id, "cantidad": 1}],
            },
            user=enc,
        )
        t = VentaTicketService().get_ticket(res["id"])
        assert t["total"] == res["total"]
        assert t["productos"][0]["subtotal"] == res["detalles"][0]["subtotal"]


@pytest.mark.django_db
class TestFlujoGestion:
    def test_admin_encargado_cajero_en_cadena(self):
        suc = SucursalFactory()
        staff = UserFactory(username="staff_e2e", is_staff=True)
        c_staff = _auth(staff)
        r = c_staff.post(
            "/api/users",
            {
                "username": "enc_cad",
                "password": "testpass123",
                "id_sucursal": suc.id,
                "rol": "encargado",
            },
            format="json",
        )
        assert r.status_code == 201
        enc = User.objects.get(username="enc_cad")
        r2 = _auth(enc).post(
            "/api/users",
            {"username": "caj_cad", "password": "testpass123"},
            format="json",
        )
        assert r2.status_code == 201
        assert Perfil.objects.get(usuario__username="caj_cad").rol == "cajero"
        # cajero vende pero no gestiona
        assert _auth(User.objects.get(username="caj_cad")).get("/api/users").status_code == 403
        # encargado desactiva: persiste en BD
        caj = User.objects.get(username="caj_cad")
        assert (
            _auth(enc).put(f"/api/users/{caj.id}", {"is_active": False}, format="json").status_code
            == 200
        )
        assert User.objects.get(username="caj_cad").is_active is False
