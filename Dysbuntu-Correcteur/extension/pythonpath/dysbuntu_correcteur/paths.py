"""Emplacements des fichiers de l'utilisateur (norme XDG). Rien n'est écrit ailleurs."""

from __future__ import annotations

import os

APP_DIR = "dysbuntu-correcteur"


def _xdg(var: str, default_rel: str) -> str:
    base = os.environ.get(var) or os.path.join(os.path.expanduser("~"), default_rel)
    return os.path.join(base, APP_DIR)


def config_dir() -> str:
    return _xdg("XDG_CONFIG_HOME", ".config")


def data_dir() -> str:
    return _xdg("XDG_DATA_HOME", os.path.join(".local", "share"))


def state_dir() -> str:
    return _xdg("XDG_STATE_HOME", os.path.join(".local", "state"))


def config_file() -> str:
    return os.path.join(config_dir(), "config.json")


def default_languagetool_dir() -> str:
    return os.path.join(data_dir(), "languagetool")


def log_file() -> str:
    return os.path.join(state_dir(), "correcteur.log")


def server_log_file() -> str:
    return os.path.join(state_dir(), "languagetool-server.log")
