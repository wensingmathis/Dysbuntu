"""Algorithmes mathématiques sans dépendance graphique, faciles à tester."""
from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Iterator

from .safe_eval import (
    ExpressionError, checked_number, compile_expression,
)

MAX_SEQUENCE_TERMS = 500


@dataclass(frozen=True, slots=True)
class EquationSolution:
    status: str  # none | all | one | two | double | complex
    roots: tuple[complex | float, ...] = ()
    discriminant: float | None = None


def _check_root(value: float) -> float:
    return checked_number(value, "Racine")


def solve_linear(a: float, b: float) -> EquationSolution:
    a = checked_number(a, "a")
    b = checked_number(b, "b")
    if a == 0:
        return EquationSolution("all" if b == 0 else "none")
    return EquationSolution("one", (_check_root(-b / a),))


def solve_quadratic(a: float, b: float, c: float) -> EquationSolution:
    a, b, c = (checked_number(v, key) for v, key in zip((a, b, c), "abc"))
    if a == 0:
        raise ExpressionError("a doit être différent de zéro (degré 2)")
    # Normalise les coefficients afin de limiter les débordements de b² et 4ac.
    scale = max(abs(a), abs(b), abs(c))
    aa, bb, cc = a / scale, b / scale, c / scale
    if aa == 0:
        raise ExpressionError("Coefficients trop déséquilibrés")
    delta = bb * bb - 4 * aa * cc
    actual_delta = b * b - 4 * a * c
    if delta > 0:
        sqrt_delta = math.sqrt(delta)
        # Formule stable pour éviter une soustraction de valeurs proches.
        q = -0.5 * (bb + math.copysign(sqrt_delta, bb))
        roots = (_check_root(q / aa), _check_root(cc / q)) if q else (
            _check_root((-bb - sqrt_delta) / (2 * aa)),
            _check_root((-bb + sqrt_delta) / (2 * aa)),
        )
        return EquationSolution("two", tuple(sorted(roots)), actual_delta)
    if delta == 0:
        return EquationSolution("double", (_check_root(-bb / (2 * aa)),), actual_delta)
    real = _check_root(-bb / (2 * aa))
    imaginary = _check_root(math.sqrt(-delta) / abs(2 * aa))
    return EquationSolution("complex", (complex(real, -imaginary), complex(real, imaginary)), actual_delta)


def sequence_terms(expression: str, u0: float, count: int, degree_mode: bool = False) -> Iterator[tuple[int, float]]:
    """Produit u0...uN, avec N borné et compilation unique."""
    if type(count) is not int or not (1 <= count <= MAX_SEQUENCE_TERMS):
        raise ExpressionError("Choisissez entre 1 et 500 termes")
    compiled = compile_expression(expression, ("u", "n"))
    u = checked_number(u0, "u0")
    yield 0, u
    for n in range(count):
        try:
            u = compiled.evaluate({"u": u, "n": n}, degree_mode=degree_mode)
        except ExpressionError as exc:
            raise ExpressionError(f"Erreur au terme {n+1} : {exc}") from exc
        yield n + 1, u
