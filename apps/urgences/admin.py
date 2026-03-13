"""
Configuration de l'admin Django pour l'application urgences.
"""

from django.contrib import admin
from .models import Secourist, Hospital, EmergencyAlert


@admin.register(Secourist)
class SecouristAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle Secourist."""

    list_display = (
        'get_user_name', 'get_user_email', 'specialization',
        'is_available', 'license_number', 'created_at'
    )
    list_filter = ('is_available', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'specialization')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Informations professionnelles', {
            'fields': ('specialization', 'license_number', 'is_available')
        }),
        ('Localisation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25

    def get_user_name(self, obj):
        """Affiche le nom de l'utilisateur."""
        return obj.user.get_full_name()
    get_user_name.short_description = 'Nom'

    def get_user_email(self, obj):
        """Affiche l'email de l'utilisateur."""
        return obj.user.email
    get_user_email.short_description = 'Email'


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle Hospital."""

    list_display = (
        'name', 'city', 'hospital_type', 'capacity',
        'has_emergency_room', 'has_maternity', 'is_active', 'created_at'
    )
    list_filter = ('hospital_type', 'has_emergency_room', 'has_maternity', 'is_active', 'city', 'created_at')
    search_fields = ('name', 'city', 'address')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'hospital_type', 'capacity', 'is_active')
        }),
        ('Contact', {
            'fields': ('phone', 'email')
        }),
        ('Adresse', {
            'fields': ('address', 'city')
        }),
        ('Services', {
            'fields': ('has_emergency_room', 'has_maternity')
        }),
        ('Localisation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25


@admin.register(EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle EmergencyAlert."""

    list_display = (
        'id', 'get_patient_name', 'get_secourist_name', 'status',
        'priority', 'emergency_type', 'created_at'
    )
    list_filter = ('status', 'priority', 'created_at')
    search_fields = (
        'patient__first_name', 'patient__last_name',
        'secourist__user__first_name', 'secourist__user__last_name',
        'emergency_type'
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'assigned_at', 'resolved_at')

    fieldsets = (
        ('Patient et Secouriste', {
            'fields': ('patient', 'secourist', 'hospital')
        }),
        ('Statut', {
            'fields': ('status', 'priority', 'emergency_type')
        }),
        ('Description', {
            'fields': ('description', 'symptoms')
        }),
        ('Localisation du patient', {
            'fields': ('patient_latitude', 'patient_longitude', 'patient_address')
        }),
        ('Notes', {
            'fields': ('notes', 'resolution_notes')
        }),
        ('Dates', {
            'fields': ('created_at', 'assigned_at', 'resolved_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25

    def get_patient_name(self, obj):
        """Affiche le nom du patient."""
        return obj.patient.get_full_name()
    get_patient_name.short_description = 'Patient'

    def get_secourist_name(self, obj):
        """Affiche le nom du secouriste."""
        if obj.secourist:
            return obj.secourist.user.get_full_name()
        return '-'
    get_secourist_name.short_description = 'Secouriste'
