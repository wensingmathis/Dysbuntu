"""Client HTTP pour le serveur LanguageTool LOCAL (API /v2/check).

Garanties de confidentialité :
- l'adresse du serveur doit être une adresse locale (127.0.0.1, localhost, ::1) ;
- les variables d'environnement de proxy sont ignorées (le trafic ne sort pas de la machine) ;
- aucune autre requête que /v2/check, /v2/languages n'est émise.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, NamedTuple, Optional

from .config import ConfigError, is_loopback


class LanguageToolUnavailable(Exception):
    """Le serveur local ne répond pas (arrêté, démarrage en cours...)."""


class LanguageToolError(Exception):
    """Le serveur a répondu par une erreur ou une réponse incompréhensible."""


class Match(NamedTuple):
    offset: int  # unités UTF-16
    length: int  # unités UTF-16
    message: str
    short_message: str
    rule_id: str
    rule_description: str
    category_id: str
    issue_type: str
    replacements: List[str]


def language_code(locale_tag: str) -> str:
    """Convertit une langue Writer (fr-FR, fr_CA...) en code LanguageTool."""
    tag = (locale_tag or "fr").replace("_", "-")
    parts = tag.split("-")
    lang = parts[0].lower() or "fr"
    country = parts[1].upper() if len(parts) > 1 else ""
    if lang == "fr" and country in ("CA", "BE", "CH"):
        return "fr-%s" % country
    return lang


class LanguageToolClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8081, timeout: float = 8.0):
        if not is_loopback(host):
            raise ConfigError("Serveur non local refusé : %r" % host)
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)
        # ProxyHandler({}) : ne jamais passer par un proxy défini dans l'environnement.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def base_url(self) -> str:
        host = "[%s]" % self.host if ":" in self.host else self.host
        return "http://%s:%d" % (host, self.port)

    # -- requêtes ----------------------------------------------------------
    def _request(self, path: str, data: Optional[Dict[str, str]] = None, timeout: Optional[float] = None) -> Any:
        body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(self.base_url + path, data=body)
        if body is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
        try:
            with self._opener.open(req, timeout=timeout or self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            err = LanguageToolError("HTTP %d : %s" % (exc.code, detail))
            err.code = exc.code  # type: ignore[attr-defined]
            raise err
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            raise LanguageToolUnavailable(str(exc))
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError as exc:
            raise LanguageToolError("Réponse illisible : %s" % exc)

    def is_alive(self, timeout: float = 1.5) -> bool:
        try:
            self._request("/v2/languages", timeout=timeout)
            return True
        except (LanguageToolUnavailable, LanguageToolError):
            return False

    def check(
        self,
        text: str,
        language: str = "fr",
        disabled_rules: Iterable[str] = (),
        disabled_categories: Iterable[str] = (),
    ) -> List[Match]:
        if not text.strip():
            return []
        payload = {"text": text, "language": language_code(language)}
        rules = [r for r in disabled_rules if r]
        cats = [c for c in disabled_categories if c]
        if rules:
            payload["disabledRules"] = ",".join(rules)
        if cats:
            payload["disabledCategories"] = ",".join(cats)
        try:
            data = self._request("/v2/check", payload)
        except LanguageToolError as exc:
            # Variante inconnue (ex. fr-BE) : on retente avec le français générique.
            if getattr(exc, "code", 0) == 400 and "-" in payload["language"]:
                payload["language"] = payload["language"].split("-")[0]
                data = self._request("/v2/check", payload)
            else:
                raise
        return parse_matches(data)


def parse_matches(data: Any) -> List[Match]:
    if not isinstance(data, dict) or not isinstance(data.get("matches"), list):
        raise LanguageToolError("Réponse inattendue du serveur.")
    out: List[Match] = []
    for m in data["matches"]:
        try:
            rule = m.get("rule") or {}
            cat = rule.get("category") or {}
            out.append(
                Match(
                    offset=int(m["offset"]),
                    length=int(m["length"]),
                    message=str(m.get("message", "")),
                    short_message=str(m.get("shortMessage", "")),
                    rule_id=str(rule.get("id", "")),
                    rule_description=str(rule.get("description", "")),
                    category_id=str(cat.get("id", "")),
                    issue_type=str(rule.get("issueType", "")),
                    replacements=[str(r.get("value", "")) for r in (m.get("replacements") or []) if r.get("value")],
                )
            )
        except (KeyError, TypeError, ValueError):
            continue  # on ignore une correspondance mal formée
    return out
