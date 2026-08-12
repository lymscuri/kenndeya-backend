"""
Règle d'alerte obstétricale.

À partir d'un WeeklyCheckup, retourne :
- level : 'vert' | 'jaune' | 'orange' | 'rouge' — la CATÉGORIE la plus
  grave dont au moins un déclencheur est présent.
- reasons : liste de chaînes lisibles, TOUS niveaux confondus, décrivant
  chaque déclencheur trouvé.

Les libellés de symptômes doivent correspondre exactement à ceux du
formulaire Expo (weekly-checkup.tsx, constante SYMPTOMS). Toute
divergence d'accent ou de casse rend la règle inopérante.
"""

from typing import Iterable, List, Optional, Tuple


# Libellés copiés textuellement depuis
# expo/app/(tabs)/maternite/weekly-checkup.tsx (constante SYMPTOMS).
SYMPTOM_BLEEDING = 'Saignements'
SYMPTOM_HEADACHE = 'Maux de tête persistants'
SYMPTOM_BLURRY_VISION = 'Vision floue'
SYMPTOM_EDEMA = 'Gonflement visage-mains-pieds'
SYMPTOM_FEVER = 'Fièvre'
SYMPTOM_ABDOMINAL_PAIN = 'Douleurs abdominales'
SYMPTOM_REDUCED_MOVEMENTS = 'Mouvements fœtaux diminués'
SYMPTOM_ABNORMAL_DISCHARGE = 'Pertes vaginales anormales'

PRE_ECLAMPSIA_SIGNS = (
    SYMPTOM_HEADACHE,
    SYMPTOM_BLURRY_VISION,
    SYMPTOM_EDEMA,
)

# Ordre canonique des niveaux, du plus grave au moins grave.
LEVEL_ORDER = ('rouge', 'orange', 'jaune', 'vert')


def _symptom_set(symptoms) -> set:
    """Normalise le champ symptoms en set. Le modèle stocke un JSONField
    liste ; on tolère None et les valeurs non-itérables sans exploser."""
    if not symptoms:
        return set()
    try:
        return {str(s) for s in symptoms}
    except TypeError:
        return set()


def evaluate_weekly_checkup(checkup) -> Tuple[str, List[str]]:
    """
    Applique la règle d'alerte obstétricale au checkup fourni.

    Retourne (level, reasons). Si le checkup est None, renvoie
    ('vert', []).
    """
    if checkup is None:
        return 'vert', []

    systolic = getattr(checkup, 'blood_pressure_systolic', None)
    diastolic = getattr(checkup, 'blood_pressure_diastolic', None)
    fetal_movements = getattr(checkup, 'fetal_movements', None) or ''
    symptoms = _symptom_set(getattr(checkup, 'symptoms', None))

    red_reasons: List[str] = []
    orange_reasons: List[str] = []
    yellow_reasons: List[str] = []

    # ─── ROUGE ────────────────────────────────────────────────────────
    hypertension_urgent = (
        (systolic is not None and systolic >= 160)
        or (diastolic is not None and diastolic >= 110)
    )
    if hypertension_urgent:
        red_reasons.append(
            f"Tension {systolic or '?'}/{diastolic or '?'} "
            f"(seuil urgence 160/110)"
        )

    if fetal_movements == 'absents':
        red_reasons.append("Mouvements fœtaux absents")

    if SYMPTOM_BLEEDING in symptoms:
        red_reasons.append("Saignements déclarés")

    # ─── ORANGE ───────────────────────────────────────────────────────
    hypertension_moderate = (
        not hypertension_urgent
        and (
            (systolic is not None and systolic >= 140)
            or (diastolic is not None and diastolic >= 90)
        )
    )
    if hypertension_moderate:
        orange_reasons.append(
            f"Tension {systolic or '?'}/{diastolic or '?'} "
            f"(seuil surveillance 140/90)"
        )

    pre_eclampsia_count = sum(1 for s in PRE_ECLAMPSIA_SIGNS if s in symptoms)
    if pre_eclampsia_count >= 2:
        matched = [s for s in PRE_ECLAMPSIA_SIGNS if s in symptoms]
        orange_reasons.append(
            "Signes de pré-éclampsie : " + ", ".join(matched)
        )

    if SYMPTOM_FEVER in symptoms:
        orange_reasons.append("Fièvre déclarée")

    if SYMPTOM_ABDOMINAL_PAIN in symptoms:
        orange_reasons.append("Douleurs abdominales déclarées")

    # ─── JAUNE ────────────────────────────────────────────────────────
    if fetal_movements == 'reduits':
        yellow_reasons.append("Mouvements fœtaux réduits")

    if SYMPTOM_REDUCED_MOVEMENTS in symptoms:
        yellow_reasons.append("Symptôme : mouvements fœtaux diminués")

    if pre_eclampsia_count == 1:
        matched = [s for s in PRE_ECLAMPSIA_SIGNS if s in symptoms]
        yellow_reasons.append(
            "Signe isolé de pré-éclampsie : " + matched[0]
        )

    if SYMPTOM_ABNORMAL_DISCHARGE in symptoms:
        yellow_reasons.append("Pertes vaginales anormales déclarées")

    # Niveau = catégorie la plus grave qui a au moins une raison.
    if red_reasons:
        level = 'rouge'
    elif orange_reasons:
        level = 'orange'
    elif yellow_reasons:
        level = 'jaune'
    else:
        level = 'vert'

    reasons = red_reasons + orange_reasons + yellow_reasons
    return level, reasons


def evaluate_pregnancy(pregnancy) -> Tuple[str, List[str]]:
    """
    Applique la règle au checkup le plus récent (par checkup_date
    décroissant) de la grossesse. Retourne ('vert', []) si aucun.

    Optimisé pour prefetch : si pregnancy.weekly_checkups.all() a été
    prefetché avec l'ordering par défaut du modèle (-checkup_date),
    aucun SELECT supplémentaire n'est émis ici.
    """
    if pregnancy is None:
        return 'vert', []

    checkups: Optional[Iterable] = getattr(pregnancy, 'weekly_checkups', None)
    if checkups is None:
        return 'vert', []

    # Convertir en liste : si prefetché, c'est déjà du Python en mémoire.
    # Sinon .all() déclenche 1 SELECT — acceptable.
    ordered = list(checkups.all()) if hasattr(checkups, 'all') else list(checkups)
    if not ordered:
        return 'vert', []

    # Le modèle WeeklyCheckup a Meta.ordering = ['-checkup_date'], donc
    # ordered[0] est le plus récent chronologiquement quand la relation
    # est prefetchée avec cet ordering. On force malgré tout un tri en
    # Python pour ne pas dépendre d'un ordering qu'un jour on modifierait.
    latest = max(
        ordered,
        key=lambda wc: getattr(wc, 'checkup_date', None) or 0,
    )
    return evaluate_weekly_checkup(latest)
