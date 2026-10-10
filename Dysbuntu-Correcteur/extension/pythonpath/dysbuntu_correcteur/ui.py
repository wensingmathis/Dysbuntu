"""Fenêtres de l'extension (boîtes de dialogue UNO construites par programme).

Ce module ne dépend d'UNO qu'à l'exécution : les imports ``com.sun.star`` sont faits
dans les fonctions, ce qui permet d'importer le module hors de LibreOffice.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import __version__
from .categories import CATEGORIES
from .config import CATEGORY_KEYS
from .review import ReviewItem, ReviewSession

PUSH_OK = 1
PUSH_CANCEL = 2


class DialogBuilder:
    """Petit utilitaire pour construire une boîte de dialogue UNO (unités AppFont)."""

    def __init__(self, ctx: Any, title: str, width: int, height: int, font_size: int):
        smgr = ctx.getServiceManager()
        self.ctx = ctx
        self.smgr = smgr
        self.scale = max(1.0, font_size / 11.0)
        self.font_size = float(font_size)
        self.model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
        self._set(self.model, Title=title, Width=int(width * self.scale), Height=int(height * self.scale))
        self.dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
        self.dialog.setModel(self.model)
        self.width = int(width * self.scale)

    @staticmethod
    def _set(obj: Any, **props: Any) -> None:
        for name, value in props.items():
            obj.setPropertyValue(name, value)

    def add(self, kind: str, name: str, x: int, y: int, w: int, h: int, **props: Any) -> Any:
        m = self.model.createInstance("com.sun.star.awt.UnoControl%sModel" % kind)
        s = self.scale
        self._set(m, Name=name, PositionX=int(x * s), PositionY=int(y * s), Width=int(w * s), Height=int(h * s))
        if kind in ("FixedText", "Button", "CheckBox", "NumericField"):
            try:
                self._set(m, FontHeight=self.font_size)
            except Exception:
                pass  # taille de police non applicable : on garde celle du système
        self._set(m, **props)
        self.model.insertByName(name, m)
        return m

    def create_peer(self) -> None:
        toolkit = self.smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        self.dialog.setVisible(False)
        self.dialog.createPeer(toolkit, None)


def message_box(ctx: Any, frame: Any, title: str, text: str, error: bool = False) -> None:
    from com.sun.star.awt.MessageBoxType import ERRORBOX, INFOBOX  # type: ignore

    smgr = ctx.getServiceManager()
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    parent = frame.getContainerWindow() if frame is not None else None
    box = toolkit.createMessageBox(parent, ERRORBOX if error else INFOBOX, 1, title, text)
    box.execute()


def about_text() -> str:
    return (
        "Dysbuntu Correcteur %s\n\n"
        "Correcteur orthographique et grammatical pour LibreOffice Writer, "
        "pensé pour les personnes dyslexiques, dysgraphiques et dysorthographiques.\n\n"
        "Fonctionne hors ligne avec un serveur LanguageTool local. "
        "Aucun texte n'est envoyé sur Internet, aucune donnée n'est collectée.\n\n"
        "Cet outil aide à relire, mais ne remplace ni une relecture attentive "
        "ni un accompagnement pédagogique ou médical."
    ) % __version__


# --------------------------------------------------------------------------
# Revue guidée
# --------------------------------------------------------------------------
def build_review_dialog(ctx: Any, session: ReviewSession, cfg: Dict[str, Any]):
    """Construit la fenêtre de revue. Retourne (constructeur, fonction show(item))."""
    import unohelper  # type: ignore
    from com.sun.star.awt import XActionListener  # type: ignore

    b = DialogBuilder(ctx, "Dysbuntu Correcteur", 270, 178, cfg["font_size"])
    W = 262
    b.add("FixedText", "lbl_progress", 4, 4, W, 10)
    b.add("FixedText", "lbl_category", 4, 16, W, 11, FontWeight=150.0)
    b.add("FixedText", "lbl_context", 4, 30, W, 34, MultiLine=True)
    b.add("FixedText", "lbl_explain", 4, 68, W, 42, MultiLine=True)
    for i in range(3):
        b.add("Button", "sug%d" % i, 4 + i * 88, 114, 84, 14)
    b.add("Button", "btn_ignore", 4, 134, 84, 14, Label="Ignorer")
    b.add("Button", "btn_ignore_rule", 92, 134, 128, 14, Label="Toujours ignorer cette règle")
    b.add("Button", "btn_close", 4, 156, 84, 14, Label="Fermer", PushButtonType=PUSH_CANCEL)

    def ctl(name: str) -> Any:
        return b.dialog.getControl(name)

    def mdl(name: str) -> Any:
        return b.model.getByName(name)

    def show(item: Optional[ReviewItem]) -> None:
        sugg_visible = [False] * 3
        if item is None:
            mdl("lbl_category").setPropertyValue("TextColor", 0x000000)
            mdl("lbl_category").setPropertyValue("Label", "Vérification terminée")
            mdl("lbl_context").setPropertyValue("Label", "")
            if session.server_problem and session.applied == 0 and session.ignored == 0:
                msg = (
                    "Le serveur de correction ne répond pas.\n"
                    "Lancez-le avec le menu Dysbuntu > Démarrer le serveur, puis recommencez."
                )
            else:
                msg = "%d correction(s) appliquée(s), %d ignorée(s)." % (session.applied, session.ignored)
                if session.skipped_language:
                    msg += (
                        "\n%d paragraphe(s) non vérifié(s) : leur langue n'est pas le français "
                        "(Outils > Langue, ou option « Vérifier comme du français »)." % session.skipped_language
                    )
            mdl("lbl_explain").setPropertyValue("Label", msg)
            mdl("lbl_progress").setPropertyValue("Label", "")
            ctl("btn_ignore").setVisible(False)
            ctl("btn_ignore_rule").setVisible(False)
        else:
            issue = item.issue
            mdl("lbl_progress").setPropertyValue(
                "Label",
                "Paragraphe %d sur %d  -  %d corrigée(s), %d ignorée(s)"
                % (item.paragraph + 1, item.paragraph_total, session.applied, session.ignored),
            )
            mdl("lbl_category").setPropertyValue("TextColor", issue.color)
            mdl("lbl_category").setPropertyValue("Label", issue.category_label)
            mdl("lbl_context").setPropertyValue(
                "Label", "…%s« %s »%s…" % (item.before, item.error_text, item.after)
            )
            mdl("lbl_explain").setPropertyValue("Label", issue.full_comment)
            for i, s in enumerate(issue.suggestions[:3]):
                mdl("sug%d" % i).setPropertyValue("Label", s if s else "(supprimer)")
                sugg_visible[i] = True
            ctl("btn_ignore").setVisible(True)
            ctl("btn_ignore_rule").setVisible(True)
        for i in range(3):
            ctl("sug%d" % i).setVisible(sugg_visible[i])

    class Listener(unohelper.Base, XActionListener):
        def actionPerformed(self, ev: Any) -> None:  # noqa: N802 (nom imposé par UNO)
            cmd = ev.ActionCommand
            if cmd.startswith("sug"):
                show(session.apply(int(cmd[3:])))
            elif cmd == "ignore":
                show(session.ignore())
            elif cmd == "ignore_rule":
                show(session.ignore_rule())

        def disposing(self, ev: Any) -> None:
            pass

    listener = Listener()
    for i in range(3):
        c = ctl("sug%d" % i)
        c.setActionCommand("sug%d" % i)
        c.addActionListener(listener)
    ctl("btn_ignore").setActionCommand("ignore")
    ctl("btn_ignore").addActionListener(listener)
    ctl("btn_ignore_rule").setActionCommand("ignore_rule")
    ctl("btn_ignore_rule").addActionListener(listener)

    return b, show


def run_review_dialog(ctx: Any, frame: Any, session: ReviewSession, cfg: Dict[str, Any]) -> None:
    b, show = build_review_dialog(ctx, session, cfg)
    b.create_peer()
    show(session.start())
    try:
        b.dialog.execute()
    finally:
        b.dialog.dispose()


# --------------------------------------------------------------------------
# Options
# --------------------------------------------------------------------------
def build_options_dialog(ctx: Any, cfg: Dict[str, Any]) -> DialogBuilder:
    b = DialogBuilder(ctx, "Dysbuntu Correcteur - Options", 230, 170, cfg["font_size"])
    b.add("FixedText", "lbl_cat", 6, 6, 218, 10, Label="Types d'erreurs à signaler :", FontWeight=150.0)
    y = 20
    for key in CATEGORY_KEYS:
        b.add(
            "CheckBox", "cat_" + key, 12, y, 210, 11,
            Label=CATEGORIES[key].label, State=1 if cfg["categories"].get(key) else 0,
        )
        y += 13
    b.add(
        "CheckBox", "auto_start", 6, y + 4, 218, 11,
        Label="Démarrer le serveur LanguageTool automatiquement", State=1 if cfg["auto_start_server"] else 0,
    )
    b.add(
        "CheckBox", "force_fr", 6, y + 18, 218, 11,
        Label="Vérification guidée : tout lire comme du français", State=1 if cfg["review_force_french"] else 0,
    )
    y += 14
    b.add("FixedText", "lbl_font", 6, y + 22, 150, 11, Label="Taille du texte des fenêtres (9 à 32) :")
    b.add(
        "NumericField", "font_size", 160, y + 20, 40, 12,
        Value=float(cfg["font_size"]), ValueMin=9.0, ValueMax=32.0, DecimalAccuracy=0, Spin=True,
    )
    b.add("Button", "btn_ok", 6, y + 42, 60, 14, Label="Enregistrer", PushButtonType=PUSH_OK, DefaultButton=True)
    b.add("Button", "btn_cancel", 72, y + 42, 60, 14, Label="Annuler", PushButtonType=PUSH_CANCEL)
    b.model.setPropertyValue("Height", int((y + 62) * b.scale))
    return b


def run_options_dialog(ctx: Any, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Affiche les options ; retourne la nouvelle configuration, ou None si annulé."""
    b = build_options_dialog(ctx, cfg)
    b.create_peer()
    try:
        if b.dialog.execute() != PUSH_OK:
            return None
        new = dict(cfg)
        new["categories"] = {
            k: bool(b.model.getByName("cat_" + k).getPropertyValue("State")) for k in CATEGORY_KEYS
        }
        new["auto_start_server"] = bool(b.model.getByName("auto_start").getPropertyValue("State"))
        new["review_force_french"] = bool(b.model.getByName("force_fr").getPropertyValue("State"))
        new["font_size"] = int(b.model.getByName("font_size").getPropertyValue("Value"))
        return new
    finally:
        b.dialog.dispose()
