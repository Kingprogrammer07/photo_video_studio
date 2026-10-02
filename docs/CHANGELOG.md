# Changelog

## 2026-10-02

### Added

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

- Replaced the old single-screen `app.py` with a larger tabbed CustomTkinter app.
- Extended `studio_engine.build_video()` to accept background and enhanced-photo config fields.
- Updated `build_exe.bat` hidden imports for new modules.
- Corrected OpenAI image-edit payload to use the official `image` form field and request base64 output.

### Fixed

- Guarded short clip fade-out timing so ffmpeg does not receive negative fade start values.

### Verification

- `python -m py_compile app.py studio_engine.py image_enhance.py pvs_storage.py video_converter\src\video_converter\converter.py`
- `$env:PYTHONPATH="C:\Users\Admin\Desktop\photo_video_studio\video_converter\src"; python -m pytest tests video_converter\tests`
- Result: `20 passed`.
- Real ffmpeg smoke render with temporary images/background completed successfully.
