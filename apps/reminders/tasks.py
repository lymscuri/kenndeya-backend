"""
Tâches Celery pour l'application reminders.
Gère l'envoi automatique des rappels SMS.
"""

from celery import shared_task
from django.utils import timezone
from .models import SmsReminder


@shared_task(name='reminders.send_sms_reminder')
def send_sms_reminder(reminder_id):
    """
    Envoie un SMS de rappel à un patient.

    Cette tâche est appelée par Celery Beat selon le planning configuré.
    """
    try:
        reminder = SmsReminder.objects.get(id=reminder_id)

        # Vérifier que le rappel est toujours en attente
        if reminder.status != 'pending':
            return f"Rappel {reminder_id} - Statut: {reminder.status} (ignoré)"

        # TODO: Intégration avec un service SMS (Twilio, Vonage, etc.)
        # Pour le moment, on simule l'envoi

        # Exemple d'intégration Twilio (commenté):
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     body=reminder.message,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=reminder.phone_number
        # )

        # Marquer le rappel comme envoyé
        reminder.status = 'sent'
        reminder.sent_at = timezone.now()
        reminder.save()

        return f"SMS envoyé avec succès à {reminder.phone_number}"

    except SmsReminder.DoesNotExist:
        return f"Rappel {reminder_id} introuvable"
    except Exception as e:
        # Marquer le rappel comme échoué
        try:
            reminder = SmsReminder.objects.get(id=reminder_id)
            reminder.status = 'failed'
            reminder.error_message = str(e)
            reminder.save()
        except:
            pass

        return f"Erreur lors de l'envoi du SMS: {str(e)}"


@shared_task(name='reminders.process_pending_sms')
def process_pending_sms():
    """
    Tâche périodique qui traite tous les SMS en attente dont la date d'envoi est passée.

    Cette tâche doit être configurée dans Celery Beat pour s'exécuter toutes les minutes.
    """
    now = timezone.now()

    # Récupérer tous les rappels en attente dont la date d'envoi est passée
    pending_reminders = SmsReminder.objects.filter(
        status='pending',
        scheduled_at__lte=now
    )

    count = 0
    for reminder in pending_reminders:
        # Lancer la tâche d'envoi pour chaque rappel
        send_sms_reminder.delay(str(reminder.id))
        count += 1

    return f"{count} rappels SMS envoyés en file d'attente"


@shared_task(name='reminders.cleanup_old_sms')
def cleanup_old_sms():
    """
    Nettoie les anciens rappels SMS (plus de 90 jours).

    Cette tâche doit être configurée dans Celery Beat pour s'exécuter quotidiennement.
    """
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=90)

    # Supprimer les rappels envoyés ou annulés de plus de 90 jours
    deleted_count = SmsReminder.objects.filter(
        status__in=['sent', 'cancelled'],
        created_at__lt=cutoff_date
    ).delete()[0]

    return f"{deleted_count} anciens rappels SMS supprimés"
