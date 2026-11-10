"""
Tests de l'import des lieux de santé OSM (apps.urgences.osm_import) — fichier
.osm.pbf construit dans le test avec pyosmium, téléchargement mocké, aucun réseau.
"""

import os
import shutil
import tempfile
from io import StringIO
from unittest import mock

import osmium
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from . import osm_import
from .models import OsmHealthPlace

LAT, LON = 9.5370, -13.6785          # Conakry


def _write_pbf(path, *, drop_pharmacy=False, rename_donka=None):
    """Petit extrait : nœuds, un way (centroïde), une relation multipolygone, un nœud hors sujet."""
    w = osmium.SimpleWriter(path)
    node = osmium.osm.mutable.Node
    w.add_node(node(id=1, location=(LON, LAT), tags={
        'amenity': 'hospital', 'name': rename_donka or 'Hôpital National Donka', 'opening_hours': '24/7',
        'addr:street': 'Route de Donka', 'addr:city': 'Conakry', 'phone': '+224 622 00 00 00'}))
    if not drop_pharmacy:
        w.add_node(node(id=2, location=(LON, LAT + 0.001), tags={'amenity': 'pharmacy'}))          # sans nom
    w.add_node(node(id=3, location=(LON, LAT + 0.002), tags={'amenity': 'doctors', 'name': 'Cabinet Dr Bah',
                                                             'opening_hours': 'Mo-Fr 08:00-18:00'}))
    w.add_node(node(id=4, location=(LON, LAT + 0.003), tags={'healthcare': 'centre', 'name': 'CS Ratoma',
                                                             'emergency': 'yes'}))
    w.add_node(node(id=5, location=(LON, LAT + 0.004), tags={'healthcare': 'clinic', 'name': 'Clinique Ambroise Paré',
                                                             'healthcare:speciality': 'maternity;general'}))
    w.add_node(node(id=6, location=(LON, LAT + 0.005), tags={'amenity': 'school', 'name': 'École'}))   # ignoré
    # way hôpital : 3 nœuds sans tags, centroïde attendu au milieu
    w.add_node(node(id=11, location=(LON + 0.010, LAT)))
    w.add_node(node(id=12, location=(LON + 0.012, LAT)))
    w.add_node(node(id=13, location=(LON + 0.011, LAT + 0.002)))
    w.add_way(osmium.osm.mutable.Way(id=100, nodes=[11, 12, 13, 11], tags={'amenity': 'hospital', 'name': 'Ignace Deen'}))
    # relation multipolygone clinique : way membre sans tags
    w.add_node(node(id=21, location=(LON + 0.020, LAT)))
    w.add_node(node(id=22, location=(LON + 0.022, LAT + 0.002)))
    w.add_way(osmium.osm.mutable.Way(id=200, nodes=[21, 22, 21]))
    w.add_relation(osmium.osm.mutable.Relation(id=300, members=[('w', 200, 'outer')],
                                               tags={'type': 'multipolygon', 'amenity': 'clinic', 'name': 'Pasteur'}))
    w.close()


class _FakeDownload:
    """Contexte imitant requests.get(stream=True) : sert les octets d'un fichier local."""

    def __init__(self, path, status_code=200):
        self.path, self.status_code = path, status_code

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, chunk_size):
        with open(self.path, 'rb') as fh:
            while chunk := fh.read(chunk_size):
                yield chunk


class OsmImportTests(TestCase):

    def setUp(self):
        cache.clear()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.pbf = os.path.join(self.tmp, 'fixture.osm.pbf')
        _write_pbf(self.pbf)

    def _mock_download(self, path=None, status_code=200):
        patcher = mock.patch('apps.urgences.osm_import.requests.get',
                             return_value=_FakeDownload(path or self.pbf, status_code))
        self.get = patcher.start()
        self.addCleanup(patcher.stop)

    # --- parse -----------------------------------------------------------------------

    def test_parse_kinds_fields_and_geometry(self):
        places = {p['osm_id']: p for p in osm_import.parse_pbf(self.pbf)}
        self.assertEqual(set(places), {'node/1', 'node/2', 'node/3', 'node/4', 'node/5', 'way/100', 'relation/300'})
        donka = places['node/1']
        self.assertEqual((donka['kind'], donka['name'], donka['is_24h'], donka['has_emergency']),
                         ('hospital', 'Hôpital National Donka', True, None))
        self.assertEqual(donka['address'], 'Route de Donka, Conakry')
        self.assertEqual(donka['phone'], '+224 622 00 00 00')
        self.assertEqual(donka['tags']['opening_hours'], '24/7')                  # tags bruts conservés
        self.assertIsNone(places['node/2']['name'])                               # sans nom gardé
        self.assertEqual(places['node/2']['kind'], 'pharmacy')
        self.assertEqual(places['node/3']['kind'], 'clinic')                      # amenity=doctors → clinic
        self.assertIsNone(places['node/3']['is_24h'])                             # horaires ≠ 24/7 → inconnu, pas False
        self.assertEqual(places['node/4']['kind'], 'health_center')               # healthcare=centre
        self.assertEqual((places['node/4']['is_24h'], places['node/4']['has_emergency']), (True, True))  # emergency=yes
        self.assertTrue(places['node/5']['has_maternity'])
        self.assertIsNone(places['node/1']['has_maternity'])
        way = places['way/100']
        self.assertEqual(way['kind'], 'hospital')
        self.assertAlmostEqual(way['lat'], LAT + 0.002 / 3, places=6)             # moyenne des 3 nœuds distincts
        self.assertAlmostEqual(way['lon'], LON + 0.011, places=6)
        rel = places['relation/300']
        self.assertEqual((rel['kind'], rel['name']), ('clinic', 'Pasteur'))
        self.assertAlmostEqual(rel['lat'], LAT + 0.001, places=6)
        self.assertAlmostEqual(rel['lon'], LON + 0.021, places=6)

    def test_kind_from_tags(self):
        self.assertEqual(osm_import.kind_from_tags({'amenity': 'pharmacy'}), 'pharmacy')
        self.assertEqual(osm_import.kind_from_tags({'healthcare': 'health_post'}), 'health_center')
        self.assertEqual(osm_import.kind_from_tags({'amenity': 'hospital', 'healthcare': 'centre'}), 'hospital')  # amenity prime
        self.assertIsNone(osm_import.kind_from_tags({'healthcare': 'dentist'}))
        self.assertIsNone(osm_import.kind_from_tags({'amenity': 'school'}))

    # --- import complet ------------------------------------------------------------------

    def test_import_creates_then_upserts_and_deletes_absent(self):
        self._mock_download()
        with self.assertLogs('apps.urgences.osm_import', level='INFO') as logs:
            reports = osm_import.import_all(['GN'])
        r = reports[0]
        self.assertIsNone(r.error)
        self.assertEqual(r.downloaded_bytes, os.path.getsize(self.pbf))
        self.assertEqual(r.by_kind, {'clinic': 3, 'health_center': 1, 'hospital': 2, 'pharmacy': 1})
        self.assertEqual((r.created, r.updated, r.deleted), (7, 0, 0))
        self.assertEqual(OsmHealthPlace.objects.filter(country='GN').count(), 7)
        self.assertEqual(self.get.call_args.args[0], 'https://download.geofabrik.de/africa/guinea-latest.osm.pbf')
        self.assertIn('KendeyaBackend', self.get.call_args.kwargs['headers']['User-Agent'])
        joined = '\n'.join(logs.output)
        self.assertIn('téléchargés en', joined)
        self.assertIn('7 lieux (clinic=3, health_center=1, hospital=2, pharmacy=1)', joined)
        # aucun fichier temporaire kendeya-osm-* ne subsiste
        self.assertEqual([d for d in os.listdir(tempfile.gettempdir()) if d.startswith('kendeya-osm-')], [])

        # un lieu d'un autre pays ne doit pas être touché par l'import GN
        OsmHealthPlace.objects.create(osm_id='node/999', kind='pharmacy', lat=9.03, lon=38.74, country='ET',
                                      imported_at=OsmHealthPlace.objects.first().imported_at)
        # second import : pharmacie disparue, Donka renommé
        pbf2 = os.path.join(self.tmp, 'fixture2.osm.pbf')
        _write_pbf(pbf2, drop_pharmacy=True, rename_donka='Hôpital Donka')
        self.get.return_value = _FakeDownload(pbf2)
        r2 = osm_import.import_all(['GN'])[0]
        self.assertEqual((r2.created, r2.updated, r2.deleted), (0, 6, 1))
        self.assertFalse(OsmHealthPlace.objects.filter(osm_id='node/2').exists())
        self.assertEqual(OsmHealthPlace.objects.get(osm_id='node/1').name, 'Hôpital Donka')
        self.assertTrue(OsmHealthPlace.objects.filter(osm_id='node/999', country='ET').exists())

    def test_download_failure_reported_others_continue(self):
        def get(url, **kw):
            return _FakeDownload(self.pbf, status_code=503 if 'ethiopia' in url else 200)
        with mock.patch('apps.urgences.osm_import.requests.get', side_effect=get):
            with self.assertLogs('apps.urgences.osm_import', level='ERROR') as logs:
                reports = osm_import.import_all(['ET', 'GN'])
        self.assertEqual([(r.country, r.error is None) for r in reports], [('ET', False), ('GN', True)])
        self.assertIn('HTTP 503', reports[0].error)
        self.assertIn('import osm ET ÉCHEC', logs.output[0])
        self.assertEqual(OsmHealthPlace.objects.filter(country='GN').count(), 7)
        self.assertIsNone(cache.get(osm_import.LOCK_KEY))                         # verrou relâché

    @override_settings(EMERGENCY_PLACES_COUNTRIES=['GN', 'ET'])
    def test_command_uses_setting_and_prints_report(self):
        self._mock_download()
        out = StringIO()
        call_command('import_osm_health', stdout=out)
        text = out.getvalue()
        self.assertIn('GN  0.0 Mo en', text)
        self.assertIn('lieux=7 (clinic=3, health_center=1, hospital=2, pharmacy=1)  créés=7 mis à jour=0 supprimés=0', text)
        self.assertIn('ET  ', text)
        self.assertIn('2 pays, 0 en erreur', text)
        self.assertEqual([c.args[0].split('/')[-1] for c in self.get.call_args_list],
                         ['guinea-latest.osm.pbf', 'ethiopia-latest.osm.pbf'])

    def test_command_unknown_country(self):
        with self.assertRaises(CommandError) as ctx:
            call_command('import_osm_health', '--country', 'XX', stdout=StringIO())
        self.assertIn('pays inconnu(s) : XX', str(ctx.exception))

    # --- verrou + planification ----------------------------------------------------------

    def test_lock_prevents_concurrent_run(self):
        self.assertTrue(osm_import.acquire_lock())
        with mock.patch('apps.urgences.osm_import.import_country') as ic:
            with self.assertLogs('apps.urgences.osm_import', level='WARNING'):
                self.assertIsNone(osm_import.import_all(['GN']))
            with self.assertRaises(CommandError) as ctx:
                call_command('import_osm_health', '--country', 'GN', stdout=StringIO())
            self.assertIn('déjà en cours', str(ctx.exception))
            with self.assertLogs('apps.urgences.osm_import', level='WARNING'):
                osm_import.scheduled_import()
            ic.assert_not_called()
        osm_import.release_lock()
        self._mock_download()
        self.assertEqual(len(osm_import.import_all(['GN'])), 1)
        self.assertIsNone(cache.get(osm_import.LOCK_KEY))

    def test_scheduled_job_registered_weekly_sunday_03_utc(self):
        from apscheduler.triggers.cron import CronTrigger
        from apps.sms.scheduler import _scheduler
        job = _scheduler.get_job('import_osm_health')
        self.assertIsNotNone(job)
        self.assertEqual(job.func, osm_import.scheduled_import)
        self.assertIsInstance(job.trigger, CronTrigger)
        fields = {f.name: str(f) for f in job.trigger.fields}
        self.assertEqual((fields['day_of_week'], fields['hour'], fields['minute']), ('sun', '3', '0'))
        self.assertEqual(str(job.trigger.timezone), 'UTC')
        self.assertEqual(job.max_instances, 1)
        self.assertIsNotNone(_scheduler.get_job('warm_emergency_places'))         # les autres jobs sont toujours là
        self.assertIsNotNone(_scheduler.get_job('process_sms_reminders'))
