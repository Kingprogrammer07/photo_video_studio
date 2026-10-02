# Photo Video Studio Handoff

Last updated: 2026-10-02

GitHub: https://github.com/Kingprogrammer07/photo_video_studio

## Product Direction

Photo Video Studio is becoming a simple but powerful Windows desktop studio for users around age 30-55. The product goal is: add photos, choose a beautiful template/background, optionally improve photos with AI/pro controls, and export a polished MP4 without needing Photoshop or a professional editor.

## Current Architecture

- `app.py` is the main CustomTkinter application. It now uses top-level tabs: `Slideshow`, `Fonlar/Shablonlar`, `AI Rasm Studio`, `Video Tools`, and `Sozlamalar`.
- `studio_engine.py` owns video rendering. It accepts enhanced photo paths and optional background/template layout fields, then renders title card, photo scenes, outro, music, and final MP4 through ffmpeg.
- `image_enhance.py` owns local photo enhancement, AI cache keys, OpenAI image-edit integration, and OpenAI API key testing.
- `pvs_storage.py` owns AppData folders, settings, background import, template JSON, AI cache paths, and secure API key storage.
- `starter_pack.py` generates 8 procedural, copyright-safe backgrounds/templates and installs them into AppData once.
- `video_converter/src/video_converter/converter.py` remains the ffmpeg conversion backend; `app.py` imports it into the `Video Tools` tab.

## Persistent Data

Runtime data is outside the repo:

- `%APPDATA%\PhotoVideoStudio\settings.json`
- `%APPDATA%\PhotoVideoStudio\backgrounds\`
- `%APPDATA%\PhotoVideoStudio\templates\`
- `%APPDATA%\PhotoVideoStudio\templates\previews\`
- `%APPDATA%\PhotoVideoStudio\cache\ai\`

API keys are not stored in JSON. On Windows, `pvs_storage.py` uses Windows Credential Manager through `ctypes`; `keyring` is only an optional fallback.

## Important Behavior

- Original photos are never overwritten.
- Enhanced photos are cache files and are passed to `build_video()` through `enhanced_photos`.
- Background rendering uses `background_path`, `photo_layout`, `photo_scale`, and `photo_frame`.
- With a background, photo scenes are rendered as layered static scenes so the background stays stable.
- Starter pack installation is tracked in `settings.json` with `starter_pack_version`; API keys are never stored there.
- Background favorites are stored as path strings in `settings.json`; background image files remain under AppData.
- Slideshow render, AI jobs, and Video Tools conversion all support cancellation. Render cancellation raises `studio_engine.CancelledError`; converter cancellation returns return code `-1`.
- Drag-and-drop is optional: it only activates when `tkinterdnd2` is importable and the Tk root exposes DnD methods. The file picker is the supported fallback.
- OpenAI photo enhance requires a saved API key and explicit user consent because photos are sent to a cloud API.
- OpenAI image edits use `/v1/images/edits`, multipart field `image`, `response_format=b64_json`, and the model from settings.
- Real OpenAI image enhancement still needs manual validation with a live key; use `docs/OPENAI_MANUAL_TEST.md`.

## Verification Run

Latest checks run successfully:

```powershell
python -m py_compile app.py studio_engine.py image_enhance.py pvs_storage.py starter_pack.py video_converter\src\video_converter\converter.py
$env:PYTHONPATH="C:\Users\Admin\Desktop\photo_video_studio\video_converter\src"; python -m pytest tests video_converter\tests
```

Result: `24 passed`.

Also verified a real ffmpeg smoke render with temporary photos/background after cancel-aware ffmpeg changes. It produced an MP4 in `%TEMP%`.

## Git Status

- Local branch: `main`
- Remote: `origin` -> `https://github.com/Kingprogrammer07/photo_video_studio.git`
- First public push completed from commit `2d0e325`.
