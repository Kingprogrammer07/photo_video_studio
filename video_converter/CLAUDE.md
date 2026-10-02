# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Desktop GUI video converter for Windows. Tkinter front end, ffmpeg does the actual encoding via subprocess. No web server, no bundled ffmpeg binary — it must already be on PATH.

## Commands

Setup (from repo root):
```
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Run the app:
```
python -m video_converter
```

Run tests:
```
pytest
```

Run a single test:
```
pytest tests/test_converter.py::test_probe_duration_seconds_parses_hms
```

## Architecture

Src-layout package under `src/video_converter/`:

- `converter.py` — all ffmpeg interaction lives here.
  - `convert()` shells out to `ffmpeg -i <in> <extra_args> -progress pipe:1 -nostats <out>` and parses stdout/stderr concurrently on two threads: one drains `-progress` key=value lines from stdout for `out_time_ms` (progress), the other drains stderr for the `Duration:` banner (used to turn elapsed time into a 0.0-1.0 fraction) and keeps the tail for error reporting. Reading both streams concurrently is required — reading only one risks a full pipe buffer deadlocking the subprocess on longer conversions. `find_ffmpeg()` resolves the binary via `shutil.which` and raises `FfmpegNotFoundError` if missing.
  - `build_conversion_args(output_format, resolution=, fps=, quality=)` builds the `extra_args` list for `convert()` — this is where format/resolution/fps/quality turns into actual ffmpeg flags. Any input format ffmpeg can demux works as input (the GUI file picker has no extension filter); this function only controls the *output* side.
    - Resolution (`RESOLUTIONS` dict, label → target height) is applied as `scale=-2:<height>:flags=lanczos` — the `-2` auto-derives width to preserve aspect ratio and rounds to even, which H.264/VP9 require. `None`/"Original" skips the filter entirely (no re-scale).
    - Frame rate (`FRAME_RATES` dict) is a plain `fps=<n>` filter (frame duplicate/drop, not motion-interpolated).
    - Quality (`QUALITY_PRESETS`) maps to per-codec settings: CRF+preset for libx264 (`_X264_QUALITY`), CRF for libvpx-vp9 in constant-quality mode (`_VP9_CRF`, requires `-b:v 0` alongside `-crf`), `-q:a` for libmp3lame (`_MP3_QUALITY`), and palette size for GIF (`_GIF_MAX_COLORS`).
    - Container-specific gotchas baked in here: **AVI output uses libmp3lame audio, not AAC** — ffmpeg happily muxes AAC into AVI but many players only recognize MP3/PCM/AC3 audio in that legacy container. GIF uses a `-filter_complex` palettegen/paletteuse two-pass-in-one-command chain (not `-vf`) for non-banded output — don't add a plain `-vf` alongside it. `mp4`/`mov` get `-movflags +faststart`. mp3/wav outputs are audio-only (`-vn`) and ignore resolution/fps entirely.
- `gui.py` — `ConverterApp` (Tkinter/ttk). Runs `convert()` on a background thread so the UI stays responsive; progress/completion callbacks marshal back to the main thread via `root.after(0, ...)` since Tkinter isn't thread-safe. Format/resolution/fps/quality comboboxes feed straight into `build_conversion_args()` when Convert is pressed. `_on_format_changed` disables (and resets to "Original") the resolution/fps comboboxes when an audio-only format is selected, since those don't apply. Output defaults to `<input_stem>.<format>` in the input's folder unless a different output folder is picked, and conversion is blocked if that would overwrite the input file.
- `__main__.py` — `python -m video_converter` entry point, just calls `gui.main()`.

When adding a new output format: add it to `SUPPORTED_FORMATS`, decide whether it's audio-only (add to `AUDIO_ONLY_FORMATS`) or video, and extend `build_conversion_args()` — check codec/container compatibility empirically (`ffprobe` the real output) rather than assuming a codec that works in one container works in another; AVI+AAC was a real bug found exactly that way (see git history / smoke tests in this session).

## Notes

- `MAIN COMPOSITION_1.avi` in the repo root is a large local sample file for manual testing, not project source — it's gitignored along with other video extensions dropped in this folder.
- ffmpeg must be present on PATH; there is no vendoring/download step. `find_ffmpeg()` is the single choke point for that check.
- When changing `build_conversion_args()`, unit tests only check the built argv list — they can't catch codec/container mismatches. Do a real `convert()` + `ffprobe` smoke test (short `-t 2` clip) for anything touching codec/container pairing.
