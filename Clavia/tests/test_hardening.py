"""Regression tests for Clavia 3.5.7 hardening, no GTK dependency."""

import math
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / 'src'))

from audio import SoundManager
from engine import compute_metrics, consecutive_days, level_from_xp, safe_volume
from storage import Storage, StorageError


class MetricsValidationTests(unittest.TestCase):
    def test_rejects_invalid_counts(self):
        for args in ((-1, 0, 0, 1), (3, 2, 0, 1), (0, 1, 2, 1), (0, -1, 0, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                compute_metrics(*args)

    def test_rejects_invalid_seconds(self):
        for elapsed in (-1, math.nan, math.inf, 'slow'):
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                compute_metrics(1, 1, 0, elapsed)

    def test_empty_session_earns_nothing(self):
        metrics = compute_metrics(0, 0, 0, 0)
        self.assertEqual((metrics['score'], metrics['xp'], metrics['stars']), (0, 0, 0))

    def test_volume_preferences(self):
        self.assertEqual(safe_volume('oops'), 55)
        self.assertEqual(safe_volume('99999'), 100)
        self.assertEqual(safe_volume('-15'), 0)
        self.assertEqual(safe_volume('43'), 43)

    def test_bad_historical_dates_are_ignored(self):
        self.assertEqual(consecutive_days(['bad-date', '2026-10-25'], date(2026, 10, 26)), 1)

    def test_negative_xp_is_rejected(self):
        with self.assertRaises(ValueError):
            level_from_xp(-5)


class StorageHardeningTests(unittest.TestCase):
    def test_default_save_file_permissions_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('storage.Path.home', return_value=Path(tmp)):
                db = Storage()
                self.assertEqual(os.stat(db.path).st_mode & 0o777, 0o600)
                self.assertEqual(os.stat(db.path.parent).st_mode & 0o777, 0o700)
                db.close()

    def test_invalid_session_not_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Storage(Path(tmp) / 'progress.db')
            metrics = compute_metrics(2, 2, 0, 5)
            with self.assertRaises(ValueError):
                db.save(1, 'Mots', 5, 2, 0, 5, metrics)
            self.assertEqual(db.summary()['sessions'], 0)
            db.close()

    def test_grouped_best_scores_preserves_existing_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Storage(Path(tmp) / 'progress.db')
            fast = compute_metrics(8, 8, 0, 3)
            slow = compute_metrics(8, 9, 1, 12)
            db.save(1, 'Mots', 8, 8, 0, 3, fast)
            db.save(1, 'Mots', 8, 9, 1, 12, slow)
            db.save(2, 'Mots', 8, 8, 0, 3, fast)
            self.assertEqual(db.best_by_lesson()[1]['best_score'], db.best(1)['best_score'])
            self.assertEqual(db.best_by_lesson()[2]['best_score'], fast['score'])
            db.close()

    def test_invalid_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Storage(Path(tmp) / 'progress.db')
            for limit in (0, -1, 501, 'all'):
                with self.subTest(limit=limit), self.assertRaises(ValueError):
                    db.recent_sessions(limit)
            db.close()

    def test_corrupt_database_has_explicit_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'progress.db'
            path.write_bytes(b'not a valid sqlite database')
            with self.assertRaises(StorageError):
                Storage(path)

    def test_closed_database_has_explicit_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Storage(Path(tmp) / 'progress.db')
            db.close()
            db.close()
            with self.assertRaises(StorageError):
                db.summary()

    def test_symlink_database_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            target = p / 'target.db'
            target.write_bytes(b'placeholder')
            (p / 'link.db').symlink_to(target)
            with self.assertRaises(StorageError):
                Storage(p / 'link.db')
            self.assertEqual(target.read_bytes(), b'placeholder')

    def test_legacy_preferences_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'progress.db'
            db = Storage(path)
            db.set_preference('dark', '0')
            db.close()
            reopened = Storage(path)
            self.assertEqual(reopened.preference('dark', '1'), '0')
            reopened.close()


class AudioHardeningTests(unittest.TestCase):
    def test_allowlist_blocks_unexpected_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'button_click.wav').touch()
            audio = SoundManager(tmp)
            audio.player = '/usr/bin/paplay'
            with patch('audio.subprocess.Popen') as mocked:
                audio.play('../button_click')
                audio.play('button_click/../button_click')
                mocked.assert_not_called()

    def test_terminate_and_reap_processes(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = SoundManager(tmp)
            child = MagicMock()
            child.poll.return_value = None
            child.wait.return_value = 0
            audio.running.append(child)
            audio.close()
            child.terminate.assert_called_once()
            child.wait.assert_called_once()
            self.assertEqual(audio.running, [])
            audio.close()

    def test_force_kill_stuck_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = SoundManager(tmp)
            child = MagicMock()
            child.poll.return_value = None
            child.wait.side_effect = [subprocess.TimeoutExpired('paplay', .15), 0]
            audio.running.append(child)
            audio.close()
            child.kill.assert_called_once()


class LocalInstallationTests(unittest.TestCase):
    def test_local_install_is_independent_of_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'home with spaces'
            home.mkdir()
            proc = subprocess.run(['sh', str(SOURCE / 'install-local.sh')],
                                  env={'HOME': str(home), 'PATH': '/usr/bin:/bin'},
                                  capture_output=True, text=True, timeout=15, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            launcher = (home / '.local/bin/clavia').read_text()
            self.assertIn('"$HOME/.local/share/clavia/src/main.py"', launcher)
            self.assertNotIn(str(SOURCE), launcher)
            self.assertTrue((home / '.local/share/clavia/assets/flamme-streak.png').is_file())
            self.assertTrue((home / '.local/share/clavia/src/main.py').is_file())


if __name__ == '__main__':
    unittest.main()
