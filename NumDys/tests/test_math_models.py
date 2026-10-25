import unittest
from unittest.mock import patch

from numdys.math_models import solve_linear, solve_quadratic, sequence_terms
from numdys.safe_eval import ExpressionError


class TestModels(unittest.TestCase):
    def test_linear(self):
        self.assertEqual(solve_linear(2, -4).roots, (2,))
        self.assertEqual(solve_linear(0, 0).status, "all")
        self.assertEqual(solve_linear(0, 3).status, "none")

    def test_quadratic(self):
        solution = solve_quadratic(2, 5, 2)
        self.assertEqual(solution.status, "two")
        self.assertEqual(solution.discriminant, 9)
        for actual, expected in zip(solution.roots, (-2, -0.5)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(solve_quadratic(1, 2, 1).status, "double")
        self.assertEqual(solve_quadratic(1, 0, 1).roots, (-1j, 1j))
        for coefficients in ((0, 1, 1), (float('inf'), 2, 3)):
            with self.subTest(coefficients=coefficients), self.assertRaises(ExpressionError):
                solve_quadratic(*coefficients)

    def test_sequences(self):
        terms = list(sequence_terms("u / 2 + 1", 1, 3))
        self.assertEqual([n for n, _ in terms], [0, 1, 2, 3])
        self.assertEqual([v for _, v in terms], [1, 1.5, 1.75, 1.875])
        self.assertAlmostEqual(list(sequence_terms("sin(u)", 90, 1, True))[-1][1], 1)
        for count in (0, 501, "10", True):
            with self.subTest(count=count), self.assertRaises(ExpressionError):
                list(sequence_terms("u + 1", 0, count))
        with self.assertRaisesRegex(ExpressionError, "terme 2"):
            list(sequence_terms("1 / (u - 1)", 2, 5))

    def test_compiled_only_once(self):
        from numdys import math_models
        original = math_models.compile_expression
        with patch.object(math_models, "compile_expression", wraps=original) as compile_mock:
            self.assertEqual(len(list(sequence_terms("u + 1", 1, 400))), 401)
            compile_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
