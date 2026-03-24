"""
Configuration WSGI pour Kendeya Backend.
Expose l'application WSGI pour les serveurs de production (Gunicorn).
"""

import os
from django.core.wsgi import get_wsgi_application

# Définir les paramètres Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

# Lancer collectstatic automatiquement au démarrage
import subprocess
import sys
try:
    subprocess.run(
        [sys.executable, 'manage.py', 'collectstatic', '--noinput'],
        check=True,
        capture_output=True
    )
except Exception as e:
    print(f'collectstatic warning: {e}')

application = get_wsgi_application()
