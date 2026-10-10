"""Teste l'adaptateur Writer avec des objets UNO factices (duck typing)."""
import unittest

from tests import helpers  # noqa: F401
from dysbuntu_correcteur import uno_document as ud


class FakeLocale:
    def __init__(self, lang="fr", country="FR"):
        self.Language, self.Country = lang, country


class FakeCursor:
    def __init__(self, para):
        self.para, self.start, self.end = para, 0, 0
        self.log = []

    # Pas de gotoStart() : sur un vrai paragraphe il va au début du document (piège réel).

    def goRight(self, n, expand):
        assert -32768 <= n <= 32767, "goRight prend un short"
        self.end += n
        if not expand:
            self.start = self.end

    def setString(self, s):
        t = self.para.text
        self.para.text = t[:self.start] + s + t[self.end:]

    def getEnd(self):
        return ("pos", self.end)

    def getText(self):
        return self.para.getText()


class FakePara:
    def __init__(self, text, locale=None):
        self.text, self.locale = text, locale or FakeLocale()

    def supportsService(self, name):
        return name == "com.sun.star.text.Paragraph"

    def getString(self):
        return self.text

    def getPropertyValue(self, name):
        assert name == "CharLocale"
        return self.locale

    def getStart(self):
        return "debut-paragraphe"

    def getText(self):
        para = self

        class _Text:
            def createTextCursorByRange(self, rng):
                assert rng == "debut-paragraphe"
                return FakeCursor(para)

            def insertString(self, rng, s, absorb):
                assert rng[0] == "pos" and absorb is False
                para.text = para.text[:rng[1]] + s + para.text[rng[1]:]

        return _Text()


class FakeEnum:
    def __init__(self, items):
        self.items = list(items)

    def hasMoreElements(self):
        return bool(self.items)

    def nextElement(self):
        return self.items.pop(0)


class FakeText:
    def __init__(self, items):
        self.items = items

    def createEnumeration(self):
        return FakeEnum(self.items)


class FakeTable:
    def __init__(self, cells):
        self.cells = cells

    def supportsService(self, name):
        return name == "com.sun.star.text.TextTable"

    def getCellNames(self):
        return list(self.cells)

    def getCellByName(self, n):
        return FakeText([self.cells[n]])


class FakeController:
    def __init__(self):
        self.selected = None

    def select(self, cur):
        self.selected = (cur.start, cur.end)


class AdapterTests(unittest.TestCase):
    def test_collects_paragraphs_including_tables(self):
        doc = FakeText([FakePara("a"), FakeTable({"A1": FakePara("b"), "B1": FakePara("c")}), FakePara("d")])
        ad = ud.WriterAdapter.whole_document(type("D", (), {"getText": lambda s: doc})())
        self.assertEqual([ad.paragraph_text(i) for i in range(ad.paragraph_count())], ["a", "b", "c", "d"])

    def test_replace_and_select(self):
        ctl = FakeController()
        ad = ud.WriterAdapter([FakePara("Je vois les chat.")], ctl)
        ad.select(0, 8, 8)
        self.assertEqual(ctl.selected, (8, 16))
        ad.replace(0, 8, 8, "les chats")
        self.assertEqual(ad.paragraph_text(0), "Je vois les chats.")

    def test_positions_with_emoji_use_code_points_for_cursor(self):
        ad = ud.WriterAdapter([FakePara("😀 les chat")])
        # positions UTF-16 : l'emoji vaut 2 unités -> « les chat » commence à 3
        ad.replace(0, 3, 8, "les chats")
        self.assertEqual(ad.paragraph_text(0), "😀 les chats")

    def test_long_move_is_chunked(self):
        text = "x" * 40000 + " les chat"
        ad = ud.WriterAdapter([FakePara(text)])
        ad.replace(0, 40001, 8, "les chats")
        self.assertTrue(ad.paragraph_text(0).endswith("les chats"))

    def test_language_detection_and_fallback(self):
        ad = ud.WriterAdapter([FakePara("a", FakeLocale("fr", "CA")), FakePara("b", FakeLocale("", ""))])
        self.assertEqual(ad.paragraph_language(0), "fr-CA")
        self.assertEqual(ad.paragraph_language(1), "fr-FR")

    def test_selection_ranges_are_units_not_whole_paragraphs(self):
        class Sel:
            def supportsService(self, n):
                return n == "com.sun.star.text.TextRanges"

            def getCount(self):
                return 2

            def getByIndex(self, i):
                return FakePara("sel%d" % i)

        ctl = type("C", (), {"getSelection": lambda s: Sel()})()
        ad = ud.WriterAdapter.selection(ctl)
        self.assertEqual([ad.paragraph_text(i) for i in range(2)], ["sel0", "sel1"])

    def test_empty_selection(self):
        class Sel:
            def supportsService(self, n):
                return n == "com.sun.star.text.TextRanges"

            def getCount(self):
                return 1

            def getByIndex(self, i):
                return FakePara("")

        ctl = type("C", (), {"getSelection": lambda s: Sel()})()
        self.assertEqual(ud.WriterAdapter.selection(ctl).paragraph_count(), 0)

    def test_no_selection_object(self):
        ctl = type("C", (), {"getSelection": lambda s: None})()
        self.assertEqual(ud.WriterAdapter.selection(ctl).paragraph_count(), 0)


if __name__ == "__main__":
    unittest.main()
