import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from content import LESSONS
from engine import (compute_metrics, consecutive_days, error_positions,
                    level_from_xp, next_expected, rich_target)
from storage import Storage


class TestGame(unittest.TestCase):
    def test_curriculum(self):
        self.assertEqual(len(LESSONS), 18)
        self.assertEqual(LESSONS[0].kind, 'Mots')
        self.assertEqual(LESSONS[6].kind, 'Phrases')
        self.assertEqual(LESSONS[12].kind, 'Textes')
        self.assertTrue(all(lesson.prompts for lesson in LESSONS))

    def test_key_prompt(self):
        self.assertEqual(next_expected('été', 'é'), 't')
        self.assertEqual(next_expected('test', 'test'), '')
        self.assertEqual(error_positions('bonjour', 'bonx'), {3})

    def test_markup_safe(self):
        self.assertIn('&amp;', rich_target('a&b', 'a'))
        self.assertIn('#CA4754', rich_target('abc', 'ax'))

    def test_metrics(self):
        quick = compute_metrics(120, 120, 0, 30)
        slow = compute_metrics(120, 120, 0, 120)
        self.assertGreater(quick['score'], slow['score'])
        inaccurate = compute_metrics(120, 120, 25, 30)
        self.assertLess(inaccurate['score'], quick['score'])
        self.assertEqual(quick['accuracy'], 100)

    def test_streak(self):
        d = date(2026, 10, 20)
        self.assertEqual(consecutive_days(['2026-10-18', '2026-10-19'], d), 2)
        self.assertEqual(consecutive_days(['2026-10-17'], d), 0)
        self.assertEqual(consecutive_days(['2026-10-18', '2026-10-19', '2026-10-20'], d), 3)

    def test_level(self):
        self.assertEqual(level_from_xp(0), 1)
        self.assertEqual(level_from_xp(999), 2)

    def test_storage(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            db = Storage(Path(d) / 'progress.db')
            self.assertEqual(db.unlocked_id(), 1)
            metrics = compute_metrics(40, 40, 0, 20)
            db.save(1, 'Mots', 40, 40, 0, 20, metrics)
            self.assertEqual(db.unlocked_id(), 2)
            self.assertEqual(db.today_sessions(), 1)
            self.assertEqual(db.best(1)['stars'], metrics['stars'])
            self.assertEqual(db.recent_sessions()[-1]['cpm'], metrics['cpm'])
            db.close()


if __name__ == '__main__':
    unittest.main()
