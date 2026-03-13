"""
Serializers pour l'application reminders.
Gère la sérialisation des rappels SMS.
"""

from rest_framework import serializers
from .models import SmsReminder


class SmsReminderSerializer(serializers.ModelSerializer):
    """
    Serializer pour les rappels SMS.
    """
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = SmsReminder
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'reminder_type', 'phone_number', 'message', 'scheduled_at',
            'sent_at', 'status', 'error_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'patient', 'doctor', 'sent_at', 'status', 'created_at', 'updated_at']

    def validate_scheduled_at(self, value):
        """Valide que la date d'envoi n'est pas dans le passé."""
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError(
                "La date d'envoi prévue ne peut pas être dans le passé."
            )
        return value
