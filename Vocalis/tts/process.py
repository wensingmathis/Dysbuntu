"""Exécution de programmes locaux sans shell, avec annulation et timeouts."""
from __future__ import annotations

import shutil
import subprocess
import threading
from collections.abc import Sequence
from pathlib import Path

from .common import CancelledError, DependencyError, EngineError


class CancellationToken:
    """Protège la fenêtre de course entre création et enregistrement du processus."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled = False
        self._process: subprocess.Popen[str] | None = None

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def check(self) -> None:
        if self.cancelled:
            raise CancelledError("Opération annulée.")

    def attach(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._process = process
            cancelled = self._cancelled
        if cancelled:
            self._terminate(process)

    def detach(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            if self._process is process:
                self._process = None

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            process = self._process
        if process is not None:
            self._terminate(process)

    @staticmethod
    def _terminate(process: subprocess.Popen[str]) -> None:
        try:
            if process.poll() is None:
                process.kill()  # Annulation immédiate, même si SIGTERM serait ignoré.
        except (OSError, ProcessLookupError):
            pass  # Le processus a pu se terminer entre-temps.


def find_binary(name: str) -> str | None:
    """Résout le binaire au démarrage, sans interprétation par un shell."""
    return shutil.which(name)


def run_command(
    command: Sequence[str], token: CancellationToken, *,
    label: str, text: str | None = None, timeout: int = 300,
) -> None:
    """Exécute une commande bornée dans le temps, en envoyant le texte sur stdin.

    stdout/stderr sont supprimés pour éviter des captures non bornées ou
    l'enregistrement accidentel de textes personnels dans les journaux.
    """
    token.check()
    if not command or not all(isinstance(x, str) and x for x in command):
        raise EngineError("Commande interne invalide.")
    try:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE if text is not None else subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        raise EngineError(f"Impossible de démarrer {label} : {exc}") from exc
    token.attach(process)
    try:
        try:
            process.communicate(input=text, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.communicate()
            if token.cancelled:
                raise CancelledError("Opération annulée.") from exc
            raise EngineError(f"{label} a dépassé le délai maximal de {timeout} secondes.") from exc
        if token.cancelled:
            raise CancelledError("Opération annulée.")
        if process.returncode != 0:
            raise EngineError(f"{label} s'est terminé avec le code {process.returncode}.")
    except OSError as exc:
        raise EngineError(f"Erreur pendant {label} : {exc}") from exc
    finally:
        token.detach(process)


def choose_player() -> list[str]:
    for name, options in (
        ("paplay", ()), ("aplay", ("-q",)),
        ("ffplay", ("-nodisp", "-autoexit", "-loglevel", "error")),
        ("play", ("-q",)),
    ):
        executable = find_binary(name)
        if executable:
            return [executable, *options]
    raise DependencyError(
        "Aucun lecteur audio disponible. Installez par exemple 'alsa-utils' "
        "(aplay) ou 'pulseaudio-utils' (paplay)."
    )


def play_wav(path: Path, token: CancellationToken) -> None:
    run_command([*choose_player(), str(path)], token, label="la lecture audio", timeout=1_800)
