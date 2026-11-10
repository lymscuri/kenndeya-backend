"""
Tests de GET /api/v1/emergency/places/ — requests mocké, aucun réseau.
"""

from unittest import mock

import requests
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Hospital
from .places import OVERPASS_MIRRORS, cell_key, haversine_m

URL = '/api/v1/emergency/places/'
LAT, LON = 9.5370, -13.6785          # Conakry


class _Resp:
    def __init__(self, status_code=200, payload=None, bad_json=False):
        self.status_code = status_code
        self._payload = payload
        self._bad = bad_json

    def json(self):
        if self._bad:
            raise ValueError('JSON invalide')
        return self._payload


def _node(i, lat, lon, amenity, **tags):
    return {'type': 'node', 'id': i, 'lat': lat, 'lon': lon, 'tags': {'amenity': amenity, **tags}}


def _way(i, lat, lon, amenity, **tags):
    return {'type': 'way', 'id': i, 'center': {'lat': lat, 'lon': lon}, 'tags': {'amenity': amenity, **tags}}


# Décalages : 0.001° de latitude ≈ 111 m
ELEMENTS = [
    _way(20, LAT + 0.010, LON, 'hospital', name='Hôpital National Donka', opening_hours='24/7', emergency='yes'),
    _node(10, LAT + 0.001, LON, 'pharmacy'),                                          # sans nom, la plus proche
    _node(30, LAT + 0.004, LON, 'clinic', name='Clinique Pasteur', phone='+224 620 00 00 00',
          **{'addr:street': 'Rue KA 020', 'addr:city': 'Conakry', 'opening_hours': 'Mo-Fr 08:00-18:00'}),
]


class PlacesApiTests(TestCase):

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.calls = []
        patcher = mock.patch('apps.urgences.places.requests.post', side_effect=self._post)
        self.post = patcher.start()
        self.addCleanup(patcher.stop)
        self.responses = [_Resp(200, {'elements': ELEMENTS})]      # une réponse par miroir, dans l'ordre

    def _post(self, url, **kw):
        self.calls.append((url, kw))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def get(self, **params):
        return self.client.get(URL, {'lat': LAT, 'lon': LON, **params})

    # --- paramètres ---------------------------------------------------------------

    def test_params_validation(self):
        cases = [
            ({}, 'coordinates_required'), ({'lat': LAT}, 'coordinates_required'),
            ({'lat': 'abc', 'lon': LON}, 'coordinates_invalid'), ({'lat': 95, 'lon': LON}, 'coordinates_invalid'),
            ({'lat': LAT, 'lon': 181}, 'coordinates_invalid'), ({'lat': 'nan', 'lon': LON}, 'coordinates_invalid'),
            ({'lat': LAT, 'lon': LON, 'radius': 30000}, 'radius_invalid'),
            ({'lat': LAT, 'lon': LON, 'radius': 0}, 'radius_invalid'),
            ({'lat': LAT, 'lon': LON, 'radius': 'abc'}, 'radius_invalid'),
            ({'lat': LAT, 'lon': LON, 'lang': 'de'}, 'lang_invalid'),
        ]
        for params, code in cases:
            r = self.client.get(URL, params)
            self.assertEqual(r.status_code, 400, params)
            self.assertEqual(r.json()['error']['code'], code, params)
            self.assertIn(' / ', r.json()['error']['message'])        # bilingue
        self.assertEqual(self.calls, [])

    # --- contenu ----------------------------------------------------------------------

    def test_sorted_by_distance_unnamed_kept_and_fields(self):
        r = self.get()
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()['data']
        self.assertEqual(data['source'], 'live')
        self.assertEqual(data['center'], {'lat': LAT, 'lon': LON})
        self.assertEqual(data['radius'], 5000)
        self.assertTrue(data['generated_at'].endswith('+00:00'))
        self.assertEqual(r['Cache-Control'], 'no-store')
        places = data['places']
        self.assertEqual([p['id'] for p in places], ['osm:node:10', 'osm:node:30', 'osm:way:20'])
        self.assertEqual([p['distance_m'] for p in places], sorted(p['distance_m'] for p in places))
        self.assertEqual(set(places[0]), {'id', 'name', 'kind', 'lat', 'lon', 'distance_m', 'address', 'phone',
                                          'is_24h', 'has_emergency', 'has_maternity', 'origin'})
        pharmacy, clinic, hospital = places
        self.assertEqual(pharmacy['name'], 'Pharmacie (sans nom)')          # sans nom : gardée
        self.assertEqual(pharmacy['kind'], 'pharmacy')
        self.assertAlmostEqual(pharmacy['distance_m'], 111, delta=2)
        self.assertIsNone(pharmacy['is_24h'])                                # inconnu, jamais False par défaut
        self.assertIsNone(pharmacy['has_emergency'])
        self.assertIsNone(pharmacy['has_maternity'])
        self.assertEqual(pharmacy['origin'], 'osm')
        self.assertEqual(clinic['address'], 'Rue KA 020, Conakry')
        self.assertEqual(clinic['phone'], '+224 620 00 00 00')
        self.assertIs(clinic['is_24h'], False)                                # horaires connus, pas 24/7
        self.assertEqual(hospital['name'], 'Hôpital National Donka')
        self.assertIs(hospital['is_24h'], True)
        self.assertIs(hospital['has_emergency'], True)
        # requête Overpass : celle de l'app, User-Agent identifié avec contact
        url, kw = self.calls[0]
        self.assertEqual(url, OVERPASS_MIRRORS[0])
        self.assertIn('node["amenity"="hospital"](around:5000,', kw['data']['data'])
        self.assertIn('out center body;', kw['data']['data'])
        self.assertIn('Kendeya', kw['headers']['User-Agent'])
        self.assertIn('contact: ', kw['headers']['User-Agent'])
        self.assertEqual(kw['timeout'], 8.0)                                   # EMERGENCY_PLACES_TIMEOUT par défaut

    def test_generic_name_in_english(self):
        r = self.get(lang='en')
        self.assertEqual(r.json()['data']['places'][0]['name'], 'Pharmacy (unnamed)')

    def test_merge_referential_and_osm(self):
        ref = Hospital.objects.create(
            name='Hôpital National Donka', address='Dixinn', city='Conakry', phone='+224 622 11 22 33',
            hospital_type='public', has_emergency_room=True, has_maternity=True,
            latitude=LAT + 0.0102, longitude=LON,                        # ≈ 22 m du way OSM 20
        )
        far = Hospital.objects.create(
            name='Hôpital Ignace Deen', address='Kaloum', city='Conakry', phone='',
            hospital_type='public', has_emergency_room=True, has_maternity=False,
            latitude=LAT - 0.020, longitude=LON,                         # aucun lieu OSM à proximité
        )
        Hospital.objects.create(name='Inactif', address='x', city='Conakry', latitude=LAT, longitude=LON,
                                is_active=False)
        Hospital.objects.create(name='Sans coordonnées', address='x', city='Conakry')
        Hospital.objects.create(name='Hors rayon', address='x', city='Labé', latitude=11.318, longitude=-12.283)
        self.responses = [_Resp(200, {'elements': ELEMENTS + [
            _node(40, LAT + 0.0103, LON, 'pharmacy', name='Pharmacie Donka'),   # 30 m de l'hôpital : kind incompatible
        ]})]
        places = self.get().json()['data']['places']
        ids = [p['id'] for p in places]
        self.assertNotIn('osm:way:20', ids)                               # absorbé
        self.assertIn('osm:node:40', ids)                                 # pharmacie non absorbée
        self.assertEqual(len(places), 5)                                  # 3 OSM restants + merged + far
        merged = next(p for p in places if p['id'] == f'ref:{ref.id}')
        self.assertEqual(merged['origin'], 'merged')
        self.assertEqual(merged['phone'], '+224 622 11 22 33')           # référentiel gagne
        self.assertEqual(merged['name'], 'Hôpital National Donka')
        self.assertEqual(merged['address'], 'Dixinn, Conakry')
        self.assertIs(merged['is_24h'], True)                             # inconnu du référentiel → OSM complète
        self.assertIs(merged['has_emergency'], True)
        self.assertIs(merged['has_maternity'], True)
        self.assertEqual(merged['kind'], 'hospital')
        self.assertEqual((merged['lat'], merged['lon']), (round(LAT + 0.0102, 6), LON))
        alone = next(p for p in places if p['id'] == f'ref:{far.id}')
        self.assertEqual(alone['origin'], 'referential')
        self.assertIsNone(alone['phone'])
        self.assertIsNone(alone['is_24h'])                                # inconnu des deux côtés → null

    def test_merge_is_24h_null_when_unknown_to_both(self):
        ref = Hospital.objects.create(name='Clinique Pasteur', address='', city='Conakry', hospital_type='clinic',
                                      latitude=LAT + 0.004, longitude=LON + 0.0002)
        self.responses = [_Resp(200, {'elements': [_node(30, LAT + 0.004, LON, 'clinic', name='Clinique Pasteur')]})]
        places = self.get().json()['data']['places']
        self.assertEqual(len(places), 1)
        self.assertEqual(places[0]['id'], f'ref:{ref.id}')
        self.assertEqual(places[0]['origin'], 'merged')
        self.assertIsNone(places[0]['is_24h'])
        self.assertEqual(places[0]['address'], 'Conakry')

    # --- cache et résilience ---------------------------------------------------------

    def test_cache_hit(self):
        first = self.get().json()['data']
        self.assertEqual(first['source'], 'live')
        second = self.get().json()['data']
        self.assertEqual(second['source'], 'cache')
        self.assertEqual(second['generated_at'], first['generated_at'])
        self.assertEqual(second['places'], first['places'])
        self.assertEqual(len(self.calls), 1)
        # une position à 300 m partage la cellule (~1 km) : même cache
        r = self.client.get(URL, {'lat': LAT + 0.002, 'lon': LON})
        self.assertEqual(r.json()['data']['source'], 'cache')
        self.assertEqual(len(self.calls), 1)
        # un autre rayon : nouvelle collecte
        self.responses = [_Resp(200, {'elements': ELEMENTS})]
        self.assertEqual(self.get(radius=10000).json()['data']['source'], 'live')
        self.assertEqual(len(self.calls), 2)

    def test_overpass_429_serves_stale(self):
        first = self.get().json()['data']
        cache.delete(cell_key(LAT, LON, 5000))                             # entrée fraîche expirée, stale conservée
        self.responses = [_Resp(429), _Resp(429), _Resp(429)]
        with self.assertLogs('apps.urgences.places', level='WARNING') as logs:
            r = self.get()
        self.assertEqual(r.status_code, 200)
        data = r.json()['data']
        self.assertEqual(data['source'], 'stale')
        self.assertEqual(data['generated_at'], first['generated_at'])
        self.assertEqual(data['places'], first['places'])
        self.assertEqual(len(self.calls), 4)                              # 1 + un essai par miroir (3), pas de retry
        joined = '\n'.join(logs.output)
        self.assertIn('code=429', joined)
        for mirror in OVERPASS_MIRRORS:
            self.assertIn(f'miroir={mirror}', joined)

    def test_overpass_down_without_cache_serves_referential_only(self):
        ref = Hospital.objects.create(name='Hôpital Ignace Deen', address='Kaloum', city='Conakry',
                                      phone='+224 622 00 00 01', latitude=LAT - 0.005, longitude=LON)
        self.responses = [requests.ConnectionError('refusé'), requests.Timeout('délai'), _Resp(504)]
        with self.assertLogs('apps.urgences.places', level='WARNING'):
            r = self.get()
        self.assertEqual(r.status_code, 200)                              # jamais de 5xx
        data = r.json()['data']
        self.assertEqual(data['source'], 'referential_only')
        self.assertEqual([p['id'] for p in data['places']], [f'ref:{ref.id}'])
        self.assertEqual(data['places'][0]['origin'], 'referential')
        self.assertEqual(data['places'][0]['phone'], '+224 622 00 00 01')
        # rien n'est mis en cache : la prochaine requête retente Overpass
        self.responses = [_Resp(200, {'elements': ELEMENTS})]
        self.assertEqual(self.get().json()['data']['source'], 'live')

    def test_second_mirror_after_first_failure(self):
        for first in (_Resp(500), _Resp(502, bad_json=True), _Resp(200, bad_json=True),
                      _Resp(200, {'pas': 'elements'}), requests.Timeout('délai')):
            cache.clear(); self.calls.clear()
            self.responses = [first, _Resp(200, {'elements': ELEMENTS})]
            with self.assertLogs('apps.urgences.places', level='WARNING'):
                r = self.get()
            self.assertEqual(r.json()['data']['source'], 'live', first)
            self.assertEqual([c[0] for c in self.calls], list(OVERPASS_MIRRORS[:2]), first)

    def test_third_mirror_after_two_failures(self):
        self.assertEqual(len(OVERPASS_MIRRORS), 3)
        self.assertEqual(OVERPASS_MIRRORS[2], 'https://overpass.private.coffee/api/interpreter')
        self.assertFalse(any('osm.ch' in m for m in OVERPASS_MIRRORS))      # Suisse seulement : exclu
        self.responses = [_Resp(502), requests.Timeout('délai'), _Resp(200, {'elements': ELEMENTS})]
        with self.assertLogs('apps.urgences.places', level='WARNING'):
            r = self.get()
        self.assertEqual(r.json()['data']['source'], 'live')
        self.assertEqual([c[0] for c in self.calls], list(OVERPASS_MIRRORS))

    @override_settings(EMERGENCY_PLACES_TIMEOUT=3)
    def test_timeout_setting_is_passed_to_requests(self):
        self.get()
        self.assertEqual(self.calls[0][1]['timeout'], 3.0)

    def test_stale_served_after_six_hours_then_referential_only_after_seven_days(self):
        import time as _time
        from .places import CACHE_TTL, STALE_TTL
        self.assertEqual(CACHE_TTL, 6 * 3600)
        self.assertEqual(STALE_TTL, 7 * 24 * 3600)
        t0 = _time.time()
        first = self.get().json()['data']
        self.assertEqual(first['source'], 'live')
        with mock.patch('time.time', return_value=t0 + 6 * 3600 + 1):       # cache frais expiré
            self.responses = [_Resp(429), _Resp(429), _Resp(429)]
            with self.assertLogs('apps.urgences.places', level='WARNING'):
                data = self.get().json()['data']
            self.assertEqual(data['source'], 'stale')
            self.assertEqual(data['places'], first['places'])
        with mock.patch('time.time', return_value=t0 + STALE_TTL + 1):      # stale expirée aussi
            self.responses = [_Resp(429), _Resp(429), _Resp(429)]
            with self.assertLogs('apps.urgences.places', level='WARNING'):
                data = self.get().json()['data']
            self.assertEqual(data['source'], 'referential_only')

    # --- accès ---------------------------------------------------------------------------

    def test_throttle_active(self):
        with mock.patch.dict(ScopedRateThrottleRates(), {'emergency_places': '2/hour'}):
            self.assertEqual(self.get().status_code, 200)
            self.assertEqual(self.get().status_code, 200)
            self.assertEqual(self.get().status_code, 429)

    def test_public_but_hospitals_endpoint_still_authenticated(self):
        self.assertEqual(self.get().status_code, 200)                      # aucune authentification
        r = self.client.get('/api/v1/emergency/hospitals/')
        self.assertEqual(r.status_code, 401)

    def test_only_get(self):
        for method in ('post', 'put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)(URL).status_code, 405, method)


def ScopedRateThrottleRates():
    """Le dictionnaire des taux lu par les throttles DRF (partagé avec api_settings)."""
    from rest_framework.throttling import SimpleRateThrottle
    return SimpleRateThrottle.THROTTLE_RATES


class HaversineTests(TestCase):

    def test_known_distances(self):
        self.assertAlmostEqual(haversine_m(LAT, LON, LAT, LON), 0.0)
        self.assertAlmostEqual(haversine_m(LAT, LON, LAT + 0.001, LON), 111.2, delta=0.5)
        # Conakry → Labé ≈ 250 km
        self.assertAlmostEqual(haversine_m(LAT, LON, 11.318, -12.283), 250_000, delta=5_000)


# ==============================================================================
# Préchauffage (warm.py, commande warm_emergency_places, job planifié)
# ==============================================================================

from io import StringIO

from django.core.management import call_command

from . import warm
from .places import PlacesResult


class WarmTests(TestCase):

    POINTS = ['Conakry:9.537:-13.678', 'Labé:11.318:-12.283', 'Addis-Abeba:9.03:38.74']

    def setUp(self):
        cache.clear()
        self.sleeps = []
        patcher = mock.patch('apps.urgences.warm.time.sleep', side_effect=self.sleeps.append)
        patcher.start(); self.addCleanup(patcher.stop)

    def test_parse_points(self):
        pts = warm.parse_points(["N'Zérékoré:7.756:-8.818", 'mauvais', 'x:91:0', 'Labé:11.318:-12.283'])
        self.assertEqual([(p.name, p.lat, p.lon) for p in pts],
                         [("N'Zérékoré", 7.756, -8.818), ('Labé', 11.318, -12.283)])
        self.assertEqual(len(warm.warm_points()), 9)                     # défaut des réglages, Addis compris

    @override_settings(EMERGENCY_PLACES_WARM_POINTS=POINTS)
    def test_command_processes_all_points_even_if_one_fails(self):
        def fake_get_places(lat, lon, radius, lang='fr'):
            if abs(lat - 11.318) < 1e-6:
                raise RuntimeError('base indisponible')
            source = 'cache' if (lat, radius) == (9.03, 5000) else 'live'
            return PlacesResult([{'id': 'osm:node:1'}] * (2 if radius == 5000 else 5), source, 'now')
        out = StringIO()
        with mock.patch('apps.urgences.warm.get_places', side_effect=fake_get_places) as gp:
            with self.assertLogs('apps.urgences.warm', level='INFO') as logs:
                call_command('warm_emergency_places', stdout=out)
        self.assertEqual(gp.call_count, 6)                               # 3 points × 2 rayons, malgré l'échec
        self.assertEqual([c.args[2] for c in gp.call_args_list], [5000, 15000] * 3)
        text = out.getvalue()
        self.assertIn('Conakry      r=5000   source=live', text)
        self.assertIn('Labé         r=5000   source=error', text)
        self.assertIn('Addis-Abeba  r=5000   source=cache', text)
        self.assertIn('6 appels, 2 en erreur', text)
        joined = '\n'.join(logs.output)
        self.assertIn('warm Labé r=5000 ÉCHEC RuntimeError: base indisponible', joined)
        self.assertIn('warm Conakry r=15000 source=live lieux=5', joined)
        self.assertEqual(self.sleeps, [10] * 5)                          # pas d'attente après un hit cache
        self.assertIsNone(cache.get(warm.LOCK_KEY))                      # verrou relâché

    @override_settings(EMERGENCY_PLACES_WARM_POINTS=POINTS)
    def test_lock_prevents_concurrent_run(self):
        self.assertTrue(warm.acquire_lock())
        with mock.patch('apps.urgences.warm.get_places') as gp:
            with self.assertLogs('apps.urgences.warm', level='WARNING'):
                self.assertIsNone(warm.warm_all())
            gp.assert_not_called()
            with self.assertRaises(Exception) as ctx:
                call_command('warm_emergency_places', stdout=StringIO())
            self.assertIn('déjà en cours', str(ctx.exception))
            # le job planifié ne lève rien et ne fait rien non plus
            with self.assertLogs('apps.urgences.warm', level='WARNING'):
                warm.scheduled_warm()
            gp.assert_not_called()
        warm.release_lock()
        with mock.patch('apps.urgences.warm.get_places', return_value=PlacesResult([], 'live', 'now')) as gp:
            self.assertEqual(len(warm.warm_all()), 6)
            self.assertEqual(gp.call_count, 6)

    def test_lock_released_even_on_unexpected_error(self):
        with mock.patch('apps.urgences.warm.warm_points', side_effect=RuntimeError('boum')):
            with self.assertRaises(RuntimeError):
                warm.warm_all()
        self.assertIsNone(cache.get(warm.LOCK_KEY))

    def test_scheduled_job_registered_with_sms_scheduler(self):
        from datetime import datetime, timedelta
        from apscheduler.triggers.interval import IntervalTrigger
        from apps.sms.scheduler import _scheduler
        job = _scheduler.get_job('warm_emergency_places')
        self.assertIsNotNone(job)
        self.assertEqual(job.func, warm.scheduled_warm)
        self.assertIsInstance(job.trigger, IntervalTrigger)
        self.assertEqual(job.trigger.interval, timedelta(hours=4))
        self.assertEqual(job.max_instances, 1)
        self.assertIsNotNone(_scheduler.get_job('process_sms_reminders'))   # le job SMS est toujours là
        self.assertEqual(warm.WARM_FIRST_DELAY_S, 120)
        self.assertEqual(warm.LOCK_TTL, 30 * 60)
