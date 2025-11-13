#from django.test import TestCase
#from django.contrib.auth.models import User
#from usuario.repositories.usuario_repositorie import UserRepository
#
#
#class UserRepositoryTestCase(TestCase):
#
#    def setUp(self):
#
#        #Crear usuario de prueba
#        self.user = User.objects.create_user(
#            username="miguel",
#            email="miguel@gmail.com",
#            password="eldenring"
#        )
#
#    def test_get_all_returns_all_users(self):
#
#        """
#        Debe devolver todos los usuarios creados en la base de datos
#        """
#
#        users = UserRepository.get_all()
#        self.assertEqual(users.count(), 1)
#        self.assertEqual(users.first().username, "miguel")
#
#
#    def test_create_user_successfully(self):
#
#        """
#        Debe crear un nuevo usuario
#        """
#
#        data = {
#            "username": "felipe",
#            "email": "felipe@outlook.com",
#            "password": "megutaeltoto"
#        }
#        user = UserRepository.create(data)
#
#        self.assertIsNotNone(user.id)
#        self.assertEqual(user.username, "felipe")
#        self.assertTrue(user.check_password("megutaeltoto"))
#
#    def test_update_existing_user(self):
#
#        """
#        Debe actualizar los datos de un usuario existente
#        """
#
#        updated_data = {"email": "nuevo@nose.com"}
#        updated_user = UserRepository.update(self.user.id, updated_data)
#
#        self.assertIsNotNone(updated_user)
#        self.assertEqual(updated_user.email, "nuevo@nose.com")
#
#    def test_update_nonexistent_user_returns_none(self):
#
#        """
#        Si el usuario no existe devuelve none
#        """
#
#        result = UserRepository.update(9999, {"email": "x@example.com"})
#        self.assertIsNone(result)
#
#    def test_delete_existing_user(self):
#
#        """
#        Debe eliminar un usuario existente
#        """
#
#        result = UserRepository.delete(self.user.id)
#        self.assertTrue(result)
#        self.assertFalse(User.objects.filter(id=self.user.id).exists())
#
#    def test_delete_nonexistent_user_returns_false(self):
#        """
#        Si el usuario no existe devuelve false
#        """
#        result = UserRepository.delete(9999)
#        self.assertFalse(result)
#
#    def test_get_by_username_existing_user(self):
#
#        """
#        Debe devolver el usuario correcto cuando existe el username
#        """
#        user = UserRepository.get_by_username("miguel")
#        self.assertIsNotNone(user)
#        self.assertEqual(user.username, "miguel")
#
#    def test_get_by_username_nonexistent_user_returns_none(self):
#        """
#        Si el usuario no existe devuelve none
#        """
#        user = UserRepository.get_by_username("no_existe")
#        self.assertIsNone(user)
#