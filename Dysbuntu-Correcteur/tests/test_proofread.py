import tempfile
import unittest

from tests import helpers
from tests import fake_languagetool


class ProofreaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.port = fake_languagetool.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def pr(self, **cfg):
        return helpers.make_proofreader(self.port, self.tmp.name, **cfg)

    def test_issue_fields(self):
        p, _ = self.pr()
        issues = p.check("Je vois les chat.", "fr-FR")
        self.assertEqual(len(issues), 1)
        i = issues[0]
        self.assertEqual((i.offset, i.length, i.category), (8, 8, "grammaire"))
        self.assertEqual(i.suggestions, ["les chats"])
        self.assertIn("Grammaire", i.short_comment)
        self.assertIn("Essayez", i.full_comment)
        self.assertEqual(p.last_status, "ok")

    def test_correct_text_not_modified_or_flagged(self):
        p, _ = self.pr()
        self.assertEqual(p.check("Les élèves écoutent attentivement la maîtresse.", "fr-FR"), [])

    def test_non_french_ignored(self):
        p, _ = self.pr()
        self.assertEqual(p.check("les chat", "en-US"), [])

    def test_categories_can_be_disabled(self):
        p, store = self.pr()
        text = "Bonjours les chat ,"
        self.assertEqual({i.category for i in p.check(text, "fr-FR")}, {"orthographe", "grammaire", "ponctuation"})
        cats = store.get()["categories"]
        cats["orthographe"] = False
        store.update(categories=cats)
        self.assertNotIn("orthographe", {i.category for i in p.check(text, "fr-FR")})

    def test_ignore_rule_persists(self):
        p, store = self.pr()
        self.assertEqual(len(p.check("les chat", "fr-FR")), 1)
        p.ignore_rule("FAKE_ACCORD_PLURIEL")
        self.assertEqual(p.check("les chat", "fr-FR"), [])
        self.assertIn("FAKE_ACCORD_PLURIEL", store.get()["ignored_rules"])
        p.reset_ignored_rules()
        self.assertEqual(len(p.check("les chat", "fr-FR")), 1)

    def test_cache_avoids_second_request(self):
        p, _ = self.pr()
        p.check("les chat", "fr-FR")
        before = fake_languagetool.Handler.requests_seen
        p.check("les chat", "fr-FR")
        self.assertEqual(fake_languagetool.Handler.requests_seen, before)

    def test_unavailable_server_returns_empty_and_never_raises(self):
        p, _ = helpers.make_proofreader(helpers.closed_port(), self.tmp.name)
        self.assertEqual(p.check("les chat", "fr-FR"), [])
        self.assertEqual(p.last_status, "indisponible")

    def test_long_text_offsets_are_global(self):
        p, _ = self.pr(max_chunk_chars=1000)
        text = ("Il fait beau aujourd'hui. " * 100) + "les chat mangent."
        issues = p.check(text, "fr-FR")
        self.assertEqual(len(issues), 1)
        self.assertEqual(text[issues[0].offset:issues[0].offset + issues[0].length], "les chat")

    def test_multi_paragraph_text(self):
        p, _ = self.pr()
        text = "Premier paragraphe correct.\nDeuxième avec les chat.\nTroisième : bonjours"
        found = {text[i.offset:i.offset + i.length] for i in p.check(text, "fr-FR")}
        self.assertEqual(found, {"les chat", "bonjours"})

    def test_max_suggestions(self):
        p, _ = self.pr(max_suggestions=1)
        self.assertLessEqual(len(p.check("les chat", "fr-FR")[0].suggestions), 1)


if __name__ == "__main__":
    unittest.main()
