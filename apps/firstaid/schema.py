"""
Schéma d'un protocole de premiers secours et règles de validation.

Ce module ne lit aucun fichier : il reçoit des dictionnaires déjà chargés
(avec les numéros de ligne injectés par le chargeur) et produit soit un objet
`Protocol`, soit une liste d'erreurs localisées (fichier + ligne).

Toutes les règles « bloquantes » du cahier des charges vivent ici :
- 'validated' sans signataire → refusé
- source ou source_page manquante → refusé
- étape de 15 mots ou plus (dans l'une OU l'autre langue) → refusée
- réponse vers une question inexistante → refusée
- numéro d'urgence écrit en dur (dans l'une OU l'autre langue) → refusé
- texte affiché sans ses DEUX langues fr et en → refusé, aucun repli

Bilinguisme : tout texte destiné à l'utilisateur est un dictionnaire
{fr: ..., en: ...}. Les deux clés sont obligatoires et non vides, toute autre
clé est refusée. Un endpoint n'obtient du texte que par Protocol.localized(lang),
qui sert une seule langue, sans valeur par défaut et sans repli.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Any

# ------------------------------------------------------------------------------
# Constantes du schéma
# ------------------------------------------------------------------------------

LINE_KEY = '__line__'                      # clé injectée par le chargeur YAML


class LineInfo(int):
    """Ligne d'un bloc YAML ; `.keys` donne la ligne de chacune de ses clés."""
    keys: dict[str, int] = {}


LANGS = ('fr', 'en')                       # les deux langues servies, rien d'autre

STATUS_DRAFT = 'draft_unvalidated'
STATUS_REVIEW = 'under_review'
STATUS_VALIDATED = 'validated'
STATUSES = (STATUS_DRAFT, STATUS_REVIEW, STATUS_VALIDATED)

VARIANTS = ('adult', 'child', 'infant')    # adulte / enfant / nourrisson

MAX_STEP_WORDS = 14                        # « moins de 15 mots », par langue

ID_RE = re.compile(r'^[a-z][a-z0-9_]{2,63}$')
PAGE_PLACEHOLDER_NUMBER = '{emergency_number}'   # seul moyen d'afficher le numéro

# Numéros d'urgence courants : leur présence littérale dans un texte est une
# erreur, le numéro vient toujours de settings.EMERGENCY_NUMBER.
FORBIDDEN_NUMBERS_RE = re.compile(r'(?<!\d)(442|112|911|999|115|117|122)(?!\d)')

# Un seul type de cible par réponse du decision_tree
ANSWER_TARGET_KEYS = ('next_question', 'action_block', 'switch_to')


# ------------------------------------------------------------------------------
# Erreurs
# ------------------------------------------------------------------------------

@dataclass(frozen=True)
class ProtocolError:
    """Une erreur de validation localisée dans un fichier."""
    file: str
    line: int | None
    message: str

    def __str__(self) -> str:
        where = f'{self.file}:{self.line}' if self.line else self.file
        return f'{where} — {self.message}'


class ProtocolValidationError(Exception):
    """Levée par le chargeur quand au moins un protocole est invalide."""

    def __init__(self, errors: list[ProtocolError]):
        self.errors = list(errors)
        lines = '\n'.join(f'  • {e}' for e in self.errors)
        super().__init__(
            f'{len(self.errors)} erreur(s) dans les protocoles de premiers secours :\n{lines}'
        )


# ------------------------------------------------------------------------------
# Structures validées
# ------------------------------------------------------------------------------

@dataclass(frozen=True)
class LocalizedText:
    """
    Un texte affiché, dans ses deux langues. Les deux sont toujours présentes :
    la validation l'impose, il n'existe donc aucun repli d'une langue sur l'autre.
    """
    fr: str
    en: str

    def get(self, lang: str) -> str:
        if lang not in LANGS:
            raise ValueError(f"langue non supportée : {lang!r} (attendu 'fr' ou 'en')")
        return getattr(self, lang)

    def values(self) -> tuple[str, str]:
        return (self.fr, self.en)


@dataclass(frozen=True)
class Validator:
    name: str
    qualification: str
    organisation: str
    date: _dt.date


@dataclass(frozen=True)
class Source:
    key: str
    organisation: str
    title: str
    edition: str              # année ou version, texte libre (« 2025 », « 2020 FR »)
    url: str
    licence: str
    pages: tuple[int, ...]    # pages citées, dans l'édition indiquée
    role: str                 # 'content' | 'terminology'


@dataclass(frozen=True)
class SourcePage:
    source: str               # clé d'une entrée de `sources`
    page: int


@dataclass(frozen=True)
class Step:
    number: int
    text: LocalizedText
    source_page: SourcePage
    visual: str = ''          # réservé : identifiant d'illustration, vide pour l'instant
    timer_seconds: int | None = None


@dataclass(frozen=True)
class ActionBlock:
    id: str
    title: LocalizedText
    # soit des étapes communes, soit des étapes par variante (adult/child/infant)
    steps: tuple[Step, ...] = ()
    variants: dict[str, tuple[Step, ...]] = field(default_factory=dict)
    next_question: str | None = None   # question posée une fois les étapes faites

    def steps_for(self, variant: str = 'adult') -> tuple[Step, ...]:
        if self.variants:
            return self.variants.get(variant) or self.variants.get('adult') or ()
        return self.steps

    def all_steps(self) -> tuple[Step, ...]:
        if self.variants:
            return tuple(s for steps in self.variants.values() for s in steps)
        return self.steps


@dataclass(frozen=True)
class Answer:
    label: LocalizedText
    next_question: str | None = None
    action_block: str | None = None
    switch_to: str | None = None


@dataclass(frozen=True)
class Question:
    id: str
    text: LocalizedText
    answers: dict[str, Answer]      # clé = valeur de réponse ('yes', 'no', ...)


@dataclass(frozen=True)
class DecisionTree:
    entry: str
    questions: dict[str, Question]


@dataclass(frozen=True)
class Flag:
    """Red flag ou interdit : une phrase et sa page source."""
    text: LocalizedText
    source_page: SourcePage
    switch_to: str | None = None       # red flag : scénario vers lequel basculer


@dataclass(frozen=True)
class Protocol:
    id: str
    title: LocalizedText
    description: LocalizedText
    version: int
    updated_at: _dt.date
    status: str
    validated_by: tuple[Validator, ...]
    sources: dict[str, Source]
    call_emergency_first: bool
    decision_tree: DecisionTree
    action_blocks: dict[str, ActionBlock]
    red_flags: tuple[Flag, ...]
    do_not: tuple[Flag, ...]
    variants: dict[str, LocalizedText]    # variante → libellé
    vision_checkpoints: tuple[Any, ...]   # réservé, vide pour l'instant
    incomplete: bool                      # squelette non rédigé, jamais publiable
    file: str

    @property
    def is_validated(self) -> bool:
        return self.status == STATUS_VALIDATED and bool(self.validated_by)

    # --- textes -------------------------------------------------------------

    def all_texts(self) -> tuple[LocalizedText, ...]:
        """Tous les textes affichables du protocole (pour audits et tests)."""
        out: list[LocalizedText] = [self.title, self.description, *self.variants.values()]
        for q in self.decision_tree.questions.values():
            out.append(q.text)
            out.extend(a.label for a in q.answers.values())
        for b in self.action_blocks.values():
            out.append(b.title)
            out.extend(s.text for s in b.all_steps())
        out.extend(f.text for f in self.red_flags)
        out.extend(f.text for f in self.do_not)
        return tuple(out)

    def localized(self, lang: str) -> dict[str, Any]:
        """
        Vue plate du protocole dans UNE seule langue.

        C'est la seule voie par laquelle un endpoint obtient du texte. `lang`
        n'a pas de valeur par défaut ; toute valeur autre que 'fr' ou 'en'
        lève ValueError. Aucun texte d'une autre langue ne peut apparaître :
        chaque LocalizedText porte obligatoirement les deux langues.
        """
        if lang not in LANGS:
            raise ValueError(f"langue non supportée : {lang!r} (attendu 'fr' ou 'en')")

        def t(text: LocalizedText) -> str:
            return text.get(lang)

        def step(s: Step) -> dict[str, Any]:
            return {
                'number': s.number,
                'text': t(s.text),
                'visual': s.visual,
                'timer_seconds': s.timer_seconds,
                'source': {'key': s.source_page.source, 'page': s.source_page.page},
            }

        def block(b: ActionBlock) -> dict[str, Any]:
            out: dict[str, Any] = {'id': b.id, 'title': t(b.title), 'next_question': b.next_question}
            if b.variants:
                out['variants'] = {v: [step(s) for s in steps] for v, steps in b.variants.items()}
            else:
                out['steps'] = [step(s) for s in b.steps]
            return out

        def flag(f: Flag) -> dict[str, Any]:
            out: dict[str, Any] = {
                'text': t(f.text),
                'source': {'key': f.source_page.source, 'page': f.source_page.page},
            }
            if f.switch_to:
                out['switch_to'] = f.switch_to
            return out

        return {
            'id': self.id,
            'lang': lang,
            'title': t(self.title),
            'description': t(self.description),
            'version': self.version,
            'updated_at': self.updated_at.isoformat(),
            'status': self.status,
            'call_emergency_first': self.call_emergency_first,
            'variants': {k: t(v) for k, v in self.variants.items()},
            'decision_tree': {
                'entry': self.decision_tree.entry,
                'questions': {
                    qid: {
                        'text': t(q.text),
                        'answers': {
                            akey: {
                                'label': t(a.label),
                                'next_question': a.next_question,
                                'action_block': a.action_block,
                                'switch_to': a.switch_to,
                            }
                            for akey, a in q.answers.items()
                        },
                    }
                    for qid, q in self.decision_tree.questions.items()
                },
            },
            'action_blocks': {bid: block(b) for bid, b in self.action_blocks.items()},
            'red_flags': [flag(f) for f in self.red_flags],
            'do_not': [flag(f) for f in self.do_not],
            'sources': [
                {
                    'key': s.key, 'organisation': s.organisation, 'title': s.title,
                    'edition': s.edition, 'url': s.url, 'licence': s.licence,
                    'role': s.role, 'pages': list(s.pages),
                }
                for s in self.sources.values()
            ],
        }


# ------------------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------------------

def word_count(text: str) -> int:
    """Compte les mots d'une étape (séparés par des espaces)."""
    return len([w for w in text.replace('\n', ' ').split(' ') if w.strip()])


class _Ctx:
    """Accumule les erreurs d'un fichier et fournit des accesseurs typés."""

    def __init__(self, file: str):
        self.file = file
        self.errors: list[ProtocolError] = []

    def err(self, node: Any, message: str, key: str | None = None) -> None:
        """Ajoute une erreur ; `key` cible la ligne précise d'un champ du bloc."""
        line = node.get(LINE_KEY) if isinstance(node, dict) else None
        if key is not None and isinstance(line, LineInfo):
            line = line.keys.get(key, line)
        self.errors.append(ProtocolError(self.file, int(line) if line is not None else None, message))

    # --- accesseurs ---------------------------------------------------------

    def req(self, node: dict, key: str, typ: type | tuple, label: str = '') -> Any:
        """Champ obligatoire du type attendu ; sinon erreur + None."""
        label = label or key
        if key not in node:
            self.err(node, f"champ obligatoire manquant : '{label}'")
            return None
        val = node[key]
        if typ is bool and not isinstance(val, bool):
            self.err(node, f"'{label}' doit être un booléen (true/false)", key)
            return None
        if typ is int and (isinstance(val, bool) or not isinstance(val, int)):
            self.err(node, f"'{label}' doit être un entier", key)
            return None
        if typ is str and (not isinstance(val, str) or not val.strip()):
            self.err(node, f"'{label}' doit être une chaîne non vide", key)
            return None
        if typ is list and not isinstance(val, list):
            self.err(node, f"'{label}' doit être une liste", key)
            return None
        if typ is dict and not isinstance(val, dict):
            self.err(node, f"'{label}' doit être un dictionnaire (clé: valeur)", key)
            return None
        return val

    def opt(self, node: dict, key: str, typ: type, default: Any) -> Any:
        if key not in node or node[key] is None:
            return default
        return self.req(node, key, typ)

    def date(self, node: dict, key: str) -> _dt.date | None:
        if key not in node:
            self.err(node, f"champ obligatoire manquant : '{key}'")
            return None
        val = node[key]
        if isinstance(val, _dt.datetime):
            return val.date()
        if isinstance(val, _dt.date):
            return val
        if isinstance(val, str):
            try:
                return _dt.date.fromisoformat(val)
            except ValueError:
                pass
        self.err(node, f"'{key}' doit être une date ISO (AAAA-MM-JJ)")
        return None

    # --- textes bilingues ---------------------------------------------------

    def ltext(self, node: dict, key: str, label: str, *,
              max_words: int | None = None, question: bool = False) -> LocalizedText | None:
        """
        Lit un texte affiché {fr, en}. Chaque règle (présence, non-vide, clé
        inconnue, longueur, « ? », numéro en dur) est vérifiée pour CHAQUE
        langue séparément et rapportée à la ligne de la langue concernée.
        """
        if key not in node:
            self.err(node, f"champ obligatoire manquant : '{label}'")
            return None
        raw = node[key]
        if not isinstance(raw, dict):
            self.err(node, f"'{label}' doit être un dictionnaire {{fr: ..., en: ...}} (texte bilingue)", key)
            return None
        ok = True
        for k in raw:
            if k != LINE_KEY and k not in LANGS:
                self.err(raw, f"'{label}' : clé de langue inconnue '{k}' (seules 'fr' et 'en' sont admises)", k)
                ok = False
        values: dict[str, str] = {}
        for lang in LANGS:
            if lang not in raw:
                self.err(raw, f"'{label}' : langue '{lang}' manquante (aucun repli d'une langue sur l'autre)")
                ok = False
                continue
            val = raw[lang]
            if not isinstance(val, str) or not val.strip():
                hint = ''
                if isinstance(val, bool):
                    hint = " (yes/no/true/false sans guillemets sont lus comme des booléens : écrire \"Yes\")"
                self.err(raw, f"'{label}.{lang}' doit être une chaîne non vide{hint}", lang)
                ok = False
                continue
            if max_words is not None:
                n = word_count(val)
                if n > max_words:
                    self.err(raw, f"'{label}.{lang}' : {n} mots, maximum {max_words} (« {val} »)", lang)
                    ok = False
            if question and not val.strip().endswith('?'):
                self.err(raw, f"'{label}.{lang}' : une question fermée se termine par « ? »", lang)
                ok = False
            if FORBIDDEN_NUMBERS_RE.search(val.replace(PAGE_PLACEHOLDER_NUMBER, '')):
                self.err(raw, f"'{label}.{lang}' : numéro d'urgence écrit en dur — utiliser settings.EMERGENCY_NUMBER", lang)
                ok = False
            values[lang] = val
        if not ok:
            return None
        return LocalizedText(fr=values['fr'], en=values['en'])


def _parse_source_page(ctx: _Ctx, node: dict, sources: dict[str, Source], label: str) -> SourcePage | None:
    sp = node.get('source_page')
    if sp is None:
        ctx.err(node, f"{label} : 'source_page' manquante (chaque consigne doit citer sa page)")
        return None
    if not isinstance(sp, dict):
        ctx.err(node, f"{label} : 'source_page' doit être {{source: clé, page: n}}")
        return None
    src = ctx.req(sp, 'source', str, f'{label}.source_page.source')
    page = ctx.req(sp, 'page', int, f'{label}.source_page.page')
    if src is None or page is None:
        return None
    if src not in sources:
        ctx.err(sp, f"{label} : source '{src}' non déclarée dans 'sources'")
        return None
    if page not in sources[src].pages:
        ctx.err(sp, f"{label} : page {page} absente des pages citées pour '{src}' {list(sources[src].pages)}")
        return None
    return SourcePage(source=src, page=page)


def _parse_sources(ctx: _Ctx, root: dict) -> dict[str, Source]:
    out: dict[str, Source] = {}
    raw = ctx.req(root, 'sources', list)
    if raw is None:
        return out
    if not raw:
        ctx.err(root, "'sources' ne peut pas être vide : au moins une source citée")
        return out
    for i, s in enumerate(raw):
        if not isinstance(s, dict):
            ctx.err(root, f"sources[{i}] doit être un dictionnaire")
            continue
        key = ctx.req(s, 'key', str, f'sources[{i}].key')
        org = ctx.req(s, 'organisation', str, f'sources[{i}].organisation')
        title = ctx.req(s, 'title', str, f'sources[{i}].title')
        edition = s.get('edition')
        if edition is None:
            ctx.err(s, f"sources[{i}] : 'edition' (année/version) manquante")
        edition = str(edition) if edition is not None else ''
        url = ctx.req(s, 'url', str, f'sources[{i}].url')
        licence = ctx.req(s, 'licence', str, f'sources[{i}].licence')
        pages = ctx.req(s, 'pages', list, f'sources[{i}].pages')
        role = ctx.opt(s, 'role', str, 'content')
        if role not in ('content', 'terminology'):
            ctx.err(s, f"sources[{i}] : 'role' doit être 'content' ou 'terminology'")
        if pages is not None:
            if not pages or not all(isinstance(p, int) and not isinstance(p, bool) and p > 0 for p in pages):
                ctx.err(s, f"sources[{i}] : 'pages' doit être une liste non vide d'entiers positifs")
                pages = None
        if key and ID_RE.match(key) is None:
            ctx.err(s, f"sources[{i}] : 'key' doit être un identifiant snake_case")
        if key in out:
            ctx.err(s, f"sources[{i}] : clé '{key}' en double")
        if None in (key, org, title, url, licence, pages):
            continue
        out[key] = Source(key=key, organisation=org, title=title, edition=edition, url=url,
                          licence=licence, pages=tuple(pages), role=role)
    return out


def _parse_steps(ctx: _Ctx, raw: Any, sources: dict[str, Source], label: str) -> tuple[Step, ...]:
    if not isinstance(raw, list) or not raw:
        ctx.err(raw if isinstance(raw, dict) else {}, f"{label} : liste d'étapes vide ou invalide")
        return ()
    steps: list[Step] = []
    for i, st in enumerate(raw, start=1):
        if not isinstance(st, dict):
            ctx.err({}, f"{label}[{i}] doit être un dictionnaire")
            continue
        lab = f'{label} étape {i}'
        text = ctx.ltext(st, 'text', f'{lab}.text', max_words=MAX_STEP_WORDS)
        visual = ctx.opt(st, 'visual', str, '') if st.get('visual') else ''
        timer = st.get('timer_seconds')
        if timer is not None and (isinstance(timer, bool) or not isinstance(timer, int) or timer <= 0):
            ctx.err(st, f"{lab} : 'timer_seconds' doit être un entier positif")
            timer = None
        sp = _parse_source_page(ctx, st, sources, lab)
        if text is None or sp is None:
            continue
        steps.append(Step(number=i, text=text, source_page=sp, visual=visual or '', timer_seconds=timer))
    return tuple(steps)


def _parse_action_blocks(ctx: _Ctx, root: dict, sources: dict[str, Source],
                         variants: dict[str, LocalizedText]) -> dict[str, ActionBlock]:
    out: dict[str, ActionBlock] = {}
    raw = ctx.req(root, 'action_blocks', dict)
    if raw is None:
        return out
    for bid, b in raw.items():
        if bid == LINE_KEY:
            continue
        if not isinstance(b, dict):
            ctx.err(root, f"action_blocks.{bid} doit être un dictionnaire")
            continue
        if ID_RE.match(str(bid)) is None:
            ctx.err(b, f"action_blocks : identifiant '{bid}' invalide (snake_case attendu)")
        title = ctx.ltext(b, 'title', f'action_blocks.{bid}.title')
        nq = b.get('next_question')
        if nq is not None and (not isinstance(nq, str) or not nq.strip()):
            ctx.err(b, f"action_blocks.{bid}.next_question doit être un identifiant de question")
            nq = None
        has_steps = 'steps' in b
        has_variants = 'variants' in b
        if has_steps == has_variants:
            ctx.err(b, f"action_blocks.{bid} : exactement un de 'steps' (commun) ou 'variants' (par âge)")
            continue
        if title is None:
            title = LocalizedText(fr='', en='')      # erreur déjà rapportée ; le protocole sera rejeté
        if has_steps:
            steps = _parse_steps(ctx, b['steps'], sources, f'action_blocks.{bid}.steps')
            out[bid] = ActionBlock(id=bid, title=title, steps=steps, next_question=nq)
        else:
            vr = b['variants']
            if not isinstance(vr, dict) or not any(k != LINE_KEY for k in vr):
                ctx.err(b, f"action_blocks.{bid}.variants doit être un dictionnaire variante → étapes")
                continue
            per: dict[str, tuple[Step, ...]] = {}
            for vname, vsteps in vr.items():
                if vname == LINE_KEY:
                    continue
                if vname not in variants:
                    ctx.err(vr, f"action_blocks.{bid}.variants : '{vname}' non déclarée dans 'variants' "
                                f"(attendu parmi {list(variants)})")
                    continue
                per[vname] = _parse_steps(ctx, vsteps, sources, f'action_blocks.{bid}.variants.{vname}')
            out[bid] = ActionBlock(id=bid, title=title, variants=per, next_question=nq)
    if not out:
        ctx.err(root, "'action_blocks' ne contient aucun bloc valide")
    return out


def _parse_decision_tree(ctx: _Ctx, root: dict, blocks: dict[str, ActionBlock]) -> tuple[DecisionTree | None, set[str]]:
    """Retourne l'arbre et l'ensemble des ids de scénarios référencés (switch_to)."""
    switches: set[str] = set()
    raw = ctx.req(root, 'decision_tree', dict)
    if raw is None:
        return None, switches
    entry = ctx.req(raw, 'entry', str, 'decision_tree.entry')
    qraw = ctx.req(raw, 'questions', dict, 'decision_tree.questions')
    if qraw is None:
        return None, switches
    qids = {k for k in qraw if k != LINE_KEY}
    questions: dict[str, Question] = {}
    for qid in qids:
        q = qraw[qid]
        if not isinstance(q, dict):
            ctx.err(qraw, f"decision_tree.questions.{qid} doit être un dictionnaire")
            continue
        if ID_RE.match(str(qid)) is None:
            ctx.err(q, f"decision_tree : identifiant de question '{qid}' invalide")
        text = ctx.ltext(q, 'text', f'questions.{qid}.text', question=True)
        araw = ctx.req(q, 'answers', dict, f'questions.{qid}.answers')
        if araw is None:
            continue
        answers: dict[str, Answer] = {}
        for akey, a in araw.items():
            if akey == LINE_KEY:
                continue
            lab = f'questions.{qid}.answers.{akey}'
            if not isinstance(a, dict):
                ctx.err(araw, f"{lab} doit être un dictionnaire")
                continue
            label = ctx.ltext(a, 'label', f'{lab}.label')
            targets = [k for k in ANSWER_TARGET_KEYS if k in a]
            if len(targets) != 1:
                ctx.err(a, f"{lab} : exactement une cible parmi {list(ANSWER_TARGET_KEYS)}")
                continue
            tkey = targets[0]
            tval = ctx.req(a, tkey, str, f'{lab}.{tkey}')
            if tval is None or label is None:
                continue
            if tkey == 'next_question' and tval not in qids:
                ctx.err(a, f"{lab} : réponse vers la question inexistante '{tval}'", tkey)
                continue
            if tkey == 'action_block' and tval not in blocks:
                ctx.err(a, f"{lab} : bloc d'actions inexistant '{tval}'", tkey)
                continue
            if tkey == 'switch_to':
                switches.add(tval)
            answers[str(akey)] = Answer(label=label, **{tkey: tval})
        if len(answers) < 2:
            ctx.err(q, f"questions.{qid} : une question fermée a au moins deux réponses")
        if text is None:
            continue
        questions[qid] = Question(id=qid, text=text, answers=answers)
    for bid, blk in blocks.items():
        if blk.next_question is not None and blk.next_question not in qids:
            ctx.err(root['action_blocks'][bid], f"action_blocks.{bid}.next_question : question inexistante '{blk.next_question}'", 'next_question')
    if entry is not None and entry not in qids:
        ctx.err(raw, f"decision_tree.entry : question d'entrée inexistante '{entry}'")
        return None, switches
    if entry is None:
        return None, switches
    return DecisionTree(entry=entry, questions=questions), switches


def _parse_flags(ctx: _Ctx, root: dict, key: str, sources: dict[str, Source],
                 switches: set[str]) -> tuple[Flag, ...]:
    raw = ctx.req(root, key, list)
    if raw is None:
        return ()
    flags: list[Flag] = []
    for i, f in enumerate(raw, start=1):
        if not isinstance(f, dict):
            ctx.err(root, f"{key}[{i}] doit être un dictionnaire")
            continue
        text = ctx.ltext(f, 'text', f'{key}[{i}].text')
        sp = _parse_source_page(ctx, f, sources, f'{key}[{i}]')
        sw = f.get('switch_to')
        if sw is not None:
            if key != 'red_flags':
                ctx.err(f, f"{key}[{i}] : 'switch_to' n'est autorisé que sur les red_flags")
                sw = None
            elif not isinstance(sw, str) or not sw.strip():
                ctx.err(f, f"{key}[{i}].switch_to doit être un identifiant de scénario")
                sw = None
            else:
                switches.add(sw)
        if text is None or sp is None:
            continue
        flags.append(Flag(text=text, source_page=sp, switch_to=sw))
    return tuple(flags)


def _parse_validators(ctx: _Ctx, root: dict) -> tuple[Validator, ...]:
    raw = ctx.opt(root, 'validated_by', list, [])
    if raw is None:
        return ()
    out: list[Validator] = []
    for i, v in enumerate(raw, start=1):
        if not isinstance(v, dict):
            ctx.err(root, f"validated_by[{i}] doit être un dictionnaire")
            continue
        name = ctx.req(v, 'name', str, f'validated_by[{i}].name')
        qual = ctx.req(v, 'qualification', str, f'validated_by[{i}].qualification')
        org = ctx.req(v, 'organisation', str, f'validated_by[{i}].organisation')
        date = ctx.date(v, 'date')
        if None in (name, qual, org, date):
            continue
        out.append(Validator(name=name, qualification=qual, organisation=org, date=date))
    return tuple(out)


def parse_protocol(data: Any, file: str, expected_id: str | None = None) -> tuple[Protocol | None, list[ProtocolError], set[str]]:
    """
    Valide un document YAML déjà chargé.

    Retourne (protocole ou None, erreurs, ids de scénarios référencés par switch_to).
    La cohérence inter-fichiers (switch_to vers un scénario absent) est vérifiée
    par le chargeur, qui connaît l'ensemble des protocoles.
    """
    ctx = _Ctx(file)
    if not isinstance(data, dict):
        ctx.err({}, 'le document YAML doit être un dictionnaire à la racine')
        return None, ctx.errors, set()

    pid = ctx.req(data, 'id', str)
    if pid is not None:
        if ID_RE.match(pid) is None:
            ctx.err(data, f"'id' doit être un identifiant anglais snake_case stable ('{pid}')")
        if expected_id is not None and pid != expected_id:
            ctx.err(data, f"'id' ({pid}) doit être égal au nom du fichier ({expected_id})")

    title = ctx.ltext(data, 'title', 'title')
    description = ctx.ltext(data, 'description', 'description')
    version = ctx.req(data, 'version', int)
    if version is not None and version < 1:
        ctx.err(data, "'version' commence à 1")
    updated_at = ctx.date(data, 'updated_at')

    status = ctx.opt(data, 'status', str, STATUS_DRAFT)
    if status not in STATUSES:
        ctx.err(data, f"'status' doit être l'un de {list(STATUSES)} ('{status}')")
    validators = _parse_validators(ctx, data)
    incomplete = ctx.opt(data, 'incomplete', bool, False)
    if status == STATUS_VALIDATED and not validators:
        ctx.err(data, "status 'validated' sans aucune entrée dans 'validated_by' : refusé", 'status')
    if status == STATUS_VALIDATED and incomplete:
        ctx.err(data, "un protocole 'incomplete: true' ne peut pas être 'validated'")

    call_first = ctx.opt(data, 'call_emergency_first', bool, True)

    sources = _parse_sources(ctx, data)

    variants_raw = ctx.opt(data, 'variants', dict, {})
    variants: dict[str, LocalizedText] = {}
    if isinstance(variants_raw, dict):
        for k in variants_raw:
            if k == LINE_KEY:
                continue
            if k not in VARIANTS:
                ctx.err(variants_raw, f"variants : '{k}' inconnue (attendu parmi {list(VARIANTS)})", k)
                continue
            label = ctx.ltext(variants_raw, k, f'variants.{k}')
            if label is not None:
                variants[k] = label

    blocks = _parse_action_blocks(ctx, data, sources, variants)
    tree, switches = _parse_decision_tree(ctx, data, blocks)
    red_flags = _parse_flags(ctx, data, 'red_flags', sources, switches)
    do_not = _parse_flags(ctx, data, 'do_not', sources, switches)
    if not red_flags and not incomplete:
        ctx.err(data, "'red_flags' vide : un protocole complet définit au moins un signe d'alerte")

    vision = ctx.opt(data, 'vision_checkpoints', list, [])
    if vision:
        ctx.err(data, "'vision_checkpoints' doit rester vide pour l'instant (réservé au médecin)")

    # Blocs d'actions non atteignables depuis l'arbre : signalés comme erreur,
    # une consigne qui ne peut jamais s'afficher n'a pas de raison d'exister.
    if tree is not None:
        reachable = {a.action_block for q in tree.questions.values() for a in q.answers.values() if a.action_block}
        for bid in blocks:
            if bid not in reachable:
                ctx.err(data, f"action_blocks.{bid} n'est référencé par aucune réponse du decision_tree")

    if ctx.errors or None in (pid, title, description, version, updated_at, tree):
        return None, ctx.errors, switches

    proto = Protocol(
        id=pid, title=title, description=description, version=version, updated_at=updated_at,
        status=status, validated_by=validators, sources=sources, call_emergency_first=call_first,
        decision_tree=tree, action_blocks=blocks, red_flags=red_flags, do_not=do_not,
        variants=variants, vision_checkpoints=tuple(vision or ()), incomplete=bool(incomplete), file=file,
    )
    return proto, [], switches
