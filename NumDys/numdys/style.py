"""CSS partagé par toute l'application : police OpenDyslexic + thème."""

from gi.repository import Gtk, Gdk

CSS = """
window {
    background-color: #22252b;
}

* {
    font-family: "OpenDyslexic", "OpenDyslexic Regular", sans-serif;
}

/* --- Écran d'accueil --------------------------------------------------- */

.home-title {
    font-size: 22px;
    color: #f5f5f5;
    margin-bottom: 6px;
}

.app-tile {
    background-color: #33363f;
    border-radius: 14px;
    min-width: 120px;
    min-height: 100px;
    color: #ffffff;
    font-size: 15px;
}

.app-tile:hover {
    background-color: #454955;
}

/* --- Barre supérieure --------------------------------------------------- */

headerbar {
    background-color: #ffb734;
    color: #22252b;
    font-size: 15px;
}

headerbar button {
    background-color: transparent;
    color: #22252b;
}

/* --- Affichage / champs de saisie --------------------------------------- */

#display, .numdys-entry {
    font-size: 24px;
    color: #ffffff;
    background-color: #1a1c21;
    border-radius: 8px;
    padding: 10px;
}

.numdys-label {
    color: #e6e6e6;
    font-size: 15px;
}

.numdys-result {
    color: #7be07f;
    font-size: 20px;
}

.numdys-error {
    color: #ff8080;
    font-size: 16px;
}

/* --- Boutons calculatrice ------------------------------------------------ */

button.number {
    background-color: #3c3f48;
    color: #ffffff;
    font-size: 18px;
    min-width: 52px;
    min-height: 46px;
    border-radius: 8px;
    margin: 2px;
}

button.operator {
    background-color: #ffb734;
    color: #22252b;
    font-size: 18px;
    min-width: 52px;
    min-height: 46px;
    border-radius: 8px;
    margin: 2px;
}

button.function {
    background-color: #52565f;
    color: #ffffff;
    font-size: 15px;
    min-width: 52px;
    min-height: 46px;
    border-radius: 8px;
    margin: 2px;
}

button.equals {
    background-color: #2ba84a;
    color: #ffffff;
    font-size: 18px;
    min-width: 52px;
    min-height: 46px;
    border-radius: 8px;
    margin: 2px;
}

button:hover {
    opacity: 0.85;
}

scrolledwindow, list, row {
    background-color: transparent;
}

list row {
    color: #f0f0f0;
    padding: 4px;
}
"""


def apply():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
