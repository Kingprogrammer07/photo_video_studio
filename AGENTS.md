# Repository Guidelines

## Project Structure & Module Organization

- `app.py` is the main CustomTkinter GUI for Photo Video Studio.
- `connectivity.py`, `updater.py`, `runtime_paths.py`, and `version.py` support online/offline status, GitHub release updates, bundled runtime paths, and version metadata.
- `studio_engine.py` contains the slideshow render pipeline, effect registries, ffmpeg calls, and image processing.
- `music.py` generates built-in piano background audio.
- `image_enhance.py`, `pvs_storage.py`, and `starter_pack.py` support AI enhancement, AppData storage, templates, backgrounds, starter assets, and secure API keys.
- `fonts/`, `previews/`, and `wheels/` are committed assets used for consistent rendering and offline setup.
- `output/` is for generated videos; keep it out of commits.
- `video_converter/` is a separate packaged Tkinter utility using `src/video_converter/` and `video_converter/tests/`.
- `docs/` contains handoff, process, task, and changelog notes. Update these when behavior changes.

## Build, Test, and Development Commands

- `run.bat`: Windows entry point; creates `.venv`, installs dependencies from `wheels/` when possible, then runs `app.py`.
- `pip install -r requirements.txt`: installs root app dependencies.
- `python app.py`: starts Photo Video Studio manually.
- `python music.py warm`: writes a sample generated music track for quick audio checks.
- `python -m pytest tests video_converter\tests`: runs root vNext tests and converter tests when `video_converter\src` is on `PYTHONPATH`.
- `build_exe.bat`: runs the release builder; it creates a PyInstaller onedir app and, when Inno Setup is available, `release\PhotoVideoStudioSetup-<version>.exe`.
- `scripts\build_release.ps1 -SkipInstaller`: smoke-builds the bundled app folder without compiling the installer.
- `scripts\publish_release.ps1`: publishes the setup file to GitHub Releases with `gh`.
- `cd video_converter && pip install -e ".[dev]"`: installs the converter package and pytest.
- `cd video_converter && pytest`: runs converter tests.

Development runs can use `ffmpeg` on `PATH`; release installers bundle `ffmpeg.exe` under `ffmpeg\bin\`.

## Coding Style & Naming Conventions

Use Python 3.9+ for the root app and Python 3.10+ for `video_converter/`. Follow the local style: module-level constants in `UPPER_CASE`, simple snake_case functions, and GUI state owned by the Tkinter app classes. Keep root UI text in Uzbek Latin where existing controls use it. Avoid moving long-running PIL or ffmpeg work onto the GUI thread; use the existing queue/thread pattern.

No formatter or linter is configured. Keep edits focused, readable, and lightly commented.

## Testing Guidelines

The root vNext tests live in `tests/`; converter tests live in `video_converter/tests/`. Validate GUI and render changes with a short preview render before full export. Add focused tests for storage, templates, cancel flow, converter arguments, parsing, and error behavior when changing those areas.

For vNext core changes, run:

`python -m py_compile app.py studio_engine.py image_enhance.py pvs_storage.py starter_pack.py connectivity.py runtime_paths.py updater.py version.py video_converter\src\video_converter\converter.py`

`$env:PYTHONPATH="C:\Users\Admin\Desktop\photo_video_studio\video_converter\src"; python -m pytest tests video_converter\tests`

## Commit & Pull Request Guidelines

Use concise imperative commit subjects such as `Add starter template pack` or `Fix ffmpeg cancel handling`. Pull requests should describe the user-visible change, list checks or pytest results, mention ffmpeg/Python/Inno Setup versions when relevant, and include screenshots or sample output paths for GUI/rendering changes.

## Security & Configuration Tips

Do not commit generated media, virtual environments, `.log` files, local diagnostic outputs, AppData caches, API keys, or personal photos. Preserve `fonts/` and `wheels/`; they are required for consistent offline operation. Original user photos must never be overwritten; AI output belongs in cache or a user-chosen export path.

## Agent-Specific Instructions

Before changing code, read `docs/HANDOFF.md`, `docs/PROCESS.md`, and `docs/TASKS.md`. Every completed work session must update `docs/CHANGELOG.md` and, when relevant, `docs/TASKS.md` or `docs/HANDOFF.md`. Keep labels and help text friendly for non-technical Uzbek-speaking users.
