"""
Serializers pour l'application dossiers.
Gère la sérialisation des dossiers médicaux, consultations, etc.
"""

from rest_framework import serializers
from .models import Patient, MedicalRecord, Consultation, Prescription, LabTest, Vaccination


class PatientListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des patients (version allégée).
    """
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'full_name', 'first_name', 'last_name', 'age',
            'date_of_birth', 'gender', 'phone', 'email', 'created_at', 'doctor'
        ]
        read_only_fields = ['id', 'created_at']


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour les patients.
    """
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'doctor', 'doctor_name', 'full_name',
            'first_name', 'last_name', 'date_of_birth', 'age', 'gender',
            'phone', 'email', 'blood_type', 'allergies', 'chronic_conditions',
            'address', 'city', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']

    def validate_date_of_birth(self, value):
        """Valide que la date de naissance n'est pas dans le futur."""
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError(
                "La date de naissance ne peut pas être dans le futur."
            )
        return value


class MedicalRecordSerializer(serializers.ModelSerializer):
    """
    Serializer pour les dossiers médicaux.
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient', 'patient_name', 'record_number',
            'qr_code', 'qr_code_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'record_number', 'qr_code', 'created_at', 'updated_at']

    def get_qr_code_url(self, obj):
        """Retourne l'URL complète du QR code."""
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
            return obj.qr_code.url
        return None


class PrescriptionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les ordonnances.
    """
    class Meta:
        model = Prescription
        fields = [
            'id', 'consultation', 'medication_name', 'dosage',
            'frequency', 'duration', 'instructions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LabTestSerializer(serializers.ModelSerializer):
    """
    Serializer pour les examens de laboratoire.
    """
    attachments_url = serializers.SerializerMethodField()

    class Meta:
        model = LabTest
        fields = [
            'id', 'consultation', 'test_name', 'test_type', 'status',
            'ordered_date', 'completed_date', 'results', 'interpretation',
            'attachments', 'attachments_url', 'created_at', 'updated_at'
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


class ConsultationListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des consultations (version allégée).
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = Consultation
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'date', 'reason', 'diagnosis', 'created_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at']


class ConsultationSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour les consultations avec prescriptions et examens.
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    lab_tests = LabTestSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'date', 'reason', 'symptoms', 'diagnosis', 'treatment', 'notes',
            'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'weight', 'height',
            'prescriptions', 'lab_tests',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Valide la cohérence des constantes vitales."""
        systolic = attrs.get('blood_pressure_systolic')
        diastolic = attrs.get('blood_pressure_diastolic')

        if systolic and diastolic:
            if systolic <= diastolic:
                raise serializers.ValidationError({
                    'blood_pressure_systolic':
                    "La pression systolique doit être supérieure à la pression diastolique."
                })

        return attrs


class VaccinationSerializer(serializers.ModelSerializer):
    """
    Serializer pour les vaccinations.
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = Vaccination
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
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


class MyMedicalRecordSerializer(serializers.ModelSerializer):
    """
    Serializer pour le dossier médical complet d'un patient.
    Retourne toutes les informations : identité, consultations, vaccinations, etc.
    """
    consultations = ConsultationListSerializer(many=True, read_only=True)
    vaccinations = VaccinationSerializer(many=True, read_only=True)
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth', 'age', 'gender',
            'phone', 'email', 'blood_type', 'allergies', 'chronic_conditions',
            'address', 'city', 'consultations', 'vaccinations', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at'
        ]
