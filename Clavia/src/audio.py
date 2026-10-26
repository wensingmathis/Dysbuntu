"""Bounded, non-blocking playback of bundled WAV sounds using paplay."""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path

from engine import safe_volume

LOGGER = logging.getLogger(__name__)
KEY_SOUNDS = frozenset({'key_press', 'key_error', 'key_backspace', 'word_complete'})
REWARD_SOUNDS = frozenset({'lesson_complete', 'level_up', 'xp_gain', 'new_record',
                           'streak_gain', 'badge_unlock', 'timer_end'})
ALLOWED_SOUNDS = KEY_SOUNDS | REWARD_SOUNDS | {'button_click'}
MAX_PLAYERS = 6


class SoundManager:
    def __init__(self, folder: str | Path, enabled: bool = True, keyboard: bool = False,
                 rewards: bool = True, volume: int = 55) -> None:
        self.folder = Path(folder)
        self.enabled = enabled
        self.keyboard = keyboard
        self.rewards = rewards
        self.volume = safe_volume(volume)
        self.player: str | None = shutil.which('paplay')
        self.running: list[subprocess.Popen] = []
        self.last_key = 0.0
        self._closed = False

    def play(self, name: str) -> None:
        if (self._closed or name not in ALLOWED_SOUNDS or not self.enabled
                or self.volume <= 0 or not self.player):
            return
        if (name in KEY_SOUNDS and not self.keyboard) or (name in REWARD_SOUNDS and not self.rewards):
            return
        path = self.folder / f'{name}.wav'
        if not path.is_file():
            return
        if name in KEY_SOUNDS:
            now = time.monotonic()
            if now - self.last_key < 0.055:
                return
            self.last_key = now
        # Popen.poll() reaps finished children; drop their references promptly.
        self.running = [process for process in self.running if process.poll() is None]
        if len(self.running) >= MAX_PLAYERS:
            return
        try:
            self.running.append(subprocess.Popen(
                [self.player, '--volume', str(round(65536 * safe_volume(self.volume) / 100)), str(path)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, close_fds=True,
            ))
        except (OSError, subprocess.SubprocessError) as exc:
            LOGGER.warning('Lecture audio indisponible : %s', exc)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for process in self.running:
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=0.15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=0.15)
            except (OSError, subprocess.SubprocessError) as exc:
                LOGGER.warning('Arrêt d’un lecteur audio impossible : %s', exc)
        self.running.clear()
