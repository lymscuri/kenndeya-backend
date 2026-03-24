"""
Configuration Django temporaire pour tester l'interface admin avec SQLite.
"""

from .base import *

# MODE DEBUG ACTIVÉ
DEBUG = True

# HOSTS AUTORISÉS
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', '*']

# BASE DE DONNÉES SQLITE (temporaire pour démo)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_demo.sqlite3',
    }
}

# EMAIL (Console backend)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CACHE (Simple cache local)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# INTERNAL IPS
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]
