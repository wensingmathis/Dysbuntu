"""Explications en phrases simples, adaptées aux personnes dyslexiques."""

from __future__ import annotations

import re
from typing import List, Tuple

from .categories import CATEGORIES

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def clean(text: str) -> str:
    """Retire les balises éventuelles et normalise les espaces."""
    return _SPACE_RE.sub(" ", _TAG_RE.sub("", text or "")).strip()


def build_comments(category_key: str, message: str, suggestions: List[str]) -> Tuple[str, str]:
    """Retourne (commentaire_court, commentaire_complet).

    Le commentaire court tient sur une ligne (menu contextuel de Writer).
    Le commentaire complet ajoute la suggestion et le détail du correcteur.
    """
    cat = CATEGORIES.get(category_key, CATEGORIES["autres"])
    short = "%s : %s" % (cat.label, cat.plain)
    lines = [cat.plain]
    if suggestions:
        quoted = " ou ".join("« %s »" % s for s in suggestions[:2])
        lines.append("Essayez : %s." % quoted)
    detail = clean(message)
    if detail:
        lines.append("Détail : %s" % detail)
    return short, "\n".join(lines)
