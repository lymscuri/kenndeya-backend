from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)
_scheduler = None

def start_scheduler():
    """Démarrer le scheduler APScheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    from .utils import process_pending_reminders

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        process_pending_reminders,
        trigger=IntervalTrigger(minutes=30),
        id='process_sms_reminders',
        replace_existing=True,
    )
    _scheduler.start()
    logger.info('SMS Scheduler started — checking every 30 minutes')

def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
