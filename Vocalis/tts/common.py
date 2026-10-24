"""Types, validation et erreurs explicites partagés par les moteurs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MAX_TEXT_CHARS = 5_000
RATE_MIN, RATE_MAX, RATE_DEFAULT = 80, 450, 175
VOLUME_MIN, VOLUME_MAX, VOLUME_DEFAULT = 0, 200, 100
PITCH_MIN, PITCH_MAX, PITCH_DEFAULT = 0, 99, 50
MAX_WAV_BYTES = 256 * 1024 * 1024


class VocalisError(Exception):
    """Erreur prévue, affichable à l'utilisateur."""


class InputError(VocalisError):
    """Entrée ou réglage invalide."""


class DependencyError(VocalisError):
    """Moteur ou programme audio non disponible."""


class EngineError(VocalisError):
    """Le moteur ou le lecteur audio a échoué."""


class BusyError(VocalisError):
    """Une opération est déjà en cours."""


class CancelledError(VocalisError):
    """L'utilisateur a interrompu l'opération."""


@dataclass(frozen=True, slots=True)
class AudioSettings:
    rate: int = RATE_DEFAULT
    volume: int = VOLUME_DEFAULT
    pitch: int = PITCH_DEFAULT

    def __post_init__(self) -> None:
        for name, minimum, maximum in (
            ("rate", RATE_MIN, RATE_MAX),
            ("volume", VOLUME_MIN, VOLUME_MAX),
            ("pitch", PITCH_MIN, PITCH_MAX),
        ):
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise InputError(f"{name} doit être un entier entre {minimum} et {maximum}.")


@dataclass(frozen=True, slots=True)
class Voice:
    identifier: str
    label: str
    engine: str  # 'piper' ou 'espeak'
    is_french: bool
    supports_pitch: bool
    model: Path | None = None
    config: Path | None = None


def validate_text(text: str) -> str:
    if not isinstance(text, str):
        raise InputError("Le texte doit être une chaîne de caractères.")
    value = text.strip()
    if not value:
        raise InputError("Saisissez un texte avant de lancer la lecture.")
    if len(value) > MAX_TEXT_CHARS:
        raise InputError(f"Le texte dépasse {MAX_TEXT_CHARS} caractères.")
    if "\x00" in value:
        raise InputError("Le texte contient un caractère NUL interdit.")
    return value
