"""Outils de texte : positions UTF-16 (LibreOffice / LanguageTool) vs indices Python.

LibreOffice (OUString) et LanguageTool (Java) comptent en unités UTF-16.
Python compte en points de code. Pour le texte courant (BMP) c'est identique ;
les caractères hors BMP (emoji...) comptent 2 unités UTF-16 mais 1 point de code.
"""

from __future__ import annotations

from typing import List, Tuple


def utf16_len(text: str) -> int:
    """Longueur du texte en unités UTF-16."""
    return len(text.encode("utf-16-le", "surrogatepass")) // 2


def utf16_to_index(text: str, u16_pos: int) -> int:
    """Convertit une position UTF-16 en indice Python (points de code)."""
    if u16_pos <= 0:
        return 0
    units = 0
    for i, ch in enumerate(text):
        if units >= u16_pos:
            return i
        units += 2 if ord(ch) > 0xFFFF else 1
    return len(text)


def index_to_utf16(text: str, index: int) -> int:
    """Convertit un indice Python en position UTF-16."""
    return utf16_len(text[: max(index, 0)])


def utf16_slice(text: str, start: int, length: int) -> str:
    """Extrait ``length`` unités UTF-16 à partir de ``start``."""
    a = utf16_to_index(text, start)
    b = utf16_to_index(text, start + length)
    return text[a:b]


def split_text(text: str, max_len: int) -> List[Tuple[int, str]]:
    """Découpe un long texte en morceaux d'au plus ``max_len`` caractères.

    Retourne des couples ``(décalage_utf16, morceau)``. Les coupures se font
    de préférence après un saut de ligne, puis après une fin de phrase, puis
    après une espace, pour ne pas couper un mot.
    """
    if max_len <= 0 or len(text) <= max_len:
        return [(0, text)]
    chunks: List[Tuple[int, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        end = min(pos + max_len, n)
        if end < n:
            window = text[pos:end]
            cut = -1
            for sep in ("\n", ". ", "! ", "? ", " "):
                k = window.rfind(sep)
                if k > max_len // 4:
                    cut = k + len(sep)
                    break
            if cut > 0:
                end = pos + cut
        chunk = text[pos:end]
        chunks.append((index_to_utf16(text, pos), chunk))
        pos = end
    return chunks
