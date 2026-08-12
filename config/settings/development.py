"""
Configuration Django pour l'environnement de développement.
Hérite de base.py et ajoute des paramètres spécifiques au développement.
"""

from .base import *

# MODE DEBUG ACTIVÉ
DEBUG = True

# HOSTS AUTORISÉS EN DÉVELOPPEMENT
# On ouvre à tous les hosts UNIQUEMENT si DEBUG est vrai. L'IP LAN du
# poste de dev change à chaque reconnexion (partage de connexion,
# hotspot, Wi-Fi différent) — figer une IP casse le workflow. Ce fichier
# n'est jamais chargé en production (settings.production reste distinct).
if DEBUG:
    ALLOWED_HOSTS = ['*']
    CORS_ALLOW_ALL_ORIGINS = True
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
    CORS_ALLOW_ALL_ORIGINS = False

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
