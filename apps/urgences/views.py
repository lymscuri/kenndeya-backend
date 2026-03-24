"""
Vues pour l'application urgences.
Gère les alertes d'urgence, secouristes et hôpitaux.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.permissions import IsSecourist
from .models import Secourist, Hospital, EmergencyAlert
from .serializers import SecouristSerializer, HospitalSerializer, EmergencyAlertSerializer
from apps.notifications.services import push_service


# ========== SECOURIST PROFILES ==========

@api_view(['POST'])
@permission_classes([IsSecourist])
def secourist_profile_create(request):
    """
    Crée un profil de secouriste pour l'utilisateur connecté.

    POST /api/v1/urgences/secourist/profile/
    """
    # Vérifier que l'utilisateur n'a pas déjà un profil de secouriste
    if hasattr(request.user, 'secourist_profile'):
        return Response({
            'success': False,
            'error': {
                'code': 'already_exists',
                'message': 'Vous avez déjà un profil de secouriste.',
                'details': {}
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    serializer = SecouristSerializer(data=request.data)

    if serializer.is_valid():
        secourist = serializer.save(user=request.user)

        return Response({
            'success': True,
            'message': 'Profil de secouriste créé avec succès.',
            'data': SecouristSerializer(secourist).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH'])
@permission_classes([IsSecourist])
def secourist_profile_detail(request):
    """
    Récupère ou modifie le profil de secouriste de l'utilisateur connecté.

    GET /api/v1/urgences/secourist/profile/detail/
    PATCH /api/v1/urgences/secourist/profile/detail/
    """
    secourist = get_object_or_404(Secourist, user=request.user)

    if request.method == 'GET':
        serializer = SecouristSerializer(secourist)
        return Response({
            'success': True,
            'message': 'Profil de secouriste récupéré avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = SecouristSerializer(secourist, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profil de secouriste mis à jour avec succès.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def secourist_list(request):
    """
    Liste tous les secouristes disponibles.

    GET /api/v1/urgences/secourists/
    """
    secourists = Secourist.objects.filter(is_available=True)
    serializer = SecouristSerializer(secourists, many=True)

    return Response({
        'success': True,
        'count': secourists.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


# ========== HOSPITALS ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_list(request):
    """
    Liste tous les hôpitaux actifs.

    GET /api/v1/urgences/hospitals/
    """
    hospitals = Hospital.objects.filter(is_active=True)

    # Filtres optionnels
    city = request.query_params.get('city')
    has_emergency = request.query_params.get('has_emergency_room')

    if city:
        hospitals = hospitals.filter(city__icontains=city)
    if has_emergency:
        hospitals = hospitals.filter(has_emergency_room=True)

    paginator = PageNumberPagination()
    paginated_hospitals = paginator.paginate_queryset(hospitals, request)
    serializer = HospitalSerializer(paginated_hospitals, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hospital_detail(request, hospital_id):
    """
    Récupère les détails d'un hôpital.

    GET /api/v1/urgences/hospitals/:id/
    """
    hospital = get_object_or_404(Hospital, id=hospital_id, is_active=True)
    serializer = HospitalSerializer(hospital)

    return Response({
        'success': True,
        'message': 'Hôpital récupéré avec succès.',
        'data': serializer.data
    }, status=status.HTTP_200_OK)


# ========== EMERGENCY ALERTS ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def emergency_alert_create(request):
    """
    Crée une nouvelle alerte d'urgence.

    POST /api/v1/urgences/alerts/
    """
    serializer = EmergencyAlertSerializer(data=request.data)

    if serializer.is_valid():
        alert = serializer.save(patient=request.user)

        # Envoyer une notification push aux médecins et secouristes
        description = alert.description[:50] if alert.description else "Urgence signalée"
        push_service.send_to_roles(
            roles=['medecin', 'secourist', 'patient', 'doctor'],
            title="🚨 Alerte SOS",
            body=f"Urgence signalée : {description}",
            data={"type": "emergency", "alertId": str(alert.id)}
        )

        # TODO: Déclencher la notification WebSocket aux secouristes disponibles

        return Response({
            'success': True,
            'message': 'Alerte d\'urgence créée avec succès.',
            'data': EmergencyAlertSerializer(alert).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emergency_alert_list(request):
    """
    Liste les alertes d'urgence.
    - Pour un patient : ses propres alertes
    - Pour un secouriste : les alertes qui lui sont assignées

    GET /api/v1/urgences/alerts/
    """
    if request.user.role == 'secourist':
        # Secouriste voit ses alertes assignées
        try:
            secourist = Secourist.objects.get(user=request.user)
            alerts = EmergencyAlert.objects.filter(secourist=secourist)
        except Secourist.DoesNotExist:
            alerts = EmergencyAlert.objects.none()
    else:
        # Patient voit ses propres alertes
        alerts = EmergencyAlert.objects.filter(patient=request.user)

    paginator = PageNumberPagination()
    paginated_alerts = paginator.paginate_queryset(alerts, request)
    serializer = EmergencyAlertSerializer(paginated_alerts, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emergency_alert_detail(request, alert_id):
    """
    Récupère les détails d'une alerte d'urgence.

    GET /api/v1/urgences/alerts/:id/
    """
    alert = get_object_or_404(EmergencyAlert, id=alert_id)

    # Vérifier les permissions
    if request.user.role == 'secourist':
        # Secouriste doit être assigné à cette alerte
        try:
            secourist = Secourist.objects.get(user=request.user)
            if alert.secourist != secourist:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'permission_denied',
                        'message': 'Vous n\'avez pas accès à cette alerte.',
                        'details': {}
                    }
                }, status=status.HTTP_403_FORBIDDEN)
        except Secourist.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': 'Vous n\'avez pas de profil de secouriste.',
                    'details': {}
                }
            }, status=status.HTTP_403_FORBIDDEN)
    else:
        # Patient doit être le propriétaire
        if alert.patient != request.user:
            return Response({
                'success': False,
                'error': {
                    'code': 'permission_denied',
                    'message': 'Vous n\'avez pas accès à cette alerte.',
                    'details': {}
                }
            }, status=status.HTTP_403_FORBIDDEN)

    serializer = EmergencyAlertSerializer(alert)
    return Response({
        'success': True,
        'message': 'Alerte récupérée avec succès.',
        'data': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsSecourist])
def emergency_alert_assign(request, alert_id):
    """
    Assigne une alerte d'urgence au secouriste connecté.

    PATCH /api/v1/urgences/alerts/:id/assign/
    """
    alert = get_object_or_404(EmergencyAlert, id=alert_id)
    secourist = get_object_or_404(Secourist, user=request.user)

    # Vérifier que l'alerte est en attente
    if alert.status != 'pending':
        return Response({
            'success': False,
            'error': {
                'code': 'invalid_status',
                'message': 'Cette alerte n\'est plus disponible.',
                'details': {}
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # Vérifier que le secouriste est disponible
    if not secourist.is_available:
        return Response({
            'success': False,
            'error': {
                'code': 'unavailable',
                'message': 'Vous n\'êtes pas disponible.',
                'details': {}
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # Assigner l'alerte
    alert.secourist = secourist
    alert.status = 'assigned'
    alert.assigned_at = timezone.now()
    alert.save()

    # TODO: Notifier le patient via WebSocket

    serializer = EmergencyAlertSerializer(alert)
    return Response({
        'success': True,
        'message': 'Alerte assignée avec succès.',
        'data': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsSecourist])
def emergency_alert_update_status(request, alert_id):
    """
    Met à jour le statut d'une alerte d'urgence.

    PATCH /api/v1/urgences/alerts/:id/status/
    """
    alert = get_object_or_404(EmergencyAlert, id=alert_id)
    secourist = get_object_or_404(Secourist, user=request.user)

    # Vérifier que le secouriste est assigné à cette alerte
    if alert.secourist != secourist:
        return Response({
            'success': False,
            'error': {
                'code': 'permission_denied',
                'message': 'Vous n\'êtes pas assigné à cette alerte.',
                'details': {}
            }
        }, status=status.HTTP_403_FORBIDDEN)

    serializer = EmergencyAlertSerializer(alert, data=request.data, partial=True)

    if serializer.is_valid():
        # Si l'alerte est résolue, enregistrer la date de résolution
        if request.data.get('status') == 'resolved':
            alert.resolved_at = timezone.now()

        serializer.save()

        # TODO: Notifier le patient via WebSocket

        return Response({
            'success': True,
            'message': 'Alerte mise à jour avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    return Response({
        'success': False,
        'error': {
            'code': 'validation_error',
            'message': 'Les données fournies sont invalides.',
            'details': serializer.errors
        }
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsSecourist])
def emergency_alert_pending(request):
    """
    Liste toutes les alertes d'urgence en attente (non assignées).

    GET /api/v1/urgences/alerts/pending/
    """
    alerts = EmergencyAlert.objects.filter(status='pending').order_by('-priority', '-created_at')

    paginator = PageNumberPagination()
    paginated_alerts = paginator.paginate_queryset(alerts, request)
    serializer = EmergencyAlertSerializer(paginated_alerts, many=True)

    return paginator.get_paginated_response(serializer.data)
