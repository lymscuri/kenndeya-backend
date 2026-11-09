"""
python manage.py firstaid_review --out <dossier> [--lang fr|en|both]

Génère le dossier de relecture médicale : un PDF par protocole et par langue,
nommé <protocol_id>_<lang>_v<version>.pdf, depuis les YAML chargés par le
registre (brouillons compris : c'est précisément ce que le médecin relit).
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.firstaid.loader import all_protocols
from apps.firstaid.review import render_protocol_pdf, review_filename
from apps.firstaid.schema import LANGS


class Command(BaseCommand):
    help = 'Génère les PDF de relecture médicale des protocoles de premiers secours.'

    def add_arguments(self, parser):
        parser.add_argument('--out', required=True, help='Dossier de sortie des PDF')
        parser.add_argument('--lang', choices=[*LANGS, 'both'], default='both',
                            help="Langue : fr, en ou both (défaut : both)")
        parser.add_argument('--protocol', action='append', default=None,
                            help='Limiter à un id de protocole (répétable)')

    def handle(self, *args, **options):
        out = Path(options['out'])
        langs = list(LANGS) if options['lang'] == 'both' else [options['lang']]
        protocols = all_protocols()
        wanted = options['protocol']
        if wanted:
            unknown = [w for w in wanted if w not in protocols]
            if unknown:
                raise CommandError(f'protocole(s) inconnu(s) : {", ".join(unknown)}')
            protocols = {k: v for k, v in protocols.items() if k in wanted}
        if not protocols:
            raise CommandError('aucun protocole chargé')

        written: list[Path] = []
        for pid, proto in sorted(protocols.items()):
            for lang in langs:
                path = render_protocol_pdf(proto, lang, out / review_filename(proto, lang))
                written.append(path)
                self.stdout.write(f'{path}  ({pid}, {lang}, v{proto.version}, {proto.status})')
        self.stdout.write(self.style.SUCCESS(f'{len(written)} PDF générés dans {out}'))
