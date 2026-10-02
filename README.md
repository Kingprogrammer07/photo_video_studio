# 🎬 Photo Video Studio

Rasmlaringizdan kinematik slideshow video yasaydigan **desktop dastur** (CustomTkinter).
ProShow Producer uslubida — rasm yuklaysiz, uslub/effekt/sifatni tanlaysiz, "Video yaratish"
bosasiz. Tayyor MP4 chiqadi.

---

## ⚡ Oson ishga tushirish

**Eng oson yo'l (Windows):** `run.bat` faylini ikki marta bosing — u kerakli kutubxonalarni
o'rnatadi va dasturni ochadi.

**Qo'lda:**
```bash
pip install -r requirements.txt
python app.py
```

**Talab:**
- Python 3.9+
- **ffmpeg** — PATH da bo'lishi shart. Windows: `winget install Gyan.FFmpeg`
  (tekshirish: `ffmpeg -version`)

---

## 🖥  Standalone `.exe` (Python'siz ochiladigan)

Bir marta `build_exe.bat` ni ishga tushiring — `dist\PhotoVideoStudio.exe` yaratiladi.
Uni istalgan Windows kompyuterda ikki marta bosib ochish mumkin (Python o'rnatish shart emas).
> Eslatma: ffmpeg baribir tizimда bo'lishi kerak (yoki exe yoniga `ffmpeg.exe` qo'ying).

---

## ✨ Imkoniyatlar

**2 uslub:**
- **Iliq oltin (kinematik)** — qora fon, kalligrafik shrift, oltin nur, vignette.
- **Zamonaviy yorqin** — och/oq fon, qalin sans-serif, coral accent, slide o'tishlar.

**Effektlar (har biri sozlanadi):**
- **Rang (grade):** Avto / Iliq / Neytral / Yorqin / Oq-qora / Vintage / Yo'q
- **O'tish effekti:** Fade / Slide / Wipe / Circle / Dissolve / Radial
- **Ken Burns kuchi:** Yumshoq / O'rta / Kuchli (zoom-pan harakati)
- **Vignette** va **Film grain (don)** — yoqish/o'chirish

**Sifat / format:**
- **O'lcham:** 1080p / 1440p (2K) / 2160p (4K) / Vertical 1080×1920 / Kvadrat
- **FPS:** 24 / 30 / 60
- **Sifat:** Yuqori / Yaxshi / O'rta / Tez  (+ tezlik preset)

**Matnlar:** Sarlavha, yuqori yozuv, sana, yakun izohi/yozuvi, va har rasmga alohida caption.

**Musiqa:** Avtomatik original pianino (uslubga mos) yoki o'z mp3/wav faylingiz.

---

## 📋 Ishlatish tartibi

1. **＋ Qo'shish** — rasmlarni tanlang (bir nechta bo'lishi mumkin).
2. Kerak bo'lsa **▲ ▼** bilan tartibni o'zgartiring.
3. Rasmni tanlab, pastdagi maydonga **caption** yozing (ixtiyoriy).
4. O'ngdan **uslub, effekt, sifat, fps** ni tanlang.
5. **Chiqish fayli** ni belgilang.
6. **🎬 Video yaratish** — progress bar to'lguncha kuting.

---

## 📂 Tuzilma

```
photo_video_studio/
├── app.py            # dastur (shuni ishga tushirasiz)
├── studio_engine.py  # video engine (grade, kartalar, sahnalar, merge)
├── music.py          # original pianino generator (2 uslub)
├── fonts/            # ichiga joylangan shriftlar
├── run.bat           # oson ishga tushirish
├── build_exe.bat     # standalone .exe yasash
├── requirements.txt
└── output/           # tayyor videolar
```

Shriftlar ichida — har qanday kompyuterda bir xil ko'rinadi. Biror shrift bo'lmasa,
avtomatik tizim shriftiga o'tadi.

---

## 💡 Maslahatlar

- **Tez sinash:** sifatni "Tez" + FPS 30 + 1080p qo'ying — tez render bo'ladi.
- **Eng zo'r sifat:** 2K yoki 4K + FPS 60 + Sifat "Yuqori" + preset "medium/slow" (sekinroq).
- Rasm soni ixtiyoriy — 5 ta ham, 50 ta ham.
- Vertical format Instagram Reels / Telegram status uchun.

Yangi uslub yoki effekt kerak bo'lsa — ayting, qo'shamiz. 🎥

---

## ❗ Muammolar (Troubleshooting)

**"[WinError 2] The system cannot find the file specified"**
Bu — **ffmpeg topilmadi** degani. Yechim:
1. ffmpeg o'rnating:  `winget install Gyan.FFmpeg`  (yoki https://ffmpeg.org/download.html)
2. Yangi oyna oching (PATH yangilanishi uchun) va qaytadan urinib ko'ring.
3. Agar ffmpeg allaqachon bor bo'lsa — dastur pastidagi **"ffmpeg.exe ni ko'rsatish"**
   tugmasini bosib, `ffmpeg.exe` faylini tanlang.

Dastur ochilganda ffmpeg holatini pastda ko'rsatadi (✔ topildi / ✗ topilmadi).

**Rasm ko'rinishi (preview):** har bir rasm ro'yxatda kichik ko'rinishi (thumbnail) bilan
chiqadi; tanlangan rasm katta preview'da ko'rinadi. Tartibni **▲ ▼** bilan o'zgartirasiz.

---

## 🆕 Yangiliklar (v2)

- **Ko'proq effektlar:** ranglar — Iliq, Salqin, Neytral, Yorqin, Jonli, Yumshoq, Sepia, Oq-qora, Vintage.
  O'tishlar — Fade, Qoraga, Oqqa, Slide, Push, Wipe, Doira, Radial, Piksel, Blur, Erish, Diagonal.
  Yangi: **Bloom** (yumshoq porlash) va **Film grain** kalitlari.
- **Rang preview:** rangni tanlaganingizda tanlangan rasm o'sha rang bilan **jonli** ko'rinadi.
- **👁 Qisqa namuna** tugmasi: joriy sozlamalar bilan ~5 soniyalik test video yaratib, darrov ochib beradi
  (barcha effektlarni harakatda ko'rasiz) — to'liq render kutmasdan.
- **Oson dizayn:** yirik tugmalar va shriftlar (yoshi kattalarga qulay).
- **To'liq offline:** kerakli Python kutubxonalari `wheels/` ichida — birinchi ishga tushirish
  internetsiz ham ishlaydi. `run.bat` avtomatik **virtual muhit (.venv)** yaratadi.
- **Yangi effekt qo'shish:** `EFFEKT_QOSHISH.md` ga qarang — bir-ikki qator kod bilan qo'shiladi.

### Ishga tushirish (yangilangan)
`run.bat` ni ikki marta bosing → birinchi marta `.venv` yaratadi va kutubxonalarni
offline o'rnatadi (~1 daqiqa), keyingi safarlar darrov ochiladi.
