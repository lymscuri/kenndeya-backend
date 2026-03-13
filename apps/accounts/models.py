"""
Modèles pour l'application accounts.
Gère l'authentification et les utilisateurs du système Kendeya.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager personnalisé pour le modèle User."""

    def create_user(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un utilisateur avec l'email et le mot de passe donnés.
        """
        if not email:
            raise ValueError("L'adresse email est obligatoire")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un superutilisateur avec l'email et le mot de passe donnés.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'doctor')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Modèle utilisateur personnalisé pour Kendeya.
    Utilise l'email comme identifiant unique (pas de username).
    """

    ROLE_CHOICES = [
        ('doctor', 'Médecin/Soignant'),
        ('patient', 'Patient'),
        ('secourist', 'Secouriste'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        verbose_name='Adresse email',
        max_length=255,
        unique=True,
        db_index=True
    )
    first_name = models.CharField('Prénom', max_length=150)
    last_name = models.CharField('Nom', max_length=150)
    phone = models.CharField('Téléphone', max_length=20, blank=True, default='')
    role = models.CharField(
        'Rôle',
        max_length=20,
        choices=ROLE_CHOICES,
        default='patient'
    )

    # Permissions et statuts
    is_active = models.BooleanField('Actif', default=True)
    is_staff = models.BooleanField('Staff', default=False)
    is_superuser = models.BooleanField('Superutilisateur', default=False)

    # Timestamps
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Date de modification', auto_now=True)
    last_login = models.DateTimeField('Dernière connexion', null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Retourne le prénom de l'utilisateur."""
        return self.first_name

    @property
    def is_doctor(self):
        """Vérifie si l'utilisateur est un médecin/soignant."""
        return self.role == 'doctor'

    @property
    def is_patient(self):
        """Vérifie si l'utilisateur est un patient."""
        return self.role == 'patient'

    @property
    def is_secourist(self):
        """Vérifie si l'utilisateur est un secouriste."""
        return self.role == 'secourist'
