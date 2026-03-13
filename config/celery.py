"""
Configuration Celery pour Kendeya Backend.
Gère les tâches asynchrones (rappels SMS, notifications, etc.).
"""

import os
from celery import Celery

# Définir les paramètres Django par défaut pour Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Créer l'instance Celery
app = Celery('kendeya_backend')

# Charger la configuration depuis Django settings avec le préfixe CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans les fichiers tasks.py de chaque application
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tâche de debug pour tester Celery."""
    print(f'Request: {self.request!r}')
