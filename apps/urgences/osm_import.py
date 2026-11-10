"""
Import des lieux de santé OpenStreetMap par pays (extrait Geofabrik .osm.pbf)
dans OsmHealthPlace. Remplace Overpass en temps réel pour les pays importés.

Parse en trois passes avec pyosmium, sans index de localisation en mémoire
(un extrait pays compte des dizaines de millions de nœuds ; seuls ceux des
lieux retenus sont gardés) :
1. relations de santé → ways membres ;
2. ways de santé + ways membres → nœuds nécessaires ;
3. nœuds : lieux ponctuels, et coordonnées des nœuds nécessaires.
Position d'un way / d'une relation : moyenne des nœuds (centroïde simple).

Verrou dans le cache (clé + TTL), même mécanisme que warm.py : une seule
exécution à la fois, scheduler ou commande manuelle.
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .places import (
    KINDS, address_from_tags, emergency_from_tags, maternity_from_tags,
    name_from_tags, phone_from_tags,
)

logger = logging.getLogger('apps.urgences.osm_import')

GEOFABRIK_URL = 'https://download.geofabrik.de/africa/{slug}-latest.osm.pbf'
# Code ISO 3166-1 alpha-2 → extrait Geofabrik (extensible).
COUNTRY_SLUGS = {
    'GN': 'guinea', 'ET': 'ethiopia', 'SN': 'senegal', 'ML': 'mali', 'SL': 'sierra-leone',
    'LR': 'liberia', 'CI': 'ivory-coast', 'GW': 'guinea-bissau',
}
AMENITY_KINDS = {'hospital': 'hospital', 'clinic': 'clinic', 'pharmacy': 'pharmacy', 'doctors': 'clinic'}
HEALTHCARE_KINDS = {
    'hospital': 'hospital', 'clinic': 'clinic', 'pharmacy': 'pharmacy', 'doctor': 'clinic',
    'centre': 'health_center', 'center': 'health_center', 'health_post': 'health_center',
    'birthing_centre': 'health_center', 'midwife': 'health_center',
}
DOWNLOAD_TIMEOUT = (15, 120)     # (connexion, lecture) en secondes
DOWNLOAD_CHUNK = 1 << 20
LOCK_KEY = 'places:import:lock'
LOCK_TTL = 2 * 3600              # un import complet dure quelques minutes ; verrou orphelin expiré au-delà
BATCH = 500


class ImportError_(Exception):
    """Téléchargement ou parse impossible pour un pays (les autres continuent)."""


@dataclass
class ImportReport:
    country: str
    downloaded_bytes: int = 0
    download_seconds: float = 0.0
    parse_seconds: float = 0.0
    by_kind: dict[str, int] = field(default_factory=dict)
    created: int = 0
    updated: int = 0
    deleted: int = 0
    error: str | None = None

    @property
    def total(self) -> int:
        return sum(self.by_kind.values())


# ------------------------------------------------------------------------------
# Tags → champs
# ------------------------------------------------------------------------------

def kind_from_tags(tags: dict[str, str]) -> str | None:
    """amenity= prime, puis healthcare= ; None si ce n'est pas un lieu de santé retenu."""
    kind = AMENITY_KINDS.get(tags.get('amenity', ''))
    if kind is None:
        kind = HEALTHCARE_KINDS.get(tags.get('healthcare', ''))
    return kind if kind in KINDS else None


def place_fields(tags: dict[str, str]) -> dict[str, Any]:
    """Champs dérivés (règles tri-état : jamais False par défaut)."""
    emergency = emergency_from_tags(tags)
    is_24h = True if (tags.get('opening_hours') == '24/7' or emergency is True) else None
    return {
        'name': name_from_tags(tags),
        'phone': phone_from_tags(tags) or '',
        'address': address_from_tags(tags) or '',
        'is_24h': is_24h,
        'has_emergency': emergency,
        'has_maternity': maternity_from_tags(tags),
    }


# ------------------------------------------------------------------------------
# Téléchargement
# ------------------------------------------------------------------------------

def _user_agent() -> str:
    contact = getattr(settings, 'EMERGENCY_PLACES_CONTACT', '')
    return f'KendeyaBackend/1.0 (import OSM santé; contact: {contact})'


def geofabrik_url(country: str) -> str:
    slug = COUNTRY_SLUGS.get(country.upper())
    if slug is None:
        raise ImportError_(f'pays {country!r} inconnu (connus : {", ".join(sorted(COUNTRY_SLUGS))})')
    return GEOFABRIK_URL.format(slug=slug)


def download_pbf(country: str, dest_dir: str) -> tuple[str, int]:
    """Télécharge l'extrait dans dest_dir ; retourne (chemin, octets). Lève ImportError_."""
    url = geofabrik_url(country)
    path = os.path.join(dest_dir, f'{country.lower()}-latest.osm.pbf')
    size = 0
    try:
        with requests.get(url, headers={'User-Agent': _user_agent()}, stream=True,
                          timeout=DOWNLOAD_TIMEOUT) as resp:
            if resp.status_code != 200:
                raise ImportError_(f'téléchargement {url} : HTTP {resp.status_code}')
            with open(path, 'wb') as fh:
                for chunk in resp.iter_content(chunk_size=DOWNLOAD_CHUNK):
                    fh.write(chunk)
                    size += len(chunk)
    except requests.RequestException as exc:
        raise ImportError_(f'téléchargement {url} : {exc.__class__.__name__}') from exc
    if size == 0:
        raise ImportError_(f'téléchargement {url} : fichier vide')
    return path, size


# ------------------------------------------------------------------------------
# Parse (pyosmium, trois passes)
# ------------------------------------------------------------------------------

def parse_pbf(path: str) -> list[dict[str, Any]]:
    """
    Lieux de santé d'un fichier .osm.pbf : liste de dicts
    {osm_id, kind, lat, lon, tags, + place_fields}. Un way/relation sans aucun
    nœud localisable est ignoré (journalisé).
    """
    import osmium

    # Passe 1 : relations de santé → ways membres (nœuds membres directs aussi)
    relations: dict[int, dict[str, Any]] = {}
    member_ways: set[int] = set()
    for rel in osmium.FileProcessor(path, osmium.osm.RELATION):
        tags = dict(rel.tags)
        if kind_from_tags(tags) is None:
            continue
        ways = [m.ref for m in rel.members if m.type == 'w']
        nodes = [m.ref for m in rel.members if m.type == 'n']
        relations[rel.id] = {'tags': tags, 'ways': ways, 'nodes': nodes}
        member_ways.update(ways)

    # Passe 2 : ways de santé + ways membres → nœuds nécessaires
    ways: dict[int, dict[str, Any]] = {}        # ways de santé
    way_nodes: dict[int, list[int]] = {}        # ways membres de relations
    needed: set[int] = set()
    for rel in relations.values():
        needed.update(rel['nodes'])
    for way in osmium.FileProcessor(path, osmium.osm.WAY):
        refs = None
        if way.id in member_ways:
            refs = [n.ref for n in way.nodes]
            way_nodes[way.id] = refs
            needed.update(refs)
        tags = dict(way.tags)
        if kind_from_tags(tags) is not None:
            refs = refs if refs is not None else [n.ref for n in way.nodes]
            ways[way.id] = {'tags': tags, 'nodes': refs}
            needed.update(refs)

    # Passe 3 : nœuds de santé + coordonnées des nœuds nécessaires
    coords: dict[int, tuple[float, float]] = {}
    places: list[dict[str, Any]] = []
    for node in osmium.FileProcessor(path, osmium.osm.NODE):
        if not node.location.valid():
            continue
        if node.id in needed:
            coords[node.id] = (node.location.lat, node.location.lon)
        tags = dict(node.tags)
        kind = kind_from_tags(tags)
        if kind is not None:
            places.append(_place('node', node.id, kind, node.location.lat, node.location.lon, tags))

    def centroid(refs: list[int]) -> tuple[float, float] | None:
        pts = [coords[r] for r in dict.fromkeys(refs) if r in coords]
        if not pts:
            return None
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    for wid, way in ways.items():
        c = centroid(way['nodes'])
        if c is None:
            logger.warning('import osm : way/%d sans nœud localisable, ignoré', wid)
            continue
        places.append(_place('way', wid, kind_from_tags(way['tags']), c[0], c[1], way['tags']))
    for rid, rel in relations.items():
        refs = list(rel['nodes'])
        for wid in rel['ways']:
            refs.extend(way_nodes.get(wid, ()))
        c = centroid(refs)
        if c is None:
            logger.warning('import osm : relation/%d sans nœud localisable, ignorée', rid)
            continue
        places.append(_place('relation', rid, kind_from_tags(rel['tags']), c[0], c[1], rel['tags']))
    return places


def _place(otype: str, oid: int, kind: str, lat: float, lon: float, tags: dict[str, str]) -> dict[str, Any]:
    return {'osm_id': f'{otype}/{oid}', 'kind': kind, 'lat': float(lat), 'lon': float(lon),
            'tags': tags, **place_fields(tags)}


# ------------------------------------------------------------------------------
# Upsert
# ------------------------------------------------------------------------------

_UPDATE_FIELDS = ('kind', 'name', 'lat', 'lon', 'phone', 'address', 'is_24h', 'has_emergency',
                  'has_maternity', 'country', 'tags', 'imported_at')


def upsert_places(country: str, places: list[dict[str, Any]], report: ImportReport) -> None:
    """Upsert par osm_id, puis suppression des lieux du pays absents de l'import. Transactionnel."""
    from .models import OsmHealthPlace
    now = timezone.now()
    with transaction.atomic():
        existing = {p.osm_id: p for p in OsmHealthPlace.objects.filter(osm_id__in=[p['osm_id'] for p in places])}
        to_create, to_update = [], []
        for data in places:
            row = existing.get(data['osm_id'])
            if row is None:
                to_create.append(OsmHealthPlace(country=country, imported_at=now, **data))
                continue
            for k, v in data.items():
                setattr(row, k, v)
            row.country, row.imported_at = country, now
            to_update.append(row)
        OsmHealthPlace.objects.bulk_create(to_create, batch_size=BATCH)
        OsmHealthPlace.objects.bulk_update(to_update, _UPDATE_FIELDS, batch_size=BATCH)
        deleted, _ = OsmHealthPlace.objects.filter(country=country).exclude(
            osm_id__in=[p['osm_id'] for p in places]).delete()
    report.created, report.updated, report.deleted = len(to_create), len(to_update), deleted


# ------------------------------------------------------------------------------
# Orchestration + verrou
# ------------------------------------------------------------------------------

def acquire_lock() -> bool:
    return bool(cache.add(LOCK_KEY, time.time(), LOCK_TTL))


def release_lock() -> None:
    cache.delete(LOCK_KEY)


def countries_setting() -> list[str]:
    return [c.strip().upper() for c in getattr(settings, 'EMERGENCY_PLACES_COUNTRIES', []) if c.strip()]


def import_country(country: str) -> ImportReport:
    """Télécharge, parse, upsert un pays. Le fichier temporaire est toujours supprimé."""
    country = country.upper()
    report = ImportReport(country)
    tmp = tempfile.mkdtemp(prefix='kendeya-osm-')
    try:
        t0 = time.monotonic()
        path, report.downloaded_bytes = download_pbf(country, tmp)
        report.download_seconds = round(time.monotonic() - t0, 1)
        logger.info('import osm %s : %.1f Mo téléchargés en %.1fs', country,
                    report.downloaded_bytes / 1e6, report.download_seconds)
        t1 = time.monotonic()
        places = parse_pbf(path)
        report.parse_seconds = round(time.monotonic() - t1, 1)
        report.by_kind = dict(sorted(Counter(p['kind'] for p in places).items()))
        upsert_places(country, places, report)
        logger.info('import osm %s : %d lieux (%s) en %.1fs — créés=%d mis à jour=%d supprimés=%d',
                    country, report.total,
                    ', '.join(f'{k}={v}' for k, v in report.by_kind.items()) or 'aucun',
                    report.parse_seconds, report.created, report.updated, report.deleted)
    finally:
        for name in os.listdir(tmp):
            try:
                os.remove(os.path.join(tmp, name))
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
    return report


def import_all(countries: list[str] | None = None) -> list[ImportReport] | None:
    """
    Importe chaque pays ; un échec n'arrête pas les autres. Retourne les
    rapports, ou None si une autre exécution détient le verrou.
    """
    if not acquire_lock():
        logger.warning('import osm : déjà en cours (verrou %s), exécution ignorée', LOCK_KEY)
        return None
    reports: list[ImportReport] = []
    try:
        for country in (countries_setting() if countries is None else countries):
            try:
                reports.append(import_country(country))
            except Exception as exc:  # noqa: BLE001 — un pays en échec n'arrête pas les autres
                report = ImportReport(country.upper(), error=f'{exc.__class__.__name__}: {exc}')
                logger.error('import osm %s ÉCHEC %s', report.country, report.error)
                reports.append(report)
    finally:
        release_lock()
    return reports


def scheduled_import() -> None:
    """Point d'entrée du scheduler APScheduler (apps/sms/scheduler.py), hebdomadaire."""
    try:
        reports = import_all()
    except Exception as exc:  # noqa: BLE001
        logger.error('import osm planifié : erreur inattendue %s: %s', exc.__class__.__name__, exc)
        return
    if reports is not None:
        logger.info('import osm planifié terminé : %s',
                    ', '.join(f'{r.country}={r.total if r.error is None else "ÉCHEC"}' for r in reports) or 'aucun pays')
