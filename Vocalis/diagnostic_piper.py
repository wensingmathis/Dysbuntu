#!/usr/bin/env python3
"""Diagnostic non destructif : liste des modèles locaux sans lecture du texte."""
from __future__ import annotations

import sys

from tts.common import VocalisError
from tts.piper import PiperEngine


def main() -> int:
    try:
        engine = PiperEngine()
        print(f"Exécutable : {engine.binary}")
        voices = engine.list_voices()
        for voice in voices:
            print(f"{voice.label} | {voice.model} | configuration : {voice.config}")
        if not voices:
            print("Aucune paire .onnx / .onnx.json trouvée dans ~/piper-voices.")
            return 1
        return 0
    except (VocalisError, OSError) as exc:
        print(f"Diagnostic échoué : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
