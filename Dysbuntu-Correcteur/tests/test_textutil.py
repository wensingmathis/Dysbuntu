import unittest

from tests import helpers  # noqa: F401
from dysbuntu_correcteur import textutil as t


class TextUtilTests(unittest.TestCase):
    def test_bmp_text_identical(self):
        s = "Élève très ému, où ça ?"
        self.assertEqual(t.utf16_len(s), len(s))
        self.assertEqual(t.utf16_to_index(s, 5), 5)

    def test_emoji_counts_two_units(self):
        s = "a😀b"
        self.assertEqual(t.utf16_len(s), 4)
        self.assertEqual(t.utf16_to_index(s, 3), 2)  # 'b'
        self.assertEqual(t.index_to_utf16(s, 2), 3)
        self.assertEqual(t.utf16_slice(s, 3, 1), "b")
        self.assertEqual(t.utf16_slice(s, 1, 2), "😀")

    def test_split_short_text_untouched(self):
        self.assertEqual(t.split_text("abc", 100), [(0, "abc")])

    def test_split_reassembles_and_offsets(self):
        text = ("Une phrase. " * 50).strip()
        chunks = t.split_text(text, 80)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(c for _, c in chunks), text)
        for off, chunk in chunks:
            self.assertLessEqual(len(chunk), 80)
            self.assertEqual(text[off:off + len(chunk)], chunk)

    def test_split_without_spaces_still_terminates(self):
        chunks = t.split_text("x" * 250, 100)
        self.assertEqual("".join(c for _, c in chunks), "x" * 250)


if __name__ == "__main__":
    unittest.main()
