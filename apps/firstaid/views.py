"""
Endpoints publics, lecture seule, des protocoles de premiers secours.

Règles absolues :
- Seul registry.publishable_protocols() est consulté. Un brouillon répond 404,
  indiscernable d'un identifiant inexistant.
- `lang` est obligatoire et vaut exactement 'fr' ou 'en'. Pas de lecture de
  Accept-Language, pas de langue par défaut : 400 bilingue sinon.
- Le payload public ne contient pas review_notes ; validated_by est réduit à
  {name, qualification, date}.
- AllowAny, aucune base de données, aucun appel à un modèle de langage.
- Cache-Control public 1 h, ETag calculé depuis (id, version, lang).
"""

from __future__ import annotations

import hashlib
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .loader import registry
from .schema import LANGS

CACHE_MAX_AGE = 3600  # les protocoles ne changent qu'avec un déploiement

LANG_ERROR = {
    'success': False,
    'error': {
        'code': 'lang_required',
        'message': "Le paramètre « lang » est obligatoire et vaut « fr » ou « en ». "
                   "/ The 'lang' parameter is required and must be 'fr' or 'en'.",
        'details': {'allowed': list(LANGS)},
    },
}

NOT_FOUND = {
    'success': False,
    'error': {'code': 'not_found', 'message': 'Protocole introuvable. / Protocol not found.', 'details': {}},
}


class FirstaidThrottle(ScopedRateThrottle):
    scope = 'firstaid'


def _lang(request) -> str | None:
    """Langue demandée, ou None si absente ou invalide (strict, sensible à la casse)."""
    lang = request.query_params.get('lang')
    return lang if lang in LANGS else None


def _etag(*parts: Any) -> str:
    raw = '|'.join(str(p) for p in parts).encode('utf-8')
    return '"' + hashlib.sha256(raw).hexdigest()[:32] + '"'


def _cached(response: Response, etag: str, request) -> Response:
    """Ajoute Cache-Control et ETag ; répond 304 si le client a déjà cette version."""
    if request.headers.get('If-None-Match') == etag:
        response = Response(status=status.HTTP_304_NOT_MODIFIED)
    response['ETag'] = etag
    response['Cache-Control'] = f'public, max-age={CACHE_MAX_AGE}'
    response['Vary'] = 'Accept'
    return response


def _public_payload(view: dict[str, Any], protocol) -> dict[str, Any]:
    """Vue localisée expurgée pour le public (retraits faits ici, pas dans localized())."""
    payload = dict(view)
    payload.pop('review_notes', None)
    payload['validated_by'] = [
        {'name': v.name, 'qualification': v.qualification, 'date': v.date.isoformat()}
        for v in protocol.validated_by
    ]
    payload['emergency_number'] = str(settings.EMERGENCY_NUMBER)
    return payload


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([FirstaidThrottle])
def protocol_list(request):
    """GET /api/v1/firstaid/protocols/?lang=fr|en — protocoles publiables, résumé."""
    lang = _lang(request)
    if lang is None:
        return Response(LANG_ERROR, status=status.HTTP_400_BAD_REQUEST)
    protocols = registry.publishable_protocols()
    results = []
    for pid in sorted(protocols):
        p = protocols[pid]
        results.append({
            'id': p.id,
            'title': p.title.get(lang),
            'description': p.description.get(lang),
            'version': p.version,
            'updated_at': p.updated_at.isoformat(),
            'status': p.status,          # même chaîne que dans le détail (bandeau « données de test »)
            'variants': {k: v.get(lang) for k, v in p.variants.items()},
        })
    etag = _etag('list', lang, *(f'{p.id}:{p.version}:{p.status}' for p in (protocols[k] for k in sorted(protocols))))
    return _cached(Response({'success': True, 'count': len(results), 'results': results}), etag, request)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([FirstaidThrottle])
def protocol_detail(request, protocol_id: str):
    """GET /api/v1/firstaid/protocols/<id>/?lang=fr|en — protocole complet dans une langue."""
    lang = _lang(request)
    if lang is None:
        return Response(LANG_ERROR, status=status.HTTP_400_BAD_REQUEST)
    protocol = registry.get_publishable(protocol_id)
    if protocol is None:
        return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
    payload = _public_payload(protocol.localized(lang), protocol)
    etag = _etag(protocol.id, protocol.version, lang)
    return _cached(Response({'success': True, 'message': 'Protocole.', 'data': payload}), etag, request)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([FirstaidThrottle])
def meta(request):
    """GET /api/v1/firstaid/meta/?lang=fr|en — numéro d'urgence, langues, nombre de protocoles."""
    lang = _lang(request)
    if lang is None:
        return Response(LANG_ERROR, status=status.HTTP_400_BAD_REQUEST)
    protocols = registry.publishable_protocols()
    data = {
        'emergency_number': str(settings.EMERGENCY_NUMBER),
        'languages': list(LANGS),
        'protocol_count': len(protocols),
        'lang': lang,
    }
    etag = _etag('meta', lang, settings.EMERGENCY_NUMBER,
                 *(f'{p.id}:{p.version}' for p in (protocols[k] for k in sorted(protocols))))
    return _cached(Response({'success': True, 'message': 'Méta.' if lang == 'fr' else 'Meta.', 'data': data}),
                   etag, request)
