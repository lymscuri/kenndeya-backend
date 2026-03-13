"""
Configuration Django pour l'environnement de développement.
Hérite de base.py et ajoute des paramètres spécifiques au développement.
"""

from .base import *

# MODE DEBUG ACTIVÉ
DEBUG = True

# HOSTS AUTORISÉS EN DÉVELOPPEMENT
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# SÉCURITÉ (Relâchée pour le développement)
CORS_ALLOW_ALL_ORIGINS = False  # On garde les origines définies dans base.py

# EMAIL (Console backend pour le développement)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# AFFICHAGE DES ERREURS SQL DANS LA CONSOLE
LOGGING['loggers']['django.db.backends'] = {
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}

# CACHE (Simple cache local pour le développement)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# INTERNAL IPS (pour Django Debug Toolbar si installé)
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]
