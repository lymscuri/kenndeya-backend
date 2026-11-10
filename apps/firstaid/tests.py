"""
Tests du chargeur de protocoles de premiers secours.

Aucune base de données n'est nécessaire : SimpleTestCase. Les cas invalides
sont construits en copiant les protocoles réels dans un dossier temporaire et
en y introduisant une seule faute, pour vérifier que le chargeur la refuse en
la localisant (fichier + ligne).
"""

import importlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from .loader import PROTOCOLS_DIR, ProtocolRegistry, load_protocols
from .schema import LANGS, MAX_STEP_WORDS, ProtocolValidationError, word_count

REAL = PROTOCOLS_DIR
MAIN = 'unconscious_breathing.yaml'

SIGNATURE = """validated_by:
  - name: Dr Test Médecin
    qualification: Médecin urgentiste
    organisation: Numerica Guinée
    date: 2026-11-09
"""

# Étape témoin utilisée par les tests de mutation (bloc spine_suspected, étape 1).
STEP_FR = '          fr: Ne déplacez pas la personne.\n'
STEP_EN = '          en: Do not move the person.\n'
STEP_BLOCK = (
    '      - text:\n'
    + STEP_FR
    + STEP_EN
    + '        visual: ""\n'
    + '        source_page: {source: ifrc_2025_en, page: 152}\n'
)


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
        # chaque étape porte une page citée dans une source déclarée, et respecte
        # la limite de mots dans CHAQUE langue
        for block in p.action_blocks.values():
            for step in block.all_steps():
                self.assertIn(step.source_page.source, p.sources)
                self.assertIn(step.source_page.page, p.sources[step.source_page.source].pages)
                for lang in LANGS:
                    self.assertLessEqual(word_count(step.text.get(lang)), MAX_STEP_WORDS, step.text)
        # la bascule vers cardiac_arrest est résolue
        answer = p.decision_tree.questions['q_breathing_normal'].answers['no']
        self.assertEqual(answer.switch_to, 'cardiac_arrest')
        self.assertFalse(protocols['cardiac_arrest'].incomplete)

    def test_cardiac_arrest_is_complete_but_not_publishable(self):
        """cardiac_arrest charge, n'est plus un squelette, reste un brouillon non publiable."""
        reg = ProtocolRegistry()
        reg.load(REAL)
        p = reg.all_protocols()['cardiac_arrest']
        self.assertFalse(p.incomplete)
        self.assertEqual(p.version, 4)
        self.assertEqual(p.status, 'draft_unvalidated')
        self.assertEqual(p.validated_by, ())
        self.assertNotIn('cardiac_arrest', reg.publishable_protocols())
        # les trois variantes existent dans les blocs de RCP
        for bid in ('cpr_with_breaths', 'cpr_compressions_only', 'use_aed'):
            self.assertEqual(set(p.action_blocks[bid].variants), {'adult', 'child', 'infant'}, bid)
        # le red flag « respire à nouveau » bascule vers unconscious_breathing
        self.assertTrue(any(f.switch_to == 'unconscious_breathing' for f in p.red_flags))
        # enfant et bébé : les insufflations précèdent les compressions
        for variant in ('child', 'infant'):
            texts = [st.text.fr for st in p.action_blocks['cpr_with_breaths'].variants[variant]]
            first_breath = next(i for i, t in enumerate(texts) if 'insufflations' in t)
            first_compression = next(i for i, t in enumerate(texts) if '30 compressions' in t)
            self.assertLess(first_breath, first_compression, variant)
        # adulte : les compressions précèdent les insufflations
        texts = [st.text.fr for st in p.action_blocks['cpr_with_breaths'].variants['adult']]
        self.assertLess(next(i for i, t in enumerate(texts) if '30 compressions' in t),
                        next(i for i, t in enumerate(texts) if 'insufflations' in t))

    def test_every_text_has_both_languages(self):
        """Aucun texte affichable ne manque d'une langue, et aucune n'est vide."""
        for p in load_protocols(REAL).values():
            for text in p.all_texts():
                self.assertTrue(text.fr.strip(), text)
                self.assertTrue(text.en.strip(), text)

    def test_no_emergency_number_in_files(self):
        """Le numéro d'urgence ne figure dans aucun fichier : il vient des settings."""
        for path in REAL.glob('*.yaml'):
            self.assertNotIn(settings.EMERGENCY_NUMBER, path.read_text(encoding='utf-8'), path.name)

    def test_source_urls_point_to_the_pdfs(self):
        p = load_protocols(REAL)['unconscious_breathing']
        self.assertTrue(p.sources['ifrc_2025_en'].url.endswith('Guidelines-2025_compressed.pdf'))
        self.assertTrue(p.sources['ifrc_2020_fr'].url.endswith('FR_GFARC-GUIDELINES.pdf'))


class _RejectMixin:
    """Assertion commune : le dossier est refusé avec une erreur localisée."""

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


class LoaderRejectTests(_RejectMixin, SimpleTestCase):

    def test_malformed_yaml_rejected_with_line(self):
        with _TmpProtocols() as d:
            broken_line = _replace_once(d / MAIN, 'vision_checkpoints: []', 'vision_checkpoints: [')
            errors = self._assert_rejected(d, 'YAML malformé')
            self.assertIsNotNone(errors[0].line)
            self.assertGreaterEqual(errors[0].line, broken_line)
            self.assertIn(MAIN, str(errors[0]))

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
            self._assert_rejected(d, "'validated' sans aucune entrée dans 'validated_by'", line=line)

    def test_step_with_15_or_16_words_rejected(self):
        for n in (15, 16):
            with _TmpProtocols() as d:
                line = _replace_once(d / MAIN, STEP_FR, '          fr: ' + ' '.join(['mot'] * n) + '\n')
                self._assert_rejected(d, f'text.fr\' : {n} mots, maximum {MAX_STEP_WORDS}', line=line)

    def test_step_with_14_words_accepted(self):
        with _TmpProtocols() as d:
            _replace_once(d / MAIN, STEP_FR, '          fr: ' + ' '.join(['mot'] * 14) + '\n')
            load_protocols(d)  # ne lève pas

    def test_missing_source_page_rejected(self):
        with _TmpProtocols() as d:
            without = STEP_BLOCK.replace('        source_page: {source: ifrc_2025_en, page: 152}\n', '')
            line = _replace_once(d / MAIN, STEP_BLOCK, without)
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
            line = _replace_once(d / MAIN, STEP_FR, '          fr: Appelez le 442 maintenant.\n')
            self._assert_rejected(d, "numéro d'urgence écrit en dur", line=line)

    def test_hardcoded_emergency_number_in_english_rejected(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, STEP_EN, '          en: Call 112 now.\n')
            self._assert_rejected(d, "text.en' : numéro d'urgence écrit en dur", line=line)


class BilingualRejectTests(_RejectMixin, SimpleTestCase):
    """Règles propres au bilinguisme strict."""

    def test_missing_language_rejected_with_line(self):
        """`en` absent sur une étape → refusé, ligne du bloc texte (celle de `fr`)."""
        with _TmpProtocols() as d:
            en_line = _replace_once(d / MAIN, STEP_EN, '')
            # le bloc {fr, en} commence à la ligne de `fr`, juste au-dessus du `en` retiré
            self._assert_rejected(d, "langue 'en' manquante", line=en_line - 1)

    def test_empty_language_rejected(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, STEP_EN, '          en: ""\n')
            self._assert_rejected(d, "text.en' doit être une chaîne non vide", line=line)

    def test_unknown_language_key_rejected(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, STEP_EN, STEP_EN + '          es: No mueva a la persona.\n')
            self._assert_rejected(d, "clé de langue inconnue 'es'", line=line + 1)

    def test_word_limit_applies_to_each_language(self):
        """fr à 10 mots, en à 15 → refusé sur `en` seul."""
        with _TmpProtocols() as d:
            path = d / MAIN
            _replace_once(path, STEP_FR, '          fr: ' + ' '.join(['mot'] * 10) + '\n')
            line = _replace_once(path, STEP_EN, '          en: ' + ' '.join(['word'] * 15) + '\n')
            matching = self._assert_rejected(d, f"text.en' : 15 mots, maximum {MAX_STEP_WORDS}", line=line)
            self.assertFalse(any('text.fr' in e.message for e in matching))

    def test_question_mark_required_in_both_languages(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, 'en: Do you suspect a spine injury?', 'en: Do you suspect a spine injury')
            self._assert_rejected(d, "text.en' : une question fermée se termine par « ? »", line=line)

    def test_plain_string_instead_of_bilingual_dict_rejected(self):
        with _TmpProtocols() as d:
            line = _replace_once(d / MAIN, 'title:\n  fr: Personne inconsciente qui respire\n  en: Unresponsive person who is breathing\n',
                                 'title: Personne inconsciente qui respire\n')
            self._assert_rejected(d, "'title' doit être un dictionnaire {fr: ..., en: ...}", line=line)


class LocalizedTests(SimpleTestCase):

    def setUp(self):
        self.protocols = load_protocols(REAL)

    def _strings(self, lang: str) -> set[str]:
        return {t.get(lang) for p in self.protocols.values() for t in p.all_texts()}

    def test_fr_and_en_corpora_are_disjoint(self):
        """Prérequis du test suivant : aucune chaîne n'est identique dans les deux langues."""
        self.assertEqual(self._strings('fr') & self._strings('en'), set())

    def test_localized_fr_contains_no_english_and_vice_versa(self):
        fr_strings, en_strings = self._strings('fr'), self._strings('en')
        for p in self.protocols.values():
            view_fr = json.dumps(p.localized('fr'), ensure_ascii=False)
            view_en = json.dumps(p.localized('en'), ensure_ascii=False)
            for s in en_strings:
                self.assertNotIn(json.dumps(s, ensure_ascii=False), view_fr, f'anglais dans la vue fr : {s!r}')
            for s in fr_strings:
                self.assertNotIn(json.dumps(s, ensure_ascii=False), view_en, f'français dans la vue en : {s!r}')
            # et la vue contient bien tous les textes de sa langue
            for t in p.all_texts():
                self.assertIn(json.dumps(t.fr, ensure_ascii=False), view_fr)
                self.assertIn(json.dumps(t.en, ensure_ascii=False), view_en)
            self.assertEqual(p.localized('fr')['lang'], 'fr')
            self.assertEqual(p.localized('en')['lang'], 'en')

    def test_localized_unknown_language_raises(self):
        p = self.protocols['unconscious_breathing']
        with self.assertRaises(ValueError):
            p.localized('de')
        with self.assertRaises(ValueError):
            p.localized('')
        with self.assertRaises(TypeError):
            p.localized()  # pas de valeur par défaut  # noqa

    def test_localized_is_flat_single_language(self):
        """Aucun dict {fr, en} ne subsiste dans la vue localisée."""
        def walk(node):
            if isinstance(node, dict):
                self.assertNotEqual(set(node) & {'fr', 'en'}, {'fr', 'en'}, node)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        for p in self.protocols.values():
            walk(p.localized('fr'))
            walk(p.localized('en'))


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
            self.assertNotIn('cardiac_arrest', pub)
            for pid, p in pub.items():
                self.assertEqual(p.status, 'validated', f'{pid} non validé a traversé publishable_protocols()')
                self.assertTrue(p.validated_by, f'{pid} sans signataire a traversé publishable_protocols()')

    @override_settings(FIRSTAID_ALLOW_DRAFTS=True)
    def test_allow_drafts_exposes_complete_drafts_only(self):
        """Hors production, ALLOW_DRAFTS laisse passer les brouillons complets, jamais les squelettes."""
        reg = ProtocolRegistry()
        reg.load(REAL)
        self.assertEqual(set(reg.publishable_protocols()), {'unconscious_breathing', 'cardiac_arrest'})
        # un squelette (incomplete: true) reste exclu même avec ALLOW_DRAFTS
        with _TmpProtocols() as d:
            _replace_once(d / 'cardiac_arrest.yaml', 'incomplete: false', 'incomplete: true')
            reg2 = ProtocolRegistry()
            reg2.load(d)
            self.assertEqual(set(reg2.publishable_protocols()), {'unconscious_breathing'})


class ProductionSettingsTests(SimpleTestCase):

    @staticmethod
    def _import_settings(module: str, env_value: str | None):
        """Importe un module de settings à neuf, avec FIRSTAID_ALLOW_DRAFTS posé (ou retiré) dans l'env."""
        saved_env = os.environ.get('FIRSTAID_ALLOW_DRAFTS')
        saved_modules = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith('config.settings')}
        try:
            if env_value is None:
                os.environ.pop('FIRSTAID_ALLOW_DRAFTS', None)
            else:
                os.environ['FIRSTAID_ALLOW_DRAFTS'] = env_value
            return importlib.import_module(module).FIRSTAID_ALLOW_DRAFTS
        finally:
            if saved_env is None:
                os.environ.pop('FIRSTAID_ALLOW_DRAFTS', None)
            else:
                os.environ['FIRSTAID_ALLOW_DRAFTS'] = saved_env
            for k in list(sys.modules):
                if k.startswith('config.settings'):
                    sys.modules.pop(k)
            sys.modules.update(saved_modules)

    def test_staging_reads_allow_drafts_from_environment(self):
        """staging.py : True si l'env dit True, False sans variable ; production reste False dans les deux cas."""
        self.assertIs(self._import_settings('config.settings.staging', 'True'), True)
        self.assertIs(self._import_settings('config.settings.staging', None), False)
        self.assertIs(self._import_settings('config.settings.staging', 'False'), False)
        self.assertIs(self._import_settings('config.settings.production', 'True'), False)
        self.assertIs(self._import_settings('config.settings.production', None), False)

    def test_staging_is_production_plus_one_setting(self):
        """staging.py = import étoile de production + la seule ligne FIRSTAID_ALLOW_DRAFTS (analyse ast)."""
        import ast
        source = (Path(settings.BASE_DIR) / 'config' / 'settings' / 'staging.py').read_text(encoding='utf-8')
        body = [n for n in ast.parse(source).body
                if not (isinstance(n, ast.Expr) and isinstance(getattr(n, 'value', None), ast.Constant))]
        self.assertEqual(len(body), 2, [type(n).__name__ for n in body])
        imp, assign = body
        self.assertIsInstance(imp, ast.ImportFrom)
        self.assertEqual((imp.module, imp.names[0].name), ('production', '*'))
        self.assertIsInstance(assign, ast.Assign)
        self.assertEqual(assign.targets[0].id, 'FIRSTAID_ALLOW_DRAFTS')
        self.assertIn("env.bool('FIRSTAID_ALLOW_DRAFTS', default=False)", ast.get_source_segment(source, assign.value))

    def test_allow_drafts_cannot_be_enabled_in_production(self):
        """production.py force FIRSTAID_ALLOW_DRAFTS=False même si l'environnement dit True."""
        source = (Path(settings.BASE_DIR) / 'config' / 'settings' / 'production.py').read_text(encoding='utf-8')
        lines = [l for l in source.splitlines() if l.strip().startswith('FIRSTAID_ALLOW_DRAFTS')]
        self.assertEqual(lines, ['FIRSTAID_ALLOW_DRAFTS = False'], 'la valeur doit être un littéral, sans env()')

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


class ReviewNotesTests(_RejectMixin, SimpleTestCase):

    def test_real_review_notes_loaded(self):
        protocols = load_protocols(REAL)
        self.assertEqual(len(protocols['unconscious_breathing'].review_notes), 3)
        self.assertEqual(len(protocols['cardiac_arrest'].review_notes), 12)
        for p in protocols.values():
            for n in p.review_notes:
                self.assertTrue(n.fr.strip() and n.en.strip())
            self.assertEqual(len(p.localized('fr')['review_notes']), len(p.review_notes))

    def test_empty_review_notes_accepted(self):
        with _TmpProtocols() as d:
            path = d / MAIN
            text = path.read_text(encoding='utf-8')
            start = text.index('review_notes:\n')
            end = text.index('# Réservé : points de contrôle caméra')
            path.write_text(text[:start] + 'review_notes: []\n\n' + text[end:], encoding='utf-8')
            self.assertEqual(load_protocols(d)['unconscious_breathing'].review_notes, ())

    def test_missing_review_notes_accepted(self):
        with _TmpProtocols() as d:
            path = d / MAIN
            text = path.read_text(encoding='utf-8')
            start = text.index('review_notes:\n')
            end = text.index('# Réservé : points de contrôle caméra')
            path.write_text(text[:start] + text[end:], encoding='utf-8')
            self.assertEqual(load_protocols(d)['unconscious_breathing'].review_notes, ())

    def test_mistyped_review_notes_rejected(self):
        with _TmpProtocols() as d:
            path = d / MAIN
            text = path.read_text(encoding='utf-8')
            start = text.index('review_notes:\n')
            end = text.index('# Réservé : points de contrôle caméra')
            path.write_text(text[:start] + 'review_notes: "une seule chaîne"\n\n' + text[end:], encoding='utf-8')
            self._assert_rejected(d, "'review_notes' doit être une liste")
        with _TmpProtocols() as d:
            path = d / MAIN
            text = path.read_text(encoding='utf-8')
            start = text.index('review_notes:\n')
            end = text.index('# Réservé : points de contrôle caméra')
            path.write_text(text[:start] + 'review_notes:\n  - fr: Seulement en français\n\n' + text[end:],
                            encoding='utf-8')
            self._assert_rejected(d, "review_notes[1]' : langue 'en' manquante")


class ReviewCommandTests(SimpleTestCase):
    """La commande firstaid_review produit un PDF par protocole et par langue."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import shutil as _sh
        from django.core.management import call_command
        cls.tmp = Path(tempfile.mkdtemp(prefix='firstaid_review_'))
        cls.pdftotext = _sh.which('pdftotext')
        cls.stdout = __import__('io').StringIO()
        call_command('firstaid_review', '--out', str(cls.tmp), stdout=cls.stdout)
        cls.protocols = load_protocols(REAL)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)
        super().tearDownClass()

    def _text(self, pdf: Path) -> str:
        if not self.pdftotext:
            self.skipTest('pdftotext absent')
        import subprocess
        out = subprocess.run([self.pdftotext, '-layout', str(pdf), '-'], capture_output=True, text=True, check=True)
        import re
        return re.sub(r'\s+', ' ', out.stdout)

    def test_four_pdfs_named_by_protocol_lang_version(self):
        names = sorted(p.name for p in self.tmp.glob('*.pdf'))
        self.assertEqual(names, [
            'cardiac_arrest_en_v4.pdf', 'cardiac_arrest_fr_v4.pdf',
            'unconscious_breathing_en_v3.pdf', 'unconscious_breathing_fr_v3.pdf',
        ])
        for p in self.tmp.glob('*.pdf'):
            self.assertGreater(p.stat().st_size, 5000, p.name)
            self.assertEqual(p.read_bytes()[:5], b'%PDF-', p.name)
        self.assertIn('4 PDF', self.stdout.getvalue())

    def test_pdf_contains_only_its_language(self):
        import re
        for pid, proto in self.protocols.items():
            for lang, other in (('fr', 'en'), ('en', 'fr')):
                text = self._text(self.tmp / f'{pid}_{lang}_v{proto.version}.pdf')
                for t in proto.all_texts():
                    foreign = t.get(other)
                    pattern = r'(?<!\w)' + re.escape(re.sub(r'\s+', ' ', foreign)) + r'(?!\w)'
                    self.assertIsNone(re.search(pattern, text), f'{pid}/{lang} contient « {foreign} »')
                # et les textes courts de sa propre langue y figurent
                for t in proto.all_texts():
                    own = re.sub(r'\s+', ' ', t.get(lang))
                    if len(own) <= 60:
                        self.assertIn(own, text, f'{pid}/{lang} ne contient pas « {own} »')

    def test_pdf_has_control_headers_and_footer(self):
        text = self._text(self.tmp / 'cardiac_arrest_fr_v4.pdf')
        for needle in ('cardiac_arrest', 'Version', '4', 'draft_unvalidated', 'NON VALIDÉ',
                       settings.EMERGENCY_NUMBER, 'IFRC 2025 EN p.162', 'cardiac_arrest.yaml version 4',
                       'Points à trancher par le médecin', '☐ OK'):
            self.assertIn(needle, text, needle)

    def test_lang_option_limits_output(self):
        from django.core.management import call_command
        tmp = Path(tempfile.mkdtemp(prefix='firstaid_review_fr_'))
        try:
            call_command('firstaid_review', '--out', str(tmp), '--lang', 'fr', stdout=__import__('io').StringIO())
            self.assertEqual(sorted(p.name for p in tmp.glob('*.pdf')),
                             ['cardiac_arrest_fr_v4.pdf', 'unconscious_breathing_fr_v3.pdf'])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class PublicApiTests(SimpleTestCase):
    """Endpoints publics : lecture seule, langue stricte, brouillons invisibles."""

    LIST = '/api/v1/firstaid/protocols/'
    META = '/api/v1/firstaid/meta/'

    def setUp(self):
        from django.core.cache import cache
        from rest_framework.test import APIClient
        cache.clear()                      # compteurs de throttle
        self.client = APIClient()
        from .loader import registry
        registry.load(REAL)

    def tearDown(self):
        from .loader import registry
        registry.load(REAL)

    # --- sans ALLOW_DRAFTS : rien n'est servi ------------------------------------

    def test_drafts_are_invisible_by_default(self):
        r = self.client.get(self.LIST, {'lang': 'fr'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'success': True, 'count': 0, 'results': []})
        for pid in ('unconscious_breathing', 'cardiac_arrest', 'does_not_exist'):
            r = self.client.get(f'{self.LIST}{pid}/', {'lang': 'fr'})
            self.assertEqual(r.status_code, 404, pid)
            self.assertFalse(r.json()['success'])
            self.assertEqual(r.json()['error']['code'], 'not_found')
        # un brouillon et un id inexistant produisent exactement la même réponse
        draft = self.client.get(f'{self.LIST}cardiac_arrest/', {'lang': 'en'}).json()
        unknown = self.client.get(f'{self.LIST}zzz_unknown/', {'lang': 'en'}).json()
        self.assertEqual(draft, unknown)
        r = self.client.get(self.META, {'lang': 'en'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['protocol_count'], 0)
        self.assertEqual(r.json()['data']['emergency_number'], str(settings.EMERGENCY_NUMBER))
        self.assertEqual(r.json()['data']['languages'], ['fr', 'en'])

    # --- lang strict -------------------------------------------------------------------

    def test_lang_is_mandatory_and_strict(self):
        for params in ({}, {'lang': 'de'}, {'lang': 'FR'}, {'lang': ''}, {'lang': 'fr,en'}):
            for url in (self.LIST, f'{self.LIST}unconscious_breathing/', self.META):
                r = self.client.get(url, params)
                self.assertEqual(r.status_code, 400, (url, params))
                body = r.json()
                self.assertFalse(body['success'])
                self.assertEqual(body['error']['code'], 'lang_required')
                self.assertIn('obligatoire', body['error']['message'])   # français
                self.assertIn('required', body['error']['message'])      # anglais
        # Accept-Language est ignoré
        r = self.client.get(self.LIST, HTTP_ACCEPT_LANGUAGE='fr')
        self.assertEqual(r.status_code, 400)

    # --- avec ALLOW_DRAFTS : contenu complet, une seule langue, champs expurgés ---------

    @override_settings(FIRSTAID_ALLOW_DRAFTS=True)
    def test_list_and_detail_with_drafts_allowed(self):
        protocols = load_protocols(REAL)
        r = self.client.get(self.LIST, {'lang': 'fr'})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body['count'], 2)
        self.assertEqual([x['id'] for x in body['results']], ['cardiac_arrest', 'unconscious_breathing'])
        for item in body['results']:
            self.assertEqual(set(item), {'id', 'title', 'description', 'version', 'updated_at', 'status', 'variants'})
            p = protocols[item['id']]
            self.assertEqual(item['title'], p.title.fr)
            self.assertEqual(item['version'], p.version)
            self.assertEqual(item['status'], 'draft_unvalidated')
            detail = self.client.get(f"{self.LIST}{item['id']}/", {'lang': 'fr'}).json()['data']
            self.assertEqual(item['status'], detail['status'])
        self.assertEqual(self.client.get(self.META, {'lang': 'fr'}).json()['data']['protocol_count'], 2)

        for pid, p in protocols.items():
            for lang, other in (('fr', 'en'), ('en', 'fr')):
                r = self.client.get(f'{self.LIST}{pid}/', {'lang': lang})
                self.assertEqual(r.status_code, 200, pid)
                body = r.json()
                self.assertTrue(body['success'])
                data = body['data']
                self.assertEqual(data['id'], pid)
                self.assertEqual(data['lang'], lang)
                self.assertEqual(data['emergency_number'], str(settings.EMERGENCY_NUMBER))
                self.assertNotIn('review_notes', data)
                self.assertEqual(data['validated_by'], [])      # brouillon : liste vide, mais clé présente
                raw = json.dumps(body, ensure_ascii=False)
                for t in p.all_texts():
                    if t in p.review_notes:
                        self.assertNotIn(json.dumps(t.get(lang), ensure_ascii=False), raw, 'review_notes a fui')
                        continue
                    self.assertNotIn(json.dumps(t.get(other), ensure_ascii=False), raw,
                                     f'{pid}/{lang} contient « {t.get(other)} »')
                    self.assertIn(json.dumps(t.get(lang), ensure_ascii=False), raw)
                # structure attendue par l'app mobile
                for key in ('title', 'description', 'version', 'status', 'call_emergency_first', 'variants',
                            'decision_tree', 'action_blocks', 'red_flags', 'do_not', 'sources'):
                    self.assertIn(key, data, key)

    # --- cache : ETag et Cache-Control ----------------------------------------------------

    @override_settings(FIRSTAID_ALLOW_DRAFTS=True)
    def test_etag_and_cache_headers(self):
        fr = self.client.get(f'{self.LIST}unconscious_breathing/', {'lang': 'fr'})
        en = self.client.get(f'{self.LIST}unconscious_breathing/', {'lang': 'en'})
        other = self.client.get(f'{self.LIST}cardiac_arrest/', {'lang': 'fr'})
        for r in (fr, en, other):
            self.assertEqual(r['Cache-Control'], 'public, max-age=3600')
            self.assertTrue(r['ETag'].startswith('"') and r['ETag'].endswith('"'))
        self.assertNotEqual(fr['ETag'], en['ETag'])
        self.assertNotEqual(fr['ETag'], other['ETag'])
        # If-None-Match → 304 sans corps
        again = self.client.get(f'{self.LIST}unconscious_breathing/', {'lang': 'fr'}, HTTP_IF_NONE_MATCH=fr['ETag'])
        self.assertEqual(again.status_code, 304)
        self.assertEqual(again['ETag'], fr['ETag'])
        # une autre version produit un autre ETag
        with _TmpProtocols() as d:
            _replace_once(d / MAIN, 'version: 3\n', 'version: 99\n')
            from .loader import registry
            registry.load(d)
            bumped = self.client.get(f'{self.LIST}unconscious_breathing/', {'lang': 'fr'})
            self.assertEqual(bumped.status_code, 200)
            self.assertNotEqual(bumped['ETag'], fr['ETag'])
        # la liste et meta sont aussi mis en cache
        for url in (self.LIST, self.META):
            r = self.client.get(url, {'lang': 'fr'})
            self.assertEqual(r['Cache-Control'], 'public, max-age=3600')
            self.assertIn('ETag', r)
        # l'ETag de la liste change si un status change (même ids, mêmes versions)
        from .loader import registry
        registry.load(REAL)
        before = self.client.get(self.LIST, {'lang': 'fr'})['ETag']
        with _TmpProtocols() as d:
            _replace_once(d / MAIN, 'status: draft_unvalidated', 'status: under_review')
            registry.load(d)
            after = self.client.get(self.LIST, {'lang': 'fr'})['ETag']
        self.assertNotEqual(before, after)

    # --- un protocole validé et signé sort sans ALLOW_DRAFTS -----------------------------

    def test_validated_protocol_is_served_without_allow_drafts(self):
        self.assertFalse(settings.FIRSTAID_ALLOW_DRAFTS)
        with _TmpProtocols() as d:
            path = d / MAIN
            _replace_once(path, 'status: draft_unvalidated', 'status: validated')
            _replace_once(path, 'validated_by: []\n', SIGNATURE)
            from .loader import registry
            registry.load(d)
            lst = self.client.get(self.LIST, {'lang': 'fr'}).json()
            self.assertEqual([x['id'] for x in lst['results']], ['unconscious_breathing'])
            self.assertEqual(lst['results'][0]['status'], 'validated')
            self.assertEqual(self.client.get(self.META, {'lang': 'fr'}).json()['data']['protocol_count'], 1)
            r = self.client.get(f'{self.LIST}unconscious_breathing/', {'lang': 'fr'})
            self.assertEqual(r.status_code, 200)
            data = r.json()['data']
            self.assertEqual(data['status'], 'validated')
            # validated_by réduit : name, qualification, date — ni organisation ni autre champ
            self.assertEqual(data['validated_by'], [
                {'name': 'Dr Test Médecin', 'qualification': 'Médecin urgentiste', 'date': '2026-11-09'},
            ])
            self.assertNotIn('review_notes', data)
            # le brouillon voisin reste invisible
            self.assertEqual(self.client.get(f'{self.LIST}cardiac_arrest/', {'lang': 'fr'}).status_code, 404)

    def test_throttle_is_active(self):
        from unittest import mock
        from rest_framework.throttling import SimpleRateThrottle
        with mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, {'firstaid': '2/hour'}):
            self.assertEqual(self.client.get(self.META, {'lang': 'fr'}).status_code, 200)
            self.assertEqual(self.client.get(self.META, {'lang': 'fr'}).status_code, 200)
            self.assertEqual(self.client.get(self.META, {'lang': 'fr'}).status_code, 429)

    def test_only_get_is_allowed(self):
        for method in ('post', 'put', 'patch', 'delete'):
            r = getattr(self.client, method)(f'{self.LIST}?lang=fr', {}, format='json')
            self.assertEqual(r.status_code, 405, method)


# ==============================================================================
# Détection de langue (sans modèle)
# ==============================================================================

class LangDetectTests(SimpleTestCase):

    def test_french(self):
        from .lang import detect_lang
        self.assertEqual(detect_lang('mon frère est tombé, il ne répond pas mais il respire'), 'fr')
        self.assertEqual(detect_lang("j'ai mal à la tête depuis ce matin"), 'fr')
        self.assertEqual(detect_lang('Oui, elle réagit'), 'fr')

    def test_english(self):
        from .lang import detect_lang
        self.assertEqual(detect_lang('my father collapsed, he is not breathing'), 'en')
        self.assertEqual(detect_lang("he isn't moving and there is blood"), 'en')
        self.assertEqual(detect_lang('No, no reaction'), 'en')

    def test_undecidable(self):
        from .lang import detect_lang
        for text in ('', '   ', None, 'ok', '442', 'OK!!!', '...'):
            self.assertIsNone(detect_lang(text), repr(text))

    def test_mixed_tie_is_undecidable(self):
        from .lang import detect_lang
        # un indice français, un indice anglais : égalité → None, on ne devine pas
        self.assertIsNone(detect_lang('il respire he breathes'))


# ==============================================================================
# Classification : POST classify/ et answer/ — client Groq mocké, aucun réseau
# ==============================================================================

TRAP = 'TRAP_PHRASE_DU_MODELE_7731'  # ne doit JAMAIS apparaître dans une réponse HTTP


class _FakeClient:
    """Remplace GroqClient : rejoue des sorties scriptées et enregistre les prompts envoyés."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []  # [(system, user)]

    def complete(self, system, user, **kw):
        self.calls.append((system, user))
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


class _ClassifyMixin:
    CLASSIFY = '/api/v1/firstaid/classify/'
    ANSWER = '/api/v1/firstaid/answer/'

    def setUp(self):
        from unittest import mock
        from django.core.cache import cache
        from rest_framework.test import APIClient
        cache.clear()
        self.client = APIClient()
        from .loader import registry
        registry.load(REAL)
        self.fake = _FakeClient([])
        patcher = mock.patch('apps.firstaid.classify.get_client', return_value=self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        from .loader import registry
        registry.load(REAL)

    def post(self, url, body):
        return self.client.post(url, body, format='json')

    def classify(self, text, lang=None, outputs=(), **extra):
        self.fake.outputs = list(outputs)
        body = {'text': text, **extra}
        if lang is not None:
            body['lang'] = lang
        return self.post(self.CLASSIFY, body)


@override_settings(FIRSTAID_ALLOW_DRAFTS=True)
class ClassifyApiTests(_ClassifyMixin, SimpleTestCase):

    def test_scenario_recognized_and_lang_detected(self):
        r = self.classify('mon frère est tombé, il ne répond pas mais il respire',
                          outputs=['{"scenario": "unconscious_breathing", "confidence": 0.92}'])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r['Cache-Control'], 'no-store')
        data = r.json()['data']
        self.assertEqual(data['lang'], 'fr')
        self.assertEqual(data['scenario'], 'unconscious_breathing')
        self.assertEqual(data['confidence'], 0.92)
        self.assertEqual(data['emergency_number'], str(settings.EMERGENCY_NUMBER))
        self.assertEqual(set(data['protocol']), {'id', 'title', 'description', 'version', 'status'})
        self.assertEqual(data['protocol']['id'], 'unconscious_breathing')
        self.assertEqual(data['protocol']['title'], 'Personne inconsciente qui respire')
        self.assertEqual(data['protocol']['status'], 'draft_unvalidated')
        # un seul appel, prompt système en français, texte utilisateur dans le message user
        self.assertEqual(len(self.fake.calls), 1)
        system, user = self.fake.calls[0]
        self.assertTrue(system.startswith('Tu es un classifieur.'))
        self.assertIn('- unconscious_breathing : Personne inconsciente qui respire', system)
        self.assertIn('- cardiac_arrest : Personne inconsciente qui ne respire pas normalement', system)
        self.assertIn('- none', system)
        self.assertNotIn('Unresponsive', system)          # rien en anglais dans le prompt fr
        # titre ET description du protocole, dans la langue du prompt
        self.assertIn('— La personne ne réagit ni à la voix ni au toucher', system)
        self.assertIn('— La personne ne réagit pas et ne respire pas', system)
        # règle de routage, avec l'id d'entrée puisque unconscious_breathing est publiable
        self.assertIn('Règles de routage', system)
        self.assertIn('choisis unconscious_breathing : son parcours vérifie ensuite la respiration', system)
        self.assertIn('la grossesse', system)
        self.assertEqual(user, 'mon frère est tombé, il ne répond pas mais il respire')
        self.assertNotIn('442', system)                    # pas de numéro d'urgence dans le prompt

    def test_explicit_english_prompt(self):
        r = self.classify('my father collapsed, he is not breathing', lang='en',
                          outputs=['{"scenario": "cardiac_arrest", "confidence": 0.95}'])
        self.assertEqual(r.status_code, 200)
        data = r.json()['data']
        self.assertEqual(data['lang'], 'en')
        self.assertEqual(data['scenario'], 'cardiac_arrest')
        self.assertEqual(data['protocol']['title'], 'Unresponsive person who is not breathing normally')
        system, _ = self.fake.calls[0]
        self.assertTrue(system.startswith('You are a classifier.'))
        self.assertIn('- cardiac_arrest: Unresponsive person who is not breathing normally', system)
        self.assertNotIn('Personne inconsciente', system)  # rien en français dans le prompt en
        self.assertIn('— The person does not respond and is not breathing', system)
        self.assertIn('Routing rules', system)
        self.assertIn('choose unconscious_breathing: its pathway then checks breathing', system)

    def test_none_scenario(self):
        r = self.classify("j'ai mal à la tête depuis ce matin",
                          outputs=['{"scenario": "none", "confidence": 0.9}'])
        data = r.json()['data']
        self.assertIsNone(data['scenario'])
        self.assertIsNone(data['protocol'])
        self.assertEqual(data['confidence'], 0.9)

    def test_invalid_json_is_none_zero(self):
        for raw in ('pas du json', '```json\n{"scenario": "cardiac_arrest", "confidence": 0.9}\n```',
                    '[1, 2]', '{"confidence": 0.9}', '{"scenario": "cardiac_arrest"}',
                    '{"scenario": "cardiac_arrest", "confidence": "0.9"}',
                    '{"scenario": "cardiac_arrest", "confidence": 1.2}',
                    '{"scenario": "cardiac_arrest", "confidence": -0.1}',
                    '{"scenario": "cardiac_arrest", "confidence": true}'):
            with self.assertLogs('apps.firstaid.classify', level='WARNING'):
                r = self.classify('il ne respire plus', outputs=[raw])
            data = r.json()['data']
            self.assertIsNone(data['scenario'], raw)
            self.assertEqual(data['confidence'], 0.0, raw)
            self.assertIsNone(data['protocol'], raw)

    def test_invented_scenario_is_none_zero(self):
        with self.assertLogs('apps.firstaid.classify', level='WARNING'):
            r = self.classify('il ne respire plus', outputs=['{"scenario": "snake_bite", "confidence": 0.99}'])
        data = r.json()['data']
        self.assertIsNone(data['scenario'])
        self.assertEqual(data['confidence'], 0.0)

    def test_below_threshold_is_null_with_confidence(self):
        self.assertEqual(settings.FIRSTAID_CLASSIFY_MIN, 0.6)
        r = self.classify('il est tombé', outputs=['{"scenario": "cardiac_arrest", "confidence": 0.4}'])
        data = r.json()['data']
        self.assertIsNone(data['scenario'])
        self.assertIsNone(data['protocol'])
        self.assertEqual(data['confidence'], 0.4)
        r = self.classify('il est tombé', outputs=['{"scenario": "cardiac_arrest", "confidence": 0.6}'])
        self.assertEqual(r.json()['data']['scenario'], 'cardiac_arrest')  # seuil inclus

    @override_settings(FIRSTAID_ALLOW_DRAFTS=False)
    def test_unpublishable_draft_never_offered_to_model(self):
        with _TmpProtocols() as d:
            path = d / MAIN
            _replace_once(path, 'status: draft_unvalidated', 'status: validated')
            _replace_once(path, 'validated_by: []\n', SIGNATURE)
            from .loader import registry
            registry.load(d)                     # unconscious_breathing publiable, cardiac_arrest brouillon
            r = self.classify('il ne respire plus', outputs=['{"scenario": "cardiac_arrest", "confidence": 0.99}'])
            system, _ = self.fake.calls[0]
            self.assertIn('unconscious_breathing', system)
            self.assertNotIn('cardiac_arrest', system)
            # même si le modèle le nomme quand même, il est hors liste → null / 0
            data = r.json()['data']
            self.assertIsNone(data['scenario'])
            self.assertEqual(data['confidence'], 0.0)

    @override_settings(FIRSTAID_ALLOW_DRAFTS=False)
    def test_routing_rule_names_entry_only_when_publishable(self):
        with _TmpProtocols() as d:
            path = d / 'cardiac_arrest.yaml'
            _replace_once(path, 'status: draft_unvalidated', 'status: validated')
            _replace_once(path, 'validated_by: []\n', SIGNATURE)
            from .loader import registry
            registry.load(d)                     # cardiac_arrest publiable, unconscious_breathing brouillon
            for lang in LANGS:
                self.fake.calls.clear()
                self.classify('x', lang=lang, outputs=['{"scenario": "none", "confidence": 1}'])
                system, _ = self.fake.calls[0]
                self.assertIn('cardiac_arrest', system)
                self.assertNotIn('unconscious_breathing', system, lang)   # ni candidat, ni règle de routage
                self.assertIn('Règles de routage' if lang == 'fr' else 'Routing rules', system)

    @override_settings(FIRSTAID_ALLOW_DRAFTS=False)
    def test_no_publishable_means_no_model_call(self):
        r = self.classify('il ne respire plus', outputs=['{"scenario": "cardiac_arrest", "confidence": 0.99}'])
        self.assertEqual(r.status_code, 200)
        data = r.json()['data']
        self.assertIsNone(data['scenario'])
        self.assertEqual(data['confidence'], 0.0)
        self.assertIsNone(data['protocol'])
        self.assertEqual(self.fake.calls, [])

    def test_lang_undetermined_and_invalid(self):
        r = self.classify('ok')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['code'], 'lang_undetermined')
        self.assertIn('/', r.json()['error']['message'])       # bilingue
        r = self.classify('442', lang=None)
        self.assertEqual(r.json()['error']['code'], 'lang_undetermined')
        r = self.classify('ok', lang='de')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['code'], 'lang_invalid')
        r = self.post(self.CLASSIFY, {'text': 'ok', 'lang': None})   # null explicite → détection
        self.assertEqual(r.json()['error']['code'], 'lang_undetermined')
        self.assertEqual(self.fake.calls, [])

    def test_text_validation(self):
        for body in ({}, {'text': ''}, {'text': '   '}, {'text': 42}, {'text': None}):
            r = self.post(self.CLASSIFY, body)
            self.assertEqual(r.status_code, 400, body)
            self.assertEqual(r.json()['error']['code'], 'text_required', body)
        r = self.classify('a' * 1001, lang='fr')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['code'], 'text_too_long')
        self.fake.outputs = ['{"scenario": "none", "confidence": 1}']
        r = self.classify('a' * 1000, lang='fr', outputs=['{"scenario": "none", "confidence": 1}'])
        self.assertEqual(r.status_code, 200)
        r = self.post(self.CLASSIFY, [1, 2])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['error']['code'], 'body_invalid')

    def test_classifier_unavailable_is_503(self):
        from .classify import ClassifierUnavailable
        r = self.classify('il ne respire plus', outputs=[ClassifierUnavailable('HTTP 500')])
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()['error']['code'], 'classifier_unavailable')
        self.assertNotIn('HTTP 500', r.content.decode())

    @override_settings(GROQ_API_KEY='')
    def test_missing_key_is_503_without_mock(self):
        from unittest import mock
        from .classify import GroqClient
        with mock.patch('apps.firstaid.classify.get_client', return_value=GroqClient()):
            with mock.patch('apps.firstaid.classify.requests.post') as post:
                r = self.classify('il ne respire plus')
                self.assertEqual(r.status_code, 503)
                post.assert_not_called()

    def test_model_text_never_leaks(self):
        traps = [
            f'{TRAP} prenez de l\'aspirine',
            f'{{"scenario": "{TRAP}", "confidence": 0.99}}',
            f'{{"scenario": "cardiac_arrest", "confidence": 0.99, "advice": "{TRAP}"}}',
            f'{{"scenario": "none", "confidence": 0.5, "message": "{TRAP}"}}',
        ]
        for raw in traps:
            r = self.classify('il ne respire plus', outputs=[raw])
            self.assertEqual(r.status_code, 200, raw)
            self.assertNotIn(TRAP, r.content.decode(), raw)
        # texte du protocole : vient du YAML, pas du modèle
        self.assertEqual(self.classify('x', lang='fr', outputs=[traps[2]]).json()['data']['protocol']['title'],
                         'Personne inconsciente qui ne respire pas normalement')

    def test_only_post_is_allowed(self):
        for method in ('get', 'put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)(self.CLASSIFY).status_code, 405, method)
            self.assertEqual(getattr(self.client, method)(self.ANSWER).status_code, 405, method)


@override_settings(FIRSTAID_ALLOW_DRAFTS=True)
class AnswerApiTests(_ClassifyMixin, SimpleTestCase):

    OPTIONS = {'yes': 'Oui, elle réagit', 'no': 'Non, aucune réaction'}

    def answer(self, text, lang=None, outputs=(), options=None):
        self.fake.outputs = list(outputs)
        body = {'text': text, 'options': self.OPTIONS if options is None else options}
        if lang is not None:
            body['lang'] = lang
        return self.post(self.ANSWER, body)

    def test_trivial_yes_no_without_model(self):
        for text, expected in (('Oui', 'yes'), ('oui !', 'yes'), ('yes', 'yes'), ('Non.', 'no'),
                               ('no', 'no'), ('NON', 'no')):
            r = self.answer(text, lang='fr')
            self.assertEqual(r.status_code, 200, text)
            self.assertEqual(r.json()['data']['answer'], expected, text)
            self.assertEqual(r.json()['data']['confidence'], 1.0)
            self.assertEqual(r['Cache-Control'], 'no-store')
        self.assertEqual(self.fake.calls, [])

    def test_trivial_shortcut_only_if_key_exists(self):
        r = self.answer('oui', lang='fr', options={'moves': 'Elle bouge', 'still': 'Elle ne bouge pas'},
                        outputs=['{"answer": "unclear", "confidence": 0.9}'])
        self.assertIsNone(r.json()['data']['answer'])
        self.assertEqual(len(self.fake.calls), 1)   # pas de raccourci : le modèle a été appelé

    def test_via_model(self):
        r = self.answer('elle a bougé un peu la main quand je lui ai parlé',
                        outputs=['{"answer": "yes", "confidence": 0.85}'])
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()['data']
        self.assertEqual(data, {'lang': 'fr', 'answer': 'yes', 'confidence': 0.85})
        system, user = self.fake.calls[0]
        self.assertTrue(system.startswith('Tu es un classifieur.'))
        self.assertIn('- yes : Oui, elle réagit', system)
        self.assertIn('- no : Non, aucune réaction', system)
        self.assertIn('- unclear', system)
        self.assertEqual(user, 'elle a bougé un peu la main quand je lui ai parlé')

    def test_via_model_english(self):
        r = self.answer('she moved her hand a little when I spoke', lang='en',
                        options={'yes': 'Yes, she reacts', 'no': 'No reaction'},
                        outputs=['{"answer": "yes", "confidence": 0.8}'])
        self.assertEqual(r.json()['data']['answer'], 'yes')
        self.assertTrue(self.fake.calls[0][0].startswith('You are a classifier.'))

    def test_unclear_invented_and_threshold(self):
        r = self.answer('je ne sais pas trop', outputs=['{"answer": "unclear", "confidence": 0.9}'])
        self.assertEqual(r.json()['data'], {'lang': 'fr', 'answer': None, 'confidence': 0.9})
        with self.assertLogs('apps.firstaid.classify', level='WARNING'):
            r = self.answer('je ne sais pas trop', outputs=['{"answer": "maybe", "confidence": 0.9}'])
        self.assertEqual(r.json()['data'], {'lang': 'fr', 'answer': None, 'confidence': 0.0})
        with self.assertLogs('apps.firstaid.classify', level='WARNING'):
            r = self.answer('je ne sais pas trop', outputs=['pas du json'])
        self.assertEqual(r.json()['data'], {'lang': 'fr', 'answer': None, 'confidence': 0.0})
        r = self.answer('elle bouge un peu', outputs=['{"answer": "yes", "confidence": 0.3}'])
        self.assertEqual(r.json()['data'], {'lang': 'fr', 'answer': None, 'confidence': 0.3})

    def test_options_validation(self):
        bad = [None, 'x', {}, {'yes': 'Oui'}, {'yes': 'Oui', 'no': ''}, {'yes': 'Oui', 'no': 3},
               {'Yes': 'Oui', 'no': 'Non'}, {'yes': 'Oui', 'unclear': 'Non'}, {'yes': 'Oui', 'no': 'x' * 121},
               {f'k{i}': 'v' for i in range(9)}]
        for options in bad:
            r = self.post(self.ANSWER, {'text': 'elle bouge', 'lang': 'fr', 'options': options})
            self.assertEqual(r.status_code, 400, options)
            self.assertEqual(r.json()['error']['code'], 'options_invalid', options)
        self.assertEqual(self.fake.calls, [])
        r = self.post(self.ANSWER, {'text': 'ok', 'options': self.OPTIONS})
        self.assertEqual(r.json()['error']['code'], 'lang_undetermined')

    def test_model_text_never_leaks(self):
        for raw in (f'{TRAP} allongez-la', f'{{"answer": "{TRAP}", "confidence": 0.9}}',
                    f'{{"answer": "yes", "confidence": 0.9, "note": "{TRAP}"}}'):
            r = self.answer('elle bouge un peu', outputs=[raw])
            self.assertEqual(r.status_code, 200)
            self.assertNotIn(TRAP, r.content.decode(), raw)

    def test_classifier_unavailable_is_503(self):
        from .classify import ClassifierUnavailable
        r = self.answer('elle bouge un peu', outputs=[ClassifierUnavailable('délai')])
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()['error']['code'], 'classifier_unavailable')
