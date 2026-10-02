# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Photo Video Studio — Windows desktop app (CustomTkinter GUI) that turns a folder of photos into a
cinematic MP4 slideshow (ProShow Producer style): pick photos, pick style/effect/quality, hit
generate, get an MP4. UI strings and code comments are in Uzbek (Latin script, with a Latin→Cyrillic
transliterator built in). Not a git repo currently.

## Running

```bash
pip install -r requirements.txt
python app.py
```

Or double-click `run.bat` — it creates `.venv`, installs from `wheels/` (fully offline, no internet
needed) falling back to PyPI via `requirements.txt` if that fails, then launches `app.py`.

**Requires ffmpeg on PATH** (`winget install Gyan.FFmpeg`). The app checks for it on startup and
lets the user browse to `ffmpeg.exe` manually if not found (`SE.set_ffmpeg`).

No test suite, linter, or build/typecheck config exists in this repo.

## Building the standalone .exe

```bash
build_exe.bat
```

Runs PyInstaller (`--onefile --windowed`), bundling `fonts/` as data and `music`/`studio_engine` as
hidden imports → `dist\PhotoVideoStudio.exe`. ffmpeg is still an external requirement (not bundled).

## Architecture

Three-module pipeline, no framework/package structure — everything is flat, single-directory Python:

- **`app.py`** — CustomTkinter GUI (`App` class). Owns all UI state (`self.sel`, `self.mvar`,
  per-photo captions in `self.items`), builds a plain `dict` config, and hands it to
  `studio_engine.build_video()` on a background `threading.Thread` (GUI thread polls a
  `queue.Queue()` via `self.root.after(120, self._poll)` for progress/done/error messages — never
  call ffmpeg or PIL work directly on the GUI thread).
- **`studio_engine.py`** — the actual video engine and the single source of truth for what
  effects/styles exist. Pipeline inside `build_video()`: grade photos (numpy) → render caption PNGs
  → render title/outro cards (Pillow) → render per-photo scenes (Ken Burns zoom/pan + optional
  bloom/grain/vignette via ffmpeg `zoompan`/filters) → stitch all clips with ffmpeg `xfade`
  transitions → mux generated/user music with `-shortest`. Every stage writes intermediate files to
  a `tempfile.mkdtemp(prefix="pvs_")` work dir. `progress(pct, msg)` callback is threaded through the
  whole pipeline for the GUI progress bar.
- **`music.py`** — generates original royalty-free piano-bed audio (additive synthesis + convolution
  reverb, no external samples) for two moods (`warm`, `bright`) matching the two styles. Standalone
  runnable: `python music.py warm` writes a test wav.

### Effects are registries, not a plugin system

`GRADES`, `TRANSITIONS`, `STYLES` in `studio_engine.py` are the menus the GUI renders — adding an
entry there and one branch in `grade()` or `_trans_list()`'s `M` dict is the entire integration; the
GUI picks it up automatically. **See [EFFEKT_QOSHISH.md](EFFEKT_QOSHISH.md)** (Uzbek) for the exact
recipe for adding a new color grade, transition, or full style. `TRANS_UZ`/`GRADE_UZ` are the
Uzbek display labels shown in the GUI — every registry entry needs one.

Transitions map to ffmpeg's native `xfade` filter names (`fade`, `wipeleft`, `circleopen`, etc.) —
`_trans_list()` alternates between two ffmpeg transitions per logical transition type and always
forces the very first and last cut to `fade`.

### Style dict shape (`STYLES` in studio_engine.py)

Each style bundles: `grade` (default color grade), `card_bg` (`"dark"` or `"light"` — selects
`warm_gradient()`+bokeh vs `light_bg()` background for title/outro cards), `vignette`, `transition`
(default), `music` (`"warm"` or `"bright"` — picked up by `music.py`), `caption` style (`"glow"` or
`"halo"`), `col` (color palette dict), `fonts` (role→font-family key, resolved via `font()`/`_CAND`
against `fonts/*.pfb` first, then Windows/Linux system fonts, then Pillow's default).

### Config dict contract

`app.py:_base_cfg()` builds the dict `studio_engine.build_video()` expects. Keys use `"auto"` as a
sentinel meaning "inherit from the selected style" (e.g. `grade`, `transition_type`, `vignette`) —
resolved inside `build_video()` by checking against `st[...]` from `STYLES`. When adding a new
config knob, follow this same auto-fallback pattern rather than requiring the GUI to always pass an
explicit value.

### Preview vs. full render

`app.py:preview_sample()` builds the same config but caps it to 4 photos, 720p, short durations, and
`veryfast`/high-CRF — same `build_video()` path, just cheaper, written to a temp file and opened
immediately. Useful as the fast path when testing effect/style changes instead of a full render.

## Gotchas

- All ffmpeg calls go through `studio_engine._run()`, which resolves the literal string `"ffmpeg"` in
  argv[0] to the discovered/user-picked binary (`find_ffmpeg()`/`set_ffmpeg()`) — always build
  commands as `["ffmpeg", ...]` rather than hardcoding a path.
- `output/*.mp4`/`.mkv`/`.mov` and `*_namuna.mp4` (preview output) are gitignored; `fonts/` and
  `wheels/` are intentionally committed (required for offline operation).
- `_applog.txt`, `_diag.bat`, `_fixpip.bat` are ad hoc debug artifacts for diagnosing a local
  install/launch issue — not part of the app itself.
