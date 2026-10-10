"""Gestion du serveur LanguageTool local (démarrage, arrêt, état).

Le serveur est lancé avec ``HTTPServer`` SANS l'option ``--public`` : il n'écoute
donc que sur l'interface locale. Aucun téléchargement n'est fait ici (voir
``scripts/install_languagetool.sh``, qui demande un consentement explicite).
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

from . import paths
from .config import effective_languagetool_dir
from .lt_client import LanguageToolClient
from .logutil import get_logger

log = get_logger("server")

_JAR_NAMES = ("languagetool-server.jar",)


def find_server_jar(lt_dir: str) -> Optional[str]:
    for name in _JAR_NAMES:
        direct = os.path.join(lt_dir, name)
        if os.path.isfile(direct):
            return direct
    # Archive officielle : un sous-dossier LanguageTool-X.Y
    try:
        for entry in sorted(os.listdir(lt_dir), reverse=True):
            sub = os.path.join(lt_dir, entry)
            for name in _JAR_NAMES:
                cand = os.path.join(sub, name)
                if os.path.isfile(cand):
                    return cand
    except OSError:
        pass
    return None


def build_command(cfg: Dict[str, Any], jar: str) -> List[str]:
    return (
        [cfg["java_command"]]
        + list(cfg["java_options"])
        + ["-cp", os.path.basename(jar), "org.languagetool.server.HTTPServer", "--port", str(cfg["port"])]
    )


class ServerManager:
    """Démarre LanguageTool en arrière-plan ; ne l'arrête que s'il l'a lancé."""

    START_COOLDOWN_S = 30.0

    def __init__(self):
        self._proc = None  # type: Optional[subprocess.Popen]
        self._lock = threading.Lock()
        self._last_attempt = 0.0
        self.last_error = ""

    def status(self, cfg: Dict[str, Any]) -> str:
        """'running' | 'installed' | 'missing'."""
        client = LanguageToolClient(cfg["host"], cfg["port"], cfg["timeout_s"])
        if client.is_alive():
            return "running"
        if find_server_jar(effective_languagetool_dir(cfg)):
            return "installed"
        return "missing"

    def start_async(self, cfg: Dict[str, Any], force: bool = False) -> bool:
        """Lance le serveur si besoin. Retourne True si un lancement a été tenté."""
        with self._lock:
            now = time.monotonic()
            if not force and now - self._last_attempt < self.START_COOLDOWN_S:
                return False
            self._last_attempt = now
            client = LanguageToolClient(cfg["host"], cfg["port"], cfg["timeout_s"])
            if client.is_alive():
                return False
            if self._proc is not None and self._proc.poll() is None:
                return False  # déjà en cours de démarrage
            lt_dir = effective_languagetool_dir(cfg)
            jar = find_server_jar(lt_dir)
            if not jar:
                self.last_error = "LanguageTool n'est pas installé (voir scripts/install_languagetool.sh)."
                log.warning("Démarrage impossible : %s", self.last_error)
                return False
            cmd = build_command(cfg, jar)
            try:
                os.makedirs(paths.state_dir(), exist_ok=True)
                logfh = open(paths.server_log_file(), "ab")
                self._proc = subprocess.Popen(
                    cmd,
                    cwd=os.path.dirname(jar),
                    stdin=subprocess.DEVNULL,
                    stdout=logfh,
                    stderr=logfh,
                    start_new_session=True,
                )
                self.last_error = ""
                log.info("Serveur LanguageTool lancé (pid %s) sur le port %s", self._proc.pid, cfg["port"])
                return True
            except (OSError, ValueError) as exc:
                self.last_error = "Impossible de lancer Java : %s" % exc
                log.warning(self.last_error)
                return False

    def wait_ready(self, cfg: Dict[str, Any], timeout: float = 30.0) -> bool:
        client = LanguageToolClient(cfg["host"], cfg["port"], cfg["timeout_s"])
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if client.is_alive(timeout=1.0):
                return True
            time.sleep(0.5)
        return False

    def stop_if_started_by_us(self) -> None:
        with self._lock:
            proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            log.info("Arrêt du serveur LanguageTool (pid %s)", proc.pid)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
