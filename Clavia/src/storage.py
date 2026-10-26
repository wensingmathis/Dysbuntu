"""SQLite local storage; retains the v3.5.6 schema and historical data."""

from __future__ import annotations

import math
import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


class StorageError(RuntimeError):
    """A local progress operation failed; the user must be informed."""


class Storage:
    """Own one SQLite connection, with parameterized queries and atomic writes.

    The historical path and table names remain unchanged for backward compatibility.
    This database is user-editable: it is not a security boundary or anti-cheat store.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        is_default_path = path is None
        self.path = Path(path) if path is not None else Path.home() / '.local/share/jeu-clavier/progress.db'
        self.db: sqlite3.Connection | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if is_default_path:
                # Private user-local data, including SQLite journal/sidecar files.
                self.path.parent.chmod(0o700)
            # Avoid unintentionally writing through a link to another database.
            if self.path.is_symlink():
                raise StorageError(f'Chemin de sauvegarde symbolique refusé : {self.path}')
            connection = sqlite3.connect(self.path, timeout=5.0)
            self.db = connection
            if is_default_path and self.path.stat().st_uid == os.getuid():
                self.path.chmod(0o600)
            connection.row_factory = sqlite3.Row
            with connection:
                connection.executescript('''
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
                connection.execute('CREATE INDEX IF NOT EXISTS idx_sessions_lesson ON sessions_v2(lesson_id)')
                connection.execute('CREATE INDEX IF NOT EXISTS idx_sessions_day ON sessions_v2(day)')
        except (OSError, sqlite3.Error) as exc:
            if self.db is not None:
                self.db.close()
                self.db = None
            raise StorageError(f'Impossible d’ouvrir la sauvegarde {self.path}: {exc}') from exc

    def _connection(self) -> sqlite3.Connection:
        if self.db is None:
            raise StorageError('La sauvegarde est déjà fermée.')
        return self.db

    def _one(self, sql: str, values: tuple[Any, ...] = ()) -> sqlite3.Row:
        try:
            row = self._connection().execute(sql, values).fetchone()
        except sqlite3.Error as exc:
            raise StorageError(f'Lecture SQLite impossible : {exc}') from exc
        if row is None:
            raise StorageError('Résultat SQLite absent.')
        return row

    def _all(self, sql: str, values: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        try:
            return self._connection().execute(sql, values).fetchall()
        except sqlite3.Error as exc:
            raise StorageError(f'Lecture SQLite impossible : {exc}') from exc

    @staticmethod
    def _validate_session(lesson_id: int | None, mode: str, typed: int,
                          attempts: int, errors: int, seconds: float,
                          metrics: dict[str, int | float]) -> None:
        from content import LESSONS
        if lesson_id is not None and (type(lesson_id) is not int or not 1 <= lesson_id <= len(LESSONS)):
            raise ValueError('Identifiant de leçon incorrect.')
        if not isinstance(mode, str) or not mode or len(mode) > 32:
            raise ValueError('Mode de jeu incorrect.')
        if (not all(type(value) is int for value in (typed, attempts, errors))
                or not 0 <= typed <= attempts or not 0 <= errors <= attempts):
            raise ValueError('Compteurs de session incohérents.')
        if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Durée de session incorrecte.')
        for field in ('cpm', 'score', 'xp', 'stars'):
            if type(metrics.get(field)) is not int or metrics[field] < 0:
                raise ValueError(f'Métrique incorrecte : {field}.')
        if metrics['stars'] > 3:
            raise ValueError('Nombre d’étoiles incorrect.')
        accuracy = metrics.get('accuracy')
        if not isinstance(accuracy, (int, float)) or not math.isfinite(accuracy) or not 0 <= accuracy <= 100:
            raise ValueError('Précision incorrecte.')

    def save(self, lesson_id: int | None, mode: str, typed: int, attempts: int,
             errors: int, seconds: float, metrics: dict[str, int | float]) -> None:
        self._validate_session(lesson_id, mode, typed, attempts, errors, seconds, metrics)
        try:
            with self._connection() as db:
                db.execute('''
                    INSERT INTO sessions_v2
                    (lesson_id,mode,typed,attempts,errors,seconds,accuracy,cpm,score,xp,stars,day)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (lesson_id, mode, typed, attempts, errors, seconds,
                      metrics['accuracy'], metrics['cpm'], metrics['score'],
                      metrics['xp'], metrics['stars'], date.today().isoformat()))
        except sqlite3.Error as exc:
            raise StorageError(f'Enregistrement de la session impossible : {exc}') from exc

    def summary(self) -> dict[str, int | float]:
        row = self._one('''
            SELECT COUNT(*) sessions, COALESCE(SUM(xp), 0) xp,
            COALESCE(SUM(score), 0) score, COALESCE(SUM(typed), 0) chars,
            COALESCE(SUM(errors), 0) errors, COALESCE(SUM(attempts), 0) attempts,
            COALESCE(SUM(seconds), 0) seconds
            FROM sessions_v2
        ''')
        return dict(row)

    def completed_ids(self) -> set[int]:
        return {row[0] for row in self._all(
            'SELECT DISTINCT lesson_id FROM sessions_v2 WHERE lesson_id IS NOT NULL')
                if type(row[0]) is int}

    def unlocked_id(self) -> int:
        from content import LESSONS
        completed = self.completed_ids()
        for index in range(1, len(LESSONS) + 1):
            if index not in completed:
                return index
        return len(LESSONS) + 1

    def best(self, lesson_id: int) -> dict[str, int | None]:
        return dict(self._one('''
            SELECT MAX(score) best_score, MAX(stars) stars, MAX(cpm) best_cpm
            FROM sessions_v2 WHERE lesson_id=?
        ''', (lesson_id,)))

    def best_by_lesson(self) -> dict[int, dict[str, int | None]]:
        """Fetch all lesson records in a single query for the home screen."""
        rows = self._all('''
            SELECT lesson_id, MAX(score) best_score, MAX(stars) stars,
                   MAX(cpm) best_cpm FROM sessions_v2
            WHERE lesson_id IS NOT NULL GROUP BY lesson_id
        ''')
        return {row['lesson_id']: dict(row) for row in rows}

    def active_days(self) -> list[str]:
        return [row[0] for row in self._all('SELECT DISTINCT day FROM sessions_v2')]

    def today_sessions(self) -> int:
        return self._one('SELECT COUNT(*) FROM sessions_v2 WHERE day=?',
                         (date.today().isoformat(),))[0]

    def records(self) -> list[sqlite3.Row]:
        return self._all('''
            SELECT mode, MAX(cpm) best_cpm, MAX(score) best_score,
                   COUNT(*) completed FROM sessions_v2 GROUP BY mode ORDER BY mode
        ''')

    def recent_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError('La limite doit être comprise entre 1 et 500.')
        rows = self._all('''
            SELECT cpm, accuracy, day FROM sessions_v2
            ORDER BY id DESC LIMIT ?
        ''', (limit,))
        return [dict(row) for row in reversed(rows)]

    def preference(self, name: str, default: str) -> str:
        if not isinstance(name, str) or not name:
            raise ValueError('Préférence sans nom.')
        try:
            row = self._connection().execute('SELECT value FROM preferences WHERE name=?', (name,)).fetchone()
        except sqlite3.Error as exc:
            raise StorageError(f'Préférence illisible ({name}) : {exc}') from exc
        return str(row[0]) if row else default

    def set_preference(self, name: str, value: str | int) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError('Préférence sans nom.')
        try:
            with self._connection() as db:
                db.execute('INSERT OR REPLACE INTO preferences(name,value) VALUES(?,?)',
                           (name, str(value)))
        except sqlite3.Error as exc:
            raise StorageError(f'Préférence non enregistrée ({name}) : {exc}') from exc

    def close(self) -> None:
        if self.db is not None:
            db, self.db = self.db, None
            try:
                db.close()
            except sqlite3.Error as exc:
                raise StorageError(f'Fermeture de la sauvegarde impossible : {exc}') from exc
