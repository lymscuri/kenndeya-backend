"""
Consumers WebSocket pour l'application urgences.
Gère les notifications en temps réel pour les alertes d'urgence.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class EmergencyAlertConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket pour les alertes d'urgence.

    Les secouristes se connectent à ce consumer pour recevoir
    les notifications d'alertes d'urgence en temps réel.
    """

    async def connect(self):
        """Connexion d'un secouriste au canal WebSocket."""
        self.user = self.scope['user']

        # Vérifier que l'utilisateur est authentifié
        if not self.user.is_authenticated:
            await self.close()
            return

        # Rejoindre le groupe des secouristes
        self.room_group_name = 'emergency_alerts'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Déconnexion du canal WebSocket."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Réception d'un message du client.
        Non utilisé pour le moment.
        """
        pass

    async def emergency_alert_created(self, event):
        """
        Envoi d'une notification de nouvelle alerte d'urgence.
        """
        await self.send(text_data=json.dumps({
            'type': 'emergency_alert_created',
            'alert': event['alert']
        }))

    async def emergency_alert_updated(self, event):
        """
        Envoi d'une notification de mise à jour d'alerte.
        """
        await self.send(text_data=json.dumps({
            'type': 'emergency_alert_updated',
            'alert': event['alert']
        }))

    async def emergency_alert_assigned(self, event):
        """
        Envoi d'une notification d'assignation d'alerte.
        """
        await self.send(text_data=json.dumps({
            'type': 'emergency_alert_assigned',
            'alert': event['alert']
        }))


class PatientAlertConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket pour les patients.

    Les patients se connectent pour recevoir les mises à jour
    sur leurs alertes d'urgence.
    """

    async def connect(self):
        """Connexion d'un patient au canal WebSocket."""
        self.user = self.scope['user']

        # Vérifier que l'utilisateur est authentifié
        if not self.user.is_authenticated:
            await self.close()
            return

        # Rejoindre le groupe personnel du patient
        self.room_group_name = f'patient_{self.user.id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Déconnexion du canal WebSocket."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Réception d'un message du client.
        Non utilisé pour le moment.
        """
        pass

    async def alert_status_updated(self, event):
        """
        Envoi d'une notification de mise à jour du statut de l'alerte.
        """
        await self.send(text_data=json.dumps({
            'type': 'alert_status_updated',
            'alert': event['alert'],
            'message': event.get('message', '')
        }))

    async def secourist_assigned(self, event):
        """
        Envoi d'une notification d'assignation d'un secouriste.
        """
        await self.send(text_data=json.dumps({
            'type': 'secourist_assigned',
            'alert': event['alert'],
            'secourist': event['secourist'],
            'message': event.get('message', '')
        }))
