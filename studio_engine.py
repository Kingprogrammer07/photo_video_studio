"""
studio_engine.py — style- and effect-aware cinematic slideshow engine.
build_video(config, progress) => grade -> cards -> scenes -> merge -> music -> mux.
Pure Pillow + numpy + ffmpeg. Fonts from ./fonts then system.

YANGI EFFEKT QO'SHISH: pastdagi GRADES/grade() (rang uchun) yoki
TRANSITIONS/_trans_list() (o'tish uchun) ga bitta qator qo'shing. Batafsil: EFFEKT_QOSHISH.md
"""
import os, math, tempfile, subprocess, shutil, time, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import runtime_paths

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(HERE, "fonts")
RES = {"720p (tez)": (1280,720), "1080p": (1920,1080), "1440p (2K)": (2560,1440),
       "2160p (4K)": (3840,2160), "Vertical 1080x1920": (1080,1920), "Kvadrat 1080": (1080,1080)}


class CancelledError(RuntimeError):
    """Raised when the user cancels a render."""

# --- EFFEKTLAR ro'yxati (GUI shulardan menyu yasaydi) ---
GRADES = ["auto","warm","cool","neutral","bright","vivid","soft","sepia","bw","vintage","none"]
GRADE_UZ = {"auto":"Avto","warm":"Iliq","cool":"Salqin","neutral":"Neytral","bright":"Yorqin",
            "vivid":"Jonli","soft":"Yumshoq","sepia":"Sepia","bw":"Oq-qora","vintage":"Vintage","none":"Yo'q"}
TRANSITIONS = ["auto","fade","fadeblack","fadewhite","slide","push","wipe","circle","radial","pixelize","blur","dissolve","diagonal"]
TRANS_UZ = {"auto":"Avto","fade":"Fade","fadeblack":"Qoraga","fadewhite":"Oqqa","slide":"Slide","push":"Push",
            "wipe":"Wipe","circle":"Doira","radial":"Radial","pixelize":"Piksel","blur":"Blur","dissolve":"Erish","diagonal":"Diagonal"}
KB_LEVELS = {"subtle": 0.08, "normal": 0.15, "strong": 0.24}
MOTION_SETTING_LIMITS = {
    "start_scale": (0.05, 3.0),
    "end_scale": (0.05, 3.0),
    "speed": (0.25, 3.0),
    "start_x": (-1.0, 1.0),
    "end_x": (-1.0, 1.0),
    "start_y": (-1.0, 1.0),
    "end_y": (-1.0, 1.0),
}
MOTION_PRESETS = [
    "auto",
    "still",
    "zoom_in",
    "zoom_out",
    "tiny_to_big",
    "dramatic_zoom",
    "left_to_center",
    "right_to_center",
    "slow_pan_left",
    "slow_pan_right",
    "bottom_to_center",
]
MOTION_UZ = {
    "auto": "Avto",
    "still": "Harakatsiz",
    "zoom_in": "Yaqinlashish",
    "zoom_out": "Uzoqlashish",
    "tiny_to_big": "Kichikdan katta",
    "dramatic_zoom": "Kuchli zoom",
    "left_to_center": "Chapdan markazga",
    "right_to_center": "O'ngdan markazga",
    "slow_pan_left": "Sekin chapga",
    "slow_pan_right": "Sekin o'ngga",
    "bottom_to_center": "Pastdan markazga",
}

def normalize_motion_preset(preset):
    preset = (preset or "auto").lower()
    return preset if preset in MOTION_PRESETS else "auto"

def _bounded_float(value, default, lo, hi):
    try:
        value = float(value)
    except Exception:
        value = default
    return max(lo, min(hi, value))

def normalize_motion_settings(settings):
    if not isinstance(settings, dict):
        return None
    out = {}
    for key, (lo, hi) in MOTION_SETTING_LIMITS.items():
        if key in settings and settings.get(key) is not None:
            default = 1.0 if key == "speed" else 0.0
            out[key] = _bounded_float(settings.get(key), default, lo, hi)
    return out or None

def _offset_to_pixels(value, axis):
    try:
        v = float(value)
    except Exception:
        return 0.0
    if abs(v) <= 1.0:
        return v * axis
    return v

def _motion_progress_expr(progress, speed):
    speed = _bounded_float(speed, 1.0, 0.25, 3.0)
    exponent = 1.0 / speed
    return f"pow({progress},{exponent:.5f})"

def resolve_photo_durations(count, default_duration, overrides=None):
    result = []
    overrides = list(overrides or [])
    for idx in range(count):
        try:
            value = float(overrides[idx])
        except Exception:
            value = float(default_duration)
        result.append(max(0.4, value))
    return result

def resolve_text_flags(config):
    text_enabled = bool(config.get("text_enabled", True))
    return {
        "text_enabled": text_enabled,
        "show_title_card": bool(config.get("show_title_card", text_enabled)) and text_enabled,
        "show_outro_card": bool(config.get("show_outro_card", text_enabled)) and text_enabled,
        "show_captions": bool(config.get("show_captions", text_enabled)) and text_enabled,
    }

_CAND = {
 "script":  ["chancery.pfb","C:/Windows/Fonts/GABRIOLA.TTF","/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"],
 "serif":   ["palladio.pfb","C:/Windows/Fonts/georgia.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
 "serif_it":["palladio_italic.pfb","C:/Windows/Fonts/georgiai.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"],
 "book":    ["gothic_book.pfb","C:/Windows/Fonts/segoeui.ttf","C:/Windows/Fonts/arial.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
 "demi":    ["gothic_demi.pfb","C:/Windows/Fonts/segoeuib.ttf","C:/Windows/Fonts/arialbd.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
}
FONT_PRESETS = ["default", "classic", "modern", "serif", "script"]
FONT_UZ = {
    "default": "Uslubdagi font",
    "classic": "Klassik",
    "modern": "Zamonaviy",
    "serif": "Kitobiy",
    "script": "Bezakli",
}
_fc={}
def font(role,size):
    k=(role,int(size))
    if k in _fc: return _fc[k]
    for c in _CAND.get(role,[]):
        p=c if (os.path.isabs(c) or ":" in c) else os.path.join(FONTS_DIR,c)
        try: f=ImageFont.truetype(p,int(size)); _fc[k]=f; return f
        except Exception: continue
    f=ImageFont.load_default(); _fc[k]=f; return f

def apply_font_preset(st, preset):
    preset = (preset or "default").lower()
    if preset not in FONT_PRESETS:
        preset = "default"
    if preset == "default":
        return st
    out = dict(st)
    fonts = dict(st.get("fonts", {}))
    if preset == "classic":
        fonts.update(title="serif", kicker="book", sub="serif", cap="serif_it")
    elif preset == "modern":
        fonts.update(title="demi", kicker="book", sub="book", cap="demi")
    elif preset == "serif":
        fonts.update(title="serif", kicker="serif", sub="serif", cap="serif_it")
    elif preset == "script":
        fonts.update(title="script", kicker="book", sub="serif", cap="script")
    out["fonts"] = fonts
    return out

STYLES={
 "Iliq oltin (kinematik)": dict(key="warm", grade="neutral", card_bg="dark", vignette=True,
    transition="fade", music="warm", caption="glow",
    col=dict(text=(248,224,176),kicker=(216,184,140),sub=(224,196,152),accent=(212,170,110),fx=(255,170,80)),
    fonts=dict(title="script",kicker="book",sub="serif",cap="script")),
 "Zamonaviy yorqin": dict(key="modern", grade="bright", card_bg="light", vignette=False,
    transition="slide", music="bright", caption="halo",
    col=dict(text=(46,46,52),kicker=(214,120,104),sub=(120,116,120),accent=(214,120,104),fx=(255,255,255)),
    fonts=dict(title="demi",kicker="book",sub="book",cap="demi")),
}

def load_photo(p):
    im=Image.open(p); return ImageOps.exif_transpose(im).convert("RGB")

def grade(im,mode):
    if mode in ("none","auto"): return im
    a=np.asarray(im).astype(np.float32)/255.0
    if mode=="bw":
        g=a[...,0]*0.299+a[...,1]*0.587+a[...,2]*0.114; g=np.clip((g-0.5)*1.12+0.5,0,1)
        return Image.fromarray((np.repeat(g[...,None],3,axis=2)*255).astype(np.uint8))
    if mode=="sepia":
        g=a[...,0]*0.299+a[...,1]*0.587+a[...,2]*0.114
        a=np.stack([np.clip(g*1.07+0.05,0,1),np.clip(g*0.82+0.03,0,1),np.clip(g*0.62,0,1)],axis=2)
        return Image.fromarray((a*255).astype(np.uint8))
    if mode=="warm":
        a=np.clip((a-0.5)*1.10+0.5,0,1); a[...,0]=np.clip(a[...,0]*1.10,0,1); a[...,2]=np.clip(a[...,2]*0.85,0,1)
        sh=1-a; a[...,0]=np.clip(a[...,0]+0.035*sh[...,0],0,1); sat=1.14
    elif mode=="cool":
        a=np.clip((a-0.5)*1.08+0.5,0,1); a[...,2]=np.clip(a[...,2]*1.10,0,1); a[...,0]=np.clip(a[...,0]*0.93,0,1)
        sh=1-a; a[...,2]=np.clip(a[...,2]+0.03*sh[...,2],0,1); sat=1.05
    elif mode=="bright":
        a=1-(1-a)**1.12; a=np.clip((a-0.5)*1.03+0.5,0,1); a[...,2]=np.clip(a[...,2]*1.015,0,1); a[...,0]=np.clip(a[...,0]*0.997,0,1); sat=1.13
    elif mode=="vivid":
        a=np.clip((a-0.5)*1.13+0.5,0,1); sat=1.38
    elif mode=="soft":
        a=np.clip((a-0.5)*0.90+0.5,0,1); a=a*0.90+0.07; sat=0.95
    elif mode=="vintage":
        a=np.clip((a-0.5)*0.92+0.5,0,1); a=a*0.94+0.05; a[...,0]=np.clip(a[...,0]*1.06,0,1); a[...,2]=np.clip(a[...,2]*0.90,0,1); sat=0.80
    else:
        a=np.clip((a-0.5)*1.04+0.5,0,1); sat=1.05
    g=a[...,0]*0.299+a[...,1]*0.587+a[...,2]*0.114
    a=np.clip(g[...,None]+(a-g[...,None])*sat,0,1)
    return Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8))

def warm_gradient(w,h):
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32); cx,cy=w*0.5,h*0.46
    d=np.clip(np.sqrt(((xx-cx)/(w*0.62))**2+((yy-cy)/(h*0.62))**2),0,1)
    img=np.array([56,35,17],np.float32)*(1-d[...,None])+np.array([11,8,6],np.float32)*d[...,None]
    glow=np.exp(-(((xx-cx)/(w*0.34))**2+((yy-cy*1.05)/(h*0.34))**2))
    img+=glow[...,None]*np.array([42,25,9],np.float32)
    return Image.fromarray(np.clip(img,0,255).astype(np.uint8))
def light_bg(w,h,accent=(224,137,126)):
    yy=np.linspace(0,1,h)[:,None,None].astype(np.float32)
    img=np.repeat(np.array([247,242,236],np.float32)*(1-yy)+np.array([233,224,214],np.float32)*yy,w,axis=1)
    xx,yg=np.meshgrid(np.linspace(0,1,w),np.linspace(0,1,h))
    blob=np.exp(-(((xx-0.80)/0.35)**2+((yg-0.80)/0.35)**2))*0.16
    img=img*(1-blob[...,None])+np.array(accent,np.float32)*blob[...,None]
    return Image.fromarray(np.clip(img,0,255).astype(np.uint8))

def _cover(im,w,h):
    im=ImageOps.exif_transpose(im).convert("RGB")
    s=max(w/im.width,h/im.height)
    nw,nh=max(1,int(im.width*s)),max(1,int(im.height*s))
    im=im.resize((nw,nh),Image.LANCZOS)
    return im.crop(((nw-w)//2,(nh-h)//2,(nw+w)//2,(nh+h)//2))

def _photo_box(W,H,layout,scale):
    scale=float(scale or 0.66); scale=max(0.18,min(0.96,scale))
    bw=int(W*scale); bh=int(H*scale)
    layout=(layout or "center").lower()
    margin=int(min(W,H)*0.07)
    if layout=="left": cx=margin+bw//2; cy=H//2
    elif layout=="right": cx=W-margin-bw//2; cy=H//2
    elif layout=="top": cx=W//2; cy=margin+bh//2
    elif layout=="bottom": cx=W//2; cy=H-margin-bh//2
    elif layout=="fill": cx=W//2; cy=H//2; bw=int(W*0.88); bh=int(H*0.82)
    else: cx=W//2; cy=H//2
    return (max(0,int(cx-bw/2)),max(0,int(cy-bh/2)),min(W,int(cx+bw/2)),min(H,int(cy+bh/2)))

def _fit_in_box(im,box):
    x1,y1,x2,y2=box; bw=max(1,x2-x1); bh=max(1,y2-y1)
    src=ImageOps.exif_transpose(im).convert("RGB")
    s=min(bw/src.width,bh/src.height)
    nw,nh=max(1,int(src.width*s)),max(1,int(src.height*s))
    return src.resize((nw,nh),Image.LANCZOS)

def _paste_with_round(base,photo,x,y,radius):
    if radius<=0:
        base.paste(photo,(x,y)); return
    mask=Image.new("L",photo.size,0)
    d=ImageDraw.Draw(mask); d.rounded_rectangle([0,0,photo.width-1,photo.height-1],radius=radius,fill=255)
    base.paste(photo,(x,y),mask)

def _motion_spec(preset,i=0,amt=0.15,W=1920,H=1080,settings=None):
    preset=normalize_motion_preset(preset)
    if preset=="auto":
        zdir,dx,dy=_kb(i)
        if zdir=="out": ss,es=1.08+amt,1.02
        else: ss,es=1.02,1.08+amt
        spec=dict(preset=preset,start_scale=ss,end_scale=es,start_dx=-dx*W*0.04,end_dx=dx*W*0.04,start_dy=-dy*H*0.035,end_dy=dy*H*0.035,speed=1.0)
    elif preset=="still": spec=dict(preset=preset,start_scale=1.0,end_scale=1.0,start_dx=0,end_dx=0,start_dy=0,end_dy=0,speed=1.0)
    elif preset=="zoom_in": spec=dict(preset=preset,start_scale=0.92,end_scale=1.15,start_dx=0,end_dx=0,start_dy=0,end_dy=0,speed=0.9)
    elif preset=="zoom_out": spec=dict(preset=preset,start_scale=1.15,end_scale=0.96,start_dx=0,end_dx=0,start_dy=0,end_dy=0,speed=0.9)
    elif preset=="tiny_to_big": spec=dict(preset=preset,start_scale=0.45,end_scale=1.10,start_dx=0,end_dx=0,start_dy=0,end_dy=0,speed=0.65)
    elif preset=="dramatic_zoom": spec=dict(preset=preset,start_scale=0.35,end_scale=1.50,start_dx=0,end_dx=0,start_dy=0,end_dy=0,speed=0.85)
    elif preset=="left_to_center": spec=dict(preset=preset,start_scale=0.90,end_scale=1.18,start_dx=-W*0.12,end_dx=0,start_dy=0,end_dy=0,speed=0.9)
    elif preset=="right_to_center": spec=dict(preset=preset,start_scale=0.90,end_scale=1.18,start_dx=W*0.12,end_dx=0,start_dy=0,end_dy=0,speed=0.9)
    elif preset=="slow_pan_left": spec=dict(preset=preset,start_scale=1.12,end_scale=1.12,start_dx=W*0.06,end_dx=-W*0.06,start_dy=0,end_dy=0,speed=0.75)
    elif preset=="slow_pan_right": spec=dict(preset=preset,start_scale=1.12,end_scale=1.12,start_dx=-W*0.06,end_dx=W*0.06,start_dy=0,end_dy=0,speed=0.75)
    elif preset=="bottom_to_center": spec=dict(preset=preset,start_scale=0.90,end_scale=1.15,start_dx=0,end_dx=0,start_dy=H*0.10,end_dy=0,speed=0.85)
    else:
        return _motion_spec("auto",i,amt,W,H,settings)
    custom=normalize_motion_settings(settings)
    if custom:
        if "start_scale" in custom: spec["start_scale"]=custom["start_scale"]
        if "end_scale" in custom: spec["end_scale"]=custom["end_scale"]
        if "speed" in custom: spec["speed"]=custom["speed"]
        if "start_x" in custom: spec["start_dx"]=_offset_to_pixels(custom["start_x"],W)
        if "end_x" in custom: spec["end_dx"]=_offset_to_pixels(custom["end_x"],W)
        if "start_y" in custom: spec["start_dy"]=_offset_to_pixels(custom["start_y"],H)
        if "end_y" in custom: spec["end_dy"]=_offset_to_pixels(custom["end_y"],H)
    return spec

def _photo_panel(photo,box,frame=None):
    frame=frame or {}
    ph=_fit_in_box(photo,box).convert("RGBA")
    border=bool(frame.get("border",True)); shadow=bool(frame.get("shadow",True))
    radius=int(frame.get("radius",0)); bw=int(frame.get("border_width",max(6,ph.height*0.018))) if border else 0
    pad=max(36,bw+18) if shadow else max(10,bw+4)
    panel=Image.new("RGBA",(ph.width+bw*2+pad*2,ph.height+bw*2+pad*2),(0,0,0,0))
    ox=pad+bw; oy=pad+bw
    if shadow:
        sh=Image.new("RGBA",(ph.width+bw*2+40,ph.height+bw*2+40),(0,0,0,0))
        sd=ImageDraw.Draw(sh); sd.rounded_rectangle([20,20,20+ph.width+bw*2,20+ph.height+bw*2],radius=radius+bw+6,fill=(0,0,0,150))
        sh=sh.filter(ImageFilter.GaussianBlur(max(8,int(ph.height*0.025))))
        panel.alpha_composite(sh,(pad-20,pad-10))
    if border:
        bg=Image.new("RGBA",(ph.width+bw*2,ph.height+bw*2),(255,255,255,255))
        if radius>0:
            mask=Image.new("L",bg.size,0)
            d=ImageDraw.Draw(mask); d.rounded_rectangle([0,0,bg.width-1,bg.height-1],radius=radius+bw,fill=255)
            cut=Image.new("RGBA",bg.size,(0,0,0,0)); cut.paste(bg,(0,0),mask); bg=cut
        panel.alpha_composite(bg,(pad,pad))
    _paste_with_round(panel,ph,ox,oy,radius)
    return panel

def compose_background_scene(photo,bg_path,W,H,layout="center",scale=0.66,frame=None):
    bg=_cover(Image.open(bg_path),W,H).convert("RGBA")
    overlay=Image.new("RGBA",(W,H),(0,0,0,0))
    frame=frame or {}
    box=_photo_box(W,H,layout,scale)
    ph=_fit_in_box(photo,box).convert("RGBA")
    x1,y1,x2,y2=box
    x=x1+(x2-x1-ph.width)//2; y=y1+(y2-y1-ph.height)//2
    border=bool(frame.get("border",True)); shadow=bool(frame.get("shadow",True))
    radius=int(frame.get("radius",0)); bw=int(frame.get("border_width",max(6,H*0.008)))
    if shadow:
        sh=Image.new("RGBA",(ph.width+60,ph.height+60),(0,0,0,0))
        sd=ImageDraw.Draw(sh); sd.rounded_rectangle([30,30,30+ph.width,30+ph.height],radius=radius+6,fill=(0,0,0,150))
        sh=sh.filter(ImageFilter.GaussianBlur(max(8,int(H*0.012))))
        overlay.alpha_composite(sh,(x-30,y-20))
    if border:
        panel=Image.new("RGBA",(ph.width+bw*2,ph.height+bw*2),(255,255,255,255))
        if radius>0:
            pm=Image.new("L",panel.size,0)
            pd=ImageDraw.Draw(pm); pd.rounded_rectangle([0,0,panel.width-1,panel.height-1],radius=radius+bw,fill=255)
            cut=Image.new("RGBA",panel.size,(0,0,0,0)); cut.paste(panel,(0,0),pm); panel=cut
        overlay.alpha_composite(panel,(x-bw,y-bw))
    _paste_with_round(overlay,ph,x,y,radius)
    return Image.alpha_composite(bg,overlay).convert("RGB")

def make_bokeh(n,seed,w,h):
    rng=np.random.default_rng(seed);P=[]
    for _ in range(n):P.append(dict(x=rng.uniform(-.05,1.05),y=rng.uniform(0,1.1),r=rng.uniform(.012,.05)*h,ph=rng.uniform(0,6.28),base=rng.uniform(.06,.2)))
    return P
def bokeh_layer(P,w,h,t=3.0):
    L=Image.new("L",(w,h),0);d=ImageDraw.Draw(L)
    for p in P:
        cx,cy=(p["x"]+0.015*math.sin(p["ph"]))*w,(p["y"])%1.1*h;op=p["base"]
        for s in (1.0,0.66,0.36):
            a=int(255*op*(1-s)*0.8);rr=p["r"]*s
            if a>0:d.ellipse([cx-rr,cy-rr,cx+rr,cy+rr],fill=a)
    L=L.filter(ImageFilter.GaussianBlur(max(1,int(h*0.012))))
    col=Image.new("RGB",(w,h),(255,206,140));out=Image.new("RGBA",(w,h),(0,0,0,0));out.paste(col,(0,0),L);return out

def _tsize(txt,fnt,tr=0):
    if not txt:return(0,0)
    asc,desc=fnt.getmetrics();tmp=ImageDraw.Draw(Image.new("L",(10,10)));w=0
    for ch in txt:bb=tmp.textbbox((0,0),ch,font=fnt);w+=(bb[2]-bb[0])+tr
    return(max(0,w-tr),asc+desc)
def _tracked(layer,xy,txt,fnt,fill,tr=0,anchor="mm"):
    d=ImageDraw.Draw(layer);tw,th=_tsize(txt,fnt,tr);x,y=xy
    if anchor[0]=="m":x-=tw/2
    elif anchor[0]=="r":x-=tw
    if anchor[1]=="m":y-=th/2
    elif anchor[1]=="b":y-=th
    cx=x
    for ch in txt:bb=d.textbbox((0,0),ch,font=fnt);d.text((cx-bb[0],y),ch,font=fnt,fill=fill);cx+=(bb[2]-bb[0])+tr
def crisp(w,h,draws):
    L=Image.new("RGBA",(w,h),(0,0,0,0))
    for xy,txt,fnt,fill,tr,an in draws:_tracked(L,xy,txt,fnt,tuple(fill)+(255,),tr,an)
    return L
def glow(w,h,draws,fx,rad,op=0.9):
    base=crisp(w,h,draws);al=base.split()[3]
    g=Image.new("RGBA",(w,h),tuple(fx)+(0,));g.putalpha(al.filter(ImageFilter.GaussianBlur(rad)).point(lambda a:int(a*op)))
    out=Image.new("RGBA",(w,h),(0,0,0,0));out=Image.alpha_composite(out,g);out=Image.alpha_composite(out,g)
    return Image.alpha_composite(out,base)

def build_title_card(cfg,st,W,H,path):
    S=H/1080.0;C=st["col"];F=st["fonts"];cy=H*0.47
    if st["card_bg"]=="dark":
        b=warm_gradient(W,H).convert("RGBA");b=Image.alpha_composite(b,bokeh_layer(make_bokeh(22,11,W,H),W,H))
        draws=[((W/2,cy-300*S),cfg.get("kicker",""),font(F["kicker"],34*S),C["kicker"],int(16*S),"mm"),
               ((W/2,cy),cfg.get("title",""),font(F["title"],300*S),C["text"],0,"mm")]
        if cfg.get("date"):draws.append(((W/2,cy+250*S),cfg["date"],font(F["sub"],52*S),C["sub"],int(10*S),"mm"))
        b=Image.alpha_composite(b,glow(W,H,draws,C["fx"],int(28*S),0.9))
        d=ImageDraw.Draw(b);lw=int(150*S);d.line([(W/2-lw,cy+160*S),(W/2+lw,cy+160*S)],fill=tuple(C["accent"])+(230,),width=max(2,int(3*S)))
    else:
        b=light_bg(W,H,C["accent"]).convert("RGBA")
        b=Image.alpha_composite(b,crisp(W,H,[((W/2,cy-195*S),cfg.get("kicker",""),font(F["kicker"],38*S),C["kicker"],int(26*S),"mm"),
          ((W/2,cy),cfg.get("title",""),font(F["title"],210*S),C["text"],0,"mm"),
          ((W/2,cy+200*S),cfg.get("date",""),font(F["sub"],30*S),C["sub"],int(14*S),"mm")]))
        d=ImageDraw.Draw(b);lw=int(130*S);d.line([(W/2-lw,cy+140*S),(W/2+lw,cy+140*S)],fill=tuple(C["accent"])+(255,),width=max(2,int(4*S)))
    b.convert("RGB").save(path)
def build_outro_card(cfg,st,W,H,path):
    S=H/1080.0;C=st["col"];F=st["fonts"];cy=H*0.46;ot=cfg.get("outro_title") or cfg.get("title","")
    if st["card_bg"]=="dark":
        b=warm_gradient(W,H).convert("RGBA");b=Image.alpha_composite(b,bokeh_layer(make_bokeh(20,21,W,H),W,H,2.0))
        draws=[((W/2,cy-250*S),cfg.get("outro_kicker",""),font(F["kicker"],32*S),C["kicker"],int(16*S),"mm"),
               ((W/2,cy),ot,font(F["title"],290*S),C["text"],0,"mm")]
        b=Image.alpha_composite(b,glow(W,H,draws,C["fx"],int(28*S),0.9))
        d=ImageDraw.Draw(b);lw=int(150*S);d.line([(W/2-lw,cy+155*S),(W/2+lw,cy+155*S)],fill=tuple(C["accent"])+(230,),width=max(2,int(3*S)))
        if cfg.get("subtitle"):b=Image.alpha_composite(b,glow(W,H,[((W/2,cy+215*S),cfg["subtitle"],font(F["sub"],42*S),C["sub"],int(2*S),"mm")],C["fx"],int(8*S),0.5))
    else:
        b=light_bg(W,H,C["accent"]).convert("RGBA")
        b=Image.alpha_composite(b,crisp(W,H,[((W/2,cy-180*S),cfg.get("outro_kicker",""),font(F["kicker"],32*S),C["kicker"],int(22*S),"mm"),
          ((W/2,cy),ot,font(F["title"],200*S),C["text"],0,"mm"),
          ((W/2,cy+190*S),cfg.get("subtitle",""),font(F["sub"],30*S),C["sub"],int(14*S),"mm")]))
        d=ImageDraw.Draw(b);lw=int(130*S);d.line([(W/2-lw,cy+132*S),(W/2+lw,cy+132*S)],fill=tuple(C["accent"])+(255,),width=max(2,int(4*S)))
    b.convert("RGB").save(path)
def build_caption(text,st,W,H,path):
    S=H/1080.0;C=st["col"];F=st["fonts"]
    if st["caption"]=="glow":
        img=glow(W,H,[((W/2,H*0.815),text,font(F["cap"],104*S),C["text"],0,"mm")],C["fx"],int(22*S),0.85)
    else:
        y=H*0.85;img=Image.new("RGBA",(W,H),(0,0,0,0))
        base=crisp(W,H,[((W/2,y),text,font(F["cap"],62*S),C["text"],int(2*S),"mm")]);al=base.split()[3]
        halo=Image.new("RGBA",(W,H),(255,255,255,0));halo.putalpha(al.filter(ImageFilter.GaussianBlur(int(18*S))).point(lambda a:int(a*0.95)))
        img=Image.alpha_composite(img,halo);img=Image.alpha_composite(img,halo);img=Image.alpha_composite(img,base)
        d=ImageDraw.Draw(img);lw=int(55*S);d.line([(W/2-lw,y-68*S),(W/2+lw,y-68*S)],fill=tuple(C["accent"])+(255,),width=max(2,int(4*S)))
    img.save(path)

# ---------- ffmpeg ----------
FFMPEG=None
def find_ffmpeg():
    global FFMPEG
    if FFMPEG and os.path.isfile(FFMPEG): return FFMPEG
    b=runtime_paths.find_bundled_ffmpeg()
    if b: FFMPEG=b; return b
    c=shutil.which("ffmpeg")
    if c: FFMPEG=c; return c
    for x in ["C:/ffmpeg/bin/ffmpeg.exe","C:/Program Files/ffmpeg/bin/ffmpeg.exe",
              os.path.expanduser("~/ffmpeg/bin/ffmpeg.exe"), os.path.join(HERE,"ffmpeg.exe"),
              os.path.join(HERE,"ffmpeg","bin","ffmpeg.exe")]:
        if os.path.isfile(x): FFMPEG=x; return x
    return None
def set_ffmpeg(path):
    global FFMPEG
    if path and os.path.isfile(path): FFMPEG=path; return True
    return False
MSG_NOFF="ffmpeg topilmadi. Uni PATH ga qo'shing (winget install Gyan.FFmpeg) yoki ffmpeg.exe manzilini bering."
def _ff():
    f=find_ffmpeg()
    if not f: raise RuntimeError(MSG_NOFF)
    return f
def _check_cancel(cancel_event=None):
    if cancel_event is not None and cancel_event.is_set():
        raise CancelledError("Bekor qilindi")


def _run(cmd, cancel_event=None):
    _check_cancel(cancel_event)
    if cmd and cmd[0]=="ffmpeg": cmd=[_ff()]+list(cmd[1:])
    proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    while proc.poll() is None:
        if cancel_event is not None and cancel_event.is_set():
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            raise CancelledError("Bekor qilindi")
        time.sleep(0.12)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode,cmd)

# ---------- scene / clip ----------
def _kb(i):
    seq=[("in",1,-0.2),("out",-1,0.2),("in",0,-1),("out",1,0.2),("in",-1,0),("out",0,-0.3),
         ("in",1,0.3),("out",-1,0),("in",0,-1),("out",1,0.3),("in",-1,0)]
    return seq[i%len(seq)]
def _vf(dur,zdir,dx,dy,W,H,fps,vig,amt,grain,motion=None,i=0,motion_settings=None):
    N=int(dur*fps)
    ax=0.95*dx; ay=0.7*dy; half=N/2; sc=max(3840,int(W*1.5))
    if (motion and motion!="auto") or motion_settings:
        spec=_motion_spec(motion or "auto",i,amt,W,H,motion_settings)
        ss=max(1.0,float(spec["start_scale"])); es=max(1.0,float(spec["end_scale"]))
        prog=_motion_progress_expr(f"on/{max(1,N-1)}", spec.get("speed",1.0))
        z=f"'{ss:.4f}+({es-ss:.6f})*{prog}'"
        sdx=float(spec["start_dx"])*sc/max(1,W); edx=float(spec["end_dx"])*sc/max(1,W)
        sdy=float(spec["start_dy"])*sc/max(1,H); edy=float(spec["end_dy"])*sc/max(1,H)
        x=f"'iw/2-(iw/zoom/2)+({sdx:.3f}+({edx-sdx:.3f})*{prog})'"
        y=f"'ih/2-(ih/zoom/2)+({sdy:.3f}+({edy-sdy:.3f})*{prog})'"
    else:
        z=f"'min(1.02+{amt/N:.6f}*on,{1.02+amt:.3f})'" if zdir=="in" else f"'max({1.02+amt:.3f}-{amt/N:.6f}*on,1.02)'"
        x=f"'iw/2-(iw/zoom/2)+{ax:.3f}*(on-{half:.1f})'"; y=f"'ih/2-(ih/zoom/2)+{ay:.3f}*(on-{half:.1f})'"
    base=f"scale={sc}:-1,zoompan=z={z}:d={N}:x={x}:y={y}:s={W}x{H}:fps={fps}"
    if vig: base+=",vignette=PI/5.0"
    if grain: base+=",noise=alls=6:allf=t"
    return base,N
def render_scene(gp,cap_png,dur,i,W,H,fps,vig,amt,grain,bloom,out,cancel_event=None,motion=None,motion_settings=None):
    zdir,dx,dy=_kb(i); base,N=_vf(dur,zdir,dx,dy,W,H,fps,vig,amt,grain,motion,i,motion_settings)
    parts=[f"[0:v]{base}[v0]"]; last="v0"
    if bloom:
        s=max(6,int(H*0.014))
        parts.append(f"[v0]split[b0][b1];[b1]gblur=sigma={s}[b2];[b0][b2]blend=all_mode=screen:all_opacity=0.22[v1]"); last="v1"
    inp=["-i",gp]
    if cap_png:
        inp+=["-loop","1","-t",str(dur),"-i",cap_png]
        fade_out=max(0.0,dur-1.0)
        parts.append(f"[1:v]fade=t=in:st=0.5:d=0.6:alpha=1,fade=t=out:st={fade_out:.2f}:d=0.6:alpha=1[c]")
        parts.append(f"[{last}][c]overlay=0:0[o]"); last="o"
    fc=";".join(parts)
    _run(["ffmpeg","-y",*inp,"-filter_complex",fc,"-map",f"[{last}]","-frames:v",str(N),"-r",str(fps),
          "-c:v","libx264","-crf","12","-preset","veryfast","-pix_fmt","yuv420p",out], cancel_event)

def render_static_scene(gp,cap_png,dur,i,W,H,fps,grain,bloom,out,cancel_event=None):
    N=int(dur*fps)
    parts=[f"[0:v]scale={W}:{H},fps={fps}"]
    if grain: parts[0]+=",noise=alls=4:allf=t"
    parts[0]+="[v0]"
    last="v0"; inp=["-loop","1","-t",str(dur),"-i",gp]
    if bloom:
        s=max(6,int(H*0.014))
        parts.append(f"[v0]split[b0][b1];[b1]gblur=sigma={s}[b2];[b0][b2]blend=all_mode=screen:all_opacity=0.18[v1]")
        last="v1"
    if cap_png:
        inp+=["-loop","1","-t",str(dur),"-i",cap_png]
        fade_out=max(0.0,dur-1.0)
        parts.append(f"[1:v]fade=t=in:st=0.5:d=0.6:alpha=1,fade=t=out:st={fade_out:.2f}:d=0.6:alpha=1[c]")
        parts.append(f"[{last}][c]overlay=0:0[o]"); last="o"
    _run(["ffmpeg","-y",*inp,"-filter_complex",";".join(parts),"-map",f"[{last}]","-frames:v",str(N),"-r",str(fps),
          "-c:v","libx264","-crf","12","-preset","veryfast","-pix_fmt","yuv420p",out], cancel_event)

def render_background_motion_scene(gp,bg_path,cap_png,dur,i,W,H,fps,grain,bloom,out,layout,scale,frame,motion=None,cancel_event=None,motion_settings=None):
    bg=_cover(Image.open(bg_path),W,H).convert("RGB")
    bg_tmp=out+".bg.jpg"; panel_tmp=out+".panel.png"
    bg.save(bg_tmp,quality=94)
    panel=_photo_panel(Image.open(gp),_photo_box(W,H,layout,scale),frame)
    panel.save(panel_tmp)
    N=int(dur*fps); spec=_motion_spec(motion or "auto",i,0.15,W,H,motion_settings)
    ss,es=float(spec["start_scale"]),float(spec["end_scale"])
    sdx,edx=float(spec["start_dx"]),float(spec["end_dx"])
    sdy,edy=float(spec["start_dy"]),float(spec["end_dy"])
    cx,cy=W/2,H/2
    t=f"min(t\\,{dur:.4f})/{max(0.001,dur):.4f}"
    parts=[f"[0:v]scale={W}:{H},setsar=1,fps={fps}"]
    if grain: parts[0]+=",noise=alls=4:allf=t"
    parts[0]+="[bg0]"
    last="bg0"; inp=["-loop","1","-t",str(dur),"-i",bg_tmp,"-loop","1","-t",str(dur),"-i",panel_tmp]
    if bloom:
        s=max(6,int(H*0.014))
        parts.append(f"[bg0]split[b0][b1];[b1]gblur=sigma={s}[b2];[b0][b2]blend=all_mode=screen:all_opacity=0.18[bg1]")
        last="bg1"
    progress=_motion_progress_expr(t, spec.get("speed",1.0))
    scale_expr=f"{ss:.5f}+({es-ss:.5f})*{progress}"
    x_expr=f"{cx:.3f}-overlay_w/2+({sdx:.3f}+({edx-sdx:.3f})*{progress})"
    y_expr=f"{cy:.3f}-overlay_h/2+({sdy:.3f}+({edy-sdy:.3f})*{progress})"
    parts.append(f"[1:v]format=rgba,scale=w='iw*({scale_expr})':h='ih*({scale_expr})':eval=frame[p]")
    parts.append(f"[{last}][p]overlay=x='{x_expr}':y='{y_expr}':eval=frame[o0]")
    last="o0"
    if cap_png:
        inp+=["-loop","1","-t",str(dur),"-i",cap_png]
        fade_out=max(0.0,dur-1.0)
        parts.append(f"[2:v]fade=t=in:st=0.5:d=0.6:alpha=1,fade=t=out:st={fade_out:.2f}:d=0.6:alpha=1[c]")
        parts.append(f"[{last}][c]overlay=0:0[o]"); last="o"
    _run(["ffmpeg","-y",*inp,"-filter_complex",";".join(parts),"-map",f"[{last}]","-frames:v",str(N),"-r",str(fps),
          "-c:v","libx264","-crf","12","-preset","veryfast","-pix_fmt","yuv420p",out], cancel_event)
def render_card_clip(card,dur,W,H,fps,fade_out,bg,out,cancel_event=None):
    N=int(dur*fps); sc=max(3840,int(W*1.5)); sch=int(sc*H/W); col="white" if bg=="light" else "black"
    vf=(f"scale={sc}:{sch},zoompan=z='min(1.001+0.0004*on,1.05)':d={N}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={fps},fade=t=in:st=0:d=0.6:color={col}")
    if fade_out: vf+=f",fade=t=out:st={max(0.0,dur-1.0):.2f}:d=1.0:color={col}"
    _run(["ffmpeg","-y","-i",card,"-vf",vf,"-frames:v",str(N),"-r",str(fps),"-c:v","libx264","-crf","12","-preset","veryfast","-pix_fmt","yuv420p",out], cancel_event)
def _trans_list(ttype,n):
    M={"fade":["fade"],"fadeblack":["fadeblack"],"fadewhite":["fadewhite"],
       "slide":["slideleft","slideright"],"push":["smoothleft","smoothright"],
       "wipe":["wipeleft","wiperight"],"circle":["circleopen","circleclose"],
       "radial":["radial"],"pixelize":["pixelize"],"blur":["hblur"],
       "dissolve":["dissolve"],"diagonal":["diagtl","diagbr"]}
    seq=M.get(ttype,["fade"]); tr=[seq[i%len(seq)] for i in range(n)]
    if tr: tr[0]="fade"; tr[-1]="fade"
    return tr
def stitch(clips,durs,D,ttype,music,crf,preset,fps,out,cancel_event=None):
    n=len(clips); cum=0.0; off=[]
    if n <= 0:
        raise RuntimeError("Video uchun clip topilmadi.")
    if n == 1:
        _run(["ffmpeg","-y","-i",clips[0],"-i",music,"-map","0:v","-map","1:a",
              "-c:v","libx264","-pix_fmt","yuv420p","-r",str(fps),"-crf",str(crf),"-preset",preset,
              "-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",out], cancel_event)
        return
    for k in range(n-1): cum+=durs[k]; off.append(round(cum-(k+1)*D,3))
    tr=_trans_list(ttype,n-1)
    inp=[]
    for c in clips: inp+=["-i",c]
    inp+=["-i",music]
    parts=[]; prev="0:v"
    for k in range(1,n):
        lbl=f"x{k}"; parts.append(f"[{prev}][{k}:v]xfade=transition={tr[k-1]}:duration={D}:offset={off[k-1]}[{lbl}]"); prev=lbl
    _run(["ffmpeg","-y",*inp,"-filter_complex",";".join(parts),"-map",f"[{prev}]","-map",f"{n}:a",
          "-c:v","libx264","-pix_fmt","yuv420p","-r",str(fps),"-crf",str(crf),"-preset",preset,
          "-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",out], cancel_event)

def build_video(config, progress=lambda p,m: None, cancel_event=None):
    import music as MU
    _check_cancel(cancel_event)
    if find_ffmpeg() is None: raise RuntimeError(MSG_NOFF)
    st=apply_font_preset(STYLES[config["style"]], config.get("font_preset", "default"))
    W,H=RES.get(config.get("resolution","1440p (2K)"),(2560,1440)); fps=int(config.get("fps",30))
    D=float(config.get("transition_dur",0.7)); PDUR=float(config.get("photo_duration",4.5))
    TDUR=float(config.get("title_duration",6.0)); ODUR=float(config.get("outro_duration",4.5))
    crf=int(config.get("crf",17)); preset=config.get("preset","fast")
    gmode=config.get("grade","auto"); gmode=st["grade"] if gmode in ("auto",None,"") else gmode
    amt=KB_LEVELS.get(config.get("kb_intensity","normal"),0.15)
    grain=bool(config.get("grain",False)); bloom=bool(config.get("bloom",False))
    vig=config.get("vignette","auto"); vig=st["vignette"] if vig in ("auto",None,"") else bool(vig)
    ttype=config.get("transition_type","auto"); ttype=st["transition"] if ttype in ("auto",None,"") else ttype
    photos=config["photos"]; caps=config.get("captions",{}); out=config["output"]
    text_flags=resolve_text_flags(config)
    show_title=text_flags["show_title_card"]
    show_outro=text_flags["show_outro_card"]
    show_captions=text_flags["show_captions"]
    if not show_captions:
        caps={}
    enhanced=config.get("enhanced_photos") or {}
    pdurs=resolve_photo_durations(len(photos), PDUR, config.get("photo_durations"))
    pmotions=list(config.get("photo_motions") or [])
    pmotion_settings=list(config.get("photo_motion_settings") or [])
    bg_path=config.get("background_path") or ""
    has_bg=bool(bg_path and os.path.isfile(bg_path))
    playout=config.get("photo_layout","center")
    pscale=float(config.get("photo_scale",0.66))
    pframe=config.get("photo_frame") or {}
    def _pdur(idx):
        try:
            return pdurs[idx]
        except Exception:
            return PDUR
    def _motion(idx):
        try:
            return normalize_motion_preset(pmotions[idx])
        except Exception:
            return "auto"
    def _motion_settings(idx):
        try:
            return normalize_motion_settings(pmotion_settings[idx])
        except Exception:
            return None
    work=tempfile.mkdtemp(prefix="pvs_")
    progress(3,"Rasmlar tayyorlanmoqda...")
    graded=[]
    for i,p in enumerate(photos):
        _check_cancel(cancel_event)
        ep=enhanced.get(p) if isinstance(enhanced,dict) else None
        src=ep if ep and os.path.isfile(ep) else p
        g=grade(load_photo(src),gmode)
        if not has_bg:
            mx=max(3840,int(W*1.5)); s=mx/max(g.size)
            if s<1: g=g.resize((int(g.size[0]*s),int(g.size[1]*s)),Image.LANCZOS)
        gp=os.path.join(work,f"g{i}.png"); g.save(gp); graded.append(gp)
        progress(3+int(12*(i+1)/len(photos)),f"Rang: {i+1}/{len(photos)}")
    cap_png={}
    for k,txt in caps.items():
        _check_cancel(cancel_event)
        if txt: cp=os.path.join(work,f"c{int(k)}.png"); build_caption(txt,st,W,H,cp); cap_png[int(k)]=cp
    progress(18,"Kartalar...")
    _check_cancel(cancel_event)
    tclip=oclip=None
    if show_title:
        tc=os.path.join(work,"tc.png"); build_title_card(config,st,W,H,tc)
        tclip=os.path.join(work,"title.mkv"); render_card_clip(tc,TDUR,W,H,fps,False,st["card_bg"],tclip,cancel_event)
    if show_outro:
        oc=os.path.join(work,"oc.png"); build_outro_card(config,st,W,H,oc)
        oclip=os.path.join(work,"outro.mkv"); render_card_clip(oc,ODUR,W,H,fps,True,st["card_bg"],oclip,cancel_event)
    progress(30,"Sahnalar...")
    sclips=[]
    for i,gp in enumerate(graded):
        _check_cancel(cancel_event)
        dur_i=_pdur(i)
        sc=os.path.join(work,f"s{i}.mkv")
        if has_bg:
            render_background_motion_scene(gp,bg_path,cap_png.get(i+1),dur_i,i,W,H,fps,grain,bloom,sc,playout,pscale,pframe,_motion(i),cancel_event,_motion_settings(i))
        else:
            render_scene(gp,cap_png.get(i+1),dur_i,i,W,H,fps,vig,amt,grain,bloom,sc,cancel_event,_motion(i),_motion_settings(i))
        sclips.append(sc)
        progress(30+int(48*(i+1)/len(graded)),f"Sahna: {i+1}/{len(graded)}")
    photo_durs=[_pdur(i) for i in range(len(sclips))]
    clips=[]; durs=[]
    if tclip:
        clips.append(tclip); durs.append(TDUR)
    clips.extend(sclips); durs.extend(photo_durs)
    if oclip:
        clips.append(oclip); durs.append(ODUR)
    total=round(sum(durs)-(len(durs)-1)*D,3)
    progress(82,"Musiqa...")
    _check_cancel(cancel_event)
    if config.get("music","auto")=="auto":
        mp=os.path.join(work,"m.wav"); MU.generate(st["music"],round(total+0.3,2),mp)
    else: mp=config["music"]
    progress(90,"Video yig'ilmoqda...")
    stitch(clips,durs,D,ttype,mp,crf,preset,fps,out,cancel_event)
    progress(100,"Tayyor!")
    return out
