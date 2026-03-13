"""Configuration de l'application dossiers."""

from django.apps import AppConfig


class DossiersConfig(AppConfig):
    """Configuration pour l'application dossiers."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dossiers'
    verbose_name = 'Dossiers Médicaux'
