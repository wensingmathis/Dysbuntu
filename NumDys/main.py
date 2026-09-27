#!/usr/bin/env python3
"""
NumDys — une calculatrice scientifique/graphique inspirée de la NumWorks,
avec la police OpenDyslexic sur toute l'interface i love gorillaz .

Applications incluses :
    - Calculs      : calculatrice scientifique avec historique pour voir tes cacules de merde 
    - Graphiques   : traceur de courbes y = f(x), zoom et déplacement chian 
    - Équations    : résolution du 1er et du 2nd degré 
    - Suites       : suites récurrentes u(n+1) = f(u, n)
    - Réglages     : mode degrés / radians

Dépendances système (Debian) :
    sudo apt install python3-gi gir1.2-gtk-3.0 fonts-opendyslexic

Lancement :
    python3 main.py
"""

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from numdys import style
from numdys.state import AppState
from numdys.app_home import HomeApp
from numdys.app_calculator import CalculatorApp
from numdys.app_graphing import GraphingApp
from numdys.app_equations import EquationsApp
from numdys.app_sequences import SequencesApp
from numdys.app_settings import SettingsApp


APP_TITLES = {
    "calculatrice": "Calculs",
    "graphiques": "Graphiques",
    "equations": "Équations",
    "suites": "Suites",
    "reglages": "Réglages",
}


class NumDysWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="NumDys")
        self.set_default_size(400, 620)
        self.connect("destroy", Gtk.main_quit)

        self.state = AppState()

        # --- Barre supérieure avec bouton Accueil -----------------------------
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title("NumDys")
        self.set_titlebar(self.header)

        self.home_button = Gtk.Button(label="⌂ Accueil")
        self.home_button.connect("clicked", self.go_home)
        self.home_button.set_no_show_all(True)  # caché tant qu'on est à l'accueil
        self.header.pack_start(self.home_button)

        # --- Pile d'écrans (une page par application) -----------------------
        self.stack = Gtk.Stack()
        self.add(self.stack)

        self.stack.add_named(HomeApp(self.open_app), "accueil")
        self.stack.add_named(CalculatorApp(self.state), "calculatrice")
        self.stack.add_named(GraphingApp(self.state), "graphiques")
        self.stack.add_named(EquationsApp(self.state), "equations")
        self.stack.add_named(SequencesApp(self.state), "suites")
        self.stack.add_named(SettingsApp(self.state), "reglages")

        self.stack.set_visible_child_name("accueil")

    def open_app(self, app_id):
        self.stack.set_visible_child_name(app_id)
        self.header.set_title(APP_TITLES.get(app_id, "NumDys"))
        self.home_button.show()

    def go_home(self, _widget):
        self.stack.set_visible_child_name("accueil")
        self.header.set_title("NumDys")
        self.home_button.hide()


def main():
    style.apply()
    win = NumDysWindow()
    win.show_all()
    win.home_button.hide()  # masqué après show_all(), on est à l'accueil
    Gtk.main()


if __name__ == "__main__":
    main()
