"""Journalisation locale. Le texte des documents n'est JAMAIS écrit dans les journaux."""

from __future__ import annotations

import logging
import logging.handlers
import os

from . import paths

_configured = False


def get_logger(name: str = "dysbuntu") -> logging.Logger:
    global _configured
    logger = logging.getLogger("dysbuntu")
    if not _configured:
        _configured = True
        logger.setLevel(logging.INFO)
        logger.propagate = False
        try:
            os.makedirs(paths.state_dir(), exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(
                paths.log_file(), maxBytes=200_000, backupCount=1, encoding="utf-8"
            )
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        except OSError:
            logger.addHandler(logging.NullHandler())
    return logger.getChild(name) if name != "dysbuntu" else logger
