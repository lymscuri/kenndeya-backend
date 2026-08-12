"""
Tests de non-régression sur les contrôles d'accès patient (IDOR).

Contexte : ChirurgieListCreateView et HospitalisationListCreateView
étaient en IsAuthenticated sans filtre de propriété, permettant à
tout compte authentifié de lire/écrire les chirurgies et hospitalisations
d'un patient quelconque via son UUID. Le fix a passé les deux vues en
IsDoctor + get_object_or_404(Patient, id=..., doctor=request.user).

Ces tests figent le comportement attendu :
- médecin propriétaire du patient : 200/201
- autre médecin : 404 (pas 403 : on ne fuite pas l'existence)
- patient authentifié : 403 (bloqué en amont par IsDoctor)

Même couverture pour maternity_patient_detail_simple, corrigée en même
temps (get_object_or_404(Patient, id=patient_id, doctor=request.user)).
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.dossiers.models import Chirurgie, Hospitalisation, Patient
from apps.maternite.models import MaternityPatient


User = get_user_model()


# ---------------------------------------------------------------------------
# Base de setup partagée : deux médecins (owner + autre), un patient (pour
# l'owner), un compte patient sans lien.
# ---------------------------------------------------------------------------
class _PermissionSetup:
    """Mixin pour installer un jeu de comptes réutilisables."""

    def _install_actors(self):
        self.owner_doctor = User.objects.create_user(
            email='owner_doc@test.com', password='pwd_test_only',
            first_name='Owner', last_name='Doc', role='doctor',
        )
        self.other_doctor = User.objects.create_user(
            email='other_doc@test.com', password='pwd_test_only',
            first_name='Other', last_name='Doc', role='doctor',
        )
        self.patient_user = User.objects.create_user(
            email='pat@test.com', password='pwd_test_only',
            first_name='Some', last_name='Patient', role='patient',
        )

        self.patient = Patient.objects.create(
            doctor=self.owner_doctor,
            first_name='Own', last_name='Patient',
            date_of_birth=date.today() - timedelta(days=365 * 30),
            gender='M',
            phone='+22400000301',
        )

    def _client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def _uuid_in(self, body: bytes) -> bool:
        """Retourne True si l'UUID du patient apparaît dans la réponse
        (indice de fuite d'existence)."""
        return str(self.patient.id) in body.decode('utf-8', errors='replace')


# ===========================================================================
# ChirurgieListCreateView
# ===========================================================================
class ChirurgiePermissionTest(_PermissionSetup, APITestCase):

    def setUp(self):
        self._install_actors()
        self.url = reverse('chirurgie_list_create', kwargs={
            'patient_id': self.patient.id,
        })
        # Un enregistrement existant pour que GET puisse renvoyer du contenu
        # au propriétaire — sans quoi on ne verrait pas la différence entre
        # accès légitime et queryset filtré à vide.
        self.existing = Chirurgie.objects.create(
            patient=self.patient,
            nom='Appendicectomie',
            hopital='Donka',
        )
        self.payload = {
            'nom': 'Test op',
            'date': date.today().isoformat(),
            'hopital': 'Kaloum',
            'notes': '',
        }

    # ── GET ────────────────────────────────────────────────────────────────
    def test_get_medecin_owner_ok(self):
        response = self._client_for(self.owner_doctor).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        results = response.data.get('results', response.data)
        # ListCreateAPIView renvoie la liste paginée : au moins 1 entrée.
        self.assertTrue(results, f"Réponse vide inattendue : {response.data}")

    def test_get_autre_medecin_refuse_et_ne_fuite_pas_le_patient(self):
        response = self._client_for(self.other_doctor).get(self.url)
        # get_object_or_404 sur Patient(doctor=other) → 404, pas 403.
        # C'est la propriété "safe" : indistinguable de "patient inexistant".
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                         response.data)
        self.assertFalse(
            self._uuid_in(response.content),
            f"L'UUID du patient fuite dans le corps 404 : {response.content!r}",
        )

    def test_get_patient_authentifie_refuse(self):
        response = self._client_for(self.patient_user).get(self.url)
        # IsDoctor rejette en amont — 403 avant d'atteindre get_queryset.
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.data)

    # ── POST ───────────────────────────────────────────────────────────────
    def test_post_medecin_owner_cree(self):
        before = Chirurgie.objects.filter(patient=self.patient).count()
        response = self._client_for(self.owner_doctor).post(
            self.url, self.payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.data)
        self.assertEqual(
            Chirurgie.objects.filter(patient=self.patient).count(),
            before + 1,
        )

    def test_post_autre_medecin_refuse_et_ne_cree_rien(self):
        before = Chirurgie.objects.filter(patient=self.patient).count()
        response = self._client_for(self.other_doctor).post(
            self.url, self.payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                         response.data)
        self.assertEqual(
            Chirurgie.objects.filter(patient=self.patient).count(),
            before,
            "Aucune chirurgie ne doit être créée par un médecin non owner.",
        )

    def test_post_patient_authentifie_refuse(self):
        before = Chirurgie.objects.filter(patient=self.patient).count()
        response = self._client_for(self.patient_user).post(
            self.url, self.payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.data)
        self.assertEqual(
            Chirurgie.objects.filter(patient=self.patient).count(),
            before,
        )


# ===========================================================================
# HospitalisationListCreateView — même matrice.
# ===========================================================================
class HospitalisationPermissionTest(_PermissionSetup, APITestCase):

    def setUp(self):
        self._install_actors()
        self.url = reverse('hospitalisation_list_create', kwargs={
            'patient_id': self.patient.id,
        })
        self.existing = Hospitalisation.objects.create(
            patient=self.patient,
            motif='Observation',
            hopital='Donka',
        )
        self.payload = {
            'motif': 'Test motif',
            'date_entree': date.today().isoformat(),
            'hopital': 'Kaloum',
            'notes': '',
        }

    # ── GET ────────────────────────────────────────────────────────────────
    def test_get_medecin_owner_ok(self):
        response = self._client_for(self.owner_doctor).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        results = response.data.get('results', response.data)
        self.assertTrue(results, f"Réponse vide inattendue : {response.data}")

    def test_get_autre_medecin_refuse_et_ne_fuite_pas_le_patient(self):
        response = self._client_for(self.other_doctor).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                         response.data)
        self.assertFalse(
            self._uuid_in(response.content),
            f"L'UUID du patient fuite dans le corps 404 : {response.content!r}",
        )

    def test_get_patient_authentifie_refuse(self):
        response = self._client_for(self.patient_user).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.data)

    # ── POST ───────────────────────────────────────────────────────────────
    def test_post_medecin_owner_cree(self):
        before = Hospitalisation.objects.filter(patient=self.patient).count()
        response = self._client_for(self.owner_doctor).post(
            self.url, self.payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.data)
        self.assertEqual(
            Hospitalisation.objects.filter(patient=self.patient).count(),
            before + 1,
        )

    def test_post_autre_medecin_refuse_et_ne_cree_rien(self):
        before = Hospitalisation.objects.filter(patient=self.patient).count()
        response = self._client_for(self.other_doctor).post(
            self.url, self.payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                         response.data)
        self.assertEqual(
            Hospitalisation.objects.filter(patient=self.patient).count(),
            before,
        )

    def test_post_patient_authentifie_refuse(self):
        before = Hospitalisation.objects.filter(patient=self.patient).count()
        response = self._client_for(self.patient_user).post(
            self.url, self.payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.data)
        self.assertEqual(
            Hospitalisation.objects.filter(patient=self.patient).count(),
            before,
        )


# ===========================================================================
# maternity_patient_detail_simple — corrigée dans le même commit.
# GET /api/v1/maternity/patients/:id/
# ===========================================================================
class MaternityPatientDetailSimplePermissionTest(_PermissionSetup, APITestCase):

    def setUp(self):
        self._install_actors()
        # Endpoint utilisable même sans MaternityPatient (c'est un stub qui
        # renvoie {id}). On ne crée le profil que pour être réaliste ;
        # aucun test ne dépend de sa présence.
        MaternityPatient.objects.create(patient=self.patient)
        self.url = reverse('maternity_patient_detail_simple', kwargs={
            'patient_id': self.patient.id,
        })

    def test_get_medecin_owner_ok(self):
        response = self._client_for(self.owner_doctor).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['data']['id'], str(self.patient.id))

    def test_get_autre_medecin_refuse_et_ne_fuite_pas_le_patient(self):
        response = self._client_for(self.other_doctor).get(self.url)
        # get_object_or_404(Patient, id=..., doctor=request.user) → 404.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND,
                         response.data)
        self.assertFalse(
            self._uuid_in(response.content),
            f"L'UUID du patient fuite dans le corps 404 : {response.content!r}",
        )

    def test_get_patient_authentifie_refuse(self):
        # La vue est en IsDoctor → un compte patient est rejeté 403.
        response = self._client_for(self.patient_user).get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.data)
