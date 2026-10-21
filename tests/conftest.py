"""Fixtures globales pytest-django: user, JWT/API clients, sucursal/inventario base."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from sucursales.models import Sucursal
from inventario.models import Inventario
from usuario.models import Perfil


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
def inventario(db, sucursal):
    return Inventario.objects.create(
        id_sucursal=sucursal, descripcion="Inventario principal"
    )


@pytest.fixture
def perfil(db, user, sucursal, inventario):
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
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
