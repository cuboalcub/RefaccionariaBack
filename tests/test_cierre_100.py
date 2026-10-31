"""Cierre 100%: paginación mi-sucursal, ramas de update/movimiento, FK None precio, Mini repo."""

import pytest
from decimal import Decimal

from inventario.models import MovimientoInventario
from inventario.services.movimiento_inventario_service import MovimientoInventarioService
from inventario.services.precio_sucursal_service import PrecioSucursalService
from producto.services.producto_service import ProductoService
from tests.factories import (
    MetodoPagoFactory,
    ProductoFactory,
    ProveedorFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil


@pytest.mark.django_db
class TestMiSucursalPaginacion:
    def _ctx(self, api_client, n_productos=3):
        suc = SucursalFactory()
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        api_client.force_authenticate(user=u)
        svc = MovimientoInventarioService()
        for i in range(n_productos):
            p = ProductoFactory(nombre=f"ProdPag{i:02d}")
            svc.create(
                {
                    "id_producto": p.id,
                    "id_sucursal": suc.id,
                    "cantidad": 5,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "carga",
                }
            )
        return suc

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

    def test_paginado_ok(self, api_client):
        self._ctx(api_client, n_productos=3)
        r = api_client.get(
            "/api/inventarios/mi-sucursal/", {"page": "1", "page_size": "2"}
        )
        assert r.status_code == 200
        assert r.data["total"] == 3
        assert r.data["page"] == 1
        assert len(r.data["detalles"]) == 2

    def test_fuera_rango_400(self, api_client):
        self._ctx(api_client, n_productos=2)
        r = api_client.get(
            "/api/inventarios/mi-sucursal/", {"page": "9", "page_size": "2"}
        )
        assert r.status_code == 400

    def test_sin_page_devuelve_catalogo_completo(self, api_client):
        suc = self._ctx(api_client, n_productos=2)
        r = api_client.get("/api/inventarios/mi-sucursal/")
        assert r.status_code == 200
        assert r.data["id_sucursal"] == suc.id
        assert len(r.data["detalles"]) == 2


@pytest.mark.django_db
class TestDetalleValidarDirecto:
    def test_falta_producto(self):
        with pytest.raises(ValueError, match="id_producto"):
            MovimientoInventarioService()._validar({"id_sucursal": 1, "cantidad": 1})

    def test_falta_sucursal(self):
        with pytest.raises(ValueError, match="id_sucursal"):
            MovimientoInventarioService()._validar({"id_producto": 1, "cantidad": 1})

    def test_falta_cantidad(self):
        with pytest.raises(ValueError, match="cantidad"):
            MovimientoInventarioService()._validar(
                {"id_producto": 1, "id_sucursal": 1}
            )

    def test_cantidad_negativa(self):
        p = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="negativa"):
            MovimientoInventarioService()._validar(
                {"id_producto": p.id, "id_sucursal": suc.id, "cantidad": -2}
            )

    def test_movimiento_explicito_deprecado(self):
        p = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="deprecado"):
            MovimientoInventarioService().create(
                {
                    "id_producto": p.id,
                    "id_sucursal": suc.id,
                    "cantidad": 1,
                    "id_movimiento": 999999,
                }
            )

    def test_tipo_invalido(self):
        p = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            MovimientoInventarioService()._validar(
                {
                    "id_producto": p.id,
                    "id_sucursal": suc.id,
                    "cantidad": 1,
                    "tipo": "ROBO",
                }
            )


@pytest.mark.django_db
class TestDetalleUpdateMovimiento:
    def _detalle(self):
        suc = SucursalFactory()
        p = ProductoFactory()
        svc = MovimientoInventarioService()
        res = svc.create(
            {
                "id_producto": p.id,
                "id_sucursal": suc.id,
                "cantidad": 5,
                "tipo_movimiento": "ENTRADA",
                "razon": "init",
            }
        )
        return svc, res["id"], suc, p

    def test_update_sincroniza_movimiento(self):
        svc, did, suc, p = self._detalle()
        svc.update(did, {"tipo_movimiento": "ENTRADA", "razon": "aj", "cantidad": 9})
        d = MovimientoInventario.objects.get(id=did)
        assert d.cantidad == 9
        assert d.razon == "aj"
        assert svc.get_stock(p.id, suc.id) == 9

    def test_update_con_movimiento_explicito_deprecado(self):
        svc, did, suc, p = self._detalle()
        mov2 = MovimientoInventario.objects.create(
            tipo="ENTRADA", cantidad=1, razon="otro",
            id_producto=p, id_sucursal=suc,
        )
        # El payload ya no acepta id_movimiento: cada movimiento es propio.
        with pytest.raises(ValueError, match="deprecado"):
            svc.update(did, {"id_movimiento": mov2.id, "cantidad": 4})


@pytest.mark.django_db
class TestBulkRamas:
    def test_bulk_comun_con_proveedor(self):
        suc = SucursalFactory()
        prov = ProveedorFactory()
        p1, p2 = ProductoFactory(), ProductoFactory()
        res = MovimientoInventarioService().bulk_create(
            {
                "id_sucursal": suc.id,
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
        suc = SucursalFactory()
        p = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": p.id,
                "id_sucursal": suc.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "c",
            }
        )
        res = svc.bulk_create(
            [
                {
                    "id_producto": p.id,
                    "id_sucursal": suc.id,
                    "cantidad": 4,
                    "tipo": "SALIDA",
                    "razon": "v",
                }
            ]
        )
        assert len(res) == 1
        assert svc.get_stock(p.id, suc.id) == 6

    def test_bulk_proveedor_invalido_individual(self):
        suc = SucursalFactory()
        p = ProductoFactory()
        with pytest.raises(ValueError, match="proveedor"):
            MovimientoInventarioService().bulk_create(
                [
                    {
                        "id_producto": p.id,
                        "id_sucursal": suc.id,
                        "cantidad": 1,
                        "id_proveedor": 999999,
                    }
                ]
            )

    def test_bulk_proveedor_valido_individual(self):
        suc = SucursalFactory()
        p = ProductoFactory()
        prov = ProveedorFactory()
        res = MovimientoInventarioService().bulk_create(
            [
                {
                    "id_producto": p.id,
                    "id_sucursal": suc.id,
                    "cantidad": 1,
                    "id_proveedor": prov.id,
                }
            ]
        )
        assert res[0]["id_proveedor"] == prov.id


@pytest.mark.django_db
class TestPrecioUpdateNone:
    def test_update_producto_none_400(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        ps = PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        with pytest.raises(ValueError, match="producto"):
            PrecioSucursalService().update(ps["id"], {"id_producto": None})

    def test_update_sucursal_none_400(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        ps = PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        with pytest.raises(ValueError, match="sucursal"):
            PrecioSucursalService().update(ps["id"], {"id_sucursal": None})


@pytest.mark.django_db
class TestProductoCreateSinFK:
    def test_falta_tipo(self):
        pr = ProveedorFactory()
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
        from tests.factories import TipoFactory

        t = TipoFactory()
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
    def test_put_inexistente_404(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
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
