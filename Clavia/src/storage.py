"""Sauvegardes locales SQLite. L'ancienne base des versions précédentes est conservée."""
import sqlite3
from datetime import date
from pathlib import Path


class Storage:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path.home() / '.local/share/jeu-clavier/progress.db'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS sessions_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER,
                mode TEXT NOT NULL,
                typed INTEGER NOT NULL,
                attempts INTEGER NOT NULL,
                errors INTEGER NOT NULL,
                seconds REAL NOT NULL,
                accuracy REAL NOT NULL,
                cpm INTEGER NOT NULL,
                score INTEGER NOT NULL,
                xp INTEGER NOT NULL,
                stars INTEGER NOT NULL,
                day TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS preferences (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        ''')
        self.db.commit()

    def save(self, lesson_id, mode, typed, attempts, errors, seconds, metrics):
        self.db.execute('''
            INSERT INTO sessions_v2
            (lesson_id,mode,typed,attempts,errors,seconds,accuracy,cpm,score,xp,stars,day)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (lesson_id, mode, typed, attempts, errors, seconds, metrics['accuracy'],
              metrics['cpm'], metrics['score'], metrics['xp'], metrics['stars'], date.today().isoformat()))
        self.db.commit()

    def summary(self):
        row = self.db.execute('''
            SELECT COUNT(*) sessions, COALESCE(SUM(xp), 0) xp,
            COALESCE(SUM(score), 0) score, COALESCE(SUM(typed), 0) chars,
            COALESCE(SUM(errors), 0) errors, COALESCE(SUM(attempts), 0) attempts,
            COALESCE(SUM(seconds), 0) seconds
            FROM sessions_v2
        ''').fetchone()
        return dict(row)

    def completed_ids(self):
        return {row[0] for row in self.db.execute('SELECT DISTINCT lesson_id FROM sessions_v2 WHERE lesson_id IS NOT NULL')}

    def unlocked_id(self):
        ids = self.completed_ids()
        # Aucun saut de niveau permis, même si la base était modifiée autrefois.
        from content import LESSONS
        for i in range(1, len(LESSONS) + 1):
            if i not in ids:
                return i
        return len(LESSONS) + 1

    def best(self, lesson_id):
        row = self.db.execute('''
            SELECT MAX(score) best_score, MAX(stars) stars, MAX(cpm) best_cpm
            FROM sessions_v2 WHERE lesson_id=?
        ''', (lesson_id,)).fetchone()
        return dict(row)

    def active_days(self):
        return [row[0] for row in self.db.execute('SELECT DISTINCT day FROM sessions_v2')]

    def today_sessions(self):
        return self.db.execute('SELECT COUNT(*) FROM sessions_v2 WHERE day=?', (date.today().isoformat(),)).fetchone()[0]

    def records(self):
        return self.db.execute('''
            SELECT mode, MAX(cpm) best_cpm, MAX(score) best_score, COUNT(*) completed
            FROM sessions_v2 GROUP BY mode ORDER BY mode
        ''').fetchall()

    def recent_sessions(self, limit=20):
        """Dernières vitesses, présentées du plus ancien au plus récent."""
        rows = self.db.execute('''
            SELECT cpm, accuracy, day FROM sessions_v2
            ORDER BY id DESC LIMIT ?
        ''', (limit,)).fetchall()
        return list(reversed([dict(row) for row in rows]))

    def preference(self, name, default):
        row = self.db.execute('SELECT value FROM preferences WHERE name=?', (name,)).fetchone()
        return row[0] if row else default

    def set_preference(self, name, value):
        self.db.execute('INSERT OR REPLACE INTO preferences(name,value) VALUES(?,?)', (name, str(value)))
        self.db.commit()

    def close(self):
        self.db.close()
