"""
Tests pour l'application maternité.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from datetime import date, timedelta
from django.utils import timezone

from apps.dossiers.models import Patient
from .models import MaternityPatient, Pregnancy, WeeklyCheckup, PrenatalConsultation, Child

User = get_user_model()


class MaternityPatientModelTest(TestCase):
    """Tests pour le modèle MaternityPatient."""

    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )
        self.patient = Patient.objects.create(
            doctor=self.doctor,
            first_name='Patient',
            last_name='Test',
            date_of_birth=date.today() - timedelta(days=365 * 28),
            gender='F',
            phone='+224621234567',
        )

    def test_create_maternity_patient(self):
        """Test de création d'un profil de maternité."""
        maternity_patient = MaternityPatient.objects.create(
            patient=self.patient,
            blood_rhesus='positive',
            number_of_pregnancies=2,
            number_of_deliveries=1,
            number_of_living_children=1,
        )
        self.assertEqual(maternity_patient.patient, self.patient)
        self.assertEqual(maternity_patient.number_of_pregnancies, 2)
        self.assertEqual(maternity_patient.blood_rhesus, 'positive')

    def test_maternity_patient_str(self):
        """Test de la représentation string."""
        maternity_patient = MaternityPatient.objects.create(
            patient=self.patient,
        )
        expected = f"Profil maternité - {self.patient.full_name}"
        self.assertEqual(str(maternity_patient), expected)


class PregnancyModelTest(TestCase):
    """Tests pour le modèle Pregnancy."""

    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )
        self.patient = Patient.objects.create(
            doctor=self.doctor,
            first_name='Patient',
            last_name='Test',
            date_of_birth=date.today() - timedelta(days=365 * 28),
            gender='F',
            phone='+224621234567',
        )
        self.maternity_patient = MaternityPatient.objects.create(
            patient=self.patient,
        )

    def test_create_pregnancy(self):
        """Test de création d'une grossesse."""
        pregnancy = Pregnancy.objects.create(
            maternity_patient=self.maternity_patient,
            doctor=self.doctor,
            pregnancy_number=1,
            status='ongoing',
            last_menstrual_period=date.today() - timedelta(days=100),
            expected_delivery_date=date.today() + timedelta(days=180),
            weeks_of_gestation=14,
        )
        self.assertEqual(pregnancy.status, 'ongoing')
        self.assertEqual(pregnancy.pregnancy_number, 1)
        self.assertEqual(pregnancy.weeks_of_gestation, 14)

    def test_pregnancy_str(self):
        """Test de la représentation string."""
        pregnancy = Pregnancy.objects.create(
            maternity_patient=self.maternity_patient,
            doctor=self.doctor,
            pregnancy_number=2,
            last_menstrual_period=date.today() - timedelta(days=100),
            expected_delivery_date=date.today() + timedelta(days=180),
        )
        self.assertIn('Grossesse #2', str(pregnancy))


class MaternityAPITest(APITestCase):
    """Tests pour les endpoints de l'API Maternité."""

    def setUp(self):
        self.client = APIClient()
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )
        self.client.force_authenticate(user=self.doctor)

        self.patient = Patient.objects.create(
            doctor=self.doctor,
            first_name='Female',
            last_name='Patient',
            date_of_birth=date.today() - timedelta(days=365 * 26),
            gender='F',
            phone='+224621111111',
        )

    def test_create_maternity_profile(self):
        """Test de création d'un profil de maternité via l'API."""
        url = reverse('maternity_patient_create', kwargs={'patient_id': self.patient.id})
        data = {
            'blood_rhesus': 'positive',
            'number_of_pregnancies': 1,
            'number_of_deliveries': 0,
            'number_of_living_children': 0,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['blood_rhesus'], 'positive')

    def test_create_duplicate_maternity_profile(self):
        """Test qu'on ne peut pas créer deux profils pour la même patiente."""
        MaternityPatient.objects.create(patient=self.patient)

        url = reverse('maternity_patient_create', kwargs={'patient_id': self.patient.id})
        data = {'blood_rhesus': 'negative'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_create_pregnancy(self):
        """Test de création d'une grossesse via l'API."""
        maternity_patient = MaternityPatient.objects.create(patient=self.patient)

        url = reverse('pregnancy_list_create', kwargs={'patient_id': self.patient.id})
        data = {
            'pregnancy_number': 1,
            'status': 'ongoing',
            'last_menstrual_period': (date.today() - timedelta(days=140)).isoformat(),
            'expected_delivery_date': (date.today() + timedelta(days=140)).isoformat(),
            'weeks_of_gestation': 20,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['pregnancy_number'], 1)

    def test_list_pregnancies(self):
        """Test de listing des grossesses."""
        maternity_patient = MaternityPatient.objects.create(patient=self.patient)

        # Créer quelques grossesses
        Pregnancy.objects.create(
            maternity_patient=maternity_patient,
            doctor=self.doctor,
            pregnancy_number=1,
            last_menstrual_period=date.today() - timedelta(days=500),
            expected_delivery_date=date.today() - timedelta(days=220),
            status='completed',
        )
        Pregnancy.objects.create(
            maternity_patient=maternity_patient,
            doctor=self.doctor,
            pregnancy_number=2,
            last_menstrual_period=date.today() - timedelta(days=140),
            expected_delivery_date=date.today() + timedelta(days=140),
            status='ongoing',
        )

        url = reverse('pregnancy_list_create', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 2)

    def test_create_prenatal_consultation(self):
        """Test de création d'une consultation prénatale."""
        maternity_patient = MaternityPatient.objects.create(patient=self.patient)
        pregnancy = Pregnancy.objects.create(
            maternity_patient=maternity_patient,
            doctor=self.doctor,
            pregnancy_number=1,
            last_menstrual_period=date.today() - timedelta(days=140),
            expected_delivery_date=date.today() + timedelta(days=140),
        )

        url = reverse('prenatal_consultation_list_create', kwargs={
            'patient_id': self.patient.id,
            'pregnancy_id': pregnancy.id
        })
        data = {
            'consultation_date': timezone.now().isoformat(),
            'consultation_number': 1,
            'week_of_gestation': 20,
            'weight': 65.5,
            'blood_pressure_systolic': 115,
            'blood_pressure_diastolic': 75,
            'uterine_height': 20.0,
            'fetal_heart_rate': 145,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['consultation_number'], 1)

    def test_create_child(self):
        """Test de création d'un enfant."""
        maternity_patient = MaternityPatient.objects.create(patient=self.patient)
        pregnancy = Pregnancy.objects.create(
            maternity_patient=maternity_patient,
            doctor=self.doctor,
            pregnancy_number=1,
            last_menstrual_period=date.today() - timedelta(days=280),
            expected_delivery_date=date.today(),
            status='completed',
        )

        url = reverse('child_list_create', kwargs={
            'patient_id': self.patient.id,
            'pregnancy_id': pregnancy.id
        })
        data = {
            'first_name': 'Baby',
            'last_name': 'Test',
            'gender': 'M',
            'birth_date': timezone.now().isoformat(),
            'birth_weight': 3.5,
            'birth_height': 50.0,
            'apgar_score_1min': 9,
            'apgar_score_5min': 10,
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['first_name'], 'Baby')

    def test_pregnancy_date_validation(self):
        """Test de validation des dates de grossesse."""
        maternity_patient = MaternityPatient.objects.create(patient=self.patient)

        url = reverse('pregnancy_list_create', kwargs={'patient_id': self.patient.id})
        # Date prévue d'accouchement avant date des dernières règles
        data = {
            'pregnancy_number': 1,
            'last_menstrual_period': date.today().isoformat(),
            'expected_delivery_date': (date.today() - timedelta(days=1)).isoformat(),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])


class ChildModelTest(TestCase):
    """Tests pour le modèle Child."""

    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )
        self.patient = Patient.objects.create(
            doctor=self.doctor,
            first_name='Mother',
            last_name='Test',
            date_of_birth=date.today() - timedelta(days=365 * 28),
            gender='F',
            phone='+224621234567',
        )
        self.maternity_patient = MaternityPatient.objects.create(patient=self.patient)
        self.pregnancy = Pregnancy.objects.create(
            maternity_patient=self.maternity_patient,
            doctor=self.doctor,
            pregnancy_number=1,
            last_menstrual_period=date.today() - timedelta(days=280),
            expected_delivery_date=date.today(),
        )

    def test_create_child(self):
        """Test de création d'un enfant."""
        child = Child.objects.create(
            pregnancy=self.pregnancy,
            first_name='Baby',
            last_name='Test',
            gender='F',
            birth_date=timezone.now(),
            birth_weight=3.2,
            birth_height=49.0,
            apgar_score_1min=8,
            apgar_score_5min=9,
        )
        self.assertEqual(child.first_name, 'Baby')
        self.assertEqual(child.gender, 'F')
        self.assertEqual(child.full_name, 'Baby Test')

    def test_child_full_name_property(self):
        """Test de la propriété full_name."""
        child = Child.objects.create(
            pregnancy=self.pregnancy,
            first_name='Jean',
            last_name='Dupont',
            gender='M',
            birth_date=timezone.now(),
        )
        self.assertEqual(child.full_name, 'Jean Dupont')
