from django.test import TestCase
from django.contrib.auth.models import User
from usuario.repositories.usuario_repositorie import UserRepository


class UserRepositoryTestCase(TestCase):

    def setUp(self):
        self.repo = UserRepository()
        self.user = User.objects.create_user(
            username="miguel",
            email="miguel@gmail.com",
            password="eldenring"
        )

    def test_get_all_returns_all_users(self):
        users = self.repo.get_all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, "miguel")

    def test_create_user_successfully(self):
        data = {
            "username": "felipe",
            "email": "felipe@outlook.com",
            "password": "megutaeltoto"
        }
        user = self.repo.create(data)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "felipe")
        self.assertTrue(user.check_password("megutaeltoto"))

    def test_update_existing_user(self):
        updated_data = {"email": "nuevo@nose.com"}
        updated_user = self.repo.update(self.user, updated_data)

        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.email, "nuevo@nose.com")

    def test_update_nonexistent_user_returns_none(self):
        result = self.repo.get_by_id(9999)
        self.assertIsNone(result)

    def test_delete_existing_user(self):
        result = self.repo.delete(self.user)
        self.assertTrue(result)
        self.assertFalse(User.objects.filter(id=self.user.id).exists())

    def test_delete_nonexistent_user_returns_false(self):
        fake_user = User(id=9999)
        result = self.repo.delete(fake_user)
        self.assertFalse(result)

    def test_get_by_username_existing_user(self):
        user = self.repo.get_by_username("miguel")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "miguel")

    def test_get_by_username_nonexistent_user_returns_none(self):
        user = self.repo.get_by_username("no_existe")
        self.assertIsNone(user)
