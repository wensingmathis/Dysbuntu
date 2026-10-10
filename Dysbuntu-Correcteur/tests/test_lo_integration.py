"""Test d'intégration dans un VRAI LibreOffice (mode headless).

Ce test installe le .oxt dans un profil temporaire, démarre LibreOffice avec un
faux serveur LanguageTool, puis utilise l'API UNO réelle. Il est ignoré
automatiquement si LibreOffice, unopkg ou le module Python « uno » manquent.
"""
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

from tests import helpers  # noqa: F401  (configure sys.path)
from tests import fake_languagetool

try:
    import uno  # type: ignore
    from com.sun.star.beans import PropertyValue  # type: ignore
    from com.sun.star.lang import Locale  # type: ignore
    HAVE_UNO = True
except Exception:  # pragma: no cover
    HAVE_UNO = False

HAVE_LO = bool(shutil.which("soffice") and shutil.which("unopkg")) and HAVE_UNO


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def prop(name, value):
    p = PropertyValue()
    p.Name, p.Value = name, value
    return p


@unittest.skipUnless(HAVE_LO, "LibreOffice / unopkg / python-uno indisponibles")
class LibreOfficeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build
        cls.tmp = tempfile.mkdtemp(prefix="dysbuntu-lo-")
        os.chmod(cls.tmp, 0o777)
        cls.fake, cls.lt_port = fake_languagetool.start()
        cfgdir = os.path.join(cls.tmp, "cfg", "dysbuntu-correcteur")
        os.makedirs(cfgdir)
        with open(os.path.join(cfgdir, "config.json"), "w") as fh:
            fh.write('{"port": %d, "auto_start_server": false}' % cls.lt_port)
        for d in ("state", "data", "home"):
            os.makedirs(os.path.join(cls.tmp, d))
        oxt = os.path.join(cls.tmp, "ext.oxt")
        shutil.copy(build.build(), oxt)
        for dirpath, dirs, files in os.walk(cls.tmp):
            os.chmod(dirpath, 0o777)
            for f in files:
                os.chmod(os.path.join(dirpath, f), 0o666)

        env = {
            "HOME": os.path.join(cls.tmp, "home"),
            "XDG_CONFIG_HOME": os.path.join(cls.tmp, "cfg"),
            "XDG_STATE_HOME": os.path.join(cls.tmp, "state"),
            "XDG_DATA_HOME": os.path.join(cls.tmp, "data"),
        }
        prefix = []
        if os.geteuid() == 0:  # unopkg refuse de tourner en root
            prefix = ["runuser", "-u", "nobody", "--", "env"] + ["%s=%s" % kv for kv in env.items()]
            cls.run_env = None
        else:
            cls.run_env = dict(os.environ, **env)
        profile = "-env:UserInstallation=file://" + os.path.join(cls.tmp, "profile")
        r = subprocess.run(prefix + ["unopkg", "add", "--suppress-license", profile, oxt],
                           env=cls.run_env, capture_output=True, text=True, timeout=180)
        out = r.stdout + r.stderr
        if r.returncode != 0 or "ERROR" in out:
            raise RuntimeError("unopkg add a échoué : " + out)
        r = subprocess.run(prefix + ["unopkg", "list", profile],
                           env=cls.run_env, capture_output=True, text=True, timeout=120)
        cls.install_out = r.stdout + r.stderr

        cls.lo_port = free_port()
        cls.log_path = os.path.join(cls.tmp, "soffice.log")
        cls.logfh = open(cls.log_path, "w")
        os.chmod(cls.log_path, 0o666)
        cls.proc = subprocess.Popen(
            prefix + ["soffice", "--headless", "--invisible", "--norestore", "--nologo", profile,
                      "--accept=socket,host=127.0.0.1,port=%d;urp;" % cls.lo_port],
            env=cls.run_env, stdout=cls.logfh, stderr=subprocess.STDOUT, start_new_session=True)
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        cls.ctx = None
        for _ in range(120):
            try:
                cls.ctx = resolver.resolve(
                    "uno:socket,host=127.0.0.1,port=%d;urp;StarOffice.ComponentContext" % cls.lo_port)
                break
            except Exception:
                time.sleep(0.5)
        if cls.ctx is None:
            raise RuntimeError("LibreOffice n'a pas démarré")
        cls.smgr = cls.ctx.ServiceManager
        cls.desktop = cls.smgr.createInstanceWithContext("com.sun.star.frame.Desktop", cls.ctx)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.desktop.terminate()
        except Exception:
            pass
        try:
            cls.proc.wait(timeout=15)
        except Exception:
            cls.proc.kill()
        cls.logfh.close()
        cls.fake.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def new_doc(self):
        doc = self.desktop.loadComponentFromURL("private:factory/swriter", "_blank", 0, (prop("Hidden", True),))
        self.addCleanup(doc.close, True)
        return doc

    # ------------------------------------------------------------------
    def test_01_extension_listed(self):
        self.assertIn("org.dysbuntu.correcteur", self.install_out)

    def test_02_grammar_checker_registered_for_french(self):
        lingu = self.smgr.createInstanceWithContext("com.sun.star.linguistic2.LinguServiceManager", self.ctx)
        impls = lingu.getAvailableServices("com.sun.star.linguistic2.Proofreader", Locale("fr", "FR", ""))
        self.assertIn("org.dysbuntu.correcteur.Proofreader", impls)
        impls_en = lingu.getAvailableServices("com.sun.star.linguistic2.Proofreader", Locale("en", "US", ""))
        self.assertNotIn("org.dysbuntu.correcteur.Proofreader", impls_en)

    def test_03_do_proofreading_real_component(self):
        pr = self.smgr.createInstanceWithContext("org.dysbuntu.correcteur.Proofreader", self.ctx)
        self.assertTrue(pr.hasLocale(Locale("fr", "FR", "")))
        self.assertFalse(pr.hasLocale(Locale("en", "US", "")))
        text = "Je vois les chat. Bonjours !"
        res = pr.doProofreading("doc-1", text, Locale("fr", "FR", ""), 0, len(text), ())
        self.assertEqual(res.nBehindEndOfSentencePosition, len(text))
        errs = {text[e.nErrorStart:e.nErrorStart + e.nErrorLength]: e for e in res.aErrors}
        self.assertEqual(set(errs), {"les chat", "Bonjours"})
        e = errs["les chat"]
        self.assertEqual(tuple(e.aSuggestions), ("les chats",))
        self.assertEqual(e.nErrorType, 2)  # TextMarkupType.PROOFREADING
        self.assertTrue(e.aShortComment and e.aFullComment)
        self.assertEqual(e.aProperties[0].Name, "LineColor")
        self.assertNotEqual(errs["Bonjours"].aProperties[0].Value, e.aProperties[0].Value)

    def test_04_correct_text_has_no_errors(self):
        pr = self.smgr.createInstanceWithContext("org.dysbuntu.correcteur.Proofreader", self.ctx)
        text = "Les élèves écoutent attentivement la maîtresse."
        res = pr.doProofreading("doc-2", text, Locale("fr", "FR", ""), 0, len(text), ())
        self.assertEqual(len(res.aErrors), 0)

    def test_05_menu_registered_in_writer(self):
        provider = self.smgr.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", self.ctx)
        node = provider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess",
            (prop("nodepath", "/org.openoffice.Office.Addons/AddonUI/OfficeMenuBar"),))
        self.assertTrue(node.hasByName("org.dysbuntu.correcteur"))
        sub = node.getByName("org.dysbuntu.correcteur").getByName("Submenu")
        self.assertEqual(len(sub.getElementNames()), 6)

    def test_06_protocol_handler_answers(self):
        doc = self.new_doc()
        frame = doc.getCurrentController().getFrame()
        transformer = self.smgr.createInstanceWithContext("com.sun.star.util.URLTransformer", self.ctx)
        for command in ("CheckSelection", "CheckDocument", "StartServer", "Options", "ResetIgnored", "About"):
            url = uno.createUnoStruct("com.sun.star.util.URL")
            url.Complete = "org.dysbuntu.correcteur:" + command
            _, url = transformer.parseStrict(url)
            self.assertIsNotNone(frame.queryDispatch(url, "", 0), command)

    def test_07_review_session_on_real_writer_document(self):
        from dysbuntu_correcteur.config import ConfigStore
        from dysbuntu_correcteur.proofread import Proofreader
        from dysbuntu_correcteur.review import ReviewSession
        from dysbuntu_correcteur.uno_document import WriterAdapter

        store = ConfigStore(os.path.join(self.tmp, "review-config.json"))
        store.update(port=self.lt_port, auto_start_server=False)
        doc = self.new_doc()
        text = doc.getText()
        cur = text.createTextCursor()
        pbreak = uno.getConstantByName("com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK")
        text.insertString(cur, "Je vois les chat.", False)
        text.insertControlCharacter(cur, pbreak, False)
        text.insertString(cur, "Ce paragraphe est correct.", False)
        text.insertControlCharacter(cur, pbreak, False)
        text.insertString(cur, "Il dit bonjours \U0001F600 à tous.", False)
        table = doc.createInstance("com.sun.star.text.TextTable")
        table.initialize(1, 1)
        text.insertTextContent(text.getEnd(), table, False)
        table.getCellByName("A1").setString("Je suis aller au marché.")

        ctrl = doc.getCurrentController()
        adapter = WriterAdapter.whole_document(doc, ctrl)
        self.assertGreaterEqual(adapter.paragraph_count(), 4)
        session = ReviewSession(Proofreader(store), adapter, force_language="fr-FR")
        item = session.start()
        self.assertEqual(item.error_text, "les chat")
        sel = ctrl.getSelection().getByIndex(0).getString()
        self.assertEqual(sel, "les chat")  # la sélection visuelle est bien posée dans Writer
        item = session.apply(0)
        self.assertEqual(item.error_text, "bonjours")
        item = session.apply(0)  # le paragraphe contient un emoji (UTF-16 !)
        self.assertEqual(item.error_text, "Je suis aller")
        self.assertIsNone(session.apply(0))
        content = doc.getText().getString()
        self.assertIn("Je vois les chats.", content)
        self.assertIn("Il dit bonjour \U0001F600 à tous.", content)
        self.assertEqual(table.getCellByName("A1").getString(), "Je suis allé au marché.")
        self.assertEqual(session.applied, 3)

    def test_08_selection_only(self):
        from dysbuntu_correcteur.config import ConfigStore
        from dysbuntu_correcteur.proofread import Proofreader
        from dysbuntu_correcteur.review import ReviewSession
        from dysbuntu_correcteur.uno_document import WriterAdapter

        store = ConfigStore(os.path.join(self.tmp, "sel-config.json"))
        store.update(port=self.lt_port, auto_start_server=False)
        doc = self.new_doc()
        text = doc.getText()
        text.setString("les chat dorment. bonjours à tous.")
        ctrl = doc.getCurrentController()
        cur = text.createTextCursor()
        cur.gotoStart(False)
        cur.goRight(8, True)  # sélectionne « les chat »
        ctrl.select(cur)
        adapter = WriterAdapter.selection(ctrl)
        self.assertEqual(adapter.paragraph_count(), 1)
        session = ReviewSession(Proofreader(store), adapter, force_language="fr-FR")
        item = session.start()
        self.assertEqual(item.error_text, "les chat")
        self.assertIsNone(session.apply(0))  # « bonjours » est hors sélection : pas proposé
        self.assertEqual(doc.getText().getString(), "les chats dorment. bonjours à tous.")

    def test_08b_selection_across_paragraphs(self):
        from dysbuntu_correcteur.config import ConfigStore
        from dysbuntu_correcteur.proofread import Proofreader
        from dysbuntu_correcteur.review import ReviewSession
        from dysbuntu_correcteur.uno_document import WriterAdapter

        store = ConfigStore(os.path.join(self.tmp, "sel2-config.json"))
        store.update(port=self.lt_port, auto_start_server=False)
        doc = self.new_doc()
        text = doc.getText()
        pbreak = uno.getConstantByName("com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK")
        cur = text.createTextCursor()
        text.insertString(cur, "les chat avant.", False)
        text.insertControlCharacter(cur, pbreak, False)
        text.insertString(cur, "Ici les chat et bonjours.", False)
        text.insertControlCharacter(cur, pbreak, False)
        text.insertString(cur, "après bonjours.", False)
        ctrl = doc.getCurrentController()
        c2 = text.createTextCursor()
        c2.gotoStart(False)
        c2.goRight(len("les chat avant.") + 1 + 4, False)  # début de « les chat » du 2e paragraphe
        c2.goRight(len("les chat et bonjours.") + 1 + 5, True)  # jusqu'à la fin du 3e paragraphe ("après")
        ctrl.select(c2)
        adapter = WriterAdapter.selection(ctrl)
        session = ReviewSession(Proofreader(store), adapter, force_language="fr-FR")
        item = session.start()
        self.assertEqual(item.error_text, "les chat")
        item = session.apply(0)
        self.assertEqual(item.error_text, "bonjours")
        self.assertIsNone(session.apply(0))
        self.assertEqual(
            doc.getText().getString().replace("\r", ""),
            "les chat avant.\nIci les chats et bonjour.\naprès bonjours.",
        )

    def test_08c_dialogs_build_in_real_office(self):
        """Construit (sans les afficher) les fenêtres réelles et vérifie leur contenu."""
        from dysbuntu_correcteur import ui
        from dysbuntu_correcteur.config import ConfigStore, CATEGORY_KEYS
        from dysbuntu_correcteur.proofread import Proofreader
        from dysbuntu_correcteur.review import ReviewSession
        from dysbuntu_correcteur.uno_document import WriterAdapter

        store = ConfigStore(os.path.join(self.tmp, "ui-config.json"))
        store.update(port=self.lt_port, auto_start_server=False, font_size=16)
        cfg = store.get()
        opt = ui.build_options_dialog(self.ctx, cfg)
        opt.create_peer()
        for k in CATEGORY_KEYS:
            self.assertTrue(opt.model.hasByName("cat_" + k))
        self.assertEqual(int(opt.model.getByName("font_size").getPropertyValue("Value")), 16)
        opt.dialog.dispose()

        doc = self.new_doc()
        doc.getText().setString("Je vois les chat. Bonjours.")
        session = ReviewSession(Proofreader(store), WriterAdapter.whole_document(doc, doc.getCurrentController()),
                                force_language="fr-FR")
        b, show = ui.build_review_dialog(self.ctx, session, cfg)
        b.create_peer()
        show(session.start())
        m = b.model.getByName
        self.assertEqual(m("lbl_category").getPropertyValue("Label"), "Grammaire et accords")
        self.assertIn("« les chat »", m("lbl_context").getPropertyValue("Label"))
        self.assertEqual(m("sug0").getPropertyValue("Label"), "les chats")
        self.assertFalse(b.dialog.getControl("sug1").isVisible())
        show(session.ignore())
        self.assertEqual(m("lbl_category").getPropertyValue("Label"), "Orthographe")
        show(session.ignore())
        self.assertEqual(m("lbl_category").getPropertyValue("Label"), "Vérification terminée")
        self.assertIn("0 correction(s)", m("lbl_explain").getPropertyValue("Label"))
        b.dialog.dispose()

    def test_09_no_python_errors_in_office_log(self):
        self.logfh.flush()
        with open(self.log_path, errors="replace") as fh:
            log = fh.read()
        self.assertNotIn("Traceback", log)


if __name__ == "__main__":
    unittest.main()
