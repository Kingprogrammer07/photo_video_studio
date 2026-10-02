# Repository Guidelines

## Project Structure & Module Organization

- `app.py` is the main CustomTkinter GUI for Photo Video Studio.
- `studio_engine.py` contains the slideshow render pipeline, effect registries, ffmpeg calls, and image processing.
- `music.py` generates built-in piano background audio.
- `image_enhance.py` and `pvs_storage.py` support AI enhancement, AppData storage, templates, backgrounds, and secure API keys.
- `fonts/`, `previews/`, and `wheels/` are committed assets used for consistent rendering and offline setup.
- `output/` is for generated videos; keep it out of commits.
- `video_converter/` is a separate packaged Tkinter utility using `src/video_converter/` and `video_converter/tests/`.
- `docs/` contains handoff, process, task, and changelog notes. Update these when behavior changes.

## Build, Test, and Development Commands

- `run.bat`: Windows entry point; creates `.venv`, installs dependencies from `wheels/` when possible, then runs `app.py`.
- `pip install -r requirements.txt`: installs root app dependencies.
- `python app.py`: starts Photo Video Studio manually.
- `python music.py warm`: writes a sample generated music track for quick audio checks.
- `build_exe.bat`: builds `dist/PhotoVideoStudio.exe` with PyInstaller; ffmpeg is still required externally.
- `cd video_converter && pip install -e ".[dev]"`: installs the converter package and pytest.
- `cd video_converter && pytest`: runs converter tests.

Both apps require `ffmpeg` on `PATH` (`ffmpeg -version` should work).

## Coding Style & Naming Conventions

Use Python 3.9+ for the root app and Python 3.10+ for `video_converter/`. Follow the local style: module-level constants in `UPPER_CASE`, simple snake_case functions, and GUI state owned by the Tkinter app classes. Keep root UI text in Uzbek Latin where existing controls use it. Avoid moving long-running PIL or ffmpeg work onto the GUI thread; use the existing queue/thread pattern.

No formatter or linter is configured. Keep edits focused, readable, and lightly commented.

## Testing Guidelines

The root slideshow app currently has no automated tests; validate GUI and render changes with a short preview render before full export. The converter package uses pytest, with tests named `test_*.py` under `video_converter/tests/`. Add tests for converter argument-building, parsing, and error behavior when changing `converter.py`.

For vNext core changes, run:

`python -m py_compile app.py studio_engine.py image_enhance.py pvs_storage.py video_converter\src\video_converter\converter.py`

`$env:PYTHONPATH="C:\Users\Admin\Desktop\photo_video_studio\video_converter\src"; python -m pytest tests video_converter\tests`

## Commit & Pull Request Guidelines

This checkout has no Git history available, so use concise imperative commit subjects such as `Add radial transition preview` or `Fix ffmpeg path handling`. Pull requests should describe the user-visible change, list checks or pytest results, mention ffmpeg/Python versions when relevant, and include screenshots or sample output paths for GUI/rendering changes.

## Security & Configuration Tips

Do not commit generated media, virtual environments, `.log` files, local diagnostic outputs, AppData caches, API keys, or personal photos. Preserve `fonts/` and `wheels/`; they are required for consistent offline operation. Original user photos must never be overwritten; AI output belongs in cache or a user-chosen export path.

## Agent-Specific Instructions

Before changing code, read `docs/HANDOFF.md`, `docs/PROCESS.md`, and `docs/TASKS.md`. Every completed work session must update `docs/CHANGELOG.md` and, when relevant, `docs/TASKS.md` or `docs/HANDOFF.md`. Keep labels and help text friendly for non-technical Uzbek-speaking users.
