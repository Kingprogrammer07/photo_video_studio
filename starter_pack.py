"""Procedural starter backgrounds and templates for Photo Video Studio."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import pvs_storage as Store

VERSION = "1"
WIDE = (1920, 1080)
VERTICAL = (1080, 1920)


@dataclass(frozen=True)
class StarterTemplate:
    ident: str
    name: str
    size: tuple[int, int]
    palette: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]
    layout: str
    scale: float
    style: str
    grade: str
    transition: str
    title: str
    kicker: str
    subtitle: str
    pattern: str


PACKS = [
    StarterTemplate("family_blue", "Oilaviy ko'k", WIDE, ((18, 95, 137), (10, 55, 86), (236, 190, 72)), "center", 0.60, "Iliq oltin (kinematik)", "warm", "fade", "Oilaviy xotira", "MEHR BILAN", "Eng yaxshi kunlar", "tile"),
    StarterTemplate("wedding_gold", "To'y oltin", WIDE, ((33, 47, 83), (7, 25, 48), (224, 176, 84)), "center", 0.58, "Iliq oltin (kinematik)", "warm", "circle", "To'y muborak", "BAHTLI KUN", "Sevgi va hurmat bilan", "arch"),
    StarterTemplate("birthday", "Tug'ilgan kun", WIDE, ((246, 93, 108), (72, 137, 220), (255, 214, 86)), "center", 0.62, "Zamonaviy yorqin", "bright", "slide", "Tug'ilgan kun", "TABRIKLAYMIZ", "Quvonchli lahzalar", "confetti"),
    StarterTemplate("ramadan_eid", "Ramazon/Hayit", WIDE, ((8, 83, 92), (6, 40, 52), (229, 184, 89)), "center", 0.56, "Iliq oltin (kinematik)", "warm", "radial", "Hayit muborak", "EZGU NIYATLAR", "Xonadoningiz fayzga to'lsin", "lantern"),
    StarterTemplate("memory", "Xotira", WIDE, ((70, 73, 78), (24, 25, 29), (197, 170, 116)), "center", 0.58, "Iliq oltin (kinematik)", "soft", "fadeblack", "Xotira", "YODDA QOLGAN ONLAR", "Mehr bilan eslaymiz", "classic"),
    StarterTemplate("business", "Biznes reklama", WIDE, ((27, 94, 116), (238, 241, 236), (231, 143, 69)), "right", 0.48, "Zamonaviy yorqin", "neutral", "push", "Mahsulot nomi", "REKLAMA", "Qisqa, aniq va ishonchli", "business"),
    StarterTemplate("instagram_vertical", "Instagram vertical", VERTICAL, ((169, 64, 147), (56, 94, 180), (255, 194, 76)), "center", 0.64, "Zamonaviy yorqin", "vivid", "slide", "Story video", "INSTAGRAM", "Vertikal format", "story"),
    StarterTemplate("classic_album", "Klassik albom", WIDE, ((221, 216, 205), (151, 123, 92), (62, 74, 92)), "center", 0.58, "Iliq oltin (kinematik)", "vintage", "dissolve", "Klassik albom", "OILAVIY ARXIV", "Sokin va chiroyli", "album"),
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _gradient(size: tuple[int, int], a: tuple[int, int, int], b: tuple[int, int, int]) -> Image.Image:
    w, h = size
    strip = Image.new("RGB", (1, h))
    pix = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(a[0] * (1 - t) + b[0] * t)
        g = int(a[1] * (1 - t) + b[1] * t)
        bl = int(a[2] * (1 - t) + b[2] * t)
        pix[0, y] = (r, g, bl)
    return strip.resize((w, h), Image.BICUBIC)


def _add_vignette(im: Image.Image, strength: float = 0.45) -> Image.Image:
    w, h = im.size
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    margin = int(min(w, h) * 0.08)
    d.ellipse([-margin, -margin, w + margin, h + margin], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(int(min(w, h) * 0.16)))
    dark = Image.new("RGB", im.size, (0, 0, 0))
    return Image.composite(im, dark, mask.point(lambda v: int(v * (1 - strength))))


def _tile_pattern(draw: ImageDraw.ImageDraw, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    w, h = size
    step = max(80, w // 18)
    for y in range(-step, h + step, step):
        for x in range(-step, w + step, step):
            r = step // 5
            draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=max(2, step // 40))
            draw.line([x - r, y, x + r, y], fill=color, width=2)
            draw.line([x, y - r, x, y + r], fill=color, width=2)


def _draw_arch(draw: ImageDraw.ImageDraw, size: tuple[int, int], accent: tuple[int, int, int]) -> None:
    w, h = size
    pad = int(w * 0.13)
    top = int(h * 0.16)
    bottom = int(h * 0.88)
    for off, width in ((0, 12), (28, 4)):
        box = [pad + off, top + off, w - pad - off, top + int(h * 0.48) + off]
        draw.arc(box, 180, 360, fill=accent, width=width)
        draw.line([pad + off, top + int(h * 0.24), pad + off, bottom], fill=accent, width=width)
        draw.line([w - pad - off, top + int(h * 0.24), w - pad - off, bottom], fill=accent, width=width)
        draw.line([pad + off, bottom, w - pad - off, bottom], fill=accent, width=width)


def _draw_confetti(draw: ImageDraw.ImageDraw, size: tuple[int, int], colors: list[tuple[int, int, int]]) -> None:
    w, h = size
    for i in range(120):
        x = (i * 167) % w
        y = (i * 97) % h
        col = colors[i % len(colors)]
        if i % 3 == 0:
            draw.ellipse([x, y, x + 13, y + 13], fill=col)
        else:
            draw.rectangle([x, y, x + 18, y + 7], fill=col)


def _draw_lanterns(draw: ImageDraw.ImageDraw, size: tuple[int, int], accent: tuple[int, int, int]) -> None:
    w, h = size
    for x in (int(w * 0.15), int(w * 0.85)):
        draw.line([x, 0, x, int(h * 0.22)], fill=accent, width=5)
        y = int(h * 0.20)
        draw.rounded_rectangle([x - 45, y, x + 45, y + 120], radius=28, outline=accent, width=7)
        draw.ellipse([x - 34, y + 24, x + 34, y + 96], fill=(255, 209, 122))
        draw.line([x - 55, y + 125, x + 55, y + 125], fill=accent, width=4)
    cres_x, cres_y = int(w * 0.50), int(h * 0.15)
    draw.ellipse([cres_x - 70, cres_y - 70, cres_x + 70, cres_y + 70], fill=accent)
    draw.ellipse([cres_x - 35, cres_y - 72, cres_x + 95, cres_y + 58], fill=(8, 83, 92))


def _draw_business(draw: ImageDraw.ImageDraw, size: tuple[int, int], accent: tuple[int, int, int]) -> None:
    w, h = size
    draw.polygon([(0, 0), (int(w * 0.52), 0), (int(w * 0.36), h), (0, h)], fill=(238, 241, 236))
    draw.polygon([(int(w * 0.08), h), (int(w * 0.42), h), (int(w * 0.50), 0), (int(w * 0.18), 0)], fill=accent)
    for i in range(6):
        x = int(w * (0.07 + i * 0.055))
        draw.line([x, int(h * 0.18), x + int(w * 0.16), int(h * 0.18)], fill=(27, 94, 116), width=7)


def _draw_story(draw: ImageDraw.ImageDraw, size: tuple[int, int], accent: tuple[int, int, int]) -> None:
    w, h = size
    for i in range(10):
        r = int(min(w, h) * (0.10 + i * 0.035))
        cx = int(w * (0.18 + (i % 3) * 0.27))
        cy = int(h * (0.12 + (i % 4) * 0.22))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent, width=5)


def _make_background(tpl: StarterTemplate) -> Image.Image:
    c1, c2, accent = tpl.palette
    im = _gradient(tpl.size, c1, c2)
    overlay = Image.new("RGBA", tpl.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    faint = tuple(min(255, int(v * 1.25)) for v in accent) + (70,)
    _tile_pattern(d, tpl.size, faint)
    if tpl.pattern == "arch":
        _draw_arch(d, tpl.size, accent)
    elif tpl.pattern == "confetti":
        _draw_confetti(d, tpl.size, [accent, (255, 255, 255), c1, c2])
    elif tpl.pattern == "lantern":
        _draw_lanterns(d, tpl.size, accent)
    elif tpl.pattern == "business":
        _draw_business(d, tpl.size, accent)
    elif tpl.pattern == "story":
        _draw_story(d, tpl.size, accent)
    elif tpl.pattern == "album":
        w, h = tpl.size
        d.rectangle([int(w * 0.07), int(h * 0.09), int(w * 0.93), int(h * 0.91)], outline=accent, width=10)
        d.rectangle([int(w * 0.095), int(h * 0.12), int(w * 0.905), int(h * 0.88)], outline=(255, 255, 255, 80), width=3)
    elif tpl.pattern == "classic":
        w, h = tpl.size
        for i in range(12):
            y = int(h * (0.08 + i * 0.075))
            d.line([int(w * 0.12), y, int(w * 0.88), y], fill=(255, 255, 255, 28), width=2)
    im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
    return _add_vignette(im, 0.22)


def _preview(bg: Image.Image, tpl: StarterTemplate) -> Image.Image:
    w, h = (640, 360) if tpl.size[0] >= tpl.size[1] else (270, 480)
    im = bg.copy()
    im.thumbnail((w, h), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), bg.getpixel((0, 0)))
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    d = ImageDraw.Draw(canvas, "RGBA")
    bw, bh = int(w * tpl.scale), int(h * min(0.70, tpl.scale))
    x = (w - bw) // 2
    if tpl.layout == "right":
        x = int(w * 0.47)
    elif tpl.layout == "left":
        x = int(w * 0.07)
    y = int(h * 0.30)
    d.rounded_rectangle([x - 8, y - 8, x + bw + 8, y + bh + 8], radius=8, fill=(255, 255, 255, 220))
    d.rectangle([x, y, x + bw, y + bh], fill=(218, 226, 232, 255))
    d.line([x, y, x + bw, y + bh], fill=(165, 175, 185, 255), width=3)
    d.line([x + bw, y, x, y + bh], fill=(165, 175, 185, 255), width=3)
    d.text((24, 22), tpl.kicker, fill=(255, 255, 255), font=_font(18, True))
    d.text((24, h - 58), tpl.title, fill=(255, 255, 255), font=_font(34, True))
    return canvas


def _payload(tpl: StarterTemplate, background: Path) -> dict:
    return {
        "style": tpl.style,
        "grade": tpl.grade,
        "transition_type": tpl.transition,
        "kb_intensity": "normal",
        "vignette": "auto",
        "resolution": "Vertical 1080x1920" if tpl.size[1] > tpl.size[0] else "1440p (2K)",
        "fps": 30,
        "preset": "fast",
        "photo_duration": 4.5,
        "title": tpl.title,
        "kicker": tpl.kicker,
        "date": "",
        "outro_kicker": "SEVGI BILAN",
        "subtitle": tpl.subtitle,
        "background_path": str(background),
        "photo_layout": tpl.layout,
        "photo_scale": tpl.scale,
        "photo_frame": {"border": True, "shadow": True, "radius": 0},
        "ai_settings": {
            "brightness": 1.0,
            "contrast": 1.08,
            "saturation": 1.12,
            "warmth": 0.08,
            "sharpness": 1.25,
            "denoise": 0.12,
            "upscale": "auto",
            "face_restore": True,
        },
    }


def install_if_needed(force: bool = False) -> bool:
    """Install starter backgrounds/templates into AppData.

    Returns True when files were created or refreshed.
    """
    Store.ensure_dirs()
    expected = []
    for tpl in PACKS:
        expected.append(Store.backgrounds_dir() / f"starter_{tpl.ident}.jpg")
        expected.append(Store.templates_dir() / f"starter_{tpl.ident}.json")
        expected.append(Store.templates_dir() / "previews" / f"starter_{tpl.ident}.jpg")
    if not force and Store.starter_pack_installed(VERSION) and all(path.exists() for path in expected):
        return False

    changed = False
    thumb_dir = Store.templates_dir() / "previews"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    for tpl in PACKS:
        bg_path = Store.backgrounds_dir() / f"starter_{tpl.ident}.jpg"
        template_path = Store.templates_dir() / f"starter_{tpl.ident}.json"
        preview_path = thumb_dir / f"starter_{tpl.ident}.jpg"
        if force or not bg_path.exists():
            bg = _make_background(tpl)
            bg.save(bg_path, quality=92)
            changed = True
        else:
            bg = Image.open(bg_path).convert("RGB")
        if force or not preview_path.exists():
            _preview(bg, tpl).save(preview_path, quality=90)
            changed = True
        payload = {
            "name": tpl.name,
            "preview_path": str(preview_path),
            "data": _payload(tpl, bg_path),
        }
        refresh_template = force or not template_path.exists()
        if not refresh_template:
            try:
                refresh_template = json.loads(template_path.read_text(encoding="utf-8")).get("name") != tpl.name
            except Exception:
                refresh_template = True
        if refresh_template:
            template_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            changed = True

    Store.mark_starter_pack_installed(VERSION)
    return changed
