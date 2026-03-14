"""
Configuration Django pour l'environnement de production.
Hérite de base.py et ajoute des paramètres de sécurité renforcés.
"""

from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# MODE DEBUG DÉSACTIVÉ
DEBUG = env.bool('DEBUG', default=False)

# HOSTS AUTORISÉS (définis dans les variables d'environnement)
# Exemple : ALLOWED_HOSTS=kendeya.railway.app,api.kendeya.com
# Railway utilise healthcheck.railway.app pour le healthcheck
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])
if 'healthcheck.railway.app' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('healthcheck.railway.app')

# CSRF pour l'admin en production
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[
    'https://kenndeya-backend-production.up.railway.app',
    'https://*.up.railway.app',
])

# SÉCURITÉ RENFORCÉE

# HTTPS géré par Railway
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies sécurisés
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# En-têtes de sécurité
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CORS (origines strictes en production)
CORS_ALLOW_ALL_ORIGINS = False
# CORS_ALLOWED_ORIGINS est déjà défini dans base.py via les variables d'environnement

# CONFIGURATION EMAIL (utiliser un service SMTP en production)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@kendeya.com')

# CACHE (Redis en production)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# FICHIERS STATIQUES (WhiteNoise pour servir les fichiers statiques)
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# LOGGING (plus détaillé en production pour déboguer)
LOGGING['handlers']['console']['level'] = 'INFO'
LOGGING['root']['level'] = 'INFO'
LOGGING['loggers']['django'] = {
    'handlers': ['console'],
    'level': 'INFO',
    'propagate': False,
}

# MONITORING SENTRY (si configuré)
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% des transactions
        send_default_pii=False,  # Ne pas envoyer d'infos personnelles
        environment='production',
    )

# LIMITE DE TAILLE DES FICHIERS UPLOADÉS
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
