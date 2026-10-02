# Tasks

Last updated: 2026-10-02

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

## Next High-Value Tasks

- Add drag-and-drop photo import.
- Add built-in starter background/template packs.
- Add manual template preview thumbnails.
- Add background delete/rename/favorite controls.
- Add cancel button for render and AI batch work.
- Improve AI compare view with a real draggable before/after divider.
- Add Gemini provider adapter after OpenAI flow is stable and real OpenAI photo edits are manually validated.
- Add installer or portable EXE packaging test.
- Add UI smoke tests if a Windows GUI test approach is chosen.

## Known Limitations

- OpenAI enhance is wired through the Images edit endpoint but still needs real API-key/manual validation with real photos.
- Local “face-safe restore” is conservative Pillow smoothing/detail, not a dedicated face restoration model.
- Background scenes currently keep the background stable; Ken Burns motion is disabled for layered background scenes.
- GitHub repo setup is being completed through `gh`.
