"""
Configuration de l'admin Django pour l'application maternité.
"""

from django.contrib import admin
from .models import (
    MaternityPatient, Pregnancy, WeeklyCheckup,
    PrenatalConsultation, PrenatalExam, Child,
    ChildGrowth, ChildVaccine
)


# ========== INLINES ==========

class PregnancyInline(admin.TabularInline):
    """Inline pour afficher les grossesses d'une patiente."""
    model = Pregnancy
    extra = 0
    fields = ('pregnancy_number', 'status', 'last_menstrual_period', 'expected_delivery_date', 'doctor')
    readonly_fields = ('doctor',)
    show_change_link = True


class WeeklyCheckupInline(admin.TabularInline):
    """Inline pour afficher les consultations hebdomadaires d'une grossesse."""
    model = WeeklyCheckup
    extra = 0
    fields = ('checkup_date', 'week_number', 'weight', 'doctor')
    readonly_fields = ('doctor',)
    show_change_link = True
    can_delete = False


class PrenatalConsultationInline(admin.TabularInline):
    """Inline pour afficher les CPN d'une grossesse."""
    model = PrenatalConsultation
    extra = 0
    fields = ('consultation_date', 'consultation_number', 'week_of_gestation', 'doctor')
    readonly_fields = ('doctor',)
    show_change_link = True


class PrenatalExamInline(admin.TabularInline):
    """Inline pour afficher les examens prénatals d'une grossesse."""
    model = PrenatalExam
    extra = 0
    fields = ('exam_name', 'exam_type', 'status', 'ordered_date')
    readonly_fields = ('ordered_date',)
    show_change_link = True


class ChildInline(admin.TabularInline):
    """Inline pour afficher les enfants d'une grossesse."""
    model = Child
    extra = 0
    fields = ('first_name', 'last_name', 'gender', 'birth_date', 'birth_weight')
    show_change_link = True


class ChildGrowthInline(admin.TabularInline):
    """Inline pour afficher le suivi de croissance d'un enfant."""
    model = ChildGrowth
    extra = 0
    fields = ('checkup_date', 'age_in_months', 'weight', 'height', 'doctor')
    readonly_fields = ('doctor',)
    show_change_link = True


class ChildVaccineInline(admin.TabularInline):
    """Inline pour afficher les vaccins d'un enfant."""
    model = ChildVaccine
    extra = 0
    fields = ('vaccine_name', 'dose_number', 'date_administered', 'doctor')
    readonly_fields = ('doctor',)
    show_change_link = True


# ========== ADMIN CLASSES ==========

@admin.register(MaternityPatient)
class MaternityPatientAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle MaternityPatient."""

    list_display = (
        'get_patient_name', 'blood_rhesus', 'number_of_pregnancies',
        'number_of_deliveries', 'number_of_living_children', 'created_at'
    )
    list_filter = ('blood_rhesus', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Patient', {
            'fields': ('patient',)
        }),
        ('Informations obstétricales', {
            'fields': (
                'blood_rhesus', 'number_of_pregnancies',
                'number_of_deliveries', 'number_of_living_children'
            )
        }),
        ('Antécédents', {
            'fields': ('medical_history', 'obstetric_history')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [PregnancyInline]
    list_per_page = 25

    def get_patient_name(self, obj):
        """Affiche le nom de la patiente."""
        return obj.patient.full_name
    get_patient_name.short_description = 'Patiente'


@admin.register(Pregnancy)
class PregnancyAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle Pregnancy."""

    list_display = (
        'get_patient_name', 'pregnancy_number', 'status',
        'last_menstrual_period', 'expected_delivery_date',
        'weeks_of_gestation', 'doctor', 'created_at'
    )
    list_filter = ('status', 'doctor', 'created_at')
    search_fields = (
        'maternity_patient__patient__first_name',
        'maternity_patient__patient__last_name'
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Patiente et Médecin', {
            'fields': ('maternity_patient', 'doctor')
        }),
        ('Grossesse', {
            'fields': ('pregnancy_number', 'status', 'weeks_of_gestation')
        }),
        ('Dates', {
            'fields': (
                'last_menstrual_period', 'expected_delivery_date',
                'actual_delivery_date'
            )
        }),
        ('Informations cliniques', {
            'fields': ('risk_factors', 'notes'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [WeeklyCheckupInline, PrenatalConsultationInline, PrenatalExamInline, ChildInline]
    list_per_page = 25

    def get_patient_name(self, obj):
        """Affiche le nom de la patiente."""
        return obj.maternity_patient.patient.full_name
    get_patient_name.short_description = 'Patiente'


@admin.register(WeeklyCheckup)
class WeeklyCheckupAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle WeeklyCheckup."""

    list_display = (
        'get_patient_name', 'week_number', 'checkup_date',
        'weight', 'fetal_heart_rate', 'doctor', 'created_at'
    )
    list_filter = ('checkup_date', 'doctor', 'created_at')
    search_fields = (
        'pregnancy__maternity_patient__patient__first_name',
        'pregnancy__maternity_patient__patient__last_name'
    )
    ordering = ('-checkup_date',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Grossesse et Médecin', {
            'fields': ('pregnancy', 'doctor')
        }),
        ('Consultation', {
            'fields': ('checkup_date', 'week_number')
        }),
        ('Constantes vitales', {
            'fields': (
                'weight', 'blood_pressure_systolic', 'blood_pressure_diastolic',
                'uterine_height', 'fetal_heart_rate'
            )
        }),
        ('Observations', {
            'fields': ('complaints', 'observations', 'recommendations', 'next_appointment')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25

    def get_patient_name(self, obj):
        """Affiche le nom de la patiente."""
        return obj.pregnancy.maternity_patient.patient.full_name
    get_patient_name.short_description = 'Patiente'


@admin.register(PrenatalConsultation)
class PrenatalConsultationAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle PrenatalConsultation."""

    list_display = (
        'get_patient_name', 'consultation_number', 'consultation_date',
        'week_of_gestation', 'doctor', 'created_at'
    )
    list_filter = ('consultation_date', 'doctor', 'created_at')
    search_fields = (
        'pregnancy__maternity_patient__patient__first_name',
        'pregnancy__maternity_patient__patient__last_name'
    )
    ordering = ('-consultation_date',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Grossesse et Médecin', {
            'fields': ('pregnancy', 'doctor')
        }),
        ('Consultation', {
            'fields': ('consultation_date', 'consultation_number', 'week_of_gestation')
        }),
        ('Constantes vitales', {
            'fields': (
                'weight', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'temperature'
            )
        }),
        ('Examen clinique', {
            'fields': ('uterine_height', 'fetal_heart_rate', 'fetal_presentation', 'edema')
        }),
        ('Plaintes et diagnostic', {
            'fields': ('complaints', 'clinical_findings', 'diagnosis', 'treatment')
        }),
        ('Suivi', {
            'fields': ('recommendations', 'next_appointment')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [PrenatalExamInline]
    list_per_page = 25

    def get_patient_name(self, obj):
        """Affiche le nom de la patiente."""
        return obj.pregnancy.maternity_patient.patient.full_name
    get_patient_name.short_description = 'Patiente'


@admin.register(PrenatalExam)
class PrenatalExamAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle PrenatalExam."""

    list_display = (
        'exam_name', 'get_patient_name', 'exam_type',
        'status', 'ordered_date', 'completed_date'
    )
    list_filter = ('status', 'exam_type', 'ordered_date')
    search_fields = (
        'exam_name',
        'pregnancy__maternity_patient__patient__first_name',
        'pregnancy__maternity_patient__patient__last_name'
    )
    ordering = ('-ordered_date',)
    readonly_fields = ('ordered_date', 'created_at', 'updated_at')

    fieldsets = (
        ('Grossesse', {
            'fields': ('pregnancy', 'prenatal_consultation')
        }),
        ('Examen', {
            'fields': ('exam_name', 'exam_type', 'status')
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
        """Affiche le nom de la patiente."""
        return obj.pregnancy.maternity_patient.patient.full_name
    get_patient_name.short_description = 'Patiente'


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle Child."""

    list_display = (
        'full_name', 'get_mother_name', 'gender', 'birth_date',
        'birth_weight', 'birth_height', 'created_at'
    )
    list_filter = ('gender', 'birth_date', 'created_at')
    search_fields = ('first_name', 'last_name', 'pregnancy__maternity_patient__patient__first_name')
    ordering = ('-birth_date',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Grossesse', {
            'fields': ('pregnancy', 'patient')
        }),
        ('Identité', {
            'fields': ('first_name', 'last_name', 'gender', 'birth_date')
        }),
        ('Mensurations à la naissance', {
            'fields': ('birth_weight', 'birth_height', 'head_circumference')
        }),
        ('Score APGAR', {
            'fields': ('apgar_score_1min', 'apgar_score_5min')
        }),
        ('Notes', {
            'fields': ('complications', 'notes'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ChildGrowthInline, ChildVaccineInline]
    list_per_page = 25

    def get_mother_name(self, obj):
        """Affiche le nom de la mère."""
        return obj.pregnancy.maternity_patient.patient.full_name
    get_mother_name.short_description = 'Mère'


@admin.register(ChildGrowth)
class ChildGrowthAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle ChildGrowth."""

    list_display = (
        'get_child_name', 'age_in_months', 'checkup_date',
        'weight', 'height', 'doctor', 'created_at'
    )
    list_filter = ('checkup_date', 'doctor', 'created_at')
    search_fields = ('child__first_name', 'child__last_name')
    ordering = ('-checkup_date',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Enfant et Médecin', {
            'fields': ('child', 'doctor')
        }),
        ('Consultation', {
            'fields': ('checkup_date', 'age_in_months')
        }),
        ('Mensurations', {
            'fields': ('weight', 'height', 'head_circumference')
        }),
        ('État nutritionnel et développement', {
            'fields': ('nutritional_status', 'developmental_milestones')
        }),
        ('Suivi', {
            'fields': ('observations', 'recommendations', 'next_appointment')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    list_per_page = 25

    def get_child_name(self, obj):
        """Affiche le nom de l'enfant."""
        return obj.child.full_name
    get_child_name.short_description = 'Enfant'


@admin.register(ChildVaccine)
class ChildVaccineAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour le modèle ChildVaccine."""

    list_display = (
        'vaccine_name', 'get_child_name', 'dose_number',
        'date_administered', 'next_dose_date', 'doctor'
    )
    list_filter = ('vaccine_type', 'date_administered', 'doctor')
    search_fields = ('vaccine_name', 'child__first_name', 'child__last_name')
    ordering = ('-date_administered',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Enfant et Médecin', {
            'fields': ('child', 'doctor')
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

    def get_child_name(self, obj):
        """Affiche le nom de l'enfant."""
        return obj.child.full_name
    get_child_name.short_description = 'Enfant'
