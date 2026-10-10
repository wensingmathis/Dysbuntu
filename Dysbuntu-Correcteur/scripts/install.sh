#!/usr/bin/env bash
# Installation complète de Dysbuntu Correcteur (Ubuntu / Linux Mint).
# Usage : scripts/install.sh [--no-apt] [--with-languagetool]
set -euo pipefail
cd "$(dirname "$0")/.."

NO_APT=0; WITH_LT=0
for a in "$@"; do
  case "$a" in
    --no-apt) NO_APT=1 ;;
    --with-languagetool) WITH_LT=1 ;;
    -h|--help) sed -n '2,3p' "$0"; exit 0 ;;
    *) echo "Option inconnue : $a" >&2; exit 2 ;;
  esac
done

if [ "$(id -u)" -eq 0 ]; then
  echo "Ne lancez pas ce script en root : unopkg refuse d'installer pour root." >&2
  echo "Lancez-le avec votre utilisateur ; sudo sera demandé uniquement pour apt." >&2
  exit 1
fi

if [ "$NO_APT" -ne 1 ]; then
  echo "== Paquets système (sudo requis) =="
  sudo apt-get install -y libreoffice-writer libreoffice-script-provider-python python3-uno default-jre-headless unzip curl
fi

echo "== Construction de l'extension =="
OXT="$(python3 build.py)"

echo "== Installation dans LibreOffice (fermez LibreOffice avant) =="
unopkg remove org.dysbuntu.correcteur >/dev/null 2>&1 || true
unopkg add --suppress-license "$OXT"

if [ "$WITH_LT" -eq 1 ]; then
  scripts/install_languagetool.sh
else
  echo
  echo "Étape suivante : installer le moteur de correction (téléchargement unique, avec votre accord) :"
  echo "    scripts/install_languagetool.sh"
fi
echo
echo "Terminé. Ouvrez Writer : menu « Dysbuntu »."
