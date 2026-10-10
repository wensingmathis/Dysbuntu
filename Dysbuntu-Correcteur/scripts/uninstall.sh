#!/usr/bin/env bash
# Désinstalle Dysbuntu Correcteur. Avec --purge : supprime aussi réglages, journaux et LanguageTool.
set -euo pipefail
unopkg remove org.dysbuntu.correcteur || echo "(extension non installée)"
if [ "${1:-}" = "--purge" ]; then
  for d in "${XDG_CONFIG_HOME:-$HOME/.config}/dysbuntu-correcteur" \
           "${XDG_STATE_HOME:-$HOME/.local/state}/dysbuntu-correcteur" \
           "${XDG_DATA_HOME:-$HOME/.local/share}/dysbuntu-correcteur"; do
    if [ -d "$d" ]; then
      read -r -p "Supprimer $d ? [o/N] " ans
      case "$ans" in o|O|oui|OUI) rm -rf "$d"; echo "supprimé : $d" ;; esac
    fi
  done
fi
echo "Désinstallation terminée."
