"""
Tests pour l'application urgences.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone

from .models import Secourist, Hospital, EmergencyAlert

User = get_user_model()


class SecouristModelTest(TestCase):
    """Tests pour le modèle Secourist."""

    def setUp(self):
        self.secourist_user = User.objects.create_user(
            email='secourist@test.com',
            password='password123',
            first_name='John',
            last_name='Secourist',
            role='secourist'
        )

    def test_create_secourist(self):
        """Test de création d'un secouriste."""
        secourist = Secourist.objects.create(
            user=self.secourist_user,
            specialization='Paramédic',
            license_number='SEC-12345',
            is_available=True,
        )
        self.assertEqual(secourist.user, self.secourist_user)
        self.assertEqual(secourist.specialization, 'Paramédic')
        self.assertTrue(secourist.is_available)

    def test_secourist_str(self):
        """Test de la représentation string."""
        secourist = Secourist.objects.create(
            user=self.secourist_user,
            specialization='Ambulancier',
        )
        expected = f"{self.secourist_user.get_full_name()} - Ambulancier"
        self.assertEqual(str(secourist), expected)


class HospitalModelTest(TestCase):
    """Tests pour le modèle Hospital."""

    def test_create_hospital(self):
        """Test de création d'un hôpital."""
        hospital = Hospital.objects.create(
            name='Hôpital National',
            address='123 Rue de la Santé',
            city='Conakry',
            phone='+224621111111',
            hospital_type='public',
            capacity=500,
            has_emergency_room=True,
            has_maternity=True,
        )
        self.assertEqual(hospital.name, 'Hôpital National')
        self.assertEqual(hospital.city, 'Conakry')
        self.assertTrue(hospital.has_emergency_room)
        self.assertTrue(hospital.is_active)

    def test_hospital_str(self):
        """Test de la représentation string."""
        hospital = Hospital.objects.create(
            name='Clinique Privée',
            address='456 Avenue',
            city='Kindia',
            hospital_type='private',
        )
        expected = "Clinique Privée - Kindia"
        self.assertEqual(str(hospital), expected)


class EmergencyAlertModelTest(TestCase):
    """Tests pour le modèle EmergencyAlert."""

    def setUp(self):
        self.patient_user = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient',
            last_name='Test',
            role='patient'
        )
        self.secourist_user = User.objects.create_user(
            email='secourist@test.com',
            password='password123',
            first_name='Secourist',
            last_name='Test',
            role='secourist'
        )
        self.secourist = Secourist.objects.create(user=self.secourist_user)
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            address='Test Address',
            city='Conakry',
        )

    def test_create_emergency_alert(self):
        """Test de création d'une alerte d'urgence."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            status='pending',
            priority='high',
            emergency_type='Accident',
            description='Accident de la route',
            patient_latitude=9.5092,
            patient_longitude=-13.7122,
        )
        self.assertEqual(alert.patient, self.patient_user)
        self.assertEqual(alert.status, 'pending')
        self.assertEqual(alert.priority, 'high')

    def test_emergency_alert_str(self):
        """Test de la représentation string."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            status='assigned',
            priority='critical',
        )
        self.assertIn('Alerte', str(alert))
        self.assertIn(self.patient_user.get_full_name(), str(alert))
        self.assertIn('assigned', str(alert))

    def test_emergency_alert_assignment(self):
        """Test d'assignation d'une alerte à un secouriste."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            status='pending',
        )
        # Assigner l'alerte
        alert.secourist = self.secourist
        alert.status = 'assigned'
        alert.assigned_at = timezone.now()
        alert.save()

        self.assertEqual(alert.secourist, self.secourist)
        self.assertEqual(alert.status, 'assigned')
        self.assertIsNotNone(alert.assigned_at)


class SecouristAPITest(APITestCase):
    """Tests pour les endpoints de secouriste."""

    def setUp(self):
        self.client = APIClient()
        self.secourist_user = User.objects.create_user(
            email='secourist@test.com',
            password='password123',
            first_name='Secourist',
            last_name='Test',
            role='secourist'
        )
        self.client.force_authenticate(user=self.secourist_user)

    def test_create_secourist_profile(self):
        """Test de création d'un profil de secouriste."""
        url = reverse('secourist_profile_create')
        data = {
            'specialization': 'Paramédic',
            'license_number': 'SEC-12345',
            'is_available': True,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['specialization'], 'Paramédic')

    def test_create_duplicate_secourist_profile(self):
        """Test qu'on ne peut pas créer deux profils pour le même utilisateur."""
        Secourist.objects.create(user=self.secourist_user)

        url = reverse('secourist_profile_create')
        data = {'specialization': 'Ambulancier'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_get_secourist_profile_detail(self):
        """Test de récupération du profil de secouriste."""
        Secourist.objects.create(
            user=self.secourist_user,
            specialization='Paramédic'
        )

        url = reverse('secourist_profile_detail')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['specialization'], 'Paramédic')

    def test_update_secourist_profile(self):
        """Test de mise à jour du profil de secouriste."""
        Secourist.objects.create(
            user=self.secourist_user,
            specialization='Paramédic',
            is_available=True
        )

        url = reverse('secourist_profile_detail')
        data = {'is_available': False}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(response.data['data']['is_available'])

    def test_list_available_secourists(self):
        """Test de listing des secouristes disponibles."""
        # Créer quelques secouristes
        user1 = User.objects.create_user(
            email='sec1@test.com',
            password='password123',
            first_name='Sec1',
            last_name='Test',
            role='secourist'
        )
        Secourist.objects.create(user=user1, is_available=True)

        user2 = User.objects.create_user(
            email='sec2@test.com',
            password='password123',
            first_name='Sec2',
            last_name='Test',
            role='secourist'
        )
        Secourist.objects.create(user=user2, is_available=True)

        url = reverse('secourist_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertGreaterEqual(response.data['count'], 2)


class HospitalAPITest(APITestCase):
    """Tests pour les endpoints d'hôpitaux."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@test.com',
            password='password123',
            first_name='User',
            last_name='Test',
            role='patient'
        )
        self.client.force_authenticate(user=self.user)

        self.hospital = Hospital.objects.create(
            name='Hôpital Test',
            address='123 Rue Test',
            city='Conakry',
            hospital_type='public',
            has_emergency_room=True,
            is_active=True,
        )

    def test_list_hospitals(self):
        """Test de listing des hôpitaux."""
        url = reverse('hospital_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_filter_hospitals_by_city(self):
        """Test de filtrage des hôpitaux par ville."""
        Hospital.objects.create(
            name='Hôpital Kindia',
            address='456 Avenue',
            city='Kindia',
            is_active=True,
        )

        url = reverse('hospital_list')
        response = self.client.get(url, {'city': 'Kindia'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_filter_hospitals_by_emergency_room(self):
        """Test de filtrage des hôpitaux avec service d'urgence."""
        url = reverse('hospital_list')
        response = self.client.get(url, {'has_emergency_room': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_get_hospital_detail(self):
        """Test de récupération des détails d'un hôpital."""
        url = reverse('hospital_detail', kwargs={'hospital_id': self.hospital.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Hôpital Test')


class EmergencyAlertAPITest(APITestCase):
    """Tests pour les endpoints d'alertes d'urgence."""

    def setUp(self):
        self.client = APIClient()

        # Créer un patient
        self.patient_user = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient',
            last_name='Test',
            role='patient'
        )

        # Créer un secouriste
        self.secourist_user = User.objects.create_user(
            email='secourist@test.com',
            password='password123',
            first_name='Secourist',
            last_name='Test',
            role='secourist'
        )
        self.secourist = Secourist.objects.create(
            user=self.secourist_user,
            is_available=True
        )

        # Créer un hôpital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            address='Test Address',
            city='Conakry',
        )

    def test_create_emergency_alert(self):
        """Test de création d'une alerte d'urgence."""
        self.client.force_authenticate(user=self.patient_user)

        url = reverse('emergency_alert_create')
        data = {
            'priority': 'high',
            'emergency_type': 'Accident',
            'description': 'Accident de moto',
            'symptoms': 'Douleur jambe',
            'patient_latitude': 9.5092,
            'patient_longitude': -13.7122,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['priority'], 'high')
        self.assertEqual(response.data['data']['status'], 'pending')

    def test_list_patient_alerts(self):
        """Test de listing des alertes d'un patient."""
        self.client.force_authenticate(user=self.patient_user)

        # Créer des alertes
        EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='high',
            status='pending',
        )
        EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='medium',
            status='resolved',
        )

        url = reverse('emergency_alert_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 2)

    def test_list_secourist_assigned_alerts(self):
        """Test de listing des alertes assignées à un secouriste."""
        self.client.force_authenticate(user=self.secourist_user)

        # Créer des alertes assignées
        EmergencyAlert.objects.create(
            patient=self.patient_user,
            secourist=self.secourist,
            status='assigned',
        )

        url = reverse('emergency_alert_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_get_alert_detail_as_patient(self):
        """Test de récupération d'une alerte par le patient."""
        self.client.force_authenticate(user=self.patient_user)

        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='critical',
        )

        url = reverse('emergency_alert_detail', kwargs={'alert_id': alert.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_get_alert_detail_as_assigned_secourist(self):
        """Test de récupération d'une alerte par le secouriste assigné."""
        self.client.force_authenticate(user=self.secourist_user)

        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            secourist=self.secourist,
            status='assigned',
        )

        url = reverse('emergency_alert_detail', kwargs={'alert_id': alert.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_get_alert_detail_unauthorized(self):
        """Test qu'un patient ne peut pas accéder aux alertes d'autres patients."""
        other_patient = User.objects.create_user(
            email='other@test.com',
            password='password123',
            first_name='Other',
            last_name='Patient',
            role='patient'
        )

        alert = EmergencyAlert.objects.create(
            patient=other_patient,
            priority='high',
        )

        self.client.force_authenticate(user=self.patient_user)
        url = reverse('emergency_alert_detail', kwargs={'alert_id': alert.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success'])

    def test_assign_alert_to_secourist(self):
        """Test d'assignation d'une alerte à un secouriste."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='high',
            status='pending',
        )

        self.client.force_authenticate(user=self.secourist_user)
        url = reverse('emergency_alert_assign', kwargs={'alert_id': alert.id})
        response = self.client.patch(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['status'], 'assigned')
        self.assertIsNotNone(response.data['data']['assigned_at'])

    def test_assign_alert_already_assigned(self):
        """Test qu'on ne peut pas assigner une alerte déjà assignée."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='high',
            status='assigned',
            secourist=self.secourist,
        )

        # Créer un autre secouriste
        other_sec_user = User.objects.create_user(
            email='other_sec@test.com',
            password='password123',
            first_name='Other',
            last_name='Secourist',
            role='secourist'
        )
        other_sec = Secourist.objects.create(user=other_sec_user, is_available=True)

        self.client.force_authenticate(user=other_sec_user)
        url = reverse('emergency_alert_assign', kwargs={'alert_id': alert.id})
        response = self.client.patch(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_assign_alert_unavailable_secourist(self):
        """Test qu'un secouriste non disponible ne peut pas s'assigner une alerte."""
        # Rendre le secouriste non disponible
        self.secourist.is_available = False
        self.secourist.save()

        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='high',
            status='pending',
        )

        self.client.force_authenticate(user=self.secourist_user)
        url = reverse('emergency_alert_assign', kwargs={'alert_id': alert.id})
        response = self.client.patch(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_update_alert_status(self):
        """Test de mise à jour du statut d'une alerte."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            secourist=self.secourist,
            priority='high',
            status='assigned',
        )

        self.client.force_authenticate(user=self.secourist_user)
        url = reverse('emergency_alert_update_status', kwargs={'alert_id': alert.id})
        data = {
            'status': 'in_progress',
            'notes': 'En route vers le patient',
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['status'], 'in_progress')

    def test_update_alert_status_resolve(self):
        """Test de résolution d'une alerte."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            secourist=self.secourist,
            priority='high',
            status='in_progress',
        )

        self.client.force_authenticate(user=self.secourist_user)
        url = reverse('emergency_alert_update_status', kwargs={'alert_id': alert.id})
        data = {
            'status': 'resolved',
            'resolution_notes': 'Patient transporté à l\'hôpital',
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['status'], 'resolved')
        self.assertIsNotNone(response.data['data']['resolved_at'])

    def test_update_alert_status_unauthorized(self):
        """Test qu'un secouriste ne peut pas modifier une alerte non assignée à lui."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient_user,
            secourist=self.secourist,
            status='assigned',
        )

        # Créer un autre secouriste
        other_sec_user = User.objects.create_user(
            email='other_sec@test.com',
            password='password123',
            first_name='Other',
            last_name='Secourist',
            role='secourist'
        )
        Secourist.objects.create(user=other_sec_user)

        self.client.force_authenticate(user=other_sec_user)
        url = reverse('emergency_alert_update_status', kwargs={'alert_id': alert.id})
        data = {'status': 'in_progress'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success'])

    def test_list_pending_alerts(self):
        """Test de listing des alertes en attente."""
        # Créer des alertes en attente
        EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='critical',
            status='pending',
        )
        EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='high',
            status='pending',
        )
        EmergencyAlert.objects.create(
            patient=self.patient_user,
            priority='low',
            status='assigned',
        )

        self.client.force_authenticate(user=self.secourist_user)
        url = reverse('emergency_alert_pending')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 2)

        # Vérifier que les alertes sont triées par priorité
        results = response.data['results']
        if len(results) >= 2:
            # La première alerte devrait avoir une priorité plus haute
            priorities = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            self.assertGreaterEqual(
                priorities.get(results[0]['priority'], 0),
                priorities.get(results[1]['priority'], 0)
            )


class PermissionTest(APITestCase):
    """Tests des permissions pour l'application urgences."""

    def setUp(self):
        self.client = APIClient()

        self.patient = User.objects.create_user(
            email='patient@test.com',
            password='password123',
            first_name='Patient',
            last_name='Test',
            role='patient'
        )

        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )

        self.secourist_user = User.objects.create_user(
            email='secourist@test.com',
            password='password123',
            first_name='Secourist',
            last_name='Test',
            role='secourist'
        )

    def test_only_secourist_can_create_profile(self):
        """Test que seul un utilisateur avec rôle secourist peut créer un profil."""
        # Test avec un patient
        self.client.force_authenticate(user=self.patient)
        url = reverse('secourist_profile_create')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test avec un médecin
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test avec un secouriste
        self.client.force_authenticate(user=self.secourist_user)
        response = self.client.post(url, {'specialization': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_only_secourist_can_assign_alerts(self):
        """Test que seul un secouriste peut assigner des alertes."""
        alert = EmergencyAlert.objects.create(
            patient=self.patient,
            status='pending',
        )

        # Test avec un patient
        self.client.force_authenticate(user=self.patient)
        url = reverse('emergency_alert_assign', kwargs={'alert_id': alert.id})
        response = self.client.patch(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test avec un médecin
        self.client.force_authenticate(user=self.doctor)
        response = self.client.patch(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
