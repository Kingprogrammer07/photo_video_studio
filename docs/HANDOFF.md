# Photo Video Studio Handoff

Last updated: 2026-10-05

GitHub: https://github.com/Kingprogrammer07/photo_video_studio

## Product Direction

Photo Video Studio is becoming a simple but powerful Windows desktop studio for users around age 30-55. The product goal is: add photos, choose a beautiful template/background, optionally improve photos with AI/pro controls, and export a polished MP4 without needing Photoshop or a professional editor.

## Current Architecture

- `app.py` is the main CustomTkinter application. It now uses top-level tabs: `Slideshow`, `Fonlar/Shablonlar`, `AI Rasm Studio`, `Video Tools`, and `Sozlamalar`.
- `studio_engine.py` owns video rendering. It accepts enhanced photo paths, background/template layout fields, optional text flags, font presets, per-slide durations, motion preset lists, and optional per-slide motion settings, then renders title card, photo scenes, outro, music, and final MP4 through ffmpeg.
- `image_enhance.py` owns local enhancement, OpenAI prompt construction, AI cache keys, OpenAI cost estimates, economy input resizing, OpenAI image-edit integration, and OpenAI API key testing.
- `pvs_storage.py` owns AppData folders, settings, background import, template JSON, AI cache paths, AI usage history, and secure API key storage.
- `starter_pack.py` generates 8 procedural, copyright-safe backgrounds/templates and installs them into AppData once.
- `connectivity.py`, `updater.py`, `runtime_paths.py`, and `version.py` own online/offline status, GitHub Releases update checks, bundled runtime resource lookup, and app version metadata.
- `video_converter/src/video_converter/converter.py` remains the ffmpeg conversion backend; `app.py` imports it into the `Video Tools` tab.
- `scripts/build_release.ps1` builds a PyInstaller onedir release, bundles `ffmpeg.exe`, and compiles the Inno installer when Inno Setup is available.

## Persistent Data

Runtime data is outside the repo:

- `%APPDATA%\PhotoVideoStudio\settings.json`
- `%APPDATA%\PhotoVideoStudio\backgrounds\`
- `%APPDATA%\PhotoVideoStudio\templates\`
- `%APPDATA%\PhotoVideoStudio\templates\previews\`
- `%APPDATA%\PhotoVideoStudio\cache\ai\`
- `%APPDATA%\PhotoVideoStudio\ai_history.jsonl`

API keys are not stored in JSON. On Windows, `pvs_storage.py` uses Windows Credential Manager through `ctypes`; `keyring` is only an optional fallback.

## Important Behavior

- Original photos are never overwritten.
- Enhanced photos are cache files and are passed to `build_video()` through `enhanced_photos`.
- Background rendering uses `background_path`, `photo_layout`, `photo_scale`, and `photo_frame`.
- With a background, photo scenes are rendered as a stable background plus animated foreground photo/frame layer. Motion presets include `auto`, `still`, `zoom_in`, `zoom_out`, `tiny_to_big`, `dramatic_zoom`, `left_to_center`, `right_to_center`, `slow_pan_left`, `slow_pan_right`, and `bottom_to_center`.
- Motion rendering deliberately rounds animated coordinates and uses even-sized scaled layers with Lanczos accurate rounding. HD 60fps exports render motion at 2x internal resolution and downscale to final size to reduce zoom shimmer during photo growth.
- `tiny_to_big` now defaults to a gentler `0.45 -> 1.10` scale and slower easing. Users can adjust start scale, end scale, motion speed, and X/Y drift globally or per selected slide.
- `build_video(config)` accepts `photo_durations`, `photo_motions`, and `photo_motion_settings`. Missing or invalid durations fall back to global `photo_duration`; unknown motion presets fall back to `auto`; invalid motion setting values are clamped.
- `build_video(config)` accepts `text_enabled`, `show_title_card`, `show_outro_card`, `show_captions`, and `font_preset`. When title/outro are disabled, those clips are not rendered; one-clip videos mux without xfade.
- User-selected music is looped during final muxing so short audio files do not cut the video before later photos appear.
- Slideshow live preview is debounced and uses a lightweight animated PIL loop for motion/effect visibility. The `Aniq ko'rish` button renders a more faithful still frame in a worker thread.
- The selected slide duration can be entered directly in the `Ushbu slide sekund` field after turning off `Global vaqtni ishlatish`.
- AI Studio supports free local enhancement plus OpenAI enhancement. Sliders and presets build either local Pillow adjustments or an OpenAI edit prompt; before/after shows the latest cached result when available.
- OpenAI default quality for new installs is `low`. Batch OpenAI enhancement shows an estimated uncached cost before sending photos; cache hits cost `$0.00` in the app estimate.
- Each AI attempt is appended to `ai_history.jsonl` with provider, model, quality, preset, photo path/name, cache hit, status, estimated cost, output path, and sanitized error text. API keys and prompts are not logged.
- Switching Lotin/Kiril rebuilds the UI but restores selected tab, selected photo, captions, enhanced paths, per-slide durations, and motion controls after idle.
- Starter pack installation is tracked in `settings.json` with `starter_pack_version`; API keys are never stored there.
- Background favorites are stored as path strings in `settings.json`; background image files remain under AppData.
- Slideshow render, AI jobs, and Video Tools conversion all support cancellation. Render cancellation raises `studio_engine.CancelledError`; converter cancellation returns return code `-1`.
- Drag-and-drop is optional: it only activates when `tkinterdnd2` is importable and the Tk root exposes DnD methods. The file picker is the supported fallback.
- Runtime ffmpeg lookup prefers bundled `ffmpeg\bin\ffmpeg.exe`, then falls back to `PATH`.
- Installer builds are per-user under `%LOCALAPPDATA%\Programs\Photo Video Studio` and require internet before install; after install, render/convert works offline.
- App updates use GitHub Releases latest release; the app downloads the setup file and lets the user run it manually.
- OpenAI photo enhance requires a saved API key and explicit user consent because photos are sent to a cloud API.
- OpenAI image edits use `/v1/images/edits`, multipart field `image`, `output_format=jpeg`, `quality`, `size=auto`, and the model from settings. Current docs return base64 in `data[0].b64_json`; the request no longer sends `response_format`. Large input photos are temporarily resized for economy before upload; originals are not modified.
- Real OpenAI image enhancement still needs manual validation with a live key; use `docs/OPENAI_MANUAL_TEST.md`.

## Verification Run

Latest checks run successfully:

```powershell
python -m py_compile app.py studio_engine.py image_enhance.py pvs_storage.py starter_pack.py connectivity.py runtime_paths.py updater.py version.py video_converter\src\video_converter\converter.py
$env:PYTHONPATH="C:\Users\Admin\Desktop\photo_video_studio\video_converter\src"; python -m pytest tests video_converter\tests
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_release.ps1 -SkipInstaller
```

Result: `39 passed` for the pytest suite. PyInstaller onedir build completed earlier and bundled ffmpeg was copied.

Also verified real ffmpeg smoke renders with temporary photos/backgrounds after cancel-aware, motion, and text-toggle changes. The latest smoke covered short user audio looping through all slides, custom `tiny_to_big` motion at 30fps, regular background/fonsiz 60fps motion exports, and supersampled background/fonsiz 60fps motion exports in `%TEMP%`.

## Git Status

- Local branch: `main`
- Remote: `origin` -> `https://github.com/Kingprogrammer07/photo_video_studio.git`
- First public push completed from commit `2d0e325`.
