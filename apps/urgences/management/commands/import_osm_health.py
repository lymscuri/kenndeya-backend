"""
python manage.py import_osm_health [--country GN] [--country ET]

Importe les lieux de santé OSM d'un ou plusieurs pays (extrait Geofabrik) dans
OsmHealthPlace. Sans --country : réglage EMERGENCY_PLACES_COUNTRIES. Verrou
partagé avec le job planifié : refuse de tourner si un import est en cours.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.urgences import osm_import


class Command(BaseCommand):
    help = "Importe les lieux de santé OpenStreetMap par pays (Geofabrik → OsmHealthPlace)."

    def add_arguments(self, parser):
        parser.add_argument('--country', action='append', default=None, metavar='ISO2',
                            help='code pays ISO 3166-1 alpha-2, répétable (défaut : EMERGENCY_PLACES_COUNTRIES)')

    def handle(self, *args, **options):
        countries = options['country']
        if countries is not None:
            countries = [c.upper() for c in countries]
            unknown = [c for c in countries if c not in osm_import.COUNTRY_SLUGS]
            if unknown:
                raise CommandError(f'pays inconnu(s) : {", ".join(unknown)} '
                                   f'(connus : {", ".join(sorted(osm_import.COUNTRY_SLUGS))})')
        reports = osm_import.import_all(countries)
        if reports is None:
            raise CommandError('import déjà en cours (verrou dans le cache), rien fait')
        for r in reports:
            if r.error:
                self.stdout.write(f'{r.country}  ÉCHEC  {r.error}')
                continue
            kinds = ', '.join(f'{k}={v}' for k, v in r.by_kind.items()) or 'aucun'
            self.stdout.write(
                f'{r.country}  {r.downloaded_bytes / 1e6:.1f} Mo en {r.download_seconds}s  '
                f'parse {r.parse_seconds}s  lieux={r.total} ({kinds})  '
                f'créés={r.created} mis à jour={r.updated} supprimés={r.deleted}'
            )
        failed = sum(1 for r in reports if r.error)
        self.stdout.write(f'{len(reports)} pays, {failed} en erreur')
