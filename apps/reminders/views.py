"""
apps/reminders/views.py — Vues Reminders Kendeya
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsDoctor
from .models import SmsReminder
from .serializers import SmsReminderSerializer


@api_view(['GET', 'POST'])
@permission_classes([IsDoctor])
def sms_reminder_list_create(request):
    """
    GET  /api/v1/reminders/sms/ — Liste rappels du médecin
    POST /api/v1/reminders/sms/ — Créer un rappel
    """
    if request.method == 'GET':
        reminders = SmsReminder.objects.filter(doctor=request.user)

        status_filter = request.query_params.get('status')
        if status_filter:
            reminders = reminders.filter(status=status_filter)

        type_filter = request.query_params.get('type')
        if type_filter:
            reminders = reminders.filter(reminder_type=type_filter)

        paginator = PageNumberPagination()
        paginated = paginator.paginate_queryset(reminders, request)
        serializer = SmsReminderSerializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    # POST
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
    GET    /api/v1/reminders/sms/:id/
    PATCH  /api/v1/reminders/sms/:id/
    DELETE /api/v1/reminders/sms/:id/
    """
    reminder = get_object_or_404(SmsReminder, id=reminder_id, doctor=request.user)

    if request.method == 'GET':
        return Response({
            'success': True,
            'data': SmsReminderSerializer(reminder).data
        })

    if request.method == 'PATCH':
        if reminder.status == 'sent':
            return Response({
                'success': False,
                'error': {'code': 'invalid_status', 'message': 'Impossible de modifier un rappel déjà envoyé.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = SmsReminderSerializer(reminder, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'data': serializer.data})

        return Response({
            'success': False,
            'error': {'code': 'validation_error', 'details': serializer.errors}
        }, status=status.HTTP_400_BAD_REQUEST)

    # DELETE → annuler
    if reminder.status == 'sent':
        return Response({
            'success': False,
            'error': {'message': 'Impossible de supprimer un rappel déjà envoyé.'}
        }, status=status.HTTP_400_BAD_REQUEST)

    reminder.status = 'cancelled'
    reminder.save()
    return Response({'success': True, 'message': 'Rappel annulé.'})


@api_view(['POST'])
@permission_classes([IsDoctor])
def send_reminder_now(request, reminder_id):
    """
    POST /api/v1/reminders/sms/:id/send/ — Envoyer immédiatement
    """
    reminder = get_object_or_404(SmsReminder, id=reminder_id, doctor=request.user)

    if reminder.status == 'sent':
        return Response({
            'success': False,
            'error': {'message': 'Ce rappel a déjà été envoyé.'}
        }, status=status.HTTP_400_BAD_REQUEST)

    # Envoi via Celery (asynchrone)
    from .tasks import send_single_reminder
    send_single_reminder.delay(str(reminder.id))

    return Response({
        'success': True,
        'message': 'SMS en cours d\'envoi...',
    })


@api_view(['POST'])
@permission_classes([IsDoctor])
def create_vaccination_reminder(request):
    """
    POST /api/v1/reminders/vaccination/
    Crée un rappel vaccin enfant avec message automatique.
    """
    from .services import build_vaccination_message

    child_name  = request.data.get('child_name', '')
    vaccine     = request.data.get('vaccine_name', '')
    target_age  = request.data.get('target_age', '')
    phone       = request.data.get('phone_number', '')
    scheduled   = request.data.get('scheduled_at', '')
    patient_id  = request.data.get('patient_id')

    if not all([phone, scheduled]):
        return Response({
            'success': False,
            'error': {'message': 'Champs obligatoires : phone_number, scheduled_at'}
        }, status=status.HTTP_400_BAD_REQUEST)

    patient = request.user
    if patient_id:
        try:
            from apps.accounts.models import User
            patient = User.objects.get(id=patient_id)
        except Exception:
            pass

    message = build_vaccination_message(child_name, vaccine, target_age)

    reminder = SmsReminder.objects.create(
        patient=patient,
        doctor=request.user,
        reminder_type='vaccination',
        phone_number=phone,
        message=message,
        scheduled_at=scheduled,
    )

    return Response({
        'success': True,
        'message': 'Rappel vaccination créé.',
        'data': SmsReminderSerializer(reminder).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsDoctor])
def create_prenatal_reminder(request):
    """
    POST /api/v1/reminders/prenatal/
    Crée un rappel consultation prénatale avec message automatique.
    """
    from .services import build_prenatal_message

    patient_name = request.data.get('patient_name', '')
    week         = request.data.get('week', '')
    date_str     = request.data.get('date', '')
    phone        = request.data.get('phone_number', '')
    scheduled    = request.data.get('scheduled_at', '')
    patient_id   = request.data.get('patient_id')

    if not all([phone, scheduled]):
        return Response({
            'success': False,
            'error': {'message': 'Champs obligatoires : phone_number, scheduled_at'}
        }, status=status.HTTP_400_BAD_REQUEST)

    patient = request.user
    if patient_id:
        try:
            from apps.accounts.models import User
            patient = User.objects.get(id=patient_id)
        except Exception:
            pass

    message = build_prenatal_message(patient_name, week, date_str)

    reminder = SmsReminder.objects.create(
        patient=patient,
        doctor=request.user,
        reminder_type='prenatal',
        phone_number=phone,
        message=message,
        scheduled_at=scheduled,
    )

    return Response({
        'success': True,
        'message': 'Rappel prénatal créé.',
        'data': SmsReminderSerializer(reminder).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsDoctor])
def create_appointment_reminder(request):
    """
    POST /api/v1/reminders/appointment/
    Crée un rappel RDV médecin avec message automatique.
    """
    from .services import build_appointment_message

    patient_name = request.data.get('patient_name', '')
    date_str     = request.data.get('date', '')
    phone        = request.data.get('phone_number', '')
    scheduled    = request.data.get('scheduled_at', '')
    patient_id   = request.data.get('patient_id')

    if not all([phone, scheduled]):
        return Response({
            'success': False,
            'error': {'message': 'Champs obligatoires : phone_number, scheduled_at'}
        }, status=status.HTTP_400_BAD_REQUEST)

    patient = request.user
    if patient_id:
        try:
            from apps.accounts.models import User
            patient = User.objects.get(id=patient_id)
        except Exception:
            pass

    doctor_name = request.user.get_full_name()
    message = build_appointment_message(patient_name, doctor_name, date_str)

    reminder = SmsReminder.objects.create(
        patient=patient,
        doctor=request.user,
        reminder_type='appointment',
        phone_number=phone,
        message=message,
        scheduled_at=scheduled,
    )

    return Response({
        'success': True,
        'message': 'Rappel RDV créé.',
        'data': SmsReminderSerializer(reminder).data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reminders_stats(request):
    """GET /api/v1/reminders/stats/ — Statistiques rappels."""
    reminders = SmsReminder.objects.filter(doctor=request.user)
    return Response({
        'success': True,
        'data': {
            'total':      reminders.count(),
            'pending':    reminders.filter(status='pending').count(),
            'sent':       reminders.filter(status='sent').count(),
            'failed':     reminders.filter(status='failed').count(),
            'cancelled':  reminders.filter(status='cancelled').count(),
        }
    })