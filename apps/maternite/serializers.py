"""
Serializers pour l'application maternité.
Gère la sérialisation des données de maternité et grossesse.
"""

from rest_framework import serializers
from .models import (
    MaternityPatient, Pregnancy, WeeklyCheckup,
    PrenatalConsultation, PrenatalExam, Child,
    ChildGrowth, ChildVaccine
)


class MaternityPatientSerializer(serializers.ModelSerializer):
    """
    Serializer pour les patientes de maternité.
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_id = serializers.UUIDField(source='patient.id', read_only=True)

    class Meta:
        model = MaternityPatient
        fields = [
            'id', 'patient', 'patient_id', 'patient_name',
            'blood_rhesus', 'number_of_pregnancies', 'number_of_deliveries',
            'number_of_living_children', 'medical_history', 'obstetric_history',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PregnancySerializer(serializers.ModelSerializer):
    """
    Serializer pour les grossesses.
    """
    patient_name = serializers.CharField(source='maternity_patient.patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = Pregnancy
        fields = [
            'id', 'maternity_patient', 'patient_name', 'doctor', 'doctor_name',
            'pregnancy_number', 'status', 'last_menstrual_period',
            'expected_delivery_date', 'actual_delivery_date',
            'weeks_of_gestation', 'risk_factors', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Valide la cohérence des dates."""
        last_period = attrs.get('last_menstrual_period')
        expected_delivery = attrs.get('expected_delivery_date')

        if last_period and expected_delivery:
            if expected_delivery <= last_period:
                raise serializers.ValidationError({
                    'expected_delivery_date':
                    "La date prévue d'accouchement doit être postérieure à la date des dernières règles."
                })

        actual_delivery = attrs.get('actual_delivery_date')
        if actual_delivery and last_period:
            if actual_delivery < last_period:
                raise serializers.ValidationError({
                    'actual_delivery_date':
                    "La date réelle d'accouchement ne peut pas être antérieure à la date des dernières règles."
                })

        return attrs


class WeeklyCheckupSerializer(serializers.ModelSerializer):
    """
    Serializer pour les consultations hebdomadaires.
    """
    patient_name = serializers.CharField(source='pregnancy.maternity_patient.patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = WeeklyCheckup
        fields = [
            'id', 'pregnancy', 'patient_name', 'doctor', 'doctor_name',
            'checkup_date', 'week_number', 'weight',
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'uterine_height', 'fetal_heart_rate',
            'complaints', 'observations', 'recommendations',
            'next_appointment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Valide la cohérence de la pression artérielle."""
        systolic = attrs.get('blood_pressure_systolic')
        diastolic = attrs.get('blood_pressure_diastolic')

        if systolic and diastolic:
            if systolic <= diastolic:
                raise serializers.ValidationError({
                    'blood_pressure_systolic':
                    "La pression systolique doit être supérieure à la pression diastolique."
                })

        return attrs


class PrenatalExamSerializer(serializers.ModelSerializer):
    """
    Serializer pour les examens prénatals.
    """
    attachments_url = serializers.SerializerMethodField()

    class Meta:
        model = PrenatalExam
        fields = [
            'id', 'pregnancy', 'prenatal_consultation', 'exam_name', 'exam_type',
            'status', 'ordered_date', 'completed_date',
            'results', 'interpretation', 'attachments', 'attachments_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'ordered_date', 'created_at', 'updated_at']

    def get_attachments_url(self, obj):
        """Retourne l'URL complète des pièces jointes."""
        if obj.attachments:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachments.url)
            return obj.attachments.url
        return None


class PrenatalConsultationSerializer(serializers.ModelSerializer):
    """
    Serializer pour les consultations prénatales (CPN).
    """
    patient_name = serializers.CharField(source='pregnancy.maternity_patient.patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    exams = PrenatalExamSerializer(many=True, read_only=True)

    class Meta:
        model = PrenatalConsultation
        fields = [
            'id', 'pregnancy', 'patient_name', 'doctor', 'doctor_name',
            'consultation_date', 'consultation_number', 'week_of_gestation',
            'weight', 'blood_pressure_systolic', 'blood_pressure_diastolic', 'temperature',
            'uterine_height', 'fetal_heart_rate', 'fetal_presentation', 'edema',
            'complaints', 'clinical_findings', 'diagnosis', 'treatment',
            'recommendations', 'next_appointment', 'exams',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Valide la cohérence de la pression artérielle."""
        systolic = attrs.get('blood_pressure_systolic')
        diastolic = attrs.get('blood_pressure_diastolic')

        if systolic and diastolic:
            if systolic <= diastolic:
                raise serializers.ValidationError({
                    'blood_pressure_systolic':
                    "La pression systolique doit être supérieure à la pression diastolique."
                })

        return attrs


class ChildSerializer(serializers.ModelSerializer):
    """
    Serializer pour les enfants.
    """
    full_name = serializers.CharField(source='full_name', read_only=True)
    mother_name = serializers.CharField(source='pregnancy.maternity_patient.patient.full_name', read_only=True)

    class Meta:
        model = Child
        fields = [
            'id', 'pregnancy', 'mother_name', 'patient', 'full_name',
            'first_name', 'last_name', 'gender', 'birth_date',
            'birth_weight', 'birth_height', 'head_circumference',
            'apgar_score_1min', 'apgar_score_5min',
            'complications', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_birth_date(self, value):
        """Valide que la date de naissance n'est pas dans le futur."""
        from django.utils import timezone
        if value > timezone.now():
            raise serializers.ValidationError(
                "La date de naissance ne peut pas être dans le futur."
            )
        return value


class ChildGrowthSerializer(serializers.ModelSerializer):
    """
    Serializer pour le suivi de croissance des enfants.
    """
    child_name = serializers.CharField(source='child.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = ChildGrowth
        fields = [
            'id', 'child', 'child_name', 'doctor', 'doctor_name',
            'checkup_date', 'age_in_months', 'weight', 'height',
            'head_circumference', 'nutritional_status',
            'developmental_milestones', 'observations',
            'recommendations', 'next_appointment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']


class ChildVaccineSerializer(serializers.ModelSerializer):
    """
    Serializer pour les vaccins des enfants.
    """
    child_name = serializers.CharField(source='child.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = ChildVaccine
        fields = [
            'id', 'child', 'child_name', 'doctor', 'doctor_name',
            'vaccine_name', 'vaccine_type', 'dose_number',
            'date_administered', 'next_dose_date',
            'batch_number', 'manufacturer', 'site', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']

    def validate_next_dose_date(self, value):
        """Valide que la date de la prochaine dose est dans le futur."""
        if value:
            date_administered = self.initial_data.get('date_administered')
            if date_administered and value <= date_administered:
                raise serializers.ValidationError(
                    "La date de la prochaine dose doit être postérieure à la date d'administration."
                )
        return value
