"""Fase 1 roles: scoping por sucursal en inventario/detalles/bulk/precios.

Convención: permiso antes que scoping. Cajero (default) puede leer;
escribir/anular/admin exigen encargado/admin. Sin sucursal -> 400
(solo si el permiso lo permite).
"""

from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from inventario.models import MovimientoInventario, Stock
from inventario.services.precio_sucursal_service import PrecioSucursalService
from repository.permissions import (
    entero_o_none,
    es_staff,
    exigir_misma_sucursal,
    sucursal_de_usuario,
)
from tests.factories import (
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil


def _auth(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _encargado(suc=None):
    u = UserFactory()
    Perfil.objects.create(usuario=u, id_sucursal=suc, rol="encargado")
    return u


@pytest.mark.django_db
class TestPermisosCentrales:
    def test_es_staff(self, staff_user, user):
        assert es_staff(staff_user) is True
        assert es_staff(user) is False
        assert es_staff(SimpleNamespace(is_staff=False, is_superuser=True)) is True
        assert es_staff(SimpleNamespace()) is False

    def test_sucursal_de_usuario(self, user, perfil, sucursal):
        assert sucursal_de_usuario(user) == sucursal.id
        assert sucursal_de_usuario(UserFactory()) is None

    def test_entero_o_none(self):
        assert entero_o_none("5") == 5
        assert entero_o_none(7) == 7
        assert entero_o_none("abc") is None
        assert entero_o_none(None) is None

    def test_exigir(self, staff_user, user, perfil, sucursal):
        exigir_misma_sucursal(staff_user, 999999, "x")  # bypass
        exigir_misma_sucursal(user, sucursal.id, "x")  # propia
        exigir_misma_sucursal(user, None, "x")  # sin recurso
        from rest_framework.exceptions import PermissionDenied

        with pytest.raises(PermissionDenied):
            exigir_misma_sucursal(user, 999999, "x")
        with pytest.raises(ValueError, match="sucursal"):
            exigir_misma_sucursal(UserFactory(), sucursal.id, "x")


@pytest.mark.django_db
class TestStockScoping:
    def _stock(self, suc, cantidad=5):
        prod = ProductoFactory()
        Stock.objects.create(id_producto=prod, id_sucursal=suc, cantidad=cantidad)
        return prod

    def test_list_solo_propia(self, auth_client, perfil):
        self._stock(perfil.id_sucursal)
        self._stock(SucursalFactory())
        r = auth_client.get("/api/stock/")
        assert r.status_code == 200
        assert {f["id_sucursal"] for f in r.data} == {perfil.id_sucursal_id}

    def test_list_staff_ve_todo_y_filtra(self, api_client, staff_user):
        a, b = SucursalFactory(), SucursalFactory()
        self._stock(a)
        self._stock(b)
        api_client.force_authenticate(user=staff_user)
        r = api_client.get("/api/stock/")
        assert r.status_code == 200
        assert {f["id_sucursal"] for f in r.data} == {a.id, b.id}
        r = api_client.get(f"/api/stock/?sucursal_id={a.id}")
        assert {f["id_sucursal"] for f in r.data} == {a.id}
        assert api_client.get("/api/stock/?sucursal_id=abc").status_code == 400

    def test_list_sin_sucursal_400(self, api_client, user):
        api_client.force_authenticate(user=user)
        assert api_client.get("/api/stock/").status_code == 400


@pytest.mark.django_db
class TestDetalleScoping:
    def _detalle_propio(self, auth_client, perfil):
        suc = perfil.id_sucursal
        prod = ProductoFactory()
        r = auth_client.post(
            "/api/detalles-inventario/",
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 3,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            },
            format="json",
        )
        assert r.status_code == 201, r.content
        return r.data["id"], suc

    def _encargado_con_perfil(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])

    def test_post_otra_sucursal_403(self, auth_client):
        suc = SucursalFactory()
        prod = ProductoFactory()
        r = auth_client.post(
            "/api/detalles-inventario/",
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 1,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            },
            format="json",
        )
        # cajero sin permiso de escritura -> 403 (antes del scoping)
        assert r.status_code == 403

    def test_post_basura_400(self, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        prod = ProductoFactory()
        r = auth_client.post(
            "/api/detalles-inventario/",
            {
                "id_producto": prod.id,
                "id_sucursal": "abc",
                "cantidad": 1,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_list_solo_propia_y_detail_cross(self, auth_client, perfil, staff_user):
        self._encargado_con_perfil(auth_client, perfil)
        did, _ = self._detalle_propio(auth_client, perfil)
        r = auth_client.get("/api/detalles-inventario/")
        assert r.status_code == 200
        assert did in [d["id"] for d in r.data]
        # detalle de otra sucursal vía servicio directo (bypass) para el 403
        from inventario.services.movimiento_inventario_service import (
            MovimientoInventarioService,
        )

        prod = ProductoFactory()
        otro = MovimientoInventarioService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": SucursalFactory().id,
                "cantidad": 1,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        assert auth_client.get(f"/api/detalles-inventario/{otro['id']}/").status_code == 403
        assert auth_client.delete(f"/api/detalles-inventario/{otro['id']}/").status_code == 403
        c_staff = APIClient()
        c_staff.force_authenticate(user=staff_user)
        assert c_staff.get(f"/api/detalles-inventario/{did}/").status_code == 200

    def test_put_ignora_cambio_sucursal(self, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        did, suc = self._detalle_propio(auth_client, perfil)
        otro = SucursalFactory()
        r = auth_client.put(
            f"/api/detalles-inventario/{did}/",
            {"cantidad": 5, "id_sucursal": otro.id},
            format="json",
        )
        assert r.status_code == 200
        assert MovimientoInventario.objects.get(id=did).id_sucursal_id == suc.id

    def test_staff_y_errores_varios(self, api_client, staff_user, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        suc = perfil.id_sucursal
        prod = ProductoFactory()
        c_staff = APIClient()
        c_staff.force_authenticate(user=staff_user)
        assert c_staff.get("/api/detalles-inventario/").status_code == 200
        # POST incompleto -> 400 del servicio
        assert (
            auth_client.post(
                "/api/detalles-inventario/",
                {"id_producto": prod.id, "id_sucursal": suc.id},
                format="json",
            ).status_code
            == 400
        )
        # bulk en forma de lista plana
        r = auth_client.post(
            "/api/detalles-inventario/bulk/",
            [
                {
                    "id_producto": prod.id,
                    "id_sucursal": suc.id,
                    "cantidad": 1,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Compra",
                }
            ],
            format="json",
        )
        assert r.status_code == 201, r.content
        # bulk staff
        assert (
            c_staff.post(
                "/api/detalles-inventario/bulk/",
                {
                    "id_sucursal": suc.id,
                    "tipo_movimiento": "ENTRADA",
                    "items": [{"id_producto": prod.id, "cantidad": 1}],
                },
                format="json",
            ).status_code
            == 201
        )

    def test_sin_sucursal_y_errores_put_delete(self, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        suc = perfil.id_sucursal
        prod = ProductoFactory()
        r = auth_client.post(
            "/api/detalles-inventario/",
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 1,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            },
            format="json",
        )
        did = r.data["id"]
        enc_sin = UserFactory()
        Perfil.objects.create(usuario=enc_sin, rol="encargado")
        c_sin = _auth(enc_sin)
        assert c_sin.get("/api/detalles-inventario/").status_code == 400
        assert c_sin.get(f"/api/detalles-inventario/{did}/").status_code == 400
        assert (
            c_sin.put(
                f"/api/detalles-inventario/{did}/", {"cantidad": 2}, format="json"
            ).status_code
            == 400
        )
        assert c_sin.delete(f"/api/detalles-inventario/{did}/").status_code == 400
        # PUT inválido y DELETE propio con usuario válido
        assert (
            auth_client.put(
                f"/api/detalles-inventario/{did}/", {"cantidad": -1}, format="json"
            ).status_code
            == 400
        )
        assert auth_client.put("/api/detalles-inventario/999999/", {"cantidad": 1},
                               format="json").status_code == 404
        assert auth_client.delete(f"/api/detalles-inventario/{did}/").status_code == 200
        assert auth_client.delete("/api/detalles-inventario/999999/").status_code == 404

    def test_bulk_formato_invalido_400(self, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        r = auth_client.post(
            "/api/detalles-inventario/bulk/", "texto-plano", format="json"
        )
        assert r.status_code == 400

    def test_bulk_cross_403_y_basura_400(self, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        suc = perfil.id_sucursal
        otra = SucursalFactory()
        p1, p2 = ProductoFactory(), ProductoFactory()
        r = auth_client.post(
            "/api/detalles-inventario/bulk/",
            {
                "id_sucursal": suc.id,
                "tipo_movimiento": "ENTRADA",
                "items": [{"id_producto": p1.id, "cantidad": 1}],
            },
            format="json",
        )
        assert r.status_code == 201, r.content
        r2 = auth_client.post(
            "/api/detalles-inventario/bulk/",
            {
                "id_sucursal": suc.id,
                "tipo_movimiento": "ENTRADA",
                "items": [{"id_producto": p2.id, "cantidad": 1, "id_sucursal": otra.id}],
            },
            format="json",
        )
        assert r2.status_code == 403
        r3 = auth_client.post(
            "/api/detalles-inventario/bulk/",
            {"id_sucursal": "abc", "items": [{"id_producto": p2.id, "cantidad": 1}]},
            format="json",
        )
        assert r3.status_code == 400


@pytest.mark.django_db
class TestPrecioScoping:
    def _encargado_con_perfil(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])

    def test_post_otra_sucursal_403_y_basura_400(self, auth_client, perfil):
        otra = SucursalFactory()
        prod = ProductoFactory()
        base = {"id_producto": prod.id, "precio_venta": "10.00"}
        assert (
            auth_client.post(
                "/api/precios-sucursal/", {**base, "id_sucursal": otra.id}, format="json"
            ).status_code
            == 403
        )
        # cajero: el permiso falla antes que el formato
        assert (
            auth_client.post(
                "/api/precios-sucursal/", {**base, "id_sucursal": "abc"}, format="json"
            ).status_code
            == 403
        )
        self._encargado_con_perfil(auth_client, perfil)
        assert (
            auth_client.post(
                "/api/precios-sucursal/", {**base, "id_sucursal": "abc"}, format="json"
            ).status_code
            == 400
        )

    def test_post_sin_sucursal_usa_propia(self, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        prod = ProductoFactory()
        r = auth_client.post(
            "/api/precios-sucursal/",
            {"id_producto": prod.id, "precio_venta": "12.00"},
            format="json",
        )
        assert r.status_code == 201, r.content
        assert r.data["id_sucursal"] == perfil.id_sucursal_id

    def test_list_detail_cross(self, auth_client, perfil, staff_user):
        prod = ProductoFactory()
        propio = PrecioSucursalService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": perfil.id_sucursal_id,
                "precio_venta": "20.00",
            }
        )
        otra = SucursalFactory()
        ajeno = PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": otra.id, "precio_venta": "30.00"}
        )
        r = auth_client.get("/api/precios-sucursal/")
        assert r.status_code == 200
        assert propio["id"] in [p["id"] for p in r.data]
        assert ajeno["id"] not in [p["id"] for p in r.data]
        assert auth_client.get(f"/api/precios-sucursal/{ajeno['id']}/").status_code == 403
        assert auth_client.delete(f"/api/precios-sucursal/{ajeno['id']}/").status_code == 403
        c_staff = APIClient()
        c_staff.force_authenticate(user=staff_user)
        assert c_staff.get(f"/api/precios-sucursal/{ajeno['id']}/").status_code == 200

    def test_put_ignora_cambio_sucursal(self, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        prod = ProductoFactory()
        propio = PrecioSucursalService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": perfil.id_sucursal_id,
                "precio_venta": "20.00",
            }
        )
        otra = SucursalFactory()
        r = auth_client.put(
            f"/api/precios-sucursal/{propio['id']}/",
            {"precio_venta": "25.00", "id_sucursal": otra.id},
            format="json",
        )
        assert r.status_code == 200
        from inventario.models import PrecioSucursal

        assert PrecioSucursal.objects.get(id=propio["id"]).id_sucursal_id == perfil.id_sucursal_id

    def test_staff_y_errores_varios(self, api_client, staff_user, auth_client, perfil):
        self._encargado_con_perfil(auth_client, perfil)
        prod = ProductoFactory()
        propio = PrecioSucursalService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": perfil.id_sucursal_id,
                "precio_venta": "20.00",
            }
        )
        c_staff = APIClient()
        c_staff.force_authenticate(user=staff_user)
        assert c_staff.get("/api/precios-sucursal/").status_code == 200
        assert c_staff.post("/api/precios-sucursal/", {}, format="json").status_code == 400
        assert (
            c_staff.put(
                f"/api/precios-sucursal/{propio['id']}/",
                {"precio_venta": "-5.00"},
                format="json",
            ).status_code
            == 400
        )
        enc_sin = UserFactory()
        Perfil.objects.create(usuario=enc_sin, rol="encargado")
        c_sin = _auth(enc_sin)
        assert c_sin.get("/api/precios-sucursal/").status_code == 400
        assert (
            c_sin.post(
                "/api/precios-sucursal/",
                {"id_producto": prod.id, "precio_venta": "10.00"},
                format="json",
            ).status_code
            == 400
        )
        assert c_sin.get(f"/api/precios-sucursal/{propio['id']}/").status_code == 400
        assert (
            c_sin.put(
                f"/api/precios-sucursal/{propio['id']}/",
                {"precio_venta": "21.00"},
                format="json",
            ).status_code
            == 400
        )
        assert c_sin.delete(f"/api/precios-sucursal/{propio['id']}/").status_code == 400
        assert auth_client.delete(f"/api/precios-sucursal/{propio['id']}/").status_code == 200
        assert auth_client.put("/api/precios-sucursal/999999/", {"precio_venta": "1.00"},
                               format="json").status_code == 404
        assert auth_client.delete("/api/precios-sucursal/999999/").status_code == 404

    def test_activo_fuerza_propia(self, auth_client, perfil):
        prod = ProductoFactory()
        PrecioSucursalService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": perfil.id_sucursal_id,
                "precio_venta": "60.00",
            }
        )
        otra = SucursalFactory()
        # parámetro de otra sucursal se ignora: responde con la propia
        r = auth_client.get(
            f"/api/precios-sucursal/activo/?id_producto={prod.id}&id_sucursal={otra.id}"
        )
        assert r.status_code == 200

    def test_activo_historial_staff(self, api_client, staff_user):
        prod = ProductoFactory()
        suc = SucursalFactory()
        PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "60.00"}
        )
        api_client.force_authenticate(user=staff_user)
        assert (
            api_client.get(
                f"/api/precios-sucursal/activo/?id_producto={prod.id}&id_sucursal={suc.id}"
            ).status_code
            == 200
        )
        assert api_client.get("/api/precios-sucursal/activo/").status_code == 400
        assert (
            api_client.get(
                "/api/precios-sucursal/activo/?id_producto=abc&id_sucursal=xyz"
            ).status_code
            == 400
        )
        assert (
            api_client.get(
                f"/api/precios-sucursal/historial/?id_producto={prod.id}&id_sucursal={suc.id}"
            ).status_code
            == 200
        )
        assert api_client.get("/api/precios-sucursal/historial/").status_code == 400
        assert (
            api_client.get(
                "/api/precios-sucursal/historial/?id_producto=abc&id_sucursal=xyz"
            ).status_code
            == 400
        )

    def test_activo_sin_sucursal_400(self, api_client, user):
        prod = ProductoFactory()
        api_client.force_authenticate(user=user)
        assert (
            api_client.get(
                f"/api/precios-sucursal/activo/?id_producto={prod.id}&id_sucursal=1"
            ).status_code
            == 400
        )
        assert (
            api_client.get(
                f"/api/precios-sucursal/historial/?id_producto={prod.id}&id_sucursal=1"
            ).status_code
            == 400
        )


@pytest.mark.django_db
class TestRolesFase2:
    def test_rol_default_cajero_y_matriz(self):
        from repository.permissions import puede

        u = UserFactory()
        assert Perfil.objects.create(usuario=u).rol == "cajero"
        assert puede(u, "precios.leer") is True
        assert puede(u, "precios.escribir") is False
        assert puede(u, "accion.inexistente") is False
        assert puede(SimpleNamespace(), "precios.leer") is True
        assert puede(SimpleNamespace(), "precios.escribir") is False

    def test_rol_desconocido_niega(self):
        from repository.permissions import puede

        u = UserFactory()
        Perfil.objects.create(usuario=u, rol="superjefe")
        assert puede(u, "precios.leer") is False

    def test_admin_no_staff_global_en_accion_pero_acotado_en_sucursal(self, auth_client, perfil):
        perfil.rol = "admin"
        perfil.save(update_fields=["rol"])
        prod = ProductoFactory()
        # puede escribir precios en la propia...
        r = auth_client.post(
            "/api/precios-sucursal/",
            {"id_producto": prod.id, "id_sucursal": perfil.id_sucursal_id, "precio_venta": "9.00"},
            format="json",
        )
        assert r.status_code == 201
        # ...pero sigue acotado por sucursal
        otra = SucursalFactory()
        assert (
            auth_client.post(
                "/api/precios-sucursal/",
                {"id_producto": prod.id, "id_sucursal": otra.id, "precio_venta": "9.00"},
                format="json",
            ).status_code
            == 403
        )

    def test_cajero_no_anula_ni_reporta(self, auth_client):
        assert auth_client.delete("/api/ventas/999999/").status_code == 403
        assert auth_client.get("/api/reporte/", {"tipo": "day"}).status_code == 403

    def test_login_expone_rol_y_registro_lo_ignora(self, api_client):
        from usuario.services.usuario_service import UserService

        enc = _encargado(SucursalFactory())
        c = _auth(enc)
        r = c.post(
            "/api/users",
            {"username": "nuevorol", "password": "testpass123", "rol": "admin"},
            format="json",
        )
        assert r.status_code == 201
        out = UserService().login("nuevorol", "testpass123")
        assert out["user"]["rol"] == "cajero"
        # registro anónimo cerrado
        assert (
            api_client.post(
                "/api/users",
                {"username": "anonimo", "password": "testpass123"},
                format="json",
            ).status_code
            == 401
        )

    def test_perfil_put_ignora_rol(self, auth_client, user, perfil):
        r = auth_client.put("/api/perfil/", {"rol": "admin"}, format="json")
        assert r.status_code == 200
        assert r.data["rol"] == "cajero"
        assert r.data["rol"] != "admin"
