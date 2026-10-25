"""Moteur mathématique NumDys, sans eval/exec et avec budget d'exécution.

Les expressions sont compilées une fois, puis évaluées pour plusieurs points.
Les seules données utilisateur évaluées sont des scalaires numériques finis.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import math
import operator
from collections.abc import Mapping
from typing import Callable

MAX_EXPRESSION_LENGTH = 256
MAX_AST_NODES = 128
MAX_AST_DEPTH = 24
MAX_ABS_VALUE = 1e100
MAX_EXPONENT = 100.0

_BINARY: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_CONSTANTS = {"pi": math.pi, "e": math.e}
_FUNCTIONS = frozenset({"sin", "cos", "tan", "asin", "acos", "atan", "sqrt", "ln", "log", "exp", "abs"})


class ExpressionError(ValueError):
    """Une saisie mathématique est interdite, invalide ou trop coûteuse."""


def checked_number(value: object, name: str = "Nombre") -> float:
    """Refuse les booléens, entiers géants, NaN et infinis dès l'entrée."""
    if type(value) not in (int, float):
        raise ExpressionError(f"{name} : nombre invalide")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ExpressionError(f"{name} : nombre trop grand") from exc
    if not math.isfinite(number) or abs(number) > MAX_ABS_VALUE:
        raise ExpressionError(f"{name} : valeur hors limites")
    return number


def parse_number(text: str, name: str = "Nombre") -> float:
    """Lit un coefficient décimal en notation française, sans expression."""
    if len(text) > 64:
        raise ExpressionError(f"{name} : saisie trop longue")
    try:
        return checked_number(float(text.strip().replace(",", ".")), name)
    except ValueError as exc:
        if isinstance(exc, ExpressionError):
            raise
        raise ExpressionError(f"{name} : nombre invalide") from exc


def _normalize(expression: str) -> str:
    return (expression.strip().replace("×", "*").replace("÷", "/")
            .replace(",", ".").replace("^", "**")
            .replace("π", "pi").replace("√", "sqrt"))


def _validate_node(node: ast.AST, allowed: frozenset[str], depth: int = 0) -> None:
    if depth > MAX_AST_DEPTH:
        raise ExpressionError("Expression trop imbriquée")
    if isinstance(node, ast.Expression):
        _validate_node(node.body, allowed, depth + 1)
    elif isinstance(node, ast.Constant):
        checked_number(node.value)
    elif isinstance(node, ast.Name):
        if node.id not in allowed and node.id not in _CONSTANTS:
            raise ExpressionError(f"Variable inconnue : {node.id}")
    elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        _validate_node(node.left, allowed, depth + 1)
        _validate_node(node.right, allowed, depth + 1)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        _validate_node(node.operand, allowed, depth + 1)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise ExpressionError("Fonction non autorisée")
        if len(node.args) != 1 or node.keywords:
            raise ExpressionError("Cette fonction attend exactement un argument")
        _validate_node(node.args[0], allowed, depth + 1)
    else:
        raise ExpressionError("Expression non autorisée")


def _apply_function(name: str, x: float, degree_mode: bool) -> float:
    # Conversion des angles seulement pour la trigonométrie directe/inverse.
    if name in {"sin", "cos", "tan"}:
        return getattr(math, name)(math.radians(x) if degree_mode else x)
    if name in {"asin", "acos", "atan"}:
        result = getattr(math, name)(x)
        return math.degrees(result) if degree_mode else result
    if name == "ln":
        return math.log(x)
    if name == "log":
        return math.log10(x)
    if name == "sqrt":
        return math.sqrt(x)
    if name == "exp":
        return math.exp(x)
    if name == "abs":
        return abs(x)
    raise ExpressionError("Fonction non autorisée")


@dataclass(frozen=True, slots=True)
class CompiledExpression:
    """AST validé et réutilisable ; aucun code Python externe n'est exécuté."""

    body: ast.expr
    variables: frozenset[str]

    def evaluate(self, variables: Mapping[str, float] | None = None, degree_mode: bool = False) -> float:
        values = variables if variables is not None else {}
        numbers = {key: checked_number(values[key], key) for key in self.variables if key in values}
        if len(numbers) != len(self.variables):
            missing = self.variables - numbers.keys()
            raise ExpressionError(f"Variable manquante : {', '.join(sorted(missing))}")

        def run(node: ast.AST) -> float:
            if isinstance(node, ast.Constant):
                return checked_number(node.value)
            if isinstance(node, ast.Name):
                return numbers[node.id] if node.id in numbers else _CONSTANTS[node.id]
            if isinstance(node, ast.UnaryOp):
                result = _UNARY[type(node.op)](run(node.operand))
                return checked_number(result, "Résultat")
            if isinstance(node, ast.BinOp):
                left, right = run(node.left), run(node.right)
                if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
                    raise ExpressionError("Exposant trop grand (limite : 100)")
                result = _BINARY[type(node.op)](left, right)
                return checked_number(result, "Résultat")
            if isinstance(node, ast.Call):
                result = _apply_function(node.func.id, run(node.args[0]), degree_mode)
                return checked_number(result, "Résultat")
            raise ExpressionError("Expression non autorisée")

        try:
            return run(self.body)
        except ZeroDivisionError as exc:
            raise ExpressionError("Division par zéro") from exc
        except OverflowError as exc:
            raise ExpressionError("Dépassement de capacité numérique") from exc
        except ValueError as exc:
            if isinstance(exc, ExpressionError):
                raise
            raise ExpressionError("Valeur hors domaine mathématique") from exc
        except TypeError as exc:
            raise ExpressionError("Arguments mathématiques invalides") from exc


def compile_expression(expression: str, allowed_variables: tuple[str, ...] = ()) -> CompiledExpression:
    """Contrôle une seule fois la longueur, les noms, l'AST et sa profondeur."""
    if not isinstance(expression, str):
        raise ExpressionError("Expression invalide")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ExpressionError("Expression trop longue (256 caractères maximum)")
    normalized = _normalize(expression)
    if not normalized:
        raise ExpressionError("Expression vide")
    allowed = frozenset(allowed_variables)
    if not allowed.issubset({"x", "n", "u"}):
        raise ExpressionError("Nom de variable non autorisé")
    try:
        tree = ast.parse(normalized, mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        raise ExpressionError("Syntaxe invalide") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise ExpressionError("Expression trop complexe")
    _validate_node(tree, allowed)
    used = frozenset(node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in allowed)
    return CompiledExpression(tree.body, used)


def evaluate(expression: str, variables: Mapping[str, float] | None = None, degree_mode: bool = False) -> float:
    """Interface simple de compatibilité pour les calculs ponctuels."""
    values = variables if variables is not None else {}
    return compile_expression(expression, tuple(values)).evaluate(values, degree_mode)


def format_result(value: int | float) -> str:
    """Notation lisible, bornée et compatible avec un nouveau calcul."""
    number = checked_number(value, "Résultat")
    if abs(number) < 1e12 and number.is_integer():
        return str(int(number))
    return f"{number:.12g}"
