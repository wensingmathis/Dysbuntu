import os
import stat
import sys
import tempfile
import unittest

from tests import helpers
from tests.helpers import ROOT
from dysbuntu_correcteur import server
from dysbuntu_correcteur.config import ConfigStore


class ServerManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp.name, "state")
        self.addCleanup(os.environ.pop, "XDG_STATE_HOME", None)

    def make_cfg(self, with_jar=True):
        lt = os.path.join(self.tmp.name, "lt", "LanguageTool-6.x")
        os.makedirs(lt)
        if with_jar:
            open(os.path.join(lt, "languagetool-server.jar"), "w").close()
        # « java » factice : lance le faux serveur sur le port demandé (--port N).
        fake_java = os.path.join(self.tmp.name, "fakejava")
        with open(fake_java, "w") as fh:
            fh.write('#!/bin/sh\nwhile [ "$1" != "--port" ]; do shift; done\n'
                     'exec %s %s --port "$2"\n' % (sys.executable, os.path.join(ROOT, "tests", "fake_languagetool.py")))
        os.chmod(fake_java, os.stat(fake_java).st_mode | stat.S_IEXEC)
        store = ConfigStore(os.path.join(self.tmp.name, "c.json"))
        return store.save(dict(store.get(), port=helpers.closed_port(), java_command=fake_java,
                               languagetool_dir=os.path.join(self.tmp.name, "lt")))

    def test_command_has_no_public_flag(self):
        cfg = self.make_cfg()
        cmd = server.build_command(cfg, "/x/languagetool-server.jar")
        self.assertNotIn("--public", cmd)
        self.assertIn("org.languagetool.server.HTTPServer", cmd)

    def test_missing_install_is_reported(self):
        cfg = self.make_cfg(with_jar=False)
        mgr = server.ServerManager()
        self.assertEqual(mgr.status(cfg), "missing")
        self.assertFalse(mgr.start_async(cfg, force=True))
        self.assertIn("pas installé", mgr.last_error)

    def test_start_wait_status_stop(self):
        cfg = self.make_cfg()
        mgr = server.ServerManager()
        self.assertEqual(mgr.status(cfg), "installed")
        self.assertTrue(mgr.start_async(cfg, force=True))
        try:
            self.assertTrue(mgr.wait_ready(cfg, timeout=15))
            self.assertEqual(mgr.status(cfg), "running")
            self.assertFalse(mgr.start_async(cfg, force=True))  # déjà en marche : pas de 2e lancement
        finally:
            mgr.stop_if_started_by_us()
        self.assertNotEqual(mgr.status(cfg), "running")

    def test_cooldown_prevents_repeated_launch_attempts(self):
        cfg = self.make_cfg(with_jar=False)
        mgr = server.ServerManager()
        mgr.start_async(cfg)
        self.assertFalse(mgr.start_async(cfg))  # dans le délai de grâce

    def test_bad_java_command_does_not_raise(self):
        cfg = self.make_cfg()
        cfg["java_command"] = "/nonexistent/java"
        mgr = server.ServerManager()
        self.assertFalse(mgr.start_async(cfg, force=True))
        self.assertIn("Java", mgr.last_error)


if __name__ == "__main__":
    unittest.main()
