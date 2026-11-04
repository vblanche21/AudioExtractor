import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "Audio Extractor 1.1"
VIDEO_TYPES = [
    ("Fichiers vidéo", "*.mkv *.mp4 *.avi *.mov *.webm *.m4v *.ts *.mts *.m2ts"),
    ("Tous les fichiers", "*.*"),
]


def subprocess_flags():
    """Hide console windows on Windows."""
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0


def find_binary(name):
    """
    Search executable:
    1) next to this script / executable
    2) in a 'ffmpeg' subfolder
    3) in PATH
    """
    candidates = []

    base_dir = Path(__file__).resolve().parent
    exe_name = f"{name}.exe" if os.name == "nt" else name

    # PyInstaller --onefile extracts bundled binaries next to __file__.
    candidates.append(base_dir / exe_name)
    # Also allow external binaries next to a frozen executable.
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / exe_name)
    candidates.append(base_dir / "ffmpeg" / exe_name)
    candidates.append(base_dir / "bin" / exe_name)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    found = shutil.which(name)
    return found


class AudioExtractorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x500")
        self.minsize(700, 450)

        self.ffmpeg = find_binary("ffmpeg")
        self.ffprobe = find_binary("ffprobe")

        self.input_file = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.track_var = tk.StringVar()
        self.format_var = tk.StringVar(value="Original (sans réencodage)")
        self.status_var = tk.StringVar(value="Prêt.")

        self.audio_streams = []
        self.is_working = False
        self._probed_input = None
        self._events = queue.Queue()

        self.create_widgets()
        # All Tk updates happen on the GUI thread. Worker threads only post events.
        self.after(100, self._poll_events)
        self.update_ffmpeg_status()

    def create_widgets(self):
        pad = {"padx": 10, "pady": 6}

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text="Extraire l'audio d'une vidéo", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", pady=(0, 10))

        # Input
        input_frame = ttk.LabelFrame(main, text="1. Vidéo source")
        input_frame.pack(fill="x", pady=(0, 8))

        row = ttk.Frame(input_frame)
        row.pack(fill="x", **pad)

        ttk.Entry(row, textvariable=self.input_file).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Parcourir…", command=self.choose_input).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="Analyser", command=self.detect_audio_tracks).pack(side="left", padx=(8, 0))

        # Track
        track_frame = ttk.LabelFrame(main, text="2. Piste audio")
        track_frame.pack(fill="x", pady=8)

        row = ttk.Frame(track_frame)
        row.pack(fill="x", **pad)

        self.track_combo = ttk.Combobox(
            row,
            textvariable=self.track_var,
            state="readonly",
            values=[]
        )
        self.track_combo.pack(fill="x", expand=True)

        # Output format
        format_frame = ttk.LabelFrame(main, text="3. Format de sortie")
        format_frame.pack(fill="x", pady=8)

        row = ttk.Frame(format_frame)
        row.pack(fill="x", **pad)

        self.format_combo = ttk.Combobox(
            row,
            textvariable=self.format_var,
            state="readonly",
            values=[
                "Original (sans réencodage)",
                "MP3 - haute qualité",
                "WAV - PCM",
                "FLAC - sans perte",
            ],
        )
        self.format_combo.pack(fill="x", expand=True)

        # Output folder
        output_frame = ttk.LabelFrame(main, text="4. Dossier de destination")
        output_frame.pack(fill="x", pady=8)

        row = ttk.Frame(output_frame)
        row.pack(fill="x", **pad)

        ttk.Entry(row, textvariable=self.output_folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Parcourir…", command=self.choose_output_folder).pack(side="left", padx=(8, 0))

        # Actions
        action_row = ttk.Frame(main)
        action_row.pack(fill="x", pady=(12, 4))

        self.extract_button = ttk.Button(
            action_row,
            text="Extraire l'audio",
            command=self.start_extraction
        )
        self.extract_button.pack(side="left")

        self.progress = ttk.Progressbar(action_row, mode="indeterminate", length=220)
        self.progress.pack(side="left", padx=12)

        ttk.Label(action_row, textvariable=self.status_var).pack(side="left", padx=4)

        # Log
        log_frame = ttk.LabelFrame(main, text="Informations")
        log_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.log_text = tk.Text(log_frame, height=8, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _poll_events(self):
        try:
            while True:
                kind, args = self._events.get_nowait()
                if kind == "probe_success":
                    self._populate_tracks(*args)
                elif kind == "probe_error":
                    self._probe_failed(*args)
                elif kind == "extract_success":
                    self._extract_success(*args)
                elif kind == "extract_error":
                    self._extract_failed(*args)
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def update_ffmpeg_status(self):
        if self.ffmpeg and self.ffprobe:
            self.log(f"FFmpeg détecté : {self.ffmpeg}")
            self.log(f"FFprobe détecté : {self.ffprobe}")
        else:
            self.log("FFmpeg/FFprobe non détecté.")
            self.log("Place ffmpeg.exe et ffprobe.exe dans le même dossier que ce programme,")
            self.log("dans un sous-dossier 'ffmpeg'/'bin', ou ajoute FFmpeg au PATH Windows.")

    def choose_input(self):
        filename = filedialog.askopenfilename(
            title="Sélectionner une vidéo",
            filetypes=VIDEO_TYPES
        )
        if not filename:
            return

        self.input_file.set(filename)
        self.output_folder.set(str(Path(filename).parent))
        self.detect_audio_tracks()

    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="Choisir le dossier de destination")
        if folder:
            self.output_folder.set(folder)

    def detect_audio_tracks(self):
        path = self.input_file.get().strip()
        if not path:
            return

        if not self.ffprobe:
            messagebox.showerror(
                "FFprobe introuvable",
                "FFprobe n'a pas été trouvé. Installe FFmpeg ou place ffprobe.exe "
                "à côté du programme."
            )
            return

        self.status_var.set("Analyse des pistes audio…")
        if not Path(path).is_file():
            messagebox.showwarning("Fichier introuvable", "Sélectionne une vidéo valide.")
            return

        self.track_combo["values"] = []
        self.track_var.set("")
        self.audio_streams = []
        self._probed_input = None
        self.extract_button.configure(state="disabled")
        self.output_folder.set(self.output_folder.get() or str(Path(path).parent))

        threading.Thread(target=self._probe_worker, args=(path,), daemon=True).start()

    def _probe_worker(self, path):
        cmd = [
            self.ffprobe,
            "-v", "error",
            "-select_streams", "a",
            "-show_entries",
            "stream=index,codec_name,channels,channel_layout:stream_tags=language,title",
            "-of", "json",
            path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess_flags(),
                check=True,
            )
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            self._events.put(("probe_success", (streams, path)))
        except Exception as exc:
            self._events.put(("probe_error", (str(exc), path)))

    def _populate_tracks(self, streams, path):
        # Ignore old asynchronous analysis results after another file was chosen.
        if self.input_file.get().strip() != path:
            return
        self.audio_streams = streams
        self._probed_input = path

        if not streams:
            self.status_var.set("Aucune piste audio détectée.")
            self.log("Aucune piste audio détectée dans le fichier.")
            return

        labels = []
        for n, stream in enumerate(streams):
            tags = stream.get("tags") or {}
            lang = tags.get("language", "inconnue")
            title = tags.get("title", "")
            codec = stream.get("codec_name", "?")
            channels = stream.get("channels", "?")
            index = stream.get("index", "?")

            label = f"Piste {n + 1} — {lang} — {codec} — {channels} canaux"
            if title:
                label += f" — {title}"
            label += f"  [stream {index}]"
            labels.append(label)

        self.track_combo["values"] = labels
        self.track_combo.current(0)
        self.extract_button.configure(state="normal")
        self.status_var.set(f"{len(streams)} piste(s) audio détectée(s).")

        self.log(f"{len(streams)} piste(s) audio trouvée(s) :")
        for label in labels:
            self.log("  " + label)

    def _probe_failed(self, error, path):
        if self.input_file.get().strip() != path:
            return
        self.status_var.set("Erreur d'analyse.")
        self.log("Erreur FFprobe : " + error)
        messagebox.showerror("Erreur", "Impossible d'analyser les pistes audio.")

    def build_output_path(self):
        input_path = Path(self.input_file.get())
        output_dir = Path(self.output_folder.get())

        selected_index = self.track_combo.current()
        track_no = selected_index + 1

        mode = self.format_var.get()
        if mode == "Original (sans réencodage)":
            ext = ".mka"
        elif mode.startswith("MP3"):
            ext = ".mp3"
        elif mode.startswith("WAV"):
            ext = ".wav"
        elif mode.startswith("FLAC"):
            ext = ".flac"
        else:
            ext = ".mka"

        base_name = input_path.stem
        suffix = "" if len(self.audio_streams) == 1 else f"_audio_{track_no}"
        output_path = output_dir / f"{base_name}{suffix}{ext}"

        # Avoid accidental overwrite.
        counter = 2
        original = output_path
        while output_path.exists():
            output_path = original.with_name(f"{original.stem}_{counter}{original.suffix}")
            counter += 1

        return output_path

    def start_extraction(self):
        if self.is_working:
            return

        input_path = self.input_file.get().strip()
        output_folder = self.output_folder.get().strip()

        if not self.ffmpeg:
            messagebox.showerror(
                "FFmpeg introuvable",
                "FFmpeg n'a pas été trouvé. Installe FFmpeg ou place ffmpeg.exe "
                "à côté du programme."
            )
            return

        if not input_path or not Path(input_path).is_file():
            messagebox.showwarning("Vidéo manquante", "Sélectionne d'abord une vidéo valide.")
            return

        if (not self.audio_streams or self.track_combo.current() < 0
                or self._probed_input != input_path):
            messagebox.showwarning("Piste manquante", "Aucune piste audio n'est sélectionnée.")
            return

        if not output_folder:
            messagebox.showwarning("Destination manquante", "Choisis un dossier de destination.")
            return

        try:
            Path(output_folder).mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Erreur", f"Impossible d'utiliser ce dossier :\n{exc}")
            return

        output_path = self.build_output_path()
        track_index = self.track_combo.current()
        mode = self.format_var.get()

        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-n",
            "-i", input_path,
            "-map", f"0:a:{track_index}",
            "-vn",
        ]

        if mode == "Original (sans réencodage)":
            cmd += ["-c:a", "copy"]
        elif mode.startswith("MP3"):
            # MP3 supports no more than two channels: downmix multichannel.
            cmd += ["-c:a", "libmp3lame", "-ac", "2", "-q:a", "2"]
        elif mode.startswith("WAV"):
            cmd += ["-c:a", "pcm_s16le"]
        elif mode.startswith("FLAC"):
            cmd += ["-c:a", "flac"]

        cmd.append(str(output_path))

        self.is_working = True
        self.extract_button.configure(state="disabled")
        self.progress.start(10)
        self.status_var.set("Extraction en cours…")
        self.log("")
        self.log(f"Extraction vers : {output_path}")

        threading.Thread(
            target=self._extract_worker,
            args=(cmd, output_path),
            daemon=True
        ).start()

    def _extract_worker(self, cmd, output_path):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess_flags(),
            )

            if result.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 0:
                self._events.put(("extract_success", (output_path,)))
            else:
                err = result.stderr[-5000:] if result.stderr else "Erreur FFmpeg inconnue."
                self._events.put(("extract_error", (err,)))
        except Exception as exc:
            self._events.put(("extract_error", (str(exc),)))

    def _extract_success(self, output_path):
        self.is_working = False
        self.progress.stop()
        self.extract_button.configure(state="normal")
        self.status_var.set("Extraction terminée.")
        self.log(f"Terminé : {output_path} ({output_path.stat().st_size / (1024 * 1024):.1f} Mo)")

        answer = messagebox.askyesno(
            "Extraction terminée",
            f"Le fichier audio a été créé :\n\n{output_path}\n\n"
            "Ouvrir le dossier de destination ?"
        )
        if answer:
            self.open_folder(output_path.parent)

    def _extract_failed(self, error):
        self.is_working = False
        self.progress.stop()
        self.extract_button.configure(state="normal")
        self.status_var.set("Échec de l'extraction.")
        self.log("Erreur FFmpeg :")
        self.log(error)
        messagebox.showerror(
            "Erreur",
            "L'extraction a échoué.\n\nConsulte la zone Informations pour le détail."
        )

    @staticmethod
    def open_folder(folder):
        try:
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception:
            pass


if __name__ == "__main__":
    app = AudioExtractorApp()
    app.mainloop()
