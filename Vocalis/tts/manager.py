"""Orchestration des tâches TTS. Aucun appel Tkinter depuis un worker."""
from __future__ import annotations

import os
import queue
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from .common import (AudioSettings, BusyError, CancelledError, DependencyError,
                     EngineError, InputError, Voice, VocalisError, validate_text)
from .espeak import EspeakEngine
from .piper import PiperEngine, check_wav
from .process import CancellationToken, play_wav


@dataclass(frozen=True, slots=True)
class Event:
    kind: str  # started, finished, saved, stopped, error
    message: str = ""


class TTSManager:
    """Une opération à la fois ; les événements sont consommés par la boucle UI."""

    def __init__(self, espeak: EspeakEngine | None = None,
                 piper: PiperEngine | None = None, *, detect: bool = True) -> None:
        self._espeak = espeak
        self._piper = piper
        if detect:
            if self._espeak is None:
                try:
                    self._espeak = EspeakEngine()
                except DependencyError:
                    pass
            if self._piper is None:
                try:
                    self._piper = PiperEngine()
                except DependencyError:
                    pass
        if self._espeak is None and self._piper is None:
            raise DependencyError(
                "Aucun moteur TTS installé. Installez eSpeak NG avec :\n"
                "sudo apt install espeak-ng\n"
                "ou Piper avec : pipx install piper-tts"
            )
        self.events: queue.Queue[Event] = queue.Queue()
        self._lock = threading.Lock()
        self._token: CancellationToken | None = None
        self._thread: threading.Thread | None = None
        self._voices: dict[str, Voice] = {}
        self.refresh_voices()

    def refresh_voices(self) -> list[Voice]:
        if self.busy:
            raise BusyError("Patientez jusqu'à la fin de l'opération.")
        found: list[Voice] = []
        errors: list[str] = []
        for engine in (self._piper, self._espeak):
            if engine is None:
                continue
            try:
                found.extend(engine.list_voices())
            except VocalisError as exc:
                errors.append(str(exc))
        if not found:
            raise EngineError("Aucune voix disponible. " + " ; ".join(errors))
        self._voices = {voice.identifier: voice for voice in found}
        return found

    def list_voices(self, french_only: bool = False) -> list[Voice]:
        voices = list(self._voices.values())
        selected = [v for v in voices if v.is_french]
        return selected if french_only and selected else voices

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._token is not None

    def _start(self, text: str, voice_id: str, settings: AudioSettings,
               kind: str, destination: Path | None = None) -> None:
        validated = validate_text(text)
        if not isinstance(settings, AudioSettings):
            raise InputError("Réglages audio invalides.")
        voice = self._voices.get(voice_id)
        if voice is None:
            raise InputError("Cette voix n'est pas disponible.")
        if kind == "save" and destination is None:
            raise InputError("Chemin de destination manquant.")
        with self._lock:
            if self._token is not None:
                raise BusyError("Une lecture ou un enregistrement est déjà en cours.")
            token = CancellationToken()
            self._token = token
        thread = threading.Thread(
            target=self._worker, args=(validated, voice, settings, kind, destination, token),
            name="vocalis-tts-worker", daemon=True,
        )
        self._thread = thread
        self.events.put(Event("started", kind))
        try:
            thread.start()
        except RuntimeError as exc:
            with self._lock:
                self._token = None
            raise EngineError(f"Impossible de démarrer le traitement : {exc}") from exc

    def speak(self, text: str, voice_id: str, settings: AudioSettings) -> None:
        self._start(text, voice_id, settings, "speak")

    def save_to_wav(self, text: str, voice_id: str, settings: AudioSettings,
                    destination: str | Path) -> None:
        if not str(destination).lower().endswith(".wav"):
            raise InputError("Le fichier doit avoir l'extension .wav.")
        self._start(text, voice_id, settings, "save", Path(destination).expanduser())

    def cancel(self) -> None:
        with self._lock:
            token = self._token
        if token is not None:
            token.cancel()

    def shutdown(self) -> None:
        """Annule puis laisse un bref délai au worker pour supprimer le temporaire."""
        self.cancel()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)

    def _worker(self, text: str, voice: Voice, settings: AudioSettings,
                kind: str, destination: Path | None, token: CancellationToken) -> None:
        try:
            if kind == "save":
                assert destination is not None  # garanti par _start
                self._save(text, voice, settings, destination, token)
                # La sauvegarde est engagée : une annulation tardive n’efface pas le résultat.
                self.events.put(Event("saved", str(destination)))
            elif voice.engine == "espeak":
                assert self._espeak is not None
                self._espeak.synthesize(text, voice, settings, token)
                token.check()
                self.events.put(Event("finished"))
            elif voice.engine == "piper":
                # Piper génère un WAV temporaire privé, puis un lecteur le joue.
                with temporary_wav() as wav:
                    assert self._piper is not None
                    self._piper.synthesize(text, voice, settings, token, wav)
                    token.check()
                    play_wav(wav, token)
                token.check()
                self.events.put(Event("finished"))
            else:
                raise EngineError("Moteur inconnu.")
        except CancelledError:
            self.events.put(Event("stopped"))
        except (VocalisError, OSError) as exc:
            self.events.put(Event("error", str(exc)))
        except Exception:
            # Dernier garde-fou, sans divulguer le texte ni une trace complète.
            self.events.put(Event("error", "Erreur interne inattendue. Consultez les tests."))
        finally:
            with self._lock:
                if self._token is token:
                    self._token = None

    def _save(self, text: str, voice: Voice, settings: AudioSettings,
              destination: Path, token: CancellationToken) -> None:
        directory = destination.parent
        if not directory.is_dir():
            raise InputError(f"Dossier de destination inexistant : {directory}")
        # Fichier temporaire mode 0600, même système de fichiers pour os.replace().
        with temporary_wav(directory) as wav:
            if voice.engine == "piper":
                if self._piper is None:
                    raise DependencyError("Piper non disponible.")
                self._piper.synthesize(text, voice, settings, token, wav)
            elif voice.engine == "espeak":
                if self._espeak is None:
                    raise DependencyError("eSpeak NG non disponible.")
                self._espeak.synthesize(text, voice, settings, token, wav)
            else:
                raise EngineError("Moteur inconnu.")
            check_wav(wav)
            token.check()
            # L'utilisateur choisit explicitement le fichier depuis le dialogue.
            os.replace(wav, destination)


class temporary_wav:
    """Context manager privé : suppression systématique, même après annulation."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory
        self.path: Path | None = None

    def __enter__(self) -> Path:
        handle, filename = tempfile.mkstemp(
            prefix=".vocalis-", suffix=".wav", dir=self.directory,
        )
        os.close(handle)
        self.path = Path(filename)
        return self.path

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.path is not None:
            self.path.unlink(missing_ok=True)
