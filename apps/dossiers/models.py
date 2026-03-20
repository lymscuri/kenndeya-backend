"""
Modèles pour l'application dossiers.
Gère les dossiers médicaux, consultations, prescriptions, examens et vaccinations.
"""

import uuid
from django.db import models
from django.conf import settings
from core.utils import generate_qr_code, generate_unique_code, calculate_age


class Patient(models.Model):
    """
    Modèle Patient.
    Représente un patient suivi par un médecin/soignant.
    """
    GENDER_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
        ('O', 'Autre'),
    ]

    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patients',
        verbose_name='Médecin/Soignant'
    )

    # Informations personnelles
    first_name = models.CharField('Prénom', max_length=150)
    last_name = models.CharField('Nom', max_length=150)
    date_of_birth = models.DateField('Date de naissance')
    gender = models.CharField('Sexe', max_length=1, choices=GENDER_CHOICES)
    phone = models.CharField('Téléphone', max_length=20, blank=True, default='')
    email = models.EmailField('Email', blank=True, default='')

    # Informations médicales
    blood_type = models.CharField(
        'Groupe sanguin',
        max_length=3,
        choices=BLOOD_TYPE_CHOICES,
        blank=True,
        default=''
    )
    allergies = models.TextField('Allergies', blank=True, default='')
    chronic_conditions = models.TextField('Maladies chroniques', blank=True, default='')

    # Antécédents et habitudes
    personal_history = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Antécédents personnels"
    )
    family_history = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Antécédents familiaux"
    )
    life_habits = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Habitudes de vie"
    )
    critical_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Informations critiques"
    )
    permanent_treatments = models.TextField(
        blank=True,
        default='',
        verbose_name="Traitements permanents"
    )

    # Adresse
    address = models.TextField('Adresse', blank=True, default='')
    city = models.CharField('Ville', max_length=100, blank=True, default='')
    prefecture = models.CharField('Préfecture', max_length=100, blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)

    class Meta:
        db_table = 'patients'
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['doctor', '-created_at']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        """Retourne le nom complet du patient."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        """Calcule l'âge du patient."""
        return calculate_age(self.date_of_birth)


class MedicalRecord(models.Model):
    """
    Modèle Dossier Médical.
    Chaque patient a un dossier médical unique avec un QR code.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_record',
        verbose_name='Patient'
    )

    record_number = models.CharField(
        'Numéro de dossier',
        max_length=50,
        unique=True,
        editable=False
    )
    qr_code = models.ImageField(
        'QR Code',
        upload_to='qr_codes/',
        blank=True,
        null=True
    )

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)

    class Meta:
        db_table = 'medical_records'
        verbose_name = 'Dossier Médical'
        verbose_name_plural = 'Dossiers Médicaux'
        ordering = ['-created_at']

    def __str__(self):
        return f"Dossier #{self.record_number} - {self.patient.full_name}"

    def save(self, *args, **kwargs):
        """Génère le numéro de dossier et le QR code à la création."""
        if not self.record_number:
            self.record_number = generate_unique_code('DME')

        # Sauvegarder d'abord pour avoir l'ID
        super().save(*args, **kwargs)

        # Générer le QR code s'il n'existe pas
        if not self.qr_code:
            qr_data = f"DME-{self.record_number}-{self.patient.id}"
            self.qr_code = generate_qr_code(qr_data)
            super().save(update_fields=['qr_code'])


class Consultation(models.Model):
    """
    Modèle Consultation.
    Représente une consultation médicale.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='consultations',
        verbose_name='Patient'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consultations',
        verbose_name='Médecin'
    )

    date = models.DateTimeField('Date de consultation')
    reason = models.TextField('Motif de consultation')
    symptoms = models.TextField('Symptômes', blank=True, default='')
    diagnosis = models.TextField('Diagnostic', blank=True, default='')
    treatment = models.TextField('Traitement', blank=True, default='')
    notes = models.TextField('Notes', blank=True, default='')

    # Constantes vitales
    temperature = models.DecimalField(
        'Température (°C)',
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True
    )
    blood_pressure_systolic = models.IntegerField(
        'Pression artérielle systolique',
        null=True,
        blank=True
    )
    blood_pressure_diastolic = models.IntegerField(
        'Pression artérielle diastolique',
        null=True,
        blank=True
    )
    heart_rate = models.IntegerField(
        'Fréquence cardiaque (bpm)',
        null=True,
        blank=True
    )
    weight = models.DecimalField(
        'Poids (kg)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    height = models.DecimalField(
        'Taille (cm)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)

    class Meta:
        db_table = 'consultations'
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['patient', '-date']),
            models.Index(fields=['doctor', '-date']),
        ]

    def __str__(self):
        return f"Consultation - {self.patient.full_name} - {self.date.strftime('%d/%m/%Y')}"


class Prescription(models.Model):
    """
    Modèle Ordonnance.
    Représente une ordonnance médicale.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name='Consultation'
    )

    medication_name = models.CharField('Nom du médicament', max_length=200)
    dosage = models.CharField('Posologie', max_length=100)
    frequency = models.CharField('Fréquence', max_length=100)
    duration = models.CharField('Durée', max_length=100)
    instructions = models.TextField('Instructions', blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)

    class Meta:
        db_table = 'prescriptions'
        verbose_name = 'Ordonnance'
        verbose_name_plural = 'Ordonnances'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.medication_name} - {self.consultation.patient.full_name}"


class LabTest(models.Model):
    """
    Modèle Examen de Laboratoire.
    Représente un examen médical de laboratoire.
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='lab_tests',
        verbose_name='Consultation',
        null=True,
        blank=True
    )

    test_name = models.CharField('Nom de l\'examen', max_length=200)
    test_type = models.CharField('Type d\'examen', max_length=100)
    status = models.CharField(
        'Statut',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    ordered_date = models.DateTimeField('Date de prescription', auto_now_add=True)
    completed_date = models.DateTimeField('Date de réalisation', null=True, blank=True)

    results = models.TextField('Résultats', blank=True, default='')
    interpretation = models.TextField('Interprétation', blank=True, default='')
    attachments = models.FileField(
        'Pièces jointes',
        upload_to='lab_tests/',
        null=True,
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)

    class Meta:
        db_table = 'lab_tests'
        verbose_name = 'Examen de Laboratoire'
        verbose_name_plural = 'Examens de Laboratoire'
        ordering = ['-ordered_date']

    def __str__(self):
        return f"{self.test_name} - {self.consultation.patient.full_name}"


class Vaccination(models.Model):
    """
    Modèle Vaccination.
    Représente une vaccination administrée à un patient.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='vaccinations',
        verbose_name='Patient'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vaccinations_administered',
        verbose_name='Médecin'
    )

    vaccine_name = models.CharField('Nom du vaccin', max_length=200)
    vaccine_type = models.CharField('Type de vaccin', max_length=100)
    dose_number = models.IntegerField('Numéro de dose', default=1)

    date_administered = models.DateField('Date d\'administration')
    next_dose_date = models.DateField('Date de la prochaine dose', null=True, blank=True)

    batch_number = models.CharField('Numéro de lot', max_length=100, blank=True, default='')
    manufacturer = models.CharField('Fabricant', max_length=200, blank=True, default='')
    site = models.CharField('Site d\'injection', max_length=100, blank=True, default='')
    notes = models.TextField('Notes', blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)

    class Meta:
        db_table = 'vaccinations'
        verbose_name = 'Vaccination'
        verbose_name_plural = 'Vaccinations'
        ordering = ['-date_administered']
        indexes = [
            models.Index(fields=['patient', '-date_administered']),
        ]

    def __str__(self):
        return f"{self.vaccine_name} - {self.patient.full_name} - Dose {self.dose_number}"


class Chirurgie(models.Model):
    """
    Modèle Chirurgie.
    Représente une opération chirurgicale subie par un patient.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='surgeries',
        verbose_name='Patient'
    )

    nom = models.CharField('Nom de la chirurgie', max_length=200)
    date = models.DateField('Date de la chirurgie', null=True, blank=True)
    hopital = models.CharField('Hôpital', max_length=200, blank=True, default='')
    notes = models.TextField('Notes', blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)

    class Meta:
        db_table = 'chirurgies'
        verbose_name = 'Chirurgie'
        verbose_name_plural = 'Chirurgies'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['patient', '-date']),
        ]

    def __str__(self):
        return f"{self.nom} - {self.patient.full_name}"


class Hospitalisation(models.Model):
    """
    Modèle Hospitalisation.
    Représente une hospitalisation d'un patient.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='hospitalisations',
        verbose_name='Patient'
    )

    motif = models.CharField('Motif de l\'hospitalisation', max_length=200)
    date_entree = models.DateField('Date d\'entrée', null=True, blank=True)
    date_sortie = models.DateField('Date de sortie', null=True, blank=True)
    hopital = models.CharField('Hôpital', max_length=200, blank=True, default='')
    notes = models.TextField('Notes', blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)

    class Meta:
        db_table = 'hospitalisations'
        verbose_name = 'Hospitalisation'
        verbose_name_plural = 'Hospitalisations'
        ordering = ['-date_entree']
        indexes = [
            models.Index(fields=['patient', '-date_entree']),
        ]

    def __str__(self):
        return f"{self.motif} - {self.patient.full_name}"
