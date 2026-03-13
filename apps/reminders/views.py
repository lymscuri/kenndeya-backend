"""
Vues pour l'application reminders.
Gère les rappels SMS.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404

from core.permissions import IsDoctor
from .models import SmsReminder
from .serializers import SmsReminderSerializer


@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def sms_reminder_list_create(request):
    """
    Liste tous les rappels SMS du médecin ou crée un nouveau rappel.

    GET /api/v1/reminders/sms/
    POST /api/v1/reminders/sms/
    """
    if request.method == 'GET':
        reminders = SmsReminder.objects.filter(doctor=request.user)

        # Filtres optionnels
        status_filter = request.query_params.get('status')
        if status_filter:
            reminders = reminders.filter(status=status_filter)

        paginator = PageNumberPagination()
        paginated_reminders = paginator.paginate_queryset(reminders, request)
        serializer = SmsReminderSerializer(paginated_reminders, many=True)

        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = SmsReminderSerializer(data=request.data)

        if serializer.is_valid():
            reminder = serializer.save(doctor=request.user)

            return Response({
                'success': True,
                'message': 'Rappel SMS créé avec succès.',
                'data': SmsReminderSerializer(reminder).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Les données fournies sont invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsDoctor])
def sms_reminder_detail(request, reminder_id):
    """
    Récupère, modifie ou supprime un rappel SMS.

    GET /api/v1/reminders/sms/:id/
    PATCH /api/v1/reminders/sms/:id/
    DELETE /api/v1/reminders/sms/:id/
    """
    reminder = get_object_or_404(SmsReminder, id=reminder_id, doctor=request.user)

    if request.method == 'GET':
        serializer = SmsReminderSerializer(reminder)
        return Response({
            'success': True,
            'message': 'Rappel SMS récupéré avec succès.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        # Ne peut pas modifier un rappel déjà envoyé
        if reminder.status == 'sent':
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_status',
                    'message': 'Impossible de modifier un rappel déjà envoyé.',
                    'details': {}
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = SmsReminderSerializer(reminder, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Rappel SMS mis à jour avec succès.',
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

    elif request.method == 'DELETE':
        # Ne peut pas supprimer un rappel déjà envoyé
        if reminder.status == 'sent':
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_status',
                    'message': 'Impossible de supprimer un rappel déjà envoyé.',
                    'details': {}
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        reminder.status = 'cancelled'
        reminder.save()

        return Response({
            'success': True,
            'message': 'Rappel SMS annulé avec succès.',
            'data': {}
        }, status=status.HTTP_200_OK)
