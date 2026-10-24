"""eSpeak NG : voix et synthèse via stdin (jamais via shell/argv texte)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .common import AudioSettings, DependencyError, EngineError, Voice
from .process import CancellationToken, find_binary, run_command


class EspeakEngine:
    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or find_binary("espeak-ng")
        if not self.binary:
            raise DependencyError("eSpeak NG est absent (sudo apt install espeak-ng).")

    def list_voices(self) -> list[Voice]:
        try:
            result = subprocess.run(
                [self.binary, "--voices"], stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                errors="replace", timeout=10, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EngineError(f"Impossible de lister les voix eSpeak NG : {exc}") from exc
        if result.returncode != 0:
            raise EngineError(f"Liste des voix eSpeak NG indisponible (code {result.returncode}).")
        voices: list[Voice] = []
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) < 5 or not fields[0].isdigit():
                continue
            language, gender, name, file = fields[1:5]
            if not language or language.startswith("-"):
                continue
            french = language.lower().startswith("fr")
            label = f"eSpeak NG — {name} ({language}, {gender})"
            voices.append(Voice(
                identifier=f"espeak:{language}", label=label, engine="espeak",
                is_french=french, supports_pitch=not file.lower().startswith("mb/"),
            ))
        voices.sort(key=lambda v: (not v.is_french, v.label.casefold()))
        return voices

    def synthesize(self, text: str, voice: Voice, settings: AudioSettings,
                   token: CancellationToken, output: Path | None = None) -> None:
        if voice.engine != "espeak" or not voice.identifier.startswith("espeak:"):
            raise EngineError("Voix eSpeak NG invalide.")
        language = voice.identifier.removeprefix("espeak:")
        cmd = [self.binary, "-v", language, "-s", str(settings.rate),
               "-a", str(settings.volume), "-b", "1"]
        if voice.supports_pitch:
            cmd.extend(["-p", str(settings.pitch)])
        if output is not None:
            cmd.extend(["-w", str(output)])
        cmd.append("--stdin")
        run_command(cmd, token, label="eSpeak NG", text=text, timeout=300 if output else 1_800)
