# Changelog

## 2026-10-02

### Added

- Added Polish Pack starter templates through `starter_pack.py`: 8 procedural, copyright-safe backgrounds and matching JSON templates installed into AppData once.
- Added background/template management: preview thumbnails, rename, delete, favorite backgrounds, and starter pack reinstall.
- Added optional drag-and-drop photo import when `tkinterdnd2` is available; the normal file picker remains the fallback.
- Added cancel flow for slideshow render, AI enhancement jobs, and Video Tools conversion.
- Added draggable Canvas-based AI before/after compare view with a vertical divider and labels.
- Added `docs/OPENAI_MANUAL_TEST.md` for real API-key validation.
- Added Windows release packaging flow with PyInstaller onedir build, bundled `ffmpeg.exe`, Inno Setup config, and GitHub Releases publish helper.
- Added app version metadata, online/offline status indicator, OpenAI offline warnings, and manual update check/download through GitHub Releases.
- Added fast debounced slideshow preview updates plus an `Aniq ko'rish` button for heavier preview frames.
- Added in-memory AI Professional preview rendering through `enhance_image(..., preview_mode=True)` so sliders no longer write temp JPGs on every move.
- Added ProShow-style motion presets: still, zoom in/out, tiny-to-big, dramatic zoom, side/bottom-to-center, and slow pans.
- Added per-slide duration overrides with row badges such as `[6.0s]`.
- Added `photo_durations` and `photo_motions` render config support.
- Added text controls for optional title card, per-photo captions, and outro card; fresh projects now start text-off.
- Added text template and font preset fields to templates and starter pack payloads.
- Added lightweight animated preview frames for motion, zoom strength, vignette, bloom, and grain.
- Added 2-column template cards with larger previews in `Fonlar/Shablonlar`.
- Added OpenAI-first AI Studio presets and prompt building from professional sliders.
- Added simple motion controls for start scale, end scale, speed, and X/Y drift, with global and per-slide override support.
- Added `photo_motion_settings` render config support.
- Added AppData-backed AI usage history (`ai_history.jsonl`) with estimated cost, cache hit, status, output path, and sanitized errors.
- Added AI cost summary, recent history view, CSV export, and history clear controls in Settings.
- Added OpenAI batch cost confirmation and cache-aware cost estimates.
- Added user-facing free local enhancement buttons for selected/all photos.
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
- Updated ffmpeg discovery to prefer bundled installer/runtime paths before falling back to system `PATH`.
- Replaced old onefile `build_exe.bat` with a wrapper around `scripts/build_release.ps1`.
- Background scenes now render as stable backgrounds with an animated foreground photo/frame layer.
- `studio_engine.build_video()` can skip title/outro/caption text clips and now handles single-clip final muxing without xfade.
- Language switching now snapshots and restores selected photos, captions, AI paths, per-slide settings, selected tab, and preview state after UI rebuild.
- OpenAI image-edit requests now follow current Images API behavior by reading `data[0].b64_json` without sending the deprecated `response_format` field.
- `tiny_to_big` motion now starts at `0.45` scale and ends at `1.10` scale by default, with slower easing.
- New OpenAI installs default to `low` quality for lower cost.
- OpenAI input photos are temporarily resized for economy before upload; original files are not changed.
- Replaced the old single-screen `app.py` with a larger tabbed CustomTkinter app.
- Extended `studio_engine.build_video()` to accept background and enhanced-photo config fields.
- Updated `build_exe.bat` hidden imports for new modules.
- Corrected OpenAI image-edit payload to use the official `image` form field and base64 output.

### Fixed

- Guarded short clip fade-out timing so ffmpeg does not receive negative fade start values.

### Verification

- `python -m py_compile app.py studio_engine.py image_enhance.py pvs_storage.py starter_pack.py connectivity.py runtime_paths.py updater.py version.py video_converter\src\video_converter\converter.py`
- `$env:PYTHONPATH="C:\Users\Admin\Desktop\photo_video_studio\video_converter\src"; python -m pytest tests video_converter\tests`
- Result: `35 passed`.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_release.ps1 -SkipInstaller`
- Result: PyInstaller onedir build completed; `dist\PhotoVideoStudio\PhotoVideoStudio.exe` and `dist\PhotoVideoStudio\ffmpeg\bin\ffmpeg.exe` exist.
- Real ffmpeg smoke render with temporary images/background completed successfully after cancel-aware ffmpeg changes.
- Real ffmpeg smoke render with temporary images/background completed successfully for `left_to_center` motion and per-slide duration.
- Real ffmpeg smoke renders completed for matnsiz title/outro-off output and matnli background-motion output.
- Real ffmpeg smoke render completed for custom `tiny_to_big` motion settings with background output in `%TEMP%`.
