"""
Configuration WSGI pour Kendeya Backend.
Expose l'application WSGI pour les serveurs de production (Gunicorn).
"""

import os
from django.core.wsgi import get_wsgi_application

# Définir les paramètres Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
