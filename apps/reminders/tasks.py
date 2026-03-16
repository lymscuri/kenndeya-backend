"""
apps/reminders/tasks.py — Tâches Celery pour Kendeya
Envoi automatique des rappels SMS planifiés.
"""
 
import logging
from celery import shared_task
from django.utils import timezone
 
logger = logging.getLogger(__name__)
 
 
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_pending_reminders(self):
    """
    Tâche Celery Beat — exécutée toutes les heures.
    Envoie tous les rappels SMS dont la date est atteinte.
    """
    from .models import SmsReminder
    from .services import sms_service
 
    now = timezone.now()
 
    # Récupérer tous les rappels en attente dont l'heure est passée
    pending = SmsReminder.objects.filter(
        status='pending',
        scheduled_at__lte=now,
    ).select_related('patient', 'doctor')
 
    if not pending.exists():
        logger.info('[Reminders] Aucun rappel SMS à envoyer.')
        return {'sent': 0, 'failed': 0}
 
    sent_count   = 0
    failed_count = 0
 
    for reminder in pending:
        result = sms_service.send_sms(
            to_number=reminder.phone_number,
            message=reminder.message,
        )
 
        if result['success']:
            reminder.status  = 'sent'
            reminder.sent_at = timezone.now()
            reminder.save(update_fields=['status', 'sent_at', 'updated_at'])
            sent_count += 1
            logger.info(f'[Reminders] SMS envoyé — ID: {reminder.id}')
        else:
            reminder.status        = 'failed'
            reminder.error_message = result.get('error', 'Erreur inconnue')
            reminder.save(update_fields=['status', 'error_message', 'updated_at'])
            failed_count += 1
            logger.warning(f'[Reminders] SMS échoué — ID: {reminder.id} — {reminder.error_message}')
 
    logger.info(f'[Reminders] Résultat : {sent_count} envoyés, {failed_count} échoués.')
    return {'sent': sent_count, 'failed': failed_count}
 
 
@shared_task
def send_single_reminder(reminder_id: str):
    """
    Envoie un rappel SMS immédiatement (envoi manuel).
    """
    from .models import SmsReminder
    from .services import sms_service
    import uuid
 
    try:
        reminder = SmsReminder.objects.get(id=uuid.UUID(reminder_id))
    except SmsReminder.DoesNotExist:
        logger.error(f'[Reminders] Rappel introuvable : {reminder_id}')
        return {'success': False, 'error': 'Rappel introuvable'}
 
    if reminder.status == 'sent':
        return {'success': False, 'error': 'Rappel déjà envoyé'}
 
    result = sms_service.send_sms(
        to_number=reminder.phone_number,
        message=reminder.message,
    )
 
    if result['success']:
        reminder.status  = 'sent'
        reminder.sent_at = timezone.now()
        reminder.save(update_fields=['status', 'sent_at', 'updated_at'])
        logger.info(f'[Reminders] SMS envoyé manuellement — ID: {reminder_id}')
    else:
        reminder.status        = 'failed'
        reminder.error_message = result.get('error', 'Erreur inconnue')
        reminder.save(update_fields=['status', 'error_message', 'updated_at'])
        logger.warning(f'[Reminders] SMS manuel échoué — ID: {reminder_id}')
 
    return result
 