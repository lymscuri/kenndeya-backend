"""
Configuration de l'admin Django pour l'application dossiers.
"""

from django.contrib import admin
from .models import Patient, MedicalRecord, Consultation, Prescription, LabTest, Vaccination


# ========== INLINES ==========

class ConsultationInline(admin.TabularInline):
    """Inline pour afficher les consultations d'un patient."""
    model = Consultation
    extra = 0
    fields = ('date', 'reason', 'diagnosis', 'doctor')
    readonly_fields = ('date', 'doctor')
    show_change_link = True
    can_delete = False


class VaccinationInline(admin.TabularInline):
    """Inline pour afficher les vaccinations d'un patient."""
    model = Vaccination
    extra = 0
    fields = ('vaccine_name', 'dose_number', 'date_administered', 'doctor')
    readonly_fields = ('doctor',)
    show_change_link = True


class PrescriptionInline(admin.TabularInline):
    """Inline pour afficher les prescriptions d'une consultation."""
    model = Prescription
    extra = 0
    fields = ('medication_name', 'dosage', 'frequency', 'duration')


class LabTestInline(admin.TabularInline):
    """Inline pour afficher les examens d'une consultation."""
    model = LabTest
    extra = 0
    fields = ('test_name', 'test_type', 'status', 'ordered_date')
    readonly_fields = ('ordered_date',)
    show_change_link = True


# ========== ADMIN CLASSES ==========

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle Patient."""

    list_display = (
        'full_name', 'date_of_birth', 'age', 'gender',
        'phone', 'doctor', 'created_at'
    )
    list_filter = ('gender', 'blood_type', 'created_at', 'doctor')
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    ordering = ('-created_at',)
    readonly_fields = ('age', 'created_at', 'updated_at')

    fieldsets = (
        ('Médecin', {
            'fields': ('doctor',)
        }),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'age', 'gender', 'phone', 'email')
        }),
        ('Informations médicales', {
            'fields': ('blood_type', 'allergies', 'chronic_conditions')
        }),
        ('Adresse', {
            'fields': ('address', 'city')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ConsultationInline, VaccinationInline]
    list_per_page = 25

    def full_name(self, obj):
        """Affiche le nom complet dans la liste."""
        return obj.full_name
    full_name.short_description = 'Nom complet'


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle MedicalRecord."""

    list_display = ('record_number', 'patient', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('record_number', 'patient__first_name', 'patient__last_name')
    readonly_fields = ('record_number', 'qr_code', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {
            'fields': ('patient', 'record_number')
        }),
        ('QR Code', {
            'fields': ('qr_code',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle Consultation."""

    list_display = (
        'patient', 'doctor', 'date', 'reason', 'diagnosis', 'created_at'
    )
    list_filter = ('date', 'doctor', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name', 'reason', 'diagnosis')
    ordering = ('-date',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Patient et Médecin', {
            'fields': ('patient', 'doctor', 'date')
        }),
        ('Consultation', {
            'fields': ('reason', 'symptoms', 'diagnosis', 'treatment', 'notes')
        }),
        ('Constantes vitales', {
            'fields': (
                'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
                'heart_rate', 'weight', 'height'
            ),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [PrescriptionInline, LabTestInline]
    list_per_page = 25


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle Prescription."""

    list_display = (
        'medication_name', 'get_patient_name', 'dosage',
        'frequency', 'duration', 'created_at'
    )
    list_filter = ('created_at',)
    search_fields = ('medication_name', 'consultation__patient__first_name', 'consultation__patient__last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Consultation', {
            'fields': ('consultation',)
        }),
        ('Médicament', {
            'fields': ('medication_name', 'dosage', 'frequency', 'duration', 'instructions')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25

    def get_patient_name(self, obj):
        """Affiche le nom du patient."""
        return obj.consultation.patient.full_name
    get_patient_name.short_description = 'Patient'


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle LabTest."""

    list_display = (
        'test_name', 'get_patient_name', 'test_type',
        'status', 'ordered_date', 'completed_date'
    )
    list_filter = ('status', 'test_type', 'ordered_date')
    search_fields = ('test_name', 'consultation__patient__first_name', 'consultation__patient__last_name')
    ordering = ('-ordered_date',)
    readonly_fields = ('ordered_date', 'created_at', 'updated_at')

    fieldsets = (
        ('Consultation', {
            'fields': ('consultation',)
        }),
        ('Examen', {
            'fields': ('test_name', 'test_type', 'status')
        }),
        ('Dates', {
            'fields': ('ordered_date', 'completed_date')
        }),
        ('Résultats', {
            'fields': ('results', 'interpretation', 'attachments')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25

    def get_patient_name(self, obj):
        """Affiche le nom du patient."""
        return obj.consultation.patient.full_name
    get_patient_name.short_description = 'Patient'


@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle Vaccination."""

    list_display = (
        'vaccine_name', 'patient', 'dose_number',
        'date_administered', 'next_dose_date', 'doctor'
    )
    list_filter = ('vaccine_type', 'date_administered', 'doctor')
    search_fields = ('vaccine_name', 'patient__first_name', 'patient__last_name')
    ordering = ('-date_administered',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Patient et Médecin', {
            'fields': ('patient', 'doctor')
        }),
        ('Vaccin', {
            'fields': ('vaccine_name', 'vaccine_type', 'dose_number')
        }),
        ('Dates', {
            'fields': ('date_administered', 'next_dose_date')
        }),
        ('Détails', {
            'fields': ('batch_number', 'manufacturer', 'site', 'notes'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25
