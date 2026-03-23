from django.apps import AppConfig


class SmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sms"

    def ready(self):
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            try:
                from .scheduler import start_scheduler
                start_scheduler()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f'Scheduler start error: {e}')
