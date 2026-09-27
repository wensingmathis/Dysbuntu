"""
Évaluateur d'expressions mathématiques sécurisé.

On n'utilise JAMAIS eval()/exec() sur une saisie utilisateur. On parse
l'expression en arbre syntaxique (module ast) et on interprète nous-mêmes
uniquement les nœuds explicitement autorisés (nombres, opérateurs
arithmétiques, variables connues, appels aux fonctions mathématiques
listées ci-dessous). Tout le reste lève une ExpressionError.
"""

from __future__ import annotations

import ast
import math
import operator as op

BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

UNARY_OPS = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}

CONSTANTS = {"pi": math.pi, "e": math.e}


class ExpressionError(Exception):
    """Erreur levée pour toute expression invalide ou non autorisée."""


def _functions(degree_mode: bool):
    """Renvoie le dictionnaire des fonctions autorisées, en tenant compte
    du mode degrés/radians pour les fonctions trigonométriques."""

    if degree_mode:
        return {
            "sin": lambda x: math.sin(math.radians(x)),
            "cos": lambda x: math.cos(math.radians(x)),
            "tan": lambda x: math.tan(math.radians(x)),
            "asin": lambda x: math.degrees(math.asin(x)),
            "acos": lambda x: math.degrees(math.acos(x)),
            "atan": lambda x: math.degrees(math.atan(x)),
            "sqrt": math.sqrt,
            "ln": math.log,
            "log": math.log10,
            "exp": math.exp,
            "abs": abs,
        }
    return {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sqrt": math.sqrt,
        "ln": math.log,
        "log": math.log10,
        "exp": math.exp,
        "abs": abs,
    }


def _normalize(expression: str) -> str:
    text = expression.strip()
    text = text.replace("×", "*").replace("÷", "/")
    text = text.replace(",", ".")
    text = text.replace("^", "**")
    text = text.replace("√", "sqrt")
    return text


def evaluate(expression: str, variables: dict | None = None, degree_mode: bool = False):
    """Évalue une expression mathématique et renvoie un nombre (int/float).

    variables : dictionnaire de variables autorisées dans l'expression
                (par exemple {"x": 2.5} pour les graphiques, ou
                {"n": 3, "u": 1.0} pour les suites).
    degree_mode : si True, les fonctions trigonométriques travaillent en
                  degrés plutôt qu'en radians.
    """
    variables = variables or {}
    funcs = _functions(degree_mode)
    text = _normalize(expression)

    if not text:
        raise ExpressionError("Expression vide")

    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError):
        raise ExpressionError("Syntaxe invalide")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ExpressionError("Valeur invalide")

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in BIN_OPS:
                raise ExpressionError("Opérateur non supporté")
            left = _eval(node.left)
            right = _eval(node.right)
            try:
                return BIN_OPS[op_type](left, right)
            except ZeroDivisionError:
                raise ExpressionError("Division par zéro")

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in UNARY_OPS:
                raise ExpressionError("Opérateur non supporté")
            return UNARY_OPS[op_type](_eval(node.operand))

        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            if node.id in CONSTANTS:
                return CONSTANTS[node.id]
            raise ExpressionError(f"Variable inconnue : {node.id}")

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ExpressionError("Appel de fonction invalide")
            name = node.func.id
            if name not in funcs:
                raise ExpressionError(f"Fonction inconnue : {name}")
            if node.keywords:
                raise ExpressionError("Arguments nommés non supportés")
            args = [_eval(a) for a in node.args]
            try:
                return funcs[name](*args)
            except ValueError:
                raise ExpressionError("Domaine invalide pour cette fonction")

        raise ExpressionError("Expression non supportée")

    try:
        result = _eval(tree)
    except ZeroDivisionError:
        raise ExpressionError("Division par zéro")
    except (TypeError, ValueError):
        raise ExpressionError("Expression invalide")

    if isinstance(result, complex):
        raise ExpressionError("Résultat complexe non supporté")

    return result


def format_result(value) -> str:
    """Formate un nombre pour l'affichage (entiers sans décimales)."""
    if isinstance(value, float):
        if math.isnan(value):
            return "Erreur"
        if math.isinf(value):
            return "∞" if value > 0 else "-∞"
        if value.is_integer():
            return str(int(value))
        return f"{round(value, 10):g}"
    return str(value)
