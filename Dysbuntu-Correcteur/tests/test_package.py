"""Vérifie le paquet .oxt et les garanties de confidentialité du code source."""
import os
import re
import sys
import tempfile
import unittest
import xml.dom.minidom
import zipfile

from tests import helpers
from tests.helpers import ROOT


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ROOT)
        import build
        cls.build = build
        cls.oxt = build.build()
        cls.zf = zipfile.ZipFile(cls.oxt)

    def test_manifest_entries_exist_in_archive(self):
        names = set(self.zf.namelist())
        doc = xml.dom.minidom.parseString(self.zf.read("META-INF/manifest.xml"))
        entries = [e.getAttribute("manifest:full-path") for e in doc.getElementsByTagName("manifest:file-entry")]
        self.assertGreaterEqual(len(entries), 6)
        for e in entries:
            self.assertIn(e, names)

    def test_identifier_and_version(self):
        doc = xml.dom.minidom.parseString(self.zf.read("description.xml"))
        self.assertEqual(doc.getElementsByTagName("identifier")[0].getAttribute("value"), "org.dysbuntu.correcteur")
        from dysbuntu_correcteur import __version__
        self.assertEqual(doc.getElementsByTagName("version")[0].getAttribute("value"), __version__)

    def test_no_bytecode_or_tests_in_package(self):
        for n in self.zf.namelist():
            self.assertFalse(n.endswith(".pyc") or "__pycache__" in n or n.startswith("tests/"))

    def test_registered_implementation_names_match_xcu(self):
        names = {
            "Linguistic.xcu": "org.dysbuntu.correcteur.Proofreader",
            "ProtocolHandler.xcu": "org.dysbuntu.correcteur.Dispatch",
            "Jobs.xcu": "org.dysbuntu.correcteur.StartupJob",
        }
        src = {"DysbuntuProofreader.py": "org.dysbuntu.correcteur.Proofreader",
               "DysbuntuDispatch.py": "org.dysbuntu.correcteur.Dispatch"}
        for xcu, impl in names.items():
            self.assertIn(impl, self.zf.read("registry/" + xcu).decode())
        for py, impl in src.items():
            self.assertIn(impl, self.zf.read(py).decode())


class PrivacyTests(unittest.TestCase):
    """Le code de l'extension ne doit contenir aucune adresse Internet ni outil de télémétrie."""

    def python_sources(self):
        base = os.path.join(ROOT, "extension")
        for d, _, files in os.walk(base):
            for f in files:
                if f.endswith(".py"):
                    yield os.path.join(d, f)

    def test_no_remote_urls_in_code(self):
        url = re.compile(r"https?://([^\s\"'/)]+)")
        allowed = {"127.0.0.1", "localhost", "[::1]", "%s:%d", "[%s]"}
        for path in self.python_sources():
            with open(path, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    for host in url.findall(line):
                        self.assertIn(host, allowed, "%s:%d contient une URL distante" % (path, n))

    def test_no_telemetry_libraries(self):
        bad = re.compile(r"(^|\n)\s*(import|from)\s+(requests|sentry_sdk|sentry|ftplib|smtplib|socket|telnetlib)\b|telemetry|analytics")
        for path in self.python_sources():
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            text = re.sub(r'""".*?"""', "", text, flags=re.S)  # docstrings
            text = re.sub(r"#.*", "", text)
            self.assertIsNone(bad.search(text), path)

    def test_logs_never_receive_document_text(self):
        # Les appels de journal ne doivent jamais recevoir de variable « text ».
        call = re.compile(r"log\.\w+\(([^)]*)\)")
        for path in self.python_sources():
            with open(path, encoding="utf-8") as fh:
                for m in call.finditer(fh.read()):
                    self.assertNotRegex(m.group(1), r"\b(text|chunk|paragraph_text)\b", path)


if __name__ == "__main__":
    unittest.main()
