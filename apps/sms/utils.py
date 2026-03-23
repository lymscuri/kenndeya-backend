from twilio.rest import Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_sms(to_phone: str, message: str) -> dict:
    """Envoyer un SMS via Twilio."""
    try:
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        msg = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        return {'success': True, 'sid': msg.sid}
    except Exception as e:
        logger.error(f'SMS send error: {str(e)}')
        return {'success': False, 'error': str(e)}

def process_pending_reminders():
    """Traiter les rappels planifiés — appelé par le scheduler."""
    from django.utils import timezone
    from .models import SMSReminder

    now = timezone.now()
    pending = SMSReminder.objects.filter(
        status='planifie',
        scheduled_at__lte=now
    )

    sent = 0
    failed = 0

    for reminder in pending:
        result = send_sms(reminder.patient_phone, reminder.message)
        if result['success']:
            reminder.status = 'envoye'
            reminder.sent_at = now
            sent += 1
        else:
            reminder.status = 'echec'
            reminder.error_message = result.get('error', '')
            failed += 1
        reminder.save()

    logger.info(f'SMS processed: {sent} sent, {failed} failed')
    return {'sent': sent, 'failed': failed}
