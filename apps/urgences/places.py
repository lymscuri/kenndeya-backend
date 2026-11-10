"""
Lieux d'urgence « autour de moi » : OpenStreetMap (Overpass) + référentiel Hospital.

Exécuté côté serveur à la place de l'appel direct de l'app à Overpass :
- miroirs Overpass en repli, timeout, User-Agent identifié, 429 respecté ;
- cache 6 h par cellule géographique (~1 km) + copie « stale » 7 jours ;
- préchauffage périodique des villes (warm.py) : l'app ne dépend plus d'Overpass en temps réel ;
- Overpass en échec → stale si disponible, sinon référentiel seul.
  Jamais de 5xx tant que la base répond.

Le cache ne contient que la partie OSM ; le référentiel (Hospital, is_active)
est lu à chaque requête et fusionné : un hôpital de la base à moins de 60 m
d'un lieu OSM de même nature l'absorbe, ses champs renseignés gagnent.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('apps.urgences.places')

KINDS = ('hospital', 'clinic', 'pharmacy', 'health_center')
RADIUS_DEFAULT = 5000
RADIUS_MAX = 25000
MERGE_DISTANCE_M = 60
CACHE_TTL = 6 * 3600              # cache frais ; le préchauffage toutes les 4 h le renouvelle avant expiration
STALE_TTL = 7 * 24 * 3600         # copie stale : couvre une longue panne d'Overpass
CACHE_VERSION = 'v1'
OVERPASS_TIMEOUT_DEFAULT = 8      # secondes par miroir (réglage EMERGENCY_PLACES_TIMEOUT)
OVERPASS_MIRRORS = (
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
    # PAS overpass.osm.ch : il ne couvre que la Suisse (0 élément partout ailleurs, trompeur).
)

# Noms génériques pour les lieux OSM sans nom : en urgence, une pharmacie sans
# nom reste une pharmacie. Localisés à la réponse, jamais stockés en cache.
GENERIC_NAMES = {
    'fr': {'hospital': 'Hôpital (sans nom)', 'clinic': 'Clinique (sans nom)',
           'pharmacy': 'Pharmacie (sans nom)', 'health_center': 'Centre de santé (sans nom)'},
    'en': {'hospital': 'Hospital (unnamed)', 'clinic': 'Clinic (unnamed)',
           'pharmacy': 'Pharmacy (unnamed)', 'health_center': 'Health centre (unnamed)'},
}

# Natures compatibles pour la fusion : même kind, ou hôpital/clinique entre eux.
_COMPATIBLE = {('hospital', 'clinic'), ('clinic', 'hospital')}


class OverpassError(Exception):
    """Tous les miroirs ont échoué (timeout, 429, 5xx, JSON invalide)."""


# ------------------------------------------------------------------------------
# Géométrie
# ------------------------------------------------------------------------------

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en mètres entre deux points (rayon terrestre moyen 6 371 km)."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cell_key(lat: float, lon: float, radius: int) -> str:
    """Cellule ~1 km (arrondi à 0,01°) + rayon : clé de cache partagée par le voisinage."""
    return f'places:{CACHE_VERSION}:{round(lat, 2):.2f}:{round(lon, 2):.2f}:{radius}'


def stale_key(key: str) -> str:
    return key.replace(f'places:{CACHE_VERSION}:', f'places:{CACHE_VERSION}:stale:', 1)


# ------------------------------------------------------------------------------
# Overpass
# ------------------------------------------------------------------------------

def overpass_query(lat: float, lon: float, radius: int) -> str:
    """Même requête que l'app mobile : hôpitaux, pharmacies, cliniques, out center."""
    return (
        '[out:json][timeout:25];\n(\n'
        f'  node["amenity"="hospital"](around:{radius},{lat},{lon});\n'
        f'  way["amenity"="hospital"](around:{radius},{lat},{lon});\n'
        f'  relation["amenity"="hospital"](around:{radius},{lat},{lon});\n'
        f'  node["amenity"="pharmacy"](around:{radius},{lat},{lon});\n'
        f'  way["amenity"="pharmacy"](around:{radius},{lat},{lon});\n'
        f'  node["amenity"="clinic"](around:{radius},{lat},{lon});\n'
        f'  way["amenity"="clinic"](around:{radius},{lat},{lon});\n'
        ');\nout center body;'
    )


def overpass_timeout() -> float:
    return float(getattr(settings, 'EMERGENCY_PLACES_TIMEOUT', OVERPASS_TIMEOUT_DEFAULT))


def _user_agent() -> str:
    contact = getattr(settings, 'EMERGENCY_PLACES_CONTACT', '')
    return f'KendeyaBackend/1.0 (application de santé, Guinée; contact: {contact})'


def fetch_overpass(lat: float, lon: float, radius: int) -> list[dict[str, Any]]:
    """
    Interroge les miroirs dans l'ordre, un essai chacun (un 429 n'est jamais
    réessayé sur le même miroir). Retourne les éléments bruts ou lève OverpassError.
    """
    query = overpass_query(lat, lon, radius)
    headers = {'User-Agent': _user_agent(), 'Accept': 'application/json'}
    for mirror in OVERPASS_MIRRORS:
        try:
            resp = requests.post(mirror, data={'data': query}, headers=headers, timeout=overpass_timeout())
        except requests.RequestException as exc:
            logger.warning('overpass échec miroir=%s erreur=%s', mirror, exc.__class__.__name__)
            continue
        if resp.status_code != 200:
            logger.warning('overpass échec miroir=%s code=%s', mirror, resp.status_code)
            continue
        try:
            elements = resp.json().get('elements')
        except ValueError:
            logger.warning('overpass échec miroir=%s erreur=JSON invalide', mirror)
            continue
        if not isinstance(elements, list):
            logger.warning('overpass échec miroir=%s erreur=réponse sans elements', mirror)
            continue
        return elements
    raise OverpassError('tous les miroirs Overpass ont échoué')


def _tri(value: str | None, yes: tuple[str, ...], no: tuple[str, ...]) -> bool | None:
    """True / False / None (inconnu) — jamais False par défaut."""
    if value is None:
        return None
    if value in yes:
        return True
    if value in no:
        return False
    return None


def osm_to_places(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convertit les éléments Overpass au format commun. name=None si sans nom (gardé)."""
    places = []
    for el in elements:
        tags = el.get('tags') or {}
        lat = el.get('lat', (el.get('center') or {}).get('lat'))
        lon = el.get('lon', (el.get('center') or {}).get('lon'))
        if lat is None or lon is None or el.get('type') not in ('node', 'way', 'relation'):
            continue
        amenity = tags.get('amenity')
        kind = amenity if amenity in ('hospital', 'clinic', 'pharmacy') else None
        if kind is None:
            continue
        parts = []
        if tags.get('addr:street'):
            if tags.get('addr:housenumber'):
                parts.append(tags['addr:housenumber'])
            parts.append(tags['addr:street'])
        if tags.get('addr:city'):
            parts.append(tags['addr:city'])
        address = ', '.join(parts) if parts else (tags.get('addr:full') or None)
        opening = tags.get('opening_hours')
        healthcare = ' '.join(filter(None, (tags.get('healthcare'), tags.get('healthcare:speciality')))).lower()
        has_maternity = True if any(w in healthcare for w in ('maternity', 'obstetric', 'birthing', 'midwife')) else None
        places.append({
            'id': f"osm:{el['type']}:{el['id']}",
            'name': tags.get('name') or tags.get('name:fr') or tags.get('name:en') or None,
            'kind': kind,
            'lat': float(lat),
            'lon': float(lon),
            'address': address,
            'phone': tags.get('phone') or tags.get('contact:phone') or None,
            'is_24h': True if opening == '24/7' else (False if opening else None),
            'has_emergency': _tri(tags.get('emergency'), ('yes',), ('no',)),
            'has_maternity': has_maternity,
            'origin': 'osm',
        })
    return places


# ------------------------------------------------------------------------------
# Référentiel Hospital
# ------------------------------------------------------------------------------

_REF_KIND = {'public': 'hospital', 'private': 'hospital', 'clinic': 'clinic', 'health_center': 'health_center'}


def referential_places(lat: float, lon: float, radius: int) -> list[dict[str, Any]]:
    """Hôpitaux actifs géolocalisés de la base, dans le rayon."""
    from .models import Hospital
    places = []
    qs = Hospital.objects.filter(is_active=True, latitude__isnull=False, longitude__isnull=False)
    for h in qs:
        hlat, hlon = float(h.latitude), float(h.longitude)
        if haversine_m(lat, lon, hlat, hlon) > radius:
            continue
        address = ', '.join(p for p in (h.address.strip(), h.city.strip()) if p) or None
        places.append({
            'id': f'ref:{h.id}',
            'name': h.name,
            'kind': _REF_KIND.get(h.hospital_type, 'hospital'),
            'lat': hlat,
            'lon': hlon,
            'address': address,
            'phone': h.phone or None,
            'is_24h': None,                    # inconnu du référentiel : jamais False par défaut
            'has_emergency': h.has_emergency_room,
            'has_maternity': h.has_maternity,
            'origin': 'referential',
        })
    return places


# ------------------------------------------------------------------------------
# Fusion
# ------------------------------------------------------------------------------

_MERGE_FIELDS = ('name', 'phone', 'address', 'is_24h', 'has_emergency', 'has_maternity')


def _compatible(kind_a: str, kind_b: str) -> bool:
    return kind_a == kind_b or (kind_a, kind_b) in _COMPATIBLE


def merge_places(referential: list[dict[str, Any]], osm: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Un lieu du référentiel à moins de MERGE_DISTANCE_M d'un lieu OSM de nature
    compatible absorbe ce lieu (le plus proche, une seule fois) → origin "merged".
    Pour chaque champ, le référentiel gagne s'il est renseigné (non None / non
    vide), OSM complète le reste. Position et id : ceux du référentiel.
    """
    remaining = list(osm)
    merged = []
    for ref in referential:
        best, best_d = None, MERGE_DISTANCE_M
        for o in remaining:
            if not _compatible(ref['kind'], o['kind']):
                continue
            d = haversine_m(ref['lat'], ref['lon'], o['lat'], o['lon'])
            if d <= best_d:
                best, best_d = o, d
        if best is None:
            merged.append(dict(ref))
            continue
        remaining.remove(best)
        place = dict(ref)
        for field in _MERGE_FIELDS:
            if ref.get(field) in (None, ''):
                place[field] = best.get(field)
        place['origin'] = 'merged'
        merged.append(place)
    return merged + remaining


# ------------------------------------------------------------------------------
# Orchestration : cache → Overpass → stale → référentiel seul
# ------------------------------------------------------------------------------

@dataclass(frozen=True)
class PlacesResult:
    places: list[dict[str, Any]]
    source: str            # cache | live | stale | referential_only
    generated_at: str      # ISO 8601 UTC de la collecte OSM (ou de la réponse)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _osm_places(lat: float, lon: float, radius: int) -> tuple[list[dict[str, Any]], str, str]:
    """(lieux OSM, source, generated_at) — lève OverpassError seulement sans aucun cache."""
    key = cell_key(lat, lon, radius)
    entry = cache.get(key)
    if entry is not None:
        return entry['places'], 'cache', entry['generated_at']
    try:
        places = osm_to_places(fetch_overpass(lat, lon, radius))
    except OverpassError:
        stale = cache.get(stale_key(key))
        if stale is not None:
            logger.warning('overpass indisponible : service de la copie stale %s', key)
            return stale['places'], 'stale', stale['generated_at']
        raise
    entry = {'places': places, 'generated_at': _now_iso()}
    cache.set(key, entry, CACHE_TTL)
    cache.set(stale_key(key), entry, STALE_TTL)
    return places, 'live', entry['generated_at']


def get_places(lat: float, lon: float, radius: int, lang: str = 'fr') -> PlacesResult:
    """Lieux fusionnés, localisés, triés par distance, avec la source effective."""
    referential = referential_places(lat, lon, radius)
    try:
        osm, source, generated_at = _osm_places(lat, lon, radius)
    except OverpassError:
        logger.warning('overpass indisponible et aucun cache : référentiel seul')
        osm, source, generated_at = [], 'referential_only', _now_iso()
    places = merge_places(referential, osm)
    names = GENERIC_NAMES.get(lang, GENERIC_NAMES['fr'])
    out = []
    for p in places:
        p = dict(p)
        if not p.get('name'):
            p['name'] = names[p['kind']]
        p['distance_m'] = int(round(haversine_m(lat, lon, p['lat'], p['lon'])))
        p['lat'] = round(p['lat'], 6)
        p['lon'] = round(p['lon'], 6)
        out.append(p)
    out.sort(key=lambda p: (p['distance_m'], p['id']))
    return PlacesResult(out, source, generated_at)
