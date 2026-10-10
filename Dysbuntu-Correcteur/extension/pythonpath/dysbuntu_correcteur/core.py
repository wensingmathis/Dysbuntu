"""Objets partagés entre les composants UNO (même interpréteur Python dans LibreOffice)."""

from __future__ import annotations

import threading

from .config import ConfigStore
from .proofread import Proofreader
from .server import ServerManager

_lock = threading.Lock()
_core = None


class Core:
    def __init__(self):
        self.store = ConfigStore()
        self.server = ServerManager()
        self.proofreader = Proofreader(self.store, self.server)


def get_core() -> Core:
    global _core
    with _lock:
        if _core is None:
            _core = Core()
        return _core
