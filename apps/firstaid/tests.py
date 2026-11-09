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
