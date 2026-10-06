"""Tests ventas: VentaService (JWT/inventario) + DetalleVenta (subtotal/stock/total) + API."""

import pytest
from decimal import Decimal
from django.contrib.auth.models import User

from inventario.models import Inventario
from inventario.services.detalle_inventario_service import DetalleInventarioService
from inventario.services.precio_sucursal_service import PrecioSucursalService
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


def _venta_base(user, inventario, metodo):
    return VentaService().create(
        {
            "id_usuario": user.id,
            "id_inventario": inventario.id,
            "id_metodoPago": metodo.id,
        }
    )


@pytest.mark.django_db
class TestVentaService:
    def test_create_legacy(self):
        u = UserFactory()
        inv = InventarioFactory()
        mp = MetodoPagoFactory()
        res = _venta_base(u, inv, mp)
        assert res["id_usuario"] == u.id
        assert res["id_inventario"] == inv.id
        assert Decimal(res["total"]) == Decimal("0.00")

    def test_create_via_jwt_deriva_inventario(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        mp = MetodoPagoFactory()

        res = VentaService().create({"id_metodoPago": mp.id}, user=u)
        assert res["id_usuario"] == u.id
        assert res["id_inventario"] == inv.id

    def test_create_via_jwt_sin_sucursal_falla(self):
        u = UserFactory()
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="no tiene una sucursal"):
            VentaService().create({"id_metodoPago": mp.id}, user=u)

    def test_create_sin_metodopago_falla(self):
        u = UserFactory()
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="id_metodoPago"):
            VentaService().create(
                {"id_usuario": u.id, "id_inventario": inv.id}
            )

    def test_get_all_filtra_por_sucursal(self):
        suc_a = SucursalFactory()
        suc_b = SucursalFactory()
        inv_a = InventarioFactory(id_sucursal=suc_a)
        inv_b = InventarioFactory(id_sucursal=suc_b)
        u = UserFactory()
        mp = MetodoPagoFactory()
        _venta_base(u, inv_a, mp)
        _venta_base(u, inv_b, mp)

        solo_a = VentaService().get_all(sucursal_id=suc_a.id)
        assert len(solo_a) == 1
        assert solo_a[0]["id_sucursal"] == suc_a.id


@pytest.mark.django_db
class TestDetalleVentaService:
    def _setup(self, precio_sucursal=None):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        DetalleInventarioService().create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        if precio_sucursal:
            PrecioSucursalService().create(
                {
                    "id_producto": prod.id,
                    "id_sucursal": suc.id,
                    "precio_venta": precio_sucursal,
                }
            )
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        mp = MetodoPagoFactory()
        v = _venta_base(u, inv, mp)
        return suc, inv, prod, u, v

    def test_create_calcula_subtotal_y_total(self):
        suc, inv, prod, u, v = self._setup()
        res = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2}, user=u
        )
        assert res["subtotal"] == "200.00"
        assert venta.objects.get(id=v["id"]).total == Decimal("200.00")
        # stock descontado: 10 - 2
        assert (
            DetalleInventarioService().get_stock(prod.id, inv.id) == 8
        )

    def test_create_usa_precio_sucursal(self):
        suc, inv, prod, u, v = self._setup(precio_sucursal="150.00")
        res = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2}, user=u
        )
        assert res["subtotal"] == "300.00"

    def test_create_sin_stock_falla(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory()
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        mp = MetodoPagoFactory()
        v = _venta_base(u, inv, mp)
        with pytest.raises(ValueError, match="no está disponible|Stock insuficiente"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1},
                user=u,
            )

    def test_cross_sucursal_bloqueado(self):
        suc_a = SucursalFactory()
        suc_b = SucursalFactory()
        inv_a = InventarioFactory(id_sucursal=suc_a)
        prod = ProductoFactory()
        DetalleInventarioService().create(
            {
                "id_producto": prod.id,
                "id_inventario": inv_a.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        user_b = UserFactory()
        Perfil.objects.create(usuario=user_b, id_sucursal=suc_b)
        owner_a = UserFactory()
        mp = MetodoPagoFactory()
        v = _venta_base(owner_a, inv_a, mp)
        with pytest.raises(ValueError, match="no puede ser operada"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1},
                user=user_b,
            )


@pytest.mark.django_db
class TestVentasAPI:
    def test_post_ventas_con_jwt(self, jwt_client, user, inventario):
        from ventas.models import metodoPago

        mp = metodoPago.objects.create(tipo="EFECTIVO", descripcion="cash")
        resp = jwt_client.post(
            "/api/ventas/", {"id_metodoPago": mp.id}, format="json"
        )
        assert resp.status_code == 201, resp.content
        assert resp.data["id_inventario"] == inventario.id

    def test_post_ventas_sin_auth_401(self, api_client):
        resp = api_client.post("/api/ventas/", {}, format="json")
        assert resp.status_code == 401

    def test_get_ventas_filtra_sucursal_usuario(self, auth_client, user, inventario):
        mp = MetodoPagoFactory()
        # venta de otra sucursal no debe verse
        otra_suc = SucursalFactory()
        otro_inv = Inventario.objects.create(
            id_sucursal=otra_suc, descripcion="otro"
        )
        otro_user = User.objects.create_user(username="otro")
        VentaService().create(
            {
                "id_usuario": otro_user.id,
                "id_inventario": otro_inv.id,
                "id_metodoPago": mp.id,
            }
        )
        VentaService().create(
            {
                "id_usuario": user.id,
                "id_inventario": inventario.id,
                "id_metodoPago": mp.id,
            }
        )
        resp = auth_client.get("/api/ventas/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["id_inventario"] == inventario.id
