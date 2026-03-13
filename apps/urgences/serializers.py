"""
Serializers pour l'application urgences.
Gère la sérialisation des alertes d'urgence, secouristes et hôpitaux.
"""

from rest_framework import serializers
from .models import Secourist, Hospital, EmergencyAlert


class SecouristSerializer(serializers.ModelSerializer):
    """
    Serializer pour les secouristes.
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = Secourist
        fields = [
            'id', 'user', 'user_name', 'user_email', 'user_phone',
            'specialization', 'license_number', 'is_available',
            'latitude', 'longitude',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class HospitalSerializer(serializers.ModelSerializer):
    """
    Serializer pour les hôpitaux.
    """
    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'address', 'city', 'phone', 'email',
            'hospital_type', 'capacity', 'has_emergency_room', 'has_maternity',
            'latitude', 'longitude', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmergencyAlertSerializer(serializers.ModelSerializer):
    """
    Serializer pour les alertes d'urgence.
    """
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    secourist_name = serializers.CharField(source='secourist.user.get_full_name', read_only=True, allow_null=True)
    hospital_name = serializers.CharField(source='hospital.name', read_only=True, allow_null=True)

    class Meta:
        model = EmergencyAlert
        fields = [
            'id', 'patient', 'patient_name', 'secourist', 'secourist_name',
            'hospital', 'hospital_name', 'status', 'priority',
            'emergency_type', 'description', 'symptoms',
            'patient_latitude', 'patient_longitude', 'patient_address',
            'notes', 'resolution_notes',
            'assigned_at', 'resolved_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'patient', 'created_at', 'updated_at']

    def validate(self, attrs):
        """Valide la cohérence des données."""
        status = attrs.get('status')
        secourist = attrs.get('secourist')

        # Si l'alerte est assignée, un secouriste doit être assigné
        if status in ['assigned', 'in_progress'] and not secourist:
            raise serializers.ValidationError({
                'secourist': "Un secouriste doit être assigné pour ce statut."
            })

        return attrs
