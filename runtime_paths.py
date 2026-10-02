"""Runtime path helpers for source, PyInstaller builds, and installer layout."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def app_root() -> Path:
    """Return the directory that contains app resources at runtime."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_root() -> Path:
    """Return PyInstaller's internal resource root when present."""
    return Path(getattr(sys, "_MEIPASS", app_root())).resolve()


def resource_path(*parts: str) -> Path:
    """Resolve a bundled resource path, falling back to the source tree."""
    bundled = bundle_root().joinpath(*parts)
    if bundled.exists():
        return bundled
    return app_root().joinpath(*parts)


def ffmpeg_candidates() -> list[Path]:
    roots = [app_root(), bundle_root(), Path(__file__).resolve().parent]
    names = [
        Path("ffmpeg") / "bin" / "ffmpeg.exe",
        Path("ffmpeg.exe"),
        Path("bin") / "ffmpeg.exe",
    ]
    candidates: list[Path] = []
    for root in roots:
        for name in names:
            p = (root / name).resolve()
            if p not in candidates:
                candidates.append(p)

    env = os.environ.get("PVS_FFMPEG")
    if env:
        candidates.insert(0, Path(env).resolve())

    found = shutil.which("ffmpeg")
    if found:
        candidates.append(Path(found).resolve())
    return candidates


def find_bundled_ffmpeg() -> str:
    for candidate in ffmpeg_candidates():
        if candidate.is_file():
            return str(candidate)
    return ""
