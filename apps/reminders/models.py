"""
Modèles pour l'application reminders.
Gère les rappels SMS automatiques pour les patients.
"""

import uuid
from django.db import models
from apps.accounts.models import User


class SmsReminder(models.Model):
    """
    Rappel SMS programmé pour un patient.
    """
    REMINDER_TYPE_CHOICES = [
        ('appointment', 'Rendez-vous'),
        ('medication', 'Prise de médicament'),
        ('vaccination', 'Vaccination'),
        ('prenatal', 'Consultation prénatale'),
        ('custom', 'Personnalisé'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
        ('failed', 'Échec'),
        ('cancelled', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sms_reminders',
        verbose_name="Patient"
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_sms_reminders',
        null=True,
        blank=True,
        verbose_name="Médecin"
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPE_CHOICES,
        verbose_name="Type de rappel"
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="Numéro de téléphone"
    )
    message = models.TextField(verbose_name="Message")
    scheduled_at = models.DateTimeField(verbose_name="Date d'envoi prévue")
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'envoi réelle"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    error_message = models.TextField(
        blank=True,
        default='',
        verbose_name="Message d'erreur"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        db_table = 'sms_reminders'
        verbose_name = "Rappel SMS"
        verbose_name_plural = "Rappels SMS"
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['patient', '-scheduled_at']),
        ]

    def __str__(self):
        return f"SMS {self.reminder_type} pour {self.patient.get_full_name()} - {self.scheduled_at}"
