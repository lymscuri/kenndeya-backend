"""
Chargeur des protocoles YAML de premiers secours.

- Lit tous les fichiers *.yaml de apps/firstaid/protocols/ (ou d'un dossier
  passé en paramètre, pour les tests).
- Injecte le numéro de ligne de chaque bloc YAML pour que chaque erreur soit
  localisée « fichier:ligne ».
- Valide chaque fichier (apps.firstaid.schema) puis la cohérence entre fichiers
  (switch_to vers un scénario qui existe).
- Refuse de démarrer (ProtocolValidationError) à la moindre erreur.

Deux accès au registre :
- all_protocols()         : tout, y compris brouillons — admin et tests seulement
- publishable_protocols() : UNIQUEMENT les protocoles 'validated' signés — la
                            seule fonction que les endpoints publics appellent.
"""

from __future__ import annotations

import threading
from pathlib import Path

import yaml
from django.conf import settings

from .schema import (
    LINE_KEY,
    LineInfo,
    Protocol,
    ProtocolError,
    ProtocolValidationError,
    parse_protocol,
)

PROTOCOLS_DIR = Path(__file__).resolve().parent / 'protocols'


# ------------------------------------------------------------------------------
# YAML avec numéros de ligne
# ------------------------------------------------------------------------------

class _LineLoader(yaml.SafeLoader):
    """
    SafeLoader qui ajoute '__line__' (1-indexé) à chaque dictionnaire.

    La valeur est un entier (ligne du bloc) qui porte en plus, dans `.keys`,
    la ligne de chaque clé du bloc : une erreur sur 'next_question' pointe la
    ligne de 'next_question', pas celle du début de la réponse.
    """

    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        info = LineInfo(node.start_mark.line + 1)
        info.keys = {
            key_node.value: key_node.start_mark.line + 1
            for key_node, _ in node.value
            if isinstance(key_node, yaml.ScalarNode)
        }
        mapping[LINE_KEY] = info
        return mapping


def _read_yaml(path: Path) -> tuple[object, list[ProtocolError]]:
    """Lit un fichier ; une erreur de syntaxe est rendue avec sa ligne."""
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        return None, [ProtocolError(str(path), None, f'lecture impossible : {exc}')]
    try:
        data = yaml.load(text, Loader=_LineLoader)  # noqa: S506 — SafeLoader dérivé
    except yaml.YAMLError as exc:
        line = None
        mark = getattr(exc, 'problem_mark', None)
        if mark is not None:
            line = mark.line + 1
        problem = getattr(exc, 'problem', None) or str(exc)
        return None, [ProtocolError(str(path), line, f'YAML malformé : {problem}')]
    if data is None:
        return None, [ProtocolError(str(path), 1, 'fichier vide')]
    return data, []


# ------------------------------------------------------------------------------
# Chargement d'un dossier
# ------------------------------------------------------------------------------

def load_protocols(directory: Path | str | None = None) -> dict[str, Protocol]:
    """
    Charge et valide tous les protocoles d'un dossier.

    Lève ProtocolValidationError avec la liste complète des erreurs
    (fichier + ligne) si un seul fichier est invalide.
    """
    directory = Path(directory) if directory is not None else PROTOCOLS_DIR
    if not directory.is_dir():
        raise ProtocolValidationError(
            [ProtocolError(str(directory), None, 'dossier de protocoles introuvable')]
        )

    errors: list[ProtocolError] = []
    protocols: dict[str, Protocol] = {}
    wanted: dict[str, list[str]] = {}       # id référencé par switch_to → fichiers demandeurs

    for path in sorted(directory.glob('*.yaml')) + sorted(directory.glob('*.yml')):
        rel = str(path.relative_to(directory.parent)) if directory.parent in path.parents else str(path)
        data, read_errors = _read_yaml(path)
        if read_errors:
            errors.extend(read_errors)
            continue
        proto, perrors, switches = parse_protocol(data, rel, expected_id=path.stem)
        errors.extend(perrors)
        for sid in switches:
            wanted.setdefault(sid, []).append(rel)
        if proto is None:
            continue
        if proto.id in protocols:
            errors.append(ProtocolError(rel, None, f"id '{proto.id}' déjà défini dans {protocols[proto.id].file}"))
            continue
        protocols[proto.id] = proto

    # Cohérence inter-fichiers : toute bascule vise un scénario présent.
    for sid, files in wanted.items():
        if sid not in protocols:
            for f in files:
                errors.append(ProtocolError(f, None, f"switch_to vers le scénario absent '{sid}'"))

    if errors:
        raise ProtocolValidationError(errors)
    return protocols


# ------------------------------------------------------------------------------
# Registre global
# ------------------------------------------------------------------------------

class ProtocolRegistry:
    """Registre en mémoire, rempli au démarrage de l'application."""

    def __init__(self) -> None:
        self._protocols: dict[str, Protocol] = {}
        self._loaded = False
        self._lock = threading.Lock()

    def load(self, directory: Path | str | None = None) -> None:
        with self._lock:
            self._protocols = load_protocols(directory)
            self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def all_protocols(self) -> dict[str, Protocol]:
        """Tous les protocoles, brouillons compris. Admin et tests uniquement."""
        self._ensure_loaded()
        return dict(self._protocols)

    def publishable_protocols(self) -> dict[str, Protocol]:
        """
        Protocoles exposables au public.

        Règle : status 'validated' ET au moins un signataire. Les squelettes
        (incomplete: true) ne sortent jamais. Hors production, le réglage
        FIRSTAID_ALLOW_DRAFTS=True laisse passer les brouillons complets pour
        le développement du frontend — production.py le force à False.
        """
        self._ensure_loaded()
        allow_drafts = bool(getattr(settings, 'FIRSTAID_ALLOW_DRAFTS', False))
        out: dict[str, Protocol] = {}
        for pid, p in self._protocols.items():
            if p.incomplete:
                continue
            if p.is_validated or allow_drafts:
                out[pid] = p
        return out

    def get_publishable(self, protocol_id: str) -> Protocol | None:
        return self.publishable_protocols().get(protocol_id)


registry = ProtocolRegistry()

all_protocols = registry.all_protocols
publishable_protocols = registry.publishable_protocols
