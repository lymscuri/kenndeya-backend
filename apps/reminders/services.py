"""
apps/reminders/services.py — Service Twilio pour Kendeya
Gère l'envoi des SMS via l'API Twilio.
"""
 
import logging
from django.conf import settings
 
logger = logging.getLogger(__name__)
 
 
class TwilioSMSService:
    """Service d'envoi de SMS via Twilio."""
 
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token  = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        self._client     = None
 
    @property
    def client(self):
        if not self._client:
            from twilio.rest import Client
            self._client = Client(self.account_sid, self.auth_token)
        return self._client
 
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number)
 
    def send_sms(self, to_number: str, message: str) -> dict:
        """
        Envoie un SMS via Twilio.
        Retourne : { success, message_sid, error }
        """
        if not self.is_configured():
            logger.error('[Twilio] Service non configuré — variables manquantes.')
            return {'success': False, 'error': 'Service SMS non configuré.'}
 
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number,
            )
            logger.info(f'[Twilio] SMS envoyé à {to_number} — SID: {msg.sid}')
            return {'success': True, 'message_sid': msg.sid}
 
        except Exception as e:
            error_msg = str(e)
            logger.error(f'[Twilio] Échec envoi SMS à {to_number} : {error_msg}')
            return {'success': False, 'error': error_msg}
 
 
# ---------------------------------------------------------------------------
# Templates de messages SMS
# ---------------------------------------------------------------------------
 
def build_vaccination_message(child_name: str, vaccine_name: str, target_age: str) -> str:
    return (
        f"🏥 Kendeya — Rappel vaccination\n"
        f"Le vaccin {vaccine_name} de {child_name} est prévu à {target_age}.\n"
        f"Rendez-vous dans votre centre de santé le plus proche.\n"
        f"Pour infos : Kendeya Santé"
    )
 
 
def build_prenatal_message(patient_name: str, week: int, scheduled_date: str) -> str:
    return (
        f"🏥 Kendeya — Consultation prénatale\n"
        f"Bonjour {patient_name}, votre consultation prénatale de la semaine {week} "
        f"est prévue le {scheduled_date}.\n"
        f"Merci de ne pas manquer ce rendez-vous important.\n"
        f"Kendeya Santé"
    )
 
 
def build_appointment_message(patient_name: str, doctor_name: str, date: str) -> str:
    return (
        f"🏥 Kendeya — Rappel RDV\n"
        f"Bonjour {patient_name}, votre rendez-vous avec Dr. {doctor_name} "
        f"est prévu le {date}.\n"
        f"En cas d'empêchement, contactez votre médecin.\n"
        f"Kendeya Santé"
    )
 
 
# Instance globale
sms_service = TwilioSMSService()
 