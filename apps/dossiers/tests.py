"""
Tests pour l'application dossiers.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from datetime import date, timedelta
from django.utils import timezone

from .models import Patient, MedicalRecord, Consultation, Prescription, LabTest, Vaccination

User = get_user_model()


class PatientModelTest(TestCase):
    """Tests pour le modèle Patient."""

    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor@test.com',
            password='password123',
            first_name='Doctor',
            last_name='Test',
            role='doctor'
        )
        self.patient_data = {
            'doctor': self.doctor,
            'first_name': 'Patient',
            'last_name': 'Test',
            'date_of_birth': date.today() - timedelta(days=365 * 25),
            'gender': 'M',
            'phone': '+224621234567',
            'email': 'patient@test.com',
        }

    def test_create_patient(self):
        """Test de création d'un patient."""
        patient = Patient.objects.create(**self.patient_data)
        self.assertEqual(patient.first_name, 'Patient')
        self.assertEqual(patient.last_name, 'Test')
        self.assertEqual(patient.doctor, self.doctor)

    def test_patient_full_name(self):
        """Test de la propriété full_name."""
        patient = Patient.objects.create(**self.patient_data)
        self.assertEqual(patient.full_name, 'Patient Test')

    def test_patient_age(self):
        """Test du calcul de l'âge."""
        patient = Patient.objects.create(**self.patient_data)
        self.assertEqual(patient.age, 25)

    def test_medical_record_auto_creation(self):
        """Test que le dossier médical est créé automatiquement."""
        patient = Patient.objects.create(**self.patient_data)
        medical_record = MedicalRecord.objects.create(patient=patient)
        self.assertIsNotNone(medical_record)
        self.assertTrue(medical_record.record_number.startswith('DME-'))


class PatientAPITest(APITestCase):
    """Tests pour les endpoints de l'API Patient."""

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

        self.patient_data = {
            'first_name': 'New',
            'last_name': 'Patient',
            'date_of_birth': '1995-01-15',
            'gender': 'F',
            'phone': '+224621234567',
            'email': 'newpatient@test.com',
            'city': 'Conakry',
        }

    def test_create_patient(self):
        """Test de création d'un patient via l'API."""
        url = reverse('patient_list_create')
        response = self.client.post(url, self.patient_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['first_name'], 'New')

        # Vérifier que le dossier médical a été créé
        patient_id = response.data['data']['id']
        self.assertTrue(MedicalRecord.objects.filter(patient__id=patient_id).exists())

    def test_list_patients(self):
        """Test de listing des patients."""
        # Créer quelques patients
        Patient.objects.create(
            doctor=self.doctor,
            first_name='Patient1',
            last_name='Test',
            date_of_birth=date.today() - timedelta(days=365 * 30),
            gender='M',
            phone='+224621111111',
        )
        Patient.objects.create(
            doctor=self.doctor,
            first_name='Patient2',
            last_name='Test',
            date_of_birth=date.today() - timedelta(days=365 * 25),
            gender='F',
            phone='+224622222222',
        )

        url = reverse('patient_list_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 2)

    def test_get_patient_detail(self):
        """Test de récupération des détails d'un patient."""
        patient = Patient.objects.create(
            doctor=self.doctor,
            first_name='Detail',
            last_name='Patient',
            date_of_birth=date.today() - timedelta(days=365 * 28),
            gender='M',
            phone='+224623333333',
        )

        url = reverse('patient_detail', kwargs={'patient_id': patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['first_name'], 'Detail')

    def test_update_patient(self):
        """Test de mise à jour d'un patient."""
        patient = Patient.objects.create(
            doctor=self.doctor,
            first_name='Update',
            last_name='Patient',
            date_of_birth=date.today() - timedelta(days=365 * 30),
            gender='M',
            phone='+224624444444',
        )

        url = reverse('patient_detail', kwargs={'patient_id': patient.id})
        update_data = {'first_name': 'Updated'}
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['first_name'], 'Updated')

    def test_delete_patient(self):
        """Test de suppression d'un patient."""
        patient = Patient.objects.create(
            doctor=self.doctor,
            first_name='Delete',
            last_name='Patient',
            date_of_birth=date.today() - timedelta(days=365 * 22),
            gender='F',
            phone='+224625555555',
        )

        url = reverse('patient_detail', kwargs={'patient_id': patient.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertFalse(Patient.objects.filter(id=patient.id).exists())


class ConsultationAPITest(APITestCase):
    """Tests pour les endpoints de consultation."""

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
            first_name='Patient',
            last_name='Test',
            date_of_birth=date.today() - timedelta(days=365 * 30),
            gender='M',
            phone='+224626666666',
        )

        self.consultation_data = {
            'date': timezone.now().isoformat(),
            'reason': 'Consultation de routine',
            'symptoms': 'Fièvre',
            'diagnosis': 'Grippe',
            'treatment': 'Repos et hydratation',
            'temperature': 38.5,
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
        }

    def test_create_consultation(self):
        """Test de création d'une consultation."""
        url = reverse('consultation_list_create', kwargs={'patient_id': self.patient.id})
        response = self.client.post(url, self.consultation_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['reason'], 'Consultation de routine')

    def test_list_consultations(self):
        """Test de listing des consultations d'un patient."""
        Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=timezone.now(),
            reason='Première consultation',
            diagnosis='Test',
        )
        Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=timezone.now(),
            reason='Deuxième consultation',
            diagnosis='Test',
        )

        url = reverse('consultation_list_create', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 2)

    def test_blood_pressure_validation(self):
        """Test de validation de la pression artérielle."""
        url = reverse('consultation_list_create', kwargs={'patient_id': self.patient.id})
        invalid_data = self.consultation_data.copy()
        invalid_data['blood_pressure_systolic'] = 80
        invalid_data['blood_pressure_diastolic'] = 120  # Diastolique > Systolique

        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
