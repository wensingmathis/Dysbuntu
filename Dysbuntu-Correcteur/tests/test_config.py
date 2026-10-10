import json
import os
import tempfile
import unittest

from tests import helpers  # noqa: F401
from dysbuntu_correcteur import config


class ConfigTests(unittest.TestCase):
    def test_defaults_are_valid_and_local(self):
        cfg = config.validate({})
        self.assertEqual(cfg["host"], "127.0.0.1")
        self.assertTrue(cfg["categories"]["orthographe"])
        self.assertFalse(cfg["categories"]["style"])

    def test_remote_host_is_refused(self):
        for host in ("example.com", "192.168.1.5", "0.0.0.0", "languagetool.org"):
            with self.assertRaises(config.ConfigError):
                config.validate({"host": host})

    def test_bad_port_refused(self):
        with self.assertRaises(config.ConfigError):
            config.validate({"port": 80})
        with self.assertRaises(config.ConfigError):
            config.validate({"port": "abc"})

    def test_roundtrip_and_ignored_rules(self):
        with tempfile.TemporaryDirectory() as d:
            store = config.ConfigStore(os.path.join(d, "c.json"))
            store.add_ignored_rule("R1")
            store.add_ignored_rule("R1")
            store.update(font_size=18)
            fresh = config.ConfigStore(os.path.join(d, "c.json")).get()
            self.assertEqual(fresh["ignored_rules"], ["R1"])
            self.assertEqual(fresh["font_size"], 18)
            store.reset_ignored_rules()
            self.assertEqual(store.get()["ignored_rules"], [])

    def test_corrupted_file_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.json")
            with open(p, "w") as fh:
                fh.write("{pas du json")
            self.assertEqual(config.ConfigStore(p).get()["port"], 8081)

    def test_file_with_remote_host_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.json")
            with open(p, "w") as fh:
                json.dump({"host": "evil.example.com", "port": 8081}, fh)
            self.assertEqual(config.ConfigStore(p).get()["host"], "127.0.0.1")

    def test_font_size_clamped(self):
        self.assertEqual(config.validate({"font_size": 500})["font_size"], 32)
        self.assertEqual(config.validate({"font_size": 1})["font_size"], 9)


if __name__ == "__main__":
    unittest.main()
