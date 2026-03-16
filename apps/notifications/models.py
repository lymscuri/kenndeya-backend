# apps/notifications/models.py

import uuid
from django.db import models
from apps.accounts.models import User


class PushToken(models.Model):
    """
    Stocke les tokens Expo Push pour chaque utilisateur.
    Permet d'envoyer des notifications push via l'API Expo.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='push_token',
        verbose_name='Utilisateur'
    )
    token = models.CharField(
        max_length=200,
        verbose_name='Token Expo Push',
        help_text='Token au format ExponentPushToken[xxx]'
    )
    role = models.CharField(
        max_length=20,
        verbose_name='Rôle',
        help_text='Rôle de l\'utilisateur (patient, medecin, secourist)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Créé le')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Mis à jour le')

    class Meta:
        db_table = 'push_tokens'
        ordering = ['-created_at']
        verbose_name = 'Token Push'
        verbose_name_plural = 'Tokens Push'

    def __str__(self):
        return f"PushToken {self.user.email} - {self.role}"
