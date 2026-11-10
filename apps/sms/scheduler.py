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
    # Préchauffage du cache des lieux d'urgence (apps.urgences.warm) : même
    # scheduler, même cycle de vie. Chaque worker gunicorn lance ce scheduler ;
    # le verrou dans le cache (warm_all) garantit une seule exécution à la fois.
    from datetime import datetime, timedelta
    from apps.urgences.warm import WARM_FIRST_DELAY_S, WARM_INTERVAL_HOURS, scheduled_warm
    _scheduler.add_job(
        scheduled_warm,
        trigger=IntervalTrigger(hours=WARM_INTERVAL_HOURS),
        next_run_time=datetime.now() + timedelta(seconds=WARM_FIRST_DELAY_S),
        id='warm_emergency_places',
        replace_existing=True,
        max_instances=1,
    )
    # Import hebdomadaire des lieux de santé OSM (apps.urgences.osm_import) :
    # dimanche 03:00 UTC, pays EMERGENCY_PLACES_COUNTRIES, verrou cache (un seul worker).
    from apscheduler.triggers.cron import CronTrigger
    from apps.urgences.osm_import import scheduled_import
    _scheduler.add_job(
        scheduled_import,
        trigger=CronTrigger(day_of_week='sun', hour=3, minute=0, timezone='UTC'),
        id='import_osm_health',
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info('SMS Scheduler started — checking every 30 minutes')
    logger.info('Emergency places warm-up scheduled — first run in %ds, then every %dh',
                WARM_FIRST_DELAY_S, WARM_INTERVAL_HOURS)
    logger.info('OSM health places import scheduled — every Sunday 03:00 UTC')

def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
