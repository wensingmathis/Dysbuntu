#!/usr/bin/env bash
# Lance le serveur LanguageTool LOCAL (uniquement sur cette machine : pas d'option --public).
set -euo pipefail
PORT="${1:-8081}"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/dysbuntu-correcteur/languagetool"
JAR="$(find "$DEST" -name languagetool-server.jar 2>/dev/null | head -n1 || true)"
if [ -z "$JAR" ]; then
  echo "LanguageTool n'est pas installé. Lancez d'abord : $(dirname "$0")/install_languagetool.sh" >&2
  exit 1
fi
cd "$(dirname "$JAR")"
echo "Serveur local sur http://127.0.0.1:$PORT (Ctrl+C pour arrêter)"
exec java -Xmx1g -cp languagetool-server.jar org.languagetool.server.HTTPServer --port "$PORT"
