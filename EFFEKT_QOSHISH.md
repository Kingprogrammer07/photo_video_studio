# 🎨 Yangi effekt qo'shish

Effektlar **studio_engine.py** faylida. Qo'shsangiz, ular avtomatik dastur menyularida chiqadi.

## 1. Yangi RANG (grade) qo'shish

`studio_engine.py` ni oching:

**a)** `GRADES` ro'yxatiga nom qo'shing va `GRADE_UZ` ga o'zbekcha yorlig'ini:
```python
GRADES = [..., "mint"]                 # yangi ichki nom
GRADE_UZ = {..., "mint": "Yalpiz"}     # menyuda ko'rinadigan nom
```

**b)** `grade(im, mode)` funksiyasiga shu nom uchun bir tarmoq qo'shing (numpy bilan):
```python
elif mode == "mint":
    a[...,1] = np.clip(a[...,1]*1.08, 0, 1)   # yashilni oshirish
    a[...,0] = np.clip(a[...,0]*0.95, 0, 1)
    sat = 1.05
```
`a` — [balandlik, kenglik, 3] RGB (0..1). Oxirida umumiy `sat` (to'yinganlik) qo'llanadi.

Tayyor! Dasturda "Rang → Yalpiz" chiqadi.

## 2. Yangi O'TISH (transition) qo'shish

**a)** `TRANSITIONS` va `TRANS_UZ` ga qo'shing:
```python
TRANSITIONS = [..., "zoom"]
TRANS_UZ = {..., "zoom": "Zoom"}
```

**b)** `_trans_list()` ichidagi `M` lug'atiga ffmpeg xfade nomini bering:
```python
M = {..., "zoom": ["zoomin"]}
```
Ikki nom bersangiz (mas. `["slideleft","slideright"]`) — navbatma-navbat ishlatiladi.

### Mavjud ffmpeg xfade o'tishlari (ro'yxatdan tanlang):
`fade, fadeblack, fadewhite, dissolve, pixelize, wipeleft/right/up/down,
slideleft/right/up/down, smoothleft/right/up/down, circleopen, circleclose,
circlecrop, rectcrop, radial, hblur, diagtl, diagtr, diagbl, diagbr,
horzopen, horzclose, vertopen, vertclose, distance, fadegrays` va boshqalar.

## 3. Bloom / grain / vignette
Bular allaqachon bor (`render_scene` ichida). Kuchini o'zgartirish uchun:
- **Bloom:** `render_scene` da `all_opacity=0.22` sonini o'zgartiring (0.1–0.4).
- **Grain:** `_vf` da `noise=alls=6` — 6 ni oshiring/kamaytiring.
- **Vignette:** `_vf` da `vignette=PI/5.0` — PI/4 (kuchli) ... PI/6 (yumshoq).

## 4. Yangi uslub (butun paket)
`STYLES` lug'atiga yangi kalit qo'shing (rang, karta foni, shrift, o'tish, musiqa).
Namuna sifatida mavjud ikki uslubga qarang.

> O'zgarishdan keyin dasturni qayta oching — yangi effekt menyularда chiqadi.
