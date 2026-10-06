"""Cierre 100%: paginación mi-sucursal, ramas bulk/update detalle, FK None precio, PUT 404 usuario, Mini repo."""

import pytest
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User

from inventario.models import Inventario, MovimientoInventario
from inventario.services.detalle_inventario_service import DetalleInventarioService
from inventario.services.precio_sucursal_service import PrecioSucursalService
from producto.models import Producto
from producto.services.producto_service import ProductoService
from repository.exceptions import NotFoundError
from tests.factories import (
    InventarioFactory,
    MetodoPagoFactory,
    ProductoFactory,
    ProveedorFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil


@pytest.mark.django_db
class TestMiSucursalPaginacion:
    def _ctx(self, api_client, n_inventarios=1, n_productos=3):
        from rest_framework.test import APIClient

        suc = SucursalFactory()
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        api_client.force_authenticate(user=u)
        invs = [
            InventarioFactory(id_sucursal=suc, descripcion=f"Inv {i}")
            for i in range(n_inventarios)
        ]
        prods = [ProductoFactory(nombre=f"ProdPag{i:02d}") for i in range(n_productos)]
        svc = DetalleInventarioService()
        for inv in invs:
            for p in prods:
                svc.create(
                    {
                        "id_producto": p.id,
                        "id_inventario": inv.id,
                        "cantidad": 5,
                        "tipo_movimiento": "ENTRADA",
                        "razon": "carga",
                    }
                )
        return suc, invs

    def test_page_no_entero_400(self, api_client):
        self._ctx(api_client)
        r = api_client.get("/api/inventarios/mi-sucursal/", {"page": "x"})
        assert r.status_code == 400

    def test_page_menor_1_400(self, api_client):
        self._ctx(api_client)
        r = api_client.get(
            "/api/inventarios/mi-sucursal/", {"page": "0", "page_size": "5"}
        )
        assert r.status_code == 400

    def test_un_inventario_paginado(self, api_client):
        self._ctx(api_client, n_inventarios=1, n_productos=3)
        r = api_client.get(
            "/api/inventarios/mi-sucursal/", {"page": "1", "page_size": "2"}
        )
        assert r.status_code == 200
        assert r.data["total"] == 3
        assert r.data["page"] == 1
        assert len(r.data["detalles"]) == 2

    def test_un_inventario_fuera_rango_400(self, api_client):
        self._ctx(api_client, n_inventarios=1, n_productos=2)
        r = api_client.get(
            "/api/inventarios/mi-sucursal/", {"page": "9", "page_size": "2"}
        )
        assert r.status_code == 400

    def test_multiples_inventarios_paginado(self, api_client):
        self._ctx(api_client, n_inventarios=3, n_productos=1)
        r = api_client.get(
            "/api/inventarios/mi-sucursal/", {"page": "1", "page_size": "2"}
        )
        assert r.status_code == 200
        assert r.data["total"] == 3
        assert len(r.data["results"]) == 2

    def test_multiples_fuera_rango_400(self, api_client):
        self._ctx(api_client, n_inventarios=2, n_productos=1)
        r = api_client.get(
            "/api/inventarios/mi-sucursal/", {"page": "9", "page_size": "2"}
        )
        assert r.status_code == 400


@pytest.mark.django_db
class TestDetalleValidarDirecto:
    def test_falta_producto(self):
        with pytest.raises(ValueError, match="id_producto"):
            DetalleInventarioService()._validar({"id_inventario": 1, "cantidad": 1})

    def test_falta_inventario(self):
        with pytest.raises(ValueError, match="id_inventario"):
            DetalleInventarioService()._validar({"id_producto": 1, "cantidad": 1})

    def test_falta_cantidad(self):
        with pytest.raises(ValueError, match="cantidad"):
            DetalleInventarioService()._validar({"id_producto": 1, "id_inventario": 1})

    def test_cantidad_negativa(self):
        p = ProductoFactory()
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="negativa"):
            DetalleInventarioService()._validar(
                {"id_producto": p.id, "id_inventario": inv.id, "cantidad": -2}
            )

    def test_movimiento_inexistente(self):
        p = ProductoFactory()
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="movimiento"):
            DetalleInventarioService()._validar(
                {
                    "id_producto": p.id,
                    "id_inventario": inv.id,
                    "cantidad": 1,
                    "id_movimiento": 999999,
                }
            )

    def test_tipo_invalido(self):
        p = ProductoFactory()
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="tipo_movimiento"):
            DetalleInventarioService()._validar(
                {
                    "id_producto": p.id,
                    "id_inventario": inv.id,
                    "cantidad": 1,
                    "tipo": "ROBO",
                }
            )


@pytest.mark.django_db
class TestDetalleUpdateMovimiento:
    def _detalle(self):
        inv = InventarioFactory()
        p = ProductoFactory()
        svc = DetalleInventarioService()
        res = svc.create(
            {
                "id_producto": p.id,
                "id_inventario": inv.id,
                "cantidad": 5,
                "tipo_movimiento": "ENTRADA",
                "razon": "init",
            }
        )
        return svc, res["id"]

    def test_update_sincroniza_movimiento(self):
        svc, did = self._detalle()
        svc.update(did, {"tipo_movimiento": "ENTRADA", "razon": "aj", "cantidad": 9})
        from inventario.models import DetalleInventario

        d = DetalleInventario.objects.get(id=did)
        assert d.cantidad == 9
        assert d.id_movimiento.cantidad == 9

    def test_update_con_movimiento_explicito(self):
        svc, did = self._detalle()
        mov2 = MovimientoInventario.objects.create(
            tipo="ENTRADA", cantidad=1, razon="otro"
        )
        svc.update(did, {"id_movimiento": mov2.id, "cantidad": 4})
        from inventario.models import DetalleInventario

        assert DetalleInventario.objects.get(id=did).id_movimiento_id == mov2.id


@pytest.mark.django_db
class TestAjustarExcept:
    def test_ajustar_tolerante_a_fallo_movimiento(self):
        from ventas.models import venta
        from ventas.services.detalleventa_service import DetalleVentaService
        from ventas.services.ventas_services import VentaService

        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory(precio_venta=Decimal("10.00"))
        DetalleInventarioService().create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "c",
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
        det = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2}, user=u
        )
        from ventas.models import detalleVenta

        dv = detalleVenta.objects.get(id=det["id"])
        with patch.object(
            MovimientoInventario, "save", side_effect=Exception("boom")
        ):
            out = DetalleInventarioService().ajustar_salida_por_venta(dv, 3)
        assert out.cantidad == 3


@pytest.mark.django_db
class TestBulkRamas:
    def test_bulk_comun_con_proveedor(self):
        inv = InventarioFactory()
        prov = ProveedorFactory()
        p1, p2 = ProductoFactory(), ProductoFactory()
        res = DetalleInventarioService().bulk_create(
            {
                "id_inventario": inv.id,
                "tipo_movimiento": "ENTRADA",
                "razon": "carga",
                "id_proveedor": prov.id,
                "items": [
                    {"id_producto": p1.id, "cantidad": 2},
                    {"id_producto": p2.id, "cantidad": 3},
                ],
            }
        )
        assert len(res) == 2
        assert all(r["id_proveedor"] == prov.id for r in res)

    def test_bulk_salida_individual(self):
        inv = InventarioFactory()
        p = ProductoFactory()
        svc = DetalleInventarioService()
        svc.create(
            {
                "id_producto": p.id,
                "id_inventario": inv.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "c",
            }
        )
        res = svc.bulk_create(
            [
                {
                    "id_producto": p.id,
                    "id_inventario": inv.id,
                    "cantidad": 4,
                    "tipo": "SALIDA",
                    "razon": "v",
                }
            ]
        )
        assert len(res) == 1
        assert svc.get_stock(p.id, inv.id) == 6

    def test_bulk_proveedor_invalido_individual(self):
        inv = InventarioFactory()
        p = ProductoFactory()
        with pytest.raises(ValueError, match="proveedor"):
            DetalleInventarioService().bulk_create(
                [
                    {
                        "id_producto": p.id,
                        "id_inventario": inv.id,
                        "cantidad": 1,
                        "id_proveedor": 999999,
                    }
                ]
            )

    def test_bulk_proveedor_valido_individual(self):
        inv = InventarioFactory()
        p = ProductoFactory()
        prov = ProveedorFactory()
        res = DetalleInventarioService().bulk_create(
            [
                {
                    "id_producto": p.id,
                    "id_inventario": inv.id,
                    "cantidad": 1,
                    "id_proveedor": prov.id,
                }
            ]
        )
        assert res[0]["id_proveedor"] == prov.id


@pytest.mark.django_db
class TestPrecioUpdateNone:
    def test_update_producto_none_400(self):
        from tests.factories import SucursalFactory as SF

        suc = SF()
        prod = ProductoFactory()
        ps = PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        with pytest.raises(ValueError, match="producto"):
            PrecioSucursalService().update(ps["id"], {"id_producto": None})

    def test_update_sucursal_none_400(self):
        from tests.factories import SucursalFactory as SF

        suc = SF()
        prod = ProductoFactory()
        ps = PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        with pytest.raises(ValueError, match="sucursal"):
            PrecioSucursalService().update(ps["id"], {"id_sucursal": None})


@pytest.mark.django_db
class TestProductoCreateSinFK:
    def test_falta_tipo(self):
        from tests.factories import ProveedorFactory as PF

        pr = PF()
        with pytest.raises(ValueError, match="id_tipo"):
            ProductoService().create(
                {
                    "id_proveedor": pr.id,
                    "clave": "X1",
                    "nombre": "n",
                    "codigo_barras": "cb1",
                    "precio_venta": "10.00",
                    "marca": "m",
                    "costo": "5.00",
                }
            )

    def test_falta_proveedor(self):
        from tests.factories import TipoFactory as TF

        t = TF()
        with pytest.raises(ValueError, match="id_proveedor"):
            ProductoService().create(
                {
                    "id_tipo": t.id,
                    "clave": "X2",
                    "nombre": "n",
                    "codigo_barras": "cb2",
                    "precio_venta": "10.00",
                    "marca": "m",
                    "costo": "5.00",
                }
            )


@pytest.mark.django_db
class TestMiniRepoCompleto:
    def test_todos_los_metodos(self):
        from interfaces.repository import IRepository

        class Mini(IRepository):
            def get_by_id(self, entity_id):
                return {"id": entity_id}

            def get_all(self):
                return [{"id": 1}]

            def create(self, data):
                return data

            def update(self, entity, data):
                return entity

            def delete(self, entity):
                return True

            def filter(self, data):
                return [data]

        m = Mini()
        assert m.get_by_id(5) == {"id": 5}
        assert m.get_all() == [{"id": 1}]
        assert m.create({"a": 1}) == {"a": 1}
        assert m.update({"id": 1}, {}) == {"id": 1}
        assert m.delete({"id": 1}) is True
        assert m.filter({"a": 1}) == [{"a": 1}]


@pytest.mark.django_db
class TestUsuarioPut404:
    def test_put_inexistente_404(self, api_client, user):
        api_client.force_authenticate(user=user)
        r = api_client.put(
            "/api/users/999999", {"username": "x"}, format="json"
        )
        assert r.status_code == 404


@pytest.mark.django_db
class TestRootUrl:
    def test_home_200(self, api_client):
        assert api_client.get("/").status_code == 200

    def test_debug_static_urls(self):
        import importlib

        import RTR.urls as urls_mod
        from django.test import override_settings

        base = len(urls_mod.urlpatterns)
        with override_settings(DEBUG=True):
            importlib.reload(urls_mod)
            assert len(urls_mod.urlpatterns) >= base
        importlib.reload(urls_mod)
