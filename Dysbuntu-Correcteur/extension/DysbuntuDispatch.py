# -*- coding: utf-8 -*-
"""Composants UNO : menu Dysbuntu (gestionnaire de protocole) et démarrage du serveur local."""
import os
import sys

import uno
import unohelper


def _ensure_pythonpath():
    try:
        ctx = uno.getComponentContext()
        pip = ctx.getByName("/singletons/com.sun.star.deployment.PackageInformationProvider")
        base = uno.fileUrlToSystemPath(pip.getPackageLocation("org.dysbuntu.correcteur"))
    except Exception:
        base = os.path.dirname(os.path.abspath(globals().get("__file__", ".")))
    path = os.path.join(base, "pythonpath")
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)


_ensure_pythonpath()

from com.sun.star.frame import XDispatch, XDispatchProvider  # noqa: E402
from com.sun.star.lang import XInitialization, XServiceInfo  # noqa: E402
from com.sun.star.task import XJob  # noqa: E402
from com.sun.star.frame import XTerminateListener  # noqa: E402

from dysbuntu_correcteur import ui  # noqa: E402
from dysbuntu_correcteur.config import effective_languagetool_dir  # noqa: E402
from dysbuntu_correcteur.core import get_core  # noqa: E402
from dysbuntu_correcteur.logutil import get_logger  # noqa: E402
from dysbuntu_correcteur.review import ReviewSession  # noqa: E402
from dysbuntu_correcteur.uno_document import WriterAdapter  # noqa: E402

PROTOCOL = "org.dysbuntu.correcteur:"
DISPATCH_IMPL = "org.dysbuntu.correcteur.Dispatch"
JOB_IMPL = "org.dysbuntu.correcteur.StartupJob"
TITLE = "Dysbuntu Correcteur"

log = get_logger("menu")


class DysbuntuDispatch(unohelper.Base, XServiceInfo, XDispatchProvider, XDispatch, XInitialization):
    def __init__(self, ctx):
        self.ctx = ctx
        self.frame = None
        self.core = get_core()

    # XInitialization
    def initialize(self, args):
        if args:
            self.frame = args[0]

    # XServiceInfo
    def getImplementationName(self):
        return DISPATCH_IMPL

    def supportsService(self, name):
        return name == "com.sun.star.frame.ProtocolHandler"

    def getSupportedServiceNames(self):
        return ("com.sun.star.frame.ProtocolHandler",)

    # XDispatchProvider
    def queryDispatch(self, url, target, flags):
        return self if url.Protocol == PROTOCOL else None

    def queryDispatches(self, requests):
        return tuple(self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags) for r in requests)

    # XDispatch
    def addStatusListener(self, listener, url):
        pass

    def removeStatusListener(self, listener, url):
        pass

    def dispatch(self, url, args):
        command = url.Path
        try:
            {
                "CheckSelection": self._check_selection,
                "CheckDocument": self._check_document,
                "StartServer": self._start_server,
                "Options": self._options,
                "ResetIgnored": self._reset_ignored,
                "About": self._about,
            }[command]()
        except KeyError:
            log.warning("Commande inconnue : %s", command)
        except Exception as exc:  # affichage clair plutôt qu'un plantage
            log.error("Commande %s : %s: %s", command, type(exc).__name__, exc)
            ui.message_box(self.ctx, self.frame, TITLE, "Une erreur est survenue : %s" % exc, error=True)

    # -- commandes -----------------------------------------------------------
    def _controller(self):
        return self.frame.getController() if self.frame is not None else None

    def _cfg(self):
        return self.core.store.get()

    def _ensure_server(self, cfg):
        """Vérifie que le serveur répond ; tente de le démarrer. Retourne True si prêt."""
        status = self.core.server.status(cfg)
        if status == "running":
            return True
        if status == "missing":
            ui.message_box(
                self.ctx, self.frame, TITLE,
                "LanguageTool n'est pas installé.\n\nDans un terminal, lancez :\n"
                "    scripts/install_languagetool.sh\n\n(dossier attendu : %s)" % effective_languagetool_dir(cfg),
                error=True,
            )
            return False
        self.core.server.start_async(cfg, force=True)
        if self.core.server.wait_ready(cfg, timeout=40):
            return True
        ui.message_box(
            self.ctx, self.frame, TITLE,
            "Le serveur LanguageTool n'a pas démarré. %s" % self.core.server.last_error, error=True
        )
        return False

    def _run_review(self, adapter):
        cfg = self._cfg()
        if adapter.paragraph_count() == 0:
            ui.message_box(self.ctx, self.frame, TITLE, "Aucun texte à vérifier.")
            return
        if not self._ensure_server(cfg):
            return
        force = "fr-FR" if cfg["review_force_french"] else None
        session = ReviewSession(self.core.proofreader, adapter, force_language=force)
        ui.run_review_dialog(self.ctx, self.frame, session, cfg)

    def _check_selection(self):
        ctrl = self._controller()
        adapter = WriterAdapter.selection(ctrl)
        if adapter.paragraph_count() == 0:
            ui.message_box(self.ctx, self.frame, TITLE, "Sélectionnez d'abord le texte à vérifier.")
            return
        self._run_review(adapter)

    def _check_document(self):
        ctrl = self._controller()
        self._run_review(WriterAdapter.whole_document(ctrl.getModel(), ctrl))

    def _start_server(self):
        cfg = self._cfg()
        if self._ensure_server(cfg):
            ui.message_box(self.ctx, self.frame, TITLE, "Le serveur de correction fonctionne (port %d, local)." % cfg["port"])

    def _options(self):
        cfg = self._cfg()
        new = ui.run_options_dialog(self.ctx, cfg)
        if new is not None:
            self.core.store.save(new)
            self.core.proofreader.clear_cache()
            ui.message_box(
                self.ctx, self.frame, TITLE,
                "Options enregistrées. Rouvrez le document (ou modifiez un paragraphe) pour relancer la vérification.",
            )

    def _reset_ignored(self):
        self.core.proofreader.reset_ignored_rules()
        ui.message_box(self.ctx, self.frame, TITLE, "Les règles ignorées sont de nouveau actives.")

    def _about(self):
        ui.message_box(self.ctx, self.frame, TITLE, ui.about_text())


class _Terminator(unohelper.Base, XTerminateListener):
    def queryTermination(self, ev):
        pass

    def notifyTermination(self, ev):
        get_core().server.stop_if_started_by_us()

    def disposing(self, ev):
        pass


class DysbuntuStartupJob(unohelper.Base, XServiceInfo, XJob):
    """Au premier affichage d'une fenêtre, lance le serveur local (si installé et autorisé)."""

    def __init__(self, ctx):
        self.ctx = ctx

    def getImplementationName(self):
        return JOB_IMPL

    def supportsService(self, name):
        return name == "com.sun.star.task.Job"

    def getSupportedServiceNames(self):
        return ("com.sun.star.task.Job",)

    def execute(self, args):
        try:
            core = get_core()
            cfg = core.store.get()
            if cfg["auto_start_server"]:
                core.server.start_async(cfg)
                desktop = self.ctx.getServiceManager().createInstanceWithContext(
                    "com.sun.star.frame.Desktop", self.ctx
                )
                desktop.addTerminateListener(_Terminator())
        except Exception as exc:
            log.error("StartupJob : %s: %s", type(exc).__name__, exc)
        return None


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(DysbuntuDispatch, DISPATCH_IMPL, ("com.sun.star.frame.ProtocolHandler",))
g_ImplementationHelper.addImplementation(DysbuntuStartupJob, JOB_IMPL, ("com.sun.star.task.Job",))
