"""Tests ventas: VentaService (JWT/sucursal) + DetalleVenta (subtotal/stock/total) + API."""

import pytest
from decimal import Decimal

from inventario.repositories.stock_repository import StockRepository
from inventario.services.precio_sucursal_service import PrecioSucursalService
from ventas.models import Venta
from ventas.services.detalle_venta_service import DetalleVentaService
from ventas.services.venta_service import VentaService
from tests.factories import (
    MetodoPagoFactory,
    ProductoFactory,
    StockFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil


def _venta_base(user, sucursal, metodo):
    return VentaService().create(
        {
            "id_usuario": user.id,
            "id_sucursal": sucursal.id,
            "id_metodo_pago": metodo.id,
        }
    )


@pytest.mark.django_db
class TestVentaService:
    def test_create_con_sucursal(self):
        u = UserFactory()
        suc = SucursalFactory()
        mp = MetodoPagoFactory()
        res = _venta_base(u, suc, mp)
        assert res["id_usuario"] == u.id
        assert res["id_sucursal"] == suc.id
        assert "id_inventario" not in res
        assert Decimal(res["total"]) == Decimal("0.00")

    def test_create_via_jwt_deriva_sucursal(self):
        suc = SucursalFactory()
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        mp = MetodoPagoFactory()

        res = VentaService().create({"id_metodo_pago": mp.id}, user=u)
        assert res["id_usuario"] == u.id
        assert res["id_sucursal"] == suc.id
        assert "id_inventario" not in res

    def test_create_via_jwt_sin_sucursal_falla(self):
        u = UserFactory()
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="no tiene una sucursal"):
            VentaService().create({"id_metodo_pago": mp.id}, user=u)

    def test_create_sin_metodo_pago_falla(self):
        u = UserFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="id_metodo_pago"):
            VentaService().create({"id_usuario": u.id, "id_sucursal": suc.id})

    def test_get_all_filtra_por_sucursal(self):
        suc_a = SucursalFactory()
        suc_b = SucursalFactory()
        u = UserFactory()
        mp = MetodoPagoFactory()
        _venta_base(u, suc_a, mp)
        _venta_base(u, suc_b, mp)

        solo_a = VentaService().get_all(sucursal_id=suc_a.id)
        assert len(solo_a) == 1
        assert solo_a[0]["id_sucursal"] == suc_a.id


@pytest.mark.django_db
class TestDetalleVentaService:
    def _setup(self, precio_sucursal=None):
        suc = SucursalFactory()
        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        StockFactory(id_producto=prod, id_sucursal=suc, cantidad=10)
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
        v = _venta_base(u, suc, mp)
        return suc, prod, u, v

    def test_create_calcula_subtotal_y_total(self):
        suc, prod, u, v = self._setup()
        res = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2}, user=u
        )
        assert res["subtotal"] == "200.00"
        assert Venta.objects.get(id=v["id"]).total == Decimal("200.00")
        # stock descontado: 10 - 2
        assert StockRepository().get_stock(prod.id, suc.id) == 8

    def test_create_usa_precio_sucursal(self):
        suc, prod, u, v = self._setup(precio_sucursal="150.00")
        res = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2}, user=u
        )
        assert res["subtotal"] == "300.00"

    def test_create_sin_stock_falla(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        mp = MetodoPagoFactory()
        v = _venta_base(u, suc, mp)
        with pytest.raises(ValueError, match="no está disponible|Stock insuficiente"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1},
                user=u,
            )

    def test_cross_sucursal_bloqueado(self):
        suc_a = SucursalFactory()
        suc_b = SucursalFactory()
        prod = ProductoFactory()
        StockFactory(id_producto=prod, id_sucursal=suc_a, cantidad=10)
        user_b = UserFactory()
        Perfil.objects.create(usuario=user_b, id_sucursal=suc_b)
        owner_a = UserFactory()
        mp = MetodoPagoFactory()
        v = _venta_base(owner_a, suc_a, mp)
        with pytest.raises(ValueError, match="no puede ser operada"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1},
                user=user_b,
            )


@pytest.mark.django_db
class TestVentasAPI:
    def test_post_ventas_con_jwt(self, jwt_client, user, perfil):
        from ventas.models import MetodoPago

        mp = MetodoPago.objects.create(tipo="EFECTIVO", descripcion="cash")
        resp = jwt_client.post(
            "/api/ventas/", {"id_metodo_pago": mp.id}, format="json"
        )
        assert resp.status_code == 201, resp.content
        assert resp.data["id_sucursal"] == perfil.id_sucursal_id
        assert "id_inventario" not in resp.data

    def test_post_ventas_sin_auth_401(self, api_client):
        resp = api_client.post("/api/ventas/", {}, format="json")
        assert resp.status_code == 401

    def test_get_ventas_filtra_sucursal_usuario(self, auth_client, user, perfil):
        mp = MetodoPagoFactory()
        # venta de otra sucursal no debe verse
        otra_suc = SucursalFactory()
        otro_user = UserFactory()
        VentaService().create(
            {
                "id_usuario": otro_user.id,
                "id_sucursal": otra_suc.id,
                "id_metodo_pago": mp.id,
            }
        )
        VentaService().create(
            {
                "id_usuario": user.id,
                "id_sucursal": perfil.id_sucursal_id,
                "id_metodo_pago": mp.id,
            }
        )
        resp = auth_client.get("/api/ventas/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["id_sucursal"] == perfil.id_sucursal_id
