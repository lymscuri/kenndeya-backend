from django.db import models
import uuid

class SMSReminder(models.Model):
    TYPE_CHOICES = [
        ('vaccination', 'Rappel vaccination'),
        ('consultation', 'Rappel consultation'),
        ('prenatal', 'Consultation prénatale'),
        ('urgence', 'Alerte urgence maternité'),
    ]
    STATUS_CHOICES = [
        ('planifie', 'Planifié'),
        ('envoye', 'Envoyé'),
        ('echec', 'Échec'),
        ('annule', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    doctor = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='scheduled_sms'
    )
    patient_phone = models.CharField(max_length=20)
    patient_name = models.CharField(max_length=200)
    reminder_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planifie')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_at']
        db_table = 'sms_reminder'
        verbose_name = 'Rappel SMS'
        verbose_name_plural = 'Rappels SMS'

    def __str__(self):
        return f"{self.reminder_type} → {self.patient_name} ({self.scheduled_at})"
