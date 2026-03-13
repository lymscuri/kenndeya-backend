"""
Modèles pour l'application maternité.
Gère le suivi des grossesses, consultations prénatales et enfants.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.dossiers.models import Patient
from apps.accounts.models import User


class MaternityPatient(models.Model):
    """
    Patient de maternité (extension du Patient général).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        related_name='maternity_profile',
        verbose_name="Patient"
    )
    blood_rhesus = models.CharField(
        max_length=10,
        choices=[('positive', 'Positif'), ('negative', 'Négatif')],
        blank=True,
        default='',
        verbose_name="Rhésus"
    )
    number_of_pregnancies = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Nombre de grossesses (Gestité)"
    )
    number_of_deliveries = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Nombre d'accouchements (Parité)"
    )
    number_of_living_children = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Nombre d'enfants vivants"
    )
    medical_history = models.TextField(
        blank=True,
        default='',
        verbose_name="Antécédents médicaux"
    )
    obstetric_history = models.TextField(
        blank=True,
        default='',
        verbose_name="Antécédents obstétricaux"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'maternity_patients'
        verbose_name = "Patiente de Maternité"
        verbose_name_plural = "Patientes de Maternité"
        ordering = ['-created_at']

    def __str__(self):
        return f"Profil maternité - {self.patient.full_name}"


class Pregnancy(models.Model):
    """
    Grossesse suivie.
    """
    STATUS_CHOICES = [
        ('ongoing', 'En cours'),
        ('completed', 'Terminée'),
        ('miscarriage', 'Fausse couche'),
        ('terminated', 'Interrompue'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    maternity_patient = models.ForeignKey(
        MaternityPatient,
        on_delete=models.CASCADE,
        related_name='pregnancies',
        verbose_name="Patiente"
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pregnancies_monitored',
        verbose_name="Médecin"
    )
    pregnancy_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Numéro de grossesse"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ongoing',
        verbose_name="Statut"
    )
    last_menstrual_period = models.DateField(verbose_name="Date des dernières règles (DDR)")
    expected_delivery_date = models.DateField(verbose_name="Date prévue d'accouchement (DPA)")
    actual_delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date réelle d'accouchement"
    )
    weeks_of_gestation = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        verbose_name="Semaines d'aménorrhée (SA)"
    )
    risk_factors = models.TextField(
        blank=True,
        default='',
        verbose_name="Facteurs de risque"
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name="Notes"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'pregnancies'
        verbose_name = "Grossesse"
        verbose_name_plural = "Grossesses"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['maternity_patient', '-created_at']),
            models.Index(fields=['doctor', '-created_at']),
        ]

    def __str__(self):
        return f"Grossesse #{self.pregnancy_number} - {self.maternity_patient.patient.full_name}"


class WeeklyCheckup(models.Model):
    """
    Consultation hebdomadaire de suivi de grossesse.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pregnancy = models.ForeignKey(
        Pregnancy,
        on_delete=models.CASCADE,
        related_name='weekly_checkups',
        verbose_name="Grossesse"
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='weekly_checkups_conducted',
        verbose_name="Médecin"
    )
    checkup_date = models.DateTimeField(verbose_name="Date de la consultation")
    week_number = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        verbose_name="Semaine de grossesse"
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Poids (kg)"
    )
    blood_pressure_systolic = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Pression artérielle systolique"
    )
    blood_pressure_diastolic = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Pression artérielle diastolique"
    )
    uterine_height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Hauteur utérine (cm)"
    )
    fetal_heart_rate = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Fréquence cardiaque fœtale (bpm)"
    )
    complaints = models.TextField(
        blank=True,
        default='',
        verbose_name="Plaintes"
    )
    observations = models.TextField(
        blank=True,
        default='',
        verbose_name="Observations"
    )
    recommendations = models.TextField(
        blank=True,
        default='',
        verbose_name="Recommandations"
    )
    next_appointment = models.DateField(
        null=True,
        blank=True,
        verbose_name="Prochain rendez-vous"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'weekly_checkups'
        verbose_name = "Consultation Hebdomadaire"
        verbose_name_plural = "Consultations Hebdomadaires"
        ordering = ['-checkup_date']
        indexes = [
            models.Index(fields=['pregnancy', '-checkup_date']),
        ]

    def __str__(self):
        return f"Semaine {self.week_number} - {self.pregnancy}"


class PrenatalConsultation(models.Model):
    """
    Consultation prénatale complète (CPN).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pregnancy = models.ForeignKey(
        Pregnancy,
        on_delete=models.CASCADE,
        related_name='prenatal_consultations',
        verbose_name="Grossesse"
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prenatal_consultations_conducted',
        verbose_name="Médecin"
    )
    consultation_date = models.DateTimeField(verbose_name="Date de consultation")
    consultation_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Numéro de CPN"
    )
    week_of_gestation = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        verbose_name="Semaine d'aménorrhée"
    )

    # Constantes vitales
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Poids (kg)"
    )
    blood_pressure_systolic = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Pression artérielle systolique"
    )
    blood_pressure_diastolic = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Pression artérielle diastolique"
    )
    temperature = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="Température (°C)"
    )

    # Examen clinique
    uterine_height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Hauteur utérine (cm)"
    )
    fetal_heart_rate = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Fréquence cardiaque fœtale (bpm)"
    )
    fetal_presentation = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Présentation fœtale"
    )
    edema = models.BooleanField(default=False, verbose_name="Œdèmes")

    # Plaintes et observations
    complaints = models.TextField(
        blank=True,
        default='',
        verbose_name="Plaintes"
    )
    clinical_findings = models.TextField(
        blank=True,
        default='',
        verbose_name="Constatations cliniques"
    )
    diagnosis = models.TextField(
        blank=True,
        default='',
        verbose_name="Diagnostic"
    )
    treatment = models.TextField(
        blank=True,
        default='',
        verbose_name="Traitement"
    )
    recommendations = models.TextField(
        blank=True,
        default='',
        verbose_name="Recommandations"
    )
    next_appointment = models.DateField(
        null=True,
        blank=True,
        verbose_name="Prochain rendez-vous"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'prenatal_consultations'
        verbose_name = "Consultation Prénatale (CPN)"
        verbose_name_plural = "Consultations Prénatales (CPN)"
        ordering = ['-consultation_date']
        indexes = [
            models.Index(fields=['pregnancy', '-consultation_date']),
        ]

    def __str__(self):
        return f"CPN {self.consultation_number} - {self.pregnancy}"


class PrenatalExam(models.Model):
    """
    Examen prénatal (échographie, analyses, etc.).
    """
    EXAM_TYPE_CHOICES = [
        ('ultrasound', 'Échographie'),
        ('blood_test', 'Analyse de sang'),
        ('urine_test', 'Analyse d\'urine'),
        ('glucose_test', 'Test de glycémie'),
        ('other', 'Autre'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pregnancy = models.ForeignKey(
        Pregnancy,
        on_delete=models.CASCADE,
        related_name='prenatal_exams',
        verbose_name="Grossesse"
    )
    prenatal_consultation = models.ForeignKey(
        PrenatalConsultation,
        on_delete=models.CASCADE,
        related_name='exams',
        null=True,
        blank=True,
        verbose_name="Consultation prénatale"
    )
    exam_name = models.CharField(max_length=200, verbose_name="Nom de l'examen")
    exam_type = models.CharField(
        max_length=50,
        choices=EXAM_TYPE_CHOICES,
        verbose_name="Type d'examen"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    ordered_date = models.DateTimeField(auto_now_add=True, verbose_name="Date de prescription")
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de réalisation"
    )
    results = models.TextField(
        blank=True,
        default='',
        verbose_name="Résultats"
    )
    interpretation = models.TextField(
        blank=True,
        default='',
        verbose_name="Interprétation"
    )
    attachments = models.FileField(
        upload_to='prenatal_exams/',
        null=True,
        blank=True,
        verbose_name="Pièces jointes"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'prenatal_exams'
        verbose_name = "Examen Prénatal"
        verbose_name_plural = "Examens Prénatals"
        ordering = ['-ordered_date']

    def __str__(self):
        return f"{self.exam_name} - {self.pregnancy}"


class Child(models.Model):
    """
    Enfant né d'une grossesse.
    """
    GENDER_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pregnancy = models.ForeignKey(
        Pregnancy,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name="Grossesse"
    )
    patient = models.OneToOneField(
        Patient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='birth_record',
        verbose_name="Dossier patient (si créé)"
    )
    first_name = models.CharField(max_length=150, verbose_name="Prénom")
    last_name = models.CharField(max_length=150, verbose_name="Nom")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Sexe")
    birth_date = models.DateTimeField(verbose_name="Date de naissance")
    birth_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Poids à la naissance (kg)"
    )
    birth_height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Taille à la naissance (cm)"
    )
    head_circumference = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Périmètre crânien (cm)"
    )
    apgar_score_1min = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="Score APGAR (1 min)"
    )
    apgar_score_5min = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name="Score APGAR (5 min)"
    )
    complications = models.TextField(
        blank=True,
        default='',
        verbose_name="Complications"
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name="Notes"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'children'
        verbose_name = "Enfant"
        verbose_name_plural = "Enfants"
        ordering = ['-birth_date']
        indexes = [
            models.Index(fields=['pregnancy', '-birth_date']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        """Retourne le nom complet de l'enfant."""
        return f"{self.first_name} {self.last_name}"


class ChildGrowth(models.Model):
    """
    Suivi de croissance de l'enfant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name='growth_records',
        verbose_name="Enfant"
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='child_growth_checkups',
        verbose_name="Médecin"
    )
    checkup_date = models.DateTimeField(verbose_name="Date de consultation")
    age_in_months = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Âge (en mois)"
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Poids (kg)"
    )
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Taille (cm)"
    )
    head_circumference = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Périmètre crânien (cm)"
    )
    nutritional_status = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="État nutritionnel"
    )
    developmental_milestones = models.TextField(
        blank=True,
        default='',
        verbose_name="Étapes de développement"
    )
    observations = models.TextField(
        blank=True,
        default='',
        verbose_name="Observations"
    )
    recommendations = models.TextField(
        blank=True,
        default='',
        verbose_name="Recommandations"
    )
    next_appointment = models.DateField(
        null=True,
        blank=True,
        verbose_name="Prochain rendez-vous"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'child_growth_records'
        verbose_name = "Suivi de Croissance"
        verbose_name_plural = "Suivis de Croissance"
        ordering = ['-checkup_date']
        indexes = [
            models.Index(fields=['child', '-checkup_date']),
        ]

    def __str__(self):
        return f"Croissance - {self.child.full_name} ({self.age_in_months} mois)"


class ChildVaccine(models.Model):
    """
    Vaccination d'un enfant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name='vaccines',
        verbose_name="Enfant"
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='child_vaccines_administered',
        verbose_name="Médecin"
    )
    vaccine_name = models.CharField(max_length=200, verbose_name="Nom du vaccin")
    vaccine_type = models.CharField(max_length=100, verbose_name="Type de vaccin")
    dose_number = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Numéro de dose"
    )
    date_administered = models.DateField(verbose_name="Date d'administration")
    next_dose_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de la prochaine dose"
    )
    batch_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Numéro de lot"
    )
    manufacturer = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name="Fabricant"
    )
    site = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Site d'injection"
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name="Notes"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'child_vaccines'
        verbose_name = "Vaccin Enfant"
        verbose_name_plural = "Vaccins Enfant"
        ordering = ['-date_administered']
        indexes = [
            models.Index(fields=['child', '-date_administered']),
        ]

    def __str__(self):
        return f"{self.vaccine_name} - {self.child.full_name}"
