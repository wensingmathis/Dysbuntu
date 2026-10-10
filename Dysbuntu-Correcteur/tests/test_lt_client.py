import unittest

from tests import helpers  # noqa: F401
from tests import fake_languagetool
from dysbuntu_correcteur import lt_client
from dysbuntu_correcteur.config import ConfigError


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.port = fake_languagetool.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def client(self):
        return lt_client.LanguageToolClient("127.0.0.1", self.port, 3)

    def test_refuses_remote_host(self):
        for host in ("languagetool.org", "10.0.0.2", "api.languagetoolplus.com"):
            with self.assertRaises(ConfigError):
                lt_client.LanguageToolClient(host, 8081)

    def test_is_alive(self):
        self.assertTrue(self.client().is_alive())
        self.assertFalse(lt_client.LanguageToolClient("127.0.0.1", 1, 1).is_alive())

    def test_detects_errors(self):
        ms = self.client().check("Je vois les chat. Bonjours !", "fr-FR")
        ids = [m.rule_id for m in ms]
        self.assertIn("FAKE_ACCORD_PLURIEL", ids)
        self.assertIn("FAKE_MORFOLOGIK", ids)
        m = [m for m in ms if m.rule_id == "FAKE_ACCORD_PLURIEL"][0]
        self.assertEqual(m.replacements, ["les chats"])
        self.assertEqual((m.offset, m.length), (8, 8))

    def test_correct_text_yields_nothing(self):
        self.assertEqual(self.client().check("Les chats dorment dans le jardin.", "fr-FR"), [])

    def test_accents_survive_round_trip(self):
        ms = self.client().check("Élève étourdi : ca va ?", "fr-FR")
        self.assertEqual([m.replacements for m in ms if m.rule_id == "FAKE_CA"], [["ça"]])

    def test_disabled_rules_and_categories(self):
        ms = self.client().check("les chat", "fr", disabled_rules=["FAKE_ACCORD_PLURIEL"])
        self.assertEqual(ms, [])
        ms = self.client().check("bonjours", "fr", disabled_categories=["TYPOS"])
        self.assertEqual(ms, [])

    def test_language_code_mapping(self):
        self.assertEqual(lt_client.language_code("fr-FR"), "fr")
        self.assertEqual(lt_client.language_code("fr_CA"), "fr-CA")
        self.assertEqual(lt_client.language_code(""), "fr")

    def test_unknown_variant_falls_back_to_generic_french(self):
        # le faux serveur refuse « fr-CA » (HTTP 400) ; le client doit réessayer avec « fr »
        ms = self.client().check("bonjours", "fr-CA")
        self.assertEqual(len(ms), 1)

    def test_unavailable_server_raises(self):
        with self.assertRaises(lt_client.LanguageToolUnavailable):
            lt_client.LanguageToolClient("127.0.0.1", 1, 1).check("bonjours")

    def test_parse_rejects_garbage(self):
        with self.assertRaises(lt_client.LanguageToolError):
            lt_client.parse_matches({"pas": "de matches"})
        self.assertEqual(lt_client.parse_matches({"matches": [{"offset": "x"}]}), [])

    def test_proxy_env_is_ignored(self):
        import os
        os.environ["http_proxy"] = "http://127.0.0.1:9"
        try:
            self.assertTrue(self.client().is_alive())
        finally:
            del os.environ["http_proxy"]


if __name__ == "__main__":
    unittest.main()
