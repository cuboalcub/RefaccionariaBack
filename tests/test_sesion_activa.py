from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from usuario.models import SesionActiva


def _login(client, username="tester", password="testpass123"):
    return client.post(
        "/api/login",
        {"username": username, "password": password},
        format="json",
    )


def _client_with_access(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
class TestSesionUnica:
    def test_segundo_login_invalida_tokens_anteriores(self):
        user = User.objects.create_user(username="tester", password="testpass123")
        primero = APIClient()
        r1 = _login(primero)
        assert r1.status_code == 200
        sid_anterior = SesionActiva.objects.get(usuario=user).session_jti

        segundo = APIClient()
        r2 = _login(segundo)
        assert r2.status_code == 200
        sid_nuevo = SesionActiva.objects.get(usuario=user).session_jti
        assert sid_nuevo != sid_anterior

        viejo = _client_with_access(r1.data["access"])
        assert viejo.get("/api/perfil/").status_code == 401
        assert (
            viejo.post(
                "/api/token/refresh",
                {"refresh": r1.data["refresh"]},
                format="json",
            ).status_code
            == 401
        )

        nuevo = _client_with_access(r2.data["access"])
        assert nuevo.get("/api/perfil/").status_code == 200

    def test_inactividad_expira_y_permite_nuevo_login(self):
        user = User.objects.create_user(username="tester", password="testpass123")
        client = APIClient()
        r = _login(client)
        assert r.status_code == 200

        SesionActiva.objects.filter(usuario=user).update(
            ultima_actividad=timezone.now() - timedelta(minutes=30, seconds=1)
        )

        assert _client_with_access(r.data["access"]).get("/api/perfil/").status_code == 401
        assert (
            client.post(
                "/api/token/refresh",
                {"refresh": r.data["refresh"]},
                format="json",
            ).status_code
            == 401
        )
        assert not SesionActiva.objects.filter(usuario=user).exists()
        assert _login(client).status_code == 200

    def test_actividad_se_actualiza_con_access_y_refresh(self):
        user = User.objects.create_user(username="tester", password="testpass123")
        client = APIClient()
        r = _login(client)
        assert r.status_code == 200
        vieja = timezone.now() - timedelta(minutes=2)
        SesionActiva.objects.filter(usuario=user).update(ultima_actividad=vieja)

        assert (
            _client_with_access(r.data["access"]).get("/api/perfil/").status_code
            == 200
        )
        assert SesionActiva.objects.get(usuario=user).ultima_actividad > vieja

        SesionActiva.objects.filter(usuario=user).update(ultima_actividad=vieja)
        assert (
            client.post(
                "/api/token/refresh",
                {"refresh": r.data["refresh"]},
                format="json",
            ).status_code
            == 200
        )
        assert SesionActiva.objects.get(usuario=user).ultima_actividad > vieja

    def test_tokens_sin_sid_son_rechazados(self):
        user = User.objects.create_user(username="tester", password="testpass123")
        refresh = RefreshToken.for_user(user)

        client = _client_with_access(refresh.access_token)
        assert client.get("/api/perfil/").status_code == 401
        assert (
            client.post(
                "/api/token/refresh",
                {"refresh": str(refresh)},
                format="json",
            ).status_code
            == 401
        )


@pytest.mark.django_db
class TestLogout:
    def test_logout_con_refresh_invalida_tokens(self):
        User.objects.create_user(username="tester", password="testpass123")
        login = APIClient()
        r = _login(login)
        assert r.status_code == 200

        client = _client_with_access(r.data["access"])
        assert (
            client.post(
                "/api/logout", {"refresh": r.data["refresh"]}, format="json"
            ).status_code
            == 204
        )
        assert client.get("/api/perfil/").status_code == 401
        assert (
            client.post(
                "/api/token/refresh",
                {"refresh": r.data["refresh"]},
                format="json",
            ).status_code
            == 401
        )
        assert client.post("/api/logout", {}, format="json").status_code == 204

    def test_logout_con_access(self):
        User.objects.create_user(username="tester", password="testpass123")
        r = _login(APIClient())
        assert r.status_code == 200

        client = _client_with_access(r.data["access"])
        assert client.post("/api/logout", {}, format="json").status_code == 204
        assert client.get("/api/perfil/").status_code == 401

    def test_logout_sin_tokens_o_invalidos_es_idempotente(self):
        client = APIClient()
        assert client.post("/api/logout", {}, format="json").status_code == 204
        assert (
            client.post(
                "/api/logout", {"refresh": "invalido"}, format="json"
            ).status_code
            == 204
        )
        client.credentials(HTTP_AUTHORIZATION="Bearer invalido")
        assert client.post("/api/logout", {}, format="json").status_code == 204
        client.credentials(HTTP_AUTHORIZATION="Basic invalido")
        assert client.post("/api/logout", {}, format="json").status_code == 204

    def test_staff_sin_perfil_puede_login_y_logout(self):
        User.objects.create_user(
            username="staff", password="testpass123", is_staff=True
        )
        r = _login(APIClient(), username="staff")
        assert r.status_code == 200

        client = _client_with_access(r.data["access"])
        assert client.get("/api/perfil/").status_code == 200
        assert client.post("/api/logout", {}, format="json").status_code == 204


@pytest.mark.django_db
def test_login_invalido_no_crea_sesion():
    User.objects.create_user(username="tester", password="testpass123")

    r = _login(APIClient(), password="incorrecta")

    assert r.status_code == 401
    assert not SesionActiva.objects.exists()
