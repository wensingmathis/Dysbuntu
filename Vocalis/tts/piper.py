"""Piper TTS : modèles locaux, synthèse WAV et réglage du volume en flux."""
from __future__ import annotations

import array
import os
import sys
import tempfile
import wave
from pathlib import Path

from .common import (AudioSettings, DependencyError, EngineError, MAX_WAV_BYTES,
                     RATE_DEFAULT, Voice)
from .process import CancellationToken, find_binary, run_command

PREFERRED_MODEL = "fr_FR-siwis-medium"


class PiperEngine:
    def __init__(self, binary: str | None = None, directories: tuple[Path, ...] | None = None) -> None:
        home = Path.home()
        candidates = (
            home / ".local/bin/piper",
            home / ".local/share/pipx/venvs/piper-tts/bin/piper",
        )
        resolved = binary or next((str(p) for p in candidates if p.is_file() and os.access(p, os.X_OK)), None)
        self.binary = resolved or find_binary("piper")
        if not self.binary:
            raise DependencyError("Piper n'est pas installé (pipx install piper-tts).")
        self.directories = directories or (
            home / "piper-voices", home / ".local/share/piper-voices",
        )

    def list_voices(self) -> list[Voice]:
        voices: list[Voice] = []
        seen: set[str] = set()
        for directory in self.directories:
            if not directory.is_dir():
                continue
            try:
                models = sorted(directory.glob("*.onnx"))
            except OSError as exc:
                raise EngineError(f"Impossible de lire les modèles Piper : {exc}") from exc
            for model in models:
                config = model.with_suffix(".onnx.json")
                if not config.is_file() or not model.is_file():
                    continue
                if model.stem in seen:
                    continue
                seen.add(model.stem)
                french = model.stem.lower().startswith("fr")
                voices.append(Voice(
                    identifier=f"piper:{model.stem}",
                    label=f"Piper — {model.stem}", engine="piper",
                    is_french=french, supports_pitch=False,
                    model=model, config=config,
                ))
        voices.sort(key=lambda v: (v.identifier != f"piper:{PREFERRED_MODEL}",
                                   not v.is_french, v.label.casefold()))
        return voices

    def synthesize(self, text: str, voice: Voice, settings: AudioSettings,
                   token: CancellationToken, output: Path) -> None:
        if voice.engine != "piper" or voice.model is None or voice.config is None:
            raise EngineError("Voix Piper invalide.")
        if not voice.model.is_file() or not voice.config.is_file():
            raise EngineError("Modèle Piper incomplet : .onnx et .onnx.json requis.")
        length_scale = max(0.3, min(3.0, RATE_DEFAULT / settings.rate))
        cmd = [self.binary, "--model", str(voice.model),
               "--config", str(voice.config),
               "--length_scale", f"{length_scale:.3f}",
               "--output_file", str(output)]
        run_command(cmd, token, label="Piper", text=text, timeout=300)
        check_wav(output)
        if settings.volume != 100:
            scale_volume(output, settings.volume, token)


def check_wav(path: Path) -> None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_WAV_BYTES:
            raise EngineError("WAV manquant ou trop volumineux (limite : 256 Mio).")
        with wave.open(str(path), "rb") as reader:
            if (reader.getnchannels() not in (1, 2) or reader.getsampwidth() != 2
                    or reader.getframerate() <= 0 or reader.getnframes() == 0):
                raise EngineError("Format WAV non pris en charge (PCM 16 bits mono/stéréo requis).")
    except (OSError, wave.Error, EOFError) as exc:
        raise EngineError(f"Fichier WAV illisible : {exc}") from exc


def scale_volume(path: Path, volume: int, token: CancellationToken) -> None:
    """Transforme les trames 16 bits par blocs : mémoire O(65536 échantillons)."""
    fd, name = tempfile.mkstemp(prefix=".vocalis-volume-", suffix=".wav", dir=path.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        with wave.open(str(path), "rb") as source, wave.open(str(temporary), "wb") as target:
            target.setparams(source.getparams())
            while True:
                token.check()
                data = source.readframes(32_768)
                if not data:
                    break
                samples = array.array("h")
                samples.frombytes(data)
                if sys.byteorder != "little":
                    samples.byteswap()
                gain = volume / 100
                for i, sample in enumerate(samples):
                    samples[i] = max(-32_768, min(32_767, round(sample * gain)))
                if sys.byteorder != "little":
                    samples.byteswap()
                target.writeframesraw(samples.tobytes())
        token.check()
        os.replace(temporary, path)
    except (OSError, wave.Error, ValueError) as exc:
        raise EngineError(f"Impossible de régler le volume : {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)
