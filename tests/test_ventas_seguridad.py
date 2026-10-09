"""Seguridad ventas: validación de cantidad legacy, PUT blindado,
auth en reporte y scoping por sucursal en detalle/venta.
"""

import pytest
from decimal import Decimal
from rest_framework.test import APIClient

from inventario.services.detalle_inventario_service import DetalleInventarioService
from ventas.models import venta
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


def _ctx(cantidad_entrada=10, precio=Decimal("100.00")):
    suc = SucursalFactory()
    inv = InventarioFactory(id_sucursal=suc)
    prod = ProductoFactory(precio_venta=precio)
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
        {"id_usuario": u.id, "id_inventario": inv.id, "id_metodoPago": mp.id}
    )
    return suc, inv, prod, u, mp, v


def _auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
class TestCantidadLegacy:
    def test_create_cantidad_cero_falla(self):
        _, _, prod, u, _, v = _ctx()
        with pytest.raises(ValueError, match="mayor a cero"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 0},
                user=u,
            )

    def test_create_cantidad_negativa_y_texto_fallan(self):
        _, _, prod, u, _, v = _ctx()
        with pytest.raises(ValueError, match="mayor a cero"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": -3},
                user=u,
            )
        with pytest.raises(ValueError, match="entero mayor a cero"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": "2"},
                user=u,
            )

    def test_create_producto_inexistente_404(self):
        _, _, _, u, _, v = _ctx()
        from repository.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            DetalleVentaService().create(
                {"id_producto": 999999, "id_venta": v["id"], "cantidad": 1},
                user=u,
            )

    def test_api_create_cantidad_cero_400_y_producto_404(self):
        _, inv, prod, u, _, v = _ctx()
        c = _auth(u)
        r0 = c.post(
            "/api/detalleventa/",
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 0},
            format="json",
        )
        assert r0.status_code == 400
        r404 = c.post(
            "/api/detalleventa/",
            {"id_producto": 999999, "id_venta": v["id"], "cantidad": 1},
            format="json",
        )
        assert r404.status_code == 404
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 10

    def test_update_cantidad_cero_falla(self):
        _, _, prod, u, _, v = _ctx()
        d = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2},
            user=u,
        )
        with pytest.raises(ValueError, match="mayor a cero"):
            DetalleVentaService().update(d["id"], {"cantidad": 0}, user=u)


@pytest.mark.django_db
class TestPutVentaBlindado:
    def test_put_total_se_ignora(self):
        _, _, prod, u, _, v = _ctx()
        DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2},
            user=u,
        )
        c = _auth(u)
        resp = c.put(f"/api/ventas/{v['id']}/", {"total": "99.00"}, format="json")
        assert resp.status_code == 200
        assert venta.objects.get(id=v["id"]).total == Decimal("200.00")

    def test_put_cambia_metodopago(self):
        _, _, _, u, _, v = _ctx()
        mp2 = MetodoPagoFactory(tipo="TARJETA", descripcion="Tarjeta")
        c = _auth(u)
        resp = c.put(
            f"/api/ventas/{v['id']}/", {"id_metodoPago": mp2.id}, format="json"
        )
        assert resp.status_code == 200
        assert venta.objects.get(id=v["id"]).id_metodoPago_id == mp2.id

    def test_put_metodopago_inexistente_y_basura_400(self):
        _, _, _, u, _, v = _ctx()
        c = _auth(u)
        assert (
            c.put(
                f"/api/ventas/{v['id']}/", {"id_metodoPago": 999999}, format="json"
            ).status_code
            == 400
        )
        assert (
            c.put(
                f"/api/ventas/{v['id']}/", {"id_metodoPago": "abc"}, format="json"
            ).status_code
            == 400
        )

    def test_update_con_instancia_metodopago(self):
        _, _, _, u, mp, v = _ctx()
        res = VentaService().update(v["id"], {"id_metodoPago": mp, "total": "5.00"})
        assert venta.objects.get(id=v["id"]).id_metodoPago_id == mp.id
        assert venta.objects.get(id=v["id"]).total == Decimal("0.00")


@pytest.mark.django_db
class TestReporteAuth:
    def test_anonimo_401(self, api_client):
        assert api_client.get("/api/reporte/", {"tipo": "day"}).status_code == 401


@pytest.mark.django_db
class TestScopingVentaDetalle:
    def _dos_sucursales(self):
        suc_a, inv_a, prod_a, u_a, mp_a, v_a = _ctx()
        suc_b = SucursalFactory()
        inv_b = InventarioFactory(id_sucursal=suc_b)
        u_b = UserFactory()
        Perfil.objects.create(usuario=u_b, id_sucursal=suc_b)
        d_a = DetalleVentaService().create(
            {"id_producto": prod_a.id, "id_venta": v_a["id"], "cantidad": 1},
            user=u_a,
        )
        return (suc_a, inv_a, prod_a, u_a, v_a, d_a, suc_b, inv_b, u_b)

    def test_venta_otra_sucursal_403(self):
        _, _, _, _, v_a, _, _, _, u_b = self._dos_sucursales()
        c = _auth(u_b)
        assert c.get(f"/api/ventas/{v_a['id']}/").status_code == 403
        assert (
            c.put(f"/api/ventas/{v_a['id']}/", {"total": "1.00"}, format="json").status_code
            == 403
        )
        assert c.delete(f"/api/ventas/{v_a['id']}/").status_code == 403
        assert venta.objects.filter(id=v_a["id"]).exists()

    def test_venta_otra_sucursal_staff_200(self, api_client, staff_user):
        _, _, _, _, v_a, _, _, _, _ = self._dos_sucursales()
        api_client.force_authenticate(user=staff_user)
        assert api_client.get(f"/api/ventas/{v_a['id']}/").status_code == 200

    def test_venta_usuario_sin_sucursal_400(self, api_client, user):
        _, _, _, _, v_a, _, _, _, _ = self._dos_sucursales()
        api_client.force_authenticate(user=user)
        assert api_client.get(f"/api/ventas/{v_a['id']}/").status_code == 400

    def test_detalle_otra_sucursal_403(self):
        _, _, _, _, _, d_a, _, _, u_b = self._dos_sucursales()
        c = _auth(u_b)
        assert c.get(f"/api/detalleventa/{d_a['id']}/").status_code == 403
        assert (
            c.put(
                f"/api/detalleventa/{d_a['id']}/", {"cantidad": 1}, format="json"
            ).status_code
            == 403
        )
        assert c.delete(f"/api/detalleventa/{d_a['id']}/").status_code == 403

    def test_detalle_otra_sucursal_staff_200(self, api_client, staff_user):
        _, _, _, _, _, d_a, _, _, _ = self._dos_sucursales()
        api_client.force_authenticate(user=staff_user)
        assert api_client.get(f"/api/detalleventa/{d_a['id']}/").status_code == 200

    def test_detalle_usuario_sin_sucursal_400(self, api_client, user):
        _, _, _, _, _, d_a, _, _, _ = self._dos_sucursales()
        api_client.force_authenticate(user=user)
        assert api_client.get(f"/api/detalleventa/{d_a['id']}/").status_code == 400
        assert (
            api_client.put(
                f"/api/detalleventa/{d_a['id']}/", {"cantidad": 1}, format="json"
            ).status_code
            == 400
        )
        assert api_client.delete(f"/api/detalleventa/{d_a['id']}/").status_code == 400

    def test_venta_put_usuario_sin_sucursal_400(self, api_client, user):
        _, _, _, _, v_a, _, _, _, _ = self._dos_sucursales()
        api_client.force_authenticate(user=user)
        assert (
            api_client.put(
                f"/api/ventas/{v_a['id']}/", {"total": "1.00"}, format="json"
            ).status_code
            == 400
        )
