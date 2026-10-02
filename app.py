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
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import customtkinter as ctk
    from PIL import Image, ImageOps, ImageTk
except Exception:
    r = tk.Tk()
    r.withdraw()
    messagebox.showerror("Kutubxona yo'q", "pip install -r requirements.txt (yoki run.bat).")
    sys.exit(1)

import image_enhance as AI
import pvs_storage as Store
import starter_pack
import studio_engine as SE

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

    def t(self, s: str) -> str:
        return s if self.lang == "lat" else lat2cyr(s)

    def _build(self) -> None:
        self._blank = ctk.CTkImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), size=(1, 1))
        head = ctk.CTkFrame(self.root, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(12, 4))
        ctk.CTkLabel(head, text="Photo Video Studio", font=self.FBIG).pack(side="left")
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
        ctk.CTkLabel(left, text=self.t("Ko'rinish"), font=self.FB).pack(anchor="w", padx=12, pady=(8, 2))
        pv = ctk.CTkFrame(left)
        pv.pack(fill="x", padx=10, pady=(0, 8))
        self.preview_lbl = ctk.CTkLabel(pv, text=self.t("Rasm tanlanmagan"), height=245, font=self.F, fg_color=("#dcdce0", "#232327"), corner_radius=8)
        self.preview_lbl.pack(fill="x", padx=6, pady=6)
        cf = ctk.CTkFrame(left, fg_color="transparent")
        cf.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(cf, text=self.t("Shu rasm ustidagi yozuv:"), font=self.F).pack(anchor="w")
        ce = ctk.CTkEntry(cf, textvariable=self.cap_var, height=40, font=self.F)
        ce.pack(fill="x", pady=(2, 0))
        ce.bind("<KeyRelease>", lambda _e: self._save_caption())

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
        self._opttr(parent, "Uslub", list(SE.STYLES.keys()), {k: k for k in SE.STYLES}, "style", extra=self._update_preview)
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
        self._opttr(parent, "Rasm joyi", list(LAYOUT_LAT.keys()), LAYOUT_LAT, "layout", extra=self._update_preview)
        ctk.CTkLabel(parent, text=self.t("Rasm kattaligi"), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkSlider(parent, from_=0.25, to=0.92, variable=self.photo_scale, command=lambda _v: self._update_preview()).pack(fill="x", padx=8)
        ctk.CTkSwitch(parent, text=self.t("Oq ramka"), variable=self.frame_var, font=self.F, command=self._update_preview).pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkSwitch(parent, text=self.t("Soya"), variable=self.shadow_var, font=self.F, command=self._update_preview).pack(anchor="w", padx=10, pady=(6, 0))

        h2("Effektlar")
        self._opttr(parent, "Rang", SE.GRADES, SE.GRADE_UZ, "grade", extra=self._update_preview, gallery=self.gallery_grade)
        self._opttr(parent, "O'tish effekti", SE.TRANSITIONS, SE.TRANS_UZ, "trans", gallery=self.gallery_trans)
        self._opttr(parent, "Harakat (zoom) kuchi", ["subtle", "normal", "strong"], KB_LAT, "kb")
        self._opttr(parent, "Vignette", ["auto", "on", "off"], VIG_LAT, "vig")
        ctk.CTkSwitch(parent, text=self.t("Film grain (don)"), variable=self.grain_var, font=self.F).pack(anchor="w", padx=10, pady=(10, 0))
        ctk.CTkSwitch(parent, text=self.t("Bloom (porlash)"), variable=self.bloom_var, font=self.F).pack(anchor="w", padx=10, pady=(8, 0))

        h2("Sifat va format")
        optplain("O'lcham", list(SE.RES.keys()), self.res_var)
        optplain("FPS (silliqlik)", ["24", "30", "60"], self.fps_var)
        self._opttr(parent, "Sifat", ["16", "18", "21", "24"], QUAL_LAT, "qual")
        optplain("Tezlik", ["ultrafast", "veryfast", "fast", "medium", "slow"], self.preset_var)
        ctk.CTkLabel(parent, text=self.t("Har rasm necha soniya"), anchor="w", font=self.F).pack(fill="x", padx=8, pady=(10, 0))
        self.dur_lbl = ctk.CTkLabel(parent, text=f"{self.dur_var.get():.1f} s", font=self.F)
        self.dur_lbl.pack(anchor="e", padx=8)
        ctk.CTkSlider(parent, from_=2.0, to=8.0, number_of_steps=30, variable=self.dur_var, command=lambda v: self.dur_lbl.configure(text=f"{float(v):.1f} s")).pack(fill="x", padx=8)

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
        self.template_list = ctk.CTkScrollableFrame(mid, width=360, label_text=self.t("Shablonlar"))
        self.template_list.pack(side="right", fill="y")

    def _build_ai_tab(self, parent) -> None:
        left = ctk.CTkFrame(parent)
        left.pack(side="left", fill="both", expand=True, padx=(10, 6), pady=10)
        right = ctk.CTkScrollableFrame(parent, width=390, label_text=self.t("Professional panel"))
        right.pack(side="right", fill="y", padx=(6, 10), pady=10)
        self.ai_title = ctk.CTkLabel(left, text=self.t("Rasm tanlang va AI/Professional sozlashni qo'llang"), font=self.FH)
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

        ctk.CTkLabel(right, text=self.t("Bu panel original rasmni o'zgartirmaydi."), text_color="#8a8a8a", font=self.F).pack(fill="x", padx=8, pady=(8, 4))
        slider("Yorug'lik", self.ai_brightness, 0.65, 1.45)
        slider("Kontrast", self.ai_contrast, 0.7, 1.6)
        slider("Rang to'yinganligi", self.ai_saturation, 0.5, 1.8)
        slider("Iliqlik / sovuqlik", self.ai_warmth, -0.7, 0.7)
        slider("Aniqlik", self.ai_sharpness, 0.6, 2.4)
        slider("Shovqinni kamaytirish", self.ai_denoise, 0.0, 0.55)
        ctk.CTkLabel(right, text=self.t("Upscale"), font=self.F, anchor="w").pack(fill="x", padx=8, pady=(10, 0))
        ctk.CTkOptionMenu(right, values=["auto", "none", "HD", "2K", "4K"], variable=self.ai_upscale, height=38).pack(fill="x", padx=8)
        ctk.CTkSwitch(right, text=self.t("Face-safe restore"), variable=self.ai_face, font=self.F).pack(anchor="w", padx=10, pady=(10, 4))
        ctk.CTkButton(right, text=self.t("Tanlangan rasmni yaxshilash"), height=42, font=self.FB, command=lambda: self.apply_ai(False)).pack(fill="x", padx=8, pady=(10, 4))
        ctk.CTkButton(right, text=self.t("Hammasini yaxshilash"), height=42, font=self.FB, fg_color="#3a7d44", command=lambda: self.apply_ai(True)).pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(right, text=self.t("OpenAI bilan tanlangan rasm"), height=42, font=self.FB, fg_color="#6b4fa3", command=self.apply_openai_selected).pack(fill="x", padx=8, pady=(14, 4))
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
        self.settings_status = ctk.CTkLabel(box, text="", font=self.F, anchor="w")
        self.settings_status.pack(fill="x", padx=8, pady=8)

    def _lang(self, val):
        self.lang = "lat" if val == "Lotin" else "cyr"
        for w in self.root.winfo_children():
            w.destroy()
        self._build()
        if self.cur is not None:
            self._update_preview()
            self._update_ai_compare()

    def _check_ffmpeg(self):
        if SE.find_ffmpeg():
            self.ff_lbl.configure(text="ffmpeg: ok", text_color="#4caf50")
        else:
            self.ff_lbl.configure(text="ffmpeg: topilmadi", text_color="#e05a5a")
            messagebox.showwarning("ffmpeg", self.t("ffmpeg topilmadi. winget install Gyan.FFmpeg yoki 'ffmpeg.exe ni ko'rsatish'."))

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
            self.items.append({"path": p, "caption": "", "tpil": tp, "ppil": pp, "orig_ppil": pp.copy(), "enhanced_path": ""})
            added += 1
        self._rebuild()
        if added and self.cur is None:
            self.select(len(self.items) - 1)
        elif added:
            self.status.configure(text=self.t("Rasmlar qo'shildi."))

    def remove_photo(self):
        if self.cur is None:
            return
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
        cap = f"\n     «{it['caption']}»" if it["caption"] else ""
        return f"{i + 1}.  {os.path.basename(it['path'])}{mark}{cap}"

    def _highlight(self):
        for i, rf in enumerate(self.row_frames):
            rf.configure(fg_color=ROW_SEL if i == self.cur else ROW_BG)

    def select(self, i):
        if i is None or not (0 <= i < len(self.items)):
            return
        self._save_caption()
        self.cur = i
        self._highlight()
        self.cap_var.set(self.items[i]["caption"])
        self._update_preview()
        self._update_ai_compare()

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

    def _update_preview(self):
        if self.cur is None:
            return
        try:
            src = self._preview_source(self.items[self.cur])
            g = SE.grade(src, self._rgrade())
            if self.bg_path.get() and os.path.isfile(self.bg_path.get()):
                g = SE.compose_background_scene(g, self.bg_path.get(), 640, 360, self.sel["layout"], self.photo_scale.get(), self._photo_frame())
            im = ctk.CTkImage(light_image=g, dark_image=g, size=g.size)
            self._prev_img = im
            self.preview_lbl.configure(image=im, text="")
        except Exception:
            pass

    def _update_ai_preview_only(self):
        if self.cur is not None:
            self._update_ai_compare()

    def _drag_ai_compare(self, event):
        if not hasattr(self, "ai_canvas"):
            return
        width = max(1, self.ai_canvas.winfo_width())
        pct = max(0, min(100, (event.x / width) * 100))
        self.ai_compare.set(pct)
        self._draw_ai_compare()

    def _update_ai_compare(self):
        if self.cur is None:
            return
        try:
            item = self.items[self.cur]
            original = ImageOps.exif_transpose(Image.open(item["path"])).convert("RGB")
            if item.get("enhanced_path") and os.path.isfile(item["enhanced_path"]):
                enhanced = ImageOps.exif_transpose(Image.open(item["enhanced_path"])).convert("RGB")
            else:
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                tmp.close()
                AI.enhance_local(item["path"], tmp.name, self._enhance_settings())
                enhanced = ImageOps.exif_transpose(Image.open(tmp.name)).convert("RGB")
                try:
                    os.remove(tmp.name)
                except OSError:
                    pass
            self._ai_original_pil = original
            self._ai_enhanced_pil = enhanced
            self._draw_ai_compare()
            self.ai_title.configure(text=os.path.basename(item["path"]))
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
        self._update_preview()
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
            self._update_preview()
        except Exception as exc:
            messagebox.showerror("Background", str(exc))

    def clear_background(self):
        self.bg_path.set("")
        self.settings["last_background"] = ""
        Store.save_settings(self.settings)
        self._refresh_backgrounds()
        self._update_preview()

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
        self._update_preview()

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
            self._update_preview()
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
        return {
            "style": self.sel["style"],
            "grade": self.sel["grade"],
            "transition_type": self.sel["trans"],
            "kb_intensity": self.sel["kb"],
            "vignette": self.sel["vig"],
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
        for row_meta in Store.list_templates(with_meta=True):
            p = row_meta["path"]
            name = row_meta.get("name") or p.stem
            row = ctk.CTkFrame(self.template_list)
            row.pack(fill="x", padx=6, pady=5)
            preview = str(row_meta.get("preview_path") or "")
            if preview and os.path.isfile(preview):
                try:
                    im = ImageOps.exif_transpose(Image.open(preview)).convert("RGB")
                    im.thumbnail((92, 58), Image.LANCZOS)
                    cimg = ctk.CTkImage(light_image=im, dark_image=im, size=im.size)
                    refs.append(cimg)
                    ctk.CTkLabel(row, image=cimg, text="").pack(side="left", padx=6, pady=6)
                except Exception:
                    pass
            ctk.CTkLabel(row, text=str(name), anchor="w", font=self.F).pack(side="left", fill="x", expand=True, padx=8, pady=8)
            ctk.CTkButton(row, text=self.t("O'chirish"), width=82, fg_color="#8a3c3c", command=lambda pp=p: self.delete_template_confirm(pp)).pack(side="right", padx=(0, 4))
            ctk.CTkButton(row, text=self.t("Nomlash"), width=82, fg_color="#5a5a5a", command=lambda pp=p: self.rename_template_prompt(pp)).pack(side="right", padx=(0, 4))
            ctk.CTkButton(row, text=self.t("Ochish"), width=90, command=lambda pp=p: self.load_template(pp)).pack(side="right", padx=6)
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
            self.sel["vig"] = data.get("vignette", self.sel["vig"])
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
                elif key == "vig":
                    var.set(self.t(VIG_LAT[self.sel["vig"]]))
                elif key == "style":
                    var.set(self.t(self.sel["style"]))
                elif key == "layout":
                    var.set(self.t(LAYOUT_LAT[self.sel["layout"]]))
            self._refresh_backgrounds()
            self._update_preview()
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

    def _ai_targets(self, all_photos: bool):
        if all_photos:
            return list(range(len(self.items)))
        return [] if self.cur is None else [self.cur]

    def apply_ai(self, all_photos: bool):
        targets = self._ai_targets(all_photos)
        if not targets:
            messagebox.showwarning("", self.t("Avval rasm tanlang."))
            return
        self._start_ai_job(targets, "local")

    def apply_openai_selected(self):
        if self.cur is None:
            messagebox.showwarning("", self.t("Avval rasm tanlang."))
            return
        if not self.consent_var.get():
            ok = messagebox.askyesno(self.t("AI rozilik"), self.t("OpenAI ishlaganda tanlangan rasm internet orqali AI xizmatiga yuboriladi. Davom etamizmi?"))
            if not ok:
                return
            self.consent_var.set(True)
            self.save_settings()
        key = Store.get_api_key("openai")
        if not key:
            messagebox.showwarning("OpenAI", self.t("Sozlamalarda OpenAI API key saqlang."))
            return
        self._start_ai_job([self.cur], "openai")

    def _start_ai_job(self, targets, mode):
        if self.busy:
            return
        self.busy = True
        self.cancel_event.clear()
        self.status.configure(text=self.t("AI ishlayapti..."))
        self.gen_btn.configure(state="disabled")
        self.prev_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        threading.Thread(target=self._ai_worker, args=(targets, mode), daemon=True).start()
        self.root.after(120, self._poll)

    def _ai_worker(self, targets, mode):
        try:
            settings = self._enhance_settings()
            key = Store.get_api_key("openai") if mode == "openai" else ""
            for n, idx in enumerate(targets, 1):
                if self.cancel_event.is_set():
                    self.q.put(("cancelled", 0, self.t("Bekor qilindi"), False))
                    return
                item = self.items[idx]
                provider = "openai" if mode == "openai" else "local"
                model = self.model_var.get() if mode == "openai" else "pillow-local"
                out = AI.cache_path(item["path"], settings, provider, model)
                if not out.exists():
                    if mode == "openai":
                        AI.openai_enhance(item["path"], out, key, model=self.model_var.get(), quality=self.openai_quality_var.get())
                    else:
                        AI.enhance_local(item["path"], out, settings)
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
        return dict(
            photos=[it["path"] for it in self.items],
            captions={i + 1: it["caption"] for i, it in enumerate(self.items) if it["caption"].strip()},
            enhanced_photos=enhanced,
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
        self._save_caption()
        if not self._precheck():
            return
        if not self.out_var.get():
            messagebox.showwarning("", self.t("Chiqish faylini tanlang."))
            return
        c = self._base_cfg()
        c.update(resolution=self.res_var.get(), photo_duration=float(self.dur_var.get()), transition_dur=0.7, title_duration=6.0, outro_duration=4.5, crf=int(self.sel["qual"]), output=self.out_var.get())
        self._start(c, False)

    def preview_sample(self):
        self._save_caption()
        if not self._precheck():
            return
        c = self._base_cfg()
        c["photos"] = c["photos"][:4]
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
