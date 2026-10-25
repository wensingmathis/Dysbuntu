#!/usr/bin/env python3
"""NumDys : calculatrice scientifique accessible, native GTK3 et hors ligne."""
from __future__ import annotations

import logging
import sys

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
except (ImportError, ValueError) as exc:
    print("NumDys nécessite python3-gi et gir1.2-gtk-3.0. "
          "Installez-les avec : sudo apt install python3-gi gir1.2-gtk-3.0", file=sys.stderr)
    raise SystemExit(1) from exc

from numdys import style
from numdys.app_calculator import CalculatorApp
from numdys.app_equations import EquationsApp
from numdys.app_graphing import GraphingApp
from numdys.app_home import HomeApp
from numdys.app_sequences import SequencesApp
from numdys.app_settings import SettingsApp
from numdys.state import AppState

APP_TITLES = {
    "calculatrice": "Calculs",
    "graphiques": "Graphiques",
    "equations": "Équations",
    "suites": "Suites",
    "reglages": "Réglages",
}


class NumDysWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="NumDys")
        self.set_default_size(420, 640)
        self.set_size_request(350, 440)
        self.connect("destroy", Gtk.main_quit)
        self.state = AppState()
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title("NumDys")
        self.set_titlebar(self.header)
        self.home_button = Gtk.Button(label="⌂ Accueil")
        self.home_button.connect("clicked", self.go_home)
        self.header.pack_start(self.home_button)
        self.stack = Gtk.Stack()
        self.add(self.stack)
        self.graphing_app = GraphingApp(self.state)
        pages = {
            "accueil": HomeApp(self.open_app),
            "calculatrice": CalculatorApp(self.state),
            "graphiques": self.graphing_app,
            "equations": EquationsApp(self.state),
            "suites": SequencesApp(self.state),
            "reglages": SettingsApp(self.state),
        }
        for key, page in pages.items():
            self.stack.add_named(page, key)
        self.stack.set_visible_child_name("accueil")

    def open_app(self, app_id: str) -> None:
        if app_id not in APP_TITLES:
            logging.warning("Écran inconnu demandé : %s", app_id)
            return
        self.stack.set_visible_child_name(app_id)
        self.header.set_title(APP_TITLES[app_id])
        self.home_button.show()
        if app_id == "graphiques":
            # Force le rafraîchissement après changement degrés/radians.
            self.graphing_app.drawing_area.queue_draw()

    def go_home(self, _widget) -> None:
        self.stack.set_visible_child_name("accueil")
        self.header.set_title("NumDys")
        self.home_button.hide()


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="NumDys : %(levelname)s : %(message)s")
    try:
        screen = style.apply()
        if not screen:
            return 1
        window = NumDysWindow()
        window.show_all()
        window.home_button.hide()
        Gtk.main()
        return 0
    except (OSError, RuntimeError) as exc:
        logging.exception("Erreur de lancement : %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
