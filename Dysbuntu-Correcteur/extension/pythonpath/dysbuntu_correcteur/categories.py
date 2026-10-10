"""Catégories d'erreurs : regroupement des catégories LanguageTool, couleurs, libellés.

LanguageTool ne distingue pas « conjugaison » et « accord » comme catégories
séparées : ces erreurs sont dans « GRAMMAR ». Elles sont donc regroupées ici
sous « Grammaire et accords » (voir CLAUDE.md, section limites connues).
"""

from __future__ import annotations

from typing import Dict, NamedTuple


class Category(NamedTuple):
    key: str
    label: str
    color: int  # 0xRRGGBB, pour le soulignement dans Writer
    plain: str  # explication en phrase simple


CATEGORIES: Dict[str, Category] = {
    "orthographe": Category(
        "orthographe", "Orthographe", 0xD32F2F, "Ce mot semble mal écrit."
    ),
    "grammaire": Category(
        "grammaire", "Grammaire et accords", 0x1565C0, "Il y a un problème de grammaire, d'accord ou de verbe."
    ),
    "ponctuation": Category(
        "ponctuation", "Ponctuation et typographie", 0xE65100, "Il y a un souci de ponctuation ou d'espaces."
    ),
    "style": Category(
        "style", "Style", 0x2E7D32, "On peut dire cela plus simplement ou plus clairement."
    ),
    "autres": Category(
        "autres", "Autres", 0x6A1B9A, "Une vérification est conseillée ici."
    ),
}

# Identifiants de catégories LanguageTool -> nos catégories.
_LT_CATEGORY_MAP = {
    "TYPOS": "orthographe",
    "COMPOUNDING": "orthographe",
    "CASING": "orthographe",
    "GRAMMAR": "grammaire",
    "CONFUSED_WORDS": "grammaire",
    "SEMANTICS": "grammaire",
    "PUNCTUATION": "ponctuation",
    "TYPOGRAPHY": "ponctuation",
    "STYLE": "style",
    "REDUNDANCY": "style",
    "PLAIN_ENGLISH": "style",
    "WIKIPEDIA": "style",
    "REPETITIONS_STYLE": "style",
    "COLLOQUIALISMS": "style",
    "BARBARISMS": "style",
}

# issueType LanguageTool (secours si la catégorie est inconnue).
_LT_ISSUE_MAP = {
    "misspelling": "orthographe",
    "grammar": "grammaire",
    "typographical": "ponctuation",
    "style": "style",
    "locale-violation": "style",
    "register": "style",
    "redundancy": "style",
}


def classify(category_id: str, issue_type: str = "") -> str:
    """Retourne la clé de notre catégorie pour une correspondance LanguageTool."""
    cid = (category_id or "").upper()
    if cid in _LT_CATEGORY_MAP:
        return _LT_CATEGORY_MAP[cid]
    itype = (issue_type or "").lower()
    if itype in _LT_ISSUE_MAP:
        return _LT_ISSUE_MAP[itype]
    return "autres"


def lt_categories_for(key: str):
    """Identifiants LanguageTool correspondant à une de nos catégories."""
    return sorted(c for c, k in _LT_CATEGORY_MAP.items() if k == key)
