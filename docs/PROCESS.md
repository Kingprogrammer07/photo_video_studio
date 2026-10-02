# Development Process

Last updated: 2026-10-02

## Working Rules

1. Read `AGENTS.md`, this file, and `docs/HANDOFF.md` before making changes.
2. Keep user-facing UX simple for non-technical adults. Prefer large controls, clear Uzbek Latin labels, and safe defaults.
3. Do not overwrite original user photos, videos, music, or backgrounds.
4. Never write API keys to repo files, settings JSON, logs, or console output.
5. Any new feature must update the relevant docs in the same change.
6. Keep generated media, temp files, `.venv`, logs, and output videos out of commits.

## Required Documentation Updates

When changing code, update at least one of:

- `docs/CHANGELOG.md`: what changed today.
- `docs/TASKS.md`: completed work and next steps.
- `docs/HANDOFF.md`: architecture, data flow, storage paths, or gotchas.
- `AGENTS.md`: durable contributor rules.

## Test Expectations

For normal code changes, run:

```powershell
python -m py_compile app.py studio_engine.py image_enhance.py pvs_storage.py starter_pack.py video_converter\src\video_converter\converter.py
$env:PYTHONPATH="C:\Users\Admin\Desktop\photo_video_studio\video_converter\src"; python -m pytest tests video_converter\tests
```

For render changes, also run a small ffmpeg smoke render with temporary images and a temporary background. Do not write smoke outputs into the repo.

## Release Notes Discipline

Each completed work session should record:

- User-visible feature changes.
- New files/modules.
- Tests run and results.
- Known limitations or follow-up tasks.

## GitHub / Git Rules

This checkout is a Git repository on `main` with remote `origin` at `https://github.com/Kingprogrammer07/photo_video_studio.git`. Commit focused milestones and push regularly. Do not publish API keys, personal photos, generated user media, local AppData contents, or temporary smoke-test outputs.
