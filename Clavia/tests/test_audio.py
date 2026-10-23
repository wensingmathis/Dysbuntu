import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from audio import SoundManager

class TestAudio(unittest.TestCase):
    def test_silence_and_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'key_press.wav').touch()
            Path(tmp,'lesson_complete.wav').touch()
            audio = SoundManager(tmp, keyboard=False, rewards=True)
            audio.player = '/usr/bin/paplay'
            with patch('audio.subprocess.Popen') as popen:
                popen.return_value = MagicMock()
                popen.return_value.poll.return_value = None
                audio.play('key_press')
                popen.assert_not_called()
                audio.play('lesson_complete')
                self.assertEqual(popen.call_count, 1)
                audio.volume = 0
                audio.play('lesson_complete')
                self.assertEqual(popen.call_count, 1)
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio=SoundManager(tmp)
            audio.player='/usr/bin/paplay'
            with patch('audio.subprocess.Popen') as popen:
                audio.play('button_click')
                popen.assert_not_called()
