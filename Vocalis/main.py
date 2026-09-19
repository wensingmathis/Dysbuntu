#!/usr/bin/env python3
"""
Vocalis — synthèse vocale hors ligne avec eSpeak NG.

Lancement :
    python3 main.py

Si eSpeak NG n'est pas installé, un message d'erreur compréhensible est
affiché (fenêtre graphique si possible, sinon terminal) avec la commande
d'installation à exécuter.
"""

from __future__ import annotations

import sys

from tts.espeak import INSTALL_HINT, EspeakError, EspeakNotFoundError
from tts.manager import TTSManager


def _erreur(message: str) -> None:
    """Affiche l'erreur dans une fenêtre si possible, sinon dans le terminal."""
    print(message, file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox

        racine = tk.Tk()
        racine.withdraw()
        messagebox.showerror("Vocalis — eSpeak NG requis", message)
        racine.destroy()
    except Exception:
        pass


def main() -> int:
    try:
        manager = TTSManager()
    except EspeakNotFoundError:
        _erreur(INSTALL_HINT)
        return 1
    except EspeakError as exc:
        _erreur(str(exc))
        return 1

    try:
        from ui.app import VocalisApp
    except ImportError as exc:
        _erreur(
            "L'interface graphique n'a pas pu être chargée.\n\n"
            f"Détail : {exc}\n\n"
            "Sur Ubuntu, installez Tkinter avec :\n\n"
            "    sudo apt install python3-tk"
        )
        return 1

    VocalisApp(manager).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
