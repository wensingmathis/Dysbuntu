"""
manager.py — Interface entre l'application graphique et le moteur TTS.

L'interface graphique ne connaît QUE ce module. Elle ne sait pas qu'eSpeak NG
existe, ne construit aucune commande et n'exécute aucun processus.

Le gestionnaire se charge de :
  - conserver les réglages (voix, vitesse, volume, hauteur) ;
  - lancer la synthèse dans un fil d'exécution séparé (interface jamais figée) ;
  - prévenir l'interface par des fonctions de rappel (début, fin, erreur) ;
  - arrêter une lecture en cours.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Callable, List, Optional

from .espeak import (
    PITCH_DEFAULT,
    RATE_DEFAULT,
    VOLUME_DEFAULT,
    EspeakEngine,
    EspeakError,
    EspeakNotFoundError,
    Voice,
)
from .piper import (
    PiperEngine,
    PiperError,
    PiperNotFoundError,
    PiperVoice,
    afficher_diagnostic,
)

Callback = Optional[Callable[..., None]]


class TTSManager:
    """Point d'entrée unique du moteur de synthèse vocale pour l'interface."""

    def __init__(self) -> None:
        # Lève EspeakNotFoundError si eSpeak NG est absent : l'application
        # affichera alors un message compréhensible et s'arrêtera proprement.
        self.engine = EspeakEngine()

        # Moteur PRINCIPAL de Vocalis : Piper, s'il est installé. eSpeak NG
        # reste le moteur de repli (fallback) si Piper est absent.
        try:
            self.piper: Optional[PiperEngine] = PiperEngine()
        except PiperNotFoundError as exc:
            self.piper = None
            print(f"\n[Vocalis] (1) Piper détecté : NON\n{exc}\n",
                  file=sys.stderr, flush=True)
        else:
            print(f"[Vocalis] (1) Piper détecté : OUI — {self.piper.binary} "
                  f"(HOME={Path.home()})", file=sys.stderr, flush=True)
        self.piper_error: Optional[str] = None

        self._voices: List[Voice] = []
        self._process = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Réglages courants
        self.voice: Optional[Voice] = None
        self.rate: int = RATE_DEFAULT
        self.volume: int = VOLUME_DEFAULT
        self.pitch: int = PITCH_DEFAULT

        # Fonctions de rappel fournies par l'interface
        self.on_start: Callback = None
        self.on_finish: Callback = None
        self.on_error: Callback = None

        # Chargement IMMÉDIAT des voix dès la construction de TTSManager.
        # Auparavant _voices restait vide (liste chargée à la demande, au
        # premier appel de load_voices() par l'interface) : un test lancé
        # juste après TTSManager() voyait donc _voices=[] même quand tout
        # fonctionnait normalement. Ce n'est plus le cas.
        self.load_voices()

    # ------------------------------------------------------------------
    # Voix
    # ------------------------------------------------------------------
    def load_voices(self, french_only: bool = False) -> List[Voice]:
        """Charge (et met en cache) les voix détectées sur la machine."""
        if not self._voices:
            # Les voix Piper détectées localement sont ajoutées à la liste
            # existante, en tête (fr_FR-siwis-medium en premier).
            voix_piper: List[PiperVoice] = []
            self.piper_error = None
            if self.piper is not None:
                try:
                    voix_piper = self.piper.list_voices()
                except PiperError as exc:
                    # La raison est affichée dans le terminal : sans cela, la
                    # voix Piper disparaîtrait de la liste sans explication.
                    self.piper_error = str(exc)
                    print(f"\n[Vocalis] Voix Piper indisponible :\n{exc}\n",
                          file=sys.stderr, flush=True)
            self._voices = voix_piper + self.engine.list_voices()
            print(f"[Vocalis] (2) Nombre de voix chargées : {len(self._voices)}",
                  file=sys.stderr, flush=True)
            print(f"[Vocalis] (3) Voix chargées : "
                  + ", ".join(v.label for v in self._voices), file=sys.stderr, flush=True)

        voices = self._voices
        if french_only:
            french = [v for v in voices if v.is_french]
            if french:
                voices = french

        if self.voice is None and voices:
            # Par défaut, Vocalis privilégie une voix française.
            self.voice = next((v for v in voices if v.is_french), voices[0])
        return voices

    def set_voice(self, voice: Voice) -> None:
        self.voice = voice

    def find_voice(self, identifier: str) -> Optional[Voice]:
        return next((v for v in self._voices if v.identifier == identifier), None)

    @property
    def supports_pitch(self) -> bool:
        """Vrai si la voix sélectionnée accepte le réglage de hauteur."""
        return self.voice is None or self.voice.supports_pitch

    # ------------------------------------------------------------------
    # Réglages
    # ------------------------------------------------------------------
    def set_rate(self, rate: int) -> None:
        self.rate = int(rate)

    def set_volume(self, volume: int) -> None:
        self.volume = int(volume)

    def set_pitch(self, pitch: int) -> None:
        self.pitch = int(pitch)

    @property
    def uses_piper(self) -> bool:
        """Vrai si la voix sélectionnée est une voix Piper."""
        return isinstance(self.voice, PiperVoice)

    def _current_engine(self):
        """
        Retourne le moteur à utiliser pour la voix sélectionnée.

        Si une voix Piper est sélectionnée, c'est Piper qui sera utilisé, ou
        rien du tout : aucun repli silencieux vers eSpeak NG n'est autorisé.
        """
        if not self.uses_piper:
            return self.engine
        if self.piper is None:
            raise PiperError(
                "La voix sélectionnée est une voix Piper, mais Piper n'est "
                "plus accessible.\n\nVocalis ne bascule pas automatiquement "
                "sur une autre voix : corrigez l'installation de Piper ou "
                "choisissez une voix eSpeak NG."
            )
        return self.piper

    def _options(self) -> dict:
        """Options adaptées au moteur de la voix courante."""
        if self.uses_piper:
            return {
                "voice": self.voice,       # PiperEngine attend l'objet voix
                "rate": self.rate,
                "volume": self.volume,
                "pitch": None,             # Piper ne gère pas la hauteur
            }
        return {
            "voice": self.voice.identifier if self.voice else None,
            "rate": self.rate,
            "volume": self.volume,
            "pitch": self.pitch if self.supports_pitch else None,
        }

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------
    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def speak(self, text: str) -> None:
        """
        Lit le texte à voix haute, en arrière-plan.

        Retourne immédiatement : l'interface graphique reste réactive.
        """
        text = (text or "").strip()
        if not text:
            self._notify(self.on_error, "Le texte à lire est vide.")
            return

        self.stop()  # une seule lecture à la fois

        def worker() -> None:
            try:
                moteur = self._current_engine()
                if not self.uses_piper:
                    # Permet de constater immédiatement qu'on n'écoute PAS Piper.
                    afficher_diagnostic(
                        Moteur="eSpeak NG",
                        Exécutable=self.engine.binary,
                        Voix=self.voice.identifier if self.voice else "(aucune)",
                    )
                process = moteur.speak(text, **self._options())
            except (EspeakNotFoundError, EspeakError, PiperError) as exc:
                self._notify(self.on_error, str(exc))
                return
            except Exception as exc:  # jamais d'échec muet dans le fil de fond
                self._notify(self.on_error, f"Erreur inattendue : {exc}")
                return

            with self._lock:
                self._process = process

            self._notify(self.on_start)
            _, stderr = process.communicate()

            with self._lock:
                interrompu = self._process is not process
                self._process = None

            if interrompu or process.returncode in (0, -15, -9):
                self._notify(self.on_finish)
            else:
                self._notify(
                    self.on_error,
                    (stderr or "eSpeak NG s'est arrêté de façon inattendue.").strip(),
                )

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Interrompt la lecture en cours, s'il y en a une."""
        with self._lock:
            process = self._process
            self._process = None
        if process is not None and process.poll() is None:
            process.terminate()

    def save_to_wav(self, text: str, path: str) -> None:
        """Enregistre la synthèse dans un fichier WAV, en arrière-plan."""
        text = (text or "").strip()
        if not text:
            self._notify(self.on_error, "Le texte à enregistrer est vide.")
            return

        def worker() -> None:
            try:
                self._current_engine().save_to_wav(text, path, **self._options())
            except (EspeakNotFoundError, EspeakError, PiperError) as exc:
                self._notify(self.on_error, str(exc))
            except Exception as exc:  # jamais d'échec muet dans le fil de fond
                self._notify(self.on_error, f"Erreur inattendue : {exc}")
            else:
                self._notify(self.on_finish, path)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    @staticmethod
    def _notify(callback: Callback, *args) -> None:
        if callback is not None:
            callback(*args)
