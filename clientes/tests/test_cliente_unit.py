"""Pruebas unitarias del módulo Clientes: permisos por rol, validaciones
de campos obligatorios, defaults del modelo, relación con Sucursal y 404.

Complementa clientes/tests/test_cliente_api.py (CRUD TestCase) y
tests/test_base_clientes_usuario.py::TestClienteService/TestClienteAPI
(sin duplicarlos).
"""

import pytest
from rest_framework.test import APIClient

from clientes.models import Cliente
from clientes.services.cliente_service import ClienteService
from tests.factories import SucursalFactory, UserFactory
from usuario.models import Perfil


def _auth(rol="cajero"):
    user = UserFactory()
    Perfil.objects.create(usuario=user, rol=rol)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _payload(sucursal, **extra):
    data = {
        "nombre": "Juan",
        "apellido_paterno": "Perez",
        "telefono": "5551234567",
        "id_sucursal": sucursal.id,
    }
    data.update(extra)
    return data


def _cliente(sucursal, **kw):
    base = {"nombre": "Ana", "apellido_paterno": "Lopez", "telefono": "5559876543"}
    base.update(kw)
    return Cliente.objects.create(id_sucursal=sucursal, **base)


# ---------------------------------------------------------------------------
# Permisos: matriz catalogos.* del controller
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPermisosCajero:
    def test_cajero_puede_leer_y_crear(self, db):
        suc = SucursalFactory()
        c = _auth("cajero")
        assert c.get("/api/clientes/").status_code == 200
        r = c.post("/api/clientes/", _payload(suc), format="json")
        assert r.status_code == 201

    def test_cajero_no_puede_editar_ni_borrar(self, db):
        suc = SucursalFactory()
        cid = _cliente(suc).id
        c = _auth("cajero")
        assert c.put(f"/api/clientes/{cid}/", {"nombre": "X"}, format="json").status_code == 403
        assert c.delete(f"/api/clientes/{cid}/").status_code == 403


# ---------------------------------------------------------------------------
# Validaciones: campos obligatorios del modelo vía BaseService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCamposObligatorios:
    def test_post_sin_nombre_400(self, db):
        suc = SucursalFactory()
        c = _auth("encargado")
        r = c.post(
            "/api/clientes/",
            {"apellido_paterno": "B", "telefono": "1", "id_sucursal": suc.id},
            format="json",
        )
        assert r.status_code == 400
        assert "nombre" in r.data["error"]

    def test_post_sin_apellido_paterno_400(self, db):
        suc = SucursalFactory()
        c = _auth("encargado")
        r = c.post(
            "/api/clientes/",
            {"nombre": "A", "telefono": "1", "id_sucursal": suc.id},
            format="json",
        )
        assert r.status_code == 400
        assert "apellido_paterno" in r.data["error"]

    def test_post_sin_telefono_400(self, db):
        suc = SucursalFactory()
        c = _auth("encargado")
        r = c.post(
            "/api/clientes/",
            {"nombre": "A", "apellido_paterno": "B", "id_sucursal": suc.id},
            format="json",
        )
        assert r.status_code == 400
        assert "telefono" in r.data["error"]


# ---------------------------------------------------------------------------
# Modelo: defaults y timestamps
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDefaultsModelo:
    def test_create_minimo_defaults_y_timestamps(self, db):
        suc = SucursalFactory()
        out = ClienteService().create(
            {
                "nombre": "Luz",
                "apellido_paterno": "Rios",
                "telefono": "555",
                "id_sucursal": suc.id,
            }
        )
        assert out["apellido_materno"] == ""
        assert out["direccion"] == ""
        assert out["rfc"] == ""
        assert out["correo"] is None
        assert out["created_at"] is not None
        assert out["updated_at"] is not None

    def test_to_dict_shape_completo(self, db):
        suc = SucursalFactory()
        c = _cliente(suc, correo="a@b.com", rfc="RFC123")
        d = ClienteService()._to_dict(c)
        assert set(d.keys()) == {
            "id",
            "id_sucursal",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "telefono",
            "correo",
            "direccion",
            "rfc",
            "created_at",
            "updated_at",
        }
        assert d["rfc"] == "RFC123"


# ---------------------------------------------------------------------------
# Relación con Sucursal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRelacionSucursal:
    def test_eliminar_sucursal_desvincula_cliente(self, db):
        suc = SucursalFactory()
        c = _cliente(suc)
        suc.delete()
        c.refresh_from_db()
        assert Cliente.objects.filter(id=c.id).exists()
        assert c.id_sucursal is None

    def test_update_id_sucursal_none_desvincula(self, db):
        # FK null=True: el servicio omite la validación y desvincula (documenta
        # el comportamiento actual, distinto a Inventario cuyo FK es NOT NULL)
        suc = SucursalFactory()
        c = _cliente(suc)
        out = ClienteService().update(c.id, {"id_sucursal": None})
        assert out["id_sucursal"] is None


# ---------------------------------------------------------------------------
# Detail controller: 404 en escrituras sobre id inexistente
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetalle404:
    def test_put_delete_inexistente_404(self, db):
        c = _auth("admin")
        assert c.put("/api/clientes/99999/", {"nombre": "X"}, format="json").status_code == 404
        assert c.delete("/api/clientes/99999/").status_code == 404
