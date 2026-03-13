"""
Configuration de l'admin Django pour l'application reminders.
"""

from django.contrib import admin
from .models import SmsReminder


@admin.register(SmsReminder)
class SmsReminderAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle SmsReminder."""

    list_display = (
        'get_patient_name', 'get_doctor_name', 'reminder_type',
        'phone_number', 'scheduled_at', 'status', 'created_at'
    )
    list_filter = ('status', 'reminder_type', 'scheduled_at', 'created_at')
    search_fields = (
        'patient__first_name', 'patient__last_name',
        'doctor__first_name', 'doctor__last_name',
        'phone_number', 'message'
    )
    ordering = ('-scheduled_at',)
    readonly_fields = ('sent_at', 'created_at', 'updated_at')

    fieldsets = (
        ('Patient et Médecin', {
            'fields': ('patient', 'doctor')
        }),
        ('Rappel', {
            'fields': ('reminder_type', 'phone_number', 'message', 'scheduled_at')
        }),
        ('Statut', {
            'fields': ('status', 'sent_at', 'error_message')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25

    def get_patient_name(self, obj):
        """Affiche le nom du patient."""
        return obj.patient.get_full_name()
    get_patient_name.short_description = 'Patient'

    def get_doctor_name(self, obj):
        """Affiche le nom du médecin."""
        if obj.doctor:
            return obj.doctor.get_full_name()
        return '-'
    get_doctor_name.short_description = 'Médecin'
