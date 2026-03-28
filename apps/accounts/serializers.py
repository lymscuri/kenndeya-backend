"""
Serializers pour l'application accounts.
Gère la sérialisation et validation des données d'authentification.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription d'un nouvel utilisateur.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    role = serializers.ChoiceField(choices=[('doctor', 'Médecin'), ('patient', 'Patient')])

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'role'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        """Valide que les deux mots de passe correspondent."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Les mots de passe ne correspondent pas."
            })
        return attrs

    def validate_email(self, value):
        """Valide que l'email n'existe pas déjà."""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("Cette adresse email est déjà utilisée.")
        return value.lower()

    def create(self, validated_data):
        """Crée un nouvel utilisateur."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer pour la connexion d'un utilisateur.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Valide les identifiants de connexion."""
        email = attrs.get('email', '').lower()
        password = attrs.get('password', '')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )

            if not user:
                raise serializers.ValidationError(
                    "Email ou mot de passe incorrect.",
                    code='authorization'
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    "Ce compte est désactivé.",
                    code='authorization'
                )

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                "L'email et le mot de passe sont requis.",
                code='authorization'
            )


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer pour afficher les informations d'un utilisateur.
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'is_active', 'created_at', 'updated_at',
            'last_login'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'is_active',
            'created_at', 'updated_at', 'last_login'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer pour changer le mot de passe d'un utilisateur.
    """
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        """Valide que l'ancien mot de passe est correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("L'ancien mot de passe est incorrect.")
        return value

    def validate(self, attrs):
        """Valide que les deux nouveaux mots de passe correspondent."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Les mots de passe ne correspondent pas."
            })
        return attrs

    def save(self, **kwargs):
        """Change le mot de passe de l'utilisateur."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
