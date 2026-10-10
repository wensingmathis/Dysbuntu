"""Cœur de la correction : filtre, met en cache et convertit les résultats LanguageTool.

Ce module est indépendant d'UNO. Il est utilisé par le composant
``DysbuntuProofreader.py`` (soulignement en direct) et par la revue guidée.
"""

from __future__ import annotations

import collections
import threading
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from .categories import CATEGORIES, classify, lt_categories_for
from .config import ConfigStore
from .explain import build_comments
from .lt_client import LanguageToolClient, LanguageToolError, LanguageToolUnavailable, Match
from .logutil import get_logger
from .server import ServerManager
from .textutil import split_text

log = get_logger("proofread")


class Issue(NamedTuple):
    offset: int  # unités UTF-16 dans le texte vérifié
    length: int
    category: str
    category_label: str
    color: int
    rule_id: str
    short_comment: str
    full_comment: str
    suggestions: List[str]


def supports_language(tag: str) -> bool:
    return (tag or "").lower().replace("_", "-").split("-")[0] == "fr"


class Proofreader:
    CACHE_SIZE = 256

    def __init__(
        self,
        store: ConfigStore,
        server: Optional[ServerManager] = None,
        client_factory: Optional[Callable[[Dict[str, Any]], LanguageToolClient]] = None,
    ):
        self.store = store
        self.server = server or ServerManager()
        self._client_factory = client_factory or (
            lambda cfg: LanguageToolClient(cfg["host"], cfg["port"], cfg["timeout_s"])
        )
        self._cache: "collections.OrderedDict[Tuple, List[Issue]]" = collections.OrderedDict()
        self._lock = threading.Lock()
        self.last_status = "inconnu"  # 'ok' | 'indisponible' | 'erreur'

    # -- règles ignorées ---------------------------------------------------
    def ignore_rule(self, rule_id: str) -> None:
        if rule_id:
            self.store.add_ignored_rule(rule_id)
            self.clear_cache()

    def reset_ignored_rules(self) -> None:
        self.store.reset_ignored_rules()
        self.clear_cache()

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    # -- vérification ------------------------------------------------------
    def check(self, text: str, language: str = "fr-FR") -> List[Issue]:
        """Vérifie un texte. Retourne [] si le serveur est indisponible (jamais d'exception)."""
        if not text or not text.strip() or not supports_language(language):
            return []
        cfg = self.store.get()
        disabled_cats = [k for k, on in cfg["categories"].items() if not on]
        key = (
            text,
            language,
            tuple(sorted(cfg["ignored_rules"])),
            tuple(sorted(disabled_cats)),
            cfg["max_suggestions"],
        )
        with self._lock:
            hit = self._cache.get(key)
            if hit is not None:
                self._cache.move_to_end(key)
                return list(hit)
        try:
            client = self._client_factory(cfg)
            issues = self._check_chunks(client, text, language, cfg, disabled_cats)
        except LanguageToolUnavailable as exc:
            self.last_status = "indisponible"
            log.info("Serveur indisponible : %s", exc)
            if cfg["auto_start_server"]:
                self.server.start_async(cfg)
            return []  # pas de mise en cache : on réessaiera
        except LanguageToolError as exc:
            self.last_status = "erreur"
            log.warning("Erreur LanguageTool : %s", exc)
            return []
        self.last_status = "ok"
        with self._lock:
            self._cache[key] = issues
            while len(self._cache) > self.CACHE_SIZE:
                self._cache.popitem(last=False)
        return list(issues)

    def _check_chunks(self, client, text, language, cfg, disabled_cats) -> List[Issue]:
        disabled_lt = []
        for k in disabled_cats:
            disabled_lt.extend(lt_categories_for(k))
        issues: List[Issue] = []
        for base, chunk in split_text(text, cfg["max_chunk_chars"]):
            matches = client.check(
                chunk, language, disabled_rules=cfg["ignored_rules"], disabled_categories=disabled_lt
            )
            for m in matches:
                issue = self._to_issue(m, base, cfg, disabled_cats)
                if issue is not None:
                    issues.append(issue)
        issues.sort(key=lambda i: (i.offset, i.length))
        return issues

    @staticmethod
    def _to_issue(m: Match, base: int, cfg: Dict[str, Any], disabled_cats: List[str]) -> Optional[Issue]:
        if m.length <= 0 or m.rule_id in cfg["ignored_rules"]:
            return None
        key = classify(m.category_id, m.issue_type)
        if key in disabled_cats:
            return None
        cat = CATEGORIES[key]
        suggestions = m.replacements[: cfg["max_suggestions"]]
        short, full = build_comments(key, m.message, suggestions)
        return Issue(
            offset=base + m.offset,
            length=m.length,
            category=key,
            category_label=cat.label,
            color=cat.color,
            rule_id=m.rule_id,
            short_comment=short,
            full_comment=full,
            suggestions=suggestions,
        )
