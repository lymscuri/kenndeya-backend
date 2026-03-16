# apps/notifications/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from core.permissions import IsDoctor
from .models import PushToken
from .serializers import PushTokenSerializer, SendNotificationSerializer
from .services import push_service


@extend_schema(
    tags=['Notifications'],
    summary='Enregistrer un token push',
    description='Enregistre ou met à jour le token Expo Push de l\'utilisateur connecté',
    request=PushTokenSerializer,
    responses={
        200: OpenApiResponse(description='Token enregistré avec succès'),
        400: OpenApiResponse(description='Données invalides'),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_token(request):
    """
    Enregistre ou met à jour le token Expo Push de l'utilisateur connecté.

    Body:
        token (str): Token Expo Push au format ExponentPushToken[xxx]
        role (str): Rôle de l'utilisateur (patient, medecin, secourist)
    """
    serializer = PushTokenSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': {
                'code': 'invalid_data',
                'message': 'Données invalides',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # Créer ou mettre à jour le token pour l'utilisateur connecté
    token, created = PushToken.objects.update_or_create(
        user=request.user,
        defaults={
            'token': serializer.validated_data['token'],
            'role': serializer.validated_data['role'],
        }
    )

    action = 'créé' if created else 'mis à jour'

    return Response({
        'success': True,
        'message': f'Token push {action} avec succès',
        'data': PushTokenSerializer(token).data
    }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary='Envoyer une notification push',
    description='Envoie une notification push à des utilisateurs ou à des rôles spécifiques (médecins uniquement)',
    request=SendNotificationSerializer,
    responses={
        200: OpenApiResponse(description='Notification envoyée avec succès'),
        400: OpenApiResponse(description='Données invalides'),
        403: OpenApiResponse(description='Permission refusée'),
    }
)
@api_view(['POST'])
@permission_classes([IsDoctor])
def send_notification(request):
    """
    Envoie une notification push (réservé aux médecins).

    Body:
        user_ids (list): Liste des IDs utilisateurs (optionnel si roles fourni)
        roles (list): Liste des rôles (optionnel si user_ids fourni)
        title (str): Titre de la notification (max 100 caractères)
        body (str): Corps de la notification (max 500 caractères)
        data (dict): Données additionnelles (optionnel)
    """
    serializer = SendNotificationSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': {
                'code': 'invalid_data',
                'message': 'Données invalides',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # Extraire les données validées
    user_ids = serializer.validated_data.get('user_ids', [])
    roles = serializer.validated_data.get('roles', [])
    title = serializer.validated_data['title']
    body = serializer.validated_data['body']
    data = serializer.validated_data.get('data', {})

    # Envoyer les notifications
    if user_ids:
        result = push_service.send_to_users(user_ids, title, body, data)
    else:
        result = push_service.send_to_roles(roles, title, body, data)

    if result['success']:
        return Response({
            'success': True,
            'message': result['message'],
            'data': {
                'sent': result['sent'],
                'failed': result['failed']
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'success': False,
            'error': {
                'code': 'send_failed',
                'message': result['message'],
                'details': {
                    'sent': result['sent'],
                    'failed': result['failed']
                }
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
