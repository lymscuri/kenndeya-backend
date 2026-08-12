"""
Commande Django pour charger des données de test.
Usage: python manage.py seed_data
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime
import random

from apps.accounts.models import User
from apps.dossiers.models import Patient, MedicalRecord, Consultation, Prescription, LabTest, Vaccination
from apps.maternite.models import MaternityPatient, Pregnancy, WeeklyCheckup, PrenatalConsultation, Child
from apps.urgences.models import Secourist, Hospital, EmergencyAlert
from apps.reminders.models import SmsReminder

User = get_user_model()

# Mot de passe par défaut des comptes de test. Surchargeable via
# SEED_DATA_PASSWORD dans l'environnement pour éviter d'avoir un
# secret en dur non modifiable.
SEED_PASSWORD = os.environ.get('SEED_DATA_PASSWORD', 'password123')

# Préfixe impossible en Guinée : +224 suivi de 00... Aucun opérateur
# n'attribue de numéro commençant par 0 après l'indicatif — garantit
# qu'aucun envoi accidentel ne partira sur un vrai abonné.
_FAKE_PHONE = lambda suffix: f'+22400000{suffix:04d}'


class Command(BaseCommand):
    help = 'Charge des données de test dans la base de données'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprime toutes les données avant de charger les nouvelles',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Autorise l\'exécution même quand DEBUG=False (danger)',
        )

    def handle(self, *args, **options):
        # Garde-fou : refuser de seeder une base non-dev sans confirmation explicite.
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                'seed_data refuse de s\'exécuter avec DEBUG=False. '
                'Cette commande crée des utilisateurs et rappels SMS de test. '
                'Utiliser --force pour passer outre en toute connaissance de cause.'
            )

        if options['clear']:
            self.stdout.write(self.style.WARNING('Suppression des données existantes...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Chargement des données de test...'))

        # Créer les utilisateurs
        doctors = self.create_doctors()
        patients = self.create_patients()
        secourists = self.create_secourists()

        # Créer les hôpitaux
        hospitals = self.create_hospitals()

        # Créer les données médicales
        self.create_medical_data(doctors, patients)

        # Créer les données de maternité
        self.create_maternity_data(doctors, patients)

        # Créer les alertes d'urgence
        self.create_emergency_data(patients, secourists, hospitals)

        # Créer les rappels SMS
        self.create_reminders(doctors, patients)

        self.stdout.write(self.style.SUCCESS('✅ Données de test chargées avec succès !'))

    def clear_data(self):
        """Supprime toutes les données."""
        SmsReminder.objects.all().delete()
        EmergencyAlert.objects.all().delete()
        Hospital.objects.all().delete()
        Secourist.objects.all().delete()
        Child.objects.all().delete()
        PrenatalConsultation.objects.all().delete()
        Pregnancy.objects.all().delete()
        MaternityPatient.objects.all().delete()
        Vaccination.objects.all().delete()
        LabTest.objects.all().delete()
        Prescription.objects.all().delete()
        Consultation.objects.all().delete()
        MedicalRecord.objects.all().delete()
        Patient.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING('✓ Données supprimées'))

    def create_doctors(self):
        """Crée des médecins de test."""
        doctors = []
        doctor_data = [
            {'first_name': 'Amadou', 'last_name': 'Diallo', 'email': 'amadou.diallo@kendeya.gn', 'phone': _FAKE_PHONE(1)},
            {'first_name': 'Fatoumata', 'last_name': 'Bah', 'email': 'fatoumata.bah@kendeya.gn', 'phone': _FAKE_PHONE(2)},
            {'first_name': 'Mamadou', 'last_name': 'Camara', 'email': 'mamadou.camara@kendeya.gn', 'phone': _FAKE_PHONE(3)},
        ]

        for data in doctor_data:
            doctor, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'phone': data['phone'],
                    'role': 'doctor',
                    'is_active': True,
                }
            )
            if created:
                doctor.set_password(SEED_PASSWORD)
                doctor.save()
            doctors.append(doctor)

        self.stdout.write(self.style.SUCCESS(f'✓ {len(doctors)} médecins créés'))
        return doctors

    def create_patients(self):
        """Crée des patients de test."""
        patients = []
        patient_data = [
            {'first_name': 'Aissatou', 'last_name': 'Sylla', 'email': 'aissatou.sylla@gmail.com', 'phone': _FAKE_PHONE(4), 'gender': 'F'},
            {'first_name': 'Ibrahim', 'last_name': 'Kouyate', 'email': 'ibrahim.kouyate@gmail.com', 'phone': _FAKE_PHONE(5), 'gender': 'M'},
            {'first_name': 'Mariama', 'last_name': 'Conte', 'email': 'mariama.conte@gmail.com', 'phone': _FAKE_PHONE(6), 'gender': 'F'},
            {'first_name': 'Sekou', 'last_name': 'Toure', 'email': 'sekou.toure@gmail.com', 'phone': _FAKE_PHONE(7), 'gender': 'M'},
            {'first_name': 'Hadja', 'last_name': 'Barry', 'email': 'hadja.barry@gmail.com', 'phone': _FAKE_PHONE(8), 'gender': 'F'},
        ]

        for data in patient_data:
            patient, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'phone': data['phone'],
                    'role': 'patient',
                    'is_active': True,
                }
            )
            if created:
                patient.set_password(SEED_PASSWORD)
                patient.save()
            patients.append(patient)

        self.stdout.write(self.style.SUCCESS(f'✓ {len(patients)} patients créés'))
        return patients

    def create_secourists(self):
        """Crée des secouristes de test."""
        secourists_users = []
        secourist_data = [
            {'first_name': 'Alpha', 'last_name': 'Conde', 'email': 'alpha.conde@secours.gn', 'phone': _FAKE_PHONE(9)},
            {'first_name': 'Nene', 'last_name': 'Keita', 'email': 'nene.keita@secours.gn', 'phone': _FAKE_PHONE(10)},
        ]

        for data in secourist_data:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'phone': data['phone'],
                    'role': 'secourist',
                    'is_active': True,
                }
            )
            if created:
                user.set_password(SEED_PASSWORD)
                user.save()

            # Créer le profil secouriste
            Secourist.objects.get_or_create(
                user=user,
                defaults={
                    'specialization': 'Urgences médicales',
                    'license_number': f'SEC{random.randint(1000, 9999)}',
                    'is_available': True,
                    'latitude': 9.5092 + random.uniform(-0.1, 0.1),
                    'longitude': -13.7122 + random.uniform(-0.1, 0.1),
                }
            )
            secourists_users.append(user)

        self.stdout.write(self.style.SUCCESS(f'✓ {len(secourists_users)} secouristes créés'))
        return secourists_users

    def create_hospitals(self):
        """Crée des hôpitaux de test."""
        hospitals = []
        hospital_data = [
            {
                'name': 'Hôpital National Donka',
                'city': 'Conakry',
                'address': 'Commune de Dixinn, Conakry',
                'phone': _FAKE_PHONE(11),
                'hospital_type': 'public',
                'has_emergency_room': True,
                'has_maternity': True,
                'capacity': 500,
            },
            {
                'name': 'Clinique Pasteur',
                'city': 'Conakry',
                'address': 'Commune de Kaloum, Conakry',
                'phone': _FAKE_PHONE(12),
                'hospital_type': 'private',
                'has_emergency_room': True,
                'has_maternity': False,
                'capacity': 100,
            },
            {
                'name': 'Centre de Santé de Matoto',
                'city': 'Conakry',
                'address': 'Commune de Matoto, Conakry',
                'phone': _FAKE_PHONE(13),
                'hospital_type': 'health_center',
                'has_emergency_room': False,
                'has_maternity': True,
                'capacity': 50,
            },
        ]

        for data in hospital_data:
            hospital, created = Hospital.objects.get_or_create(
                name=data['name'],
                defaults={
                    **data,
                    'latitude': 9.5092 + random.uniform(-0.1, 0.1),
                    'longitude': -13.7122 + random.uniform(-0.1, 0.1),
                    'is_active': True,
                }
            )
            hospitals.append(hospital)

        self.stdout.write(self.style.SUCCESS(f'✓ {len(hospitals)} hôpitaux créés'))
        return hospitals

    def create_medical_data(self, doctors, patients):
        """Crée des dossiers médicaux, consultations, etc."""
        for i, patient_user in enumerate(patients[:3]):
            doctor = doctors[i % len(doctors)]

            # Créer le patient
            patient, created = Patient.objects.get_or_create(
                doctor=doctor,
                first_name=patient_user.first_name,
                last_name=patient_user.last_name,
                defaults={
                    'date_of_birth': timezone.now().date() - timedelta(days=random.randint(7300, 18250)),
                    'gender': 'F' if i % 2 == 0 else 'M',
                    'phone': patient_user.phone,
                    'email': patient_user.email,
                    'blood_type': random.choice(['A+', 'B+', 'O+', 'AB+']),
                    'allergies': 'Pénicilline' if i == 0 else '',
                    'city': 'Conakry',
                }
            )

            # Créer le dossier médical
            if created:
                MedicalRecord.objects.get_or_create(patient=patient)

                # Créer une consultation
                consultation = Consultation.objects.create(
                    patient=patient,
                    doctor=doctor,
                    date=timezone.now() - timedelta(days=random.randint(1, 30)),
                    reason='Consultation de routine',
                    symptoms='Fièvre, maux de tête',
                    diagnosis='Paludisme',
                    treatment='Artemisia + Paracétamol',
                    temperature=38.5,
                    blood_pressure_systolic=120,
                    blood_pressure_diastolic=80,
                    heart_rate=75,
                )

                # Créer une prescription
                Prescription.objects.create(
                    consultation=consultation,
                    medication_name='Artemisia-Lumefantrine',
                    dosage='4 comprimés',
                    frequency='2 fois par jour',
                    duration='3 jours',
                )

                # Créer un examen de laboratoire
                LabTest.objects.create(
                    consultation=consultation,
                    test_name='Test de paludisme',
                    test_type='blood_test',
                    status='completed',
                    results='Positif',
                )

        self.stdout.write(self.style.SUCCESS(f'✓ Dossiers médicaux créés'))

    def create_maternity_data(self, doctors, patients):
        """Crée des données de maternité."""
        # Prendre une patiente féminine
        female_patients = [p for p in patients if Patient.objects.filter(
            first_name=p.first_name, last_name=p.last_name, gender='F'
        ).exists()]

        if female_patients:
            patient_user = female_patients[0]
            doctor = doctors[0]

            patient = Patient.objects.filter(
                first_name=patient_user.first_name,
                last_name=patient_user.last_name
            ).first()

            if patient:
                # Créer profil maternité
                maternity_patient, created = MaternityPatient.objects.get_or_create(
                    patient=patient,
                    defaults={
                        'blood_rhesus': 'positive',
                        'number_of_pregnancies': 2,
                        'number_of_deliveries': 1,
                        'number_of_living_children': 1,
                    }
                )

                # Créer une grossesse
                if created:
                    pregnancy = Pregnancy.objects.create(
                        maternity_patient=maternity_patient,
                        doctor=doctor,
                        pregnancy_number=2,
                        status='ongoing',
                        last_menstrual_period=timezone.now().date() - timedelta(days=140),
                        expected_delivery_date=timezone.now().date() + timedelta(days=140),
                        weeks_of_gestation=20,
                    )

                    # Créer une CPN
                    PrenatalConsultation.objects.create(
                        pregnancy=pregnancy,
                        doctor=doctor,
                        consultation_date=timezone.now() - timedelta(days=7),
                        consultation_number=3,
                        week_of_gestation=20,
                        weight=65.5,
                        blood_pressure_systolic=115,
                        blood_pressure_diastolic=75,
                        uterine_height=20.0,
                        fetal_heart_rate=145,
                    )

        self.stdout.write(self.style.SUCCESS(f'✓ Données de maternité créées'))

    def create_emergency_data(self, patients, secourists, hospitals):
        """Crée des alertes d'urgence."""
        if patients and hospitals:
            patient = patients[0]
            hospital = hospitals[0]

            EmergencyAlert.objects.create(
                patient=patient,
                hospital=hospital,
                status='pending',
                priority='high',
                emergency_type='Urgence médicale',
                description='Douleurs thoraciques',
                symptoms='Douleur à la poitrine, essoufflement',
                patient_latitude=9.5092,
                patient_longitude=-13.7122,
                patient_address='Conakry, Kaloum',
            )

        self.stdout.write(self.style.SUCCESS(f'✓ Alertes d\'urgence créées'))

    def create_reminders(self, doctors, patients):
        """Crée des rappels SMS."""
        if doctors and patients:
            doctor = doctors[0]
            patient = patients[0]

            SmsReminder.objects.create(
                patient=patient,
                doctor=doctor,
                reminder_type='appointment',
                phone_number=patient.phone,
                message=f'Rappel: Vous avez un rendez-vous demain à 10h avec Dr. {doctor.get_full_name()}',
                scheduled_at=timezone.now() + timedelta(days=1, hours=-2),
                status='pending',
            )

        self.stdout.write(self.style.SUCCESS(f'✓ Rappels SMS créés'))
