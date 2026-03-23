from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import SMSReminder
from .serializers import SMSReminderSerializer, CreateSMSReminderSerializer
from .utils import send_sms

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def reminder_list_create(request):
    if request.method == 'GET':
        reminders = SMSReminder.objects.filter(doctor=request.user)
        serializer = SMSReminderSerializer(reminders, many=True)
        return Response({'success': True, 'data': serializer.data})

    serializer = CreateSMSReminderSerializer(data=request.data)
    if serializer.is_valid():
        reminder = serializer.save(doctor=request.user)
        return Response({
            'success': True,
            'message': 'Rappel SMS planifié avec succès.',
            'data': SMSReminderSerializer(reminder).data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'success': False,
        'error': {'code': 'validation_error', 'details': serializer.errors}
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def reminder_detail(request, reminder_id):
    try:
        reminder = SMSReminder.objects.get(id=reminder_id, doctor=request.user)
    except SMSReminder.DoesNotExist:
        return Response({'success': False, 'error': 'Rappel introuvable'}, status=404)

    if request.method == 'DELETE':
        reminder.status = 'annule'
        reminder.save()
        return Response({'success': True, 'message': 'Rappel annulé'})

    if request.method == 'PATCH':
        serializer = CreateSMSReminderSerializer(reminder, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'data': SMSReminderSerializer(reminder).data})
        return Response({'success': False, 'error': serializer.errors}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_immediate_sms(request):
    """Envoyer un SMS immédiatement."""
    phone = request.data.get('phone')
    message = request.data.get('message')
    patient_name = request.data.get('patient_name', '')

    if not phone or not message:
        return Response({
            'success': False,
            'error': 'phone et message sont requis'
        }, status=400)

    result = send_sms(phone, message)

    if result['success']:
        # Enregistrer en DB
        SMSReminder.objects.create(
            doctor=request.user,
            patient_phone=phone,
            patient_name=patient_name,
            reminder_type='consultation',
            message=message,
            scheduled_at=timezone.now(),
            sent_at=timezone.now(),
            status='envoye'
        )
        return Response({'success': True, 'message': 'SMS envoyé avec succès'})

    return Response({
        'success': False,
        'error': result.get('error', 'Échec envoi SMS')
    }, status=500)
