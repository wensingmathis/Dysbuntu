"""Lecture des sons WAV locaux avec paplay, sans bloquer GTK4."""
import shutil
import subprocess
import time
from pathlib import Path

KEY_SOUNDS = {'key_press', 'key_error', 'key_backspace', 'word_complete'}
REWARD_SOUNDS = {'lesson_complete', 'level_up', 'xp_gain', 'new_record',
                 'streak_gain', 'badge_unlock', 'timer_end'}

class SoundManager:
    def __init__(self, folder, enabled=True, keyboard=False, rewards=True, volume=55):
        self.folder = Path(folder)
        self.enabled = enabled
        self.keyboard = keyboard
        self.rewards = rewards
        self.volume = max(0, min(100, volume))
        self.player = shutil.which('paplay')
        self.running = []
        self.last_key = 0.0

    def play(self, name):
        if not self.enabled or self.volume <= 0 or not self.player:
            return
        if name in KEY_SOUNDS and not self.keyboard:
            return
        if name in REWARD_SOUNDS and not self.rewards:
            return
        file = self.folder / (name + '.wav')
        if not file.is_file():
            return
        if name in KEY_SOUNDS:
            now = time.monotonic()
            if now - self.last_key < .055:
                return
            self.last_key = now
        # Limiter le nombre de lecteurs parallèles, sans interrompre GTK.
        self.running = [p for p in self.running if p.poll() is None]
        if len(self.running) >= 6:
            return
        try:
            cmd = [self.player, '--volume', str(round(65536 * self.volume / 100)), str(file)]
            self.running.append(subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                                 stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL))
        except OSError:
            return

    def close(self):
        for p in self.running:
            if p.poll() is None:
                p.terminate()
