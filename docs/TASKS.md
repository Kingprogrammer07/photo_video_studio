# Tasks

Last updated: 2026-10-05

## Done In Current vNext Pass

- Added AppData storage helpers for settings, backgrounds, templates, and AI cache.
- Added secure OpenAI API key storage using Windows Credential Manager.
- Added local professional photo enhancement and OpenAI image-edit adapter.
- Added cache keys based on original path, mtime, settings, provider, and model.
- Extended `build_video(config)` with `background_path`, `photo_layout`, `photo_scale`, `photo_frame`, and `enhanced_photos`.
- Added background scene composition with stable background, framed photo, optional shadow, and layout presets.
- Rebuilt main UI into tabs: Slideshow, Fonlar/Shablonlar, AI Rasm Studio, Video Tools, Sozlamalar.
- Integrated existing video converter backend into the main app.
- Added template save/load JSON flow and post-render “save template?” prompt.
- Added tests for settings/templates, AI cache key, local enhance safety, and background scene sizing.
- Corrected OpenAI image edit multipart payload to use the `image` field and request `b64_json`.
- Added repo hygiene rules for local diagnostics, runtime data, and generated media.
- Created public GitHub repository and pushed `main`: https://github.com/Kingprogrammer07/photo_video_studio
- Added Polish Pack starter pack with 8 procedural backgrounds/templates and idempotent AppData install.
- Added background/template preview, rename, delete, favorite, and starter-pack reinstall controls.
- Added optional drag-and-drop photo import with safe fallback to the file picker.
- Added cancel support for render, AI enhancement jobs, and Video Tools conversion.
- Replaced AI before/after slider preview with a draggable Canvas divider.
- Added manual OpenAI real-key validation checklist.
- Added tests for starter pack install, storage metadata operations, render cancel, converter cancel, and template preview metadata.
- Added release builder scripts, Inno Setup config, bundled ffmpeg lookup, online/offline status, and GitHub Releases update check/download flow.
- Verified PyInstaller onedir build with bundled `ffmpeg.exe`; full installer compile still needs Inno Setup installed.
- Added debounced slideshow preview updates and an `Aniq ko'rish` worker preview button.
- Reworked AI Professional preview to use in-memory Pillow processing with stale-result protection.
- Fixed Lotin/Kiril rebuild so selected photos, captions, enhanced paths, tab, and per-slide settings are restored immediately.
- Added ProShow-style motion presets and layered background rendering where the background stays stable while the photo/frame moves.
- Added per-slide duration override controls and render support through `photo_durations`.
- Added tests for in-memory enhance preview, motion fallback, and duration resolution.
- Added text-on/off controls, title/caption/outro switches, text templates, and font presets.
- Added lightweight animated slideshow preview for motion/effects and moved `Aniq ko'rish` to the visible preview toolbar.
- Reworked template list into 2-column cards with larger previews.
- Shifted AI Studio user flow to OpenAI-first presets and batch/selected OpenAI enhancement.
- Updated OpenAI image-edit payload to current docs: base64 response is read from `data[0].b64_json` without sending `response_format`.
- Added tests for text flags, single-clip stitch, font fallback, starter template text fields, and OpenAI prompt building.
- Added global and per-slide motion setting controls for start scale, end scale, speed, and X/Y drift.
- Made `tiny_to_big` gentler by default and added `photo_motion_settings` render support.
- Added AppData-backed AI usage history at `%APPDATA%\PhotoVideoStudio\ai_history.jsonl` with estimated cost, cache hit, status, and output path.
- Added AI cost summary, CSV export, and clear controls in Settings.
- Added OpenAI batch cost confirmation and default `low` quality for new installs.
- Restored user-facing free local enhancement buttons for selected/all photos.
- Added tests for motion settings, render config propagation, AI history JSONL, and cache-aware cost estimates.
- Fixed final muxing so short user-selected music loops instead of cutting the video before later photos appear.
- Added a direct `Ushbu slide sekund` entry field for selected-slide duration overrides.
- Added FPS normalization to background foreground-photo motion for smoother rendered animation.
- Stabilized 60fps photo motion by rounding animated coordinates and forcing even-sized scaled layers.
- Added tests for jitter-safe ffmpeg filter construction.

## Next High-Value Tasks

- Manually validate OpenAI enhance with a real API key using `docs/OPENAI_MANUAL_TEST.md`.
- Compare app-estimated OpenAI cost against real OpenAI dashboard usage after a live-key test.
- Manually verify live motion preview smoothness on the target Windows laptop.
- Manually verify exported motion smoothness on the target Windows laptop with several FPS choices.
- Install Inno Setup and run full `build_exe.bat` to produce `release\PhotoVideoStudioSetup-0.3.0.exe`.
- Create first GitHub Release with `scripts\publish_release.ps1`, then test in-app update check against that release.
- Test drag-and-drop on a machine with `tkinterdnd2` installed.
- Add Gemini provider adapter after OpenAI flow is stable.
- Add an advanced keyframe editor only if the new simple motion sliders are not enough for real users.
- Add user-facing starter template category filters if the template list grows.
- Add installer or portable EXE packaging test.
- Add UI smoke tests if a Windows GUI test approach is chosen.

## Known Limitations

- OpenAI enhance is wired through the Images edit endpoint but still needs real API-key/manual validation with real photos.
- OpenAI cost values shown in-app are estimates for user guidance; the OpenAI billing dashboard remains the source of truth.
- Background scenes support foreground photo/frame motion while the background stays stable; fonsiz scenes still use the existing zoompan-style full-photo pipeline.
- Drag-and-drop is optional and only activates when `tkinterdnd2` is present; the dependency is intentionally not added to `requirements.txt`.
- First releases are unsigned, so Windows SmartScreen may show a warning until code signing is added.
- Full installer build was not run in this pass because Inno Setup (`iscc`) is not installed on PATH.
- GitHub repo setup is complete. Future work should commit and push regularly.
