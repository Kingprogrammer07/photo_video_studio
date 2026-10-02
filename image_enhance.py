"""Photo enhancement helpers for Photo Video Studio."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import ssl
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

import pvs_storage

AI_PRESETS = {
    "auto": "Avto professional",
    "vivid": "Ranglarni jonlantir",
    "restore": "Xira rasmni tiklash",
    "faces": "Yuzlarni tabiiy saqlash",
    "album": "To'y/album",
    "ad": "Reklama",
}

OPENAI_ECONOMY_MAX_EDGE = 1536
OPENAI_QUALITY_COST_ESTIMATE = {
    "low": 0.012,
    "medium": 0.028,
    "high": 0.12,
    "xhigh": 0.20,
    "max": 0.30,
}


@dataclass(frozen=True)
class EnhanceSettings:
    brightness: float = 1.0
    contrast: float = 1.08
    saturation: float = 1.12
    warmth: float = 0.08
    sharpness: float = 1.25
    denoise: float = 0.12
    upscale: str = "auto"
    face_restore: bool = True

    def normalized(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("brightness", "contrast", "saturation", "warmth", "sharpness", "denoise"):
            data[key] = round(float(data[key]), 4)
        data["face_restore"] = bool(data["face_restore"])
        data["upscale"] = str(data["upscale"])
        return data


def cache_key(path: str | os.PathLike[str], settings: EnhanceSettings, provider: str, model: str) -> str:
    p = Path(path)
    try:
        stat = p.stat()
        stamp = f"{p.resolve()}:{stat.st_mtime_ns}:{stat.st_size}"
    except OSError:
        stamp = str(p)
    payload = {
        "source": stamp,
        "settings": settings.normalized(),
        "provider": provider,
        "model": model,
        "v": 2,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def cache_path(
    path: str | os.PathLike[str], settings: EnhanceSettings, provider: str, model: str
) -> Path:
    pvs_storage.ensure_dirs()
    return pvs_storage.ai_cache_dir() / f"{cache_key(path, settings, provider, model)}.jpg"


def openai_cache_model(model: str, quality: str, preset: str, max_edge: int = OPENAI_ECONOMY_MAX_EDGE) -> str:
    return f"{model}:{quality}:{normalize_ai_preset(preset)}:edge{int(max_edge)}"


def estimate_openai_cost(
    input_path: str | os.PathLike[str],
    *,
    quality: str = "low",
    cached: bool = False,
) -> float:
    """Return a conservative user-facing estimate for one OpenAI image edit."""
    if cached:
        return 0.0
    q = (quality or "low").lower()
    base = OPENAI_QUALITY_COST_ESTIMATE.get(q, OPENAI_QUALITY_COST_ESTIMATE["low"])
    input_cost = 0.004
    try:
        with Image.open(input_path) as im:
            megapixels = (im.width * im.height) / 1_000_000
        input_cost = min(0.035, max(0.003, megapixels * 0.004))
    except Exception:
        pass
    return round(base + input_cost, 4)


def estimate_openai_batch_cost(
    paths: list[str | os.PathLike[str]],
    settings: EnhanceSettings,
    *,
    model: str,
    quality: str,
    preset: str,
) -> dict[str, Any]:
    cache_model = openai_cache_model(model, quality, preset)
    total = 0.0
    uncached = 0
    cached = 0
    for path in paths:
        out = cache_path(path, settings, "openai", cache_model)
        is_cached = out.exists()
        if is_cached:
            cached += 1
        else:
            uncached += 1
        total += estimate_openai_cost(path, quality=quality, cached=is_cached)
    return {"estimated_cost": round(total, 4), "uncached": uncached, "cached": cached, "total": len(paths)}


def _target_edge(im: Image.Image, upscale: str) -> int | None:
    mode = (upscale or "auto").lower()
    if mode in ("yo'q", "yoq", "none", "original"):
        return None
    if mode == "hd":
        return 1920
    if mode in ("2k", "1440p"):
        return 2560
    if mode in ("4k", "2160p"):
        return 3840
    if mode == "auto":
        longest = max(im.size)
        if longest < 1200:
            return min(1920, longest * 2)
        if longest < 1900:
            return 1920
    return None


def _resize_for_target(im: Image.Image, target_edge: int | None) -> Image.Image:
    if not target_edge:
        return im
    longest = max(im.size)
    if longest >= target_edge:
        return im
    scale = min(target_edge / longest, 2.5)
    size = (max(1, int(im.width * scale)), max(1, int(im.height * scale)))
    return im.resize(size, Image.Resampling.LANCZOS)


def _prepare_openai_input(input_path: str | os.PathLike[str], folder: str, max_edge: int) -> Path:
    src = Path(input_path)
    try:
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    except Exception:
        return src
    longest = max(im.size)
    if longest <= max_edge:
        return src
    scale = max_edge / longest
    resized = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.Resampling.LANCZOS)
    out = Path(folder) / f"{src.stem[:40] or 'photo'}_openai.jpg"
    resized.save(out, quality=90, optimize=True)
    return out


def _apply_warmth(im: Image.Image, amount: float) -> Image.Image:
    if abs(amount) < 0.001:
        return im
    a = np.asarray(im).astype(np.float32)
    a[..., 0] *= 1.0 + amount * 0.18
    a[..., 2] *= 1.0 - amount * 0.16
    a[..., 1] *= 1.0 + max(amount, 0) * 0.04
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def normalize_ai_preset(preset: str | None) -> str:
    preset = (preset or "auto").lower()
    return preset if preset in AI_PRESETS else "auto"


def build_openai_prompt(settings: EnhanceSettings, preset: str | None = "auto") -> str:
    preset = normalize_ai_preset(preset)
    goals = {
        "auto": "Make balanced professional photo corrections for a family slideshow.",
        "vivid": "Make colors lively and clean while keeping skin tones natural.",
        "restore": "Restore a soft, faded, or low-quality photo with better clarity and cleaner exposure.",
        "faces": "Prioritize natural faces and identity preservation above all other changes.",
        "album": "Create a warm elegant wedding or family album look without changing clothing, people, or setting.",
        "ad": "Make the image polished, clear, and suitable for a tasteful product or business promo.",
    }
    upscale = str(settings.upscale or "auto")
    return (
        f"{goals[preset]} Preserve every person's identity, face, clothing, pose, "
        "background, composition, and all important objects. Do not add, remove, "
        "replace, beautify into a different person, or invent details. "
        f"Adjustment intent: brightness {settings.brightness:.2f}, contrast {settings.contrast:.2f}, "
        f"saturation {settings.saturation:.2f}, warmth {settings.warmth:.2f}, "
        f"sharpness {settings.sharpness:.2f}, denoise {settings.denoise:.2f}, "
        f"upscale {upscale}, face-safe restore {'on' if settings.face_restore else 'off'}. "
        "Return a natural enhanced version of the same photo."
    )


def enhance_image(
    image: Image.Image,
    settings: EnhanceSettings,
    *,
    preview_mode: bool = False,
) -> Image.Image:
    """Enhance a PIL image in memory.

    preview_mode keeps the operation light enough for live UI feedback; the
    file-writing wrapper below uses the same pipeline at full quality.
    """
    im = ImageOps.exif_transpose(image).convert("RGB")
    if preview_mode:
        im.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    else:
        im = _resize_for_target(im, _target_edge(im, settings.upscale))

    if settings.denoise > 0.02:
        if preview_mode and settings.denoise < 0.25:
            pass
        else:
            radius = 3 if settings.denoise >= 0.35 and not preview_mode else 1
            im = im.filter(ImageFilter.MedianFilter(size=radius * 2 + 1))

    im = ImageEnhance.Brightness(im).enhance(max(0.2, settings.brightness))
    im = ImageEnhance.Contrast(im).enhance(max(0.2, settings.contrast))
    im = ImageEnhance.Color(im).enhance(max(0.0, settings.saturation))
    im = _apply_warmth(im, settings.warmth)

    if settings.face_restore and not preview_mode:
        im = im.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.DETAIL)

    sharp = max(0.0, settings.sharpness)
    im = ImageEnhance.Sharpness(im).enhance(sharp)
    if sharp > 1.05:
        percent = int(min(180 if preview_mode else 220, 70 + (sharp - 1.0) * 85))
        im = im.filter(ImageFilter.UnsharpMask(radius=1.1 if preview_mode else 1.4, percent=percent, threshold=3))
    return im


def enhance_local(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    settings: EnhanceSettings,
) -> Path:
    """Enhance a photo locally without touching the original file."""
    im = enhance_image(Image.open(input_path), settings, preview_mode=False)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=94, subsampling=1, optimize=True)
    return out


def _multipart_body(fields: dict[str, str], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = "----PhotoVideoStudioBoundary" + hashlib.sha1(os.urandom(16)).hexdigest()
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    for name, path in files:
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode()
        )
        chunks.append(f"Content-Type: {mime}\r\n\r\n".encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def openai_enhance(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str],
    api_key: str,
    *,
    model: str = "gpt-image-2.5-sunburst",
    quality: str = "low",
    preset: str = "auto",
    settings: EnhanceSettings | None = None,
    input_max_edge: int = OPENAI_ECONOMY_MAX_EDGE,
) -> Path:
    """Use OpenAI image editing to enhance a photo while preserving people."""
    if not api_key.strip():
        raise RuntimeError("OpenAI API key kiritilmagan.")

    prompt = build_openai_prompt(settings or EnhanceSettings(), preset)
    fields = {
        "model": model,
        "prompt": prompt,
        "quality": quality,
        "size": "auto",
        "output_format": "jpeg",
    }
    try:
        with tempfile.TemporaryDirectory(prefix="pvs_openai_") as folder:
            send_path = _prepare_openai_input(input_path, folder, int(input_max_edge))
            body, boundary = _multipart_body(fields, [("image", send_path)])
            request = urllib.request.Request(
                "https://api.openai.com/v1/images/edits",
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=180, context=ssl.create_default_context()) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI xatosi: {exc.code}. {detail[:500]}") from exc
    except Exception as exc:
        raise RuntimeError(f"OpenAI bilan bog'lanib bo'lmadi: {exc}") from exc

    data = payload.get("data") or []
    b64 = data[0].get("b64_json") if data and isinstance(data[0], dict) else None
    if not b64:
        raise RuntimeError("OpenAI natijasida rasm ma'lumoti kelmadi.")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(b64))
    return out


def test_openai_key(api_key: str) -> bool:
    if not api_key.strip():
        return False
    req = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key.strip()}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False
