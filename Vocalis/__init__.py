"""
Msynthèse vocale de Vocalis.

Moteur obligatoire : eSpeak NG (100 % locale, aucune connexion
).
Moteur optionnel : Piper TTS, s'il est déjà installé sur la machine.il mieux

  espeak.py  → communication avec eSpeak NG
  piper.py   → communication avec Piper TTS (optionnel)
  manager.py → interface entre l'application graphique et les moteurs
"""

from .espeak import (
    EspeakEngine,
    EspeakError,
    EspeakNotFoundError,
    Voice,
)
from .manager import TTSManager
from .piper import PiperEngine, PiperError, PiperNotFoundError, PiperVoice

__all__ = [
    "EspeakEngine",
    "EspeakError",
    "EspeakNotFoundError",
    "PiperEngine",
    "PiperError",
    "PiperNotFoundError",
    "PiperVoice",
    "TTSManager",
    "Voice",
]
