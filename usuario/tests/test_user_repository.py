import pytest
from django.contrib.auth.models import User
from usuario.repositories.usuario_repositorie import UserRepository


@pytest.fixture
def sample_user():
    """Fixture que crea un usuario de prueba"""
    return User.objects.create_user(
        username="miguel",
        email="miguel@gmail.com",
        password="eldenring"
    )


@pytest.mark.django_db
class TestUserRepository:

    def test_get_all_returns_all_users(self):
        """Debe devolver todos los usuarios creados en la base de datos"""
        User.objects.create_user(username="test1", email="test1@test.com", password="test")
        users = UserRepository.get_all()
        assert users.count() == 1

    def test_create_user_successfully(self):
        """Debe crear un nuevo usuario"""
        data = {
            "username": "felipe",
            "email": "felipe@outlook.com",
            "password": "megutaeltoto"
        }
        user = UserRepository.create(data)

        assert user.id is not None
        assert user.username == "felipe"
        assert user.check_password("megutaeltoto")

    def test_update_existing_user(self, sample_user):
        """Debe actualizar los datos de un usuario existente"""
        updated_data = {"email": "nuevo@nose.com"}
        updated_user = UserRepository.update(sample_user.id, updated_data)

        assert updated_user is not None
        assert updated_user.email == "nuevo@nose.com"

    def test_update_nonexistent_user_returns_none(self):
        """Si el usuario no existe devuelve none"""
        result = UserRepository.update(9999, {"email": "x@example.com"})
        assert result is None

    def test_delete_existing_user(self, sample_user):
        """Debe eliminar un usuario existente"""
        result = UserRepository.delete(sample_user.id)
        assert result is True
        assert User.objects.filter(id=sample_user.id).exists() is False

    def test_delete_nonexistent_user_returns_false(self):
        """Si el usuario no existe devuelve false"""
        result = UserRepository.delete(9999)
        assert result is False

    def test_get_by_username_existing_user(self, sample_user):
        """Debe devolver el usuario correcto cuando existe el username"""
        user = UserRepository.get_by_username("miguel")
        assert user is not None
        assert user.username == "miguel"

    def test_get_by_username_nonexistent_user_returns_none(self):
        """Si el usuario no existe devuelve none"""
        user = UserRepository.get_by_username("no_existe")
        assert user is None