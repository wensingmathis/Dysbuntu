"""Tests sans accès Internet ni moteur externe (mocks de synthèse)."""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path

from tts.common import (AudioSettings, BusyError, CancelledError, EngineError,
                        InputError, Voice, validate_text)
from tts.manager import TTSManager
from tts.piper import check_wav, scale_volume
from tts.process import CancellationToken, run_command


VOICE = Voice("espeak:fr", "Français", "espeak", True, True)


def make_wav(path: Path, sample: int = 1_000) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(22050)
        out.writeframes(int(sample).to_bytes(2, "little", signed=True) * 256)


class FakeEspeak:
    def list_voices(self):
        return [VOICE]

    def synthesize(self, text, voice, settings, token, output=None):
        token.check()
        if output:
            make_wav(output)


class SlowEspeak(FakeEspeak):
    def synthesize(self, text, voice, settings, token, output=None):
        for _ in range(500):
            token.check()
            time.sleep(0.01)


class ValidationTests(unittest.TestCase):
    def test_valid_text(self):
        self.assertEqual(validate_text("  Bonjour !  "), "Bonjour !")

    def test_reject_empty_long_nul(self):
        for value in ("  ", "a" * 5001, "test\x00test"):
            with self.subTest(value=value[:10]), self.assertRaises(InputError):
                validate_text(value)

    def test_settings_ranges(self):
        for settings in ((0, 100, 50), (175, -1, 50), (175, 100, 100),
                         (True, 100, 50)):
            with self.subTest(settings=settings), self.assertRaises(InputError):
                AudioSettings(*settings)

    def test_subprocess_stdin_not_shell(self):
        token = CancellationToken()
        command = [sys.executable, "-c", "import sys; assert sys.stdin.read() == '$(touch /tmp/do-not-run)'"]
        run_command(command, token, label="test", text="$(touch /tmp/do-not-run)", timeout=5)

    def test_subprocess_timeout(self):
        with self.assertRaises(EngineError):
            run_command([sys.executable, "-c", "import time;time.sleep(2)"],
                        CancellationToken(), label="test", timeout=1)

    def test_stop_process(self):
        token = CancellationToken()
        results = []
        def runner():
            try:
                run_command([sys.executable, "-c", "import time;time.sleep(20)"],
                            token, label="test", timeout=30)
            except CancelledError:
                results.append("cancelled")
        thread = threading.Thread(target=runner)
        thread.start()
        time.sleep(0.2)
        token.cancel()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results, ["cancelled"])


class AudioTests(unittest.TestCase):
    def test_volume_transform(self):
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / "output.wav"
            make_wav(wav)
            scale_volume(wav, 50, CancellationToken())
            check_wav(wav)
            with wave.open(str(wav), "rb") as reader:
                self.assertEqual(int.from_bytes(reader.readframes(1), "little", signed=True), 500)

    def test_invalid_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "empty.wav"
            file.write_bytes(b"not wav")
            with self.assertRaises(EngineError):
                check_wav(file)


class ManagerTests(unittest.TestCase):
    def test_atomic_save_success(self):
        manager = TTSManager(espeak=FakeEspeak(), detect=False)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audio.wav"
            manager.save_to_wav("Bonjour", VOICE.identifier, AudioSettings(), output)
            events = self._wait(manager)
            self.assertEqual(events[-1].kind, "saved")
            check_wav(output)
            self.assertFalse(any(Path(directory).glob(".vocalis-*")))

    def test_reject_invalid_extension(self):
        manager = TTSManager(espeak=FakeEspeak(), detect=False)
        with self.assertRaises(InputError):
            manager.save_to_wav("bonjour", VOICE.identifier, AudioSettings(), "/tmp/test.txt")

    def test_busy_then_stop(self):
        manager = TTSManager(espeak=SlowEspeak(), detect=False)
        manager.speak("bonjour", VOICE.identifier, AudioSettings())
        with self.assertRaises(BusyError):
            manager.speak("encore", VOICE.identifier, AudioSettings())
        manager.cancel()
        events = self._wait(manager)
        self.assertEqual(events[-1].kind, "stopped")

    @staticmethod
    def _wait(manager: TTSManager):
        deadline = time.monotonic() + 5
        while manager.busy and time.monotonic() < deadline:
            time.sleep(0.01)
        if manager.busy:
            raise AssertionError("worker n'a pas terminé")
        events = []
        while not manager.events.empty():
            events.append(manager.events.get_nowait())
        return events


class EngineIntegrationTests(unittest.TestCase):
    """Exécutables factices : vérification réelle des arguments sans installer les moteurs."""

    @staticmethod
    def _fake_cli(path: Path) -> None:
        path.write_text(
            f"#!{sys.executable}\n"
            "import sys, wave\n"
            "from pathlib import Path\n"
            "args = sys.argv[1:]\n"
            "if '--voices' in args:\n"
            "    print('Pty Language Age/Gender VoiceName File Other Languages')\n"
            "    print(' 5 fr --/M french roa/fr')\n"
            "    sys.exit(0)\n"
            "txt = sys.stdin.read()\n"
            "if not txt: sys.exit(6)\n"
            "output = None\n"
            "if '-w' in args: output = args[args.index('-w') + 1]\n"
            "if '--output_file' in args: output = args[args.index('--output_file') + 1]\n"
            "if output:\n"
            "    with wave.open(output, 'wb') as wav:\n"
            "        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(22050)\n"
            "        wav.writeframes(b'\\x10\\x00' * 200)\n",
            encoding="utf-8",
        )
        path.chmod(0o700)

    def test_espeak_cli_end_to_end(self):
        from tts.espeak import EspeakEngine
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            binary = base / 'fake-espeak'
            self._fake_cli(binary)
            engine = EspeakEngine(binary=str(binary))
            voices = engine.list_voices()
            self.assertEqual(voices[0].identifier, 'espeak:fr')
            wav = base / 'test.wav'
            engine.synthesize('-h; $(no shell)', voices[0], AudioSettings(),
                              CancellationToken(), wav)
            check_wav(wav)

    def test_piper_cli_end_to_end(self):
        from tts.piper import PiperEngine
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            binary = base / 'fake-piper'
            self._fake_cli(binary)
            (base / 'fr_FR-siwis-medium.onnx').write_bytes(b'demo')
            (base / 'fr_FR-siwis-medium.onnx.json').write_text('{}', encoding='utf-8')
            engine = PiperEngine(binary=str(binary), directories=(base,))
            voice = engine.list_voices()[0]
            self.assertEqual(voice.identifier, 'piper:fr_FR-siwis-medium')
            wav = base / 'test.wav'
            engine.synthesize('Bonjour !', voice, AudioSettings(volume=50),
                              CancellationToken(), wav)
            check_wav(wav)

if __name__ == "__main__":
    unittest.main()
