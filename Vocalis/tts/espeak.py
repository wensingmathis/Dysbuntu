"""
espeak.py — Communication bas niveau avec eSpeak NG.

Ce module est le SEUL endroit du projet qui exécute réellement la commande
eSpeak NG. Aucune autre partie du code (et surtout pas l'interface graphique)
ne doit appeler subprocess directement.

Fonctionnement :
  - détection du binaire eSpeak NG sur la machine ;
  - lecture de la liste des voix via `espeak-ng --voices` ;
  - synthèse vocale locale via `espeak-ng -v <voix> -s <vitesse> ...` ;
  - aucune donnée n'est envoyée sur Internet, tout est traité localement.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence

# Noms possibles du binaire, dans l'ordre de préférence.
BINARY_CANDIDATES = ("espeak-ng", "espeak")

# Bornes acceptées par eSpeak NG.
RATE_MIN, RATE_MAX, RATE_DEFAULT = 80, 450, 175      # -s : mots par minute
VOLUME_MIN, VOLUME_MAX, VOLUME_DEFAULT = 0, 200, 100  # -a : amplitude
PITCH_MIN, PITCH_MAX, PITCH_DEFAULT = 0, 99, 50       # -p : hauteur de voix

INSTALL_HINT = (
    "eSpeak NG est introuvable sur ce système.\n\n"
    "Vocalis ne peut pas fonctionner sans lui.\n\n"
    "Installez-le avec la commande :\n\n"
    "    sudo apt install espeak-ng"
)


class EspeakNotFoundError(RuntimeError):
    """eSpeak NG n'est pas installé ou n'est pas accessible dans le PATH."""

    def __init__(self, message: str = INSTALL_HINT) -> None:
        super().__init__(message)


class EspeakError(RuntimeError):
    """eSpeak NG a été trouvé mais a échoué pendant son exécution."""


@dataclass(frozen=True)
class Voice:
    """Une voix eSpeak NG telle que renvoyée par `espeak-ng --voices`."""

    identifier: str   # code utilisé avec -v (ex. "fr", "fr-be")
    language: str     # code langue brut (ex. "fr-be")
    name: str         # nom lisible (ex. "french-Belgium")
    gender: str       # "M", "F" ou "-"
    file: str         # fichier de la voix (ex. "roa/fr-BE", "mb/mb-fr1")
    priority: int     # colonne Pty

    @property
    def is_french(self) -> bool:
        """Vrai si la voix est une voix française."""
        return self.language.lower().startswith("fr")

    @property
    def supports_pitch(self) -> bool:
        """
        Les voix MBROLA (fichier préfixé « mb/ ») ignorent le réglage -p.
        L'interface s'en sert pour désactiver le curseur de hauteur.
        """
        return not self.file.lower().startswith("mb/")

    @property
    def label(self) -> str:
        """Libellé affiché dans le menu « Choisir une voix »."""
        gender = {"M": "homme", "F": "femme"}.get(self.gender.upper(), "")
        drapeau = "🇫🇷 " if self.is_french else ""
        details = " — ".join(part for part in (self.language, gender) if part)
        return f"{drapeau}{self.name} ({details})"


class EspeakEngine:
    """Enveloppe autour du binaire eSpeak NG."""

    def __init__(self, binary: Optional[str] = None) -> None:
        self.binary = binary or self.find_binary()

    # ------------------------------------------------------------------
    # Détection / installation
    # ------------------------------------------------------------------
    @staticmethod
    def find_binary() -> str:
        """Retourne le chemin du binaire eSpeak NG ou lève EspeakNotFoundError."""
        for candidate in BINARY_CANDIDATES:
            path = shutil.which(candidate)
            if path:
                return path
        raise EspeakNotFoundError()

    @staticmethod
    def is_available() -> bool:
        """Vrai si eSpeak NG est installé sur la machine."""
        return any(shutil.which(name) for name in BINARY_CANDIDATES)

    def version(self) -> str:
        """Retourne la ligne de version renvoyée par eSpeak NG."""
        try:
            result = subprocess.run(
                [self.binary, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:  # pragma: no cover - dépend du système
            raise EspeakError(f"Impossible d'exécuter eSpeak NG : {exc}") from exc
        return (result.stdout or result.stderr).strip()

    # ------------------------------------------------------------------
    # Liste des voix
    # ------------------------------------------------------------------
    def list_voices(self) -> List[Voice]:
        """
        Exécute `espeak-ng --voices` et transforme la sortie en objets Voice.

        Les voix françaises sont placées en tête de liste, les autres sont
        triées par nom afin de remplir automatiquement le menu de sélection.
        """
        try:
            result = subprocess.run(
                [self.binary, "--voices"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:  # pragma: no cover - dépend du système
            raise EspeakError(f"Impossible de lister les voix : {exc}") from exc

        if result.returncode != 0:
            raise EspeakError(
                "eSpeak NG n'a pas pu lister les voix :\n"
                + (result.stderr or "erreur inconnue").strip()
            )

        voices = [
            voice
            for voice in (self._parse_voice_line(line) for line in result.stdout.splitlines())
            if voice is not None
        ]
        # Les voix françaises d'abord (exigence de Vocalis), puis l'alphabet.
        voices.sort(key=lambda v: (not v.is_french, v.language.lower(), v.name.lower()))
        return voices

    @staticmethod
    def _parse_voice_line(line: str) -> Optional[Voice]:
        """
        Analyse une ligne de `espeak-ng --voices`.

        Format attendu :
            Pty  Language  Age/Gender  VoiceName  File  Other Languages
             5   fr-be     --/M        french-Belgium  roa/fr-BE
        """
        stripped = line.strip()
        if not stripped or stripped.startswith("Pty"):
            return None

        parts = stripped.split()
        if len(parts) < 5:
            return None

        priority_raw, language, age_gender = parts[0], parts[1], parts[2]
        if not priority_raw.isdigit():
            return None

        # Le fichier est le premier champ contenant « / » après le nom.
        file_index = next(
            (i for i in range(3, len(parts)) if "/" in parts[i] and i > 3),
            len(parts) - 1,
        )
        name = " ".join(parts[3:file_index]) or parts[3]
        file = parts[file_index] if file_index < len(parts) else ""

        gender = age_gender.split("/")[-1] if "/" in age_gender else "-"

        return Voice(
            identifier=language,
            language=language,
            name=name,
            gender=gender,
            file=file,
            priority=int(priority_raw),
        )

    # ------------------------------------------------------------------
    # Synthèse vocale
    # ------------------------------------------------------------------
    def build_command(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: int = RATE_DEFAULT,
        volume: int = VOLUME_DEFAULT,
        pitch: Optional[int] = PITCH_DEFAULT,
        output_wav: Optional[str] = None,
    ) -> List[str]:
        """Construit la ligne de commande eSpeak NG (sans l'exécuter)."""
        command = [self.binary]

        if voice:
            command += ["-v", voice]
        command += ["-s", str(_clamp(rate, RATE_MIN, RATE_MAX))]
        command += ["-a", str(_clamp(volume, VOLUME_MIN, VOLUME_MAX))]
        if pitch is not None:
            command += ["-p", str(_clamp(pitch, PITCH_MIN, PITCH_MAX))]
        if output_wav:
            command += ["-w", output_wav]

        # `--` évite qu'un texte commençant par « - » soit pris pour une option.
        command += ["--", text]
        return command

    def speak(self, text: str, **options) -> subprocess.Popen:
        """
        Lance la lecture du texte et retourne immédiatement le processus.

        L'appel n'est pas bloquant : c'est le gestionnaire (manager.py) qui
        surveille la fin du processus dans un fil d'exécution séparé, afin que
        l'interface graphique ne soit jamais figée.
        """
        command = self.build_command(text, **options)
        try:
            return subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
            raise EspeakNotFoundError() from exc
        except OSError as exc:  # pragma: no cover - dépend du système
            raise EspeakError(f"Échec du lancement d'eSpeak NG : {exc}") from exc

    def save_to_wav(self, text: str, path: str, **options) -> None:
        """Écrit la synthèse dans un fichier WAV (opération bloquante et locale)."""
        command = self.build_command(text, output_wav=path, **options)
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise EspeakNotFoundError() from exc
        if result.returncode != 0:
            raise EspeakError(
                "eSpeak NG n'a pas pu enregistrer le fichier :\n"
                + (result.stderr or "erreur inconnue").strip()
            )


def _clamp(value: int, minimum: int, maximum: int) -> int:
    """Restreint une valeur aux bornes acceptées par eSpeak NG."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = minimum
    return max(minimum, min(maximum, value))


if __name__ == "__main__":  # Petit test manuel : python3 -m tts.espeak
    try:
        engine = EspeakEngine()
    except EspeakNotFoundError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)

    print(engine.version())
    for v in engine.list_voices():
        print(f"{v.identifier:<12} {v.label}")
