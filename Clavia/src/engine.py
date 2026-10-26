"""Pure, GTK-independent game rules. All markup content is XML-escaped."""

from __future__ import annotations

import math
from datetime import date, timedelta
from html import escape
from typing import TypedDict


class Metrics(TypedDict):
    accuracy: float
    cpm: int
    score: int
    xp: int
    stars: int


def same_character(typed: str, expected: str) -> bool:
    """Accept both French apostrophes but distinguish all other characters."""
    return typed == expected or (typed in ("'", '’') and expected in ("'", '’'))


def matches_target(target: str, entered: str) -> bool:
    return len(target) == len(entered) and all(
        same_character(typed, wanted) for typed, wanted in zip(entered, target)
    )


def next_expected(target: str, entered: str) -> str:
    index = len(entered)
    return target[index] if index < len(target) else ''


def error_positions(target: str, entered: str) -> set[int]:
    return {index for index, char in enumerate(entered)
            if index >= len(target) or not same_character(char, target[index])}


def rich_target(target: str, entered: str) -> str:
    """Safe Pango markup: correct / error / next character / remaining."""
    pieces: list[str] = []
    for index, char in enumerate(target):
        safe = escape(char, quote=True)
        if index < len(entered):
            color = '#D1D0C5' if same_character(entered[index], char) else '#CA4754'
            pieces.append(f'<span foreground="{color}">{safe}</span>')
        elif index == len(entered):
            pieces.append(f'<span foreground="#E2B714" background="#423B25" '
                          f'weight="bold" underline="single">{safe}</span>')
        else:
            pieces.append(f'<span foreground="#646669">{safe}</span>')
    return ''.join(pieces)


def compute_metrics(correct_chars: int, attempts: int, errors: int,
                    elapsed: float, goal_cpm: int = 100) -> Metrics:
    """Compute one session without accepting invalid or nonfinite measurements."""
    if (any(type(value) is not int for value in (correct_chars, attempts, errors, goal_cpm))
            or correct_chars < 0 or attempts < 0 or errors < 0 or errors > attempts
            or correct_chars > attempts or goal_cpm <= 0):
        raise ValueError('Compteurs ou objectif incohérents.')
    if not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError('Durée invalide.')
    safe_elapsed = max(1.0, elapsed)
    accuracy = 100 * (attempts - errors) / attempts if attempts else 100.0
    cpm = round(correct_chars * 60 / safe_elapsed)
    multiplier = max(0.15, accuracy / 100)
    base = correct_chars * 5
    speed_bonus = min(300, round(cpm / goal_cpm * 100))
    score = round((base + speed_bonus) * multiplier) if correct_chars else 0
    xp = max(5, round(score / 5)) if correct_chars else 0
    stars = (3 if accuracy >= 95 and cpm >= goal_cpm else
             2 if accuracy >= 85 else 1) if correct_chars else 0
    return {'accuracy': round(accuracy, 1), 'cpm': cpm, 'score': score,
            'xp': xp, 'stars': stars}


def consecutive_days(days: list[str] | list[date], today: date | None = None) -> int:
    """Ignore invalid historical dates instead of crashing the home screen."""
    today = today or date.today()
    unique: set[date] = set()
    for item in days:
        try:
            parsed = date.fromisoformat(item) if isinstance(item, str) else item
        except ValueError:
            continue
        if isinstance(parsed, date):
            unique.add(parsed)
    anchor = today if today in unique else today - timedelta(days=1)
    streak = 0
    while anchor in unique:
        streak += 1
        anchor -= timedelta(days=1)
    return streak


def level_from_xp(xp: int) -> int:
    if type(xp) is not int or xp < 0:
        raise ValueError('XP invalide.')
    return 1 + xp // 500


def safe_volume(value: str | int, default: int = 55) -> int:
    """Clamp an untrusted preference to the supported audio range."""
    try:
        volume = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return max(0, min(100, volume))
