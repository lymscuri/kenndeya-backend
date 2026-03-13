"""
Tests pour l'application accounts.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse

User = get_user_model()


class UserModelTest(TestCase):
    """Tests pour le modèle User."""

    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+224621234567',
            'role': 'doctor',
        }

    def test_create_user(self):
        """Test de création d'un utilisateur."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, self.user_data['email'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertEqual(user.role, 'doctor')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Test de création d'un superutilisateur."""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_user_email_unique(self):
        """Test que l'email est unique."""
        User.objects.create_user(**self.user_data)
        with self.assertRaises(Exception):
            User.objects.create_user(**self.user_data)

    def test_user_get_full_name(self):
        """Test de la méthode get_full_name."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_full_name(), 'Test User')

    def test_user_str(self):
        """Test de la représentation string du user."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'test@example.com')


class AuthenticationAPITest(APITestCase):
    """Tests pour les endpoints d'authentification."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.user_data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'first_name': 'New',
            'last_name': 'User',
            'phone': '+224621234567',
            'role': 'patient',
        }

    def test_user_registration(self):
        """Test d'inscription d'un nouvel utilisateur."""
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['email'], self.user_data['email'])

    def test_user_registration_invalid_email(self):
        """Test d'inscription avec un email invalide."""
        invalid_data = self.user_data.copy()
        invalid_data['email'] = 'invalid-email'
        response = self.client.post(self.register_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_user_login(self):
        """Test de connexion d'un utilisateur."""
        # D'abord créer l'utilisateur
        User.objects.create_user(**self.user_data)

        # Tenter de se connecter
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password'],
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])

    def test_user_login_wrong_password(self):
        """Test de connexion avec un mauvais mot de passe."""
        User.objects.create_user(**self.user_data)

        login_data = {
            'email': self.user_data['email'],
            'password': 'wrongpassword',
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_user_login_nonexistent(self):
        """Test de connexion avec un utilisateur qui n'existe pas."""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'password123',
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_get_current_user(self):
        """Test de récupération de l'utilisateur connecté."""
        # Créer et connecter l'utilisateur
        user = User.objects.create_user(**self.user_data)
        self.client.force_authenticate(user=user)

        me_url = reverse('me')
        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['email'], self.user_data['email'])

    def test_get_current_user_unauthenticated(self):
        """Test de récupération de l'utilisateur non authentifié."""
        me_url = reverse('me')
        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile(self):
        """Test de mise à jour du profil utilisateur."""
        user = User.objects.create_user(**self.user_data)
        self.client.force_authenticate(user=user)

        update_url = reverse('update_profile')
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
        }
        response = self.client.patch(update_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['first_name'], 'Updated')
        self.assertEqual(response.data['data']['last_name'], 'Name')

    def test_change_password(self):
        """Test de changement de mot de passe."""
        user = User.objects.create_user(**self.user_data)
        self.client.force_authenticate(user=user)

        change_password_url = reverse('change_password')
        password_data = {
            'old_password': self.user_data['password'],
            'new_password': 'newpassword123',
        }
        response = self.client.post(change_password_url, password_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Vérifier que l'ancien mot de passe ne fonctionne plus
        user.refresh_from_db()
        self.assertFalse(user.check_password(self.user_data['password']))
        self.assertTrue(user.check_password('newpassword123'))

    def test_change_password_wrong_old_password(self):
        """Test de changement de mot de passe avec mauvais ancien mot de passe."""
        user = User.objects.create_user(**self.user_data)
        self.client.force_authenticate(user=user)

        change_password_url = reverse('change_password')
        password_data = {
            'old_password': 'wrongoldpassword',
            'new_password': 'newpassword123',
        }
        response = self.client.post(change_password_url, password_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
