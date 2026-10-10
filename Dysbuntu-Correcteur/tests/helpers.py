import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "extension", "pythonpath"))
sys.path.insert(0, ROOT)

from dysbuntu_correcteur.config import ConfigStore  # noqa: E402
from dysbuntu_correcteur.lt_client import LanguageToolClient  # noqa: E402
from dysbuntu_correcteur.proofread import Proofreader  # noqa: E402
from tests import fake_languagetool  # noqa: E402


def make_proofreader(port, tmpdir, **cfg):
    store = ConfigStore(os.path.join(tmpdir, "config.json"))
    base = store.get()
    base.update(port=port, auto_start_server=False)
    base.update(cfg)
    store.save(base)
    return Proofreader(store), store


def closed_port():
    """Un port local libre (donc où personne n'écoute)."""
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port
