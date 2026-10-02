"""Persistent settings, templates, backgrounds, and secret helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
import ctypes
from pathlib import Path
from typing import Any

APP_NAME = "PhotoVideoStudio"
KEYRING_SERVICE = "PhotoVideoStudio"

SUPPORTED_BG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

DEFAULT_SETTINGS: dict[str, Any] = {
    "provider": "openai",
    "openai_model": "gpt-image-2.5-sunburst",
    "openai_quality": "medium",
    "ai_consent": False,
    "last_background": "",
    "last_template": "",
    "favorite_backgrounds": [],
    "starter_pack_version": "",
}


def app_dir() -> Path:
    override = os.environ.get("PVS_APPDATA")
    if override:
        return Path(override)
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / f".{APP_NAME}"


def backgrounds_dir() -> Path:
    return app_dir() / "backgrounds"


def templates_dir() -> Path:
    return app_dir() / "templates"


def ai_cache_dir() -> Path:
    return app_dir() / "cache" / "ai"


def ensure_dirs() -> None:
    for path in (app_dir(), backgrounds_dir(), templates_dir(), ai_cache_dir()):
        path.mkdir(parents=True, exist_ok=True)


def settings_path() -> Path:
    return app_dir() / "settings.json"


def load_settings() -> dict[str, Any]:
    ensure_dirs()
    path = settings_path()
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        out = dict(DEFAULT_SETTINGS)
        if isinstance(data, dict):
            out.update(data)
        return out
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict[str, Any]) -> None:
    ensure_dirs()
    data = dict(DEFAULT_SETTINGS)
    data.update(settings)
    settings_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def slugify(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "template"


def unique_path(folder: Path, stem: str, suffix: str) -> Path:
    candidate = folder / f"{stem}{suffix}"
    n = 2
    while candidate.exists():
        candidate = folder / f"{stem}_{n}{suffix}"
        n += 1
    return candidate


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if str(v).strip()]


def _safe_child(path: str | os.PathLike[str], folder: Path) -> Path:
    target = Path(path).resolve(strict=False)
    root = folder.resolve(strict=False)
    try:
        ok = target.is_relative_to(root)
    except AttributeError:
        ok = str(target).lower().startswith(str(root).lower() + os.sep)
    if not ok:
        raise ValueError("Bu fayl app papkasidan tashqarida.")
    return target


def _replace_favorite_path(old: Path, new: Path | None = None) -> None:
    settings = load_settings()
    old_s = str(old)
    favorites = [p for p in _as_list(settings.get("favorite_backgrounds")) if p != old_s]
    if new is not None:
        favorites.append(str(new))
    settings["favorite_backgrounds"] = sorted(set(favorites))
    save_settings(settings)


def import_background(src: str | os.PathLike[str]) -> Path:
    ensure_dirs()
    source = Path(src)
    if source.suffix.lower() not in SUPPORTED_BG:
        raise ValueError("Faqat rasm fayllari background sifatida qo'shiladi.")
    dest = unique_path(backgrounds_dir(), slugify(source.stem), source.suffix.lower())
    shutil.copy2(source, dest)
    return dest


def list_backgrounds(with_meta: bool = False) -> list[Path] | list[dict[str, Any]]:
    ensure_dirs()
    paths = sorted(
        [p for p in backgrounds_dir().iterdir() if p.suffix.lower() in SUPPORTED_BG],
        key=lambda p: p.name.lower(),
    )
    if not with_meta:
        return paths
    favorites = set(_as_list(load_settings().get("favorite_backgrounds")))
    rows = []
    for p in paths:
        rows.append(
            {
                "path": p,
                "name": p.stem.replace("_", " "),
                "favorite": str(p) in favorites,
                "builtin": p.name.startswith("starter_"),
                "preview_path": p,
            }
        )
    return sorted(rows, key=lambda row: (not row["favorite"], row["name"].lower()))


def rename_background(path: str | os.PathLike[str], new_name: str) -> Path:
    ensure_dirs()
    src = _safe_child(path, backgrounds_dir())
    if src.suffix.lower() not in SUPPORTED_BG or not src.exists():
        raise FileNotFoundError("Background topilmadi.")
    dest = unique_path(backgrounds_dir(), slugify(new_name), src.suffix.lower())
    src.rename(dest)
    settings = load_settings()
    if settings.get("last_background") == str(src):
        settings["last_background"] = str(dest)
        save_settings(settings)
    _replace_favorite_path(src, dest)
    return dest


def delete_background(path: str | os.PathLike[str]) -> None:
    ensure_dirs()
    target = _safe_child(path, backgrounds_dir())
    if target.exists() and target.suffix.lower() in SUPPORTED_BG:
        target.unlink()
    settings = load_settings()
    if settings.get("last_background") == str(target):
        settings["last_background"] = ""
    settings["favorite_backgrounds"] = [
        p for p in _as_list(settings.get("favorite_backgrounds")) if p != str(target)
    ]
    save_settings(settings)


def favorite_background(path: str | os.PathLike[str], favorite: bool = True) -> None:
    ensure_dirs()
    target = _safe_child(path, backgrounds_dir())
    if not target.exists():
        raise FileNotFoundError("Background topilmadi.")
    settings = load_settings()
    favorites = set(_as_list(settings.get("favorite_backgrounds")))
    if favorite:
        favorites.add(str(target))
    else:
        favorites.discard(str(target))
    settings["favorite_backgrounds"] = sorted(favorites)
    save_settings(settings)


def save_template(name: str, data: dict[str, Any], preview_path: str | os.PathLike[str] | None = None) -> Path:
    ensure_dirs()
    path = unique_path(templates_dir(), slugify(name), ".json")
    payload: dict[str, Any] = {"name": name.strip() or path.stem, "data": data}
    if preview_path:
        payload["preview_path"] = str(preview_path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_templates(with_meta: bool = False) -> list[Path] | list[dict[str, Any]]:
    ensure_dirs()
    paths = sorted(templates_dir().glob("*.json"), key=lambda p: p.name.lower())
    if not with_meta:
        return paths
    rows = []
    for p in paths:
        try:
            payload = load_template(p)
            name = payload.get("name") or p.stem
            preview = payload.get("preview_path", "")
        except Exception:
            name = p.stem
            preview = ""
        rows.append({"path": p, "name": name, "preview_path": preview})
    return rows


def load_template(path: str | os.PathLike[str]) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload
    return {"name": Path(path).stem, "data": payload if isinstance(payload, dict) else {}}


def rename_template(path: str | os.PathLike[str], new_name: str) -> Path:
    ensure_dirs()
    src = _safe_child(path, templates_dir())
    if not src.exists() or src.suffix.lower() != ".json":
        raise FileNotFoundError("Shablon topilmadi.")
    payload = load_template(src)
    payload["name"] = new_name.strip() or src.stem
    dest = unique_path(templates_dir(), slugify(payload["name"]), ".json")
    src.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    src.rename(dest)
    settings = load_settings()
    if settings.get("last_template") == str(src):
        settings["last_template"] = str(dest)
        save_settings(settings)
    return dest


def delete_template(path: str | os.PathLike[str]) -> None:
    ensure_dirs()
    target = _safe_child(path, templates_dir())
    preview = ""
    if target.exists() and target.suffix.lower() == ".json":
        try:
            preview = str(load_template(target).get("preview_path", ""))
        except Exception:
            preview = ""
        target.unlink()
    if preview:
        try:
            prev = _safe_child(preview, templates_dir())
            if prev.exists() and prev.suffix.lower() in SUPPORTED_BG:
                prev.unlink()
        except Exception:
            pass
    settings = load_settings()
    if settings.get("last_template") == str(target):
        settings["last_template"] = ""
        save_settings(settings)


def starter_pack_installed(version: str = "1") -> bool:
    return load_settings().get("starter_pack_version") == version


def mark_starter_pack_installed(version: str = "1") -> None:
    settings = load_settings()
    settings["starter_pack_version"] = version
    save_settings(settings)


def _keyring():
    try:
        import keyring  # type: ignore

        return keyring
    except Exception:
        return None


def _credential_target(provider: str) -> str:
    return f"{KEYRING_SERVICE}:{provider}"


def _windows_cred_get(provider: str) -> str:
    if os.name != "nt":
        return ""

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", ctypes.c_ulong),
            ("Type", ctypes.c_ulong),
            ("TargetName", ctypes.c_wchar_p),
            ("Comment", ctypes.c_wchar_p),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", ctypes.c_ulong),
            ("CredentialBlob", ctypes.c_void_p),
            ("Persist", ctypes.c_ulong),
            ("AttributeCount", ctypes.c_ulong),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", ctypes.c_wchar_p),
            ("UserName", ctypes.c_wchar_p),
        ]

    advapi = ctypes.windll.advapi32
    pcred = ctypes.POINTER(CREDENTIAL)()
    ok = advapi.CredReadW(_credential_target(provider), 1, 0, ctypes.byref(pcred))
    if not ok:
        return ""
    try:
        cred = pcred.contents
        if not cred.CredentialBlob or not cred.CredentialBlobSize:
            return ""
        raw = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
        return raw.decode("utf-16le")
    finally:
        advapi.CredFree(pcred)


def _windows_cred_set(provider: str, key: str) -> bool:
    if os.name != "nt":
        return False

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", ctypes.c_ulong),
            ("Type", ctypes.c_ulong),
            ("TargetName", ctypes.c_wchar_p),
            ("Comment", ctypes.c_wchar_p),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", ctypes.c_ulong),
            ("CredentialBlob", ctypes.c_void_p),
            ("Persist", ctypes.c_ulong),
            ("AttributeCount", ctypes.c_ulong),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", ctypes.c_wchar_p),
            ("UserName", ctypes.c_wchar_p),
        ]

    blob = key.strip().encode("utf-16le")
    buf = ctypes.create_string_buffer(blob)
    cred = CREDENTIAL()
    cred.Type = 1  # CRED_TYPE_GENERIC
    cred.TargetName = _credential_target(provider)
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(buf, ctypes.c_void_p)
    cred.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
    cred.UserName = provider
    return bool(ctypes.windll.advapi32.CredWriteW(ctypes.byref(cred), 0))


def _windows_cred_delete(provider: str) -> None:
    if os.name == "nt":
        try:
            ctypes.windll.advapi32.CredDeleteW(_credential_target(provider), 1, 0)
        except Exception:
            pass


def keyring_available() -> bool:
    return os.name == "nt" or _keyring() is not None


def get_api_key(provider: str = "openai") -> str:
    value = _windows_cred_get(provider)
    if value:
        return value
    kr = _keyring()
    if not kr:
        return ""
    try:
        return kr.get_password(KEYRING_SERVICE, provider) or ""
    except Exception:
        return ""


def set_api_key(provider: str, key: str) -> None:
    if _windows_cred_set(provider, key):
        return
    kr = _keyring()
    if not kr:
        raise RuntimeError("Windows Credential Manager/keyring topilmadi. API key xavfsiz saqlanmadi.")
    kr.set_password(KEYRING_SERVICE, provider, key.strip())


def delete_api_key(provider: str = "openai") -> None:
    _windows_cred_delete(provider)
    kr = _keyring()
    if not kr:
        return
    try:
        kr.delete_password(KEYRING_SERVICE, provider)
    except Exception:
        pass
