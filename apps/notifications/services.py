# apps/notifications/services.py

import logging
import requests
from typing import List, Dict, Any, Optional
from .models import PushToken

logger = logging.getLogger(__name__)


class ExpoPushService:
    """
    Service pour envoyer des notifications push via l'API Expo.
    Documentation : https://docs.expo.dev/push-notifications/sending-notifications/
    """
    BASE_URL = 'https://exp.host/--/api/v2/push/send'

    def send_to_users(
        self,
        user_ids: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Envoie une notification push à des utilisateurs spécifiques.

        Args:
            user_ids: Liste des IDs utilisateurs
            title: Titre de la notification
            body: Corps de la notification
            data: Données additionnelles (optionnel)

        Returns:
            Dict avec le résultat de l'envoi
        """
        if data is None:
            data = {}

        # Récupérer les tokens des utilisateurs
        tokens = PushToken.objects.filter(
            user_id__in=user_ids
        ).values_list('token', flat=True)

        tokens_list = list(tokens)

        if not tokens_list:
            logger.warning(f"Aucun token trouvé pour les utilisateurs : {user_ids}")
            return {
                'success': False,
                'message': 'Aucun token trouvé',
                'sent': 0,
                'failed': 0
            }

        return self._send_push_notifications(tokens_list, title, body, data)

    def send_to_roles(
        self,
        roles: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Envoie une notification push à tous les utilisateurs avec certains rôles.

        Args:
            roles: Liste des rôles (patient, medecin, secourist)
            title: Titre de la notification
            body: Corps de la notification
            data: Données additionnelles (optionnel)

        Returns:
            Dict avec le résultat de l'envoi
        """
        if data is None:
            data = {}

        # Récupérer les tokens des utilisateurs avec ces rôles
        tokens = PushToken.objects.filter(
            role__in=roles
        ).values_list('token', flat=True)

        tokens_list = list(tokens)

        if not tokens_list:
            logger.warning(f"Aucun token trouvé pour les rôles : {roles}")
            return {
                'success': False,
                'message': 'Aucun token trouvé',
                'sent': 0,
                'failed': 0
            }

        return self._send_push_notifications(tokens_list, title, body, data)

    def _send_push_notifications(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Envoie les notifications push via l'API Expo.

        Args:
            tokens: Liste des tokens Expo
            title: Titre de la notification
            body: Corps de la notification
            data: Données additionnelles

        Returns:
            Dict avec le résultat de l'envoi
        """
        # Construire les messages pour l'API Expo
        messages = []
        for token in tokens:
            messages.append({
                'to': token,
                'sound': 'default',
                'title': title,
                'body': body,
                'data': data,
                'priority': 'high',
                'channelId': 'default',
            })

        try:
            # Envoyer la requête à l'API Expo
            response = requests.post(
                self.BASE_URL,
                json=messages,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            # Compter les succès et échecs
            data_results = result.get('data', [])
            success_count = sum(1 for r in data_results if r.get('status') == 'ok')
            error_count = sum(1 for r in data_results if r.get('status') == 'error')

            # Logger les erreurs spécifiques
            for i, msg_result in enumerate(data_results):
                if msg_result.get('status') == 'error':
                    error_details = msg_result.get('details', {})
                    logger.error(
                        f"Échec d'envoi push au token {tokens[i]}: "
                        f"{error_details.get('error', 'Unknown error')}"
                    )

            logger.info(
                f"Notifications envoyées : {success_count} réussies, "
                f"{error_count} échouées sur {len(tokens)} total"
            )

            return {
                'success': True,
                'message': f'{success_count} notifications envoyées avec succès',
                'sent': success_count,
                'failed': error_count,
                'details': data_results
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'envoi des notifications push : {str(e)}")
            return {
                'success': False,
                'message': f'Erreur lors de l\'envoi : {str(e)}',
                'sent': 0,
                'failed': len(tokens)
            }
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'envoi push : {str(e)}")
            return {
                'success': False,
                'message': f'Erreur inattendue : {str(e)}',
                'sent': 0,
                'failed': len(tokens)
            }


# Instance singleton du service
push_service = ExpoPushService()
