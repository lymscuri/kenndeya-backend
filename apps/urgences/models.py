"""
Modèles pour l'application urgences.
Gère les alertes d'urgence, secouristes et hôpitaux.
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User


class Secourist(models.Model):
    """
    Secouriste (utilisateur avec rôle 'secourist').
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='secourist_profile',
        verbose_name="Utilisateur"
    )
    specialization = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name="Spécialisation"
    )
    license_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Numéro de licence"
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name="Disponible"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Latitude"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Longitude"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'secourists'
        verbose_name = "Secouriste"
        verbose_name_plural = "Secouristes"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.specialization}"


class Hospital(models.Model):
    """
    Hôpital ou centre de santé.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nom de l'hôpital")
    address = models.TextField(verbose_name="Adresse")
    city = models.CharField(max_length=100, verbose_name="Ville")
    phone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name="Téléphone"
    )
    email = models.EmailField(
        blank=True,
        default='',
        verbose_name="Email"
    )
    hospital_type = models.CharField(
        max_length=100,
        choices=[
            ('public', 'Public'),
            ('private', 'Privé'),
            ('clinic', 'Clinique'),
            ('health_center', 'Centre de santé'),
        ],
        default='public',
        verbose_name="Type d'établissement"
    )
    capacity = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Capacité d'accueil"
    )
    has_emergency_room = models.BooleanField(
        default=True,
        verbose_name="Service d'urgence"
    )
    has_maternity = models.BooleanField(
        default=False,
        verbose_name="Service de maternité"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Latitude"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Longitude"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'hospitals'
        verbose_name = "Hôpital"
        verbose_name_plural = "Hôpitaux"
        ordering = ['name']
        indexes = [
            models.Index(fields=['city', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"


class EmergencyAlert(models.Model):
    """
    Alerte d'urgence médicale.
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('assigned', 'Assignée'),
        ('in_progress', 'En cours'),
        ('resolved', 'Résolue'),
        ('cancelled', 'Annulée'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('critical', 'Critique'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='emergency_alerts',
        verbose_name="Patient"
    )
    secourist = models.ForeignKey(
        Secourist,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_alerts',
        verbose_name="Secouriste assigné"
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emergency_alerts',
        verbose_name="Hôpital recommandé"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name="Priorité"
    )
    emergency_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Type d'urgence"
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name="Description"
    )
    symptoms = models.TextField(
        blank=True,
        default='',
        verbose_name="Symptômes"
    )
    patient_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Latitude du patient"
    )
    patient_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="Longitude du patient"
    )
    patient_address = models.TextField(
        blank=True,
        default='',
        verbose_name="Adresse du patient"
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name="Notes"
    )
    resolution_notes = models.TextField(
        blank=True,
        default='',
        verbose_name="Notes de résolution"
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'assignation"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de résolution"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'emergency_alerts'
        verbose_name = "Alerte d'Urgence"
        verbose_name_plural = "Alertes d'Urgence"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['secourist', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
        ]

    def __str__(self):
        return f"Alerte #{self.id} - {self.patient.get_full_name()} ({self.status})"
