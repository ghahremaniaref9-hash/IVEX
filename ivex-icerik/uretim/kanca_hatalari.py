"""IVEX Medya - "İçeriğin 2 saniyede geçiliyorsa sebebi bu 3 hata" Reels'i (1080x1920, 28 sn, seslendirmesiz).

Kullanım:  python3 kanca_hatalari.py ../ayarlar/kanca-hatalari.json [önizleme saniyeleri ...]
Ekranda bir telefon ve içinde akan Reels'ler var. Her hatada önce kötü örnek oynar, başparmak onu kaydırıp geçer
("GEÇİLDİ"); sonra doğrusu gelir, başparmak durur ("DURDU"). Köşedeki temsilî izlenme çizgisi kötü örnekte
2. saniyede düşer, doğrusunda yüksek kalır. Sonunda video kendi kurallarını geri sarar: kanca, an, altyazı.
Bütün örnekler kodla çizilir (müşteri görseli yok); seslendirme yok, her şey ekranda yazılı. Müzik ses.py'den,
aynı zaman çizelgesinden üretilir; 3. hatada (sessiz izleme) müzik boğuklaşır, altyazı gelince açılır.
"""
import json
import math
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import ses
from marka import INK, LIME, SOFT, WHITE, background, font, logo, pill, repo, tracked, write_video
from marka_filmi import clamp, ease, ease_io, faded, glow, prog, put, text_img

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
TOTAL = 28.0
RED = (238, 52, 52)
SEGS = {"giris": (0.0, 3.0), "h1": (3.0, 3.0), "d1": (6.0, 4.0), "h2": (10.0, 3.0), "d2": (13.0, 4.0),
        "h3": (17.0, 2.5), "d3": (19.5, 3.5), "geri": (23.0, 2.0), "son": (25.0, 3.0)}
# the phone's feed: when each reel is swiped in
FEED = [(0.0, "f0"), (0.6, "f1"), (1.2, "f2"), (1.8, "f3"), (2.4, "f4"), (3.0, "logo"), (5.75, "tabak"),
        (10.0, "afis"), (12.85, "kahve"), (17.0, "konusan")]
SWIPE = 0.28
PASSED = {"f0": 0.32, "f1": 0.92, "f2": 1.52, "f3": 2.12, "f4": 2.72, "logo": 5.3, "afis": 12.4, "konusan": 19.0}
STOPPED = {"tabak": 7.0, "kahve": 14.1, "konusan": 22.0}
MARKS = (10.6, 11.0, 11.4, 11.8)  # red rings on the flyer
SUB_AT = 19.5  # subtitles (and the sound) come on
MUFFLE = (17.15, 19.45)
CUTS = (23.0, 23.5, 24.0, 24.5)  # the rewind montage
END_AT = (25.0, 25.25, 25.5, 25.8, 26.2, 26.45)

SX, SY, SW, SH = 280, 660, 520, 1000  # phone screen
BEZ = 16
CHART = (690, 690, 1020, 872)


def deco(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


ANTON, CAVEAT, OSWALD = "Anton_400Regular.ttf", "CaveatBrush_400Regular.ttf", "Oswald_700Bold.ttf"
_cache = {}


def cached(key, make):
    if key not in _cache:
        _cache[key] = make()
    return _cache[key]


def vgrad(w, h, top, bottom):
    y = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, np.float32) * (1 - y) + np.array(bottom, np.float32) * y
    return Image.fromarray(np.repeat(a, w, axis=1).astype(np.uint8), "RGB")


def shadow_text(text, fnt, fill=WHITE):
    """A line of reel text with the soft drop shadow phone captions have."""
    def make():
        t = text_img(text, fnt, fill)
        out = Image.new("RGBA", (t.width + 30, t.height + 30), (0, 0, 0, 0))
        blob = Image.new("RGBA", t.size, (0, 0, 0, 255))
        blob.putalpha(t.getchannel("A"))
        out.alpha_composite(blob, (15, 19))
        out = out.filter(ImageFilter.GaussianBlur(7))
        out.alpha_composite(t, (15, 15))
        return out
    return cached(("st", text, fnt.path, fnt.size, fill), make)


def fit(lines, size, width=960, weight="Black"):
    while size > 40 and max(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(l, font=font(weight, size))
                            for l in lines) > width:
        size -= 2
    return size


def steam(layer, cx, base_y, t, n=3, height=280, spread=58, alpha=150):
    d = ImageDraw.Draw(layer)
    for k in range(n):
        x0 = cx + (k - (n - 1) / 2) * spread
        rise = (t * 0.35 + k * 0.33) % 1
        pts = []
        for j in range(32):
            u = j / 31
            pts.append((x0 + 16 * math.sin(t * 2.6 + k * 1.7 + u * 6.5) * (0.3 + u),
                        base_y - 30 - u * height - rise * 40))
        a = alpha * (0.55 + 0.45 * math.sin(t * 1.9 + k * 2.1))
        d.line(pts, fill=(255, 255, 255, int(a)), width=12, joint="curve")


def check_mark(d, x, y, s, color, width=6):
    d.line([(x, y + s * 0.5), (x + s * 0.38, y + s * 0.88), (x + s, y + s * 0.1)], fill=color, width=width,
           joint="curve")


class Reels:
    """Everything drawn inside the phone screen (SW x SH)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.ui = self._ui()

    # ── chrome of the reel player ──
    def _ui(self):
        im = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        top = vgrad(SW, 140, (0, 0, 0), (0, 0, 0))
        top.putalpha(Image.linear_gradient("L").resize((SW, 140)).transpose(Image.FLIP_TOP_BOTTOM).point(lambda v: v // 3))
        im.alpha_composite(top)
        bottom = vgrad(SW, 220, (0, 0, 0), (0, 0, 0))
        bottom.putalpha(Image.linear_gradient("L").resize((SW, 220)).point(lambda v: v // 2))
        im.alpha_composite(bottom, (0, SH - 220))
        d.text((26, 26), "Reels", font=font("Bold", 30), fill=WHITE)
        x = SW - 50
        # heart, comment, share (generic shapes)
        y = 640
        d.ellipse((x - 18, y - 10, x + 2, y + 10), outline=WHITE, width=4)
        d.ellipse((x - 2, y - 10, x + 18, y + 10), outline=WHITE, width=4)
        d.line([(x - 17, y + 4), (x, y + 22), (x + 17, y + 4)], fill=WHITE, width=4, joint="curve")
        y = 730
        d.ellipse((x - 18, y - 16, x + 18, y + 16), outline=WHITE, width=4)
        d.polygon([(x - 14, y + 10), (x - 20, y + 24), (x - 4, y + 15)], fill=WHITE)
        y = 820
        d.polygon([(x - 18, y - 4), (x + 18, y - 16), (x + 4, y + 18)], outline=WHITE, width=4)
        d.ellipse((24, 896, 60, 932), outline=WHITE, width=3)
        d.text((72, 897), self.cfg["kullanici"], font=font("Bold", 24), fill=WHITE)
        d.text((26, 942), "Daha fazla…", font=font("Medium", 20), fill=(255, 255, 255, 200))
        return im

    def chrome(self, im, lt):
        im.alpha_composite(self.ui)
        bar = Image.new("RGBA", (SW, 6), (255, 255, 255, 70))
        ImageDraw.Draw(bar).rectangle((0, 0, SW * ((lt % 12) / 12), 6), fill=(255, 255, 255, 230))
        im.alpha_composite(bar, (0, SH - 6))

    # ── boring filler posts swiped past in the intro ──
    def filler(self, k):
        def make():
            if k == 0:
                im = vgrad(SW, SH, (247, 186, 196), (252, 220, 190))
                d = ImageDraw.Draw(im, "RGBA")
                d.text((60, 250), "“", font=deco(CAVEAT, 200), fill=(255, 255, 255, 200))
                for i, line in enumerate(("Pazartesi", "motivasyonu")):
                    f = deco(CAVEAT, 84)
                    d.text(((SW - d.textlength(line, font=f)) / 2, 400 + i * 96), line, font=f, fill=(120, 60, 80))
            elif k == 1:
                im = vgrad(SW, SH, (24, 34, 70), (14, 20, 44))
                d = ImageDraw.Draw(im, "RGBA")
                d.ellipse((150, 330, 370, 550), outline=WHITE, width=6)
                f = deco(OSWALD, 56)
                d.text(((SW - d.textlength("LOGO", font=f)) / 2, 400), "LOGO", font=f, fill=WHITE)
                f = font("Medium", 38)
                d.text(((SW - d.textlength("Hoş geldiniz", font=f)) / 2, 600), "Hoş geldiniz", font=f, fill=WHITE)
            elif k == 2:
                im = vgrad(SW, SH, (206, 206, 206), (170, 170, 170))
                d = ImageDraw.Draw(im, "RGBA")
                d.rectangle((70, 280, 450, 600), fill=(225, 225, 225))
                d.polygon([(110, 560), (210, 420), (290, 520), (340, 460), (420, 560)], fill=(170, 170, 170))
                d.ellipse((330, 320, 380, 370), fill=(190, 190, 190))
                f = deco(OSWALD, 62)
                d.text(((SW - d.textlength("Yeni sezon", font=f)) / 2, 640), "Yeni sezon", font=f, fill=(60, 60, 60))
            elif k == 3:
                im = vgrad(SW, SH, (252, 222, 64), (246, 196, 40))
                d = ImageDraw.Draw(im, "RGBA")
                for i, line in enumerate(("HAFTA SONU", "AÇIĞIZ")):
                    f = deco(ANTON, 92)
                    d.text(((SW - d.textlength(line, font=f)) / 2, 360 + i * 120), line, font=f, fill=(30, 30, 30))
            else:
                im = vgrad(SW, SH, (130, 80, 200), (70, 40, 140))
                d = ImageDraw.Draw(im, "RGBA")
                for i, line in enumerate(("1000 takipçi", "teşekkürler!")):
                    f = deco(CAVEAT, 76)
                    d.text(((SW - d.textlength(line, font=f)) / 2, 400 + i * 90), line, font=f, fill=WHITE)
            return im.convert("RGBA")
        return cached(("filler", k), make).copy()

    # ── hata 1: opens on a logo ──
    def logo_intro(self, lt):
        im = vgrad(SW, SH, (20, 30, 62), (12, 18, 40))
        d = ImageDraw.Draw(im, "RGBA")
        a = clamp(lt / 1.8)
        d.ellipse((160, 300, 360, 500), outline=(255, 255, 255, int(255 * a)), width=6)
        f = deco(OSWALD, 52)
        d.text(((SW - d.textlength("LOGO", font=f)) / 2, 362), "LOGO", font=f, fill=(255, 255, 255, int(255 * a)))
        f = deco(CAVEAT, 64)
        b = clamp((lt - 1.2) / 0.8)
        d.text(((SW - d.textlength("Lezzet Durağı", font=f)) / 2, 540), "Lezzet Durağı", font=f,
               fill=(255, 214, 120, int(255 * b)))
        f = font("Medium", 30)
        c = clamp((lt - 1.9) / 0.5)
        d.text(((SW - d.textlength("sunar…", font=f)) / 2, 630), "sunar…", font=f, fill=(255, 255, 255, int(200 * c)))
        return im.convert("RGBA")

    # ── doğrusu 1: the best frame first ──
    def plate(self):
        def make():
            im = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
            yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
            r = np.hypot((xx - SW / 2) / SW, (yy - 600) / SH)
            g = np.clip(1 - r * 1.6, 0, 1)[..., None]
            base = np.array((34, 18, 10), np.float32) + np.array((60, 34, 18), np.float32) * g
            im = Image.fromarray(base.astype(np.uint8), "RGB")
            d = ImageDraw.Draw(im, "RGBA")
            cx, cy = SW / 2, 640
            d.ellipse((cx - 205, cy - 195, cx + 205, cy + 215), fill=(0, 0, 0, 90))
            d.ellipse((cx - 200, cy - 200, cx + 200, cy + 200), fill=(242, 238, 230))
            d.ellipse((cx - 168, cy - 168, cx + 168, cy + 168), fill=(228, 222, 212))
            d.ellipse((cx - 150, cy - 150, cx + 150, cy + 150), fill=(200, 74, 32))
            rng = np.random.default_rng(3)
            for _ in range(14):
                ang, rad = rng.random() * 6.28, rng.random() * 110
                x, y = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
                s = 16 + rng.random() * 14
                d.rounded_rectangle((x - s, y - s * 0.8, x + s, y + s * 0.8), radius=8, fill=(112, 48, 26))
            for _ in range(22):
                ang, rad = rng.random() * 6.28, rng.random() * 130
                x, y = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
                d.ellipse((x - 7, y - 4, x + 7, y + 4), fill=(96, 170, 64))
            for _ in range(10):
                ang, rad = rng.random() * 6.28, rng.random() * 120
                x, y = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
                d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(236, 120, 60))
            return im.convert("RGBA")
        return cached("plate", make)

    def tabak(self, lt, labels=()):
        im = self.plate().copy()
        st = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        steam(st, SW / 2, 560, lt)
        im.alpha_composite(st.filter(ImageFilter.GaussianBlur(7)))
        for i, line in enumerate(self.cfg["ornekler"]["kanca"]):
            put(im, shadow_text(line, font("Black", 50)), SW / 2, 228 + i * 66)
        return im

    # ── hata 2: a crowded flyer ──
    def afis(self):
        def make():
            im = Image.new("RGB", (SW, SH))
            cols = [(255, 64, 129), (255, 152, 0), (255, 235, 59), (76, 175, 80), (33, 150, 243), (156, 39, 176)]
            band = SH // len(cols) + 1
            d = ImageDraw.Draw(im, "RGBA")
            for i, c in enumerate(cols):
                d.rectangle((0, i * band, SW, (i + 1) * band), fill=c)
            d.ellipse((30, 120, 150, 240), fill=WHITE, outline=(20, 20, 20), width=4)
            f = deco(OSWALD, 30)
            d.text((90 - d.textlength("LOGO", font=f) / 2, 160), "LOGO", font=f, fill=(20, 20, 20))
            for i, line in enumerate(("BÜYÜK", "İNDİRİM!!!")):
                f = deco(ANTON, 88)
                d.text(((SW - d.textlength(line, font=f)) / 2, 250 + i * 100), line, font=f, fill=(220, 20, 20),
                       stroke_width=5, stroke_fill=(255, 240, 0))
            cx, cy = 400, 530
            star = []
            for k in range(24):
                r = 98 if k % 2 == 0 else 70
                a = k * math.pi / 12
                star.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            d.polygon(star, fill=(255, 235, 0), outline=(220, 20, 20))
            f = deco(ANTON, 62)
            d.text((cx - d.textlength("%20", font=f) / 2, cy - 44), "%20", font=f, fill=(220, 20, 20))
            d.rectangle((60, 600, 300, 790), fill=(214, 214, 214), outline=WHITE, width=4)
            d.polygon([(80, 770), (150, 670), (200, 730), (240, 690), (285, 770)], fill=(160, 160, 160))
            d.text((86, 612), "stok fotoğraf", font=font("Medium", 20), fill=(110, 110, 110))
            f = deco(CAVEAT, 46)
            d.text((320, 690), "Hemen", font=f, fill=WHITE, stroke_width=2, stroke_fill=(20, 20, 20))
            d.text((320, 736), "arayın!", font=f, fill=WHITE, stroke_width=2, stroke_fill=(20, 20, 20))
            f = deco(OSWALD, 40)
            num = "0 (555) 000 00 00"
            d.text(((SW - d.textlength(num, font=f)) / 2, 812), num, font=f, fill=(20, 20, 20))
            return im.convert("RGBA")
        return cached("afis", make).copy()

    MARK_BOXES = [(18, 104, 162, 256), (288, 418, 512, 642), (40, 806, 480, 868), (44, 586, 316, 806)]

    def marks(self, im, t):
        d = ImageDraw.Draw(im)
        for at, box in zip(MARKS, self.MARK_BOXES):
            p = clamp((t - at) / 0.25)
            if p > 0:
                d.arc(box, -100, -100 + 360 * ease(p), fill=RED, width=8)

    # ── doğrusu 2: a moment, one sentence ──
    def cup(self):
        def make():
            im = vgrad(SW, SH, (226, 198, 164), (176, 128, 86))
            d = ImageDraw.Draw(im, "RGBA")
            for x, y, r, a in ((80, 180, 60, 60), (420, 140, 80, 50), (300, 260, 40, 70), (120, 360, 30, 60)):
                d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 240, 210, a))
            d.rectangle((0, 760, SW, SH), fill=(120, 76, 44))
            for k in range(8):
                y = 770 + k * 28
                d.line([(0, y), (SW, y + 6)], fill=(100, 62, 36), width=3)
            cx = SW / 2
            d.ellipse((cx - 175, 700, cx + 175, 800), fill=(0, 0, 0, 60))
            d.ellipse((cx - 165, 690, cx + 165, 780), fill=(246, 244, 238))
            d.ellipse((cx - 120, 708, cx + 120, 762), fill=(226, 222, 214))
            d.ellipse((cx + 70, 560, cx + 170, 660), outline=(246, 244, 238), width=22)
            d.polygon([(cx - 120, 520), (cx + 120, 520), (cx + 96, 735), (cx - 96, 735)], fill=(246, 244, 238))
            d.ellipse((cx - 96, 712, cx + 96, 758), fill=(246, 244, 238))
            d.polygon([(cx + 60, 540), (cx + 110, 540), (cx + 90, 720), (cx + 70, 720)], fill=(226, 222, 214))
            d.ellipse((cx - 120, 494, cx + 120, 546), fill=(232, 228, 220))
            d.ellipse((cx - 108, 500, cx + 108, 542), fill=(116, 64, 30))
            hx, hy = cx, 520  # latte heart
            d.ellipse((hx - 34, hy - 16, hx - 2, hy + 8), fill=(240, 224, 200))
            d.ellipse((hx + 2, hy - 16, hx + 34, hy + 8), fill=(240, 224, 200))
            d.polygon([(hx - 33, hy - 2), (hx + 33, hy - 2), (hx, hy + 18)], fill=(240, 224, 200))
            return im.convert("RGBA")
        return cached("cup", make)

    def kahve(self, lt):
        im = self.cup().copy()
        st = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        steam(st, SW / 2, 500, lt, height=240, spread=50, alpha=130)
        im.alpha_composite(st.filter(ImageFilter.GaussianBlur(7)))
        for i, line in enumerate(self.cfg["ornekler"]["an"]):
            put(im, shadow_text(line, font("Black", 50)), SW / 2, 236 + i * 66)
        return im

    # ── hata / doğrusu 3: someone talking, with and without subtitles ──
    def person(self):
        def make():
            im = vgrad(SW, SH, (46, 84, 96), (20, 40, 50))
            d = ImageDraw.Draw(im, "RGBA")
            d.ellipse((60, 160, 460, 560), fill=(255, 255, 255, 18))
            cx = SW / 2
            d.polygon([(cx - 200, SH), (cx - 170, 690), (cx - 60, 640), (cx + 60, 640), (cx + 170, 690),
                       (cx + 200, SH)], fill=(232, 110, 88))
            d.rectangle((cx - 34, 590, cx + 34, 660), fill=(214, 168, 136))
            d.polygon([(cx - 60, 640), (cx, 700), (cx + 60, 640)], fill=(214, 168, 136))
            d.ellipse((cx - 100, 390, cx + 100, 610), fill=(230, 190, 158))
            d.chord((cx - 108, 370, cx + 108, 560), 180, 360, fill=(52, 36, 30))
            d.ellipse((cx - 112, 420, cx - 80, 500), fill=(52, 36, 30))
            d.ellipse((cx + 80, 420, cx + 112, 500), fill=(52, 36, 30))
            d.ellipse((cx - 108, 480, cx - 88, 520), fill=(222, 178, 146))
            d.ellipse((cx + 88, 480, cx + 108, 520), fill=(222, 178, 146))
            return im.convert("RGBA")
        return cached("person", make)

    def konusan(self, t, subs):
        im = self.person().convert("RGB")
        d = ImageDraw.Draw(im, "RGBA")
        cx = SW / 2
        blink = (t % 2.6) < 0.12
        for ex in (cx - 40, cx + 40):
            if blink:
                d.line([(ex - 12, 500), (ex + 12, 500)], fill=(40, 28, 24), width=4)
            else:
                d.ellipse((ex - 9, 490, ex + 9, 510), fill=(40, 28, 24))
        talk = abs(math.sin(t * 9.0)) * (0.6 + 0.4 * math.sin(t * 2.3)) * (1 if (t % 2.2) < 1.8 else 0.1)
        h = 6 + 26 * talk
        d.rounded_rectangle((cx - 24, 548 - h / 2, cx + 24, 548 + h / 2), radius=min(12, h / 2), fill=(120, 40, 40))
        # sound icon, top left
        d.ellipse((24, 130, 112, 218), fill=(0, 0, 0, 120))
        d.rectangle((46, 160, 60, 188), fill=WHITE)
        d.polygon([(60, 160), (80, 144), (80, 204), (60, 188)], fill=WHITE)
        if subs:
            for r in (12, 22):
                d.arc((80 - r, 174 - r, 80 + r, 174 + r), -50, 50, fill=LIME, width=4)
        else:
            d.line([(36, 142), (100, 206)], fill=RED, width=7)
        im = im.convert("RGBA")
        if subs:
            for i, line in enumerate(self.cfg["ornekler"]["baslik"]):
                put(im, shadow_text(line, font("Black", 44)), cx, 250 + i * 58)
            chunks = self.cfg["ornekler"]["altyazi"]
            lt = max(0.0, t - SUB_AT - 0.1)
            k = min(int(lt / 0.6), len(chunks) - 1)
            p = clamp((lt - k * 0.6) / 0.12)
            put(im, self.subtitle(chunks[k]), cx, 770, 1.0, 0, 0.85 + 0.15 * ease(p))
        return im

    @staticmethod
    def subtitle(text):
        def make():
            f = font("ExtraBold", 40)
            tw = ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(text, font=f)
            im = Image.new("RGBA", (round(tw) + 36, 62), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((0, 0, im.width - 1, 61), radius=14, fill=LIME)
            d.text((18, 6), text, font=f, fill=INK)
            return im
        return cached(("sub", text), make)

    # ── stamps ──
    @staticmethod
    def stamp(text, color, angle):
        def make():
            f = font("Black", 66)
            d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            tw = d0.textlength(text, font=f)
            im = Image.new("RGBA", (int(tw) + 80, 130), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((6, 6, im.width - 6, im.height - 6), radius=18, outline=color, width=9)
            d.text((40, 22), text, font=f, fill=color)
            return im.rotate(angle, expand=True, resample=Image.BICUBIC)
        return cached(("stamp", text, color, angle), make)

    def stamps(self, im, key, t):
        if key in PASSED and t >= PASSED[key] and not (key == "konusan" and t >= SUB_AT):
            p = clamp((t - PASSED[key]) / 0.14)
            put(im, self.stamp("GEÇİLDİ", RED, 12), SW / 2, 420, 1.0, 0, 1.5 - 0.5 * ease(p))
        if key in STOPPED and t >= STOPPED[key]:  # pops, then clears so the good example stays in view
            p = clamp((t - STOPPED[key]) / 0.14)
            a = 1 - prog(t, STOPPED[key] + 0.9, 0.3)
            put(im, self.stamp("DURDU", LIME, -8), SW / 2, 380, a, 0, 1.5 - 0.5 * ease(p))

    def content(self, key, t, lt):
        if key.startswith("f"):
            return self.filler(int(key[1]))
        if key == "logo":
            return self.logo_intro(lt)
        if key == "tabak":
            return self.tabak(lt)
        if key == "afis":
            im = self.afis()
            self.marks(im, t)
            return im
        if key == "kahve":
            return self.kahve(lt)
        return self.konusan(t, t >= SUB_AT)

    def label_pills(self, im, labels):
        d = ImageDraw.Draw(im)
        f = font("ExtraBold", 34)
        for i, text in enumerate(labels):
            tw = d.textlength(text, font=f)
            w = tw + 100
            x0, y0 = (SW - w) / 2, 650 + i * 84 if len(labels) > 1 else 760
            d.rounded_rectangle((x0, y0, x0 + w, y0 + 66), radius=33, fill=LIME)
            d.text((x0 + 30, y0 + 13), text, font=f, fill=INK)
            check_mark(d, x0 + w - 56, y0 + 18, 30, INK, 6)

    def screen(self, t):
        if t >= CUTS[0]:  # rewind montage of the three good examples
            k = sum(t >= c for c in CUTS) - 1
            labels = self.cfg["etiketler"]
            if k == 0:
                im, lab = self.tabak(t - 22.0), labels[:1]
            elif k == 1:
                im, lab = self.kahve(t - 22.0), labels[1:2]
            elif k == 2:
                im, lab = self.konusan(t, True), labels[2:3]
            else:
                im, lab = self.tabak(t - 22.0), labels
            self.chrome(im, t)
            self.label_pills(im, lab)
            d = ImageDraw.Draw(im)
            for dx in (0, 26):  # rewind sign
                d.polygon([(SW / 2 - 4 + dx, 40), (SW / 2 - 4 + dx, 76), (SW / 2 - 30 + dx, 58)], fill=WHITE)
            flash = 0.55 * math.exp(-(t - CUTS[k]) / 0.07)
            if flash > 0.02:
                im = Image.blend(im, Image.new("RGBA", (SW, SH), (255, 255, 255, 255)), flash)
            return im
        s = 0.0
        for ts, _ in FEED[1:]:
            s += ease_io(clamp((t - ts) / SWIPE))
        out = Image.new("RGBA", (SW, SH), (0, 0, 0, 255))
        for i, (ts, key) in enumerate(FEED):
            off = (i - s) * SH
            if abs(off) >= SH:
                continue
            im = self.content(key, t, t - ts)
            self.chrome(im, t - ts)
            self.stamps(im, key, t)
            out.alpha_composite(im, (0, round(off)))
        return out


class Video:
    def __init__(self, cfg):
        self.cfg = cfg
        bg = background((W, H), seed=29, glow=(0.5, 0.42)).convert("RGBA")
        a = np.asarray(bg).astype(np.float32)
        a[..., :3] *= 0.45
        self.bg = Image.fromarray(a.astype(np.uint8), "RGBA")
        self.lime_glow = glow((900, 900), LIME, 330, 0.5)
        self.reels = Reels(cfg)
        self.mask = Image.new("L", (SW, SH), 0)
        ImageDraw.Draw(self.mask).rounded_rectangle((0, 0, SW - 1, SH - 1), radius=52, fill=255)
        body = Image.new("RGBA", (SW + 2 * BEZ + 120, SH + 2 * BEZ + 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(body)
        d.rounded_rectangle((60, 80, 60 + SW + 2 * BEZ, 80 + SH + 2 * BEZ), radius=68, fill=(0, 0, 0, 170))
        self.phone_shadow = body.filter(ImageFilter.GaussianBlur(26))
        self.phone = Image.new("RGBA", (SW + 2 * BEZ, SH + 2 * BEZ), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.phone)
        d.rounded_rectangle((0, 0, SW + 2 * BEZ - 1, SH + 2 * BEZ - 1), radius=68, fill=(14, 20, 16),
                            outline=(84, 110, 86), width=3)

    # ── outside the phone ──
    def headline(self, im, t):
        cfg = self.cfg
        for name, (s, dur) in SEGS.items():
            if not s <= t < s + dur:
                continue
            lt = t - s
            out = 1 - prog(lt, dur - 0.12, 0.12) if name != "son" else 1
            if name == "giris":
                lines = cfg["giris"]["baslik"]
                size = fit(lines, 82)
                for k, line in enumerate(lines):
                    p = prog(lt, -0.05 + k * 0.18, 0.2)
                    put(im, text_img(line, font("Black", size), LIME if k == 2 else WHITE), W / 2, 238 + k * 98,
                        p * out, (1 - p) * 20)
                p = prog(lt, 1.75, 0.3)
                put(im, text_img(cfg["giris"]["alt"], font("Medium", 34), SOFT), W / 2, 548, p * out)
            elif name[0] in "hd" and name != "geri":
                n = int(name[1]) - 1
                bad = name[0] == "h"
                p = prog(lt, 0.0, 0.25)
                tag = f"HATA {n + 1}" if bad else "DOĞRUSU"
                lab = Image.new("RGBA", (W, 70), (0, 0, 0, 0))
                pill(ImageDraw.Draw(lab), W / 2, 4, tag, font("ExtraBold", 30), RED if bad else LIME,
                     WHITE if bad else INK, pad_x=30, h=62, tracking=3, anchor="m")
                put(im, lab, W / 2, 232, p * out, 0, 0.8 + 0.2 * ease(p))
                lines = cfg["hatalar"][n]["hata" if bad else "dogrusu"]
                size = fit(lines, 92 if len(lines) == 1 else 76)
                for k, line in enumerate(lines):
                    pk = prog(lt, 0.08 + k * 0.12, 0.25)
                    col = WHITE if bad or k < len(lines) - 1 else LIME
                    put(im, text_img(line, font("Black", size), col), W / 2, 318 + k * round(size * 1.12),
                        pk * out, (1 - pk) * 24)
                if bad:
                    pk = prog(lt, 0.4, 0.3)
                    put(im, text_img(cfg["hatalar"][n]["neden"], font("Medium", 32), SOFT), W / 2,
                        318 + len(lines) * round(size * 1.12) + 10, pk * out)
            elif name == "geri":
                for j, lines in enumerate(cfg["kapanis_once"]):
                    for k, line in enumerate(lines):
                        pk = prog(lt, j * 1.0 + k * 0.12, 0.25)
                        put(im, text_img(line, font("Black", 66), LIME if j else WHITE), W / 2,
                            236 + j * 170 + k * 76, pk * out, (1 - pk) * 20)

    def chart(self, im, t):
        a = prog(t, 3.1, 0.3) * (1 - prog(t, 22.8, 0.3))
        if a <= 0:
            return
        seg = next((n for n in ("h1", "d1", "h2", "d2", "h3", "d3") if SEGS[n][0] <= t < sum(SEGS[n])), None)
        if seg is None:
            seg = "d3"
        s, dur = SEGS[seg]
        bad = seg[0] == "h"
        x0, y0, x1, y1 = CHART
        card = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=26, fill=(9, 32, 17, 240),
                            outline=(218, 255, 46, 70), width=2)
        tracked(d, (22, 18), "İZLENME", font("Bold", 20), SOFT, 3)
        d.text((card.width - 22 - d.textlength("temsilî", font=font("Medium", 17)), 20), "temsilî",
               font=font("Medium", 17), fill=(150, 170, 154))
        px0, py0, px1, py1 = 22, 60, card.width - 22, card.height - 22
        ink = Image.new("RGBA", card.size, (0, 0, 0, 0))  # translucent strokes go on their own layer
        d = ImageDraw.Draw(ink)
        d.line([(px0, py1), (px1, py1)], fill=(255, 255, 255, 50), width=2)
        xp = ease(clamp((t - s - 0.15) / (dur * 0.7)))
        col = RED if bad else LIME
        if bad:
            mx = px0 + 0.2 * (px1 - px0)
            for yy in range(py0, py1, 10):
                d.line([(mx, yy), (mx, yy + 5)], fill=(255, 255, 255, 70), width=2)
            d.text((mx + 6, py0 - 2), "2. sn", font=font("Medium", 16), fill=(200, 210, 200))
        pts = []
        for j in range(61):
            x = j / 60
            if x > xp:
                break
            r = 0.12 + 0.88 / (1 + math.exp((x - 0.2) * 30)) if bad else 1 - 0.26 * x
            pts.append((px0 + x * (px1 - px0), py1 - r * (py1 - py0)))
        if len(pts) > 1:
            d.line(pts, fill=col, width=5, joint="curve")
            ex, ey = pts[-1]
            d.ellipse((ex - 7, ey - 7, ex + 7, ey + 7), fill=col)
        card.alpha_composite(ink)
        put(im, card, (x0 + x1) / 2, y0, a, (1 - a) * 14)

    def thumb(self, im, t):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        drawn = False
        for ts, _ in FEED[1:]:
            u = (t - (ts - 0.16)) / 0.42
            if 0 <= u <= 1:
                y = 1520 - 440 * ease_io(u)
                a = math.sin(math.pi * u)
                self._finger(d, 600, y, a)
                drawn = True
        for key, ts in STOPPED.items():
            u = t - (ts - 0.75)
            if 0 <= u <= 1.1:
                y = 1600 - 190 * ease(clamp(u / 0.45))
                a = clamp(u / 0.2) * (1 - clamp((u - 0.8) / 0.3))
                self._finger(d, 610, y, a)
                if u > 0.45:
                    r = 40 + 50 * ease(clamp((u - 0.45) / 0.4))
                    d.ellipse((610 - r, y - r, 610 + r, y + r), outline=(255, 255, 255, int(160 * (1 - clamp((u - 0.45) / 0.4)))),
                              width=3)
                drawn = True
        if drawn:
            im.alpha_composite(layer)

    @staticmethod
    def _finger(d, x, y, a):
        d.ellipse((x - 46, y - 46, x + 46, y + 46), fill=(255, 255, 255, int(110 * a)))
        d.ellipse((x - 46, y - 46, x + 46, y + 46), outline=(255, 255, 255, int(220 * a)), width=3)

    def ending(self, im, t):
        if t < END_AT[0]:
            return
        s = self.cfg["son"]
        put(im, self.lime_glow, W / 2, 140, 0.55 * prog(t, END_AT[0], 0.8))
        p = prog(t, END_AT[0], 0.35)
        put(im, cached("logo112", lambda: logo(112)), W / 2, 470, p, 0, 0.85 + 0.15 * p)
        title = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(title), (W / 2, 4), s["unvan"], font("Bold", 24), SOFT, 6, anchor="m")
        put(im, title, W / 2, 612, prog(t, END_AT[1], 0.35))
        colors = {"beyaz": WHITE, "lime": LIME}
        for i, (line, col) in enumerate(s["satirlar"]):
            pp = prog(t, END_AT[2 + i], 0.35)
            put(im, text_img(line, font("Black", 70), colors[col]), W / 2, 712 + i * 88, pp, (1 - pp) * 30)
        pb = prog(t, END_AT[4], 0.3)
        if pb > 0:
            btn = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
            pill(ImageDraw.Draw(btn), W / 2, 4, s["buton"], font("ExtraBold", 31), LIME, INK, pad_x=36, h=80,
                 tracking=2, anchor="m")
            put(im, btn, W / 2, 940, pb, 0, 0.8 + 0.2 * ease(pb) + 0.06 * math.sin(pb * math.pi))
        ps = prog(t, END_AT[5], 0.4)
        for i, line in enumerate(s["alt"]):
            put(im, text_img(line, font("Medium", 30), SOFT), W / 2, 1062 + i * 42, ps)
        web = Image.new("RGBA", (W, 34), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(web), (W / 2, 2), "WWW.İVEX.COM.TR", font("Bold", 22), (196, 214, 198), 6, anchor="m")
        put(im, web, W / 2, 1122 + 42 * (len(s["alt"]) - 1), ps)

    def frame(self, t):
        im = self.bg.copy()
        drop = 1300 * ease_io(prog(t, END_AT[0], 0.55))  # the phone leaves for the end card
        pa = 1 - prog(t, END_AT[0] + 0.2, 0.35)
        rise = (1 - ease(clamp(t / 0.35))) * 120  # and slides in at the start
        y = SY + drop + rise
        if pa > 0:
            put(im, self.lime_glow, W / 2, y + 180, 0.35 * pa)
            put(im, self.phone_shadow, W / 2, y - BEZ - 80, pa)
            put(im, self.phone, W / 2, y - BEZ, pa)
            scr = self.reels.screen(t)
            scr.putalpha(Image.composite(scr.getchannel("A"), Image.new("L", (SW, SH), 0), self.mask))
            put(im, scr, W / 2, y, pa)
            notch = Image.new("RGBA", (130, 30), (0, 0, 0, 0))
            ImageDraw.Draw(notch).rounded_rectangle((0, 0, 129, 29), radius=15, fill=(6, 8, 6, 255))
            put(im, notch, W / 2, y + 12, pa)
        self.chart(im, t)
        self.thumb(im, t)
        self.headline(im, t)
        self.ending(im, t)
        return im


def sound_plan():
    ev = [[0.0, "dijital", {}], [0.25, "pop", {}], [0.5, "pop", {}]]
    ev += [[ts, "kaydir", {}] for ts, _ in FEED[1:5]] + [[PASSED[f"f{k}"], "kart", {}] for k in range(5)]
    ev += [[1.75, "nota", {"i": 0}], [2.0, "yukselis", {"sure": 0.95}],
           [2.5, "rulo", {"sure": 0.45}], [3.0, "darbe", {"boy": 1.2}], [3.08, "dijital", {}]]
    ev += [[PASSED["logo"], "kart", {}], [5.75, "kaydir", {}], [6.0, "parilti", {}], [STOPPED["tabak"], "pop", {}],
           [STOPPED["tabak"], "nota", {"i": 4}]]
    ev += [[10.0, "gecis", {}], [10.08, "dijital", {}]] + [[at, "kart", {}] for at in MARKS]
    ev += [[PASSED["afis"], "kart", {}], [12.85, "kaydir", {}], [13.0, "parilti", {}], [STOPPED["kahve"], "pop", {}],
           [STOPPED["kahve"], "nota", {"i": 5}]]
    ev += [[17.0, "gecis", {}], [17.05, "dijital", {}], [PASSED["konusan"], "kart", {}], [SUB_AT, "darbe", {"boy": 0.7}]]
    ev += [[SUB_AT + 0.1 + k * 0.6, "nota", {"i": 2 + k}] for k in range(4)]
    ev += [[STOPPED["konusan"], "pop", {}], [23.0, "gecis", {}]]
    ev += [[c, "kaydir", {}] for c in CUTS[1:]]
    ev += [[24.05, "yukselis", {"sure": 0.95}], [24.55, "rulo", {"sure": 0.45}], [END_AT[0], "darbe", {"boy": 1.4}],
           [END_AT[2], "parilti", {}], [END_AT[3], "vurgu", {"i": 0}], [END_AT[4], "pop", {}]]
    parts = {"insa": (0.0, 2.88), "drop": 3.0, "ritim": (3.0, 23.0), "son": END_AT[0], "kisilma": 26.6}
    return {"bolumler": parts, "olaylar": sorted(ev, key=lambda e: e[0])}


def muffle(path, a, b):
    """'Sound off': the mix turns dull and quiet between a and b, with short crossfades."""
    x, sr = sf.read(path)
    i0, i1 = int(a * sr), int(b * sr)
    seg = x[i0:i1].copy()
    low = ses.fft_filter(seg, hi=360) * 0.5
    f = int(0.07 * sr)
    w = np.ones(len(seg))
    w[:f] = np.linspace(0, 1, f)
    w[-f:] = np.linspace(1, 0, f)
    x[i0:i1] = seg * (1 - w)[:, None] + low * w[:, None]
    sf.write(path, x, sr)


FLASH = Image.new("RGBA", (W, H), LIME + (255,))


def frames(video, hits):
    for i in range(round(TOTAL * FPS)):
        t = i / FPS
        im = video.frame(t)
        a = max([0.0] + [0.2 * size * math.exp(-(t - h) / 0.07) for h, size in hits if 0 <= t - h < 0.3])
        if a > 0.01:
            im = Image.blend(im, FLASH, a)
        yield im.convert("RGB")


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    video = Video(cfg)
    if len(sys.argv) > 2:  # preview stills
        for arg in sys.argv[2:]:
            out = repo(f"ivex-icerik/onizleme-{float(arg):05.2f}.jpg")
            video.frame(float(arg)).convert("RGB").save(out, quality=88)
            print("önizleme:", out)
        return
    plan = sound_plan()
    hits = [(at, p.get("boy", 1.0)) for at, kind, p in plan["olaylar"] if kind == "darbe"]
    out = repo(cfg["cikti"])
    silent, raw, music = (out.replace(".mp4", suffix) for suffix in ("-sessiz.mp4", "-ham.wav", "-muzik.wav"))
    write_video(frames(video, hits), silent, (W, H), FPS)
    ses.write(plan, TOTAL, raw)
    muffle(raw, *MUFFLE)
    ses.master(raw, music)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", silent, "-i", music,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    for tmp in (silent, raw, music):
        os.remove(tmp)
    print("kaydedildi:", out, "(müzikli)")
    kapak = video.frame(2.3)
    lg = logo(58)
    kapak.alpha_composite(lg, ((W - lg.width) // 2, 1730))
    kapak.convert("RGB").save(repo(cfg["kapak"]), quality=92)
    print("kaydedildi:", repo(cfg["kapak"]))


if __name__ == "__main__":
    main()
