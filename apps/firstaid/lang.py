"""
Détection de langue SANS modèle de langage : 'fr', 'en' ou None.

Heuristique volontairement simple et lisible :
- mots fonctionnels fréquents propres à chaque langue (les mots communs aux
  deux, comme « a », « on », « plus », sont exclus) ;
- lettres accentuées (français) ;
- élisions françaises (j', l', qu'…) et contractions anglaises (n't, 's, 'm…).

Retourne None dès que rien ne tranche : texte vide, « ok », « 442 », égalité.
Le client doit alors préciser la langue ; on ne devine jamais.
"""

from __future__ import annotations

import re
import unicodedata

FR_WORDS = frozenset("""
le la les un une des du de et ou est sont il elle ils elles je tu nous vous
ne pas mais que qui quoi dans sur avec pour sans sa ses mon ma mes ton ta tes
ce cette ces cet au aux se lui leur très bien oui non depuis chez où comme
tout tous toute toutes après avant encore aussi fait faut peut va vais suis
ai été être avoir quand parce car donc alors déjà ici là moi toi
""".split())

EN_WORDS = frozenset("""
the an and or is are was were be been being he she it they we you i my his
her their our your not no yes but with for from this that these those there
here has have had do does did can cannot could will would should of in at to
into what who which when how very just still now while because then
""".split())

# Élisions françaises en début de mot : j'ai, l'enfant, qu'il, n'est…
_FR_ELISION = re.compile(r"\b(j|l|d|n|c|m|t|s|qu)['’](?=\w)", re.IGNORECASE)
# Contractions anglaises en fin de mot : isn't, he's, I'm, we're, they've, I'll
_EN_CONTRACTION = re.compile(r"\w(n['’]t|['’](s|m|re|ve|ll|d))\b", re.IGNORECASE)
_FR_ACCENTS = frozenset('àâäéèêëîïôöùûüçœ')
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

MAX_LEN = 1000  # même plafond que les endpoints ; au-delà on ne regarde que le début


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _WORD.findall(text)]


def _scores(text: str) -> tuple[int, int]:
    """(score_fr, score_en) — entiers, plus c'est grand plus c'est net."""
    text = unicodedata.normalize('NFC', text[:MAX_LEN])
    lowered = text.lower()
    tokens = _tokens(text)
    fr = sum(1 for t in tokens if t in FR_WORDS)
    en = sum(1 for t in tokens if t in EN_WORDS)
    fr += sum(1 for ch in lowered if ch in _FR_ACCENTS)
    fr += len(_FR_ELISION.findall(text))
    en += len(_EN_CONTRACTION.findall(text))
    return fr, en


def detect_lang(text: str | None) -> str | None:
    """'fr' | 'en' | None. None si le texte est vide ou indécidable (égalité ou zéro indice)."""
    if not text or not text.strip():
        return None
    fr, en = _scores(text)
    if fr == en:
        return None
    return 'fr' if fr > en else 'en'
