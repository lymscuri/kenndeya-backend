"""
python manage.py warm_emergency_places [--point Conakry --point Labé]

Préchauffe le cache des lieux d'urgence pour les points de
EMERGENCY_PLACES_WARM_POINTS (rayon par défaut et 15 km). Même verrou que le
job planifié : si une exécution est en cours, la commande s'arrête (code 1).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.urgences.warm import WARM_RADII, warm_all, warm_points


class Command(BaseCommand):
    help = "Préchauffe le cache des lieux d'urgence (OSM) pour les villes configurées."

    def add_arguments(self, parser):
        parser.add_argument('--point', action='append', default=None,
                            help='Limiter à un nom de point (répétable)')

    def handle(self, *args, **options):
        points = warm_points()
        wanted = options['point']
        if wanted:
            unknown = [w for w in wanted if w not in {p.name for p in points}]
            if unknown:
                raise CommandError(f'point(s) inconnu(s) : {", ".join(unknown)}')
            points = [p for p in points if p.name in wanted]
        if not points:
            raise CommandError('aucun point configuré (EMERGENCY_PLACES_WARM_POINTS)')
        self.stdout.write(f'{len(points)} point(s) × rayons {WARM_RADII}')
        reports = warm_all(points)
        if reports is None:
            raise CommandError('préchauffage déjà en cours (verrou dans le cache), rien fait')
        for r in reports:
            self.stdout.write(f'{r.point:<12} r={r.radius:<6} source={r.source:<17} lieux={r.count:<4} durée={r.seconds}s')
        errors = sum(1 for r in reports if r.source == 'error')
        style = self.style.WARNING if errors else self.style.SUCCESS
        self.stdout.write(style(f'{len(reports)} appels, {errors} en erreur'))
