"""
Serializers pour l'application dossiers.
Gère la sérialisation des dossiers médicaux, consultations, etc.
"""

from rest_framework import serializers
from .models import Patient, MedicalRecord, Consultation, Prescription, LabTest, Vaccination, Chirurgie, Hospitalisation


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
        read_only_fields = ['id', 'consultation', 'created_at', 'updated_at']


class LabTestSerializer(serializers.ModelSerializer):
    """
    Serializer pour les examens de laboratoire.
    """
    attachments_url = serializers.SerializerMethodField()

    class Meta:
        model = LabTest
        fields = [
            'id', 'consultation', 'patient', 'test_name', 'test_type', 'status',
            'ordered_date', 'completed_date', 'results', 'interpretation',
            'attachments', 'attachments_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'consultation', 'patient', 'ordered_date', 'created_at', 'updated_at']

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
    Accepte vital_signs comme objet pour compatibilité frontend.
    """
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    vital_signs = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = Consultation
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'date', 'reason', 'symptoms', 'diagnosis', 'treatment', 'notes',
            'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'weight', 'height',
            'vital_signs',
            'prescriptions', 'lab_tests',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']

    def validate(self, attrs):
        """
        Valide la cohérence des constantes vitales.
        Décompose vital_signs si fourni.
        """
        # Décomposer vital_signs si fourni
        vital_signs = attrs.pop('vital_signs', None)
        if vital_signs:
            attrs['temperature'] = vital_signs.get('temperature')
            attrs['blood_pressure_systolic'] = vital_signs.get('systolicBP')
            attrs['blood_pressure_diastolic'] = vital_signs.get('diastolicBP')
            attrs['heart_rate'] = vital_signs.get('heartRate')
            attrs['weight'] = vital_signs.get('weight')
            attrs['height'] = vital_signs.get('height')

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
        read_only_fields = ['id', 'patient', 'doctor', 'created_at', 'updated_at']

    def validate_next_dose_date(self, value):
        """Valide que la date de la prochaine dose est dans le futur."""
        if value:
            date_administered = self.initial_data.get('date_administered')
            if date_administered and value <= date_administered:
                raise serializers.ValidationError(
                    "La date de la prochaine dose doit être postérieure à la date d'administration."
                )
        return value


class LabTestNestedSerializer(serializers.ModelSerializer):
    """
    Serializer imbriqué pour les examens de laboratoire dans consultations.
    Version simplifiée avec uniquement les champs essentiels.
    """
    class Meta:
        model = LabTest
        fields = [
            'id', 'test_name', 'test_type', 'status',
            'ordered_date', 'completed_date', 'results', 'interpretation'
        ]
        read_only_fields = ['id']


class ConsultationNestedSerializer(serializers.ModelSerializer):
    """
    Serializer imbriqué pour les consultations dans my-record.
    Retourne les consultations avec les noms de champs attendus par le frontend.
    """
    motif = serializers.CharField(source='reason', read_only=True)
    motif_detail = serializers.CharField(source='symptoms', read_only=True)
    diagnostic = serializers.CharField(source='diagnosis', read_only=True)
    traitement = serializers.CharField(source='treatment', read_only=True)
    recommandations = serializers.CharField(source='notes', read_only=True)
    poids = serializers.DecimalField(source='weight', max_digits=5, decimal_places=2, read_only=True)
    taille = serializers.DecimalField(source='height', max_digits=5, decimal_places=2, read_only=True)
    tension_systolique = serializers.IntegerField(source='blood_pressure_systolic', read_only=True)
    tension_diastolique = serializers.IntegerField(source='blood_pressure_diastolic', read_only=True)
    frequence_cardiaque = serializers.IntegerField(source='heart_rate', read_only=True)
    spo2 = serializers.SerializerMethodField()
    prochain_rdv = serializers.SerializerMethodField()
    lab_tests = LabTestNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = [
            'id', 'date', 'motif', 'motif_detail', 'diagnostic', 'traitement',
            'recommandations', 'poids', 'taille', 'tension_systolique',
            'tension_diastolique', 'frequence_cardiaque', 'temperature',
            'spo2', 'prochain_rdv', 'lab_tests'
        ]
        read_only_fields = ['id']

    def get_spo2(self, obj):
        """SpO2 n'existe pas dans le modèle, retourne None."""
        return None

    def get_prochain_rdv(self, obj):
        """Prochain RDV n'existe pas dans le modèle, retourne None."""
        return None


class VaccinationNestedSerializer(serializers.ModelSerializer):
    """
    Serializer imbriqué pour les vaccinations dans my-record.
    Version simplifiée avec uniquement les champs essentiels.
    """
    class Meta:
        model = Vaccination
        fields = [
            'id', 'vaccine_name', 'date_administered', 'dose_number',
            'next_dose_date', 'notes'
        ]
        read_only_fields = ['id']


class ChirurgieSerializer(serializers.ModelSerializer):
    """
    Serializer pour les chirurgies.
    """
    class Meta:
        model = Chirurgie
        fields = '__all__'
        read_only_fields = ['id', 'patient', 'created_at', 'updated_at']


class HospitalisationSerializer(serializers.ModelSerializer):
    """
    Serializer pour les hospitalisations.
    """
    class Meta:
        model = Hospitalisation
        fields = '__all__'
        read_only_fields = ['id', 'patient', 'created_at', 'updated_at']


class LabTestDirectSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = ["id", "test_name", "test_type", "status",
                  "ordered_date", "completed_date", "results", "interpretation"]
        read_only_fields = ["id"]

class PatientListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des patients (version allégée).
    Inclut les consultations et vaccinations complètes pour la synchronisation frontend.
    """
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    numero_dossier = serializers.SerializerMethodField()
    linked_email = serializers.EmailField(source='email', read_only=True)
    chronic_diseases = serializers.CharField(source='chronic_conditions', read_only=True)
    emergency_contacts = serializers.SerializerMethodField()
    consultations = ConsultationNestedSerializer(many=True, read_only=True)
    vaccines = VaccinationNestedSerializer(source='vaccinations', many=True, read_only=True)
    surgeries = ChirurgieSerializer(many=True, read_only=True)
    hospitalisations = HospitalisationSerializer(many=True, read_only=True)
    direct_lab_tests = LabTestDirectSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'full_name', 'first_name', 'last_name', 'age',
            'date_of_birth', 'gender', 'phone', 'email', 'numero_dossier',
            'blood_type', 'allergies', 'chronic_diseases',
            'critical_info', 'personal_history', 'family_history',
            'life_habits', 'permanent_treatments',
            'address', 'city', 'prefecture', 'linked_email', 'emergency_contacts',
            'consultations', 'vaccines', 'surgeries', 'hospitalisations', 'direct_lab_tests',
            'created_at', 'doctor'
        ]
        read_only_fields = ['id', 'created_at']

    def get_numero_dossier(self, obj):
        """Retourne le numéro de dossier depuis MedicalRecord."""
        try:
            return obj.medical_record.record_number
        except Exception:
            return None

    def get_emergency_contacts(self, obj):
        """Retourne les contacts d'urgence depuis critical_info ou liste vide."""
        if obj.critical_info and isinstance(obj.critical_info, dict):
            return obj.critical_info.get('emergency_contacts', [])
        return []


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour les patients.
    """
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    consultations = ConsultationListSerializer(many=True, read_only=True)
    vaccinations = VaccinationSerializer(many=True, read_only=True)
    surgeries = ChirurgieSerializer(many=True, read_only=True)
    hospitalisations = HospitalisationSerializer(many=True, read_only=True)
    direct_lab_tests = LabTestDirectSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'doctor', 'doctor_name', 'full_name',
            'first_name', 'last_name', 'date_of_birth', 'age', 'gender',
            'phone', 'email', 'blood_type', 'allergies', 'chronic_conditions',
            'personal_history', 'family_history', 'life_habits',
            'critical_info', 'permanent_treatments',
            'address', 'city', 'prefecture', 'consultations', 'vaccinations',
            'created_at', 'updated_at', 'surgeries', 'hospitalisations', 'direct_lab_tests',
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


class MyMedicalRecordSerializer(serializers.ModelSerializer):
    """
    Serializer pour le dossier médical complet d'un patient.
    Retourne toutes les informations : identité, consultations, vaccinations, etc.
    """
    numero_dossier = serializers.SerializerMethodField()
    linked_email = serializers.EmailField(source='email', read_only=True)
    chronic_diseases = serializers.CharField(source='chronic_conditions', read_only=True)
    emergency_contacts = serializers.SerializerMethodField()
    age = serializers.IntegerField(read_only=True)
    consultations = ConsultationNestedSerializer(many=True, read_only=True)
    vaccines = VaccinationNestedSerializer(source='vaccinations', many=True, read_only=True)
    surgeries = ChirurgieSerializer(many=True, read_only=True)
    hospitalisations = HospitalisationSerializer(many=True, read_only=True)
    direct_lab_tests = LabTestDirectSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'numero_dossier', 'first_name', 'last_name', 'age', 'gender',
            'phone', 'address', 'city', 'prefecture', 'date_of_birth',
            'blood_type', 'allergies', 'chronic_diseases',
            'permanent_treatments', 'personal_history', 'family_history',
            'life_habits', 'critical_info', 'emergency_contacts', 'linked_email',
            'consultations', 'vaccines', 'surgeries', 'hospitalisations', 'direct_lab_tests'
        ]
        read_only_fields = ['id', 'age']

    def get_numero_dossier(self, obj):
        """Retourne le numéro de dossier depuis MedicalRecord."""
        try:
            return obj.medical_record.record_number
        except Exception:
            return None

    def get_emergency_contacts(self, obj):
        """Retourne les contacts d'urgence depuis critical_info ou liste vide."""
        if obj.critical_info and isinstance(obj.critical_info, dict):
            return obj.critical_info.get('emergency_contacts', [])
        return []
