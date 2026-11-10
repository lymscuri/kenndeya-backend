"""
Préchauffage du cache des lieux d'urgence : l'app ne dépend plus d'Overpass
en temps réel. Pour chaque point de EMERGENCY_PLACES_WARM_POINTS, get_places()
est appelé avec le rayon par défaut et 15 km ; les appels réels à Overpass
sont espacés de WARM_SPACING_S (respect des miroirs publics).

Un verrou dans le cache (clé + TTL) garantit une seule exécution à la fois,
que le déclencheur soit le scheduler (lancé dans chaque worker gunicorn, donc
en double) ou la commande manuelle warm_emergency_places.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from .places import RADIUS_DEFAULT, get_places

logger = logging.getLogger('apps.urgences.warm')

WARM_RADII = (RADIUS_DEFAULT, 15000)
WARM_SPACING_S = 10            # entre deux appels réels à Overpass
WARM_INTERVAL_HOURS = 4        # période du job planifié
WARM_FIRST_DELAY_S = 120       # premier passage après le démarrage
LOCK_KEY = 'places:warm:lock'
LOCK_TTL = 30 * 60             # au-delà, un verrou orphelin (worker tué) expire


@dataclass(frozen=True)
class WarmPoint:
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class WarmReport:
    point: str
    radius: int
    source: str          # cache | live | stale | referential_only | error
    count: int
    seconds: float


def parse_points(raw) -> list[WarmPoint]:
    """"nom:lat:lon" → WarmPoint ; une entrée mal formée est journalisée et ignorée."""
    points = []
    for item in raw or ():
        try:
            name, lat, lon = str(item).rsplit(':', 2)
            lat, lon = float(lat), float(lon)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not name.strip():
                raise ValueError
        except ValueError:
            logger.error('warm : point ignoré, format attendu "nom:lat:lon" : %r', item)
            continue
        points.append(WarmPoint(name.strip(), lat, lon))
    return points


def warm_points() -> list[WarmPoint]:
    return parse_points(getattr(settings, 'EMERGENCY_PLACES_WARM_POINTS', []))


def acquire_lock() -> bool:
    """cache.add est atomique (Redis SETNX, locmem verrouillé) : un seul gagnant."""
    return bool(cache.add(LOCK_KEY, time.time(), LOCK_TTL))


def release_lock() -> None:
    cache.delete(LOCK_KEY)


def warm_all(points: list[WarmPoint] | None = None, sleep=None) -> list[WarmReport] | None:
    """
    Préchauffe tous les points. Retourne les rapports, ou None si une autre
    exécution détient le verrou. Un échec sur un point n'arrête pas les autres.
    """
    if not acquire_lock():
        logger.warning('warm : déjà en cours (verrou %s), exécution ignorée', LOCK_KEY)
        return None
    reports: list[WarmReport] = []
    sleep = sleep or time.sleep          # résolu à l'appel (remplaçable dans les tests)
    try:
        points = warm_points() if points is None else points
        for point in points:
            for radius in WARM_RADII:
                t0 = time.monotonic()
                try:
                    result = get_places(point.lat, point.lon, radius)
                    report = WarmReport(point.name, radius, result.source, len(result.places),
                                        round(time.monotonic() - t0, 1))
                    logger.info('warm %s r=%d source=%s lieux=%d durée=%.1fs',
                                point.name, radius, result.source, len(result.places), report.seconds)
                except Exception as exc:  # noqa: BLE001 — un point en échec n'arrête pas les autres
                    report = WarmReport(point.name, radius, 'error', 0, round(time.monotonic() - t0, 1))
                    logger.error('warm %s r=%d ÉCHEC %s: %s', point.name, radius, exc.__class__.__name__, exc)
                reports.append(report)
                if report.source != 'cache':        # un appel réel a eu lieu (ou a échoué) : on espace
                    sleep(WARM_SPACING_S)
    finally:
        release_lock()
    return reports


def scheduled_warm() -> None:
    """Point d'entrée du scheduler APScheduler (apps/sms/scheduler.py)."""
    try:
        reports = warm_all()
    except Exception as exc:  # noqa: BLE001
        logger.error('warm planifié : erreur inattendue %s: %s', exc.__class__.__name__, exc)
        return
    if reports is not None:
        logger.info('warm planifié terminé : %d appels, sources=%s', len(reports),
                    sorted({r.source for r in reports}))
