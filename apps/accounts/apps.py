"""Configuration de l'application accounts."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration pour l'application accounts."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Authentification et Comptes'
