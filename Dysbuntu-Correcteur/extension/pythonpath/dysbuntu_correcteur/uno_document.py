"""Adaptateur Writer pour la revue guidée.

Une « unité » est un paragraphe (document entier) ou une plage de texte (sélection).

Les objets UNO sont utilisés par « duck typing » : ce module n'importe pas ``uno``,
ce qui permet de le tester avec des objets factices (voir tests/test_uno_document.py).
"""

from __future__ import annotations

from typing import Any, List

from .review import DocumentAdapter
from .textutil import utf16_to_index

_MAX_STEP = 16000  # goRight() prend un « short » (int16)


def _supports(obj: Any, service: str) -> bool:
    try:
        return bool(obj.supportsService(service))
    except Exception:
        return False


def collect_paragraphs(text_like: Any) -> List[Any]:
    """Liste les paragraphes (y compris dans les tableaux) d'un texte ou d'une sélection."""
    out: List[Any] = []
    enum = text_like.createEnumeration()
    while enum.hasMoreElements():
        el = enum.nextElement()
        if _supports(el, "com.sun.star.text.Paragraph"):
            out.append(el)
        elif _supports(el, "com.sun.star.text.TextTable"):
            try:
                for name in el.getCellNames():
                    out.extend(collect_paragraphs(el.getCellByName(name)))
            except Exception:
                continue
    return out


def selected_ranges(controller: Any) -> List[Any]:
    """Plages de texte de la sélection courante (chaque plage est vérifiée telle quelle).

    On n'énumère PAS les paragraphes de la sélection : Writer renverrait des paragraphes
    entiers, y compris la partie non sélectionnée.
    """
    sel = controller.getSelection()
    out: List[Any] = []
    if sel is None:
        return out
    if _supports(sel, "com.sun.star.text.TextRanges"):
        for i in range(sel.getCount()):
            rng = sel.getByIndex(i)
            if rng.getString():
                out.append(rng)
    elif hasattr(sel, "getString") and sel.getString():
        out.append(sel)
    return out


def _move(cursor: Any, count: int, expand: bool) -> None:
    while count > 0:
        step = min(count, _MAX_STEP)
        cursor.goRight(step, expand)
        count -= step


class WriterAdapter(DocumentAdapter):
    def __init__(self, paragraphs: List[Any], controller: Any = None, default_language: str = "fr-FR"):
        self._paras = paragraphs
        self._controller = controller
        self._default_language = default_language

    @classmethod
    def whole_document(cls, doc: Any, controller: Any = None) -> "WriterAdapter":
        return cls(collect_paragraphs(doc.getText()), controller)

    @classmethod
    def selection(cls, controller: Any) -> "WriterAdapter":
        return cls(selected_ranges(controller), controller)

    # -- DocumentAdapter ---------------------------------------------------
    def paragraph_count(self) -> int:
        return len(self._paras)

    def paragraph_text(self, index: int) -> str:
        return self._paras[index].getString()

    def paragraph_language(self, index: int) -> str:
        try:
            loc = self._paras[index].getPropertyValue("CharLocale")
            if loc.Language:
                return loc.Language + ("-" + loc.Country if loc.Country else "")
        except Exception:
            pass
        return self._default_language

    def _cursor_on(self, index: int, start: int, length: int) -> Any:
        para = self._paras[index]
        text = para.getString()
        a = utf16_to_index(text, start)
        b = utf16_to_index(text, start + length)
        # Attention : gotoStart() irait au début du TEXTE ENTIER, pas du paragraphe.
        cur = para.getText().createTextCursorByRange(para.getStart())
        _move(cur, a, False)
        _move(cur, b - a, True)
        return cur

    def replace(self, index: int, start: int, length: int, new_text: str) -> None:
        """Remplace un passage : on insère le nouveau texte APRÈS l'ancien, puis on supprime l'ancien.

        Un simple setString() sur le début d'une plage la ferait « rétrécir » (Writer exclut
        le texte remplacé à la frontière de la plage) ; cette méthode garde la plage intacte.
        """
        old = self._cursor_on(index, start, length)
        old.getText().insertString(old.getEnd(), new_text, False)
        self._cursor_on(index, start, length).setString("")

    def select(self, index: int, start: int, length: int) -> None:
        if self._controller is None:
            return
        try:
            self._controller.select(self._cursor_on(index, start, length))
        except Exception:
            pass  # la sélection visuelle est un confort, jamais bloquante
