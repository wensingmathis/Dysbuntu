"""Faux serveur LanguageTool (quelques règles françaises) pour les tests et les démonstrations.

Il imite l'API /v2/check et /v2/languages. Ce N'EST PAS un vrai correcteur :
il ne sert qu'à tester l'extension sans Java ni téléchargement.

Usage : python3 tests/fake_languagetool.py --port 8081
"""
import argparse
import json
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RULES = [
    # (regex, remplacement, id, catégorie, issueType, message)
    (r"\bles chat\b", "les chats", "FAKE_ACCORD_PLURIEL", "GRAMMAR", "grammar",
     "Le mot « chat » doit être au pluriel après « les »."),
    (r"\bje suis aller\b", "je suis allé", "FAKE_PARTICIPE", "GRAMMAR", "grammar",
     "Après « être », on utilise le participe passé « allé »."),
    (r"\bbonjours\b", "bonjour", "FAKE_MORFOLOGIK", "TYPOS", "misspelling",
     "Faute d'orthographe possible."),
    (r"\bca\b", "ça", "FAKE_CA", "TYPOS", "misspelling", "Il manque la cédille : « ça »."),
    (r" {2,}", " ", "FAKE_WHITESPACE", "TYPOGRAPHY", "typographical", "Espaces en trop."),
    (r" ,", ",", "FAKE_COMMA_SPACE", "PUNCTUATION", "typographical", "Pas d'espace avant une virgule."),
]


def u16(text, idx):
    return len(text[:idx].encode("utf-16-le")) // 2


def check(text, disabled_rules=(), disabled_categories=()):
    matches = []
    for pattern, repl, rid, cat, itype, msg in RULES:
        if rid in disabled_rules or cat in disabled_categories:
            continue
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = repl[:1].upper() + repl[1:] if m.group(0)[:1].isupper() else repl
            matches.append({
                "message": msg,
                "shortMessage": "",
                "offset": u16(text, m.start()),
                "length": u16(text, m.end()) - u16(text, m.start()),
                "replacements": [{"value": value}],
                "rule": {"id": rid, "description": msg, "issueType": itype,
                         "category": {"id": cat, "name": cat.title()}},
            })
    matches.sort(key=lambda x: x["offset"])
    return {"software": {"name": "FakeLanguageTool"}, "language": {"code": "fr"}, "matches": matches}


class Handler(BaseHTTPRequestHandler):
    server_version = "FakeLT"
    requests_seen = 0

    def log_message(self, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/v2/languages"):
            self._send(200, [{"name": "French", "code": "fr", "longCode": "fr"}])
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/v2/check"):
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        lang = form.get("language", [""])[0]
        if lang not in ("fr", "fr-FR"):
            return self._send(400, {"error": "unsupported language %s" % lang})
        type(self).requests_seen += 1
        text = form.get("text", [""])[0]
        rules = [r for r in form.get("disabledRules", [""])[0].split(",") if r]
        cats = [c for c in form.get("disabledCategories", [""])[0].split(",") if c]
        self._send(200, check(text, rules, cats))


def start(port=0):
    """Démarre le faux serveur dans un thread ; retourne (serveur, port)."""
    Handler.requests_seen = 0
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8081)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("Faux LanguageTool sur http://127.0.0.1:%d (Ctrl+C pour arrêter)" % args.port)
    srv.serve_forever()
