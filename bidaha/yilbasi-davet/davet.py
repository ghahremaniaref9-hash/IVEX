"""Bidaha - yılbaşı ve 10. yıl davet Reels'i (1080x1920, 30 fps, yaklaşık 17,6 sn).

Kullanım:  python3 davet.py [ayarlar.json]
Kurgu (rezervasyona çeviren bir davet; telefon fikri baştan sona taşınır):
  0,0 -  4,0  Müşterinin klibi: kırmızı kadife duvar, "Ho Ho Ho", telefon çalar ve açılır.
  4,0 -  7,0  Logo: BİDAHA harfleri, logodaki gibi ampullerle tek tek yanar; "Yemekli, müzikli eğlence".
  7,0 -  9,7  "Bu yılbaşı çifte kutlama!" ve ampullü dev "10." - "YILIMIZA GİRİYORUZ".
  9,7 - 12,4  Sayaç 2026'dan 2027'ye döner, konfeti; "Yeni yıla Bidaha'da gir!", "31 Aralık · Yılbaşı gecesi".
 12,4 - 17,6  Ampul çerçeveli rezervasyon kartı: iki telefon numarası ve adres.
Arka plan kliple aynı kırmızı kadife; yazılar Reels arayüzünün üst 250 ve alt 340 piksellik şeritlerinin dışında.
Müzik ve efektler ivex-icerik/uretim/ses.py yapı taşlarıyla kodla üretilir (telifsiz); klibin kendi sesi korunur.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FONTS = os.path.join(REPO, "ivex-icerik", "uretim", "fonts")
sys.path.insert(0, os.path.join(REPO, "ivex-icerik", "uretim"))
import ses  # noqa: E402

import imageio_ffmpeg  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
T_CLIP, T_LOGO, T_TEN, T_YEAR, T_CTA, DUR = 0.0, 4.0, 7.0, 9.7, 12.4, 17.6
ROLL_AT = 10.25  # the last digit of the year starts turning
POP_AT = 10.7  # confetti
RNG = np.random.default_rng(10)

GOLD = (1.0, 0.80, 0.36)
CREAM = (255, 243, 214)
GOLD8 = (246, 196, 92)


def tr_upper(text):
    return str(text).replace("i", "İ").replace("ı", "I").upper()


def repo(p):
    return os.path.join(REPO, p)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_back(x, s=1.7):
    x = min(max(x, 0.0), 1.0)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def ramp(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


def window(t, a, b, fade=0.25):
    """1 inside [a, b], fading in and out over `fade` seconds."""
    return min(ramp(t, a, a + fade), 1 - ramp(t, b - fade, b))


# ---------------------------------------------------------------- layers

class Layer:
    """An RGBA image kept as premultiplied float arrays, with an optional additive glow."""

    def __init__(self, img, glow=None, glow_color=GOLD, glow_strength=1.0):
        self.pad = int(glow * 3) if glow else 0
        if glow:
            pad = self.pad
            big = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
            big.paste(img, (pad, pad))
            img = big
        self.img = img
        a = np.asarray(img, np.float32) / 255.0
        self.alpha = a[..., 3:4]
        self.rgb = a[..., :3] * self.alpha
        self.glow = None
        if glow:
            g = img.getchannel("A").filter(ImageFilter.GaussianBlur(glow))
            ga = np.asarray(g, np.float32)[..., None] / 255.0
            self.glow = ga * np.array(glow_color, np.float32) * glow_strength
        self.w, self.h = img.size

    def scaled(self, s):
        if abs(s - 1) < 1e-3:
            return self
        w, h = max(1, round(self.w * s)), max(1, round(self.h * s))
        out = Layer.__new__(Layer)
        out.img = None
        out.w, out.h = w, h
        a = np.asarray(self.img.resize((w, h), Image.BILINEAR), np.float32) / 255.0
        out.alpha = a[..., 3:4]
        out.rgb = a[..., :3] * out.alpha
        out.glow = None
        if self.glow is not None:
            g = Image.fromarray(np.clip(self.glow * 255, 0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
            out.glow = np.asarray(g, np.float32) / 255.0
        return out

    def draw(self, frame, cx, cy, opacity=1.0, scale=1.0, glow=1.0):
        if opacity <= 0.003:
            return
        L = self.scaled(scale)
        x0, y0 = round(cx - L.w / 2), round(cy - L.h / 2)
        fx0, fy0, fx1, fy1 = max(x0, 0), max(y0, 0), min(x0 + L.w, W), min(y0 + L.h, H)
        if fx1 <= fx0 or fy1 <= fy0:
            return
        sx, sy = fx0 - x0, fy0 - y0
        reg = frame[fy0:fy1, fx0:fx1]
        a = L.alpha[sy:sy + fy1 - fy0, sx:sx + fx1 - fx0] * opacity
        reg *= 1 - a
        reg += L.rgb[sy:sy + fy1 - fy0, sx:sx + fx1 - fx0] * opacity
        if L.glow is not None and glow > 0:
            reg += L.glow[sy:sy + fy1 - fy0, sx:sx + fx1 - fx0] * glow * opacity


def text_img(text, fnt, fill, track=0.0, stroke=0, stroke_fill=None, pad=40, shadow=True):
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    widths = [d0.textlength(c, font=fnt) for c in text]
    tw = sum(widths) + track * (len(text) - 1)
    asc, desc = fnt.getmetrics()
    img = Image.new("RGBA", (round(tw) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        x = pad
        for c, w in zip(text, widths):
            ds.text((x, pad + 6), c, font=fnt, fill=(20, 0, 4, 200), stroke_width=stroke)
            x += w + track
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    x = pad
    for c, w in zip(text, widths):
        d.text((x, pad), c, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        x += w + track
    return img.crop(img.getbbox())


def gold_text(text, fnt, track=0.0, pad=40):
    """Text filled with a warm metallic gradient and a thin dark rim."""
    mask = text_img(text, fnt, (255, 255, 255, 255), track, pad=pad, shadow=False)
    w, h = mask.size
    yy = np.linspace(0, 1, h)[:, None]
    grad = np.zeros((h, w, 3), np.float32)
    top, mid, bot = np.array([255, 236, 170]), np.array([246, 196, 92]), np.array([196, 120, 40])
    g = np.where(yy < 0.5, top + (mid - top) * (yy / 0.5), mid + (bot - mid) * ((yy - 0.5) / 0.5))
    grad[:] = g[:, None, :] if g.ndim == 2 else g
    a = np.asarray(mask.getchannel("A"), np.float32)
    img = Image.fromarray(np.dstack([grad, a]).astype(np.uint8), "RGBA")
    rim = mask.getchannel("A").filter(ImageFilter.MaxFilter(5))
    out = Image.new("RGBA", (w, h), (70, 28, 4, 0))
    out.putalpha(rim)
    m = 60
    sh = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (w, h), (20, 0, 4, 0))
    shadow.putalpha(rim.point(lambda v: v * 0.75))
    sh.alpha_composite(shadow, (m, m + 12))
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    sh.alpha_composite(out, (m, m))
    sh.alpha_composite(img, (m, m))
    return sh


# ---------------------------------------------------------------- backdrop, sparkles, bulbs

def velvet():
    """Red velvet curtain like the client's clip: soft vertical folds, fine pile, dark edges."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    lo = RNG.standard_normal((12, 7)).astype(np.float32)
    lo = np.asarray(Image.fromarray(lo).resize((W, H), Image.BICUBIC), np.float32)
    folds = 0.5 + 0.5 * np.sin(xx / 150 * 2 * np.pi + lo * 1.4 + yy / 900)
    folds = folds ** 1.6
    grain = np.asarray(Image.fromarray(RNG.standard_normal((H // 2, W // 2)).astype(np.float32)).resize((W, H)),
                       np.float32)
    shade = 0.42 + 0.48 * folds + 0.035 * grain
    r = np.hypot((xx - W / 2) / W, (yy - H * 0.42) / H)
    vig = np.clip(1.15 - r * 1.25, 0.25, 1.0)
    base = np.array([0.43, 0.035, 0.07], np.float32)
    return (shade * vig)[..., None] * base


def glow_sprite(size, color, sigma):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) - size / 2
    r2 = xx ** 2 + yy ** 2
    g = np.exp(-r2 / (2 * sigma ** 2))
    return g[..., None] * np.array(color, np.float32)


def star_sprite(size):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) - size / 2
    core = np.exp(-(xx ** 2 + yy ** 2) / (2 * (size * 0.06) ** 2))
    rays = np.exp(-np.abs(xx) / (size * 0.018)) * np.exp(-np.abs(yy) / (size * 0.2)) + \
        np.exp(-np.abs(yy) / (size * 0.018)) * np.exp(-np.abs(xx) / (size * 0.2))
    halo = np.exp(-(xx ** 2 + yy ** 2) / (2 * (size * 0.22) ** 2)) * 0.35
    g = np.clip(core + 0.6 * rays + halo, 0, 1.5)
    return g[..., None] * np.array([1.0, 0.86, 0.55], np.float32)


def add_sprite(frame, spr, cx, cy, gain):
    if gain <= 0.003:
        return
    s = spr.shape[0]
    x0, y0 = int(cx - s / 2), int(cy - s / 2)
    fx0, fy0, fx1, fy1 = max(x0, 0), max(y0, 0), min(x0 + s, W), min(y0 + s, H)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    frame[fy0:fy1, fx0:fx1] += spr[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * gain


class Sparkles:
    def __init__(self, n=60):
        self.p = [dict(x=RNG.uniform(0, W), y=RNG.uniform(0, H), v=RNG.uniform(18, 70), sway=RNG.uniform(6, 22),
                       ph=RNG.uniform(0, 6.3), f=RNG.uniform(0.6, 1.8), s=RNG.choice([0, 1, 2])) for _ in range(n)]
        self.sprites = [star_sprite(40), star_sprite(64), glow_sprite(24, (1.0, 0.78, 0.4), 4)]

    def draw(self, frame, t, gain=1.0):
        for q in self.p:
            y = (q["y"] - q["v"] * t) % (H + 80) - 40
            x = q["x"] + q["sway"] * math.sin(t * 0.8 + q["ph"])
            tw = max(0.0, math.sin(t * q["f"] * 2 * math.pi + q["ph"])) ** 3
            add_sprite(frame, self.sprites[q["s"]], x, y, gain * (0.25 + 0.75 * tw) * 0.55)


def bulb_sprites(r):
    size = int(r * 2 + 6)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) - size / 2 + 0.5
    d = np.hypot(xx, yy)
    disk = np.clip(r - d + 0.5, 0, 1)[..., None]
    hl = np.exp(-((xx + r * 0.3) ** 2 + (yy + r * 0.35) ** 2) / (2 * (r * 0.35) ** 2))[..., None]
    on = disk * (np.array([1.0, 0.95, 0.74], np.float32) + 0.25 * hl)
    off = disk * (np.array([0.42, 0.28, 0.14], np.float32) + 0.12 * hl)
    return disk, on, off, glow_sprite(int(r * 7), (1.0, 0.74, 0.32), r * 1.2)


class Bulbs:
    """Light bulbs at fixed points; each frame gives every bulb a brightness 0..1."""

    def __init__(self, points, r):
        self.pts = points
        self.disk, self.on, self.off, self.glow = bulb_sprites(r)

    def draw(self, frame, ox, oy, levels, opacity=1.0):
        s = self.disk.shape[0]
        for (x, y), b in zip(self.pts, levels):
            cx, cy = int(ox + x - s / 2), int(oy + y - s / 2)
            if cx < 0 or cy < 0 or cx + s > W or cy + s > H:
                continue
            reg = frame[cy:cy + s, cx:cx + s]
            a = self.disk * opacity
            reg *= 1 - a
            reg += (self.off * (1 - b) + self.on * b) * opacity
            add_sprite(frame, self.glow, ox + x, oy + y, 0.55 * b * opacity)


def marquee(text, size, spacing, r):
    """Gold sign letters with light bulbs set into the strokes (like the logo)."""
    fnt = font("Anton_400Regular.ttf", size)
    img = gold_text(text, fnt, track=size * 0.04)
    a = np.asarray(img.getchannel("A")) > 200
    h, w = a.shape
    pts = []
    for y in np.arange(spacing / 2, h, spacing):
        for x in np.arange(spacing / 2, w, spacing):
            ok = a[int(y), int(x)]
            for k in range(14):
                if not ok:
                    break
                ang = 2 * math.pi * k / 14
                px, py = int(x + (r + 9) * math.cos(ang)), int(y + (r + 9) * math.sin(ang))
                ok = 0 <= px < w and 0 <= py < h and a[py, px]
            if ok:
                pts.append((x - w / 2, y - h / 2))
    return Layer(img, glow=26, glow_strength=0.35), Bulbs(pts, r)


# ---------------------------------------------------------------- logo

def load_logo(path):
    """The logo without the faint brown haze it carries around the letters."""
    src = Image.open(repo(path)).convert("RGBA")
    a = np.asarray(src.getchannel("A"), np.float32)
    src.putalpha(Image.fromarray(np.clip((a - 16) * 255 / 239, 0, 255).astype(np.uint8)))
    return src


def logo_layers(path, width):
    """The logo split into its six sign letters plus the slogan, each with an unlit version."""
    src = load_logo(path)
    s = width / src.width
    src = src.resize((width, round(src.height * s)), Image.LANCZOS)
    w, h = src.size
    cuts = [0, 412, 575, 925, 1342, 1718, 2191]
    cuts = [round(c * s) for c in cuts]
    slogan_y = round(505 * s)
    letters = []
    for x0, x1 in zip(cuts, cuts[1:]):
        part = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        part.paste(src.crop((x0, 0, x1, slogan_y)), (x0, 0))
        part = part.copy()
        dark = np.asarray(part, np.float32).copy()
        dark[..., :3] *= 0.30
        dark[..., 3] *= np.where(dark[..., 3] > 230, 1.0, 0.25)
        letters.append((Layer(part, glow=22, glow_color=(1.0, 0.62, 0.25), glow_strength=0.32),
                        Layer(Image.fromarray(dark.astype(np.uint8), "RGBA"), glow=22, glow_strength=0.0)))
    slogan = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    slogan.paste(src.crop((0, slogan_y, w, h)), (0, slogan_y))
    return letters, Layer(slogan, glow=6, glow_color=(1.0, 0.9, 0.7), glow_strength=0.4), (w, h)


# ---------------------------------------------------------------- icons

HANDSET = [((6.62, 10.79), (8.06, 13.62), (10.38, 15.93), (13.21, 17.38)), ((13.21, 17.38), None, None, (15.41, 15.18)),
           ((15.41, 15.18), (15.68, 14.91), (16.08, 14.82), (16.43, 14.94)),
           ((16.43, 14.94), (17.55, 15.31), (18.76, 15.51), (20.0, 15.51)),
           ((20.0, 15.51), (20.55, 15.51), (21.0, 15.96), (21.0, 16.51)), ((21.0, 16.51), None, None, (21.0, 20.0)),
           ((21.0, 20.0), (21.0, 20.55), (20.55, 21.0), (20.0, 21.0)),
           ((20.0, 21.0), (10.61, 21.0), (3.0, 13.39), (3.0, 4.0)), ((3.0, 4.0), (3.0, 3.45), (3.45, 3.0), (4.0, 3.0)),
           ((4.0, 3.0), None, None, (7.5, 3.0)), ((7.5, 3.0), (8.05, 3.0), (8.5, 3.45), (8.5, 4.0)),
           ((8.5, 4.0), (8.5, 5.25), (8.7, 6.45), (9.07, 7.57)), ((9.07, 7.57), (9.18, 7.92), (9.1, 8.31), (8.82, 8.59)),
           ((8.82, 8.59), None, None, (6.62, 10.79))]


def phone_icon(size):
    big = size * 4
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, big - 1, big - 1), fill=GOLD8 + (255,))
    pts = []
    for p0, c1, c2, p1 in HANDSET:
        if c1 is None:
            pts.append(p1)
            continue
        for k in range(1, 13):
            u = k / 12
            pts.append(tuple((1 - u) ** 3 * a + 3 * (1 - u) ** 2 * u * b + 3 * (1 - u) * u ** 2 * c + u ** 3 * e
                             for a, b, c, e in zip(p0, c1, c2, p1)))
    sc, off = big * 0.56 / 24, big * 0.22
    d.polygon([(off + x * sc, off + y * sc) for x, y in pts], fill=(60, 6, 14, 255))
    return im.resize((size, size), Image.LANCZOS)


def pin_icon(size):
    big = size * 4
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = big * 0.32
    cx, cy = big / 2, big * 0.38
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GOLD8 + (255,))
    d.polygon([(cx - r * 0.86, cy + r * 0.5), (cx + r * 0.86, cy + r * 0.5), (cx, big * 0.96)], fill=GOLD8 + (255,))
    d.ellipse((cx - r * 0.42, cy - r * 0.42, cx + r * 0.42, cy + r * 0.42), fill=(0, 0, 0, 0))
    return im.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- scenes

class Video:
    def __init__(self, cfg):
        self.cfg = cfg
        self.bg = velvet()
        self.sparkles = Sparkles()
        self.letters, self.slogan, self.logo_size = logo_layers(cfg["logo"], 960)

        o = cfg["onuncu"]
        self.ten_top = Layer(text_img(o["ust"], font("CaveatBrush_400Regular.ttf", 92), GOLD8 + (255,)), glow=14,
                             glow_strength=0.45)
        self.ten, self.ten_bulbs = marquee(o["sayi"], 760, 74, 21)
        self.ten_low = Layer(text_img(o["alt"], font("Montserrat_800ExtraBold.ttf", 66), CREAM + (255,), track=7),
                             glow=16, glow_color=(1.0, 0.75, 0.45), glow_strength=0.25)

        y = cfg["yil"]
        yf = font("Anton_400Regular.ttf", 330)
        self.year_head = Layer(gold_text(y["eski"][:-1], yf, track=12), glow=30, glow_strength=0.45)
        self.digit_old = Layer(gold_text(y["eski"][-1], yf), glow=30, glow_strength=0.45)
        self.digit_new = Layer(gold_text(y["yeni"][-1], yf), glow=30, glow_strength=0.45)
        dv = cfg["davet"]
        self.inv1 = Layer(text_img(dv["satir1"], font("Montserrat_800ExtraBold.ttf", 70), CREAM + (255,)), glow=16,
                          glow_color=(1.0, 0.75, 0.45), glow_strength=0.22)
        self.inv2 = Layer(text_img(dv["satir2"], font("Montserrat_700Bold.ttf", 40), GOLD8 + (255,), track=6))

        self.confetti = [dict(x=RNG.uniform(140, 940), y=RNG.uniform(560, 820), vx=RNG.normal(0, 380),
                              vy=RNG.uniform(-1350, -500), rot=RNG.uniform(0, 6.3), vr=RNG.normal(0, 9),
                              w=RNG.uniform(12, 22), h=RNG.uniform(6, 11),
                              c=[(246, 196, 92), (255, 236, 170), (214, 40, 60), (255, 120, 40), (255, 243, 214)][
                                  RNG.integers(0, 5)]) for _ in range(170)]

        c = cfg["cta"]
        self.card = (80, 320, 1000, 1480)
        self.cta_logo = None
        logo = load_logo(cfg["logo"])
        lw = 600
        self.cta_logo = Layer(logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS), glow=14,
                              glow_color=(1.0, 0.62, 0.25), glow_strength=0.5)
        self.cta_head = Layer(text_img(c["baslik"], font("Montserrat_800ExtraBold.ttf", 66), CREAM + (255,)))
        self.cta_sub = Layer(text_img(tr_upper(c["alt"]), font("Montserrat_700Bold.ttf", 34), GOLD8 + (255,), track=6))
        self.phones = []
        for num in c["telefonlar"]:
            fn = font("Montserrat_700Bold.ttf", 68)
            tx = text_img(num, fn, CREAM + (255,), track=2)
            ic = phone_icon(84)
            row = Image.new("RGBA", (ic.width + 26 + tx.width, max(ic.height, tx.height)), (0, 0, 0, 0))
            row.alpha_composite(ic, (0, (row.height - ic.height) // 2))
            row.alpha_composite(tx, (ic.width + 26, (row.height - tx.height) // 2))
            self.phones.append(Layer(row, glow=10, glow_color=(1.0, 0.8, 0.5), glow_strength=0.18))
        af = font("Montserrat_600SemiBold.ttf", 40)
        lines = [text_img(s, af, CREAM + (255,)) for s in c["adres"]]
        ic = pin_icon(70)
        tw = max(l.width for l in lines)
        lh = sum(l.height for l in lines) - 8
        row = Image.new("RGBA", (ic.width + 22 + tw, max(ic.height, lh)), (0, 0, 0, 0))
        row.alpha_composite(ic, (0, (row.height - ic.height) // 2))
        yy = (row.height - lh) // 2
        for l in lines:
            row.alpha_composite(l, (ic.width + 22, yy))
            yy += l.height - 8
        self.address = Layer(row)
        # bulbs around the card
        x0, y0, x1, y1 = self.card
        per = []
        step = 46
        for x in np.arange(x0, x1 + 1, step):
            per.append((x, y0))
        for y in np.arange(y0 + step, y1, step):
            per.append((x1, y))
        for x in np.arange(x1, x0 - 1, -step):
            per.append((x, y1))
        for y in np.arange(y1 - step, y0, -step):
            per.append((x0, y))
        self.frame_bulbs = Bulbs(per, 11)
        self.clip = None

    # -- backdrop shared by the designed scenes
    def backdrop(self, t):
        f = self.bg.copy()
        sx = W / 2 + 260 * math.sin(t * 0.45)
        yy = np.linspace(-1, 1, H, dtype=np.float32)[:, None]
        xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
        spot = np.exp(-(((xx - (sx / W * 2 - 1)) / 0.9) ** 2 + ((yy + 0.15) / 0.7) ** 2))
        f *= (0.78 + 0.5 * spot)[..., None]
        return f

    def clip_frame(self, i):
        if self.clip is None:
            self.clip = subprocess.Popen(
                [FF, "-loglevel", "error", "-i", repo(self.cfg["klip"]), "-vf",
                 f"fps={FPS},scale={W}:{H}:flags=lanczos,unsharp=5:5:0.6", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                stdout=subprocess.PIPE)
        raw = self.clip.stdout.read(W * H * 3)
        if len(raw) < W * H * 3:
            raw = self.last_raw
        self.last_raw = raw
        return np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32) / 255.0

    def logo_scene(self, f, t):
        lt = t - T_LOGO
        lw, lh = self.logo_size
        cy = 860
        s = 1.0 + 0.035 * lt
        op = 1 - ramp(t, T_TEN - 0.3, T_TEN)
        for k, (on, off) in enumerate(self.letters):
            start = 0.3 + k * 0.14
            if lt < start:
                lev = 0.0
            else:
                d = lt - start
                lev = 1.0 if d > 0.16 else (1.0 if d < 0.05 else (0.0 if d < 0.1 else 1.0))
            off.draw(f, W / 2, cy, op, s)
            if lev > 0:
                pulse = 1 + 0.12 * math.sin(lt * 7 + k)
                on.draw(f, W / 2, cy, op * lev, s, glow=pulse)
        self.slogan.draw(f, W / 2, cy, op * ramp(lt, 1.35, 1.75), s)

    def ten_scene(self, f, t):
        lt = t - T_TEN
        op = window(t, T_TEN, T_YEAR, 0.25)
        self.ten_top.draw(f, W / 2, 470 - 30 * (1 - ease_out(lt / 0.5)), op * ramp(lt, 0.0, 0.35))
        sc = 0.88 + 0.12 * ease_back(lt / 0.45)
        cy = 905
        self.ten.draw(f, W / 2, cy, op * ramp(lt, 0.05, 0.3), sc, glow=1.0)
        levels = []
        for i, (x, y) in enumerate(self.ten_bulbs.pts):
            on_at = 0.25 + (x + 400) / 800 * 0.55
            lev = ramp(lt, on_at, on_at + 0.06)
            chase = 0.55 + 0.45 * (1 if (i + int(lt * 8)) % 3 else 0)
            levels.append(lev * (chase if lt > 1.0 else 1.0))
        self._scaled_bulbs(f, self.ten_bulbs, W / 2, cy, sc, levels, op)
        self.ten_low.draw(f, W / 2, 1385 + 26 * (1 - ease_out((lt - 0.7) / 0.4)), op * ramp(lt, 0.7, 1.05))

    @staticmethod
    def _scaled_bulbs(f, bulbs, ox, oy, sc, levels, op):
        pts = bulbs.pts
        bulbs.pts = [(x * sc, y * sc) for x, y in pts]
        bulbs.draw(f, ox, oy, levels, op)
        bulbs.pts = pts

    def year_scene(self, f, t):
        lt = t - T_YEAR
        op = window(t, T_YEAR, T_CTA, 0.25)
        cy = 760
        sc = 0.9 + 0.1 * ease_back(lt / 0.45)
        inner = 2 * 60  # gold_text margin
        hw = (self.year_head.w - 2 * self.year_head.pad - inner) * sc
        dw = (max(self.digit_old.w, self.digit_new.w) - 2 * self.digit_old.pad - inner) * sc
        gap = 14 * sc
        left = W / 2 - (hw + gap + dw) / 2
        self.year_head.draw(f, left + hw / 2, cy, op * ramp(lt, 0, 0.3), sc)
        # odometer: the old digit rolls up and out, the new one rolls in from below
        p = ease_back(ramp(t, ROLL_AT, ROLL_AT + 0.42), 1.2)
        dx = left + hw + gap + dw / 2
        box_h = (self.digit_old.h - 2 * 90) * sc
        clip_top, clip_bot = cy - box_h / 2 + 10, cy + box_h / 2 - 10
        if t < ROLL_AT:
            self.digit_old.draw(f, dx, cy, op, sc)
        elif t > ROLL_AT + 0.55:
            self.digit_new.draw(f, dx, cy, op, sc)
        else:
            tmp = f.copy()
            self.digit_old.draw(tmp, dx, cy - p * box_h, op, sc)
            self.digit_new.draw(tmp, dx, cy + (1 - p) * box_h, op, sc)
            y0, y1 = int(max(clip_top, 0)), int(min(clip_bot, H))
            x0, x1 = int(dx - dw / 2 - 40), int(dx + dw / 2 + 40)
            f[y0:y1, x0:x1] = tmp[y0:y1, x0:x1]
        # flash and confetti when the new year lands
        fl = math.exp(-max(t - POP_AT, 0) / 0.18) if t >= POP_AT else 0.0
        if fl > 0.01:
            add_sprite(f, self.flash, W / 2, cy, fl * 1.2)
        if t >= POP_AT:
            self.draw_confetti(f, t - POP_AT, op)
        self.inv1.draw(f, W / 2, 1180 + 24 * (1 - ease_out((t - POP_AT - 0.1) / 0.4)),
                       op * ramp(t, POP_AT + 0.1, POP_AT + 0.45))
        self.inv2.draw(f, W / 2, 1290, op * ramp(t, POP_AT + 0.35, POP_AT + 0.7))

    def draw_confetti(self, f, dt, op):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for q in self.confetti:
            drag = math.exp(-dt * 0.9)
            x = q["x"] + q["vx"] * (1 - drag) / 0.9
            y = q["y"] + (q["vy"] * (1 - drag) / 0.9) + 520 * dt * dt
            if y > H + 40:
                continue
            ang = q["rot"] + q["vr"] * dt
            flip = abs(math.cos(ang * 1.7))
            w, h = q["w"], q["h"] * (0.3 + 0.7 * flip)
            ca, sa = math.cos(ang), math.sin(ang)
            pts = [(x + ca * px - sa * py, y + sa * px + ca * py) for px, py in
                   ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
            d.polygon(pts, fill=q["c"] + (int(255 * op),))
        Layer(layer).draw(f, W / 2, H / 2)

    def cta_scene(self, f, t):
        lt = t - T_CTA
        op = ramp(lt, 0, 0.3) * (1 - ramp(t, DUR - 0.35, DUR))
        x0, y0, x1, y1 = self.card
        # card: dark glass panel with a thin gold edge
        a = 0.62 * op
        f[y0:y1, x0:x1] *= 1 - a
        f[y0:y1, x0:x1] += np.array([0.05, 0.0, 0.01], np.float32) * a
        edge = 3
        for (sy, sx) in ((slice(y0, y0 + edge), slice(x0, x1)), (slice(y1 - edge, y1), slice(x0, x1)),
                         (slice(y0, y1), slice(x0, x0 + edge)), (slice(y0, y1), slice(x1 - edge, x1))):
            f[sy, sx] = f[sy, sx] * (1 - op) + np.array([0.96, 0.77, 0.36], np.float32) * op
        n = len(self.frame_bulbs.pts)
        lit = ramp(lt, 0.1, 0.7) * n
        levels = [(1.0 if i < lit else 0.0) * (0.45 + 0.55 * (1 if (i + int(lt * 7)) % 3 == 0 else 0.35))
                  for i in range(n)]
        self.frame_bulbs.draw(f, 0, 0, levels, op)

        def item(layer, cy, at, rise=24):
            layer.draw(f, W / 2, cy + rise * (1 - ease_out((lt - at) / 0.35)), op * ramp(lt, at, at + 0.3))

        item(self.cta_logo, 569, 0.15)
        item(self.cta_head, 754, 0.35)
        item(self.cta_sub, 836, 0.5)
        pulse = 1 + 0.025 * math.sin(lt * 5)
        for k, ph in enumerate(self.phones):
            at = 0.65 + k * 0.15
            ph.draw(f, W / 2, 970 + k * 140 + 24 * (1 - ease_out((lt - at) / 0.35)), op * ramp(lt, at, at + 0.3),
                    pulse if lt > 1.4 else 1.0)
        item(self.address, 1270, 1.0)

    def frame(self, t, i):
        if t < T_LOGO:
            f = self.clip_frame(i)
            # gold flash into the logo
            fl = ramp(t, T_LOGO - 0.22, T_LOGO)
            if fl > 0:
                add_sprite(f, self.flash, W / 2, H * 0.45, fl * 1.6)
            return f
        f = self.backdrop(t)
        if t < T_LOGO + 0.3:
            add_sprite(f, self.flash, W / 2, H * 0.45, 1.6 * (1 - ramp(t, T_LOGO, T_LOGO + 0.3)))
        self.sparkles.draw(f, t, 1.0 if t < T_CTA else 0.6)
        if t < T_TEN:
            self.logo_scene(f, t)
        elif t < T_YEAR:
            self.ten_scene(f, t)
        elif t < T_CTA:
            self.year_scene(f, t)
        else:
            self.cta_scene(f, t)
        return f

    def render(self, out_mp4, audio, t0=0.0, t1=DUR):
        self.flash = glow_sprite(2600, (1.0, 0.86, 0.6), 330)
        n = int(round((t1 - t0) * FPS))
        enc = subprocess.Popen(
            [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_mp4],
            stdin=subprocess.PIPE)
        for i in range(n):
            t = t0 + i / FPS
            f = self.frame(t, i)
            enc.stdin.write((np.clip(f, 0, 1) * 255).astype(np.uint8).tobytes())
            if i % 60 == 0:
                print(f"  kare {i}/{n}", flush=True)
        enc.stdin.close()
        enc.wait()
        if self.clip:
            self.clip.terminate()

    def still(self, t, path):
        self.flash = glow_sprite(2600, (1.0, 0.86, 0.6), 330)
        Image.fromarray((np.clip(self.frame(t, 0), 0, 1) * 255).astype(np.uint8)).save(path, quality=93)


# ---------------------------------------------------------------- sound

def phone_ring(sec):
    t = ses.t_axis(sec)
    clapper = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 20 * t))
    bell = sum(ses.osc(f, sec) * g for f, g in ((1180, 1.0), (1765, 0.6), (2370, 0.35), (3140, 0.2)))
    env = np.minimum(t / 0.02, 1) * np.minimum((sec - t) / 0.05, 1)
    return ses.stereo(bell * clapper * env * 0.16, 0.15, 0.004)


def relay_click():
    t = ses.t_axis(0.12)
    x = ses.fft_filter(ses.noise(0.12, 1)[:, 0], lo=1500, hi=9000) * np.exp(-t / 0.006) * 0.6
    return ses.stereo(x + ses.osc(1900, 0.12) * np.exp(-t / 0.02) * 0.12)


def groove(put, music, start, end, kick_from):
    """Festive groove in C major, 120 BPM, I - V - vi - IV: pad, bell arpeggio, bass, shaker, kick and clap."""
    beat = 0.5
    chords = [(65.41, (261.63, 329.63, 392.0)), (98.0, (246.94, 293.66, 392.0)),
              (110.0, (261.63, 329.63, 440.0)), (87.31, (261.63, 349.23, 440.0))]
    melody = [[523.25, 659.25, 783.99, 659.25, 1046.5, 783.99, 659.25, 783.99],
              [587.33, 783.99, 987.77, 783.99, 1174.66, 987.77, 783.99, 587.33],
              [659.25, 880.0, 1046.5, 880.0, 1318.51, 1046.5, 880.0, 659.25],
              [698.46, 880.0, 1046.5, 880.0, 1396.91, 1046.5, 880.0, 698.46]]
    t, bar = start, 0
    while t < end:
        root, triad = chords[bar % 4]
        put(music, t, ses.pad([f / 2 for f in triad], 2.05, hi=1800), 0.9)
        for k in range(8):
            at = t + k * beat / 2
            if at >= end:
                break
            put(music, at, ses.pluck(melody[bar % 4][k]), 0.55 if k % 2 else 0.75)
            put(music, at, ses.bass(root if k % 2 == 0 else root * 2, beat / 2 * 0.9), 0.5)
        for b in range(4):
            at = t + b * beat
            if at >= end:
                break
            if at >= kick_from:
                put(music, at, ses.kick(), 0.85)
                if b % 2 == 1:
                    put(music, at, ses.clap(), 0.55)
            for q in range(4):
                put(music, at + q * beat / 4, ses.hat(), 0.32 if q % 2 else 0.18)
        t += 4 * beat
        bar += 1


def finish(music, fx, sec, path):
    """Mix, add room, fade the tail and master to -14 LUFS."""
    import soundfile as sf
    SR = ses.SR
    n = len(music)
    mix = music * 0.8 + fx
    mix += ses.reverb(mix * 0.22, 2.0)
    fade = np.ones(n)
    a, b = int((sec - 0.4) * SR), min(n, int((sec + 0.6) * SR))
    fade[a:b] = np.linspace(1, 0, b - a)
    fade[b:] = 0
    fade[: int(0.03 * SR)] = np.linspace(0, 1, int(0.03 * SR))  # no hard edge on the first sample
    mix = (mix * fade[:, None])[: int(sec * SR)]
    raw = path + ".wav"
    sf.write(raw, (mix / max(1e-6, np.abs(mix).max()) * 0.9).astype(np.float32), SR)
    loud = path + ".loud.m4a"
    ses.master(raw, loud)
    # short, punchy mixes can overshoot after loudness matching: hold peaks under -1.5 dBFS
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", loud, "-af", "alimiter=limit=0.74:level=false",
                    "-c:a", "aac", "-b:a", "192k", path], check=True)
    os.remove(raw)
    os.remove(loud)


def outro_sound(path):
    """Sound for the end card on its own: whoosh in, the groove, a closing chord."""
    SR = ses.SR
    sec = DUR - T_CTA
    n = int((sec + 1.5) * SR)
    music, fx = np.zeros((n, 2)), np.zeros((n, 2))

    def put(buf, at, sig, gain=1.0):
        i = int(at * SR)
        j = min(n, i + len(sig))
        if i < n:
            buf[i:j] += sig[: j - i] * gain

    groove(put, music, 0.0, sec - 0.6, 0.0)
    put(fx, 0.0, ses.whoosh(0.4, rising=False), 0.6)
    put(fx, 0.0, ses.shimmer(1.6), 1.0)
    for k in range(2):
        put(fx, 0.65 + k * 0.15, ses.blip(1568 + 400 * k, 0.3), 0.9)
    put(fx, sec - 0.6, ses.stab((261.63, 329.63, 392.0, 523.25), 1.2), 1.3)
    put(fx, sec - 0.6, ses.impact(0.8), 0.4)
    finish(music, fx, sec, path)


def soundtrack(cfg, path):
    SR = ses.SR
    n = int((DUR + 1.5) * SR)
    music, fx = np.zeros((n, 2)), np.zeros((n, 2))

    def put(buf, at, sig, gain=1.0):
        i = int(at * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        buf[i:j] += sig[: j - i] * gain

    # the client's clip keeps its own sound (sparkles, the receiver being lifted)
    wav = os.path.join(HERE, ".klip-ses.wav")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", repo(cfg["klip"]), "-ac", "2", "-ar", str(SR), wav], check=True)
    import soundfile as sf
    clip, _ = sf.read(wav)
    os.remove(wav)
    put(fx, 0.0, clip[: int(T_LOGO * SR)], 1.0)
    put(fx, 1.6, phone_ring(1.55), 1.0)
    put(fx, T_LOGO - 0.45, ses.whoosh(0.45), 0.8)
    put(fx, T_LOGO, ses.impact(0.7), 0.5)
    put(fx, T_LOGO, ses.shimmer(1.8), 1.4)
    for k in range(6):  # each sign letter switching on
        put(fx, T_LOGO + 0.3 + k * 0.14, relay_click(), 0.9)

    groove(put, music, T_LOGO, DUR - 0.6, T_LOGO + 1.0)
    end = DUR - 0.6

    put(fx, T_TEN, ses.stab((261.63, 329.63, 392.0, 523.25)), 1.2)
    put(fx, T_TEN, ses.impact(0.6), 0.35)
    put(fx, T_TEN + 0.25, ses.shimmer(1.4), 1.1)
    put(fx, ROLL_AT - 0.5, ses.snare_roll(0.9), 0.45)
    put(fx, ROLL_AT - 0.6, ses.riser(1.0), 0.6)
    put(fx, POP_AT, ses.impact(1.0), 0.6)
    put(fx, POP_AT, ses.clap(), 1.0)
    put(fx, POP_AT, ses.shimmer(2.2), 1.6)
    put(fx, T_CTA, ses.whoosh(0.4, rising=False), 0.6)
    for k in range(2):
        put(fx, T_CTA + 0.65 + k * 0.15, ses.blip(1568 + 400 * k, 0.3), 0.9)
    put(fx, end, ses.stab((261.63, 329.63, 392.0, 523.25), 1.2), 1.3)
    put(fx, end, ses.impact(0.8), 0.4)

    finish(music, fx, DUR, path)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "ayarlar.json")
    cfg = json.load(open(path, encoding="utf-8"))
    audio = os.path.join(HERE, ".ses.m4a")
    soundtrack(cfg, audio)
    v = Video(cfg)
    out = repo(cfg["cikti"])
    v.render(out, audio)
    os.remove(audio)
    print("kaydedildi:", os.path.relpath(out, REPO))
    v2 = Video(cfg)
    v2.still(POP_AT + 1.2, repo(cfg["kapak"]))
    print("kaydedildi:", cfg["kapak"])

    # the end card on its own, for any other Bidaha video or story
    k = cfg["kapanis"]
    os.makedirs(os.path.dirname(repo(k["video"])), exist_ok=True)
    audio = os.path.join(HERE, ".kapanis.m4a")
    outro_sound(audio)
    Video(cfg).render(repo(k["video"]), audio, T_CTA, DUR)
    os.remove(audio)
    Video(cfg).still(T_CTA + 3.0, repo(k["gorsel"]))
    print("kaydedildi:", k["video"], "ve", k["gorsel"])


if __name__ == "__main__":
    main()
