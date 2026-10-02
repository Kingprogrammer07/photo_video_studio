"""Tkinter desktop GUI for the ffmpeg-backed video converter."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import BOTH, StringVar, Tk, filedialog, messagebox
from tkinter import ttk

from .converter import (
    AUDIO_ONLY_FORMATS,
    FRAME_RATES,
    QUALITY_PRESETS,
    RESOLUTIONS,
    SUPPORTED_FORMATS,
    FfmpegNotFoundError,
    build_conversion_args,
    convert,
)


class ConverterApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title("Video Converter")
        root.geometry("560x400")
        root.resizable(False, False)

        self.input_path: Path | None = None
        self.output_dir: Path | None = None
        self.format_var = StringVar(value=SUPPORTED_FORMATS[0])
        self.resolution_var = StringVar(value="Original")
        self.fps_var = StringVar(value="Original")
        self.quality_var = StringVar(value="Balanced")
        self.status_var = StringVar(value="Pick a file to convert.")

        self._build_layout()

    def _build_layout(self) -> None:
        pad = {"padx": 12, "pady": 8}

        frame = ttk.Frame(self.root)
        frame.pack(fill=BOTH, expand=True)

        self.input_label = ttk.Label(frame, text="No file selected", anchor="w")
        self.input_label.grid(row=0, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Button(frame, text="Choose file...", command=self._choose_input).grid(
            row=0, column=2, **pad
        )

        ttk.Label(frame, text="Output format:").grid(row=1, column=0, sticky="w", **pad)
        self.format_menu = ttk.Combobox(
            frame, textvariable=self.format_var, values=SUPPORTED_FORMATS, state="readonly"
        )
        self.format_menu.grid(row=1, column=1, sticky="ew", **pad)
        self.format_menu.bind("<<ComboboxSelected>>", self._on_format_changed)

        ttk.Label(frame, text="Resolution:").grid(row=2, column=0, sticky="w", **pad)
        self.resolution_menu = ttk.Combobox(
            frame,
            textvariable=self.resolution_var,
            values=list(RESOLUTIONS.keys()),
            state="readonly",
        )
        self.resolution_menu.grid(row=2, column=1, sticky="ew", **pad)

        ttk.Label(frame, text="Frame rate:").grid(row=3, column=0, sticky="w", **pad)
        self.fps_menu = ttk.Combobox(
            frame, textvariable=self.fps_var, values=list(FRAME_RATES.keys()), state="readonly"
        )
        self.fps_menu.grid(row=3, column=1, sticky="ew", **pad)

        ttk.Label(frame, text="Quality:").grid(row=4, column=0, sticky="w", **pad)
        self.quality_menu = ttk.Combobox(
            frame, textvariable=self.quality_var, values=QUALITY_PRESETS, state="readonly"
        )
        self.quality_menu.grid(row=4, column=1, sticky="ew", **pad)

        self.output_label = ttk.Label(frame, text="Output folder: same as input", anchor="w")
        self.output_label.grid(row=5, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Button(frame, text="Choose folder...", command=self._choose_output_dir).grid(
            row=5, column=2, **pad
        )

        self.convert_button = ttk.Button(frame, text="Convert", command=self._start_conversion)
        self.convert_button.grid(row=6, column=0, columnspan=3, sticky="ew", **pad)

        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=1.0)
        self.progress.grid(row=7, column=0, columnspan=3, sticky="ew", **pad)

        self.status_label = ttk.Label(frame, textvariable=self.status_var, anchor="w")
        self.status_label.grid(row=8, column=0, columnspan=3, sticky="ew", **pad)

        frame.columnconfigure(1, weight=1)

    def _on_format_changed(self, _event=None) -> None:
        is_audio_only = self.format_var.get() in AUDIO_ONLY_FORMATS
        state = "disabled" if is_audio_only else "readonly"
        self.resolution_menu.config(state=state)
        self.fps_menu.config(state=state)
        if is_audio_only:
            self.resolution_var.set("Original")
            self.fps_var.set("Original")

    def _choose_input(self) -> None:
        selected = filedialog.askopenfilename(title="Choose a video file")
        if not selected:
            return
        self.input_path = Path(selected)
        self.input_label.config(text=str(self.input_path))
        self.status_var.set("Ready to convert.")

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder")
        if not selected:
            return
        self.output_dir = Path(selected)
        self.output_label.config(text=f"Output folder: {self.output_dir}")

    def _start_conversion(self) -> None:
        if self.input_path is None:
            messagebox.showwarning("No file", "Choose a file to convert first.")
            return

        out_dir = self.output_dir or self.input_path.parent
        out_format = self.format_var.get()
        output_path = out_dir / f"{self.input_path.stem}.{out_format}"

        if output_path == self.input_path:
            messagebox.showwarning("Same file", "Output would overwrite the input file.")
            return

        extra_args = build_conversion_args(
            out_format,
            resolution=RESOLUTIONS[self.resolution_var.get()],
            fps=FRAME_RATES[self.fps_var.get()],
            quality=self.quality_var.get(),
        )

        self.convert_button.config(state="disabled")
        self.progress["value"] = 0.0
        self.status_var.set("Converting...")

        thread = threading.Thread(
            target=self._run_conversion,
            args=(self.input_path, output_path, extra_args),
            daemon=True,
        )
        thread.start()

    def _run_conversion(
        self, input_path: Path, output_path: Path, extra_args: list[str]
    ) -> None:
        try:
            result = convert(
                input_path,
                output_path,
                on_progress=lambda frac: self.root.after(0, self._set_progress, frac),
                extra_args=extra_args,
            )
        except FfmpegNotFoundError as exc:
            self.root.after(0, self._on_error, str(exc))
            return

        self.root.after(0, self._on_done, result, output_path)

    def _set_progress(self, fraction: float) -> None:
        self.progress["value"] = fraction
        self.status_var.set(f"Converting... {fraction * 100:.0f}%")

    def _on_done(self, result, output_path: Path) -> None:
        self.convert_button.config(state="normal")
        if result.success:
            self.status_var.set(f"Done: {output_path}")
        else:
            self.status_var.set("Conversion failed.")
            messagebox.showerror("Conversion failed", result.stderr_tail or "Unknown error")

    def _on_error(self, message: str) -> None:
        self.convert_button.config(state="normal")
        self.status_var.set("ffmpeg not found.")
        messagebox.showerror("ffmpeg not found", message)


def main() -> None:
    root = Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
