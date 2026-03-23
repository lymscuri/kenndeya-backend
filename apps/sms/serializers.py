from rest_framework import serializers
from .models import SMSReminder

class SMSReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSReminder
        fields = [
            'id', 'patient_phone', 'patient_name', 'reminder_type',
            'message', 'scheduled_at', 'sent_at', 'status',
            'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'sent_at', 'status', 'error_message', 'created_at']

class CreateSMSReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSReminder
        fields = [
            'patient_phone', 'patient_name', 'reminder_type',
            'message', 'scheduled_at'
        ]
