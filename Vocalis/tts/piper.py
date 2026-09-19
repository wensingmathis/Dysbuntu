"""
piper.py — Prise en charge de Piper TTS (moteur secondaire de Vocalis).

Ce module s'ajoute à eSpeak NG sans le remplacer : eSpeak NG reste le moteur
principal, Piper vient simplement enrichir la liste des voix.

Comme pour espeak.py, c'est le SEUL fichier qui exécute réellement Piper.
Tout est local : aucun téléchargement, aucun texte envoyé sur Internet.

Commande de référence reproduite par ce module :

    echo "Bonjour, ceci est un test de Vocalis." | \
    piper --model ~/piper-voices/fr_FR-siwis-medium.onnx \
          --output_file /tmp/vocalis-test.wav
"""

from __future__ import annotations

import array
import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from .espeak import RATE_DEFAULT, EspeakError

# --------------------------------------------------------------------------
# Emplacements recherchés (jamais de chemin absolu en dur : Path.home())
# --------------------------------------------------------------------------
BINARY_CANDIDATES: Sequence[Path] = (
    Path.home() / ".local" / "bin" / "piper",
    Path.home() / ".local" / "share" / "pipx" / "venvs" / "piper-tts" / "bin" / "piper",
)

MODEL_DIRECTORIES: Sequence[Path] = (
    Path.home() / "piper-voices",
    Path.home() / ".local" / "share" / "piper-voices",
)

# Voix mise en avant lorsqu'elle est présente.
PREFERRED_MODEL = "fr_FR-siwis-medium"

# --------------------------------------------------------------------------
# RÉGLAGES DE TEST — à remettre à leur valeur normale une fois la voix validée
# --------------------------------------------------------------------------
# Tant que FORCE_MODEL contient un nom de modèle, Vocalis n'expose QUE cette
# voix Piper. Mettre None pour retrouver toutes les voix Piper détectées.
FORCE_MODEL: Optional[str] = "fr_FR-siwis-medium"

# Affiche dans le terminal le moteur, l'exécutable et le modèle réellement
# utilisés à chaque génération. Mettre False pour supprimer ces messages.
DIAGNOSTIC = True

# Lecteurs audio essayés dans l'ordre pour jouer le WAV produit par Piper.
AUDIO_PLAYERS = (
    ("paplay", []),
    ("aplay", ["-q"]),
    ("play", ["-q"]),
    ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
)


class PiperNotFoundError(RuntimeError):
    """Piper n'est pas installé aux emplacements connus."""


class PiperError(RuntimeError):
    """Piper est présent mais son exécution a échoué."""


@dataclass(frozen=True)
class PiperVoice:
    """
    Une voix Piper.

    L'objet expose volontairement la même surface que tts.espeak.Voice
    (identifier / label / is_french / supports_pitch) afin que l'interface
    graphique existante n'ait pas besoin d'être modifiée.
    """

    model: Path            # chemin du .onnx
    config: Path           # chemin du .onnx.json
    name: str              # ex. "fr_FR-siwis-medium"
    engine: str = "piper"

    @property
    def identifier(self) -> str:
        # Préfixé pour ne jamais entrer en collision avec un code eSpeak NG.
        return f"piper:{self.name}"

    @property
    def language(self) -> str:
        return self.name.split("-")[0] if "-" in self.name else self.name

    @property
    def is_french(self) -> bool:
        return self.language.lower().startswith("fr")

    @property
    def supports_pitch(self) -> bool:
        # Piper ne propose pas de réglage de hauteur : l'interface désactivera
        # automatiquement le curseur correspondant.
        return False

    @property
    def label(self) -> str:
        # Le moteur est nommé en premier pour qu'aucune confusion ne soit
        # possible avec une voix eSpeak NG dans la liste déroulante.
        langue = "Français" if self.is_french else self.language
        return f"Piper — {langue} — {self.name}"


class PiperProcess:
    """
    Objet compatible avec l'API subprocess.Popen attendue par TTSManager
    (poll / communicate / terminate / returncode).

    Piper se déroule en deux temps : synthèse vers un fichier WAV temporaire,
    puis lecture de ce fichier. Ce petit adaptateur enchaîne les deux étapes
    tout en restant interruptible par le bouton « Arrêter ».
    """

    def __init__(self, command: List[str], text: str, volume: int) -> None:
        self._volume = volume
        self._stopped = False
        self._finished = False
        self._returncode: Optional[int] = None

        handle, self._wav_path = tempfile.mkstemp(prefix="vocalis-piper-", suffix=".wav")
        os.close(handle)

        command = list(command) + ["--output_file", self._wav_path]
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            self._cleanup()
            raise PiperError(f"Échec du lancement de Piper : {exc}") from exc

        # Le texte est transmis par l'entrée standard, comme dans la commande
        # de test (echo … | piper …).
        self._text = text

    # -- API type Popen ------------------------------------------------
    @property
    def returncode(self) -> Optional[int]:
        return self._returncode

    def poll(self) -> Optional[int]:
        return self._returncode if self._finished else None

    def terminate(self) -> None:
        self._stopped = True
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def communicate(self):
        """Bloquant : synthèse puis lecture. Appelé depuis un fil dédié."""
        try:
            _, erreur = self._process.communicate(input=self._text)
            code = self._process.returncode

            if self._stopped:
                return "", ""
            if code != 0:
                self._returncode = code
                return "", (erreur or "Piper s'est arrêté de façon inattendue.").strip()

            self._appliquer_volume()

            lecteur = _trouver_lecteur()
            if lecteur is None:
                self._returncode = 1
                return "", (
                    "Aucun lecteur audio n'a été trouvé pour jouer le son de Piper.\n\n"
                    "Installez-en un, par exemple :\n\n    sudo apt install alsa-utils"
                )

            self._process = subprocess.Popen(
                lecteur + [self._wav_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if self._stopped:  # arrêt demandé pendant la synthèse
                self._process.terminate()

            _, erreur_lecture = self._process.communicate()
            self._returncode = self._process.returncode
            if self._returncode not in (0, -15, -9) and not self._stopped:
                return "", (erreur_lecture or "La lecture audio a échoué.").strip()
            return "", ""
        finally:
            self._finished = True
            if self._returncode is None:
                self._returncode = 0
            self._cleanup()

    # -- Interne -------------------------------------------------------
    def _appliquer_volume(self) -> None:
        """
        Piper n'a pas d'option de volume : le gain est appliqué directement sur
        les échantillons du WAV (16 bits PCM), localement.
        """
        if self._volume == 100:
            return
        facteur = max(0, self._volume) / 100.0
        try:
            with wave.open(self._wav_path, "rb") as source:
                params = source.getparams()
                if params.sampwidth != 2:
                    return
                donnees = source.readframes(params.nframes)

            echantillons = array.array("h")
            echantillons.frombytes(donnees)
            for i, valeur in enumerate(echantillons):
                echantillons[i] = max(-32768, min(32767, int(valeur * facteur)))

            with wave.open(self._wav_path, "wb") as sortie:
                sortie.setparams(params)
                sortie.writeframes(echantillons.tobytes())
        except (wave.Error, OSError, ValueError):
            # En cas de souci, on lit simplement le son au volume d'origine.
            pass

    def _cleanup(self) -> None:
        try:
            os.unlink(self._wav_path)
        except OSError:
            pass


class PiperEngine:
    """Enveloppe autour de l'exécutable Piper."""

    def __init__(self, binary: Optional[str] = None) -> None:
        self.binary = binary or self.find_binary()
        self._voices: List[PiperVoice] = []

    # ------------------------------------------------------------------
    # Détection
    # ------------------------------------------------------------------
    @staticmethod
    def find_binary() -> str:
        """
        Cherche l'exécutable Piper :
          1. ~/.local/bin/piper
          2. ~/.local/share/pipx/venvs/piper-tts/bin/piper
          3. n'importe quel « piper » présent dans le PATH
        """
        for chemin in BINARY_CANDIDATES:
            if chemin.is_file() and os.access(chemin, os.X_OK):
                return str(chemin)
        depuis_path = shutil.which("piper")
        if depuis_path:
            return depuis_path
        raise PiperNotFoundError("Piper n'a pas été trouvé sur ce système.")

    @staticmethod
    def is_available() -> bool:
        try:
            PiperEngine.find_binary()
            return True
        except PiperNotFoundError:
            return False

    # ------------------------------------------------------------------
    # Modèles de voix
    # ------------------------------------------------------------------
    def list_voices(self) -> List[PiperVoice]:
        """
        Parcourt ~/piper-voices (et ~/.local/share/piper-voices) à la recherche
        des modèles .onnx accompagnés de leur fichier .onnx.json.

        Aucun téléchargement : seuls les modèles déjà présents sont listés.
        """
        if self._voices:
            return self._voices

        trouvees: List[PiperVoice] = []
        deja_vues = set()

        for dossier in MODEL_DIRECTORIES:
            if not dossier.is_dir():
                continue
            for modele in sorted(dossier.glob("*.onnx")):
                config = modele.with_suffix(modele.suffix + ".json")
                if not config.is_file():
                    continue  # modèle incomplet, on l'ignore
                nom = modele.stem
                if nom in deja_vues:
                    continue
                deja_vues.add(nom)
                trouvees.append(PiperVoice(model=modele, config=config, name=nom))

        # Mode test : une seule voix exposée, celle explicitement demandée.
        if FORCE_MODEL:
            trouvees = [v for v in trouvees if v.name == FORCE_MODEL]
            if not trouvees:
                attendu = Path.home() / "piper-voices" / f"{FORCE_MODEL}.onnx"
                raise PiperError(
                    f"Le modèle Piper « {FORCE_MODEL} » est introuvable.\n\n"
                    f"Fichier attendu : {attendu}\n"
                    f"Fichier attendu : {attendu}.json\n\n"
                    "Vérifiez que les deux fichiers sont bien présents.\n"
                    "Aucun téléchargement n'est effectué par Vocalis."
                )

        # fr_FR-siwis-medium en tête, puis les autres voix françaises.
        trouvees.sort(
            key=lambda v: (v.name != PREFERRED_MODEL, not v.is_french, v.name.lower())
        )
        self._voices = trouvees
        return trouvees

    # ------------------------------------------------------------------
    # Synthèse
    # ------------------------------------------------------------------
    def build_command(
        self,
        voice: PiperVoice,
        rate: int = RATE_DEFAULT,
        output_wav: Optional[str] = None,
    ) -> List[str]:
        """Construit la ligne de commande Piper (sans l'exécuter)."""
        # Vérification stricte : si le modèle demandé n'est pas utilisable, on
        # lève une erreur. Vocalis ne bascule JAMAIS silencieusement sur une
        # autre voix ni sur eSpeak NG.
        if not voice.model.is_file():
            raise PiperError(
                f"Le modèle Piper est introuvable :\n{voice.model}\n\n"
                "La voix sélectionnée ne peut pas être utilisée."
            )
        if not voice.config.is_file():
            raise PiperError(
                f"Le fichier de configuration du modèle est introuvable :\n"
                f"{voice.config}\n\nPiper ne peut pas charger cette voix."
            )

        command = [self.binary, "--model", str(voice.model)]

        if voice.config.is_file():
            command += ["--config", str(voice.config)]

        # Vitesse : Piper raisonne en « length_scale » (durée), donc l'inverse
        # des mots par minute utilisés par eSpeak NG. Le curseur existant de
        # l'interface reste ainsi cohérent d'un moteur à l'autre.
        echelle = RATE_DEFAULT / max(1, int(rate))
        command += ["--length_scale", f"{max(0.3, min(3.0, echelle)):.3f}"]

        if output_wav:
            command += ["--output_file", output_wav]
        return command

    def speak(
        self,
        text: str,
        voice: PiperVoice,
        rate: int = RATE_DEFAULT,
        volume: int = 100,
        pitch: Optional[int] = None,  # ignoré : Piper ne gère pas la hauteur
    ) -> PiperProcess:
        """Lance la synthèse puis la lecture, sans bloquer l'appelant direct."""
        command = self.build_command(voice, rate=rate)
        afficher_diagnostic(
            Moteur="Piper",
            Exécutable=self.binary,
            Modèle=voice.model,
            Config=voice.config,
            Commande=" ".join(command),
        )
        return PiperProcess(command, text, volume)

    def save_to_wav(
        self,
        text: str,
        path: str,
        voice: PiperVoice,
        rate: int = RATE_DEFAULT,
        volume: int = 100,
        pitch: Optional[int] = None,
    ) -> None:
        """Écrit la synthèse Piper dans un fichier WAV (opération locale)."""
        command = self.build_command(voice, rate=rate, output_wav=path)
        afficher_diagnostic(
            Moteur="Piper",
            Exécutable=self.binary,
            Modèle=voice.model,
            Fichier_de_sortie=path,
        )
        try:
            resultat = subprocess.run(
                command, input=text, capture_output=True, text=True, check=False
            )
        except OSError as exc:
            raise PiperError(f"Échec du lancement de Piper : {exc}") from exc

        if resultat.returncode != 0:
            raise PiperError(
                "Piper n'a pas pu enregistrer le fichier :\n"
                + (resultat.stderr or "erreur inconnue").strip()
            )


def afficher_diagnostic(**champs) -> None:
    """
    Affiche dans le terminal le moteur réellement utilisé.

    MESSAGE TEMPORAIRE DE DIAGNOSTIC : mettre DIAGNOSTIC = False (en haut de
    ce fichier) pour le désactiver une fois la voix validée.
    """
    if not DIAGNOSTIC:
        return
    largeur = max((len(cle) for cle in champs), default=0)
    print("─" * 60)
    for cle, valeur in champs.items():
        print(f"{cle.replace('_', ' '):<{largeur}} : {valeur}")
    print("─" * 60, flush=True)


def _trouver_lecteur() -> Optional[List[str]]:
    """Retourne la commande du premier lecteur audio disponible."""
    for nom, options in AUDIO_PLAYERS:
        chemin = shutil.which(nom)
        if chemin:
            return [chemin] + list(options)
    return None
