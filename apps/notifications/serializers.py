# apps/notifications/serializers.py

from rest_framework import serializers
from .models import PushToken


class PushTokenSerializer(serializers.ModelSerializer):
    """
    Serializer pour enregistrer/mettre à jour les tokens Expo Push.
    """
    class Meta:
        model = PushToken
        fields = ['id', 'token', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_token(self, value):
        """
        Valide que le token suit le format Expo Push Token.
        """
        if not value.startswith('ExponentPushToken[') and not value.startswith('ExpoPushToken['):
            raise serializers.ValidationError(
                "Le token doit commencer par 'ExponentPushToken[' ou 'ExpoPushToken['"
            )
        return value

    def validate_role(self, value):
        """
        Valide que le rôle est valide.
        """
        allowed_roles = ['patient', 'medecin', 'secourist']
        if value not in allowed_roles:
            raise serializers.ValidationError(
                f"Le rôle doit être l'un de : {', '.join(allowed_roles)}"
            )
        return value


class SendNotificationSerializer(serializers.Serializer):
    """
    Serializer pour envoyer une notification push.
    """
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text='Liste des IDs utilisateurs (facultatif si roles est fourni)'
    )
    roles = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
        help_text='Liste des rôles (facultatif si user_ids est fourni)'
    )
    title = serializers.CharField(max_length=100, required=True)
    body = serializers.CharField(max_length=500, required=True)
    data = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        """
        Vérifie qu'au moins user_ids ou roles est fourni.
        """
        if not attrs.get('user_ids') and not attrs.get('roles'):
            raise serializers.ValidationError(
                "Au moins 'user_ids' ou 'roles' doit être fourni"
            )
        return attrs
