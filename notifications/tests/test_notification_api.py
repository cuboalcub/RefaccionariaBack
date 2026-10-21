"""API de notificaciones: contrato Angular, permisos y aislamiento."""

import pytest
from django.contrib.auth.models import User

from notifications.models import Notification
from tests.factories import SucursalFactory, UserFactory
from usuario.models import Perfil


def _notif(user, **kwargs):
    base = {
        "destinatario": user,
        "tipo": Notification.Tipo.INFO,
        "titulo": "Título",
        "mensaje": "Mensaje",
    }
    base.update(kwargs)
    return Notification.objects.create(**base)


def _ctx():
    suc_a = SucursalFactory()
    suc_b = SucursalFactory()
    user_a = UserFactory()
    user_b = UserFactory()
    Perfil.objects.create(usuario=user_a, id_sucursal=suc_a)
    Perfil.objects.create(usuario=user_b, id_sucursal=suc_b)
    return user_a, user_b


@pytest.mark.django_db
class TestList:
    def test_requiere_autenticacion(self, api_client):
        assert api_client.get("/api/notifications/").status_code == 401

    def test_solo_propias(self, api_client):
        user_a, user_b = _ctx()
        _notif(user_a, titulo="A1")
        _notif(user_a, titulo="A2")
        _notif(user_b, titulo="B1")
        api_client.force_authenticate(user=user_a)
        resp = api_client.get("/api/notifications/")
        assert resp.status_code == 200
        assert {n["titulo"] for n in resp.data} == {"A1", "A2"}

    def test_contrato_campos(self, api_client):
        user_a, _ = _ctx()
        _notif(user_a)
        api_client.force_authenticate(user=user_a)
        (item,) = api_client.get("/api/notifications/").data
        assert set(item) == {"id", "titulo", "mensaje", "tipo", "leida", "creado_en"}
        assert item["leida"] is False
        assert item["tipo"] == "info"


@pytest.mark.django_db
class TestMarkRead:
    def test_patch_marca_leida(self, api_client):
        user_a, _ = _ctx()
        n = _notif(user_a)
        api_client.force_authenticate(user=user_a)
        resp = api_client.patch(f"/api/notifications/{n.id}/", {}, format="json")
        assert resp.status_code == 200
        assert resp.data["leida"] is True
        n.refresh_from_db()
        assert n.leida is True

    def test_patch_ya_leida_sigue_200(self, api_client):
        user_a, _ = _ctx()
        n = _notif(user_a, leida=True)
        api_client.force_authenticate(user=user_a)
        resp = api_client.patch(f"/api/notifications/{n.id}/", {}, format="json")
        assert resp.status_code == 200
        assert resp.data["leida"] is True

    def test_patch_ajena_404_y_no_la_marca(self, api_client):
        user_a, user_b = _ctx()
        n = _notif(user_b)
        api_client.force_authenticate(user=user_a)
        resp = api_client.patch(f"/api/notifications/{n.id}/", {}, format="json")
        assert resp.status_code == 404
        n.refresh_from_db()
        assert n.leida is False

    def test_patch_inexistente_404(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.patch("/api/notifications/999999/", {}, format="json")
        assert resp.status_code == 404

    def test_patch_sin_auth_401(self, api_client):
        user_a, _ = _ctx()
        n = _notif(user_a)
        assert (
            api_client.patch(f"/api/notifications/{n.id}/", {}, format="json").status_code
            == 401
        )


@pytest.mark.django_db
class TestMarkAll:
    def test_marca_todas_las_propias(self, api_client):
        user_a, user_b = _ctx()
        _notif(user_a)
        _notif(user_a)
        otra = _notif(user_b)
        api_client.force_authenticate(user=user_a)
        resp = api_client.post("/api/notifications/mark-all/", {}, format="json")
        assert resp.status_code == 200
        assert resp.data == {"actualizadas": 2}
        otra.refresh_from_db()
        assert otra.leida is False

    def test_sin_pendientes_devuelve_cero(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.post("/api/notifications/mark-all/", {}, format="json")
        assert resp.status_code == 200
        assert resp.data == {"actualizadas": 0}


@pytest.mark.django_db
class TestDelete:
    def test_delete_propia(self, api_client):
        user_a, _ = _ctx()
        n = _notif(user_a)
        api_client.force_authenticate(user=user_a)
        resp = api_client.delete(f"/api/notifications/{n.id}/")
        assert resp.status_code == 200
        assert Notification.objects.filter(id=n.id).count() == 0

    def test_delete_ajena_404_y_no_borra(self, api_client):
        user_a, user_b = _ctx()
        n = _notif(user_b)
        api_client.force_authenticate(user=user_a)
        resp = api_client.delete(f"/api/notifications/{n.id}/")
        assert resp.status_code == 404
        assert Notification.objects.filter(id=n.id).count() == 1

    def test_delete_inexistente_404(self, api_client, user):
        api_client.force_authenticate(user=user)
        assert api_client.delete("/api/notifications/999999/").status_code == 404

    def test_staff_no_ve_ajenas(self, api_client, staff_user):
        user_a, _ = _ctx()
        _notif(user_a)
        api_client.force_authenticate(user=staff_user)
        assert api_client.get("/api/notifications/").data == []


@pytest.mark.django_db
class TestModelo:
    def test_str(self):
        user = User(username="x")
        n = Notification(
            destinatario=user, tipo="warning", titulo="T", mensaje="M"
        )
        assert "warning" in str(n)
