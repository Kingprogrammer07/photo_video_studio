"""GitHub Releases update checker and installer downloader."""

from __future__ import annotations

import json
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from version import APP_VERSION, GITHUB_REPO

API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"PhotoVideoStudio/{APP_VERSION}"


@dataclass(frozen=True)
class UpdateInfo:
    available: bool
    current_version: str
    latest_version: str
    release_url: str
    asset_name: str
    asset_url: str


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", value.lstrip("vV"))
    return tuple(int(p) for p in parts) or (0,)


def is_newer(latest: str, current: str = APP_VERSION) -> bool:
    return _version_tuple(latest) > _version_tuple(current)


def _request(url: str, timeout: float = 8.0) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def check_for_update(timeout: float = 8.0) -> UpdateInfo:
    with urllib.request.urlopen(_request(API_LATEST), timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    latest = str(data.get("tag_name") or data.get("name") or "").lstrip("vV")
    html_url = str(data.get("html_url") or f"https://github.com/{GITHUB_REPO}/releases")
    asset_name = ""
    asset_url = ""
    for asset in data.get("assets", []):
        name = str(asset.get("name") or "")
        if name.lower().endswith((".exe", ".msi")) and "setup" in name.lower():
            asset_name = name
            asset_url = str(asset.get("browser_download_url") or "")
            break
    return UpdateInfo(
        available=bool(latest and asset_url and is_newer(latest)),
        current_version=APP_VERSION,
        latest_version=latest or APP_VERSION,
        release_url=html_url,
        asset_name=asset_name,
        asset_url=asset_url,
    )


def download_update(info: UpdateInfo, destination: Path | None = None) -> Path:
    if not info.asset_url:
        raise RuntimeError("Release ichida setup fayli topilmadi.")
    out_dir = destination or Path(tempfile.gettempdir()) / "PhotoVideoStudioUpdates"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (info.asset_name or f"PhotoVideoStudioSetup-{info.latest_version}.exe")
    with urllib.request.urlopen(_request(info.asset_url), timeout=60) as response:
        with target.open("wb") as fh:
            while True:
                chunk = response.read(1024 * 512)
                if not chunk:
                    break
                fh.write(chunk)
    return target
