"""
Tests du chargeur de protocoles de premiers secours.

Aucune base de données n'est nécessaire : SimpleTestCase. Les cas invalides
sont construits en copiant les protocoles réels dans un dossier temporaire et
en y introduisant une seule faute, pour vérifier que le chargeur la refuse en
la localisant (fichier + ligne).
"""

import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from .loader import PROTOCOLS_DIR, ProtocolRegistry, load_protocols
from .schema import MAX_STEP_WORDS, ProtocolValidationError, word_count

REAL = PROTOCOLS_DIR
MAIN = 'unconscious_breathing.yaml'

SIGNATURE = """validated_by:
  - name: Dr Test Médecin
    qualification: Médecin urgentiste
    organisation: Numerica Guinée
    date: 2026-11-09
"""


class _TmpProtocols:
    """Copie des protocoles réels dans un dossier temporaire modifiable."""

    def __enter__(self) -> Path:
        self.dir = Path(tempfile.mkdtemp(prefix='firstaid_')) / 'protocols'
        shutil.copytree(REAL, self.dir)
        return self.dir

    def __exit__(self, *exc):
        shutil.rmtree(self.dir.parent, ignore_errors=True)


def _replace_once(path: Path, old: str, new: str) -> int:
    """Remplace la première occurrence et retourne son numéro de ligne (1-indexé)."""
    text = path.read_text(encoding='utf-8')
    assert old in text, f'motif absent du fichier : {old!r}'
    idx = text.index(old)
    line = text[:idx].count('\n') + 1
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    return line


class LoaderValidTests(SimpleTestCase):

    def test_real_protocols_load(self):
        """Les YAML livrés chargent et exposent la structure attendue."""
        protocols = load_protocols(REAL)
        self.assertIn('unconscious_breathing', protocols)
        self.assertIn('cardiac_arrest', protocols)
        p = protocols['unconscious_breathing']
        self.assertEqual(p.status, 'draft_unvalidated')
        self.assertEqual(p.validated_by, ())
        self.assertTrue(p.call_emergency_first)
        self.assertEqual(p.decision_tree.entry, 'q_responds')
        self.assertIn('recovery_position', p.action_blocks)
        # chaque étape porte une page citée dans une source déclarée
        for block in p.action_blocks.values():
            groups = block.variants.values() if block.variants else [block.steps]
            for steps in groups:
                for step in steps:
                    self.assertIn(step.source_page.source, p.sources)
                    self.assertIn(step.source_page.page, p.sources[step.source_page.source].pages)
                    self.assertLessEqual(word_count(step.text), MAX_STEP_WORDS)
        # la bascule vers cardiac_arrest est résolue
        answer = p.decision_tree.questions['q_breathing_normal'].answers['no']
        self.assertEqual(answer.switch_to, 'cardiac_arrest')
        self.assertTrue(protocols['cardiac_arrest'].incomplete)

    def test_no_emergency_number_in_files(self):
        """Le numéro d'urgence ne figure dans aucun fichier : il vient des settings."""
        for path in REAL.glob('*.yaml'):
            self.assertNotIn(settings.EMERGENCY_NUMBER, path.read_text(encoding='utf-8'), path.name)


class LoaderRejectTests(SimpleTestCase):

    def _assert_rejected(self, directory: Path, fragment: str, file: str = MAIN, line: int | None = None):
        with self.assertRaises(ProtocolValidationError) as cm:
            load_protocols(directory)
        errors = cm.exception.errors
        matching = [e for e in errors if fragment in e.message and e.file.endswith(file)]
        self.assertTrue(matching, f'erreur attendue contenant {fragment!r} ; obtenu :\n'
                                  + '\n'.join(str(e) for e in errors))
        if line is not None:
            self.assertIn(line, [e.line for e in matching],
                          f'ligne {line} attendue ; lignes obtenues : {[e.line for e in matching]}')
        return matching

    def test_malformed_yaml_rejected_with_line(self):
        with _TmpProtocols() as d:
            path = d / MAIN
            text = path.read_text(encoding='utf-8')
            # on casse la syntaxe à une ligne connue : crochet non fermé
            broken_line = _replace_once(path, 'vision_checkpoints: []', 'vision_checkpoints: [')
            errors = self._assert_rejected(d, 'YAML malformé')
            self.assertIsNotNone(errors[0].line)
            self.assertGreaterEqual(errors[0].line, broken_line)
            self.assertIn(MAIN, str(errors[0]))
            del text

    def test_orphan_answer_rejected(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, 'next_question: q_spine_injury', 'next_question: q_nowhere')
            self._assert_rejected(d, "question inexistante 'q_nowhere'", line=line)

    def test_missing_switch_target_rejected(self):
        with _TmpProtocols() as d:
            (d / 'cardiac_arrest.yaml').unlink()
            self._assert_rejected(d, "scénario absent 'cardiac_arrest'")

    def test_validated_without_signer_rejected(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, 'status: draft_unvalidated', 'status: validated')
            self._assert_rejected(d, "'validated' sans aucune entrée dans 'validated_by'")
            # la ligne rapportée est celle du bloc racine (ligne 1 du document)
            self.assertIsNotNone(line)

    def test_step_with_15_or_16_words_rejected(self):
        for n in (15, 16):
            with _TmpProtocols() as d:
                long_text = ' '.join(['mot'] * n)
                line = _replace_once(d / MAIN, 'text: Ne déplacez pas la personne.', f'text: {long_text}')
                self._assert_rejected(d, f'{n} mots, maximum {MAX_STEP_WORDS}', line=line)

    def test_step_with_14_words_accepted(self):
        with _TmpProtocols() as d:
            _replace_once(d / MAIN, 'text: Ne déplacez pas la personne.', 'text: ' + ' '.join(['mot'] * 14))
            load_protocols(d)  # ne lève pas

    def test_missing_source_page_rejected(self):
        with _TmpProtocols() as d:
            path = d / MAIN
            text = path.read_text(encoding='utf-8')
            target = ('      - text: Ne déplacez pas la personne.\n'
                      '        visual: ""\n'
                      '        source_page: {source: ifrc_2025_en, page: 152}\n')
            self.assertIn(target, text)
            line = text[:text.index(target)].count('\n') + 1
            path.write_text(text.replace(target, '      - text: Ne déplacez pas la personne.\n        visual: ""\n', 1),
                            encoding='utf-8')
            self._assert_rejected(d, "'source_page' manquante", line=line)

    def test_source_page_outside_cited_pages_rejected(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, 'source_page: {source: ifrc_2025_en, page: 152}',
                                 'source_page: {source: ifrc_2025_en, page: 999}')
            self._assert_rejected(d, 'page 999 absente des pages citées', line=line)

    def test_missing_sources_rejected(self):
        with _TmpProtocols() as d:
            _replace_once(d / MAIN, 'sources:\n', 'sources_removed:\n')
            self._assert_rejected(d, "champ obligatoire manquant : 'sources'")

    def test_hardcoded_emergency_number_rejected(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, 'text: Ne déplacez pas la personne.', 'text: Appelez le 442 maintenant.')
            self._assert_rejected(d, "numéro d'urgence écrit en dur", line=line)


class PublishableTests(SimpleTestCase):

    def test_publishable_excludes_drafts(self):
        """Avec les réglages par défaut, aucun brouillon ne sort."""
        reg = ProtocolRegistry()
        reg.load(REAL)
        self.assertEqual(set(reg.all_protocols()), {'unconscious_breathing', 'cardiac_arrest'})
        self.assertEqual(reg.publishable_protocols(), {})

    def test_publishable_only_validated_and_signed(self):
        """Un protocole validé ET signé sort ; un brouillon du même dossier non."""
        with _TmpProtocols() as d:
            path = d / MAIN
            _replace_once(path, 'status: draft_unvalidated', 'status: validated')
            _replace_once(path, 'validated_by: []\n', SIGNATURE)
            reg = ProtocolRegistry()
            reg.load(d)
            pub = reg.publishable_protocols()
            self.assertEqual(set(pub), {'unconscious_breathing'})
            self.assertTrue(pub['unconscious_breathing'].is_validated)
            self.assertEqual(pub['unconscious_breathing'].validated_by[0].name, 'Dr Test Médecin')
            # cardiac_arrest est un brouillon incomplet : il ne passe jamais
            self.assertNotIn('cardiac_arrest', pub)
            for pid, p in pub.items():
                self.assertEqual(p.status, 'validated', f'{pid} non validé a traversé publishable_protocols()')
                self.assertTrue(p.validated_by, f'{pid} sans signataire a traversé publishable_protocols()')

    @override_settings(FIRSTAID_ALLOW_DRAFTS=True)
    def test_allow_drafts_exposes_complete_drafts_only(self):
        """Hors production, ALLOW_DRAFTS laisse passer les brouillons complets, jamais les squelettes."""
        reg = ProtocolRegistry()
        reg.load(REAL)
        pub = reg.publishable_protocols()
        self.assertIn('unconscious_breathing', pub)
        self.assertNotIn('cardiac_arrest', pub)


class ProductionSettingsTests(SimpleTestCase):

    def test_allow_drafts_cannot_be_enabled_in_production(self):
        """production.py force FIRSTAID_ALLOW_DRAFTS=False même si l'environnement dit True."""
        source = (Path(settings.BASE_DIR) / 'config' / 'settings' / 'production.py').read_text(encoding='utf-8')
        lines = [l for l in source.splitlines() if l.strip().startswith('FIRSTAID_ALLOW_DRAFTS')]
        self.assertEqual(lines, ['FIRSTAID_ALLOW_DRAFTS = False'], 'la valeur doit être un littéral, sans env()')

        # Import réel du module de production avec l'environnement hostile.
        saved_env = os.environ.get('FIRSTAID_ALLOW_DRAFTS')
        saved_modules = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith('config.settings')}
        try:
            os.environ['FIRSTAID_ALLOW_DRAFTS'] = 'True'
            prod = importlib.import_module('config.settings.production')
            self.assertIs(prod.FIRSTAID_ALLOW_DRAFTS, False)
            base = importlib.import_module('config.settings.base')
            self.assertIs(base.FIRSTAID_ALLOW_DRAFTS, True, 'témoin : base.py lit bien l’environnement')
        finally:
            if saved_env is None:
                os.environ.pop('FIRSTAID_ALLOW_DRAFTS', None)
            else:
                os.environ['FIRSTAID_ALLOW_DRAFTS'] = saved_env
            for k in list(sys.modules):
                if k.startswith('config.settings'):
                    sys.modules.pop(k)
            sys.modules.update(saved_modules)
