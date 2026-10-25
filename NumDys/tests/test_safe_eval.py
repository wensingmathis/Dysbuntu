"""Régressions contre injections, déni de service et erreurs de calcul."""
import math
import unittest

from numdys.safe_eval import (
    CompiledExpression, ExpressionError, MAX_EXPRESSION_LENGTH,
    compile_expression, evaluate, format_result, parse_number,
)


class TestSafeEval(unittest.TestCase):
    def test_normal_math(self):
        self.assertEqual(evaluate("1 + 2 × 3"), 7)
        self.assertAlmostEqual(evaluate("sin(90)", degree_mode=True), 1)
        self.assertAlmostEqual(evaluate("sin(pi / 2)"), 1)
        self.assertEqual(evaluate("√(9)"), 3)
        self.assertAlmostEqual(evaluate("π^2"), math.pi ** 2)
        self.assertEqual(evaluate("2,5 × 4"), 10)
        self.assertAlmostEqual(evaluate("sin(1,2)"), math.sin(1.2))
        self.assertEqual(evaluate("5//2 + 5%2"), 3)
        self.assertEqual(evaluate("abs(-4)"), 4)
        self.assertAlmostEqual(evaluate("asin(1)", degree_mode=True), 90)

    def test_compilation_and_variables(self):
        compiled = compile_expression("sin(x)+u", ("x", "u"))
        self.assertIsInstance(compiled, CompiledExpression)
        self.assertAlmostEqual(compiled.evaluate({"x": 90, "u": 2}, degree_mode=True), 3)
        with self.assertRaises(ExpressionError):
            compiled.evaluate({"x": 2})
        with self.assertRaises(ExpressionError):
            compile_expression("x", ())
        with self.assertRaises(ExpressionError):
            compile_expression("z", ("z",))

    def test_denied_python_constructs(self):
        payloads = (
            '__import__("os").system("touch /tmp/owned")',
            '().__class__.__mro__',
            'open("/etc/passwd")',
            '[x for x in range(10)]',
            '(lambda: 1)()',
            'sin(x=1)',
            'sin(1, 2)',
            'pi.real',
            'sin(*[1])',
            'True',
            '[1,2,3]',
            '1 if 1 else 2',
            '1 << 9999',
        )
        for expression in payloads:
            with self.subTest(expression=expression), self.assertRaises(ExpressionError):
                evaluate(expression)

    def test_resource_budgets(self):
        for expression in (
            "1" * (MAX_EXPRESSION_LENGTH + 1),
            "-" * 40 + "1",
            "+".join("1" for _ in range(100)),
            "2^1000",
            "2^2^200",
            "10^100*10^100",
            "1e309",
            "sqrt(-1)",
            "1 / 0",
            "1 // 0",
            "1 % 0",
            "sin(1, 2)",
        ):
            with self.subTest(expression=expression[:40]), self.assertRaises(ExpressionError):
                evaluate(expression)

    def test_invalid_variables(self):
        for value in (True, "1", float('nan'), float('inf'), 1e110, 10**600):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ExpressionError):
                evaluate("x", {"x": value})

    def test_formatting_and_parser(self):
        self.assertEqual(parse_number("3,5"), 3.5)
        self.assertEqual(format_result(2.0), "2")
        self.assertEqual(format_result(0.125), "0.125")
        for s in ("", "inf", "nan", "abc", "1" * 100):
            with self.subTest(s=s[:10]), self.assertRaises(ExpressionError):
                parse_number(s)
        with self.assertRaises(ExpressionError):
            format_result(float("inf"))


if __name__ == "__main__":
    unittest.main()
