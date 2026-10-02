#!/usr/bin/env python3
"""Photo Video Studio vNext: slideshow, templates, AI photo studio, and video tools."""

from __future__ import annotations

import os
import platform
import queue
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import customtkinter as ctk
    from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageTk
except Exception:
    r = tk.Tk()
    r.withdraw()
    messagebox.showerror("Kutubxona yo'q", "pip install -r requirements.txt (yoki run.bat).")
    sys.exit(1)

import image_enhance as AI
import connectivity
import pvs_storage as Store
import starter_pack
import studio_engine as SE
import updater
from version import APP_VERSION

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    DND_FILES = None
    TkinterDnD = None

if TkinterDnD is not None:
    try:
        class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.TkdndVersion = TkinterDnD._require(self)
    except Exception:
        CTkDnD = None
else:
    CTkDnD = None

HERE = os.path.dirname(os.path.abspath(__file__))
VC_SRC = os.path.join(HERE, "video_converter", "src")
if os.path.isdir(VC_SRC) and VC_SRC not in sys.path:
    sys.path.insert(0, VC_SRC)

try:
    from video_converter.converter import (
        AUDIO_ONLY_FORMATS,
        FRAME_RATES,
        QUALITY_PRESETS,
        RESOLUTIONS,
        SUPPORTED_FORMATS,
        build_conversion_args,
        convert,
    )
except Exception:
    AUDIO_ONLY_FORMATS = frozenset({"mp3", "wav"})
    FRAME_RATES = {"Original": None}
    QUALITY_PRESETS = ("Balanced",)
    RESOLUTIONS = {"Original": None}
    SUPPORTED_FORMATS = ("mp4",)
    build_conversion_args = convert = None

GIFDIR = os.path.join(HERE, "previews", "transitions")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
KB_LAT = {"subtle": "Yumshoq", "normal": "O'rta", "strong": "Kuchli"}
VIG_LAT = {"auto": "Avto", "on": "Yoqilgan", "off": "O'chirilgan"}
QUAL_LAT = {"16": "Yuqori (sekin)", "18": "Yaxshi", "21": "O'rta", "24": "Tez (kichik)"}
LAYOUT_LAT = {"center": "Markaz", "left": "Chap", "right": "O'ng", "top": "Yuqori", "bottom": "Past", "fill": "Katta"}
TEXT_TEMPLATES = ["family", "wedding", "eid", "memory", "ad", "minimal"]
TEXT_TEMPLATE_UZ = {
    "family": "Oilaviy",
    "wedding": "To'y",
    "eid": "Hayit",
    "memory": "Xotira",
    "ad": "Reklama",
    "minimal": "Minimal",
}
TEXT_TEMPLATE_VALUES = {
    "family": ("Oilaviy xotira", "MEHR BILAN", "Oilamizning quvonchi", "SEVGI BILAN"),
    "wedding": ("To'y muborak", "BAHTLI KUN", "Sevgi va hurmat bilan", "SEVGI BILAN"),
    "eid": ("Hayit muborak", "EZGU NIYATLAR", "Xonadoningiz fayzga to'lsin", "DUO BILAN"),
    "memory": ("Xotira", "YODDA QOLGAN ONLAR", "Mehr bilan eslaymiz", "HURMAT BILAN"),
    "ad": ("Mahsulot nomi", "REKLAMA", "Qisqa, aniq va ishonchli", "BOG'LANING"),
    "minimal": ("", "", "", ""),
}
ROW_BG = ("#e8e8ea", "#2b2b30")
ROW_SEL = ("#cfe0f7", "#35507a")

_PAIRS = [
    ("o‘", "ў"), ("o'", "ў"), ("O‘", "Ў"), ("O'", "Ў"), ("g‘", "ғ"), ("g'", "ғ"),
    ("G‘", "Ғ"), ("G'", "Ғ"), ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"), ("ch", "ч"),
    ("Ch", "Ч"), ("CH", "Ч"), ("yo", "ё"), ("Yo", "Ё"), ("YO", "Ё"), ("yu", "ю"),
    ("Yu", "Ю"), ("YU", "Ю"), ("ya", "я"), ("Ya", "Я"), ("YA", "Я"), ("ts", "ц"),
    ("Ts", "Ц"),
]
_SNG = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ", "i": "и",
    "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ",
    "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "x": "х", "y": "й", "z": "з",
    "c": "с", "w": "в", "A": "А", "B": "Б", "D": "Д", "E": "Е", "F": "Ф", "G": "Г",
    "H": "Ҳ", "I": "И", "J": "Ж", "K": "К", "L": "Л", "M": "М", "N": "Н", "O": "О",
    "P": "П", "Q": "Қ", "R": "Р", "S": "С", "T": "Т", "U": "У", "V": "В", "X": "Х",
    "Y": "Й", "Z": "З", "C": "С", "W": "В",
}


def lat2cyr(s: str) -> str:
    for a, b in _PAIRS:
        s = s.replace(a, b)
    return "".join(_SNG.get(ch, ch) for ch in s)


class App:
    def __init__(self, root: ctk.CTk):
        Store.ensure_dirs()
        starter_pack.install_if_needed()
        self.root = root
        root.title("Photo Video Studio")
        root.geometry("1260x790")
        root.minsize(1120, 720)

        self.lang = "lat"
        self.settings = Store.load_settings()
        self.items: list[dict] = []
        self.cur: int | None = None
        self.q: queue.Queue = queue.Queue()
        self.busy = False
        self.online = False
        self.update_info: updater.UpdateInfo | None = None
        self.preview_after = None
        self.preview_anim_after = None
        self.preview_job = 0
        self.preview_frames = []
        self.preview_frame_idx = 0
        self.ai_preview_after = None
        self.ai_preview_job = 0
        self.cancel_event = threading.Event()
        self.vc_cancel_event = threading.Event()
        self.row_frames: list = []
        self.row_txt: list = []
        self._imgs: list = []
        self._prev_img = None
        self._ai_img = None
        self._ai_tk = None
        self._ai_original_pil = None
        self._ai_enhanced_pil = None
        self._blank = None

        self.sel = {
            "grade": "auto",
            "trans": "auto",
            "kb": "normal",
            "vig": "auto",
            "qual": "18",
            "style": list(SE.STYLES.keys())[0],
            "layout": "center",
            "motion": "auto",
        }
        self.mvar: dict[str, tk.StringVar] = {}

        self.title_var = tk.StringVar(value="Xush kelibsan")
        self.kicker_var = tk.StringVar(value="XUSH KELIBSAN")
        self.date_var = tk.StringVar(value="")
        self.osub_var = tk.StringVar(value="Oilamizning quvonchi")
        self.okick_var = tk.StringVar(value="SEVGI BILAN KUTIB OLINDI")
        self.res_var = tk.StringVar(value="1440p (2K)")
        self.fps_var = tk.StringVar(value="30")
        self.preset_var = tk.StringVar(value="fast")
        self.dur_var = tk.DoubleVar(value=4.5)
        self.grain_var = tk.BooleanVar(value=False)
        self.bloom_var = tk.BooleanVar(value=False)
        self.cap_var = tk.StringVar()
        self.text_enabled_var = tk.BooleanVar(value=False)
        self.show_title_var = tk.BooleanVar(value=True)
        self.show_captions_var = tk.BooleanVar(value=True)
        self.show_outro_var = tk.BooleanVar(value=True)
        self.text_template_var = tk.StringVar(value=TEXT_TEMPLATE_UZ["family"])
        self.font_preset_var = tk.StringVar(value=SE.FONT_UZ["default"])
        self.slide_global_var = tk.BooleanVar(value=True)
        self.slide_duration_var = tk.DoubleVar(value=4.5)
        self.slide_motion_var = tk.StringVar(value="")
        self.music_mode = tk.StringVar(value="auto")
        self.music_path = tk.StringVar(value="")
        self.out_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "video.mp4"))

        self.bg_path = tk.StringVar(value=self.settings.get("last_background", ""))
        self.photo_scale = tk.DoubleVar(value=0.66)
        self.frame_var = tk.BooleanVar(value=True)
        self.shadow_var = tk.BooleanVar(value=True)
        self.radius_var = tk.DoubleVar(value=0)

        self.ai_brightness = tk.DoubleVar(value=1.0)
        self.ai_contrast = tk.DoubleVar(value=1.08)
        self.ai_saturation = tk.DoubleVar(value=1.12)
        self.ai_warmth = tk.DoubleVar(value=0.08)
        self.ai_sharpness = tk.DoubleVar(value=1.25)
        self.ai_denoise = tk.DoubleVar(value=0.12)
        self.ai_upscale = tk.StringVar(value="auto")
        self.ai_face = tk.BooleanVar(value=True)
        self.ai_compare = tk.DoubleVar(value=50)
        self.ai_preset_var = tk.StringVar(value=AI.AI_PRESETS["auto"])

        self.provider_var = tk.StringVar(value=self.settings.get("provider", "openai"))
        self.model_var = tk.StringVar(value=self.settings.get("openai_model", "gpt-image-2.5-sunburst"))
        self.openai_quality_var = tk.StringVar(value=self.settings.get("openai_quality", "medium"))
        self.consent_var = tk.BooleanVar(value=bool(self.settings.get("ai_consent", False)))
        self.key_var = tk.StringVar(value="")

        self.vc_input: Path | None = None
        self.vc_output_dir: Path | None = None
        self.vc_format = tk.StringVar(value=SUPPORTED_FORMATS[0])
        self.vc_res = tk.StringVar(value=list(RESOLUTIONS.keys())[0])
        self.vc_fps = tk.StringVar(value=list(FRAME_RATES.keys())[0])
        self.vc_quality = tk.StringVar(value=QUALITY_PRESETS[0])

        self.F = ctk.CTkFont(size=15)
        self.FB = ctk.CTkFont(size=15, weight="bold")
        self.FH = ctk.CTkFont(size=17, weight="bold")
        self.FBIG = ctk.CTkFont(size=25, weight="bold")
        self._build()
        self.root.after(200, self._check_ffmpeg)
        self.root.after(300, self.refresh_connectivity)

    def t(self, s: str) -> str:
        return s if self.lang == "lat" else lat2cyr(s)

    def _build(self) -> None:
        self._blank = ctk.CTkImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), size=(1, 1))
        head = ctk.CTkFrame(self.root, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(12, 4))
        ctk.CTkLabel(head, text="Photo Video Studio", font=self.FBIG).pack(side="left")
        ctk.CTkLabel(head, text=f"v{APP_VERSION}", text_color="#8a8a8a", font=self.F).pack(side="left", padx=(8, 0), pady=(8, 0))
        seg = ctk.CTkSegmentedButton(head, values=["Lotin", "Кирил"], font=self.FB, command=self._lang)
        seg.set("Lotin" if self.lang == "lat" else "Кирил")
        seg.pack(side="right")
        ctk.CTkLabel(head, text=self.t("Yozuv:"), font=self.F).pack(side="right", padx=(0, 8))

        self.tabs = ctk.CTkTabview(self.root)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=(2, 4))
        self.tab_names = {
            "slideshow": self.t("Slideshow"),
            "backgrounds": self.t("Fonlar/Shablonlar"),
            "ai": self.t("AI Rasm Studio"),
            "tools": self.t("Video Tools"),
            "settings": self.t("Sozlamalar"),
        }
        for name in self.tab_names.values():
            self.tabs.add(name)

        self._build_slideshow_tab(self.tabs.tab(self.tab_names["slideshow"]))
        self._build_background_tab(self.tabs.tab(self.tab_names["backgrounds"]))
        self._build_ai_tab(self.tabs.tab(self.tab_names["ai"]))
        self._build_video_tools_tab(self.tabs.tab(self.tab_names["tools"]))
        self._build_settings_tab(self.tabs.tab(self.tab_names["settings"]))
        self._build_bottom()
        self._rebuild()
        self._refresh_backgrounds()
        self._refresh_templates()
        self._try_enable_drag_drop()

    def _build_bottom(self) -> None:
        self.bottom = ctk.CTkFrame(self.root, fg_color="transparent")
        self.bottom.pack(fill="x", padx=18, pady=(4, 4))
        self.gen_btn = ctk.CTkButton(self.bottom, text=self.t("VIDEO YARATISH"), height=50, font=ctk.CTkFont(size=18, weight="bold"), command=self.generate)
        self.gen_btn.pack(side="left")
        self.prev_btn = ctk.CTkButton(self.bottom, text=self.t("Qisqa namuna"), height=50, width=180, font=self.FB, fg_color="#3a7d44", hover_color="#2f6838", command=self.preview_sample)
        self.prev_btn.pack(side="left", padx=8)
        self.open_btn = ctk.CTkButton(self.bottom, text=self.t("Papka"), width=90, height=50, font=self.F, fg_color="#5a5a5a", command=self.open_output, state="disabled")
        self.open_btn.pack(side="left", padx=(0, 8))
        self.cancel_btn = ctk.CTkButton(self.bottom, text=self.t("Bekor qilish"), width=130, height=50, font=self.FB, fg_color="#8a3c3c", hover_color="#703030", command=self.cancel_current_job, state="disabled")
        self.cancel_btn.pack(side="left", padx=(0, 8))
        self.pbar = ctk.CTkProgressBar(self.bottom, height=16)
        self.pbar.set(0)
        self.pbar.pack(side="left", fill="x", expand=True, padx=12)
        self.status = ctk.CTkLabel(self.bottom, text=self.t("Tayyor"), width=170, anchor="e", font=self.FB)
        self.status.pack(side="right")

        self.ffrow = ctk.CTkFrame(self.root, fg_color="transparent")
        self.ffrow.pack(fill="x", padx=18, pady=(0, 10))
        self.ff_lbl = ctk.CTkLabel(self.ffrow, text="ffmpeg...", text_color="#8a8a8a", font=self.F)
        self.ff_lbl.pack(side="left")
        self.net_lbl = ctk.CTkLabel(self.ffrow, text=self.t("Internet: tekshirilmoqda..."), text_color="#8a8a8a", font=self.F)
        self.net_lbl.pack(side="left", padx=16)
        ctk.CTkButton(self.ffrow, text=self.t("ffmpeg.exe ni ko'rsatish"), width=210, height=34, font=self.F, fg_color="#5a5a5a", command=self.pick_ffmpeg).pack(side="right")

    def _build_slideshow_tab(self, parent) -> None:
        self.body = ctk.CTkFrame(parent, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=4, pady=4)
        left = ctk.CTkFrame(self.body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        ctk.CTkLabel(left, text=self.t("1) Rasmlaringiz"), font=self.FH).pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkLabel(left, text=self.t("Bosib tanlang, tartiblang, caption yozing"), text_color="#8a8a8a", font=self.F).pack(anchor="w", padx=12)
        self.dnd_status = ctk.CTkLabel(left, text=self.t("Rasm qo'shish tugmasi orqali tanlang."), text_color="#8a8a8a", font=self.F)
        self.dnd_status.pack(anchor="w", padx=12, pady=(2, 0))
        self.strip = ctk.CTkScrollableFrame(left, height=190)
        self.strip.pack(fill="both", expand=True, padx=10, pady=(6, 0))
        pb = ctk.CTkFrame(left, fg_color="transparent")
        pb.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(pb, text=self.t("+ Rasm qo'shish"), height=42, font=self.FB, command=self.add_photos).pack(side="left")
        ctk.CTkButton(pb, text=self.t("O'chirish"), width=110, height=42, font=self.FB, fg_color="#5a5a5a", command=self.remove_photo).pack(side="left", padx=6)
        ctk.CTkButton(pb, text="↑", width=46, height=42, font=self.FB, fg_color="#5a5a5a", command=lambda: self.move(-1)).pack(side="left")
        ctk.CTkButton(pb, text="↓", width=46, height=42, font=self.FB, fg_color="#5a5a5a", command=lambda: self.move(1)).pack(side="left", padx=(4, 0))
        pr = ctk.CTkFrame(left, fg_color="transparent")
        pr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(pr, text=self.t("Ko'rinish"), font=self.FB).pack(side="left")
        ctk.CTkButton(pr, text=self.t("Aniq ko'rish"), width=120, height=32, fg_color="#5a5a5a", command=self.update_preview_exact).pack(side="right")
        pv = ctk.CTkFrame(left)
        pv.pack(fill="x", padx=10, pady=(0, 8))
        self.preview_lbl = ctk.CTkLabel(pv, text=self.t("Rasm tanlanmagan"), height=245, font=self.F, fg_color=("#dcdce0", "#232327"), corner_radius=8)
        self.preview_lbl.pack(fill="x", padx=6, pady=6)
        cf = ctk.CTkFrame(left, fg_color="transparent")
        cf.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(cf, text=self.t("Shu rasm ustidagi yozuv:"), font=self.F).pack(anchor="w")
        ce = ctk.CTkEntry(cf, textvariable=self.cap_var, height=40, font=self.F)
        ce.pack(fill="x", pady=(2, 0))
        ce.bind("<KeyRelease>", lambda _e: (self._save_caption(), self._schedule_preview_update()))

        per = ctk.CTkFrame(left, fg_color="transparent")
        per.pack(fill="x", padx=10, pady=(0, 10))
        self.slide_global_switch = ctk.CTkSwitch(per, text=self.t("Global vaqtni ishlatish"), variable=self.slide_global_var, font=self.F, command=self._toggle_slide_duration)
        self.slide_global_switch.pack(anchor="w")
        self.slide_duration_lbl = ctk.CTkLabel(per, text="4.5 s", font=self.F)
        self.slide_duration_lbl.pack(anchor="e")
        self.slide_duration_slider = ctk.CTkSlider(per, from_=1.0, to=12.0, number_of_steps=44, variable=self.slide_duration_var, command=self._slide_duration_changed)
        self.slide_duration_slider.pack(fill="x")
        ctk.CTkLabel(per, text=self.t("Ushbu rasm harakati"), font=self.F, anchor="w").pack(fill="x", pady=(8, 0))
        self.slide_motion_menu = ctk.CTkOptionMenu(per, values=[self.t(SE.MOTION_UZ[k]) for k in SE.MOTION_PRESETS], variable=self.slide_motion_var, height=36, command=self._slide_motion_changed)
        self.slide_motion_menu.pack(fill="x")

        right = ctk.CTkScrollableFrame(self.body, width=430, label_text=self.t("2) Sozlamalar"))
        right.pack(side="right", fill="y")
        self._settings_controls(right)

    def _settings_controls(self, parent) -> None:
        def h2(txt):
            ctk.CTkLabel(parent, text=self.t(txt), font=self.FH, anchor="w").pack(fill="x", padx=8, pady=(12, 2))

        def ent(lab, var):
            ctk.CTkLabel(parent, text=self.t(lab), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(8, 0))
            ctk.CTkEntry(parent, textvariable=var, height=38, font=self.F).pack(fill="x", padx=8)

        def optplain(lab, values, var):
            ctk.CTkLabel(parent, text=self.t(lab), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(8, 0))
            ctk.CTkOptionMenu(parent, values=list(values), variable=var, height=38, font=self.F).pack(fill="x", padx=8)

        h2("Uslub va matnlar")
        self._opttr(parent, "Uslub", list(SE.STYLES.keys()), {k: k for k in SE.STYLES}, "style", extra=self._schedule_preview_update)
        ctk.CTkSwitch(parent, text=self.t("Matn qo'shilsin"), variable=self.text_enabled_var, font=self.FB, command=self._text_enabled_changed).pack(anchor="w", padx=10, pady=(10, 0))
        ctk.CTkSwitch(parent, text=self.t("Boshlanish titri"), variable=self.show_title_var, font=self.F, command=self._schedule_preview_update).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkSwitch(parent, text=self.t("Har rasm yozuvi"), variable=self.show_captions_var, font=self.F, command=self._schedule_preview_update).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkSwitch(parent, text=self.t("Yakun titri"), variable=self.show_outro_var, font=self.F, command=self._schedule_preview_update).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(parent, text=self.t("Matn shabloni"), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkOptionMenu(parent, values=[self.t(TEXT_TEMPLATE_UZ[k]) for k in TEXT_TEMPLATES], variable=self.text_template_var, height=38, font=self.F, command=self._text_template_changed).pack(fill="x", padx=8)
        ctk.CTkLabel(parent, text=self.t("Font"), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkOptionMenu(parent, values=[self.t(SE.FONT_UZ[k]) for k in SE.FONT_PRESETS], variable=self.font_preset_var, height=38, font=self.F, command=lambda _v: self._schedule_preview_update()).pack(fill="x", padx=8)
        ent("Sarlavha", self.title_var)
        ent("Yuqori yozuv", self.kicker_var)
        ent("Sana", self.date_var)
        ent("Yakun izohi", self.osub_var)
        ent("Yakun yozuvi", self.okick_var)

        h2("Fon va joylashuv")
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(6, 0))
        ctk.CTkButton(row, text=self.t("Fon tanlash"), height=38, font=self.F, command=self.import_background).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text=self.t("Fonsiz"), width=90, height=38, fg_color="#5a5a5a", command=self.clear_background).pack(side="left", padx=(6, 0))
        self._opttr(parent, "Rasm joyi", list(LAYOUT_LAT.keys()), LAYOUT_LAT, "layout", extra=self._schedule_preview_update)
        ctk.CTkLabel(parent, text=self.t("Rasm kattaligi"), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkSlider(parent, from_=0.25, to=0.92, variable=self.photo_scale, command=lambda _v: self._schedule_preview_update()).pack(fill="x", padx=8)
        ctk.CTkSwitch(parent, text=self.t("Oq ramka"), variable=self.frame_var, font=self.F, command=self._schedule_preview_update).pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkSwitch(parent, text=self.t("Soya"), variable=self.shadow_var, font=self.F, command=self._schedule_preview_update).pack(anchor="w", padx=10, pady=(6, 0))

        h2("Effektlar")
        self._opttr(parent, "Rang", SE.GRADES, SE.GRADE_UZ, "grade", extra=self._schedule_preview_update, gallery=self.gallery_grade)
        self._opttr(parent, "O'tish effekti", SE.TRANSITIONS, SE.TRANS_UZ, "trans", gallery=self.gallery_trans)
        self._opttr(parent, "Harakat (zoom) kuchi", ["subtle", "normal", "strong"], KB_LAT, "kb", extra=self._schedule_preview_update)
        self._opttr(parent, "Umumiy rasm harakati", SE.MOTION_PRESETS, SE.MOTION_UZ, "motion", extra=self._schedule_preview_update)
        self._opttr(parent, "Vignette", ["auto", "on", "off"], VIG_LAT, "vig", extra=self._schedule_preview_update)
        ctk.CTkSwitch(parent, text=self.t("Film grain (don)"), variable=self.grain_var, font=self.F, command=self._schedule_preview_update).pack(anchor="w", padx=10, pady=(10, 0))
        ctk.CTkSwitch(parent, text=self.t("Bloom (porlash)"), variable=self.bloom_var, font=self.F, command=self._schedule_preview_update).pack(anchor="w", padx=10, pady=(8, 0))

        h2("Sifat va format")
        optplain("O'lcham", list(SE.RES.keys()), self.res_var)
        optplain("FPS (silliqlik)", ["24", "30", "60"], self.fps_var)
        self._opttr(parent, "Sifat", ["16", "18", "21", "24"], QUAL_LAT, "qual")
        optplain("Tezlik", ["ultrafast", "veryfast", "fast", "medium", "slow"], self.preset_var)
        ctk.CTkLabel(parent, text=self.t("Har rasm necha soniya"), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(10, 0))
        self.dur_lbl = ctk.CTkLabel(parent, text=f"{self.dur_var.get():.1f} s", font=self.F)
        self.dur_lbl.pack(anchor="e", padx=8)
        ctk.CTkSlider(parent, from_=2.0, to=8.0, number_of_steps=30, variable=self.dur_var, command=self._global_duration_changed).pack(fill="x", padx=8)

        h2("Musiqa va chiqish")
        mf = ctk.CTkFrame(parent, fg_color="transparent")
        mf.pack(fill="x", padx=8, pady=(6, 0))
        msb = ctk.CTkSegmentedButton(mf, values=[self.t("Avto"), self.t("Fayl")], font=self.F, command=self._music_seg)
        msb.set(self.t("Avto") if self.music_mode.get() == "auto" else self.t("Fayl"))
        msb.pack(side="left")
        ctk.CTkButton(mf, text="...", width=44, height=34, command=self.pick_music).pack(side="left", padx=6)
        of = ctk.CTkFrame(parent, fg_color="transparent")
        of.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkEntry(of, textvariable=self.out_var, height=38, font=self.F).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(of, text="...", width=44, height=38, command=self.pick_output).pack(side="left", padx=(6, 0))

    def _opttr(self, parent, lab, keys, latmap, selkey, extra=None, gallery=None):
        ctk.CTkLabel(parent, text=self.t(lab), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(8, 0))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8)
        disp = [self.t(latmap[k]) for k in keys]
        rev = {self.t(latmap[k]): k for k in keys}
        var = tk.StringVar(value=self.t(latmap[self.sel[selkey]]))
        self.mvar[selkey] = var

        def on(ch):
            self.sel[selkey] = rev.get(ch, self.sel[selkey])
            if extra:
                extra()

        ctk.CTkOptionMenu(row, values=disp, variable=var, height=38, font=self.F, command=on).pack(side="left", fill="x", expand=True)
        if gallery:
            ctk.CTkButton(row, text=self.t("ko'rish"), width=98, height=38, font=self.F, fg_color="#3a7d44", hover_color="#2f6838", command=gallery).pack(side="left", padx=(6, 0))

    def _motion_key_from_label(self, label: str) -> str:
        for key in SE.MOTION_PRESETS:
            if label == self.t(SE.MOTION_UZ[key]):
                return key
        return "auto"

    def _motion_label(self, key: str) -> str:
        return self.t(SE.MOTION_UZ.get(key if key in SE.MOTION_PRESETS else "auto", SE.MOTION_UZ["auto"]))

    def _font_preset_key(self) -> str:
        label = self.font_preset_var.get()
        for key in SE.FONT_PRESETS:
            if label == self.t(SE.FONT_UZ[key]):
                return key
        return "default"

    def _text_template_key(self) -> str:
        label = self.text_template_var.get()
        for key in TEXT_TEMPLATES:
            if label == self.t(TEXT_TEMPLATE_UZ[key]):
                return key
        return "family"

    def _text_enabled_changed(self) -> None:
        if self.text_enabled_var.get():
            self.show_title_var.set(True)
            self.show_captions_var.set(True)
            self.show_outro_var.set(True)
        self._schedule_preview_update()

    def _text_template_changed(self, label=None) -> None:
        key = self._text_template_key()
        title, kicker, subtitle, outro = TEXT_TEMPLATE_VALUES.get(key, TEXT_TEMPLATE_VALUES["family"])
        self.title_var.set(title)
        self.kicker_var.set(kicker)
        self.osub_var.set(subtitle)
        self.okick_var.set(outro)
        self.text_enabled_var.set(key != "minimal")
        self.show_title_var.set(key != "minimal")
        self.show_captions_var.set(key != "minimal")
        self.show_outro_var.set(key != "minimal")
        self._schedule_preview_update()

    def _schedule_preview_update(self, delay: int = 140) -> None:
        if self.preview_after is not None:
            try:
                self.root.after_cancel(self.preview_after)
            except Exception:
                pass
        self.preview_after = self.root.after(delay, self._run_scheduled_preview)

    def _run_scheduled_preview(self) -> None:
        self.preview_after = None
        self._update_preview()

    def _global_duration_changed(self, value) -> None:
        seconds = float(value)
        self.dur_lbl.configure(text=f"{seconds:.1f} s")
        if self.cur is not None and self.slide_global_var.get():
            self.slide_duration_var.set(seconds)
            self.slide_duration_lbl.configure(text=f"{seconds:.1f} s")

    def _toggle_slide_duration(self) -> None:
        if self.cur is None:
            return
        if self.slide_global_var.get():
            self.items[self.cur]["duration_override"] = None
            self.slide_duration_var.set(float(self.dur_var.get()))
            state = "disabled"
        else:
            value = float(self.slide_duration_var.get() or self.dur_var.get())
            self.items[self.cur]["duration_override"] = value
            state = "normal"
        self.slide_duration_slider.configure(state=state)
        self.slide_duration_lbl.configure(text=f"{float(self.slide_duration_var.get()):.1f} s")
        self._refresh_row_text(self.cur)

    def _slide_duration_changed(self, value) -> None:
        seconds = float(value)
        self.slide_duration_lbl.configure(text=f"{seconds:.1f} s")
        if self.cur is not None and not self.slide_global_var.get():
            self.items[self.cur]["duration_override"] = seconds
            self._refresh_row_text(self.cur)

    def _slide_motion_changed(self, label) -> None:
        if self.cur is None:
            return
        self.items[self.cur]["motion_preset"] = self._motion_key_from_label(label)
        self._refresh_row_text(self.cur)
        self._schedule_preview_update()

    def _set_slide_controls_from_item(self, idx: int) -> None:
        if not (0 <= idx < len(self.items)):
            return
        item = self.items[idx]
        override = item.get("duration_override")
        use_global = override is None
        self.slide_global_var.set(use_global)
        seconds = float(self.dur_var.get() if use_global else override)
        self.slide_duration_var.set(seconds)
        self.slide_duration_lbl.configure(text=f"{seconds:.1f} s")
        self.slide_duration_slider.configure(state="disabled" if use_global else "normal")
        motion = item.get("motion_preset") or self.sel.get("motion", "auto")
        if motion not in SE.MOTION_PRESETS:
            motion = "auto"
        self.slide_motion_var.set(self._motion_label(motion))

    def _save_current_item_controls(self) -> None:
        self._save_caption()
        if self.cur is None or not (0 <= self.cur < len(self.items)):
            return
        item = self.items[self.cur]
        item["duration_override"] = None if self.slide_global_var.get() else float(self.slide_duration_var.get())
        item["motion_preset"] = self._motion_key_from_label(self.slide_motion_var.get())
        self._refresh_row_text(self.cur)

    def _refresh_row_text(self, idx: int) -> None:
        if 0 <= idx < len(self.row_txt):
            self.row_txt[idx].configure(text=self._rowtext(idx))

    def _build_background_tab(self, parent) -> None:
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(top, text=self.t("Yangi background qo'shish"), height=42, font=self.FB, command=self.import_background).pack(side="left")
        ctk.CTkButton(top, text=self.t("Fonsiz ishlatish"), height=42, width=150, fg_color="#5a5a5a", command=self.clear_background).pack(side="left", padx=8)
        ctk.CTkButton(top, text=self.t("Starter packni qayta o'rnatish"), height=42, width=210, fg_color="#5a5a5a", command=self.reinstall_starter_pack).pack(side="left")
        ctk.CTkButton(top, text=self.t("Shablon sifatida saqlash"), height=42, command=self.save_template_prompt).pack(side="right")
        self.bg_current = ctk.CTkLabel(parent, text="", font=self.FB, anchor="w")
        self.bg_current.pack(fill="x", padx=12)
        mid = ctk.CTkFrame(parent, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=10, pady=8)
        self.bg_list = ctk.CTkScrollableFrame(mid, label_text=self.t("Backgroundlar"))
        self.bg_list.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.template_list = ctk.CTkScrollableFrame(mid, width=470, label_text=self.t("Shablonlar"))
        self.template_list.pack(side="right", fill="y")

    def _build_ai_tab(self, parent) -> None:
        left = ctk.CTkFrame(parent)
        left.pack(side="left", fill="both", expand=True, padx=(10, 6), pady=10)
        right = ctk.CTkScrollableFrame(parent, width=390, label_text=self.t("Professional panel"))
        right.pack(side="right", fill="y", padx=(6, 10), pady=10)
        self.ai_title = ctk.CTkLabel(left, text=self.t("Rasm tanlang va OpenAI bilan professional sozlang"), font=self.FH)
        self.ai_title.pack(anchor="w", padx=12, pady=(12, 4))
        self.ai_canvas = tk.Canvas(left, height=430, bd=0, highlightthickness=0, bg="#232327")
        self.ai_canvas.pack(fill="both", expand=True, padx=12, pady=8)
        self.ai_canvas.bind("<Configure>", lambda _e: self._draw_ai_compare())
        self.ai_canvas.bind("<Button-1>", self._drag_ai_compare)
        self.ai_canvas.bind("<B1-Motion>", self._drag_ai_compare)
        ctk.CTkLabel(left, text=self.t("Chiziqni ushlab suring: chap tomonda oldingi, o'ng tomonda keyingi natija."), text_color="#8a8a8a", font=self.F).pack(anchor="w", padx=12, pady=(0, 12))

        def slider(label, var, lo, hi):
            ctk.CTkLabel(right, text=self.t(label), font=self.F, anchor="w").pack(fill="x", padx=8, pady=(10, 0))
            ctk.CTkSlider(right, from_=lo, to=hi, variable=var, command=lambda _v: self._update_ai_preview_only()).pack(fill="x", padx=8)

        ctk.CTkLabel(right, text=self.t("Bu panel original rasmni o'zgartirmaydi. Natija cache'da saqlanadi."), text_color="#8a8a8a", font=self.F).pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(right, text=self.t("AI preset"), font=self.F, anchor="w").pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkOptionMenu(right, values=[self.t(AI.AI_PRESETS[k]) for k in AI.AI_PRESETS], variable=self.ai_preset_var, height=38).pack(fill="x", padx=8)
        slider("Yorug'lik", self.ai_brightness, 0.65, 1.45)
        slider("Kontrast", self.ai_contrast, 0.7, 1.6)
        slider("Rang to'yinganligi", self.ai_saturation, 0.5, 1.8)
        slider("Iliqlik / sovuqlik", self.ai_warmth, -0.7, 0.7)
        slider("Aniqlik", self.ai_sharpness, 0.6, 2.4)
        slider("Shovqinni kamaytirish", self.ai_denoise, 0.0, 0.55)
        ctk.CTkLabel(right, text=self.t("Upscale"), font=self.F, anchor="w").pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkOptionMenu(right, values=["auto", "none", "HD", "2K", "4K"], variable=self.ai_upscale, height=38, command=lambda _v: self._update_ai_preview_only()).pack(fill="x", padx=8)
        ctk.CTkSwitch(right, text=self.t("Face-safe restore"), variable=self.ai_face, font=self.F, command=self._update_ai_preview_only).pack(anchor="w", padx=10, pady=(10, 4))
        ctk.CTkButton(right, text=self.t("OpenAI bilan tanlangan rasmni tuzatish"), height=42, font=self.FB, fg_color="#6b4fa3", command=self.apply_openai_selected).pack(fill="x", padx=8, pady=(14, 4))
        ctk.CTkButton(right, text=self.t("Hammasini OpenAI bilan tuzatish"), height=42, font=self.FB, fg_color="#3a7d44", command=lambda: self.apply_openai_all()).pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(right, text=self.t("Originalga qaytish"), height=38, fg_color="#5a5a5a", command=self.reset_selected_ai).pack(fill="x", padx=8, pady=4)

    def _build_video_tools_tab(self, parent) -> None:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(frame, text=self.t("Video Tools"), font=self.FBIG).pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkLabel(frame, text=self.t("MP4 qilish, hajm kichraytirish, audio ajratish yoki GIF/WEBM yaratish."), text_color="#8a8a8a", font=self.F).pack(anchor="w", padx=14)
        self.vc_input_lbl = ctk.CTkLabel(frame, text=self.t("Fayl tanlanmagan"), font=self.F, anchor="w")
        self.vc_input_lbl.pack(fill="x", padx=14, pady=(18, 4))
        ctk.CTkButton(frame, text=self.t("Video/audio fayl tanlash"), height=42, command=self.vc_choose_input).pack(fill="x", padx=14)
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=12)
        self._vc_menu(grid, "Format", self.vc_format, SUPPORTED_FORMATS, 0)
        self._vc_menu(grid, "O'lcham", self.vc_res, list(RESOLUTIONS.keys()), 1)
        self._vc_menu(grid, "FPS", self.vc_fps, list(FRAME_RATES.keys()), 2)
        self._vc_menu(grid, "Sifat", self.vc_quality, QUALITY_PRESETS, 3)
        self.vc_out_lbl = ctk.CTkLabel(frame, text=self.t("Chiqish papkasi: fayl yonida"), font=self.F, anchor="w")
        self.vc_out_lbl.pack(fill="x", padx=14, pady=(4, 4))
        ctk.CTkButton(frame, text=self.t("Chiqish papkasini tanlash"), height=38, fg_color="#5a5a5a", command=self.vc_choose_output).pack(fill="x", padx=14)
        self.vc_progress = ctk.CTkProgressBar(frame, height=16)
        self.vc_progress.set(0)
        self.vc_progress.pack(fill="x", padx=14, pady=(18, 6))
        self.vc_status = ctk.CTkLabel(frame, text=self.t("Tayyor"), font=self.FB, anchor="w")
        self.vc_status.pack(fill="x", padx=14)
        self.vc_button = ctk.CTkButton(frame, text=self.t("Konvertatsiya qilish"), height=48, font=self.FB, command=self.vc_start)
        self.vc_button.pack(fill="x", padx=14, pady=(18, 6))
        self.vc_cancel_btn = ctk.CTkButton(frame, text=self.t("Bekor qilish"), height=42, font=self.FB, fg_color="#8a3c3c", hover_color="#703030", command=self.cancel_current_job, state="disabled")
        self.vc_cancel_btn.pack(fill="x", padx=14, pady=(0, 18))

    def _vc_menu(self, parent, label, var, values, col):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=0, column=col, sticky="ew", padx=5)
        parent.grid_columnconfigure(col, weight=1)
        ctk.CTkLabel(cell, text=self.t(label), font=self.F, anchor="w").pack(fill="x")
        ctk.CTkOptionMenu(cell, values=list(values), variable=var, height=38).pack(fill="x")

    def _build_settings_tab(self, parent) -> None:
        box = ctk.CTkScrollableFrame(parent, label_text=self.t("AI kalitlar va maxfiylik"))
        box.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(box, text=self.t("API key loyiha fayliga yozilmaydi. Windows Credential Manager/keyring ishlatiladi."), text_color="#8a8a8a", font=self.F).pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(box, text=self.t("OpenAI API key"), font=self.FB, anchor="w").pack(fill="x", padx=8, pady=(12, 0))
        ctk.CTkEntry(box, textvariable=self.key_var, show="*", height=40, font=self.F).pack(fill="x", padx=8, pady=(2, 8))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=8)
        ctk.CTkButton(row, text=self.t("Saqlash"), height=38, command=self.save_api_key).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text=self.t("Tekshirish"), height=38, fg_color="#3a7d44", command=self.test_api_key).pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkButton(row, text=self.t("O'chirish"), height=38, fg_color="#5a5a5a", command=self.delete_api_key).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(box, text=self.t("OpenAI model"), font=self.F, anchor="w").pack(fill="x", padx=8, pady=(16, 0))
        ctk.CTkEntry(box, textvariable=self.model_var, height=38, font=self.F).pack(fill="x", padx=8)
        ctk.CTkLabel(box, text=self.t("OpenAI sifat"), font=self.F, anchor="w").pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkOptionMenu(box, values=["low", "medium", "high", "xhigh", "max"], variable=self.openai_quality_var, height=38).pack(fill="x", padx=8)
        ctk.CTkSwitch(box, text=self.t("AI ishlaganda rasm internet orqali yuborilishiga roziman"), variable=self.consent_var, font=self.F, command=self.save_settings).pack(anchor="w", padx=10, pady=(14, 4))
        ctk.CTkButton(box, text=self.t("Sozlamalarni saqlash"), height=40, command=self.save_settings).pack(fill="x", padx=8, pady=(12, 8))
        ctk.CTkLabel(box, text=self.t("Dastur yangilanishi"), font=self.FB, anchor="w").pack(fill="x", padx=8, pady=(20, 0))
        ctk.CTkLabel(box, text=f"{self.t('Joriy versiya')}: {APP_VERSION}", text_color="#8a8a8a", font=self.F, anchor="w").pack(fill="x", padx=8, pady=(2, 6))
        row_update = ctk.CTkFrame(box, fg_color="transparent")
        row_update.pack(fill="x", padx=8)
        self.update_btn = ctk.CTkButton(row_update, text=self.t("Yangilanishni tekshirish"), height=38, command=self.check_update)
        self.update_btn.pack(side="left", fill="x", expand=True)
        self.download_update_btn = ctk.CTkButton(row_update, text=self.t("Yuklab olish"), height=38, fg_color="#3a7d44", command=self.download_update, state="disabled")
        self.download_update_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.update_status = ctk.CTkLabel(box, text=self.t("GitHub Releases orqali tekshiriladi."), text_color="#8a8a8a", font=self.F, anchor="w")
        self.update_status.pack(fill="x", padx=8, pady=(6, 4))
        self.settings_status = ctk.CTkLabel(box, text="", font=self.F, anchor="w")
        self.settings_status.pack(fill="x", padx=8, pady=8)

    def _lang(self, val):
        self._save_current_item_controls()
        old_cur = self.cur
        text_key = self._text_template_key()
        font_key = self._font_preset_key()
        old_tab = None
        if hasattr(self, "tabs") and hasattr(self, "tab_names"):
            try:
                current_name = self.tabs.get()
                for key, name in self.tab_names.items():
                    if name == current_name:
                        old_tab = key
                        break
            except Exception:
                old_tab = None
        for after_id in (self.preview_after, self.preview_anim_after, self.ai_preview_after):
            if after_id is not None:
                try:
                    self.root.after_cancel(after_id)
                except Exception:
                    pass
        self.preview_after = None
        self.preview_anim_after = None
        self.ai_preview_after = None
        self.ai_preview_job += 1
        self.lang = "lat" if val == "Lotin" else "cyr"
        self.text_template_var.set(self.t(TEXT_TEMPLATE_UZ.get(text_key, TEXT_TEMPLATE_UZ["family"])))
        self.font_preset_var.set(self.t(SE.FONT_UZ.get(font_key, SE.FONT_UZ["default"])))
        for w in self.root.winfo_children():
            w.destroy()
        self._build()

        def restore():
            if old_tab and old_tab in getattr(self, "tab_names", {}):
                try:
                    self.tabs.set(self.tab_names[old_tab])
                except Exception:
                    pass
            if old_cur is not None and 0 <= old_cur < len(self.items):
                self.cur = None
                self.select(old_cur)
            elif self.items:
                self.select(0)

        self.root.after_idle(restore)

    def _check_ffmpeg(self):
        if SE.find_ffmpeg():
            self.ff_lbl.configure(text="ffmpeg: ok", text_color="#4caf50")
        else:
            self.ff_lbl.configure(text="ffmpeg: topilmadi", text_color="#e05a5a")
            messagebox.showwarning("ffmpeg", self.t("ffmpeg topilmadi. winget install Gyan.FFmpeg yoki 'ffmpeg.exe ni ko'rsatish'."))

    def refresh_connectivity(self):
        def worker():
            status = connectivity.check_online()
            self.root.after(0, self._set_connectivity, status)

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(60000, self.refresh_connectivity)

    def _set_connectivity(self, status: connectivity.ConnectivityStatus):
        self.online = bool(status.online)
        if hasattr(self, "net_lbl"):
            if self.online:
                self.net_lbl.configure(text=self.t("Internet: Online"), text_color="#4caf50")
            else:
                self.net_lbl.configure(text=self.t("Internet: Offline"), text_color="#e0a84c")

    def check_update(self):
        if hasattr(self, "update_btn"):
            self.update_btn.configure(state="disabled")
            self.download_update_btn.configure(state="disabled")
            self.update_status.configure(text=self.t("Yangilanish tekshirilmoqda..."), text_color="#8a8a8a")

        def worker():
            try:
                info = updater.check_for_update()
                self.root.after(0, self._update_check_done, info, "")
            except Exception as exc:
                self.root.after(0, self._update_check_done, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _update_check_done(self, info, error):
        if hasattr(self, "update_btn"):
            self.update_btn.configure(state="normal")
        if error:
            if hasattr(self, "update_status"):
                self.update_status.configure(text=self.t("Yangilanish tekshirilmadi. Internetni tekshiring."), text_color="#e05a5a")
            return
        self.update_info = info
        if info and info.available:
            self.download_update_btn.configure(state="normal")
            self.update_status.configure(
                text=f"{self.t('Yangi versiya topildi')}: {info.latest_version}",
                text_color="#4caf50",
            )
        else:
            self.download_update_btn.configure(state="disabled")
            self.update_status.configure(text=self.t("Sizda eng yangi versiya."), text_color="#4caf50")

    def download_update(self):
        info = self.update_info
        if not info or not info.available:
            messagebox.showinfo(self.t("Yangilanish"), self.t("Avval yangilanishni tekshiring."))
            return
        self.download_update_btn.configure(state="disabled")
        self.update_status.configure(text=self.t("Setup yuklab olinmoqda..."), text_color="#8a8a8a")

        def worker():
            try:
                path = updater.download_update(info)
                self.root.after(0, self._download_update_done, path, "")
            except Exception as exc:
                self.root.after(0, self._download_update_done, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _download_update_done(self, path, error):
        if error:
            if self.update_info and self.update_info.release_url:
                self.update_status.configure(text=self.t("Yuklab olinmadi. Release sahifasi ochiladi."), text_color="#e05a5a")
                webbrowser.open(self.update_info.release_url)
            else:
                self.update_status.configure(text=self.t("Yuklab olinmadi. Internetni tekshiring."), text_color="#e05a5a")
            if hasattr(self, "download_update_btn"):
                self.download_update_btn.configure(state="normal")
            return
        self.update_status.configure(text=self.t("Setup ishga tushirilmoqda..."), text_color="#4caf50")
        try:
            if platform.system() == "Windows":
                os.startfile(str(path))
            else:
                subprocess.Popen([str(path)])
        except Exception as exc:
            messagebox.showerror(self.t("Yangilanish"), str(exc))

    def pick_ffmpeg(self):
        p = filedialog.askopenfilename(title="ffmpeg.exe", filetypes=[("ffmpeg", "ffmpeg.exe ffmpeg"), ("*", "*.*")])
        if p and SE.set_ffmpeg(p):
            self._check_ffmpeg()

    def _try_enable_drag_drop(self):
        if not hasattr(self, "strip") or DND_FILES is None:
            if hasattr(self, "dnd_status"):
                self.dnd_status.configure(text=self.t("Rasm qo'shish tugmasi orqali tanlang."))
            return
        try:
            for widget in (self.root, self.strip):
                if hasattr(widget, "drop_target_register"):
                    widget.drop_target_register(DND_FILES)
                    widget.dnd_bind("<<Drop>>", self._handle_drop)
            if hasattr(self, "dnd_status"):
                self.dnd_status.configure(text=self.t("Rasmlarni shu oynaga sudrab tashlashingiz mumkin."))
        except Exception:
            if hasattr(self, "dnd_status"):
                self.dnd_status.configure(text=self.t("Drag/drop mavjud emas, tugma orqali tanlang."))

    def _handle_drop(self, event):
        try:
            paths = list(self.root.tk.splitlist(event.data))
        except Exception:
            paths = str(event.data).split()
        self.add_photo_paths(paths)

    def add_photos(self):
        files = filedialog.askopenfilenames(title=self.t("Rasmlar"), filetypes=[("Rasm", "*.jpg *.jpeg *.png *.webp *.bmp"), ("*", "*.*")])
        self.add_photo_paths(files)

    def add_photo_paths(self, paths):
        added = 0
        for p in paths:
            p = str(p).strip("{}")
            if not p.lower().endswith(IMG_EXT):
                continue
            try:
                im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                tp = im.copy()
                tp.thumbnail((110, 70), Image.LANCZOS)
                pp = im.copy()
                pp.thumbnail((430, 270), Image.LANCZOS)
            except Exception:
                continue
            self.items.append({
                "path": p,
                "caption": "",
                "tpil": tp,
                "ppil": pp,
                "orig_ppil": pp.copy(),
                "enhanced_path": "",
                "duration_override": None,
                "motion_preset": "auto",
            })
            added += 1
        self._rebuild()
        if added and self.cur is None:
            self.select(len(self.items) - 1)
        elif added:
            self.status.configure(text=self.t("Rasmlar qo'shildi."))

    def remove_photo(self):
        if self.cur is None:
            return
        self._save_current_item_controls()
        del self.items[self.cur]
        self.cur = min(self.cur, len(self.items) - 1) if self.items else None
        self._rebuild()
        if self.cur is not None:
            self.select(self.cur)
        else:
            self.cap_var.set("")
            self.preview_lbl.configure(image=self._blank, text=self.t("Rasm tanlanmagan"))
            self._ai_original_pil = None
            self._ai_enhanced_pil = None
            self._draw_ai_compare()

    def move(self, d):
        if self.cur is None:
            return
        self._save_current_item_controls()
        j = self.cur + d
        if 0 <= j < len(self.items):
            self.items[self.cur], self.items[j] = self.items[j], self.items[self.cur]
            self.cur = j
            self._rebuild()
            self.select(j)

    def _rebuild(self):
        if not hasattr(self, "strip"):
            return
        for w in self.strip.winfo_children():
            w.destroy()
        self.row_frames = []
        self.row_txt = []
        self._imgs = []
        for i, it in enumerate(self.items):
            rf = ctk.CTkFrame(self.strip, fg_color=ROW_BG, corner_radius=8)
            rf.pack(fill="x", pady=4, padx=2)
            img = ctk.CTkImage(light_image=it["tpil"], dark_image=it["tpil"], size=it["tpil"].size)
            self._imgs.append(img)
            th = ctk.CTkLabel(rf, text="", image=img)
            th.pack(side="left", padx=8, pady=6)
            lbl = ctk.CTkLabel(rf, text=self._rowtext(i), anchor="w", justify="left", font=self.F)
            lbl.pack(side="left", padx=8, fill="x", expand=True)
            for w in (rf, th, lbl):
                w.bind("<Button-1>", lambda _e, idx=i: self.select(idx))
            self.row_frames.append(rf)
            self.row_txt.append(lbl)
        self._highlight()

    def _rowtext(self, i):
        it = self.items[i]
        mark = "  [AI]" if it.get("enhanced_path") else ""
        dur = f"  [{float(it['duration_override']):.1f}s]" if it.get("duration_override") is not None else ""
        motion = it.get("motion_preset") or "auto"
        mot = f"  [{self.t(SE.MOTION_UZ[motion])}]" if motion in SE.MOTION_PRESETS and motion != "auto" else ""
        cap = f"\n     «{it['caption']}»" if it["caption"] else ""
        return f"{i + 1}.  {os.path.basename(it['path'])}{mark}{dur}{mot}{cap}"

    def _highlight(self):
        for i, rf in enumerate(self.row_frames):
            rf.configure(fg_color=ROW_SEL if i == self.cur else ROW_BG)

    def select(self, i):
        if i is None or not (0 <= i < len(self.items)):
            return
        self._save_current_item_controls()
        self.cur = i
        self._highlight()
        self.cap_var.set(self.items[i]["caption"])
        self._set_slide_controls_from_item(i)
        self._schedule_preview_update(10)
        self._schedule_ai_compare_update(10)

    def _save_caption(self):
        if self.cur is not None and 0 <= self.cur < len(self.items):
            self.items[self.cur]["caption"] = self.cap_var.get()
            if self.cur < len(self.row_txt):
                self.row_txt[self.cur].configure(text=self._rowtext(self.cur))

    def _rgrade(self):
        g = self.sel["grade"]
        return SE.STYLES[self.sel["style"]]["grade"] if g == "auto" else g

    def _preview_source(self, item):
        if item.get("enhanced_path") and os.path.isfile(item["enhanced_path"]):
            try:
                im = ImageOps.exif_transpose(Image.open(item["enhanced_path"])).convert("RGB")
                im.thumbnail((430, 270), Image.LANCZOS)
                return im
            except Exception:
                pass
        return item["ppil"]

    def _preview_motion_key(self):
        if self.cur is not None and 0 <= self.cur < len(self.items):
            item_motion = self.items[self.cur].get("motion_preset")
            if item_motion in SE.MOTION_PRESETS and item_motion != "auto":
                return item_motion
        return self.sel.get("motion", "auto")

    def _preview_effects(self, im, t):
        out = im.convert("RGB")
        W, H = out.size
        vig = self.sel["vig"]
        use_vig = vig == "on" or (vig == "auto" and SE.STYLES[self.sel["style"]]["vignette"])
        if self.bloom_var.get():
            blur = out.filter(ImageFilter.GaussianBlur(max(3, int(H * 0.018))))
            out = Image.blend(out, blur, 0.18)
        if use_vig:
            mask = Image.new("L", (W, H), 0)
            d = ImageDraw.Draw(mask)
            margin = int(min(W, H) * 0.10)
            d.ellipse([-margin, -margin, W + margin, H + margin], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(int(min(W, H) * 0.18)))
            dark = Image.new("RGB", (W, H), (0, 0, 0))
            out = Image.composite(out, dark, mask.point(lambda v: int(v * 0.68)))
        if self.grain_var.get():
            noise = Image.effect_noise((W, H), 10).convert("L")
            grain = Image.merge("RGB", (noise, noise, noise))
            out = Image.blend(out, grain, 0.08)
        return out

    def _caption_preview(self, im):
        if not (self.text_enabled_var.get() and self.show_captions_var.get() and self.cur is not None):
            return im
        text = self.items[self.cur].get("caption", "").strip()
        if not text:
            return im
        out = im.convert("RGBA")
        d = ImageDraw.Draw(out)
        st = SE.apply_font_preset(SE.STYLES[self.sel["style"]], self._font_preset_key())
        font = SE.font(st["fonts"].get("cap", "demi"), max(18, int(out.height * 0.055)))
        y = int(out.height * 0.82)
        try:
            bbox = d.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = len(text) * 12
        x = max(16, (out.width - tw) // 2)
        d.rounded_rectangle([x - 12, y - 8, x + tw + 12, y + 38], radius=10, fill=(0, 0, 0, 110))
        d.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        return out.convert("RGB")

    def _build_preview_frames(self):
        if self.cur is None:
            return []
        item = self.items[self.cur]
        src = SE.grade(self._preview_source(item), self._rgrade())
        W, H = 640, 360
        bg_path = self.bg_path.get()
        has_bg = bool(bg_path and os.path.isfile(bg_path))
        frame = self._photo_frame()
        motion = self._preview_motion_key()
        amt = SE.KB_LEVELS.get(self.sel["kb"], 0.15)
        spec = SE._motion_spec(motion, self.cur or 0, amt, W, H)
        steps = 12 if motion != "still" else 1
        frames = []
        bg = None
        if has_bg:
            bg = SE._cover(Image.open(bg_path), W, H).convert("RGBA")
            box = SE._photo_box(W, H, self.sel["layout"], self.photo_scale.get())
            panel = SE._photo_panel(src, box, frame)
        else:
            panel = SE._photo_panel(src, (0, 0, int(W * 0.78), int(H * 0.78)), {"border": False, "shadow": False, "radius": 0})
        for n in range(steps):
            t = 0 if steps == 1 else n / (steps - 1)
            scale = float(spec["start_scale"]) + (float(spec["end_scale"]) - float(spec["start_scale"])) * t
            dx = float(spec["start_dx"]) + (float(spec["end_dx"]) - float(spec["start_dx"])) * t
            dy = float(spec["start_dy"]) + (float(spec["end_dy"]) - float(spec["start_dy"])) * t
            canvas = bg.copy() if bg is not None else Image.new("RGBA", (W, H), (18, 18, 22, 255))
            pw, ph = max(1, int(panel.width * scale)), max(1, int(panel.height * scale))
            moving = panel.resize((pw, ph), Image.LANCZOS)
            x = int(W / 2 - pw / 2 + dx)
            y = int(H / 2 - ph / 2 + dy)
            canvas.alpha_composite(moving, (x, y))
            out = self._caption_preview(canvas.convert("RGB"))
            frames.append(self._preview_effects(out, t))
        return frames

    def _update_preview(self):
        if self.cur is None:
            return
        try:
            self.preview_frames = self._build_preview_frames()
            self.preview_frame_idx = 0
            self._animate_preview()
        except Exception:
            pass

    def _animate_preview(self):
        if self.preview_anim_after is not None:
            try:
                self.root.after_cancel(self.preview_anim_after)
            except Exception:
                pass
            self.preview_anim_after = None
        if not self.preview_frames:
            return
        frame = self.preview_frames[self.preview_frame_idx % len(self.preview_frames)]
        im = ctk.CTkImage(light_image=frame, dark_image=frame, size=frame.size)
        self._prev_img = im
        self.preview_lbl.configure(image=im, text="")
        self.preview_frame_idx = (self.preview_frame_idx + 1) % len(self.preview_frames)
        if len(self.preview_frames) > 1:
            self.preview_anim_after = self.root.after(95, self._animate_preview)

    def update_preview_exact(self):
        if self.cur is None:
            return
        item = self.items[self.cur]
        source_path = item.get("enhanced_path") if item.get("enhanced_path") and os.path.isfile(item.get("enhanced_path", "")) else item["path"]
        bg_path = self.bg_path.get()
        layout = self.sel["layout"]
        scale = float(self.photo_scale.get())
        frame = self._photo_frame()
        grade_name = self._rgrade()
        resolution = self.res_var.get()
        self.preview_job += 1
        job_id = self.preview_job
        self.status.configure(text=self.t("Aniq preview tayyorlanmoqda..."))

        def worker():
            try:
                W, H = SE.RES.get(resolution, (1280, 720))
                ratio = min(1.0, 1280 / max(W, H))
                W, H = max(1, int(W * ratio)), max(1, int(H * ratio))
                with Image.open(source_path) as src:
                    photo = ImageOps.exif_transpose(src).convert("RGB")
                photo = SE.grade(photo, grade_name)
                if bg_path and os.path.isfile(bg_path):
                    image = SE.compose_background_scene(photo, bg_path, W, H, layout, scale, frame)
                else:
                    image = ImageOps.contain(photo, (W, H), Image.LANCZOS)
                    canvas = Image.new("RGB", (W, H), (18, 18, 22))
                    canvas.paste(image, ((W - image.width) // 2, (H - image.height) // 2))
                    image = canvas
                image = self._caption_preview(self._preview_effects(image, 1.0))
                image.thumbnail((760, 430), Image.LANCZOS)
                self.root.after(0, self._finish_exact_preview, job_id, image, "")
            except Exception as exc:
                self.root.after(0, self._finish_exact_preview, job_id, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_exact_preview(self, job_id, image, error):
        if job_id != self.preview_job:
            return
        if error:
            self.status.configure(text=self.t("Preview tayyorlanmadi."))
            return
        im = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        self._prev_img = im
        self.preview_lbl.configure(image=im, text="")
        self.status.configure(text=self.t("Aniq preview tayyor."))

    def _update_ai_preview_only(self):
        if self.cur is not None:
            self._schedule_ai_compare_update()

    def _schedule_ai_compare_update(self, delay: int = 180) -> None:
        if self.ai_preview_after is not None:
            try:
                self.root.after_cancel(self.ai_preview_after)
            except Exception:
                pass
        self.ai_preview_after = self.root.after(delay, self._start_ai_preview_job)

    def _drag_ai_compare(self, event):
        if not hasattr(self, "ai_canvas"):
            return
        width = max(1, self.ai_canvas.winfo_width())
        pct = max(0, min(100, (event.x / width) * 100))
        self.ai_compare.set(pct)
        self._draw_ai_compare()

    def _update_ai_compare(self):
        self._schedule_ai_compare_update(10)

    def _start_ai_preview_job(self):
        self.ai_preview_after = None
        if self.cur is None:
            return
        item = self.items[self.cur]
        path = item["path"]
        enhanced_path = item.get("enhanced_path") if item.get("enhanced_path") and os.path.isfile(item.get("enhanced_path", "")) else ""
        self.ai_preview_job += 1
        job_id = self.ai_preview_job

        def worker():
            try:
                with Image.open(path) as src:
                    original = ImageOps.exif_transpose(src).convert("RGB")
                original.thumbnail((1200, 1200), Image.LANCZOS)
                if enhanced_path:
                    with Image.open(enhanced_path) as enh:
                        enhanced = ImageOps.exif_transpose(enh).convert("RGB")
                    enhanced.thumbnail((1200, 1200), Image.LANCZOS)
                else:
                    enhanced = original.copy()
                self.root.after(0, self._finish_ai_preview_job, job_id, path, original, enhanced, "")
            except Exception as exc:
                self.root.after(0, self._finish_ai_preview_job, job_id, path, None, None, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_ai_preview_job(self, job_id, path, original, enhanced, error):
        if job_id != self.ai_preview_job:
            return
        if self.cur is None or not (0 <= self.cur < len(self.items)):
            return
        if self.items[self.cur]["path"] != path:
            return
        if error:
            return
        try:
            self._ai_original_pil = original
            self._ai_enhanced_pil = enhanced
            self._draw_ai_compare()
            self.ai_title.configure(text=os.path.basename(path))
        except Exception:
            pass

    def _draw_ai_compare(self):
        if not hasattr(self, "ai_canvas"):
            return
        canvas = self.ai_canvas
        canvas.delete("all")
        if self._ai_original_pil is None or self._ai_enhanced_pil is None:
            w = max(1, canvas.winfo_width())
            h = max(1, canvas.winfo_height())
            canvas.create_text(w // 2, h // 2, text=self.t("Oldin / Keyin ko'rinish"), fill="#d0d0d0", font=("Segoe UI", 16))
            return
        w = max(1, canvas.winfo_width())
        h = max(1, canvas.winfo_height())
        original = self._ai_original_pil.copy()
        original.thumbnail((w, h), Image.LANCZOS)
        enhanced = self._ai_enhanced_pil.copy().resize(original.size, Image.LANCZOS)
        split = int(original.width * (self.ai_compare.get() / 100.0))
        view = original.copy()
        view.paste(enhanced.crop((split, 0, original.width, original.height)), (split, 0))
        self._ai_tk = ImageTk.PhotoImage(view)
        x = (w - view.width) // 2
        y = (h - view.height) // 2
        canvas.create_image(x, y, image=self._ai_tk, anchor="nw")
        line_x = x + split
        canvas.create_line(line_x, y, line_x, y + view.height, fill="#ffffff", width=3)
        canvas.create_oval(line_x - 14, y + view.height // 2 - 14, line_x + 14, y + view.height // 2 + 14, fill="#ffffff", outline="#333333", width=2)
        canvas.create_text(x + 52, y + 28, text=self.t("Oldin"), fill="#ffffff", font=("Segoe UI", 13, "bold"))
        canvas.create_text(x + view.width - 54, y + 28, text=self.t("Keyin"), fill="#ffffff", font=("Segoe UI", 13, "bold"))

    def gallery_grade(self):
        src = self.items[self.cur]["ppil"] if self.cur is not None else (self.items[0]["ppil"] if self.items else None)
        if src is None:
            messagebox.showinfo(self.t("Rasm yo'q"), self.t("Avval rasm qo'shing."))
            return
        top = ctk.CTkToplevel(self.root)
        top.title(self.t("Ranglar - bosib tanlang"))
        top.geometry("880x620")
        top.attributes("-topmost", True)
        fr = ctk.CTkScrollableFrame(top)
        fr.pack(fill="both", expand=True, padx=8, pady=8)
        refs = []
        keys = [k for k in SE.GRADES if k != "auto"]
        for idx, k in enumerate(keys):
            g = SE.grade(src, k)
            th = g.copy()
            th.thumbnail((230, 150), Image.LANCZOS)
            ci = ctk.CTkImage(light_image=th, dark_image=th, size=th.size)
            refs.append(ci)
            cell = ctk.CTkFrame(fr)
            cell.grid(row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="n")
            ctk.CTkLabel(cell, text="", image=ci).pack(padx=6, pady=(6, 2))
            ctk.CTkButton(cell, text=self.t(SE.GRADE_UZ[k]), width=210, font=self.F, command=lambda kk=k, tt=top: self._pick_grade(kk, tt)).pack(padx=6, pady=(0, 6))
        top._refs = refs

    def _pick_grade(self, k, top):
        self.sel["grade"] = k
        if "grade" in self.mvar:
            self.mvar["grade"].set(self.t(SE.GRADE_UZ[k]))
        self._schedule_preview_update()
        top.destroy()

    def gallery_trans(self):
        top = ctk.CTkToplevel(self.root)
        top.title(self.t("O'tishlar - bosib tanlang"))
        top.geometry("880x620")
        top.attributes("-topmost", True)
        fr = ctk.CTkScrollableFrame(top)
        fr.pack(fill="both", expand=True, padx=8, pady=8)
        top._anim = []
        for idx, k in enumerate([x for x in SE.TRANSITIONS if x != "auto"]):
            cell = ctk.CTkFrame(fr)
            cell.grid(row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="n")
            lbl = ctk.CTkLabel(cell, text="")
            lbl.pack(padx=6, pady=(6, 2))
            ctk.CTkButton(cell, text=self.t(SE.TRANS_UZ[k]), width=230, font=self.F, command=lambda kk=k, tt=top: self._pick_trans(kk, tt)).pack(padx=6, pady=(0, 6))
            frames = self._load_gif(os.path.join(GIFDIR, k + ".gif"))
            if frames:
                top._anim.append([lbl, frames, 0])
        self._animate(top)

    def _load_gif(self, path):
        if not os.path.isfile(path):
            return None
        frames = []
        try:
            g = Image.open(path)
            while True:
                fr = g.convert("RGB").copy()
                fr.thumbnail((240, 140), Image.LANCZOS)
                frames.append(ctk.CTkImage(light_image=fr, dark_image=fr, size=fr.size))
                g.seek(g.tell() + 1)
        except EOFError:
            pass
        except Exception:
            return None
        return frames

    def _animate(self, top):
        if not top.winfo_exists():
            return
        for item in getattr(top, "_anim", []):
            lbl, frames, idx = item
            try:
                lbl.configure(image=frames[idx])
            except Exception:
                pass
            item[2] = (idx + 1) % len(frames)
        top.after(70, lambda: self._animate(top))

    def _pick_trans(self, k, top):
        self.sel["trans"] = k
        if "trans" in self.mvar:
            self.mvar["trans"].set(self.t(SE.TRANS_UZ[k]))
        top.destroy()

    def _music_seg(self, val):
        self.music_mode.set("auto" if val in ("Avto", lat2cyr("Avto")) else "file")

    def pick_music(self):
        p = filedialog.askopenfilename(title=self.t("Musiqa"), filetypes=[("Audio", "*.mp3 *.wav *.m4a *.aac"), ("*", "*.*")])
        if p:
            self.music_path.set(p)
            self.music_mode.set("file")

    def pick_output(self):
        p = filedialog.asksaveasfilename(title=self.t("Saqlash"), defaultextension=".mp4", initialfile="video.mp4", filetypes=[("MP4", "*.mp4")])
        if p:
            self.out_var.set(p)

    def open_output(self):
        d = os.path.dirname(self.out_var.get())
        try:
            if platform.system() == "Windows":
                os.startfile(d)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", d])
            else:
                subprocess.Popen(["xdg-open", d])
        except Exception:
            pass

    def _restore_main_buttons(self):
        self.busy = False
        self.gen_btn.configure(state="normal")
        self.prev_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.open_btn.configure(state="normal" if os.path.exists(os.path.dirname(self.out_var.get())) else "disabled")

    def cancel_current_job(self):
        self.cancel_event.set()
        self.vc_cancel_event.set()
        self.status.configure(text=self.t("Bekor qilinmoqda..."))
        if hasattr(self, "vc_status"):
            self.vc_status.configure(text=self.t("Bekor qilinmoqda..."))

    def import_background(self):
        p = filedialog.askopenfilename(title=self.t("Background tanlash"), filetypes=[("Rasm", "*.jpg *.jpeg *.png *.webp *.bmp"), ("*", "*.*")])
        if not p:
            return
        try:
            dest = Store.import_background(p)
            self.bg_path.set(str(dest))
            self.settings["last_background"] = str(dest)
            Store.save_settings(self.settings)
            self._refresh_backgrounds()
            self._schedule_preview_update()
        except Exception as exc:
            messagebox.showerror("Background", str(exc))

    def clear_background(self):
        self.bg_path.set("")
        self.settings["last_background"] = ""
        Store.save_settings(self.settings)
        self._refresh_backgrounds()
        self._schedule_preview_update()

    def _refresh_backgrounds(self):
        if not hasattr(self, "bg_list"):
            return
        for w in self.bg_list.winfo_children():
            w.destroy()
        cur = self.bg_path.get()
        self.bg_current.configure(text=self.t("Tanlangan fon: ") + (os.path.basename(cur) if cur else self.t("yo'q")))
        refs = []
        for row_meta in Store.list_backgrounds(with_meta=True):
            p = row_meta["path"]
            row = ctk.CTkFrame(self.bg_list)
            row.pack(fill="x", padx=6, pady=5)
            try:
                im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                im.thumbnail((135, 72), Image.LANCZOS)
                cimg = ctk.CTkImage(light_image=im, dark_image=im, size=im.size)
                refs.append(cimg)
                ctk.CTkLabel(row, image=cimg, text="").pack(side="left", padx=6, pady=6)
            except Exception:
                pass
            title = ("★ " if row_meta.get("favorite") else "") + str(row_meta.get("name", p.name))
            ctk.CTkLabel(row, text=title, anchor="w", font=self.F).pack(side="left", fill="x", expand=True, padx=6)
            ctk.CTkButton(row, text="★" if row_meta.get("favorite") else "☆", width=38, command=lambda pp=p, fav=bool(row_meta.get("favorite")): self.toggle_background_favorite(pp, fav)).pack(side="right", padx=(0, 4))
            ctk.CTkButton(row, text=self.t("O'chirish"), width=82, fg_color="#8a3c3c", command=lambda pp=p: self.delete_background_confirm(pp)).pack(side="right", padx=(0, 4))
            ctk.CTkButton(row, text=self.t("Nomlash"), width=82, fg_color="#5a5a5a", command=lambda pp=p: self.rename_background_prompt(pp)).pack(side="right", padx=(0, 4))
            ctk.CTkButton(row, text=self.t("Tanlash"), width=90, command=lambda pp=p: self.select_background(pp)).pack(side="right", padx=6)
        self.bg_list._refs = refs

    def select_background(self, path):
        self.bg_path.set(str(path))
        self.settings["last_background"] = str(path)
        Store.save_settings(self.settings)
        self._refresh_backgrounds()
        self._schedule_preview_update()

    def rename_background_prompt(self, path):
        name = simpledialog.askstring(self.t("Background"), self.t("Yangi nom:"), initialvalue=Path(path).stem.replace("_", " "), parent=self.root)
        if not name:
            return
        try:
            new_path = Store.rename_background(path, name)
            if self.bg_path.get() == str(path):
                self.bg_path.set(str(new_path))
            self._refresh_backgrounds()
        except Exception as exc:
            messagebox.showerror("Background", str(exc))

    def delete_background_confirm(self, path):
        if not messagebox.askyesno(self.t("Background"), self.t("Bu backgroundni o'chiramizmi?")):
            return
        try:
            Store.delete_background(path)
            if self.bg_path.get() == str(path):
                self.bg_path.set("")
                self.settings["last_background"] = ""
                Store.save_settings(self.settings)
            self._refresh_backgrounds()
            self._schedule_preview_update()
        except Exception as exc:
            messagebox.showerror("Background", str(exc))

    def toggle_background_favorite(self, path, was_favorite):
        try:
            Store.favorite_background(path, not was_favorite)
            self._refresh_backgrounds()
        except Exception as exc:
            messagebox.showerror("Background", str(exc))

    def reinstall_starter_pack(self):
        try:
            starter_pack.install_if_needed(force=True)
            self._refresh_backgrounds()
            self._refresh_templates()
            messagebox.showinfo(self.t("Starter pack"), self.t("Starter pack qayta o'rnatildi."))
        except Exception as exc:
            messagebox.showerror("Starter pack", str(exc))

    def _template_payload(self):
        self._save_current_item_controls()
        return {
            "style": self.sel["style"],
            "grade": self.sel["grade"],
            "transition_type": self.sel["trans"],
            "kb_intensity": self.sel["kb"],
            "motion_preset": self.sel["motion"],
            "vignette": self.sel["vig"],
            "text_enabled": bool(self.text_enabled_var.get()),
            "show_title_card": bool(self.show_title_var.get()),
            "show_captions": bool(self.show_captions_var.get()),
            "show_outro_card": bool(self.show_outro_var.get()),
            "text_template": self._text_template_key(),
            "font_preset": self._font_preset_key(),
            "resolution": self.res_var.get(),
            "fps": int(self.fps_var.get()),
            "preset": self.preset_var.get(),
            "photo_duration": float(self.dur_var.get()),
            "title": self.title_var.get(),
            "kicker": self.kicker_var.get(),
            "date": self.date_var.get(),
            "outro_kicker": self.okick_var.get(),
            "subtitle": self.osub_var.get(),
            "background_path": self.bg_path.get(),
            "photo_layout": self.sel["layout"],
            "photo_scale": float(self.photo_scale.get()),
            "photo_frame": self._photo_frame(),
            "ai_settings": self._enhance_settings().normalized(),
        }

    def _save_template_preview(self, name: str) -> str | None:
        try:
            folder = Store.templates_dir() / "previews"
            folder.mkdir(parents=True, exist_ok=True)
            path = Store.unique_path(folder, Store.slugify(name), ".jpg")
            if self.cur is not None:
                src = self._preview_source(self.items[self.cur])
                img = SE.grade(src, self._rgrade())
                if self.bg_path.get() and os.path.isfile(self.bg_path.get()):
                    img = SE.compose_background_scene(img, self.bg_path.get(), 640, 360, self.sel["layout"], self.photo_scale.get(), self._photo_frame())
            elif self.bg_path.get() and os.path.isfile(self.bg_path.get()):
                img = ImageOps.exif_transpose(Image.open(self.bg_path.get())).convert("RGB")
                img.thumbnail((640, 360), Image.LANCZOS)
            else:
                return None
            img.save(path, quality=88)
            return str(path)
        except Exception:
            return None

    def save_template_prompt(self):
        self._save_current_item_controls()
        name = simpledialog.askstring(self.t("Shablon"), self.t("Shablon nomi:"), parent=self.root)
        if not name:
            return
        try:
            path = Store.save_template(name, self._template_payload(), preview_path=self._save_template_preview(name))
            self.settings["last_template"] = str(path)
            Store.save_settings(self.settings)
            self._refresh_templates()
            messagebox.showinfo(self.t("Shablon"), self.t("Shablon saqlandi."))
        except Exception as exc:
            messagebox.showerror("Shablon", str(exc))

    def _refresh_templates(self):
        if not hasattr(self, "template_list"):
            return
        for w in self.template_list.winfo_children():
            w.destroy()
        refs = []
        for col in range(2):
            self.template_list.grid_columnconfigure(col, weight=1)
        for idx, row_meta in enumerate(Store.list_templates(with_meta=True)):
            p = row_meta["path"]
            name = row_meta.get("name") or p.stem
            row = ctk.CTkFrame(self.template_list, corner_radius=8)
            row.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)
            preview = str(row_meta.get("preview_path") or "")
            if preview and os.path.isfile(preview):
                try:
                    im = ImageOps.exif_transpose(Image.open(preview)).convert("RGB")
                    im.thumbnail((165, 92), Image.LANCZOS)
                    cimg = ctk.CTkImage(light_image=im, dark_image=im, size=(165, 92))
                    refs.append(cimg)
                    ctk.CTkLabel(row, image=cimg, text="").pack(fill="x", padx=8, pady=(8, 4))
                except Exception:
                    pass
            ctk.CTkLabel(row, text=str(name), anchor="w", font=self.FB, wraplength=170).pack(fill="x", padx=8, pady=(2, 6))
            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(fill="x", padx=8, pady=(0, 8))
            ctk.CTkButton(actions, text=self.t("Ochish"), height=32, command=lambda pp=p: self.load_template(pp)).pack(fill="x", pady=(0, 4))
            ctk.CTkButton(actions, text=self.t("Nomlash"), height=30, fg_color="#5a5a5a", command=lambda pp=p: self.rename_template_prompt(pp)).pack(side="left", fill="x", expand=True, padx=(0, 4))
            ctk.CTkButton(actions, text=self.t("O'chirish"), height=30, fg_color="#8a3c3c", command=lambda pp=p: self.delete_template_confirm(pp)).pack(side="left", fill="x", expand=True)
        self.template_list._refs = refs

    def rename_template_prompt(self, path):
        try:
            current = Store.load_template(path).get("name") or Path(path).stem
        except Exception:
            current = Path(path).stem
        name = simpledialog.askstring(self.t("Shablon"), self.t("Yangi nom:"), initialvalue=current, parent=self.root)
        if not name:
            return
        try:
            Store.rename_template(path, name)
            self._refresh_templates()
        except Exception as exc:
            messagebox.showerror("Shablon", str(exc))

    def delete_template_confirm(self, path):
        if not messagebox.askyesno(self.t("Shablon"), self.t("Bu shablonni o'chiramizmi?")):
            return
        try:
            Store.delete_template(path)
            self._refresh_templates()
        except Exception as exc:
            messagebox.showerror("Shablon", str(exc))

    def load_template(self, path):
        try:
            data = Store.load_template(path).get("data", {})
            self.sel["style"] = data.get("style", self.sel["style"])
            self.sel["grade"] = data.get("grade", self.sel["grade"])
            self.sel["trans"] = data.get("transition_type", self.sel["trans"])
            self.sel["kb"] = data.get("kb_intensity", self.sel["kb"])
            self.sel["motion"] = data.get("motion_preset", self.sel["motion"])
            if self.sel["motion"] not in SE.MOTION_PRESETS:
                self.sel["motion"] = "auto"
            self.sel["vig"] = data.get("vignette", self.sel["vig"])
            inferred_text = any(str(data.get(k, "")).strip() for k in ("title", "kicker", "outro_kicker", "subtitle"))
            text_enabled = bool(data.get("text_enabled", inferred_text))
            self.text_enabled_var.set(text_enabled)
            self.show_title_var.set(bool(data.get("show_title_card", text_enabled)))
            self.show_captions_var.set(bool(data.get("show_captions", text_enabled)))
            self.show_outro_var.set(bool(data.get("show_outro_card", text_enabled)))
            text_template = data.get("text_template", "family")
            if text_template not in TEXT_TEMPLATES:
                text_template = "family"
            self.text_template_var.set(self.t(TEXT_TEMPLATE_UZ[text_template]))
            font_preset = data.get("font_preset", "default")
            if font_preset not in SE.FONT_PRESETS:
                font_preset = "default"
            self.font_preset_var.set(self.t(SE.FONT_UZ[font_preset]))
            self.sel["layout"] = data.get("photo_layout", self.sel["layout"])
            self.res_var.set(data.get("resolution", self.res_var.get()))
            self.fps_var.set(str(data.get("fps", self.fps_var.get())))
            self.preset_var.set(data.get("preset", self.preset_var.get()))
            self.dur_var.set(float(data.get("photo_duration", self.dur_var.get())))
            self.title_var.set(data.get("title", self.title_var.get()))
            self.kicker_var.set(data.get("kicker", self.kicker_var.get()))
            self.date_var.set(data.get("date", self.date_var.get()))
            self.okick_var.set(data.get("outro_kicker", self.okick_var.get()))
            self.osub_var.set(data.get("subtitle", self.osub_var.get()))
            self.bg_path.set(data.get("background_path", ""))
            self.photo_scale.set(float(data.get("photo_scale", self.photo_scale.get())))
            frame = data.get("photo_frame") or {}
            self.frame_var.set(bool(frame.get("border", self.frame_var.get())))
            self.shadow_var.set(bool(frame.get("shadow", self.shadow_var.get())))
            self.radius_var.set(float(frame.get("radius", self.radius_var.get())))
            for key, var in self.mvar.items():
                if key == "grade":
                    var.set(self.t(SE.GRADE_UZ[self.sel["grade"]]))
                elif key == "trans":
                    var.set(self.t(SE.TRANS_UZ[self.sel["trans"]]))
                elif key == "kb":
                    var.set(self.t(KB_LAT[self.sel["kb"]]))
                elif key == "motion":
                    var.set(self._motion_label(self.sel["motion"]))
                elif key == "vig":
                    var.set(self.t(VIG_LAT[self.sel["vig"]]))
                elif key == "style":
                    var.set(self.t(self.sel["style"]))
                elif key == "layout":
                    var.set(self.t(LAYOUT_LAT[self.sel["layout"]]))
            self._refresh_backgrounds()
            if self.cur is not None:
                self._set_slide_controls_from_item(self.cur)
            self._schedule_preview_update()
            messagebox.showinfo(self.t("Shablon"), self.t("Shablon yuklandi."))
        except Exception as exc:
            messagebox.showerror("Shablon", str(exc))

    def _enhance_settings(self) -> AI.EnhanceSettings:
        return AI.EnhanceSettings(
            brightness=float(self.ai_brightness.get()),
            contrast=float(self.ai_contrast.get()),
            saturation=float(self.ai_saturation.get()),
            warmth=float(self.ai_warmth.get()),
            sharpness=float(self.ai_sharpness.get()),
            denoise=float(self.ai_denoise.get()),
            upscale=self.ai_upscale.get(),
            face_restore=bool(self.ai_face.get()),
        )

    def _ai_preset_key(self) -> str:
        label = self.ai_preset_var.get()
        for key, text in AI.AI_PRESETS.items():
            if label == self.t(text):
                return key
        return "auto"

    def _ai_targets(self, all_photos: bool):
        if all_photos:
            return list(range(len(self.items)))
        return [] if self.cur is None else [self.cur]

    def apply_ai(self, all_photos: bool):
        self.apply_openai_all() if all_photos else self.apply_openai_selected()

    def _ensure_openai_ready(self) -> str | None:
        if not self.online:
            status = connectivity.check_online(timeout=2.0)
            self._set_connectivity(status)
            if not status.online:
                messagebox.showwarning("OpenAI", self.t("AI uchun internet kerak. Offline holatda rasm va video funksiyalari ishlayveradi."))
                return None
        if not self.consent_var.get():
            ok = messagebox.askyesno(self.t("AI rozilik"), self.t("OpenAI ishlaganda rasm internet orqali AI xizmatiga yuboriladi. Davom etamizmi?"))
            if not ok:
                return None
            self.consent_var.set(True)
            self.save_settings()
        key = Store.get_api_key("openai")
        if not key:
            messagebox.showwarning("OpenAI", self.t("Sozlamalarda OpenAI API key saqlang."))
            return None
        return key

    def apply_openai_all(self):
        targets = self._ai_targets(True)
        if not targets:
            messagebox.showwarning("", self.t("Avval rasm tanlang."))
            return
        key = self._ensure_openai_ready()
        if key:
            self._start_ai_job(targets, "openai", key)

    def apply_openai_selected(self):
        if self.cur is None:
            messagebox.showwarning("", self.t("Avval rasm tanlang."))
            return
        key = self._ensure_openai_ready()
        if key:
            self._start_ai_job([self.cur], "openai", key)

    def _start_ai_job(self, targets, mode, key=""):
        if self.busy:
            return
        self.busy = True
        self.cancel_event.clear()
        settings = self._enhance_settings()
        model = self.model_var.get().strip() or "gpt-image-2.5-sunburst"
        quality = self.openai_quality_var.get()
        preset = self._ai_preset_key()
        self.status.configure(text=self.t("AI ishlayapti..."))
        self.gen_btn.configure(state="disabled")
        self.prev_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        threading.Thread(target=self._ai_worker, args=(targets, mode, key, settings, model, quality, preset), daemon=True).start()
        self.root.after(120, self._poll)

    def _ai_worker(self, targets, mode, key="", settings=None, model="", quality="medium", preset="auto"):
        try:
            settings = settings or AI.EnhanceSettings()
            model = model or "gpt-image-2.5-sunburst"
            for n, idx in enumerate(targets, 1):
                if self.cancel_event.is_set():
                    self.q.put(("cancelled", 0, self.t("Bekor qilindi"), False))
                    return
                item = self.items[idx]
                provider = "openai"
                cache_model = f"{model}:{quality}:{preset}"
                out = AI.cache_path(item["path"], settings, provider, cache_model)
                if not out.exists():
                    AI.openai_enhance(
                        item["path"],
                        out,
                        key,
                        model=model,
                        quality=quality,
                        preset=preset,
                        settings=settings,
                    )
                if self.cancel_event.is_set():
                    self.q.put(("cancelled", 0, self.t("Bekor qilindi"), False))
                    return
                self.q.put(("ai_one", idx, str(out), f"AI: {n}/{len(targets)}"))
            self.q.put(("ai_done", 100, self.t("AI tayyor"), False))
        except Exception as exc:
            self.q.put(("err", 0, str(exc), False))

    def _apply_ai_result(self, idx, path):
        if not (0 <= idx < len(self.items)):
            return
        it = self.items[idx]
        it["enhanced_path"] = path
        try:
            im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            tp = im.copy()
            tp.thumbnail((110, 70), Image.LANCZOS)
            pp = im.copy()
            pp.thumbnail((430, 270), Image.LANCZOS)
            it["tpil"] = tp
            it["ppil"] = pp
        except Exception:
            pass
        self._rebuild()
        if self.cur == idx:
            self.select(idx)

    def reset_selected_ai(self):
        if self.cur is None:
            return
        item = self.items[self.cur]
        item["enhanced_path"] = ""
        try:
            im = ImageOps.exif_transpose(Image.open(item["path"])).convert("RGB")
            tp = im.copy()
            tp.thumbnail((110, 70), Image.LANCZOS)
            pp = im.copy()
            pp.thumbnail((430, 270), Image.LANCZOS)
            item["tpil"] = tp
            item["ppil"] = pp
            item["orig_ppil"] = pp.copy()
        except Exception:
            pass
        self._rebuild()
        self.select(self.cur)

    def save_api_key(self):
        try:
            Store.set_api_key("openai", self.key_var.get())
            self.key_var.set("")
            self.settings_status.configure(text=self.t("OpenAI API key xavfsiz saqlandi."), text_color="#4caf50")
        except Exception as exc:
            self.settings_status.configure(text=str(exc), text_color="#e05a5a")

    def test_api_key(self):
        key = self.key_var.get().strip() or Store.get_api_key("openai")
        if not self.online:
            status = connectivity.check_online(timeout=2.0)
            self._set_connectivity(status)
            if not status.online:
                self.settings_status.configure(text=self.t("API key tekshirish uchun internet kerak."), text_color="#e0a84c")
                return
        self.settings_status.configure(text=self.t("Tekshirilmoqda..."), text_color="#8a8a8a")

        def worker():
            ok = AI.test_openai_key(key)
            self.root.after(0, lambda: self.settings_status.configure(
                text=self.t("API key ishlayapti.") if ok else self.t("API key tekshirilmadi yoki noto'g'ri."),
                text_color="#4caf50" if ok else "#e05a5a",
            ))

        threading.Thread(target=worker, daemon=True).start()

    def delete_api_key(self):
        Store.delete_api_key("openai")
        self.settings_status.configure(text=self.t("OpenAI API key o'chirildi."), text_color="#8a8a8a")

    def save_settings(self):
        self.settings.update(
            provider=self.provider_var.get(),
            openai_model=self.model_var.get(),
            openai_quality=self.openai_quality_var.get(),
            ai_consent=bool(self.consent_var.get()),
            last_background=self.bg_path.get(),
        )
        Store.save_settings(self.settings)
        if hasattr(self, "settings_status"):
            self.settings_status.configure(text=self.t("Sozlamalar saqlandi."), text_color="#4caf50")

    def vc_choose_input(self):
        p = filedialog.askopenfilename(title=self.t("Video/audio fayl tanlash"))
        if p:
            self.vc_input = Path(p)
            self.vc_input_lbl.configure(text=str(self.vc_input))

    def vc_choose_output(self):
        p = filedialog.askdirectory(title=self.t("Chiqish papkasi"))
        if p:
            self.vc_output_dir = Path(p)
            self.vc_out_lbl.configure(text=self.t("Chiqish papkasi: ") + str(self.vc_output_dir))

    def vc_start(self):
        if convert is None or build_conversion_args is None:
            messagebox.showerror("Video Tools", self.t("video_converter moduli topilmadi."))
            return
        if self.vc_input is None:
            messagebox.showwarning("", self.t("Avval fayl tanlang."))
            return
        out_dir = self.vc_output_dir or self.vc_input.parent
        out_format = self.vc_format.get()
        output_path = out_dir / f"{self.vc_input.stem}.{out_format}"
        if output_path == self.vc_input:
            messagebox.showwarning("", self.t("Chiqish fayli kirish fayli bilan bir xil bo'lmasin."))
            return
        res = None if out_format in AUDIO_ONLY_FORMATS else RESOLUTIONS.get(self.vc_res.get())
        fps = None if out_format in AUDIO_ONLY_FORMATS else FRAME_RATES.get(self.vc_fps.get())
        extra = build_conversion_args(out_format, resolution=res, fps=fps, quality=self.vc_quality.get())
        self.vc_cancel_event.clear()
        self.vc_button.configure(state="disabled")
        self.vc_cancel_btn.configure(state="normal")
        self.cancel_btn.configure(state="normal")
        self.vc_status.configure(text=self.t("Konvertatsiya..."))
        self.vc_progress.set(0)
        threading.Thread(target=self._vc_worker, args=(self.vc_input, output_path, extra), daemon=True).start()

    def _vc_worker(self, input_path, output_path, extra):
        try:
            result = convert(input_path, output_path, extra_args=extra, cancel_event=self.vc_cancel_event, on_progress=lambda frac: self.root.after(0, self._vc_progress, frac))
            self.root.after(0, self._vc_done, result, output_path)
        except Exception as exc:
            self.root.after(0, self._vc_error, str(exc))

    def _vc_progress(self, frac):
        self.vc_progress.set(float(frac))
        self.vc_status.configure(text=f"{self.t('Konvertatsiya')}... {frac * 100:.0f}%")

    def _vc_done(self, result, output_path):
        self.vc_button.configure(state="normal")
        self.vc_cancel_btn.configure(state="disabled")
        if not self.busy:
            self.cancel_btn.configure(state="disabled")
        if result.success:
            self.vc_progress.set(1)
            self.vc_status.configure(text=self.t("Tayyor: ") + str(output_path))
        elif result.returncode == -1:
            self.vc_status.configure(text=self.t("Bekor qilindi"))
        else:
            self.vc_status.configure(text=self.t("Xato"))
            messagebox.showerror("Video Tools", result.stderr_tail or self.t("Konvertatsiya xato tugadi."))

    def _vc_error(self, msg):
        self.vc_button.configure(state="normal")
        self.vc_cancel_btn.configure(state="disabled")
        if not self.busy:
            self.cancel_btn.configure(state="disabled")
        self.vc_status.configure(text=self.t("Xato"))
        messagebox.showerror("Video Tools", msg)

    def _photo_frame(self):
        return {"border": bool(self.frame_var.get()), "shadow": bool(self.shadow_var.get()), "radius": int(self.radius_var.get())}

    def _base_cfg(self):
        vigmap = {"auto": "auto", "on": True, "off": False}
        enhanced = {it["path"]: it["enhanced_path"] for it in self.items if it.get("enhanced_path") and os.path.isfile(it["enhanced_path"])}
        photo_durations = [
            (float(it["duration_override"]) if it.get("duration_override") is not None else float(self.dur_var.get()))
            for it in self.items
        ]
        photo_motions = [
            (
                it.get("motion_preset")
                if it.get("motion_preset") in SE.MOTION_PRESETS and it.get("motion_preset") != "auto"
                else self.sel.get("motion", "auto")
            )
            for it in self.items
        ]
        return dict(
            photos=[it["path"] for it in self.items],
            captions={i + 1: it["caption"] for i, it in enumerate(self.items) if it["caption"].strip()},
            enhanced_photos=enhanced,
            photo_durations=photo_durations,
            photo_motions=photo_motions,
            text_enabled=bool(self.text_enabled_var.get()),
            show_title_card=bool(self.show_title_var.get()),
            show_captions=bool(self.show_captions_var.get()),
            show_outro_card=bool(self.show_outro_var.get()),
            text_template=self._text_template_key(),
            font_preset=self._font_preset_key(),
            style=self.sel["style"],
            title=self.title_var.get(),
            kicker=self.kicker_var.get(),
            date=self.date_var.get(),
            outro_title=self.title_var.get(),
            outro_kicker=self.okick_var.get(),
            subtitle=self.osub_var.get(),
            grade=self.sel["grade"],
            transition_type=self.sel["trans"],
            kb_intensity=self.sel["kb"],
            vignette=vigmap[self.sel["vig"]],
            grain=bool(self.grain_var.get()),
            bloom=bool(self.bloom_var.get()),
            fps=int(self.fps_var.get()),
            preset=self.preset_var.get(),
            music="auto" if self.music_mode.get() == "auto" else self.music_path.get(),
            background_path=self.bg_path.get(),
            photo_layout=self.sel["layout"],
            photo_scale=float(self.photo_scale.get()),
            photo_frame=self._photo_frame(),
        )

    def _precheck(self):
        if self.busy:
            return False
        if not self.items:
            messagebox.showwarning("", self.t("Avval rasm qo'shing."))
            return False
        if not SE.find_ffmpeg():
            messagebox.showwarning("ffmpeg", self.t("ffmpeg topilmadi."))
            return False
        if self.music_mode.get() == "file" and not os.path.isfile(self.music_path.get()):
            messagebox.showwarning("", self.t("Musiqa faylini tanlang yoki Avto qiling."))
            return False
        return True

    def generate(self):
        self._save_current_item_controls()
        if not self._precheck():
            return
        if not self.out_var.get():
            messagebox.showwarning("", self.t("Chiqish faylini tanlang."))
            return
        c = self._base_cfg()
        c.update(resolution=self.res_var.get(), photo_duration=float(self.dur_var.get()), transition_dur=0.7, title_duration=6.0, outro_duration=4.5, crf=int(self.sel["qual"]), output=self.out_var.get())
        self._start(c, False)

    def preview_sample(self):
        self._save_current_item_controls()
        if not self._precheck():
            return
        c = self._base_cfg()
        c["photos"] = c["photos"][:4]
        c["photo_durations"] = [min(1.8, float(v)) for v in c.get("photo_durations", [])[:4]]
        c["photo_motions"] = c.get("photo_motions", [])[:4]
        c["captions"] = {k: v for k, v in c["captions"].items() if k <= 4}
        c.update(resolution="720p (tez)", photo_duration=1.8, transition_dur=0.5, title_duration=1.8, outro_duration=1.8, crf=23, preset="veryfast", output=os.path.join(tempfile.gettempdir(), "pvs_namuna.mp4"))
        self._start(c, True)

    def _start(self, cfg, open_after):
        self.busy = True
        self.cancel_event.clear()
        self.gen_btn.configure(state="disabled")
        self.prev_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.pbar.set(0)
        self.status.configure(text=self.t("Boshlanmoqda..."))
        threading.Thread(target=self._worker, args=(cfg, open_after), daemon=True).start()
        self.root.after(120, self._poll)

    def _worker(self, cfg, oa):
        try:
            SE.build_video(cfg, lambda p, m: self.q.put(("p", p, m)), cancel_event=self.cancel_event)
            self.q.put(("done", 100, cfg["output"], oa))
        except SE.CancelledError:
            self.q.put(("cancelled", 0, self.t("Bekor qilindi"), False))
        except Exception as e:
            self.q.put(("err", 0, str(e), False))

    def _poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "p":
                    self.pbar.set(m[1] / 100.0)
                    self.status.configure(text=m[2])
                elif m[0] == "ai_one":
                    self._apply_ai_result(m[1], m[2])
                    self.status.configure(text=m[3])
                elif m[0] == "ai_done":
                    self._restore_main_buttons()
                    self.status.configure(text=self.t("AI tayyor"))
                    return
                elif m[0] == "cancelled":
                    self._restore_main_buttons()
                    self.status.configure(text=self.t("Bekor qilindi"))
                    return
                elif m[0] == "done":
                    self._restore_main_buttons()
                    self.pbar.set(1.0)
                    self.status.configure(text=self.t("Tayyor!"))
                    if m[3]:
                        try:
                            if platform.system() == "Windows":
                                os.startfile(m[2])
                            elif platform.system() == "Darwin":
                                subprocess.Popen(["open", m[2]])
                            else:
                                subprocess.Popen(["xdg-open", m[2]])
                        except Exception:
                            pass
                    else:
                        messagebox.showinfo(self.t("Tayyor"), f"{self.t('Video yaratildi')}:\n{m[2]}")
                        if messagebox.askyesno(self.t("Shablon"), self.t("Bu sozlamalarni shablon sifatida saqlaymizmi?")):
                            self.save_template_prompt()
                    return
                elif m[0] == "err":
                    self._restore_main_buttons()
                    self.status.configure(text=self.t("Xato"))
                    messagebox.showerror("Xato", str(m[2]))
                    return
        except queue.Empty:
            pass
        self.root.after(120, self._poll)


if __name__ == "__main__":
    root = CTkDnD() if CTkDnD is not None else ctk.CTk()
    App(root)
    root.mainloop()
