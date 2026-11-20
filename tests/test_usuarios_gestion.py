"""Encargado gestiona usuarios de su sucursal; registro público cerrado."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from tests.factories import SucursalFactory, UserFactory
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
class TestEncargadoCrea:
    def test_crea_cajero_propio_forzando(self):
        suc_a = SucursalFactory()
        suc_b = SucursalFactory()
        enc = _encargado(suc_a)
        c = _auth(enc)
        r = c.post(
            "/api/users",
            {
                "username": "cajero_nuevo",
                "password": "testpass123",
                "id_sucursal": suc_b.id,  # se ignora
                "rol": "admin",  # se ignora
            },
            format="json",
        )
        assert r.status_code == 201, r.content
        nuevo = User.objects.get(username="cajero_nuevo")
        perf = Perfil.objects.get(usuario=nuevo)
        assert perf.id_sucursal_id == suc_a.id
        assert perf.rol == "cajero"

    def test_staff_crea_con_sucursal_y_rol(self, api_client, staff_user):
        suc = SucursalFactory()
        api_client.force_authenticate(user=staff_user)
        r = api_client.post(
            "/api/users",
            {
                "username": "staff_nuevo",
                "password": "testpass123",
                "id_sucursal": suc.id,
                "rol": "encargado",
            },
            format="json",
        )
        assert r.status_code == 201, r.content
        perf = Perfil.objects.get(usuario__username="staff_nuevo")
        assert (perf.id_sucursal_id, perf.rol) == (suc.id, "encargado")

    def test_staff_sin_sucursal_hereda_la_suya(self, api_client):
        suc = SucursalFactory()
        staff = UserFactory(is_staff=True)
        Perfil.objects.create(usuario=staff, id_sucursal=suc, rol="admin")
        api_client.force_authenticate(user=staff)
        r = api_client.post(
            "/api/users",
            {"username": "hereda", "password": "testpass123"},
            format="json",
        )
        assert r.status_code == 201, r.content
        perf = Perfil.objects.get(usuario__username="hereda")
        assert (perf.id_sucursal_id, perf.rol) == (suc.id, "cajero")
        assert r.data["id_sucursal"] == suc.id
        assert r.data["rol"] == "cajero"

    def test_staff_sin_sucursal_propia_400(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        r = api_client.post(
            "/api/users",
            {"username": "huerfano2", "password": "testpass123"},
            format="json",
        )
        assert r.status_code == 400

    def test_staff_edita_sucursal_y_rol(self, api_client, staff_user):
        suc = SucursalFactory()
        nuevo = UserFactory(username="editado")
        api_client.force_authenticate(user=staff_user)
        r = api_client.put(
            f"/api/users/{nuevo.id}",
            {"id_sucursal": suc.id, "rol": "encargado"},
            format="json",
        )
        assert r.status_code == 200, r.content
        perf = Perfil.objects.get(usuario=nuevo)
        assert (perf.id_sucursal_id, perf.rol) == (suc.id, "encargado")
        assert r.data["id_sucursal"] == suc.id
        assert r.data["rol"] == "encargado"

    def test_staff_rol_invalido_400(self, api_client, staff_user):
        suc = SucursalFactory()
        api_client.force_authenticate(user=staff_user)
        assert (
            api_client.post(
                "/api/users",
                {
                    "username": "malrol",
                    "password": "testpass123",
                    "id_sucursal": suc.id,
                    "rol": "jefe",
                },
                format="json",
            ).status_code
            == 400
        )

    def test_cajero_no_crea_403(self, auth_client):
        assert (
            auth_client.post(
                "/api/users",
                {"username": "negado", "password": "testpass123"},
                format="json",
            ).status_code
            == 403
        )

    def test_encargado_sin_sucursal_400(self):
        enc = _encargado(None)
        r = _auth(enc).post(
            "/api/users",
            {"username": "huerfano", "password": "testpass123"},
            format="json",
        )
        assert r.status_code == 400


@pytest.mark.django_db
class TestLoginSucursal:
    def test_login_incluye_sucursal_y_rol(self):
        suc = SucursalFactory()
        u = User.objects.create_user(username="login_suc", password="testpass123")
        Perfil.objects.create(usuario=u, id_sucursal=suc, rol="cajero")

        r = APIClient().post(
            "/api/login",
            {"username": "login_suc", "password": "testpass123"},
            format="json",
        )

        assert r.status_code == 200
        assert r.data["user"]["id_sucursal"] == suc.id
        assert r.data["user"]["rol"] == "cajero"


@pytest.mark.django_db
class TestEncargadoModifica:
    def _propio(self):
        suc = SucursalFactory()
        enc = _encargado(suc)
        caj = UserFactory(username="cajero_mod")
        Perfil.objects.create(usuario=caj, id_sucursal=suc, rol="cajero")
        return suc, enc, caj

    def test_modifica_propio_200(self):
        _, enc, caj = self._propio()
        c = _auth(enc)
        r = c.put(
            f"/api/users/{caj.id}",
            {"email": "nuevo@mail.com", "password": "nueva12345", "is_active": False},
            format="json",
        )
        assert r.status_code == 200, r.content
        caj.refresh_from_db()
        assert caj.email == "nuevo@mail.com" and not caj.is_active
        assert caj.check_password("nueva12345")

    def test_no_suberol_ni_otra_sucursal(self):
        suc, enc, caj = self._propio()
        otra = SucursalFactory()
        ajeno = UserFactory(username="ajeno_mod")
        Perfil.objects.create(usuario=ajeno, id_sucursal=otra, rol="cajero")
        c = _auth(enc)
        assert c.put(f"/api/users/{ajeno.id}", {"email": "x@y.z"}, format="json").status_code == 403
        # intenta escalar rol: se ignora, el resto aplica
        r = c.put(
            f"/api/users/{caj.id}",
            {"email": "ok@mail.com", "rol": "admin", "is_staff": True},
            format="json",
        )
        assert r.status_code == 200
        assert Perfil.objects.get(usuario=caj).rol == "cajero"
        assert User.objects.get(id=caj.id).is_staff is False

    def test_sin_sucursal_objetivo_403(self):
        _, enc, _ = self._propio()
        suelto = UserFactory(username="suelto_mod")
        c = _auth(enc)
        assert c.put(f"/api/users/{suelto.id}", {"email": "x@y.z"}, format="json").status_code == 403

    def test_staff_modifica_cualquiera(self, api_client, staff_user):
        otra = SucursalFactory()
        ajeno = UserFactory(username="ajeno_staff")
        Perfil.objects.create(usuario=ajeno, id_sucursal=otra, rol="cajero")
        api_client.force_authenticate(user=staff_user)
        assert (
            api_client.put(
                f"/api/users/{ajeno.id}", {"email": "s@mail.com"}, format="json"
            ).status_code
            == 200
        )

    def test_encargado_no_borra_403(self):
        _, enc, caj = self._propio()
        assert _auth(enc).delete(f"/api/users/{caj.id}").status_code == 403
        assert User.objects.filter(id=caj.id).exists()


@pytest.mark.django_db
class TestEncargadoListaYDetalle:
    def test_lista_filtrada(self):
        suc = SucursalFactory()
        otra = SucursalFactory()
        enc = _encargado(suc)
        propio = UserFactory(username="propio_lst")
        Perfil.objects.create(usuario=propio, id_sucursal=suc, rol="cajero")
        ajeno = UserFactory(username="ajeno_lst")
        Perfil.objects.create(usuario=ajeno, id_sucursal=otra, rol="cajero")
        r = _auth(enc).get("/api/users")
        assert r.status_code == 200
        nombres = [u["username"] for u in r.data]
        assert "propio_lst" in nombres and "ajeno_lst" not in nombres

    def test_lista_sin_sucursal_vacia(self):
        enc = _encargado(None)
        assert _auth(enc).get("/api/users").status_code == 200
        assert _auth(enc).get("/api/users").data == []

    def test_cajero_lista_403(self, auth_client):
        assert auth_client.get("/api/users").status_code == 403

    def test_detalle_cross_403_y_inexistente_404(self):
        suc = SucursalFactory()
        enc = _encargado(suc)
        c = _auth(enc)
        otra = SucursalFactory()
        ajeno = UserFactory(username="ajeno_det")
        Perfil.objects.create(usuario=ajeno, id_sucursal=otra, rol="cajero")
        assert c.get(f"/api/users/{ajeno.id}").status_code == 403
        assert c.get("/api/users/999999").status_code == 404


@pytest.mark.django_db
class TestEndurecimientoLoginYAlta:
    def test_login_inactivo_401_y_refresh_401(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        u = User.objects.create_user(
            username="inactivo_login", password="testpass123", is_active=False
        )
        c = APIClient()
        r = c.post(
            "/api/login",
            {"username": "inactivo_login", "password": "testpass123"},
            format="json",
        )
        assert r.status_code == 401
        assert "access" not in r.data and "refresh" not in r.data
        r2 = c.post(
            "/api/token/refresh",
            {"refresh": str(RefreshToken.for_user(u))},
            format="json",
        )
        assert r2.status_code == 401

    def test_encargado_no_escala_privilegios_en_alta(self):
        suc = SucursalFactory()
        enc = _encargado(suc)
        r = _auth(enc).post(
            "/api/users",
            {
                "username": "casi_admin_api",
                "password": "testpass123",
                "is_staff": True,
                "is_superuser": True,
            },
            format="json",
        )
        assert r.status_code == 201, r.content
        u = User.objects.get(username="casi_admin_api")
        assert u.is_staff is False and u.is_superuser is False

    def test_alta_email_duplicado_400(self, api_client, staff_user):
        suc = SucursalFactory()
        UserFactory(email="dup@mail.com")
        api_client.force_authenticate(user=staff_user)
        r = api_client.post(
            "/api/users",
            {
                "username": "dup_uno",
                "password": "testpass123",
                "email": "dup@mail.com",
                "id_sucursal": suc.id,
            },
            format="json",
        )
        assert r.status_code == 400
        assert "correo" in r.data["error"]
        r2 = api_client.post(
            "/api/users",
            {
                "username": "dup_dos",
                "password": "testpass123",
                "email": "DUP@MAIL.COM",
                "id_sucursal": suc.id,
            },
            format="json",
        )
        assert r2.status_code == 400

    def test_edicion_email_duplicado_400(self, api_client, staff_user):
        UserFactory(email="ocupado@mail.com")
        objetivo = UserFactory(username="edit_email", email="libre@mail.com")
        api_client.force_authenticate(user=staff_user)
        r = api_client.put(
            f"/api/users/{objetivo.id}",
            {"email": "ocupado@mail.com"},
            format="json",
        )
        assert r.status_code == 400
        assert (
            api_client.put(
                f"/api/users/{objetivo.id}",
                {"email": "libre@mail.com"},
                format="json",
            ).status_code
            == 200
        )
