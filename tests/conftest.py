"""Fixtures globales pytest-django: user, JWT/API clients, sucursal base."""

from uuid import uuid4

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from sucursales.models import Sucursal
from usuario.models import Perfil, SesionActiva


@pytest.fixture
def user(db):
    return User.objects.create_user(username="tester", password="testpass123")


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staff", password="testpass123", is_staff=True
    )


@pytest.fixture
def sucursal(db):
    return Sucursal.objects.create(ubicacion="Sucursal Test")


@pytest.fixture
def sucursal_b(db):
    return Sucursal.objects.create(ubicacion="Sucursal B")


@pytest.fixture
def perfil(db, user, sucursal):
    """Perfil vincula user -> sucursal (base para resolución JWT)."""
    return Perfil.objects.create(usuario=user, id_sucursal=sucursal)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, user, perfil):
    """APIClient autenticado vía force_authenticate (rápido, sin JWT real)."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def jwt_client(api_client, user, perfil):
    """APIClient autenticado vía JWT real (cubre SimpleJWT)."""
    sid = uuid4().hex
    refresh = RefreshToken.for_user(user)
    refresh["sid"] = sid
    SesionActiva.objects.create(
        usuario=user, session_jti=sid, ultima_actividad=timezone.now()
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
