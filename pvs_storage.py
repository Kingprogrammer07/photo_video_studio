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


def import_background(src: str | os.PathLike[str]) -> Path:
    ensure_dirs()
    source = Path(src)
    if source.suffix.lower() not in SUPPORTED_BG:
        raise ValueError("Faqat rasm fayllari background sifatida qo'shiladi.")
    dest = unique_path(backgrounds_dir(), slugify(source.stem), source.suffix.lower())
    shutil.copy2(source, dest)
    return dest


def list_backgrounds() -> list[Path]:
    ensure_dirs()
    return sorted(
        [p for p in backgrounds_dir().iterdir() if p.suffix.lower() in SUPPORTED_BG],
        key=lambda p: p.name.lower(),
    )


def save_template(name: str, data: dict[str, Any]) -> Path:
    ensure_dirs()
    path = unique_path(templates_dir(), slugify(name), ".json")
    payload = {"name": name.strip() or path.stem, "data": data}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_templates() -> list[Path]:
    ensure_dirs()
    return sorted(templates_dir().glob("*.json"), key=lambda p: p.name.lower())


def load_template(path: str | os.PathLike[str]) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload
    return {"name": Path(path).stem, "data": payload if isinstance(payload, dict) else {}}


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
