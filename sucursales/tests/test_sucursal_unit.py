"""Pruebas unitarias del módulo Sucursales: modelo, service y permisos de controller.

Complementa sucursales/tests/test_legacy.py (create básico) y
tests/test_producto_sucursal.py::TestSucursal (CRUD admin) sin duplicarlos.
"""

import re

import pytest
from rest_framework.test import APIClient

from sucursales.models import Sucursal
from sucursales.services.sucursal_service import SucursalService
from tests.factories import UserFactory


def _auth(rol="cajero"):
    from usuario.models import Perfil

    user = UserFactory()
    Perfil.objects.create(usuario=user, rol=rol)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# Modelo: codigo_sucursal y defaults
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestModelCodigoSucursal:
    def test_codigo_sucursal_default_formato(self):
        s = Sucursal.objects.create(ubicacion="Centro")
        assert re.fullmatch(r"SUC-[0-9A-F]{6}", s.codigo_sucursal)

    def test_codigo_sucursal_unico_por_instancia(self):
        a = Sucursal.objects.create(ubicacion="A")
        b = Sucursal.objects.create(ubicacion="B")
        assert a.codigo_sucursal != b.codigo_sucursal

    def test_defaults_campos_opcionales(self):
        s = Sucursal.objects.create(ubicacion="Solo ubi")
        assert s.nombre_sucursal == ""
        assert s.codigo_postal == ""
        assert s.numero_telefono == ""
        assert s.correo_electronico == ""


# ---------------------------------------------------------------------------
# Service: _to_dict expone todos los campos de la sucursal
# ---------------------------------------------------------------------------

CAMPOS_SUCURSAL = {
    "id",
    "nombre_sucursal",
    "codigo_sucursal",
    "ubicacion",
    "codigo_postal",
    "numero_telefono",
    "correo_electronico",
}


@pytest.mark.django_db
class TestServiceDict:
    def test_create_devuelve_todos_los_campos(self):
        res = SucursalService().create(
            {"nombre_sucursal": "Norte", "ubicacion": "Norte 10"}
        )
        assert set(res.keys()) == CAMPOS_SUCURSAL
        assert res["ubicacion"] == "Norte 10"

    def test_get_by_id_expone_todos_los_campos(self):
        svc = SucursalService()
        created = svc.create({"nombre_sucursal": "Sur", "ubicacion": "Sur"})
        res = svc.get_by_id(created["id"])
        assert set(res.keys()) == CAMPOS_SUCURSAL
        assert res["codigo_sucursal"] == created["codigo_sucursal"]
        assert res["nombre_sucursal"] == "Sur"


# ---------------------------------------------------------------------------
# Service: validaciones de nombre y correo
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestValidacionesSucursal:
    def test_nombre_obligatorio(self):
        for data in ({"ubicacion": "X"}, {"nombre_sucursal": "  ", "ubicacion": "X"}):
            with pytest.raises(ValueError, match="nombre_sucursal"):
                SucursalService().create(data)

    def test_nombre_unico_iexact(self):
        svc = SucursalService()
        a = svc.create({"nombre_sucursal": "Centro", "ubicacion": "A"})
        with pytest.raises(ValueError, match="Ya existe"):
            svc.create({"nombre_sucursal": "centro", "ubicacion": "B"})

        b = svc.create({"nombre_sucursal": "Norte", "ubicacion": "B"})
        with pytest.raises(ValueError, match="Ya existe"):
            svc.update(b["id"], {"nombre_sucursal": "CENTRO"})
        assert svc.update(a["id"], {"nombre_sucursal": "CENTRO"})[
            "nombre_sucursal"
        ] == "CENTRO"
        assert b["nombre_sucursal"] == "Norte"

    def test_correo_invalido_y_valido(self):
        svc = SucursalService()
        with pytest.raises(ValueError, match="correo_electronico"):
            svc.create(
                {
                    "nombre_sucursal": "Mal correo",
                    "ubicacion": "A",
                    "correo_electronico": "no-es-correo",
                }
            )

        res = svc.create(
            {
                "nombre_sucursal": "Buen correo",
                "ubicacion": "B",
                "correo_electronico": " ok@mail.com ",
            }
        )
        assert res["correo_electronico"] == "ok@mail.com"

        with pytest.raises(ValueError, match="correo_electronico"):
            svc.update(res["id"], {"correo_electronico": "mal"})
        assert svc.update(res["id"], {"correo_electronico": ""})[
            "correo_electronico"
        ] == ""

    def test_controller_validaciones_400(self):
        c = _auth("admin")
        assert (
            c.post("/api/sucursales/", {"ubicacion": "X"}, format="json").status_code
            == 400
        )
        SucursalService().create(
            {"nombre_sucursal": "Existente", "ubicacion": "A"}
        )
        assert (
            c.post(
                "/api/sucursales/",
                {"nombre_sucursal": "existente", "ubicacion": "B"},
                format="json",
            ).status_code
            == 400
        )
        assert (
            c.post(
                "/api/sucursales/",
                {
                    "nombre_sucursal": "Nueva",
                    "ubicacion": "B",
                    "correo_electronico": "no",
                },
                format="json",
            ).status_code
            == 400
        )


# ---------------------------------------------------------------------------
# Controller: matriz de permisos y edge cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPermisosController:
    def test_cajero_leer_ok_admin_403(self):
        c = _auth("cajero")
        SucursalService().create(
            {"nombre_sucursal": "Oriente", "ubicacion": "Oriente 1"}
        )
        r = c.get("/api/sucursales/")
        assert r.status_code == 200
        assert set(r.json()[0].keys()) == CAMPOS_SUCURSAL
        assert r.json()[0]["nombre_sucursal"] == "Oriente"
        assert c.post("/api/sucursales/", {"ubicacion": "X"}, format="json").status_code == 403

    def test_encargado_sin_sucursales_admin(self):
        c = _auth("encargado")
        sid = SucursalService().create(
            {"nombre_sucursal": "U", "ubicacion": "U"}
        )["id"]
        assert c.get("/api/sucursales/").status_code == 200
        assert c.post("/api/sucursales/", {"ubicacion": "X"}, format="json").status_code == 403
        assert c.put(f"/api/sucursales/{sid}/", {"ubicacion": "Y"}, format="json").status_code == 403
        assert c.delete(f"/api/sucursales/{sid}/").status_code == 403

    def test_staff_bypass_escritura(self):
        user = UserFactory(is_staff=True)
        client = APIClient()
        client.force_authenticate(user=user)
        r = client.post(
            "/api/sucursales/",
            {"nombre_sucursal": "Staff S", "ubicacion": "Staff S"},
            format="json",
        )
        assert r.status_code == 201
        sid = r.json()["id"]
        assert client.put(f"/api/sucursales/{sid}/", {"ubicacion": "Mod"}, format="json").status_code == 200
        assert client.delete(f"/api/sucursales/{sid}/").status_code == 200

    def test_sin_autenticacion_401(self):
        c = APIClient()
        assert c.get("/api/sucursales/").status_code == 401
        assert c.post("/api/sucursales/", {"ubicacion": "X"}, format="json").status_code == 401


@pytest.mark.django_db
class TestControllerEdge:
    def test_post_campo_desconocido_400(self):
        c = _auth("admin")
        r = c.post(
            "/api/sucursales/",
            {"ubicacion": "Con Basura", "campo_inexistente": 1},
            format="json",
        )
        assert r.status_code == 400

    def test_put_vacio_no_op(self):
        c = _auth("admin")
        sid = SucursalService().create(
            {"nombre_sucursal": "Original", "ubicacion": "Original"}
        )["id"]
        r = c.put(f"/api/sucursales/{sid}/", {}, format="json")
        assert r.status_code == 200
        assert SucursalService().get_by_id(sid)["ubicacion"] == "Original"

    def test_respuesta_detalle_expone_todos_los_campos(self):
        c = _auth("cajero")
        sid = SucursalService().create(
            {"nombre_sucursal": "Visible", "ubicacion": "Visible"}
        )["id"]
        data = c.get(f"/api/sucursales/{sid}/").json()
        assert set(data.keys()) == CAMPOS_SUCURSAL
