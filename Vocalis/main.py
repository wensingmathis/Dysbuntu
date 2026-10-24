#!/usr/bin/env python3
"""Point d'entrée de Vocalis (Python 3.10+)."""
from __future__ import annotations

import sys

from tts.common import VocalisError
from tts.manager import TTSManager


def main() -> int:
    try:
        manager = TTSManager()
        from ui.app import VocalisApp
        app = VocalisApp(manager)
        app.mainloop()
        return 0
    except Exception as exc:  # frontière UI : y compris TclError sans serveur graphique
        print(f"Vocalis : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
