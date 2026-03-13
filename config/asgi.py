"""
Configuration ASGI pour Kendeya Backend.
Gère les connexions HTTP et WebSocket via Django Channels.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Définir les paramètres Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Initialiser Django ASGI application tôt pour garantir que AppRegistry est peuplé
# avant d'importer du code qui pourrait l'utiliser
django_asgi_app = get_asgi_application()

# Import des routes WebSocket (après l'initialisation de Django)
from apps.urgences.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # Requêtes HTTP Django classiques
    "http": django_asgi_app,

    # Connexions WebSocket
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        )
    ),
})
