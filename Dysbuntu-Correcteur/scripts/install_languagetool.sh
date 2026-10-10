#!/usr/bin/env bash
# Installe LanguageTool (serveur local) pour Dysbuntu Correcteur.
# C'est la SEULE étape qui utilise Internet : un téléchargement, avec votre accord.
# Ensuite, tout fonctionne hors ligne.
set -euo pipefail

URL="https://languagetool.org/download/LanguageTool-stable.zip"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/dysbuntu-correcteur/languagetool"
SHA256=""
ASSUME_YES=0

usage() {
  cat <<USAGE
Usage : $0 [--yes] [--dir DOSSIER] [--url URL] [--sha256 EMPREINTE]

  --yes            accepte le téléchargement sans poser la question
  --dir DOSSIER    dossier d'installation (défaut : $DEST)
  --url URL        archive à télécharger (défaut : $URL)
                   (une URL file:///chemin/archive.zip permet une installation sans Internet)
  --sha256 HASH    vérifie l'empreinte SHA-256 de l'archive
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) ASSUME_YES=1 ;;
    --dir) DEST="$2"; shift ;;
    --url) URL="$2"; shift ;;
    --sha256) SHA256="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Option inconnue : $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

# --- Java ---------------------------------------------------------------
if ! command -v java >/dev/null 2>&1; then
  echo "Java est introuvable. Installez-le :  sudo apt install default-jre-headless" >&2
  exit 1
fi
JAVA_MAJOR="$(java -version 2>&1 | sed -n 's/.*version "\([0-9]*\)\..*/\1/p;s/.*version "\([0-9]*\)".*/\1/p' | head -n1)"
if [ -z "${JAVA_MAJOR}" ] || [ "${JAVA_MAJOR}" -lt 17 ]; then
  echo "Java 17 ou plus récent est nécessaire (trouvé : ${JAVA_MAJOR:-inconnu})." >&2
  echo "   sudo apt install default-jre-headless" >&2
  exit 1
fi

# --- Déjà installé ? --------------------------------------------------------
if find "$DEST" -name languagetool-server.jar 2>/dev/null | grep -q .; then
  echo "LanguageTool est déjà installé dans : $DEST"
  exit 0
fi

# --- Consentement -----------------------------------------------------------
case "$URL" in
  file://*) ;;  # pas de réseau
  *)
    echo "Ce script va télécharger LanguageTool (environ 200 Mo) depuis :"
    echo "    $URL"
    echo "Seule cette archive est téléchargée ; aucun de vos textes n'est envoyé."
    if [ "$ASSUME_YES" -ne 1 ]; then
      read -r -p "Continuer ? [o/N] " ans
      case "$ans" in o|O|oui|OUI|y|Y) ;; *) echo "Annulé."; exit 1 ;; esac
    fi
    ;;
esac

# --- Téléchargement ---------------------------------------------------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ARCHIVE="$TMP/languagetool.zip"
if command -v curl >/dev/null 2>&1; then
  curl --fail --location --proto '=https,file' --output "$ARCHIVE" "$URL"
elif command -v wget >/dev/null 2>&1; then
  case "$URL" in file://*) cp "${URL#file://}" "$ARCHIVE" ;; *) wget -O "$ARCHIVE" "$URL" ;; esac
else
  echo "Ni curl ni wget : installez l'un des deux (sudo apt install curl)." >&2
  exit 1
fi

if [ -n "$SHA256" ]; then
  echo "$SHA256  $ARCHIVE" | sha256sum --check --status || { echo "Empreinte SHA-256 incorrecte : archive rejetée." >&2; exit 1; }
  echo "Empreinte SHA-256 vérifiée."
else
  echo "Astuce : ajoutez --sha256 <empreinte> pour vérifier l'archive."
fi

command -v unzip >/dev/null 2>&1 || { echo "Installez unzip : sudo apt install unzip" >&2; exit 1; }
mkdir -p "$DEST"
unzip -q "$ARCHIVE" -d "$DEST"

JAR="$(find "$DEST" -name languagetool-server.jar | head -n1 || true)"
if [ -z "$JAR" ]; then
  echo "languagetool-server.jar introuvable dans l'archive : installation incomplète." >&2
  exit 1
fi
echo "LanguageTool installé : $JAR"
echo "Test manuel du serveur :  $(dirname "$0")/start_server.sh"
