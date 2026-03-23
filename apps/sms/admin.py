from django.contrib import admin
from .models import SMSReminder


@admin.register(SMSReminder)
class SMSReminderAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'patient_phone', 'reminder_type', 'status', 'scheduled_at', 'sent_at', 'doctor']
    list_filter = ['status', 'reminder_type', 'scheduled_at']
    search_fields = ['patient_name', 'patient_phone', 'message']
    readonly_fields = ['id', 'created_at', 'updated_at', 'sent_at']
    ordering = ['-scheduled_at']
    date_hierarchy = 'scheduled_at'

    fieldsets = (
        ('Informations patient', {
            'fields': ('patient_name', 'patient_phone')
        }),
        ('Rappel', {
            'fields': ('doctor', 'reminder_type', 'message', 'scheduled_at')
        }),
        ('Statut', {
            'fields': ('status', 'sent_at', 'error_message')
        }),
        ('Métadonnées', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
