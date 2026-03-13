"""
Configuration du package config pour Kendeya Backend.
Ce fichier garantit que Celery est importé au démarrage de Django.
"""

# Importe l'application Celery dès que Django démarre
from .celery import app as celery_app

__all__ = ('celery_app',)
