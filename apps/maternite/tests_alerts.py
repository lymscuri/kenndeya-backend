"""
Tests de la règle d'alerte obstétricale (apps.maternite.alerts) et du
contrôle d'accès de weekly_checkup_list_create.

La règle est pure et se prête à des tests unitaires sans DB : on utilise
un checkup fictif (namedtuple) plutôt que WeeklyCheckup. La DB n'est
mobilisée que pour evaluate_pregnancy et pour les tests d'API.
"""

from collections import namedtuple
from datetime import date, datetime, timedelta, timezone as _tz

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.dossiers.models import Patient
from apps.maternite.alerts import (
    PRE_ECLAMPSIA_SIGNS,
    SYMPTOM_ABDOMINAL_PAIN,
    SYMPTOM_ABNORMAL_DISCHARGE,
    SYMPTOM_BLEEDING,
    SYMPTOM_BLURRY_VISION,
    SYMPTOM_EDEMA,
    SYMPTOM_FEVER,
    SYMPTOM_HEADACHE,
    SYMPTOM_REDUCED_MOVEMENTS,
    evaluate_pregnancy,
    evaluate_weekly_checkup,
)
from apps.maternite.models import MaternityPatient, Pregnancy, WeeklyCheckup


User = get_user_model()


# ---------------------------------------------------------------------------
# Helper : checkup fictif — on ne dépend pas du modèle Django.
# La règle lit ses champs via getattr(...) et tolère les attributs manquants.
# ---------------------------------------------------------------------------
FakeCheckup = namedtuple(
    'FakeCheckup',
    ['blood_pressure_systolic', 'blood_pressure_diastolic',
     'fetal_movements', 'symptoms'],
)


def make_checkup(systolic=None, diastolic=None, fetal_movements=None,
                 symptoms=None):
    return FakeCheckup(systolic, diastolic, fetal_movements, symptoms)


# ===========================================================================
# A) EvaluateWeeklyCheckup — règle pure, sans DB
# ===========================================================================
class EvaluateWeeklyCheckupLevelsTest(SimpleTestCase):
    """1. Les quatre niveaux sur des scénarios types."""

    def test_vert_checkup_sain(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(systolic=120, diastolic=80,
                         fetal_movements='normaux', symptoms=[])
        )
        self.assertEqual(level, 'vert')
        self.assertEqual(reasons, [])

    def test_jaune_mouvements_reduits_seuls(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(systolic=115, diastolic=75,
                         fetal_movements='reduits', symptoms=[])
        )
        self.assertEqual(level, 'jaune')
        self.assertIn("Mouvements fœtaux réduits", reasons)

    def test_orange_hypertension_moderee(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(systolic=145, diastolic=95, symptoms=[])
        )
        self.assertEqual(level, 'orange')
        self.assertTrue(any('surveillance 140/90' in r for r in reasons))

    def test_rouge_saignements(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(systolic=120, diastolic=80,
                         symptoms=[SYMPTOM_BLEEDING])
        )
        self.assertEqual(level, 'rouge')
        self.assertIn("Saignements déclarés", reasons)

    def test_rouge_mouvements_absents(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(fetal_movements='absents')
        )
        self.assertEqual(level, 'rouge')
        self.assertIn("Mouvements fœtaux absents", reasons)


# ---------------------------------------------------------------------------
# 2. Bornes exactes de la tension — les deux côtés de chaque seuil.
# ---------------------------------------------------------------------------
class BloodPressureBoundariesTest(SimpleTestCase):

    # Seuil orange (surveillance) — 140/90
    def test_139_89_reste_vert(self):
        level, _ = evaluate_weekly_checkup(make_checkup(139, 89))
        self.assertEqual(level, 'vert')

    def test_140_bascule_orange_par_systolique(self):
        level, _ = evaluate_weekly_checkup(make_checkup(140, 80))
        self.assertEqual(level, 'orange')

    def test_90_bascule_orange_par_diastolique(self):
        level, _ = evaluate_weekly_checkup(make_checkup(120, 90))
        self.assertEqual(level, 'orange')

    def test_140_90_est_orange(self):
        level, _ = evaluate_weekly_checkup(make_checkup(140, 90))
        self.assertEqual(level, 'orange')

    # Seuil rouge (urgence) — 160/110
    def test_159_109_reste_orange(self):
        level, _ = evaluate_weekly_checkup(make_checkup(159, 109))
        self.assertEqual(level, 'orange')

    def test_160_bascule_rouge_par_systolique(self):
        level, _ = evaluate_weekly_checkup(make_checkup(160, 100))
        self.assertEqual(level, 'rouge')

    def test_110_bascule_rouge_par_diastolique(self):
        level, _ = evaluate_weekly_checkup(make_checkup(150, 110))
        self.assertEqual(level, 'rouge')

    def test_160_110_est_rouge(self):
        level, _ = evaluate_weekly_checkup(make_checkup(160, 110))
        self.assertEqual(level, 'rouge')

    def test_hypertension_urgente_ne_double_pas_l_alerte_moderee(self):
        # 160/110 : la règle ne doit lever QU'UNE raison HTA (urgence),
        # pas aussi la raison surveillance 140/90.
        _, reasons = evaluate_weekly_checkup(make_checkup(160, 110))
        hta_urgence = [r for r in reasons if 'urgence 160/110' in r]
        hta_surveillance = [r for r in reasons if 'surveillance 140/90' in r]
        self.assertEqual(len(hta_urgence), 1)
        self.assertEqual(hta_surveillance, [])


# ---------------------------------------------------------------------------
# 3. Signes de pré-éclampsie : 1 → jaune, 2 → orange.
# ---------------------------------------------------------------------------
class PreEclampsiaSignsCountTest(SimpleTestCase):

    def test_un_signe_donne_jaune(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(symptoms=[SYMPTOM_HEADACHE])
        )
        self.assertEqual(level, 'jaune')
        self.assertTrue(
            any('Signe isolé de pré-éclampsie' in r for r in reasons),
            f"Aucune raison de signe isolé dans {reasons}",
        )

    def test_deux_signes_donnent_orange(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(symptoms=[SYMPTOM_HEADACHE, SYMPTOM_BLURRY_VISION])
        )
        self.assertEqual(level, 'orange')
        self.assertTrue(
            any('Signes de pré-éclampsie' in r for r in reasons),
            f"Aucune raison composite dans {reasons}",
        )

    def test_trois_signes_donnent_orange_pas_rouge(self):
        # La règle actuelle plafonne les signes de pré-éclampsie à orange :
        # il faut hypertension >=160/110 ou saignements pour passer rouge.
        level, _ = evaluate_weekly_checkup(
            make_checkup(symptoms=list(PRE_ECLAMPSIA_SIGNS))
        )
        self.assertEqual(level, 'orange')

    def test_deux_signes_sans_double_comptage_jaune(self):
        # Avec 2 signes on est en orange ; la raison "signe isolé" ne doit
        # PAS apparaître en plus.
        _, reasons = evaluate_weekly_checkup(
            make_checkup(symptoms=[SYMPTOM_HEADACHE, SYMPTOM_EDEMA])
        )
        raisons_isolees = [r for r in reasons if 'Signe isolé' in r]
        self.assertEqual(raisons_isolees, [])


# ---------------------------------------------------------------------------
# 4. Robustesse : checkup vide, symptoms None/vides/inconnus.
# ---------------------------------------------------------------------------
class RobustnessTest(SimpleTestCase):

    def test_checkup_vide_ne_leve_pas_et_reste_vert(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(None, None, None, None)
        )
        self.assertEqual(level, 'vert')
        self.assertEqual(reasons, [])

    def test_checkup_none_retourne_vert(self):
        level, reasons = evaluate_weekly_checkup(None)
        self.assertEqual(level, 'vert')
        self.assertEqual(reasons, [])

    def test_symptoms_none_est_toleré(self):
        level, _ = evaluate_weekly_checkup(make_checkup(symptoms=None))
        self.assertEqual(level, 'vert')

    def test_symptoms_liste_vide_est_toleré(self):
        level, _ = evaluate_weekly_checkup(make_checkup(symptoms=[]))
        self.assertEqual(level, 'vert')

    def test_symptome_inconnu_est_ignoré(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(symptoms=['libellé qui ne matche rien'])
        )
        self.assertEqual(level, 'vert')
        self.assertEqual(reasons, [])

    def test_uniquement_diastolique_declenche_alerte(self):
        # systolique None mais diastolique >=90 doit quand même compter.
        level, _ = evaluate_weekly_checkup(make_checkup(None, 95))
        self.assertEqual(level, 'orange')

    def test_uniquement_systolique_declenche_alerte(self):
        level, _ = evaluate_weekly_checkup(make_checkup(145, None))
        self.assertEqual(level, 'orange')


# ---------------------------------------------------------------------------
# 5. Reasons agrégées : TOUS les niveaux doivent apparaître, pas seulement
#    celles du niveau retenu.
# ---------------------------------------------------------------------------
class ReasonsAggregationTest(SimpleTestCase):

    def test_rouge_expose_aussi_les_raisons_orange_et_jaune(self):
        level, reasons = evaluate_weekly_checkup(
            make_checkup(
                systolic=170, diastolic=115,  # rouge (HTA urgence)
                fetal_movements='reduits',    # jaune
                symptoms=[
                    SYMPTOM_BLEEDING,          # rouge
                    SYMPTOM_FEVER,             # orange
                    SYMPTOM_ABDOMINAL_PAIN,    # orange
                    SYMPTOM_HEADACHE,          # participe à pré-éclampsie
                    SYMPTOM_EDEMA,             # participe à pré-éclampsie
                    SYMPTOM_ABNORMAL_DISCHARGE,  # jaune
                    SYMPTOM_REDUCED_MOVEMENTS,   # jaune
                ],
            )
        )
        self.assertEqual(level, 'rouge')
        joined = " || ".join(reasons)

        # Rouge
        self.assertIn('urgence 160/110', joined)
        self.assertIn('Saignements déclarés', joined)
        # Orange
        self.assertIn('Fièvre déclarée', joined)
        self.assertIn('Douleurs abdominales déclarées', joined)
        self.assertIn('Signes de pré-éclampsie', joined)
        # Jaune
        self.assertIn('Mouvements fœtaux réduits', joined)
        self.assertIn('mouvements fœtaux diminués', joined)
        self.assertIn('Pertes vaginales anormales déclarées', joined)

    def test_ordre_des_raisons_rouge_puis_orange_puis_jaune(self):
        _, reasons = evaluate_weekly_checkup(
            make_checkup(
                systolic=170, diastolic=115,
                fetal_movements='reduits',
                symptoms=[SYMPTOM_BLEEDING, SYMPTOM_FEVER],
            )
        )
        # Les raisons rouge doivent précéder les orange et les jaune.
        idx_rouge = max(
            i for i, r in enumerate(reasons)
            if 'Saignements' in r or 'urgence 160/110' in r
        )
        idx_orange = next(i for i, r in enumerate(reasons) if 'Fièvre' in r)
        idx_jaune = next(i for i, r in enumerate(reasons)
                         if 'Mouvements fœtaux réduits' in r)
        self.assertLess(idx_rouge, idx_orange)
        self.assertLess(idx_orange, idx_jaune)


# ===========================================================================
# 7 & 8) EvaluatePregnancy — teste la sélection du checkup le plus récent.
# Ces tests utilisent la base parce qu'ils vérifient l'intégration
# avec le manager Django (pregnancy.weekly_checkups.all()).
# ===========================================================================
class EvaluatePregnancyTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(
            email='doc_alerts@test.com',
            password='pwd_test_only',
            first_name='Doc', last_name='Alert', role='doctor',
        )
        cls.patient = Patient.objects.create(
            doctor=cls.doctor,
            first_name='P', last_name='A',
            date_of_birth=date.today() - timedelta(days=365 * 30),
            gender='F',
            phone='+22400000101',
        )
        cls.maternity = MaternityPatient.objects.create(patient=cls.patient)
        cls.pregnancy = Pregnancy.objects.create(
            maternity_patient=cls.maternity,
            doctor=cls.doctor,
            pregnancy_number=1,
            last_menstrual_period=date.today() - timedelta(days=140),
            expected_delivery_date=date.today() + timedelta(days=140),
        )

    def test_pregnancy_sans_checkup_retourne_vert(self):
        level, reasons = evaluate_pregnancy(self.pregnancy)
        self.assertEqual(level, 'vert')
        self.assertEqual(reasons, [])

    def test_pregnancy_none_retourne_vert(self):
        level, reasons = evaluate_pregnancy(None)
        self.assertEqual(level, 'vert')
        self.assertEqual(reasons, [])

    def test_le_plus_recent_par_checkup_date_decide(self):
        """
        Insertion volontairement dans le désordre chronologique.
        - checkup A : le plus ANCIEN, rouge (HTA urgence)
        - checkup B : le plus RÉCENT, vert
        - checkup C : intermédiaire, orange
        Ordre d'insertion : C, A, B. Attendu : vert (celui de B).
        """
        now = timezone.now()

        # C — intermédiaire (orange)
        WeeklyCheckup.objects.create(
            pregnancy=self.pregnancy,
            doctor=self.doctor,
            checkup_date=now - timedelta(days=7),
            week_number=22,
            blood_pressure_systolic=145,
            blood_pressure_diastolic=95,
            symptoms=[],
        )
        # A — le plus ancien (rouge)
        WeeklyCheckup.objects.create(
            pregnancy=self.pregnancy,
            doctor=self.doctor,
            checkup_date=now - timedelta(days=30),
            week_number=18,
            blood_pressure_systolic=170,
            blood_pressure_diastolic=115,
            symptoms=[SYMPTOM_BLEEDING],
        )
        # B — le plus récent (vert)
        WeeklyCheckup.objects.create(
            pregnancy=self.pregnancy,
            doctor=self.doctor,
            checkup_date=now,
            week_number=24,
            blood_pressure_systolic=118,
            blood_pressure_diastolic=76,
            symptoms=[],
        )

        # Recharge depuis la base pour éviter tout cache du manager.
        pregnancy = Pregnancy.objects.get(pk=self.pregnancy.pk)
        level, reasons = evaluate_pregnancy(pregnancy)
        self.assertEqual(level, 'vert')
        self.assertEqual(reasons, [])


# ===========================================================================
# B) Contrôle d'accès weekly_checkup_list_create
# ===========================================================================
class WeeklyCheckupPermissionTest(APITestCase):
    """
    Vérifie la politique d'accès documentée dans la vue :
    - médecin qui suit la patiente : autorisé
    - autre médecin : 403
    - patiente propriétaire (match email) : autorisée
    - autre patiente : 403
    """

    def setUp(self):
        # Médecin de la grossesse.
        self.doctor = User.objects.create_user(
            email='owner_doc@test.com', password='pwd_test_only',
            first_name='Own', last_name='Doc', role='doctor',
        )
        # Autre médecin, sans rapport avec cette grossesse.
        self.other_doctor = User.objects.create_user(
            email='other_doc@test.com', password='pwd_test_only',
            first_name='Other', last_name='Doc', role='doctor',
        )
        # Patiente propriétaire — même email que le Patient.email.
        self.owner_user = User.objects.create_user(
            email='owner_patient@test.com', password='pwd_test_only',
            first_name='Own', last_name='Pat', role='patient',
        )
        # Autre patiente.
        self.other_user = User.objects.create_user(
            email='other_patient@test.com', password='pwd_test_only',
            first_name='Other', last_name='Pat', role='patient',
        )

        self.patient = Patient.objects.create(
            doctor=self.doctor,
            first_name='Own', last_name='Pat',
            date_of_birth=date.today() - timedelta(days=365 * 28),
            gender='F',
            phone='+22400000201',
            email='owner_patient@test.com',
        )
        self.maternity = MaternityPatient.objects.create(patient=self.patient)
        self.pregnancy = Pregnancy.objects.create(
            maternity_patient=self.maternity,
            doctor=self.doctor,
            pregnancy_number=1,
            last_menstrual_period=date.today() - timedelta(days=140),
            expected_delivery_date=date.today() + timedelta(days=140),
        )

        self.url = reverse('weekly_checkup_list_create', kwargs={
            'patient_id': self.patient.id,
            'pregnancy_id': self.pregnancy.id,
        })
        self.valid_payload = {
            'checkup_date': timezone.now().isoformat(),
            'week_number': 20,
            'weight': 65,
            'blood_pressure_systolic': 118,
            'blood_pressure_diastolic': 76,
            'fetal_movements': 'normaux',
            'symptoms': [],
        }

    def _post_as(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(self.url, self.valid_payload, format='json')

    def test_medecin_de_la_grossesse_peut_poster(self):
        response = self._post_as(self.doctor)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.data)

    def test_autre_medecin_recoit_403(self):
        response = self._post_as(self.other_doctor)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.data)

    def test_patiente_proprietaire_peut_poster(self):
        response = self._post_as(self.owner_user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.data)

    def test_autre_patiente_recoit_403(self):
        response = self._post_as(self.other_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.data)
