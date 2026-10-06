"""Tests ~100% producto + sucursales: services, repositories, controllers, models."""

from decimal import Decimal
from unittest import mock

import pytest
from rest_framework.test import APIClient

from producto.models import Producto, Proveedor, Tipo
from producto.repositories.producto_repository import ProductoRepository
from producto.repositories.proveedor_repository import ProveedorRepository
from producto.repositories.tipo_repository import TipoRepository
from producto.services.producto_service import ProductoService
from producto.services.proveedor_service import ProveedorService
from producto.services.tipo_service import TipoService
from sucursales.models import Sucursal
from sucursales.repositories.sucursal_repository import SucursalRepository
from sucursales.services.sucursal_service import SucursalService
from inventario.services.detalle_inventario_service import DetalleInventarioService
from inventario.services.precio_sucursal_service import PrecioSucursalService
from tests.factories import (
    InventarioFactory,
    ProductoFactory,
    ProveedorFactory,
    SucursalFactory,
    TipoFactory,
    UserFactory,
)


def _auth():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _producto_payload(tipo=None, proveedor=None, **kw):
    tipo = tipo or TipoFactory()
    proveedor = proveedor or ProveedorFactory()
    n = Producto.objects.count()
    data = {
        "id_tipo": tipo.id,
        "id_proveedor": proveedor.id,
        "clave": f"CL-{n}-X",
        "nombre": f"Prod {n}",
        "codigo_barras": f"CB{n:08d}X",
        "precio_venta": "100.00",
        "marca": "MarcaX",
        "costo": "50.00",
    }
    data.update(kw)
    return data


def _dar_stock(producto, sucursal, cantidad=5):
    inv = InventarioFactory(id_sucursal=sucursal)
    DetalleInventarioService().create(
        {
            "id_producto": producto.id,
            "id_inventario": inv.id,
            "cantidad": cantidad,
            "tipo_movimiento": "ENTRADA",
            "razon": "Compra",
        }
    )
    return inv


@pytest.mark.django_db
class TestProductoService:
    def test_create_ok(self):
        svc = ProductoService()
        res = svc.create(_producto_payload())
        assert res["clave"].startswith("CL-")
        assert Producto.objects.filter(id=res["id"]).exists()

    def test_update_con_fk(self):
        p = ProductoFactory()
        t2 = TipoFactory()
        pr2 = ProveedorFactory()
        res = ProductoService().update(p.id, {"id_tipo": t2.id, "id_proveedor": pr2.id, "nombre": "Nuevo"})
        assert res["id_tipo"] == t2.id and res["id_proveedor"] == pr2.id
        assert res["nombre"] == "Nuevo"

    def test_update_sin_fk(self):
        p = ProductoFactory()
        res = ProductoService().update(p.id, {"marca": "Otra"})
        assert res["marca"] == "Otra"

    def test_get_all_sin_sucursal_lista(self):
        ProductoFactory()
        ProductoFactory()
        assert len(ProductoService().get_all()) >= 2

    def test_get_all_sin_sucursal_paginado(self):
        for _ in range(3):
            ProductoFactory()
        res = ProductoService().get_all(page=1, page_size=2)
        assert res["total"] >= 3 and len(res["results"]) == 2
        assert res["total_pages"] >= 2 and res["page"] == 1

    def test_get_all_search_sin_sucursal(self):
        ProductoFactory(nombre="FiltroEspecialABC", clave="ZZZ1", marca="MMM1")
        res = ProductoService().get_all(search="FiltroEspecialABC")
        assert len(res) == 1

    def test_get_all_filtros_sin_sucursal(self):
        t = TipoFactory()
        pr = ProveedorFactory()
        p = ProductoFactory(id_tipo=t, id_proveedor=pr, clave="CLAVEUNIQA",
                            marca="MARCAUNIQA", codigo_barras="CBUNIQA123")
        assert len(ProductoService().get_all(clave="CLAVEUNIQA")) == 1
        assert len(ProductoService().get_all(marca="MARCAUNIQA")) == 1
        assert len(ProductoService().get_all(codigo_barras="CBUNIQA123")) == 1
        assert len(ProductoService().get_all(tipo_id=t.id)) >= 1
        assert len(ProductoService().get_all(proveedor_id=pr.id)) >= 1
        assert ProductoService().get_all(tipo_id=999999) == []
        assert p.id

    def test_get_all_con_sucursal_enriquecido(self):
        suc = SucursalFactory()
        p = ProductoFactory(precio_venta=Decimal("100.00"))
        _dar_stock(p, suc, cantidad=4)
        PrecioSucursalService().create(
            {"id_producto": p.id, "id_sucursal": suc.id, "precio_venta": "120.00"}
        )
        res = ProductoService().get_all(sucursal_id=suc.id)
        assert len(res) == 1
        d = res[0]
        assert d["cantidad"] == 4 and d["id_sucursal"] == suc.id
        assert d["precio_sucursal"] == "120.00"
        assert d["precio_base"] == d["precio_venta"]
        assert "vigente_desde" in d

    def test_get_all_con_sucursal_sin_precio(self):
        suc = SucursalFactory()
        p = ProductoFactory()
        _dar_stock(p, suc)
        res = ProductoService().get_all(sucursal_id=suc.id)
        assert res[0]["precio_sucursal"] is None

    def test_get_all_con_sucursal_paginado(self):
        suc = SucursalFactory()
        for _ in range(3):
            _dar_stock(ProductoFactory(), suc)
        res = ProductoService().get_all(sucursal_id=suc.id, page=1, page_size=2)
        assert res["total"] == 3 and len(res["results"]) == 2
        assert res["total_pages"] == 2

    def test_get_all_con_sucursal_filtros(self):
        suc = SucursalFactory()
        t = TipoFactory()
        pr = ProveedorFactory()
        p_ok = ProductoFactory(id_tipo=t, id_proveedor=pr, nombre="BuscadoXYZ",
                               clave="CLXYZ", marca="MXYZ", codigo_barras="CBXYZ999")
        _dar_stock(p_ok, suc)
        _dar_stock(ProductoFactory(nombre="Otro", clave="OTRO1", marca="OTROM"), suc)
        assert len(ProductoService().get_all(sucursal_id=suc.id, search="BuscadoXYZ")) == 1
        assert len(ProductoService().get_all(sucursal_id=suc.id, clave="CLXYZ")) == 1
        assert len(ProductoService().get_all(sucursal_id=suc.id, marca="MXYZ")) == 1
        assert len(ProductoService().get_all(sucursal_id=suc.id, codigo_barras="CBXYZ999")) == 1
        assert len(ProductoService().get_all(sucursal_id=suc.id, tipo_id=t.id)) == 1
        assert len(ProductoService().get_all(sucursal_id=suc.id, proveedor_id=pr.id)) == 1
        assert ProductoService().get_all(sucursal_id=suc.id, search="ZZZSINNADA") == []

    def test_get_all_sucursal_sin_stock_lista(self):
        suc = SucursalFactory()
        assert ProductoService().get_all(sucursal_id=suc.id) == []

    def test_get_all_sucursal_sin_stock_paginado(self):
        suc = SucursalFactory()
        res = ProductoService().get_all(sucursal_id=suc.id, page=1, page_size=10)
        assert res["total"] == 0 and res["results"] == [] and res["total_pages"] == 0

    def test_get_all_sucursal_inexistente(self):
        with pytest.raises(ValueError, match="no encontrada"):
            ProductoService().get_all(sucursal_id=999999)

    def test_get_all_error_generico(self):
        svc = ProductoService()
        svc.repository = mock.MagicMock()
        svc.repository.get_all.side_effect = RuntimeError("boom")
        with pytest.raises(ValueError, match="Error al obtener productos"):
            svc.get_all()

    def test_get_by_codigo_barras_found(self):
        p = ProductoFactory(codigo_barras="CB-FIND-001")
        res = ProductoService().get_by_codigo_barras("CB-FIND-001")
        assert res["id"] == p.id

    def test_get_by_codigo_barras_none(self):
        assert ProductoService().get_by_codigo_barras("NO-EXISTE") is None

    def test_to_dict_fks_nulas(self):
        p = Producto.objects.create(
            clave="CL-NULLFK", nombre="Sin FK", codigo_barras="CB-NULLFK",
            precio_venta=Decimal("10.00"), marca="M", costo=Decimal("5.00"),
            id_tipo=None, id_proveedor=None,
        )
        d = ProductoService()._to_dict(p)
        assert d["id_tipo"] is None and d["id_proveedor"] is None
        assert d["precio_venta"] == "10.00" and d["costo"] == "5.00"


@pytest.mark.django_db
class TestTipoProveedor:
    # --- services ---
    def test_tipo_crud(self):
        svc = TipoService()
        created = svc.create({"nombre": "Tipo A"})
        assert created["nombre"] == "Tipo A"
        assert len(svc.get_all()) >= 1
        got = svc.get_by_id(created["id"])
        assert got["nombre"] == "Tipo A"
        upd = svc.update(created["id"], {"nombre": "Tipo B"})
        assert upd["nombre"] == "Tipo B"
        assert svc.delete(created["id"])["message"]
        with pytest.raises(Exception):
            svc.get_by_id(created["id"])

    def test_proveedor_crud(self):
        svc = ProveedorService()
        created = svc.create({"nombre": "Prov", "direccion": "Calle 1",
                              "telefono": "5551234", "correo": "a@b.com"})
        assert created["telefono"] == "5551234"
        assert len(svc.get_all()) >= 1
        got = svc.get_by_id(created["id"])
        assert got["correo"] == "a@b.com"
        upd = svc.update(created["id"], {"nombre": "Prov 2"})
        assert upd["nombre"] == "Prov 2"
        assert svc.delete(created["id"])["message"]

    def test_tipo_to_dict(self):
        t = TipoFactory()
        assert TipoService()._to_dict(t) == {"id": t.id, "nombre": t.nombre}

    def test_proveedor_to_dict(self):
        pr = ProveedorFactory()
        d = ProveedorService()._to_dict(pr)
        assert d["nombre"] == pr.nombre and d["telefono"] == pr.telefono

    def test_modelos_str(self):
        assert str(TipoFactory(nombre="TN")) == "TN"
        assert str(ProveedorFactory(nombre="PN")) == "PN"
        assert str(ProductoFactory(nombre="PDN")) == "PDN"

    # --- repositories ---
    def test_producto_repo_codigo_barras(self):
        p = ProductoFactory(codigo_barras="CB-REPO-1")
        assert ProductoRepository().get_by_codigo_barras("CB-REPO-1").id == p.id
        assert ProductoRepository().get_by_codigo_barras("NADA") is None

    def test_producto_repo_categoria(self):
        t = TipoFactory(nombre="CatUnica")
        p = ProductoFactory(id_tipo=t)
        assert list(ProductoRepository().get_by_categoria("CatUnica"))[0].id == p.id
        assert list(ProductoRepository().get_by_categoria("OtraCat")) == []

    def test_producto_repo_search(self):
        ProductoFactory(nombre="SearchUnicoQ", clave="CLSQ", marca="MSQ")
        assert len(list(ProductoRepository().search("SearchUnicoQ"))) == 1
        assert len(list(ProductoRepository().search("CLSQ"))) == 1
        assert len(list(ProductoRepository().search("MSQ"))) == 1
        assert list(ProductoRepository().search("ZZZNADA")) == []

    def test_repos_base_ops(self):
        for repo_cls, factory in [(TipoRepository, TipoFactory),
                                  (ProveedorRepository, ProveedorFactory),
                                  (ProductoRepository, ProductoFactory),
                                  (SucursalRepository, SucursalFactory)]:
            repo = repo_cls()
            obj = factory()
            assert repo.get_by_id(obj.id).id == obj.id
            assert repo.get_by_id(999999) is None
            assert len(repo.get_all()) >= 1
            assert len(repo.filter({"id": obj.id})) == 1

    def test_repo_create_update_delete(self):
        repo = TipoRepository()
        obj = repo.create({"nombre": "RC"})
        assert obj.id
        repo.update(obj, {"nombre": "RC2"})
        obj.refresh_from_db()
        assert obj.nombre == "RC2"
        assert repo.delete(obj) is True
        assert repo.delete(obj) is False


@pytest.mark.django_db
class TestProductoControllers:
    def test_list(self):
        ProductoFactory()
        r = _auth().get("/api/productos/")
        assert r.status_code == 200 and len(r.json()) >= 1

    def test_list_search_paginacion(self):
        ProductoFactory(nombre="CtrlSearchA")
        c = _auth()
        assert len(c.get("/api/productos/", {"search": "CtrlSearchA"}).json()) == 1
        r = c.get("/api/productos/", {"page": 1, "page_size": 1})
        assert r.status_code == 200 and r.json()["total"] >= 1
        assert len(r.json()["results"]) == 1
        r = c.get("/api/productos/", {"clave": "NOEXISTEZZZ"})
        assert r.json() == []

    def test_list_sucursal_id(self):
        suc = SucursalFactory()
        _dar_stock(ProductoFactory(), suc)
        c = _auth()
        r = c.get("/api/productos/", {"sucursal_id": suc.id})
        assert r.status_code == 200 and len(r.json()) == 1
        r = c.get("/api/productos/", {"sucursal_id": suc.id, "page": 1, "page_size": 5})
        assert r.json()["total"] == 1
        r = c.get("/api/productos/", {"sucursal_id": suc.id, "search": "ZZZNADA"})
        assert r.json() == []

    def test_list_sucursal_inexistente_400(self):
        r = _auth().get("/api/productos/", {"sucursal_id": 999999})
        assert r.status_code == 400

    def test_list_params_invalidos(self):
        c = _auth()
        assert c.get("/api/productos/", {"sucursal_id": "abc"}).status_code == 400
        assert c.get("/api/productos/", {"tipo_id": "abc"}).status_code == 400
        assert c.get("/api/productos/", {"proveedor_id": "abc"}).status_code == 400

    def test_list_filtros_extra(self):
        t = TipoFactory()
        pr = ProveedorFactory()
        ProductoFactory(id_tipo=t, id_proveedor=pr, clave="CLCTRL1", marca="MC1",
                        codigo_barras="CBCTRL1", nombre="CtrlFilt")
        c = _auth()
        assert len(c.get("/api/productos/", {"tipo_id": t.id}).json()) >= 1
        assert len(c.get("/api/productos/", {"proveedor_id": pr.id}).json()) >= 1
        assert len(c.get("/api/productos/", {"id_tipo": t.id}).json()) >= 1
        assert len(c.get("/api/productos/", {"id_proveedor": pr.id}).json()) >= 1
        assert len(c.get("/api/productos/", {"clave": "CLCTRL1"}).json()) == 1
        assert len(c.get("/api/productos/", {"marca": "MC1"}).json()) == 1
        assert len(c.get("/api/productos/", {"codigo_barras": "CBCTRL1"}).json()) == 1
        assert len(c.get("/api/productos/", {"query": "x", "categoria": "y"}).json()) >= 1

    def test_create_ok_y_error(self):
        c = _auth()
        r = c.post("/api/productos/", _producto_payload(), format="json")
        assert r.status_code == 201
        r = c.post("/api/productos/", {"nombre": "incompleto",
                        "id_tipo": 999999, "id_proveedor": 999999},
                   format="json")
        assert r.status_code == 400

    def test_detail_crud(self):
        c = _auth()
        pid = c.post("/api/productos/", _producto_payload(), format="json").json()["id"]
        assert c.get(f"/api/productos/{pid}/").status_code == 200
        assert c.put(f"/api/productos/{pid}/", {"marca": "M2"}, format="json").status_code == 200
        assert c.delete(f"/api/productos/{pid}/").status_code == 200
        assert c.get(f"/api/productos/{pid}/").status_code == 404
        assert c.put("/api/productos/999999/", {"marca": "x"}, format="json").status_code == 404
        assert c.delete("/api/productos/999999/").status_code == 404

    def test_codigo_barras_view(self):
        ProductoFactory(codigo_barras="CB-VIEW-1")
        c = _auth()
        assert c.get("/api/productos/codigo-barras/", {"codigo_barras": "CB-VIEW-1"}).status_code == 200
        assert c.get("/api/productos/codigo-barras/", {"codigo_barras": "NOPE"}).status_code == 404
        assert c.get("/api/productos/codigo-barras/").status_code == 400

    def test_tipo_controller_crud(self):
        c = _auth()
        assert c.get("/api/tipos/").status_code == 200
        tid = c.post("/api/tipos/", {"nombre": "T1"}, format="json").json()["id"]
        assert c.post("/api/tipos/", {"nombre": "T1"}, format="json").status_code == 201
        assert c.get(f"/api/tipos/{tid}/").status_code == 200
        assert c.get("/api/tipos/999999/").status_code == 404
        assert c.put(f"/api/tipos/{tid}/", {"nombre": "T2"}, format="json").status_code == 200
        assert c.put("/api/tipos/999999/", {"nombre": "x"}, format="json").status_code == 404
        assert c.post("/api/tipos/", {}, format="json").status_code == 400
        assert c.delete(f"/api/tipos/{tid}/").status_code == 200
        assert c.delete("/api/tipos/999999/").status_code == 404

    def test_proveedor_controller_crud(self):
        c = _auth()
        assert c.get("/api/proveedores/").status_code == 200
        payload = {"nombre": "P1", "direccion": "D1", "telefono": "5551", "correo": "p1@m.com"}
        pid = c.post("/api/proveedores/", payload, format="json").json()["id"]
        assert c.post("/api/proveedores/", payload, format="json").status_code == 201
        assert c.get(f"/api/proveedores/{pid}/").status_code == 200
        assert c.get("/api/proveedores/999999/").status_code == 404
        assert c.put(f"/api/proveedores/{pid}/", {"nombre": "P2"}, format="json").status_code == 200
        assert c.put("/api/proveedores/999999/", {"nombre": "x"}, format="json").status_code == 404
        assert c.post("/api/proveedores/", {}, format="json").status_code == 400
        assert c.delete(f"/api/proveedores/{pid}/").status_code == 200
        assert c.delete("/api/proveedores/999999/").status_code == 404


@pytest.mark.django_db
class TestSucursal:
    def test_service_crud(self):
        svc = SucursalService()
        created = svc.create({"ubicacion": "Ubi 1"})
        assert created["ubicacion"] == "Ubi 1"
        assert len(svc.get_all()) >= 1
        assert svc.get_by_id(created["id"])["ubicacion"] == "Ubi 1"
        assert svc.update(created["id"], {"ubicacion": "Ubi 2"})["ubicacion"] == "Ubi 2"
        assert svc.delete(created["id"])["message"]
        with pytest.raises(Exception):
            svc.get_by_id(created["id"])

    def test_to_dict_none(self):
        assert SucursalService()._to_dict(None) is None

    def test_model_str(self):
        assert str(SucursalFactory(ubicacion="UbiStr")) == "UbiStr"

    def test_controller_crud(self):
        c = _auth()
        assert c.get("/api/sucursales/").status_code == 200
        sid = c.post("/api/sucursales/", {"ubicacion": "S1"}, format="json").json()["id"]
        assert c.post("/api/sucursales/", {"ubicacion": "S1"}, format="json").status_code == 201
        assert c.get(f"/api/sucursales/{sid}/").status_code == 200
        assert c.get("/api/sucursales/999999/").status_code == 404
        assert c.put(f"/api/sucursales/{sid}/", {"ubicacion": "S2"}, format="json").status_code == 200
        assert c.put("/api/sucursales/999999/", {"ubicacion": "x"}, format="json").status_code == 404
        assert c.post("/api/sucursales/", {}, format="json").status_code == 400
        assert c.delete(f"/api/sucursales/{sid}/").status_code == 200
        assert c.delete("/api/sucursales/999999/").status_code == 404

    def test_repository_ops(self):
        repo = SucursalRepository()
        s = SucursalFactory()
        assert repo.get_by_id(s.id).id == s.id
        assert repo.get_by_id(999999) is None
        assert len(repo.get_all()) >= 1
        obj = repo.create({"ubicacion": "Rep"})
        repo.update(obj, {"ubicacion": "Rep2"})
        obj.refresh_from_db()
        assert obj.ubicacion == "Rep2"
        assert repo.delete(obj) is True
