#!/usr/bin/env bash
# Installation via paquets Debian : aucune commande téléchargée/exécutée.
set -euo pipefail
if ! command -v apt-get >/dev/null 2>&1; then
    echo "Cette installation vise Debian, Ubuntu et Linux Mint." >&2
    exit 1
fi
sudo apt-get update
sudo apt-get install -y python3 python3-tk espeak-ng alsa-utils
printf '%s\n' "Dépendances de base installées. Lancez : python3 main.py"
printf '%s\n' "Piper (optionnel) : pipx install piper-tts, puis ajoutez une voix locale."
