"""
Tests pour l'application reminders.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from .models import SmsReminder
from .tasks import send_sms_reminder, process_pending_sms, cleanup_old_sms

User = get_user_model()


class SmsReminderModelTest(TestCase):
    """Tests pour le modèle SmsReminder."""

    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )
        self.patient = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient',
            last_name='Test',
            phone='+224621234567',
            role='patient'
        )

    def test_create_sms_reminder(self):
        """Test de création d'un rappel SMS."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Rappel: Rendez-vous demain à 10h',
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(reminder.patient, self.patient)
        self.assertEqual(reminder.doctor, self.doctor)
        self.assertEqual(reminder.reminder_type, 'appointment')
        self.assertEqual(reminder.status, 'pending')

    def test_sms_reminder_str(self):
        """Test de la représentation string."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='medication',
            phone_number='+224621234567',
            message='Prendre vos médicaments',
            scheduled_at=timezone.now() + timedelta(hours=12),
        )
        self.assertIn('SMS', str(reminder))
        self.assertIn('medication', str(reminder))
        self.assertIn(self.patient.get_full_name(), str(reminder))

    def test_sms_reminder_default_status(self):
        """Test que le statut par défaut est 'pending'."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='vaccination',
            phone_number='+224621234567',
            message='Vaccination prévue',
            scheduled_at=timezone.now() + timedelta(days=7),
        )
        self.assertEqual(reminder.status, 'pending')


class SmsReminderAPITest(APITestCase):
    """Tests pour les endpoints de rappels SMS."""

    def setUp(self):
        self.client = APIClient()

        # Créer un médecin
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )

        # Créer un patient
        self.patient = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient',
            last_name='Test',
            phone='+224621234567',
            role='patient'
        )

        self.client.force_authenticate(user=self.doctor)

    def test_create_sms_reminder(self):
        """Test de création d'un rappel SMS."""
        url = reverse('sms_reminder_list_create')
        data = {
            'patient': str(self.patient.id),
            'reminder_type': 'appointment',
            'phone_number': '+224621234567',
            'message': 'Rappel: Rendez-vous demain',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['reminder_type'], 'appointment')
        self.assertEqual(response.data['data']['status'], 'pending')

    def test_list_sms_reminders(self):
        """Test de listing des rappels SMS."""
        # Créer quelques rappels
        SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Rappel 1',
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='medication',
            phone_number='+224621234567',
            message='Rappel 2',
            scheduled_at=timezone.now() + timedelta(days=2),
        )

        url = reverse('sms_reminder_list_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 2)

    def test_filter_sms_reminders_by_status(self):
        """Test de filtrage des rappels par statut."""
        # Créer des rappels avec différents statuts
        SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Rappel pending',
            scheduled_at=timezone.now() + timedelta(days=1),
            status='pending',
        )
        SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='medication',
            phone_number='+224621234567',
            message='Rappel sent',
            scheduled_at=timezone.now() - timedelta(days=1),
            status='sent',
        )

        url = reverse('sms_reminder_list_create')
        response = self.client.get(url, {'status': 'pending'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

        # Vérifier que tous les résultats ont le statut 'pending'
        for reminder in response.data['results']:
            self.assertEqual(reminder['status'], 'pending')

    def test_get_sms_reminder_detail(self):
        """Test de récupération d'un rappel SMS."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='prenatal',
            phone_number='+224621234567',
            message='Consultation prénatale',
            scheduled_at=timezone.now() + timedelta(days=3),
        )

        url = reverse('sms_reminder_detail', kwargs={'reminder_id': reminder.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['reminder_type'], 'prenatal')

    def test_update_sms_reminder(self):
        """Test de mise à jour d'un rappel SMS."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Message original',
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        url = reverse('sms_reminder_detail', kwargs={'reminder_id': reminder.id})
        data = {'message': 'Message modifié'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['message'], 'Message modifié')

    def test_cannot_update_sent_reminder(self):
        """Test qu'on ne peut pas modifier un rappel déjà envoyé."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Rappel envoyé',
            scheduled_at=timezone.now() - timedelta(days=1),
            status='sent',
            sent_at=timezone.now() - timedelta(hours=1),
        )

        url = reverse('sms_reminder_detail', kwargs={'reminder_id': reminder.id})
        data = {'message': 'Tentative de modification'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error']['code'], 'invalid_status')

    def test_delete_sms_reminder(self):
        """Test de suppression (annulation) d'un rappel SMS."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Rappel à annuler',
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        url = reverse('sms_reminder_detail', kwargs={'reminder_id': reminder.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Vérifier que le statut est 'cancelled'
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, 'cancelled')

    def test_cannot_delete_sent_reminder(self):
        """Test qu'on ne peut pas supprimer un rappel déjà envoyé."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='medication',
            phone_number='+224621234567',
            message='Rappel envoyé',
            scheduled_at=timezone.now() - timedelta(days=1),
            status='sent',
            sent_at=timezone.now() - timedelta(hours=1),
        )

        url = reverse('sms_reminder_detail', kwargs={'reminder_id': reminder.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['error']['code'], 'invalid_status')

    def test_doctor_cannot_access_other_doctor_reminders(self):
        """Test qu'un médecin ne peut pas accéder aux rappels d'un autre médecin."""
        other_doctor = User.objects.create_user(
            email='other_doctor@test.com',
            password='password123',
            first_name='Other',
            last_name='Doctor',
            role='doctor'
        )

        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=other_doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Rappel autre médecin',
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        url = reverse('sms_reminder_detail', kwargs={'reminder_id': reminder.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CeleryTaskTest(TestCase):
    """Tests pour les tâches Celery."""

    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )
        self.patient = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient',
            last_name='Test',
            phone='+224621234567',
            role='patient'
        )

    def test_send_sms_reminder_task(self):
        """Test de la tâche d'envoi de SMS."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Test SMS',
            scheduled_at=timezone.now(),
            status='pending',
        )

        # Exécuter la tâche
        result = send_sms_reminder(str(reminder.id))

        # Vérifier que le SMS est marqué comme envoyé
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, 'sent')
        self.assertIsNotNone(reminder.sent_at)
        self.assertIn('succès', result)

    def test_send_sms_reminder_task_nonexistent(self):
        """Test de la tâche avec un ID inexistant."""
        result = send_sms_reminder('00000000-0000-0000-0000-000000000000')
        self.assertIn('introuvable', result)

    def test_send_sms_reminder_already_sent(self):
        """Test qu'un rappel déjà envoyé n'est pas renvoyé."""
        reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='medication',
            phone_number='+224621234567',
            message='Déjà envoyé',
            scheduled_at=timezone.now() - timedelta(days=1),
            status='sent',
            sent_at=timezone.now() - timedelta(hours=1),
        )

        result = send_sms_reminder(str(reminder.id))
        self.assertIn('ignoré', result)

    @patch('apps.reminders.tasks.send_sms_reminder.delay')
    def test_process_pending_sms_task(self, mock_send):
        """Test de la tâche de traitement des SMS en attente."""
        # Créer des rappels en attente avec dates passées
        reminder1 = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Rappel 1',
            scheduled_at=timezone.now() - timedelta(hours=1),
            status='pending',
        )
        reminder2 = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='medication',
            phone_number='+224621234567',
            message='Rappel 2',
            scheduled_at=timezone.now() - timedelta(hours=2),
            status='pending',
        )

        # Créer un rappel futur (ne devrait pas être traité)
        reminder3 = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='vaccination',
            phone_number='+224621234567',
            message='Rappel futur',
            scheduled_at=timezone.now() + timedelta(days=1),
            status='pending',
        )

        # Exécuter la tâche
        result = process_pending_sms()

        # Vérifier que send_sms_reminder a été appelé 2 fois (pas 3)
        self.assertEqual(mock_send.call_count, 2)
        self.assertIn('2 rappels', result)

    def test_cleanup_old_sms_task(self):
        """Test de la tâche de nettoyage des anciens SMS."""
        # Créer un ancien rappel envoyé (plus de 90 jours)
        old_reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='appointment',
            phone_number='+224621234567',
            message='Ancien rappel',
            scheduled_at=timezone.now() - timedelta(days=100),
            status='sent',
        )
        # Modifier la date de création manuellement
        SmsReminder.objects.filter(id=old_reminder.id).update(
            created_at=timezone.now() - timedelta(days=100)
        )

        # Créer un rappel récent (ne devrait pas être supprimé)
        recent_reminder = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='medication',
            phone_number='+224621234567',
            message='Rappel récent',
            scheduled_at=timezone.now() - timedelta(days=1),
            status='sent',
        )

        # Créer un rappel en attente ancien (ne devrait pas être supprimé)
        old_pending = SmsReminder.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            reminder_type='vaccination',
            phone_number='+224621234567',
            message='Ancien pending',
            scheduled_at=timezone.now() - timedelta(days=100),
            status='pending',
        )
        SmsReminder.objects.filter(id=old_pending.id).update(
            created_at=timezone.now() - timedelta(days=100)
        )

        # Compter les rappels avant nettoyage
        count_before = SmsReminder.objects.count()

        # Exécuter la tâche de nettoyage
        result = cleanup_old_sms()

        # Vérifier qu'un rappel a été supprimé
        count_after = SmsReminder.objects.count()
        self.assertEqual(count_before - count_after, 1)

        # Vérifier que le rappel récent et le rappel pending existent toujours
        self.assertTrue(SmsReminder.objects.filter(id=recent_reminder.id).exists())
        self.assertTrue(SmsReminder.objects.filter(id=old_pending.id).exists())

        # Vérifier que l'ancien rappel envoyé a été supprimé
        self.assertFalse(SmsReminder.objects.filter(id=old_reminder.id).exists())


class PermissionTest(APITestCase):
    """Tests des permissions pour l'application reminders."""

    def setUp(self):
        self.client = APIClient()

        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )

        self.patient = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient',
            last_name='Test',
            phone='+224621234567',
            role='patient'
        )

        self.secourist = User.objects.create_user(
            email='secourist@test.com',
            password='password123',
            first_name='Secourist',
            last_name='Test',
            role='secourist'
        )

    def test_only_doctor_can_create_reminder(self):
        """Test que seul un médecin peut créer un rappel."""
        url = reverse('sms_reminder_list_create')
        data = {
            'patient': str(self.patient.id),
            'reminder_type': 'appointment',
            'phone_number': '+224621234567',
            'message': 'Test',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
        }

        # Test avec un patient
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test avec un secouriste
        self.client.force_authenticate(user=self.secourist)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test avec un médecin
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_only_doctor_can_list_reminders(self):
        """Test que seul un médecin peut lister les rappels."""
        url = reverse('sms_reminder_list_create')

        # Test avec un patient
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test avec un secouriste
        self.client.force_authenticate(user=self.secourist)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test avec un médecin
        self.client.force_authenticate(user=self.doctor)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
