"""Configuration de l'utilisateur (fichier JSON local, aucune donnée envoyée ailleurs)."""

from __future__ import annotations

import copy
import json
import os
import threading
from typing import Any, Dict, List

from . import paths

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")

CATEGORY_KEYS = ("orthographe", "grammaire", "ponctuation", "style", "autres")

DEFAULTS: Dict[str, Any] = {
    # Serveur LanguageTool : uniquement local (voir is_loopback).
    "host": "127.0.0.1",
    "port": 8081,
    "timeout_s": 8.0,
    "auto_start_server": True,
    "languagetool_dir": "",  # vide = emplacement par défaut (paths.default_languagetool_dir)
    "java_command": "java",
    "java_options": ["-Xmx1g"],
    # Catégories de corrections actives.
    "categories": {
        "orthographe": True,
        "grammaire": True,
        "ponctuation": True,
        "style": False,
        "autres": True,
    },
    "ignored_rules": [],
    # Revue guidée : vérifier tout comme du français, même si Writer indique une autre langue.
    "review_force_french": True,
    # Taille du texte dans les fenêtres de l'extension (points).
    "font_size": 12,
    "max_suggestions": 5,
    "max_chunk_chars": 20000,
}


class ConfigError(ValueError):
    """Configuration invalide (par exemple un serveur non local)."""


def is_loopback(host: str) -> bool:
    return host.strip().lower() in LOOPBACK_HOSTS


def validate(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Retourne une configuration valide ; lève ConfigError si la vie privée est menacée."""
    out = copy.deepcopy(DEFAULTS)
    for key, value in cfg.items():
        if key == "categories" and isinstance(value, dict):
            for ck in CATEGORY_KEYS:
                if ck in value:
                    out["categories"][ck] = bool(value[ck])
        elif key in out and key != "categories":
            out[key] = value
    if not is_loopback(str(out["host"])):
        raise ConfigError(
            "Le serveur doit être local (127.0.0.1 ou localhost) : "
            "Dysbuntu Correcteur n'envoie jamais de texte vers un serveur distant."
        )
    try:
        out["port"] = int(out["port"])
    except (TypeError, ValueError):
        raise ConfigError("Port invalide.")
    if not (1024 <= out["port"] <= 65535):
        raise ConfigError("Le port doit être compris entre 1024 et 65535.")
    try:
        out["timeout_s"] = max(1.0, min(float(out["timeout_s"]), 60.0))
        out["font_size"] = max(9, min(int(out["font_size"]), 32))
        out["max_suggestions"] = max(1, min(int(out["max_suggestions"]), 10))
        out["max_chunk_chars"] = max(1000, min(int(out["max_chunk_chars"]), 100000))
    except (TypeError, ValueError):
        raise ConfigError("Valeur numérique invalide.")
    out["auto_start_server"] = bool(out["auto_start_server"])
    out["review_force_french"] = bool(out["review_force_french"])
    out["ignored_rules"] = sorted({str(r) for r in out["ignored_rules"]})
    out["java_options"] = [str(o) for o in out["java_options"]]
    out["languagetool_dir"] = str(out["languagetool_dir"] or "")
    out["java_command"] = str(out["java_command"] or "java")
    return out


def effective_languagetool_dir(cfg: Dict[str, Any]) -> str:
    return cfg["languagetool_dir"] or paths.default_languagetool_dir()


class ConfigStore:
    """Charge/enregistre la configuration ; recharge si le fichier a changé."""

    def __init__(self, path: str = ""):
        self._path = path
        self._lock = threading.Lock()
        self._mtime = None  # type: Any
        self._cfg = validate({})

    @property
    def path(self) -> str:
        return self._path or paths.config_file()

    def get(self) -> Dict[str, Any]:
        with self._lock:
            try:
                mtime = os.stat(self.path).st_mtime_ns
            except OSError:
                mtime = None
            if mtime != self._mtime:
                self._mtime = mtime
                self._cfg = self._load_locked()
            return copy.deepcopy(self._cfg)

    def _load_locked(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw, dict):
                raise ValueError("racine non-objet")
            return validate(raw)
        except FileNotFoundError:
            return validate({})
        except (OSError, ValueError, ConfigError):
            # Fichier corrompu ou non sûr : on retombe sur les valeurs par défaut.
            return validate({})

    def save(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        checked = validate(cfg)
        with self._lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(checked, fh, ensure_ascii=False, indent=2, sort_keys=True)
                fh.write("\n")
            os.replace(tmp, self.path)
            self._mtime = os.stat(self.path).st_mtime_ns
            self._cfg = checked
        return copy.deepcopy(checked)

    def update(self, **changes: Any) -> Dict[str, Any]:
        cfg = self.get()
        cfg.update(changes)
        return self.save(cfg)

    def add_ignored_rule(self, rule_id: str) -> None:
        cfg = self.get()
        rules: List[str] = list(cfg["ignored_rules"])
        if rule_id not in rules:
            rules.append(rule_id)
            self.update(ignored_rules=rules)

    def reset_ignored_rules(self) -> None:
        self.update(ignored_rules=[])
