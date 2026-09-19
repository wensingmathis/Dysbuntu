#!/usr/bin/env bash
#
# install.sh — Installation des dépendances de Vocalis (Ubuntu / Debian).
#
# Vérifie qu'eSpeak NG est présent. S'il est absent, l'explique clairement
# à l'utilisateur et propose de l'installer.
#
set -euo pipefail

echo "=== Installation de Vocalis ==="
echo

manquants=()

# --- Python 3 -----------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
    echo "[OK] Python 3 : $(python3 --version)"
else
    echo "[MANQUANT] Python 3"
    manquants+=("python3")
fi

# --- Tkinter (interface graphique) --------------------------------------
if python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "[OK] Tkinter (interface graphique)"
else
    echo "[MANQUANT] Tkinter — nécessaire pour la fenêtre de Vocalis"
    manquants+=("python3-tk")
fi

# --- eSpeak NG : dépendance OBLIGATOIRE ---------------------------------
if command -v espeak-ng >/dev/null 2>&1; then
    echo "[OK] eSpeak NG : $(espeak-ng --version | head -n 1)"
else
    echo
    echo "[MANQUANT] eSpeak NG"
    echo "  eSpeak NG est le moteur de synthèse vocale de Vocalis."
    echo "  Sans lui, l'application ne peut pas lire de texte à voix haute."
    manquants+=("espeak-ng")
fi

echo

# --- Installation des paquets manquants ---------------------------------
if [ ${#manquants[@]} -eq 0 ]; then
    echo "Toutes les dépendances sont présentes."
else
    echo "Paquets à installer : ${manquants[*]}"
    echo
    read -r -p "Voulez-vous les installer maintenant ? [O/n] " reponse
    reponse=${reponse:-O}
    if [[ "$reponse" =~ ^[OoYy]$ ]]; then
        sudo apt update
        sudo apt install -y "${manquants[@]}"
    else
        echo
        echo "Installation annulée. Vous pouvez l'effectuer plus tard avec :"
        echo
        echo "    sudo apt install ${manquants[*]}"
        echo
        exit 1
    fi
fi

# --- Vérification finale ------------------------------------------------
echo
if command -v espeak-ng >/dev/null 2>&1; then
    echo "Voix eSpeak NG françaises détectées :"
    espeak-ng --voices | awk 'NR==1 || $2 ~ /^fr/'
    echo
    echo "Vocalis est prêt. Lancez-le avec :"
    echo
    echo "    python3 main.py"
else
    echo "eSpeak NG reste introuvable : Vocalis ne pourra pas fonctionner." >&2
    exit 1
fi
