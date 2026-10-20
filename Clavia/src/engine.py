"""Calculs purs (sans GTK) pour pouvoir tester les règles du jeu."""
from datetime import date, timedelta
from html import escape


def next_expected(target: str, entered: str) -> str:
    """Prochain caractère à afficher sur le clavier virtuel."""
    i = len(entered)
    return target[i] if i < len(target) else ''


def error_positions(target: str, entered: str) -> set[int]:
    return {i for i, char in enumerate(entered) if i >= len(target) or char != target[i]}


def rich_target(target: str, entered: str) -> str:
    """Pango markup: correct / faux / caractère suivant / reste."""
    pieces = []
    for i, char in enumerate(target):
        safe = escape(char)
        if i < len(entered):
            color = '#D1D0C5' if entered[i] == char else '#CA4754'
            pieces.append(f'<span foreground="{color}">{safe}</span>')
        elif i == len(entered):
            pieces.append(f'<span foreground="#E2B714" underline="single">{safe}</span>')
        else:
            pieces.append(f'<span foreground="#646669">{safe}</span>')
    return ''.join(pieces)


def compute_metrics(correct_chars: int, attempts: int, errors: int, elapsed: float, goal_cpm: int = 100):
    elapsed = max(1.0, elapsed)
    accuracy = 100 * max(0, attempts - errors) / max(1, attempts)
    cpm = round(correct_chars * 60 / elapsed)
    # La précision compte plus que la vitesse; aucune récompense pour le spam.
    multiplier = max(0.15, accuracy / 100)
    base = correct_chars * 5
    speed_bonus = min(300, round(cpm / max(1, goal_cpm) * 100))
    score = round((base + speed_bonus) * multiplier)
    xp = max(5, round(score / 5)) if correct_chars else 0
    stars = 3 if accuracy >= 95 and cpm >= goal_cpm else 2 if accuracy >= 85 else 1
    return {'accuracy': round(accuracy, 1), 'cpm': cpm, 'score': score,
            'xp': xp, 'stars': stars}


def consecutive_days(days, today=None):
    """Série actuelle : elle subsiste si on a joué hier."""
    today = today or date.today()
    unique = {date.fromisoformat(day) if isinstance(day, str) else day for day in days}
    anchor = today if today in unique else today - timedelta(days=1)
    streak = 0
    while anchor in unique:
        streak += 1
        anchor -= timedelta(days=1)
    return streak


def level_from_xp(xp: int) -> int:
    return 1 + xp // 500
