import tempfile
import unittest

from tests import helpers
from tests import fake_languagetool
from dysbuntu_correcteur.review import DocumentAdapter, ReviewSession
from dysbuntu_correcteur.textutil import utf16_to_index


class FakeDoc(DocumentAdapter):
    def __init__(self, paragraphs, lang="fr-FR"):
        self.paras = list(paragraphs)
        self.lang = lang
        self.selected = None

    def paragraph_count(self):
        return len(self.paras)

    def paragraph_text(self, i):
        return self.paras[i]

    def paragraph_language(self, i):
        return self.lang

    def replace(self, i, start, length, new):
        t = self.paras[i]
        a = utf16_to_index(t, start)
        b = utf16_to_index(t, start + length)
        self.paras[i] = t[:a] + new + t[b:]

    def select(self, i, start, length):
        self.selected = (i, start, length)


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.port = fake_languagetool.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p, self.store = helpers.make_proofreader(self.port, self.tmp.name)

    def test_apply_corrects_and_moves_on(self):
        doc = FakeDoc(["Je vois les chat.", "Rien ici.", "bonjours à tous"])
        s = ReviewSession(self.p, doc)
        item = s.start()
        self.assertEqual((item.paragraph, item.error_text), (0, "les chat"))
        self.assertEqual(doc.selected, (0, 8, 8))
        item = s.apply(0)
        self.assertEqual(doc.paras[0], "Je vois les chats.")
        self.assertEqual((item.paragraph, item.error_text), (2, "bonjours"))
        self.assertIsNone(s.apply(0))
        self.assertEqual(doc.paras[2], "bonjour à tous")
        self.assertEqual((s.applied, s.finished), (2, True))

    def test_nothing_changes_without_apply(self):
        doc = FakeDoc(["les chat", "bonjours"])
        s = ReviewSession(self.p, doc)
        s.start()
        s.ignore()
        s.ignore()
        self.assertEqual(doc.paras, ["les chat", "bonjours"])
        self.assertEqual((s.ignored, s.applied), (2, 0))

    def test_ignore_same_error_text_everywhere_in_session(self):
        doc = FakeDoc(["les chat", "encore les chat"])
        s = ReviewSession(self.p, doc)
        s.start()
        self.assertIsNone(s.ignore())  # le second « les chat » est aussi ignoré

    def test_ignore_rule_is_persistent(self):
        doc = FakeDoc(["les chat", "bonjours"])
        s = ReviewSession(self.p, doc)
        s.start()
        item = s.ignore_rule()
        self.assertEqual(item.error_text, "bonjours")
        self.assertIn("FAKE_ACCORD_PLURIEL", self.store.get()["ignored_rules"])

    def test_several_errors_in_one_paragraph(self):
        doc = FakeDoc(["les chat et bonjours"])
        s = ReviewSession(self.p, doc)
        s.start()
        item = s.apply(0)
        self.assertEqual(item.error_text, "bonjours")
        s.apply(0)
        self.assertEqual(doc.paras[0], "les chats et bonjour")

    def test_correction_with_emoji_before_error(self):
        doc = FakeDoc(["😀 les chat"])
        s = ReviewSession(self.p, doc)
        item = s.start()
        self.assertEqual(item.error_text, "les chat")
        s.apply(0)
        self.assertEqual(doc.paras[0], "😀 les chats")

    def test_server_down_is_reported(self):
        p, _ = helpers.make_proofreader(helpers.closed_port(), self.tmp.name)
        s = ReviewSession(p, FakeDoc(["les chat"]))
        self.assertIsNone(s.start())
        self.assertTrue(s.server_problem)

    def test_non_french_paragraphs_skipped_and_counted(self):
        s = ReviewSession(self.p, FakeDoc(["les chat", "bonjours"], lang="en-US"))
        self.assertIsNone(s.start())
        self.assertEqual(s.skipped_language, 2)

    def test_force_language_checks_everything_as_french(self):
        s = ReviewSession(self.p, FakeDoc(["les chat"], lang="en-US"), force_language="fr-FR")
        self.assertEqual(s.start().error_text, "les chat")
        self.assertEqual(s.skipped_language, 0)


if __name__ == "__main__":
    unittest.main()
