#!/usr/bin/env python3
"""
diagnostic_piper.py — Vérifie, hors interface, quelle voix est réellement
utilisée par Vocalis.

    python3 diagnostic_piper.py

Le script :
  - affiche l'exécutable Piper trouvé ;
  - affiche le modèle fr_FR-siwis-medium et sa taille (un fichier tronqué est
    une cause classique de voix de mauvaise qualité) ;
  - lit le fichier .onnx.json pour afficher la fréquence d'échantillonnage ;
  - génère /tmp/vocalis-test.wav avec la commande exacte de Vocalis ;
  - compare la fréquence du WAV produit à celle annoncée par le modèle.

Aucun accès Internet, aucun téléchargement.
"""

from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

from tts.piper import (
    FORCE_MODEL,
    PiperEngine,
    PiperError,
    PiperNotFoundError,
)

TEXTE = "Bonjour, ceci est un test de Vocalis."
SORTIE = "/tmp/vocalis-test.wav"


def titre(texte: str) -> None:
    print(f"\n=== {texte} ===")


def main() -> int:
    titre("Exécutable Piper")
    try:
        engine = PiperEngine()
    except PiperNotFoundError as exc:
        print(f"ÉCHEC : {exc}")
        print(f"Cherché dans : {Path.home() / '.local' / 'bin' / 'piper'}")
        return 1
    print(f"Exécutable : {engine.binary}")

    titre("Modèle")
    try:
        voix = engine.list_voices()
    except PiperError as exc:
        print(f"ÉCHEC : {exc}")
        return 1
    if not voix:
        print("Aucun modèle Piper trouvé.")
        return 1

    for v in voix:
        taille = v.model.stat().st_size / (1024 * 1024)
        print(f"Voix       : {v.label}")
        print(f"Modèle     : {v.model}  ({taille:.1f} Mo)")
        print(f"Config     : {v.config}")
        if taille < 5:
            print("ATTENTION  : un modèle « medium » pèse environ 60 Mo. "
                  "Ce fichier semble incomplet ou corrompu.")

    voix_test = voix[0]
    if FORCE_MODEL and voix_test.name != FORCE_MODEL:
        print(f"ATTENTION : le modèle forcé est {FORCE_MODEL}, "
              f"mais {voix_test.name} a été retenu.")

    titre("Contenu du fichier .onnx.json")
    frequence_modele = None
    try:
        config = json.loads(voix_test.config.read_text(encoding="utf-8"))
        audio = config.get("audio", {})
        frequence_modele = audio.get("sample_rate")
        print(f"Fréquence annoncée : {frequence_modele} Hz")
        print(f"Phonémiseur        : {config.get('phoneme_type', 'inconnu')}")
        langue = config.get("language", {})
        print(f"Langue             : {langue.get('code', langue) or 'inconnue'}")
    except (OSError, ValueError) as exc:
        print(f"Fichier illisible : {exc}")

    titre("Génération de test")
    print(f"Commande : {' '.join(engine.build_command(voix_test, output_wav=SORTIE))}")
    try:
        engine.save_to_wav(TEXTE, SORTIE, voice=voix_test)
    except PiperError as exc:
        print(f"ÉCHEC : {exc}")
        return 1

    with wave.open(SORTIE, "rb") as f:
        frequence_wav = f.getframerate()
        duree = f.getnframes() / frequence_wav
        print(f"Fichier produit    : {SORTIE}")
        print(f"Fréquence du WAV   : {frequence_wav} Hz")
        print(f"Durée              : {duree:.2f} s")

    if frequence_modele and frequence_modele != frequence_wav:
        print("\nATTENTION : la fréquence du WAV ne correspond pas au modèle. "
              "C'est la cause typique d'une voix déformée.")
    elif duree < 1.0:
        print("\nATTENTION : la durée est anormalement courte pour cette phrase.")
    else:
        print("\nLa synthèse semble correcte. Écoutez le fichier :")
        print(f"    aplay {SORTIE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
