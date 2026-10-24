"""Interface Tkinter accessible. Toutes les opérations Tk sont sur le thread UI."""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tts.common import (AudioSettings, PITCH_DEFAULT, PITCH_MAX, PITCH_MIN,
                        RATE_DEFAULT, RATE_MAX, RATE_MIN, VOLUME_DEFAULT,
                        VOLUME_MAX, VOLUME_MIN, VocalisError)
from tts.manager import Event, TTSManager


class VocalisApp(tk.Tk):
    def __init__(self, manager: TTSManager) -> None:
        super().__init__()
        self.manager = manager
        self.title("Vocalis — synthèse vocale hors ligne")
        self.geometry("760x570")
        self.minsize(640, 500)
        self._voices = []
        self._closed = False
        self._build()
        self._load_voices()
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self.after(100, self._poll_events)

    def _build(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(4, weight=1)

        ttk.Label(root, text="1. Choisir une voix", font=("", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(root, text="Voix :").grid(row=1, column=0, sticky="w")
        self.combo = ttk.Combobox(root, state="readonly", width=42)
        self.combo.grid(row=1, column=1, sticky="ew", padx=8)
        self.combo.bind("<<ComboboxSelected>>", self._voice_changed)
        self.french = tk.BooleanVar(value=True)
        ttk.Checkbutton(root, text="Voix françaises", variable=self.french,
                        command=self._load_voices).grid(row=1, column=2)

        settings = ttk.LabelFrame(root, text="Réglages", padding=10)
        settings.grid(row=2, column=0, columnspan=3, sticky="ew", pady=14)
        settings.columnconfigure(1, weight=1)
        self.rate = tk.IntVar(value=RATE_DEFAULT)
        self.volume = tk.IntVar(value=VOLUME_DEFAULT)
        self.pitch = tk.IntVar(value=PITCH_DEFAULT)
        self._slider(settings, 0, "Vitesse", self.rate, RATE_MIN, RATE_MAX, "mots/min")
        self._slider(settings, 1, "Volume", self.volume, VOLUME_MIN, VOLUME_MAX, "%")
        self.pitch_slider = self._slider(
            settings, 2, "Hauteur", self.pitch, PITCH_MIN, PITCH_MAX, "")

        ttk.Label(root, text="2. Saisir ou coller le texte", font=("", 11, "bold")).grid(
            row=3, column=0, columnspan=3, sticky="w")
        self.text = tk.Text(root, height=10, wrap="word", undo=True, font=("", 11))
        self.text.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(7, 12))
        self.text.insert("1.0", "Bonjour, ceci est un test de Vocalis.")

        buttons = ttk.Frame(root)
        buttons.grid(row=5, column=0, columnspan=3, sticky="ew")
        self.speak_button = ttk.Button(buttons, text="🔊 Lire", command=self._speak)
        self.speak_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="■ Arrêter", state="disabled",
                                      command=self._stop)
        self.stop_button.pack(side="left", padx=8)
        self.save_button = ttk.Button(buttons, text="💾 Enregistrer WAV", command=self._save)
        self.save_button.pack(side="left")
        ttk.Button(buttons, text="Effacer", command=self._clear).pack(side="right")
        self.status = tk.StringVar(value="Prêt. Aucun texte envoyé sur Internet.")
        ttk.Separator(root).grid(row=6, column=0, columnspan=3, sticky="ew", pady=(12, 8))
        ttk.Label(root, textvariable=self.status, wraplength=710).grid(
            row=7, column=0, columnspan=3, sticky="w")

    def _slider(self, parent: ttk.Frame, row: int, name: str,
                variable: tk.IntVar, minimum: int, maximum: int,
                unit: str) -> ttk.Scale:
        ttk.Label(parent, text=name + " :").grid(row=row, column=0, sticky="w")
        output = ttk.Label(parent, width=16)
        def changed(value: str) -> None:
            variable.set(round(float(value)))
            output.config(text=f"{variable.get()} {unit}".strip())
        slider = ttk.Scale(parent, from_=minimum, to=maximum,
                           orient="horizontal", command=changed)
        slider.set(variable.get())
        slider.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        output.grid(row=row, column=2, sticky="w")
        changed(str(variable.get()))
        return slider

    def _load_voices(self) -> None:
        self._voices = self.manager.list_voices(french_only=self.french.get())
        current = self.combo.get()
        self.combo["values"] = [v.label for v in self._voices]
        index = next((i for i, voice in enumerate(self._voices)
                      if voice.label == current), 0)
        if self._voices:
            self.combo.current(index)
            self._voice_changed()
        else:
            self.status.set("Aucune voix détectée.")

    def _voice_changed(self, _event: object = None) -> None:
        index = self.combo.current()
        if 0 <= index < len(self._voices):
            self.pitch_slider.state(["!disabled"] if self._voices[index].supports_pitch
                                    else ["disabled"])

    def _request(self, operation: str, filename: str | None = None) -> None:
        try:
            index = self.combo.current()
            if not 0 <= index < len(self._voices):
                raise VocalisError("Sélectionnez une voix.")
            voice = self._voices[index]
            settings = AudioSettings(self.rate.get(), self.volume.get(), self.pitch.get())
            text = self.text.get("1.0", "end-1c")
            if operation == "speak":
                self.manager.speak(text, voice.identifier, settings)
            else:
                assert filename is not None
                self.manager.save_to_wav(text, voice.identifier, settings, filename)
        except VocalisError as exc:
            self._error(str(exc))

    def _speak(self) -> None:
        self._request("speak")

    def _save(self) -> None:
        if self.manager.busy:
            self.status.set("Une opération est déjà en cours.")
            return
        filename = filedialog.asksaveasfilename(
            title="Enregistrer en WAV", defaultextension=".wav",
            filetypes=[("Audio WAV", "*.wav")], confirmoverwrite=True)
        if filename:
            self._request("save", filename)

    def _stop(self) -> None:
        self.manager.cancel()
        self.status.set("Arrêt demandé…")
        self.stop_button.config(state="disabled")

    def _clear(self) -> None:
        self.text.delete("1.0", "end")
        self.text.focus_set()

    def _poll_events(self) -> None:
        if self._closed:
            return
        try:
            while True:
                event = self.manager.events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _handle_event(self, event: Event) -> None:
        if event.kind == "started":
            self.speak_button.config(state="disabled")
            self.save_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.status.set("Lecture en cours…" if event.message == "speak"
                            else "Enregistrement en cours…")
            return
        self.speak_button.config(state="normal")
        self.save_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if event.kind == "saved":
            self.status.set(f"WAV enregistré : {event.message}")
        elif event.kind == "finished":
            self.status.set("Lecture terminée.")
        elif event.kind == "stopped":
            self.status.set("Opération interrompue.")
        elif event.kind == "error":
            self._error(event.message)

    def _error(self, message: str) -> None:
        self.status.set("Erreur : " + message)
        messagebox.showerror("Vocalis", message)

    def _quit(self) -> None:
        self._closed = True
        self.manager.shutdown()
        self.destroy()
