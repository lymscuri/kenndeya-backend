"""
Routing WebSocket pour l'application urgences.
Définit les routes pour les connexions WebSocket.
"""

from django.urls import path
from . import consumers


websocket_urlpatterns = [
    # WebSocket pour les secouristes (alertes d'urgence)
    path('ws/urgences/alerts/', consumers.EmergencyAlertConsumer.as_asgi()),

    # WebSocket pour les patients (mises à jour de leurs alertes)
    path('ws/urgences/patient/alerts/', consumers.PatientAlertConsumer.as_asgi()),
]
