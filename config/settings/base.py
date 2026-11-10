"""
Configuration de base Django pour Kendeya Backend.
Paramètres communs à tous les environnements (dev, production).
"""

import os
from pathlib import Path
from datetime import timedelta
import environ

# Initialisation de django-environ pour gérer les variables d'environnement
env = environ.Env(
    DEBUG=(bool, False)
)

# Chemin de base du projet
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Lecture du fichier .env s'il existe
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITÉ
# ATTENTION : SECRET_KEY doit être définie dans les variables d'environnement
SECRET_KEY = env('SECRET_KEY', default='CHANGE-ME-IN-PRODUCTION')

# DEBUG sera défini dans les fichiers spécifiques (development.py, production.py)
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# APPLICATIONS DJANGO
INSTALLED_APPS = [
    # Jazzmin (doit être avant django.contrib.admin)
    'jazzmin',

    # Applications Django par défaut
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Applications tierces
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'corsheaders',
    'channels',
    'django_celery_beat',

    # Applications du projet
    'apps.accounts',
    'apps.dossiers',
    'apps.maternite',
    'apps.urgences',
    'apps.reminders',
    'apps.sms',
    'apps.notifications',
    'apps.firstaid',
    'core',
]

# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS avant CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CONFIGURATION DES URLS
ROOT_URLCONF = 'config.urls'

# TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI et ASGI
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# BASE DE DONNÉES (PostgreSQL)
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgresql://localhost/kendeya_db')
}

# MODÈLE UTILISATEUR PERSONNALISÉ
AUTH_USER_MODEL = 'accounts.User'

# VALIDATION DES MOTS DE PASSE
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# INTERNATIONALISATION
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Conakry'
USE_I18N = True
USE_TZ = True

# FICHIERS STATIQUES (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# FICHIERS MÉDIAS (uploads utilisateurs)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# TYPE DE CHAMP AUTO PAR DÉFAUT
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CONFIGURATION DJANGO REST FRAMEWORK
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    'NON_FIELD_ERRORS_KEY': 'error',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
    # Limitation de débit par portée (ScopedRateThrottle). 'firstaid' : endpoints
    # publics de premiers secours, anonymes, lecture seule, mis en cache 1 h côté client.
    'DEFAULT_THROTTLE_RATES': {
        'firstaid': '120/hour',
        'emergency_places': '60/hour',   # lieux d'urgence autour de moi, public
    },
}

# CONFIGURATION DRF-SPECTACULAR (Documentation API)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Kendeya Backend API',
    'DESCRIPTION': 'API REST pour la plateforme de gestion médicale Kendeya (Guinée)',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'Serveur de développement'},
        {'url': 'https://api.kendeya.com', 'description': 'Serveur de production'},
    ],
    'TAGS': [
        {'name': 'Authentification', 'description': 'Endpoints d\'authentification et gestion des utilisateurs'},
        {'name': 'Dossiers', 'description': 'Gestion des patients et dossiers médicaux'},
        {'name': 'Maternité', 'description': 'Suivi de grossesse et croissance des enfants'},
        {'name': 'Urgences', 'description': 'Alertes d\'urgence et secouristes'},
        {'name': 'Rappels', 'description': 'Rappels SMS automatiques'},
    ],
    'CONTACT': {
        'name': 'Équipe Kendeya',
        'email': 'support@kendeya.com',
    },
    'LICENSE': {
        'name': 'Propriétaire',
    },
    'SECURITY': [
        {
            'bearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    ],
}

# CONFIGURATION SIMPLE JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# CONFIGURATION CORS
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])
CORS_ALLOW_CREDENTIALS = True

# CONFIGURATION CHANNELS (WebSocket)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}

# CONFIGURATION CELERY
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# CONFIGURATION SMS (Twilio)
# SMS_ENABLED : interrupteur explicite d'envoi. False par défaut — l'envoi
# de SMS réels doit être un acte volontaire, jamais une valeur par défaut.
SMS_ENABLED = env.bool('SMS_ENABLED', default=False)
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = env('TWILIO_PHONE_NUMBER', default='')

# ==============================================================================
# PREMIERS SECOURS (apps.firstaid)
# ==============================================================================
# Numéro d'urgence affiché à l'utilisateur. Vient UNIQUEMENT de l'environnement,
# jamais d'un fichier de protocole (défaut : 442, Guinée).
EMERGENCY_NUMBER = env('EMERGENCY_NUMBER', default='442')

# FIRSTAID_ALLOW_DRAFTS : autorise publishable_protocols() à exposer les
# protocoles non validés par un médecin (développement/recette uniquement).
# production.py force cette valeur à False en dur, sans lire l'environnement.
FIRSTAID_ALLOW_DRAFTS = env.bool('FIRSTAID_ALLOW_DRAFTS', default=False)

# Classification de scénario (POST /api/v1/firstaid/classify/ et /answer/).
# Le modèle de langage ne fait que RECONNAÎTRE un scénario parmi les protocoles
# publiables ; aucun texte qu'il produit n'est jamais renvoyé au client.
GROQ_API_KEY = env('GROQ_API_KEY', default='')                       # vide → 503 classifier_unavailable
GROQ_MODEL_FAST = env('GROQ_MODEL_FAST', default='openai/gpt-oss-20b')  # même défaut que l'app mobile
GROQ_TIMEOUT = env.float('GROQ_TIMEOUT', default=8.0)                 # secondes
GROQ_REASONING_EFFORT = env('GROQ_REASONING_EFFORT', default='low')  # gpt-oss/qwen3 ; '' pour l'omettre
FIRSTAID_CLASSIFY_MIN = env.float('FIRSTAID_CLASSIFY_MIN', default=0.6)  # confiance minimale

# Lieux d'urgence autour de moi (apps.urgences.places) : contact affiché dans le
# User-Agent envoyé aux miroirs Overpass (politique d'usage d'OpenStreetMap).
EMERGENCY_PLACES_CONTACT = env('EMERGENCY_PLACES_CONTACT', default='admin@kendeya.com')
EMERGENCY_PLACES_TIMEOUT = env.float('EMERGENCY_PLACES_TIMEOUT', default=8.0)   # secondes par miroir Overpass
# Points préchauffés toutes les 4 h (warm_emergency_places), format "nom:lat:lon".
# Addis-Abeba : tests du DG en déplacement — à retirer après.
EMERGENCY_PLACES_WARM_POINTS = env.list('EMERGENCY_PLACES_WARM_POINTS', default=[
    'Conakry:9.537:-13.678', 'Kindia:10.056:-12.866', 'Labé:11.318:-12.283', 'Kankan:10.385:-9.306',
    "N'Zérékoré:7.756:-8.818", 'Boké:10.940:-14.291', 'Mamou:10.376:-12.084', 'Faranah:10.040:-10.743',
    'Addis-Abeba:9.03:38.74',
])
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'send-pending-reminders-every-hour': {
        'task': 'apps.reminders.tasks.send_pending_reminders',
        'schedule': crontab(minute=0),
    },
}

# LOGGING
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# CONFIGURATION JAZZMIN (Django Admin personnalisé)
JAZZMIN_SETTINGS = {
    "site_title": "Kendeya Admin",
    "site_header": "Kendeya",
    "site_brand": "Kendeya Santé",
    "welcome_sign": "Bienvenue dans l'administration Kendeya",
    "copyright": "SilySec © 2026",
    "search_model": ["accounts.User"],
    "icons": {
        "accounts.User": "fas fa-user-md",
        "dossiers.Patient": "fas fa-folder-open",
        "sms.SMSReminder": "fas fa-sms",
    },
    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "brand_colour": "navbar-purple",
    "accent": "accent-purple",
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-purple",
}

# Finders pour inclure les fichiers statiques des apps installées
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
