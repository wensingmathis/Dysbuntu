"""Revue guidée : parcourt les paragraphes, propose une correction à la fois.

La logique est indépendante d'UNO : le document est abstrait par un « adaptateur »
(voir ``uno_document.WriterAdapter`` pour l'implémentation Writer).
Rien n'est modifié sans action explicite de l'utilisateur (apply).
"""

from __future__ import annotations

from typing import List, NamedTuple, Optional, Set, Tuple

from .proofread import Issue, Proofreader, supports_language
from .textutil import utf16_len, utf16_slice

CONTEXT_CHARS = 40


class DocumentAdapter:
    """Interface minimale vers un document (à implémenter)."""

    def paragraph_count(self) -> int:
        raise NotImplementedError

    def paragraph_text(self, index: int) -> str:
        raise NotImplementedError

    def paragraph_language(self, index: int) -> str:
        return "fr-FR"

    def replace(self, index: int, start: int, length: int, new_text: str) -> None:
        raise NotImplementedError

    def select(self, index: int, start: int, length: int) -> None:
        raise NotImplementedError


class ReviewItem(NamedTuple):
    paragraph: int
    paragraph_total: int
    issue: Issue
    before: str
    error_text: str
    after: str


class ReviewSession:
    def __init__(
        self,
        proofreader: Proofreader,
        adapter: DocumentAdapter,
        default_language: str = "fr-FR",
        force_language: Optional[str] = None,
    ):
        """``force_language`` : si défini (ex. « fr-FR »), tous les paragraphes sont vérifiés
        dans cette langue, quelle que soit la langue indiquée dans Writer."""
        self.proofreader = proofreader
        self.adapter = adapter
        self.default_language = default_language
        self.force_language = force_language
        self.skipped_language = 0  # paragraphes non vérifiés car pas en français
        self.applied = 0
        self.ignored = 0
        self._para = 0
        self._min_offset = 0
        self._issues: List[Issue] = []
        self._text = ""
        self._loaded = -1
        self._session_ignored: Set[Tuple[str, str]] = set()
        self.current: Optional[ReviewItem] = None
        self.finished = False
        self._skipped_seen: Set[int] = set()

    # -- API publique ------------------------------------------------------
    def start(self) -> Optional[ReviewItem]:
        self._para, self._min_offset, self._loaded = 0, 0, -1
        return self._find_next()

    def apply(self, suggestion_index: int) -> Optional[ReviewItem]:
        item = self._require_current()
        sugg = item.issue.suggestions
        if not 0 <= suggestion_index < len(sugg):
            raise IndexError("suggestion inexistante")
        new_text = sugg[suggestion_index]
        self.adapter.replace(item.paragraph, item.issue.offset, item.issue.length, new_text)
        self.applied += 1
        self._min_offset = item.issue.offset + utf16_len(new_text)
        self._loaded = -1  # le paragraphe a changé : on le revérifie
        return self._find_next()

    def ignore(self) -> Optional[ReviewItem]:
        item = self._require_current()
        self._session_ignored.add((item.issue.rule_id, item.error_text))
        self.ignored += 1
        self._min_offset = item.issue.offset + item.issue.length
        return self._find_next()

    def ignore_rule(self) -> Optional[ReviewItem]:
        item = self._require_current()
        self.proofreader.ignore_rule(item.issue.rule_id)
        self.ignored += 1
        self._min_offset = item.issue.offset + item.issue.length
        self._loaded = -1
        return self._find_next()

    @property
    def server_problem(self) -> bool:
        return self.proofreader.last_status in ("indisponible", "erreur")

    # -- interne -----------------------------------------------------------
    def _require_current(self) -> ReviewItem:
        if self.current is None:
            raise RuntimeError("aucune erreur en cours")
        return self.current

    def _load(self, para: int) -> None:
        self._text = self.adapter.paragraph_text(para)
        lang = self.force_language or self.adapter.paragraph_language(para) or self.default_language
        if self._text.strip() and not supports_language(lang) and para not in self._skipped_seen:
            self._skipped_seen.add(para)
            self.skipped_language += 1
        self._issues = self.proofreader.check(self._text, lang)
        self._loaded = para

    def _find_next(self) -> Optional[ReviewItem]:
        total = self.adapter.paragraph_count()
        while self._para < total:
            if self._loaded != self._para:
                self._load(self._para)
            for issue in self._issues:
                if issue.offset < self._min_offset:
                    continue
                err = utf16_slice(self._text, issue.offset, issue.length)
                if (issue.rule_id, err) in self._session_ignored:
                    continue
                before = utf16_slice(self._text, max(0, issue.offset - CONTEXT_CHARS), min(CONTEXT_CHARS, issue.offset))
                after = utf16_slice(self._text, issue.offset + issue.length, CONTEXT_CHARS)
                self.current = ReviewItem(self._para, total, issue, before, err, after)
                self.adapter.select(self._para, issue.offset, issue.length)
                return self.current
            self._para += 1
            self._min_offset = 0
        self.current = None
        self.finished = True
        return None
