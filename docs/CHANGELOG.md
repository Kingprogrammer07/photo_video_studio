# Changelog

## 2026-10-02

### Added

- Added Polish Pack starter templates through `starter_pack.py`: 8 procedural, copyright-safe backgrounds and matching JSON templates installed into AppData once.
- Added background/template management: preview thumbnails, rename, delete, favorite backgrounds, and starter pack reinstall.
- Added optional drag-and-drop photo import when `tkinterdnd2` is available; the normal file picker remains the fallback.
- Added cancel flow for slideshow render, AI enhancement jobs, and Video Tools conversion.
- Added draggable Canvas-based AI before/after compare view with a vertical divider and labels.
- Added `docs/OPENAI_MANUAL_TEST.md` for real API-key validation.
- Created vNext tabbed app shell with `Slideshow`, `Fonlar/Shablonlar`, `AI Rasm Studio`, `Video Tools`, and `Sozlamalar`.
- Added AppData-backed settings, custom background library, template JSON storage, and AI cache directories.
- Added secure API key storage using Windows Credential Manager, with optional keyring fallback.
- Added local professional photo enhancement controls: brightness, contrast, saturation, warmth, sharpness, denoise, upscale, and face-safe restore.
- Added OpenAI image-edit enhance adapter, OpenAI key test, and cloud-AI consent flow.
- Added before/after AI preview slider.
- Added background-based scene composition with photo layout, scale, frame, and shadow.
- Integrated the existing video converter backend into the main app.
- Added vNext unit tests under `tests/`.
- Added project docs: handoff, process, tasks, and changelog.
- Added repository hygiene rules for local diagnostics, runtime data, and generated media.

### Changed

- Extended `pvs_storage.py` with metadata-aware background/template operations and starter-pack install tracking.
- Made `studio_engine.build_video()` and ffmpeg helpers cancel-aware through an optional `cancel_event`.
- Made `video_converter.converter.convert()` cancel-aware and return `ConversionResult(False, -1, "Bekor qilindi")` on cancellation.
- Replaced the old single-screen `app.py` with a larger tabbed CustomTkinter app.
- Extended `studio_engine.build_video()` to accept background and enhanced-photo config fields.
- Updated `build_exe.bat` hidden imports for new modules.
- Corrected OpenAI image-edit payload to use the official `image` form field and request base64 output.

### Fixed

- Guarded short clip fade-out timing so ffmpeg does not receive negative fade start values.

### Verification

- `python -m py_compile app.py studio_engine.py image_enhance.py pvs_storage.py starter_pack.py video_converter\src\video_converter\converter.py`
- `$env:PYTHONPATH="C:\Users\Admin\Desktop\photo_video_studio\video_converter\src"; python -m pytest tests video_converter\tests`
- Result: `24 passed`.
- Real ffmpeg smoke render with temporary images/background completed successfully after cancel-aware ffmpeg changes.
