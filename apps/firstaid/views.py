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

Classification (POST classify/ et answer/) : le modèle de langage ne fait que
RECONNAÎTRE (un id de protocole publiable, ou une clé d'option). Aucun texte
qu'il produit n'est jamais renvoyé ; voir classify.py. Réponses non mises en cache.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.throttling import ScopedAnonThrottle

from .classify import ClassifierUnavailable, answer_text, classify_text
from .lang import detect_lang
from .loader import registry
from .schema import LANGS

logger = logging.getLogger('apps.firstaid.views')

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

TEXT_MAX_CHARS = 1000
OPTIONS_MIN, OPTIONS_MAX = 2, 8
OPTION_LABEL_MAX = 120
OPTION_KEY_RE = re.compile(r'^[a-z][a-z0-9_]{0,31}$')


def _error(code: str, message: str, details: dict[str, Any] | None = None, http=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': {'code': code, 'message': message, 'details': details or {}}},
                    status=http)


ERR_BODY = ('body_invalid', 'Le corps doit être un objet JSON. / The body must be a JSON object.')
ERR_TEXT = ('text_required', "Le champ « text » est obligatoire (chaîne non vide). / "
                             "The 'text' field is required (non-empty string).")
ERR_TEXT_LONG = ('text_too_long', f'« text » dépasse {TEXT_MAX_CHARS} caractères. / '
                                  f"'text' exceeds {TEXT_MAX_CHARS} characters.")
ERR_LANG = ('lang_invalid', "« lang » vaut « fr », « en » ou null. / 'lang' must be 'fr', 'en' or null.")
ERR_LANG_UNDET = ('lang_undetermined', "Langue indéterminable : précisez « lang » (« fr » ou « en »). / "
                                       "Language could not be determined: provide 'lang' ('fr' or 'en').")
ERR_OPTIONS = ('options_invalid', "« options » : objet de 2 à 8 clés (a-z, 0-9, _) vers des libellés non vides. / "
                                  "'options': object of 2 to 8 keys (a-z, 0-9, _) to non-empty labels.")
ERR_UNAVAILABLE = ('classifier_unavailable', 'Classification indisponible, choisissez le scénario dans la liste. / '
                                             'Classification unavailable, pick the scenario from the list.')


def _no_store(response: Response) -> Response:
    response['Cache-Control'] = 'no-store'
    return response


def _parse_text_and_lang(request):
    """
    Valide {text, lang} du corps. Retourne (text, lang, None) ou (None, None, Response d'erreur).
    lang absent/null → détection heuristique (sans modèle) ; indécidable → 400 lang_undetermined.
    """
    body = request.data
    if not isinstance(body, dict):
        return None, None, _error(*ERR_BODY)
    text = body.get('text')
    if not isinstance(text, str) or not text.strip():
        return None, None, _error(*ERR_TEXT)
    if len(text) > TEXT_MAX_CHARS:
        return None, None, _error(*ERR_TEXT_LONG, {'max_chars': TEXT_MAX_CHARS, 'length': len(text)})
    text = text.strip()
    lang = body.get('lang')
    if lang is None:
        lang = detect_lang(text)
        if lang is None:
            return None, None, _error(*ERR_LANG_UNDET, {'allowed': list(LANGS)})
    elif lang not in LANGS:
        return None, None, _error(*ERR_LANG, {'allowed': list(LANGS)})
    return text, lang, None


def _parse_options(body) -> dict[str, str] | None:
    options = body.get('options')
    if not isinstance(options, dict) or not OPTIONS_MIN <= len(options) <= OPTIONS_MAX:
        return None
    for key, label in options.items():
        if not isinstance(key, str) or not OPTION_KEY_RE.match(key) or key == 'unclear':
            return None
        if not isinstance(label, str) or not label.strip() or len(label) > OPTION_LABEL_MAX:
            return None
    return {k: v.strip() for k, v in options.items()}


def _summary(protocol, lang: str) -> dict[str, Any]:
    return {
        'id': protocol.id,
        'title': protocol.title.get(lang),
        'description': protocol.description.get(lang),
        'version': protocol.version,
        'status': protocol.status,
    }


class FirstaidThrottle(ScopedAnonThrottle):
    scope = 'firstaid'   # taux dans REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']


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


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([FirstaidThrottle])
def classify(request):
    """POST /api/v1/firstaid/classify/ {text, lang?} — reconnaît un scénario parmi les protocoles publiables."""
    text, lang, err = _parse_text_and_lang(request)
    if err is not None:
        return _no_store(err)
    try:
        result = classify_text(text, lang)
    except ClassifierUnavailable as exc:
        logger.warning('firstaid classify indisponible : %s', exc)
        return _no_store(_error(*ERR_UNAVAILABLE, http=status.HTTP_503_SERVICE_UNAVAILABLE))
    data = {
        'lang': lang,
        'scenario': result.scenario,
        'confidence': result.confidence,
        'protocol': _summary(result.protocol, lang) if result.protocol is not None else None,
        'emergency_number': str(settings.EMERGENCY_NUMBER),
    }
    return _no_store(Response({'success': True, 'data': data}))


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([FirstaidThrottle])
def answer(request):
    """POST /api/v1/firstaid/answer/ {text, lang?, options} — convertit une réponse libre en clé d'option."""
    text, lang, err = _parse_text_and_lang(request)
    if err is not None:
        return _no_store(err)
    options = _parse_options(request.data)
    if options is None:
        return _no_store(_error(*ERR_OPTIONS))
    try:
        key, confidence, _used_model = answer_text(text, lang, options)
    except ClassifierUnavailable as exc:
        logger.warning('firstaid answer indisponible : %s', exc)
        return _no_store(_error(*ERR_UNAVAILABLE, http=status.HTTP_503_SERVICE_UNAVAILABLE))
    return _no_store(Response({'success': True, 'data': {'lang': lang, 'answer': key, 'confidence': confidence}}))
