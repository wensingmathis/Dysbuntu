"""
app.py — Interface graphique de Vocalis (Tkinter).

Parcours utilisateur :
    1. Choisir une voix eSpeak NG
    2. Écrire ou coller son texte
    3. Cliquer sur « Générer la voix »
    4. Vocalis utilise eSpeak NG
    5. Le texte est lu à voix haute

Cette couche n'exécute jamais eSpeak NG directement : elle passe uniquement
par TTSManager.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tts.espeak import (
    PITCH_DEFAULT,
    PITCH_MAX,
    PITCH_MIN,
    RATE_DEFAULT,
    RATE_MAX,
    RATE_MIN,
    VOLUME_DEFAULT,
    VOLUME_MAX,
    VOLUME_MIN,
    EspeakError,
)
from tts.manager import TTSManager

TEXTE_EXEMPLE = "Bonjour, ceci est un test."


class VocalisApp(tk.Tk):
    def __init__(self, manager: TTSManager) -> None:
        super().__init__()

        self.manager = manager
        self.manager.on_start = lambda: self.after(0, self._lecture_commencee)
        self.manager.on_finish = lambda *a: self.after(0, self._lecture_terminee, *a)
        self.manager.on_error = lambda message: self.after(0, self._afficher_erreur, message)

        self.title("Vocalis — synthèse vocale hors ligne (eSpeak NG)")
        self.geometry("720x560")
        self.minsize(620, 500)

        self._voix_affichees = []
        self._construire_interface()
        self._charger_voix()

        self.protocol("WM_DELETE_WINDOW", self._quitter)

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------
    def _construire_interface(self) -> None:
        cadre = ttk.Frame(self, padding=16)
        cadre.pack(fill="both", expand=True)
        cadre.columnconfigure(1, weight=1)

        ligne = 0

        # --- 1. Choisir une voix -------------------------------------
        ttk.Label(cadre, text="1. Choisir une voix", font=("", 11, "bold")).grid(
            row=ligne, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        ligne += 1

        ttk.Label(cadre, text="Voix :").grid(row=ligne, column=0, sticky="w")
        self.combo_voix = ttk.Combobox(cadre, state="readonly", width=48)
        self.combo_voix.grid(row=ligne, column=1, sticky="ew", padx=(8, 8))
        self.combo_voix.bind("<<ComboboxSelected>>", self._voix_changee)

        self.var_fr = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            cadre,
            text="Voix françaises",
            variable=self.var_fr,
            command=self._charger_voix,
        ).grid(row=ligne, column=2, sticky="w")
        ligne += 1

        # --- Réglages -------------------------------------------------
        reglages = ttk.LabelFrame(cadre, text="Réglages de la voix", padding=12)
        reglages.grid(row=ligne, column=0, columnspan=3, sticky="ew", pady=14)
        reglages.columnconfigure(1, weight=1)

        self.var_vitesse = tk.IntVar(value=RATE_DEFAULT)
        self.var_volume = tk.IntVar(value=VOLUME_DEFAULT)
        self.var_hauteur = tk.IntVar(value=PITCH_DEFAULT)

        self.etiquette_vitesse = self._ajouter_curseur(
            reglages, 0, "Vitesse", self.var_vitesse, RATE_MIN, RATE_MAX, "mots/min"
        )
        self.etiquette_volume = self._ajouter_curseur(
            reglages, 1, "Volume", self.var_volume, VOLUME_MIN, VOLUME_MAX, "%"
        )
        self.curseur_hauteur, self.etiquette_hauteur = self._ajouter_curseur(
            reglages, 2, "Hauteur", self.var_hauteur, PITCH_MIN, PITCH_MAX, "", renvoyer_curseur=True
        )
        ligne += 1

        # --- 2. Écrire son texte --------------------------------------
        ttk.Label(cadre, text="2. Écrire ou coller son texte", font=("", 11, "bold")).grid(
            row=ligne, column=0, columnspan=3, sticky="w"
        )
        ligne += 1

        self.zone_texte = tk.Text(cadre, height=10, wrap="word", font=("", 11))
        self.zone_texte.grid(row=ligne, column=0, columnspan=3, sticky="nsew", pady=(6, 12))
        self.zone_texte.insert("1.0", TEXTE_EXEMPLE)
        cadre.rowconfigure(ligne, weight=1)
        ligne += 1

        # --- 3. Générer la voix ---------------------------------------
        boutons = ttk.Frame(cadre)
        boutons.grid(row=ligne, column=0, columnspan=3, sticky="ew")

        self.bouton_generer = ttk.Button(
            boutons, text="🔊 Générer la voix", command=self._generer
        )
        self.bouton_generer.pack(side="left")

        self.bouton_arreter = ttk.Button(
            boutons, text="■ Arrêter", command=self.manager.stop, state="disabled"
        )
        self.bouton_arreter.pack(side="left", padx=8)

        ttk.Button(boutons, text="💾 Enregistrer en WAV", command=self._enregistrer).pack(
            side="left"
        )
        ttk.Button(boutons, text="Effacer", command=self._effacer).pack(side="right")
        ligne += 1

        # --- Barre d'état ---------------------------------------------
        self.var_etat = tk.StringVar(value="Prêt.")
        ttk.Separator(cadre).grid(row=ligne, column=0, columnspan=3, sticky="ew", pady=(12, 6))
        ligne += 1
        ttk.Label(cadre, textvariable=self.var_etat, foreground="#555").grid(
            row=ligne, column=0, columnspan=3, sticky="w"
        )

    def _ajouter_curseur(
        self, parent, ligne, titre, variable, mini, maxi, unite, renvoyer_curseur=False
    ):
        ttk.Label(parent, text=f"{titre} :").grid(row=ligne, column=0, sticky="w", pady=4)
        etiquette = ttk.Label(parent, width=12, text=f"{variable.get()} {unite}".strip())

        def maj(valeur):
            variable.set(int(float(valeur)))
            etiquette.config(text=f"{variable.get()} {unite}".strip())
            self._appliquer_reglages()

        curseur = ttk.Scale(
            parent, from_=mini, to=maxi, orient="horizontal", command=maj
        )
        curseur.set(variable.get())
        curseur.grid(row=ligne, column=1, sticky="ew", padx=8)
        etiquette.grid(row=ligne, column=2, sticky="w")
        return (curseur, etiquette) if renvoyer_curseur else etiquette

    # ------------------------------------------------------------------
    # Voix
    # ------------------------------------------------------------------
    def _charger_voix(self) -> None:
        try:
            voix = self.manager.load_voices(french_only=self.var_fr.get())
        except EspeakError as exc:
            self._afficher_erreur(str(exc))
            return

        if not voix:
            self._afficher_erreur("Aucune voix eSpeak NG n'a été détectée.")
            return

        self._voix_affichees = voix
        self.combo_voix["values"] = [v.label for v in voix]

        courante = self.manager.voice
        index = next((i for i, v in enumerate(voix) if courante and v.identifier == courante.identifier), 0)
        self.combo_voix.current(index)
        self._voix_changee()
        self.var_etat.set(f"{len(voix)} voix détectée(s) — lecture 100 % hors ligne.")

    def _voix_changee(self, _event=None) -> None:
        index = self.combo_voix.current()
        if 0 <= index < len(self._voix_affichees):
            self.manager.set_voice(self._voix_affichees[index])

        # La hauteur n'est réglable que si la voix le permet (voix MBROLA exclues).
        etat = "normal" if self.manager.supports_pitch else "disabled"
        self.curseur_hauteur.state(["!disabled"] if etat == "normal" else ["disabled"])
        self.etiquette_hauteur.config(
            foreground="black" if etat == "normal" else "#999"
        )

    def _appliquer_reglages(self) -> None:
        self.manager.set_rate(self.var_vitesse.get())
        self.manager.set_volume(self.var_volume.get())
        self.manager.set_pitch(self.var_hauteur.get())

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _texte(self) -> str:
        return self.zone_texte.get("1.0", "end-1c")

    def _generer(self) -> None:
        self._appliquer_reglages()
        self.manager.speak(self._texte())

    def _enregistrer(self) -> None:
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer la voix",
            defaultextension=".wav",
            filetypes=[("Fichier audio WAV", "*.wav")],
        )
        if not chemin:
            return
        self._appliquer_reglages()
        self.var_etat.set("Enregistrement en cours…")
        self.manager.save_to_wav(self._texte(), chemin)

    def _effacer(self) -> None:
        self.zone_texte.delete("1.0", "end")
        self.zone_texte.focus_set()

    # ------------------------------------------------------------------
    # Retours du gestionnaire (toujours exécutés dans le fil graphique)
    # ------------------------------------------------------------------
    def _lecture_commencee(self) -> None:
        self.bouton_generer.config(state="disabled")
        self.bouton_arreter.config(state="normal")
        self.var_etat.set("Lecture en cours…")

    def _lecture_terminee(self, chemin: str | None = None) -> None:
        self.bouton_generer.config(state="normal")
        self.bouton_arreter.config(state="disabled")
        self.var_etat.set(f"Fichier enregistré : {chemin}" if chemin else "Prêt.")

    def _afficher_erreur(self, message: str) -> None:
        self.bouton_generer.config(state="normal")
        self.bouton_arreter.config(state="disabled")
        self.var_etat.set("Erreur.")
        messagebox.showerror("Vocalis", message)

    def _quitter(self) -> None:
        self.manager.stop()
        self.destroy()
