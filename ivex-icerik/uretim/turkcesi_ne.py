"""IVEX Medya - "Türkçesi Ne?" serisi: her hafta bir reklam kelimesi, 15 saniyede, herkesin anlayacağı dille.

Kullanım:  python3 turkcesi_ne.py ../ayarlar/turkcesi-ne-01-roas.json [önizleme saniyeleri ...]
Her bölüm aynı beş adımdan oluşur ve yazılarını kendi ayar dosyasından alır:
  0-2 sn    kanca: kelime ekrana çarpar, arkasında anlaşılmaz reklam terimleri uçuşur.
  2-5 sn    Türkçesi: kelime yukarı çekilir, sade anlamı satır satır gelir (*yıldızlı* kısımlar lime).
  5-10 sn   örnek: kısa bir animasyon; ayar dosyasındaki "tur" hangisi olduğunu seçer (ROAS için "para").
  10-13 sn  asıl mesele: işletme sahibinin "doğru" diyeceği cümle.
  13-16 sn  kapanış: IVEX logosu, DM çağrısı, seri notu.
Seslendirme yok; müzik ve efektler ses.py'den, aynı zaman çizelgesiyle üretilir. Kapak ayrı çizilir ve
bütün bölümlerde aynı düzendedir, böylece profilde seri olarak görünür.
"""
import json
import math
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import ses
from marka import INK, LIME, SOFT, WHITE, background, font, logo, pill, repo, tracked, write_video
from marka_filmi import clamp, ease, ease_io, faded, glow, prog, put, text_img

W, H, FPS = 1080, 1920, 30
TOTAL = 16.0
DROP = 2.0  # the plain-Turkish answer lands here
TR_AT = (2.35, 2.85, 3.35, 3.85)
EX0, EX1 = 5.0, 10.0  # example
NOTE_IN, NOTE_DROP = 5.15, 5.5
OUT_AT = (6.5, 7.0, 7.5, 8.0)  # one note per beat
RESULT_AT = 8.5
POINT0 = 10.0
SUCK, CHING, ASK = 11.0, 11.4, 11.5
END_AT = (13.0, 13.4, 13.7, 14.1, 14.4, 14.6)  # logo, line 1, line 2, sub, button, series note
HEART = (237, 73, 86)
_cache = {}


def cached(key, make):
    if key not in _cache:
        _cache[key] = make()
    return _cache[key]


def rich(line, size, base=WHITE, accent=LIME):
    """One heavy line; the parts between *stars* are drawn in the accent colour."""
    f = font("Black", size)
    parts = line.split("*")
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    widths = [d.textlength(p, font=f) for p in parts]
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (round(sum(widths)) + 8, asc + desc + 8), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    x = 4
    for i, p in enumerate(parts):
        dd.text((x, 4), p, font=f, fill=accent if i % 2 else base)
        x += widths[i]
    return im


def fit(lines, size, width=960):
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    while size > 36 and max(d.textlength(l.replace("*", ""), font=font("Black", size)) for l in lines) > width:
        size -= 2
    return size


def thousands(n):
    return f"{n:,}".replace(",", ".")


def banknote(w, h):
    def make():
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        r = round(h * 0.12)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=LIME)
        m = round(h * 0.09)
        d.rounded_rectangle((m, m, w - 1 - m, h - 1 - m), radius=r // 2, outline=INK, width=max(2, h // 40))
        cr = h * 0.3
        d.ellipse((w / 2 - cr, h / 2 - cr, w / 2 + cr, h / 2 + cr), outline=INK, width=max(3, h // 30))
        f = font("Black", round(h * 0.38))
        d.text((w / 2 - d.textlength("₺", font=f) / 2, h / 2 - f.size * 0.62), "₺", font=f, fill=INK)
        s = font("Black", round(h * 0.16))
        d.text((m * 2, m * 1.6), "1.000", font=s, fill=INK)
        d.text((w - m * 2 - d.textlength("1.000", font=s), h - m * 1.6 - s.size * 1.1), "1.000", font=s, fill=INK)
        return im
    return cached(("note", w, h), make)


def heart(size):
    def make():
        big = size * 4
        im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        r = big * 0.27
        d.ellipse((big * 0.5 - 2 * r, big * 0.18, big * 0.5, big * 0.18 + 2 * r), fill=HEART)
        d.ellipse((big * 0.5, big * 0.18, big * 0.5 + 2 * r, big * 0.18 + 2 * r), fill=HEART)
        d.polygon([(big * 0.5 - 2 * r + big * 0.02, big * 0.18 + r * 1.25), (big * 0.5 + 2 * r - big * 0.02, big * 0.18 + r * 1.25),
                   (big * 0.5, big * 0.92)], fill=HEART)
        return im.resize((size, size), Image.LANCZOS)
    return cached(("heart", size), make)


def register():
    """A flat cash register in the IVEX colours."""
    def make():
        w, h = 400, 340
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((120, 20, 280, 120), radius=18, fill=LIME)
        f = font("Black", 64)
        d.text((200 - d.textlength("₺", font=f) / 2, 30), "₺", font=f, fill=INK)
        d.rectangle((185, 120, 215, 160), fill=LIME)
        d.rounded_rectangle((24, 150, 376, 300), radius=26, fill=(9, 32, 17), outline=LIME, width=6)
        for r in range(3):
            for c in range(4):
                x, y = 60 + c * 58, 172 + r * 34
                d.rounded_rectangle((x, y, x + 42, y + 22), radius=6, outline=LIME, width=3)
        d.rounded_rectangle((300, 180, 350, 260), radius=10, fill=LIME)
        d.rounded_rectangle((10, 290, 390, 334), radius=14, fill=(9, 32, 17), outline=LIME, width=6)
        d.rounded_rectangle((170, 304, 230, 318), radius=6, fill=LIME)
        return im
    return cached("register", make)


class Episode:
    def __init__(self, cfg):
        self.cfg = cfg
        bg = background((W, H), seed=31, glow=(0.5, 0.45)).convert("RGBA")
        a = np.asarray(bg).astype(np.float32)
        a[..., :3] *= 0.45
        self.bg = Image.fromarray(a.astype(np.uint8), "RGBA")
        self.lime_glow = glow((900, 900), LIME, 330, 0.5)
        # jargon floats in a band above and below the word, two per row, never over the text
        rng = np.random.default_rng(13)
        self.jargon = []
        rows = (360, 455, 1270, 1365, 1460, 1555)
        for i, y in enumerate(rows):
            for side in (0, 1):
                word = cfg["jargon"][(2 * i + side) % len(cfg["jargon"])]
                img = text_img(word, font("ExtraBold", int(rng.integers(36, 62))), (220, 235, 222))
                room = 1080 / 2 - 70 - img.width
                x = (70 + img.width / 2 + rng.uniform(0, max(room, 0))) if side == 0 else \
                    (1010 - img.width / 2 - rng.uniform(0, max(room, 0)))
                self.jargon.append((img, x, y, rng.uniform(0.2, 0.45), rng.uniform(-14, 14), rng.uniform(0, 6.28)))
        self.word = text_img(cfg["kelime"], font("Black", 240))
        self.qmark = text_img("?", font("Black", 240), LIME)
        rng = np.random.default_rng(7)
        self.hearts = [(rng.uniform(140, 940), POINT0 + i * 0.06, rng.uniform(560, 820), int(rng.integers(54, 104)),
                        rng.uniform(0, 6.28)) for i in range(16)]

    # ── always on: the series badge ──
    @staticmethod
    def outline_pill(text):
        def make():
            f = font("ExtraBold", 28)
            dd = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
            tw = sum(dd.textlength(c, font=f) for c in text) + 3 * (len(text) - 1)
            b = Image.new("RGBA", (round(tw) + 64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(b)
            d.rounded_rectangle((2, 2, b.width - 3, 61), radius=30, outline=LIME, width=3)
            tracked(d, (32, 15), text, f, LIME, 3)
            return b
        return cached(("pill", text), make)

    def badge(self, im, t):
        a = prog(t, 0.05, 0.25) * (1 - prog(t, END_AT[0] - 0.2, 0.2))
        if a > 0:
            put(im, self.outline_pill(f"{self.cfg['seri']}  #{self.cfg['bolum']}"), W / 2, 232, a)

    # ── 0-2 s: the word hits the screen in a cloud of jargon ──
    def hook(self, im, t):
        if t >= EX0:
            return
        cloud = 1 - prog(t, DROP, 0.4)
        for img, x, y, speed, drift, ph in self.jargon:
            if cloud <= 0:
                break
            put(im, img, x + drift * math.sin(t * 0.8 + ph), y - 40 * t * speed, 0.2 * cloud * prog(t, 0.0, 0.3))
        # the big word: slams in, then moves up as the subject of the answer
        p = clamp(t / 0.18)
        mv = ease_io(clamp((t - DROP) / 0.35))
        scale = (1.5 - 0.5 * ease(p)) * (1 - 0.42 * mv)
        shake = 16 * math.sin(t * 55) * math.exp(-t / 0.12)
        y = 700 + (330 - 700) * mv
        out = 1 - prog(t, EX0 - 0.2, 0.2)
        q = max(0.0, prog(t, 0.25, 0.15) * (1 - prog(t, DROP, 0.2)))
        ww = self.word.width + (self.qmark.width if q > 0 else 0)
        x0 = W / 2 - ww * scale / 2 + shake
        put(im, self.word, x0 + self.word.width * scale / 2, y, clamp(t / 0.08) * out, 0, scale)
        if q > 0:
            qm = self.qmark.rotate(10 * math.sin(t * 7), expand=True, resample=Image.BICUBIC)
            put(im, qm, x0 + (self.word.width + self.qmark.width / 2) * scale, y, q, 0, scale)
        # the question underneath
        size = fit(self.cfg["kanca"], 64)
        for k, line in enumerate(self.cfg["kanca"]):
            pk = prog(t, 0.5 * (k + 1), 0.25) * (1 - prog(t, DROP, 0.2))
            put(im, text_img(line, font("Black", size), LIME if k else WHITE), W / 2, 1010 + k * 84, pk, (1 - pk) * 20)

    # ── 2-5 s: the plain-Turkish answer ──
    def answer(self, im, t):
        if not DROP <= t < EX0:
            return
        out = 1 - prog(t, EX0 - 0.2, 0.2)
        tag = Image.new("RGBA", (W, 70), (0, 0, 0, 0))
        pill(ImageDraw.Draw(tag), W / 2, 4, "TÜRKÇESİ", font("ExtraBold", 30), LIME, INK, pad_x=30, h=62, tracking=4,
             anchor="m")
        p = prog(t, DROP + 0.2, 0.25)
        put(im, tag, W / 2, 610, p * out, 0, 0.8 + 0.2 * ease(p))
        lines = self.cfg["turkcesi"]
        size = fit(lines, 80)
        for k, (line, at) in enumerate(zip(lines, TR_AT)):
            pk = prog(t, at, 0.3)
            put(im, rich(line, size), W / 2, 712 + k * round(size * 1.18), pk * out, (1 - pk) * 26)

    # ── 5-10 s: the example (ROAS: money in, more money out) ──
    def example(self, im, t):
        if not EX0 <= t < EX1:
            return
        ex = self.cfg["ornek"]
        out = 1 - prog(t, EX1 - 0.2, 0.2)
        a0 = prog(t, EX0, 0.3) * out
        n = ex["cikan"] // ex["giren"]
        # what goes in
        lab = 1 - prog(t, NOTE_DROP + 0.1, 0.3)
        put(im, text_img(f"{thousands(ex['giren'])} TL", font("Black", 76)), W / 2, 330, prog(t, NOTE_IN, 0.3) * lab)
        lt = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(lt), (W / 2, 2), ex["giren_etiket"], font("Bold", 28), SOFT, 6, anchor="m")
        put(im, lt, W / 2, 428, prog(t, NOTE_IN + 0.1, 0.3) * lab)
        # the box the money goes through
        shake = 10 * math.sin(t * 48) * math.exp(-max(0.0, t - NOTE_DROP - 0.4) / 0.15) if t > NOTE_DROP + 0.4 else 0
        box = cached("box", lambda: self._box(ex["giren_etiket"]))
        put(im, box, W / 2 + shake, 760, a0)
        # the note dropping in
        u = ease_io(clamp((t - NOTE_DROP) / 0.4))
        if t < NOTE_DROP + 0.4:
            y = 488 + (790 - 488) * u
            vis = prog(t, NOTE_IN, 0.3) * (1 - clamp((y - 700) / 90))
            put(im, banknote(300, 150), W / 2, y, vis, 0, 1 - 0.3 * u)
        # notes coming out, one per beat, into a fan
        xs = [W / 2 + (k - (n - 1) / 2) * 150 for k in range(n)]
        for k, at in enumerate(OUT_AT[:n]):
            if t < at:
                continue
            v = ease(clamp((t - at) / 0.35))
            x = W / 2 + (xs[k] - W / 2) * v
            y = 940 + (1150 - 940) * v - 60 * math.sin(math.pi * v)
            ang = (k - (n - 1) / 2) * -7 * v
            nb = banknote(230, 115).rotate(ang, expand=True, resample=Image.BICUBIC)
            put(im, nb, x, y, out * clamp((t - at) / 0.1), 0, 0.6 + 0.4 * v)
        got = sum(t >= at for at in OUT_AT[:n])
        if got:
            amount = ex["giren"] * got
            pa = prog(t, OUT_AT[0], 0.3) * out
            bump = 1 + 0.12 * math.exp(-(t - OUT_AT[got - 1]) / 0.08)
            put(im, text_img(f"{thousands(amount)} TL", font("Black", 92), LIME), W / 2, 1310, pa, 0, bump)
            lt2 = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
            tracked(ImageDraw.Draw(lt2), (W / 2, 2), ex["cikan_etiket"], font("Bold", 30), SOFT, 6, anchor="m")
            put(im, lt2, W / 2, 1418, pa)
            put(im, text_img(ex["not"], font("Medium", 24), (160, 180, 164)), W / 2, 1476, pa * 0.9)
        # the result
        pr = prog(t, RESULT_AT, 0.25) * out
        if pr > 0:
            put(im, text_img(ex["sonuc"], font("Black", 150), LIME), W / 2, 350, pr, 0, 1.25 - 0.25 * ease(pr))
            put(im, text_img(ex["aciklama"], font("Medium", 40)), W / 2, 548, prog(t, RESULT_AT + 0.25, 0.3) * out)

    @staticmethod
    def _box(label):
        im = Image.new("RGBA", (460, 250), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((10, 30, 450, 240), radius=34, fill=(9, 32, 17), outline=LIME, width=5)
        d.rounded_rectangle((130, 18, 330, 42), radius=12, fill=(4, 14, 8), outline=LIME, width=4)
        tracked(d, (230, 112), label, font("ExtraBold", 40), LIME, 8, anchor="m")
        return im

    # ── 10-13 s: likes are nice, but what went into the till? ──
    def point(self, im, t):
        if not POINT0 <= t < END_AT[0]:
            return
        m = self.cfg["mesele"]
        out = 1 - prog(t, END_AT[0] - 0.2, 0.2)
        put(im, text_img(m["once"], font("Black", 88)), W / 2, 380, prog(t, POINT0 + 0.05, 0.3) * out)
        ra = prog(t, SUCK - 0.1, 0.3) * out
        bump = 1 + 0.15 * math.exp(-(t - CHING) / 0.1) if t >= CHING else 1
        put(im, register(), W / 2, 930, ra, 0, bump)
        if t >= CHING:  # ka-ching sparks, on their own layer so they can fade
            sparks = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(sparks)
            s = clamp((t - CHING) / 0.35)
            for k in range(8):
                ang = k * math.pi / 4
                r0, r1 = 230 + 40 * s, 260 + 90 * s
                cx, cy = W / 2, 1090
                d.line([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)),
                        (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))], fill=LIME + (int(255 * (1 - s)),),
                       width=6)
            im.alpha_composite(sparks)
        for x, start, speed, size, ph in self.hearts:
            if t < start:
                continue
            y = 1760 - (t - start) * speed
            xx = x + 34 * math.sin((t - start) * 3 + ph)
            a = clamp((t - start) / 0.2)
            sc = 1.0
            if t >= SUCK:  # pulled into the register
                v = ease_io(clamp((t - SUCK) / 0.4))
                ys = 1760 - (SUCK - start) * speed
                xs = x + 34 * math.sin((SUCK - start) * 3 + ph)
                xx, y = xs + (W / 2 - xs) * v, ys + (1060 - ys) * v
                sc, a = 1 - 0.8 * v, a * (1 - v)
            if a > 0.01:
                put(im, heart(size), xx, y, a * out, 0, sc)
        put(im, text_img(m["ara"], font("Medium", 46), SOFT), W / 2, 512, prog(t, SUCK, 0.3) * out)
        pq = prog(t, ASK, 0.25)
        put(im, text_img(m["vurgu"], font("Black", 100), LIME), W / 2, 584, pq * out, 0, 1.2 - 0.2 * ease(pq))

    # ── 13-16 s: close ──
    def ending(self, im, t):
        if t < END_AT[0]:
            return
        s = self.cfg["son"]
        put(im, self.lime_glow, W / 2, 140, 0.55 * prog(t, END_AT[0], 0.8))
        p = prog(t, END_AT[0], 0.35)
        put(im, cached("logo", lambda: logo(112)), W / 2, 470, p, 0, 0.85 + 0.15 * p)
        colors = {"beyaz": WHITE, "lime": LIME}
        size = fit([l for l, _ in s["satirlar"]], 78)
        for i, (line, col) in enumerate(s["satirlar"]):
            pp = prog(t, END_AT[1 + i], 0.35)
            put(im, text_img(line, font("Black", size), colors[col]), W / 2, 660 + i * round(size * 1.15), pp,
                (1 - pp) * 30)
        put(im, text_img(s["alt"], font("Medium", 38), SOFT), W / 2, 858, prog(t, END_AT[3], 0.35))
        pb = prog(t, END_AT[4], 0.3)
        if pb > 0:
            btn = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
            pill(ImageDraw.Draw(btn), W / 2, 4, s["buton"], font("ExtraBold", 31), LIME, INK, pad_x=36, h=80,
                 tracking=2, anchor="m")
            put(im, btn, W / 2, 940, pb, 0, 0.8 + 0.2 * ease(pb) + 0.06 * math.sin(pb * math.pi))
        ps = prog(t, END_AT[5], 0.4)
        note = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(note), (W / 2, 4), s["seri_notu"], font("Bold", 24), LIME, 5, anchor="m")
        put(im, note, W / 2, 1076, ps)
        web = Image.new("RGBA", (W, 34), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(web), (W / 2, 2), "WWW.İVEX.COM.TR", font("Bold", 22), (196, 214, 198), 6, anchor="m")
        put(im, web, W / 2, 1124, ps)

    def frame(self, t):
        im = self.bg.copy()
        self.badge(im, t)
        self.hook(im, t)
        self.answer(im, t)
        self.example(im, t)
        self.point(im, t)
        self.ending(im, t)
        return im

    def cover(self):
        """Same layout for every episode, so the series reads as one row on the profile."""
        im = self.bg.copy()
        put(im, self.lime_glow, W / 2, 420, 0.5)
        put(im, self.outline_pill(f"#{self.cfg['bolum']}"), W / 2, 470)  # inside the 3:4 profile-grid crop
        put(im, text_img(self.cfg["kelime"], font("Black", fit([self.cfg["kelime"]], 250))), W / 2, 580)
        put(im, text_img("Türkçesi ne?", font("Black", 92), LIME), W / 2, 880)
        put(im, text_img("15 saniyede, herkesin anlayacağı dille", font("Medium", 36), SOFT), W / 2, 1020)
        lg = logo(58)
        im.alpha_composite(lg, ((W - lg.width) // 2, 1560))
        return im


def sound_plan():
    ev = [[0.0, "boom", {}], [0.25, "pop", {}], [0.5, "whoosh", {"sure": 0.4}], [1.0, "whoosh", {"sure": 0.4}],
          [1.0, "yukselis", {"sure": 0.95}], [1.5, "rulo", {"sure": 0.45}], [DROP, "darbe", {"boy": 1.1}]]
    ev += [[at, "nota", {"i": 2 * k}] for k, at in enumerate(TR_AT)]
    ev += [[EX0, "gecis", {}], [NOTE_DROP, "kaydir", {}], [NOTE_DROP + 0.4, "kart", {}]]
    ev += [[at, "nota", {"i": 4 + k}] for k, at in enumerate(OUT_AT)]
    ev += [[RESULT_AT, "darbe", {"boy": 0.9}], [RESULT_AT + 0.05, "parilti", {}]]
    ev += [[POINT0, "gecis", {}], [SUCK + 0.35, "kaydir", {}], [CHING, "pop", {}], [ASK, "vurgu", {"i": 0}]]
    ev += [[END_AT[0] - 0.95, "yukselis", {"sure": 0.95}], [END_AT[0] - 0.45, "rulo", {"sure": 0.45}],
           [END_AT[0], "darbe", {"boy": 1.3}], [END_AT[1], "parilti", {}], [END_AT[2], "vurgu", {"i": 1}],
           [END_AT[4], "pop", {}]]
    parts = {"insa": (0.0, DROP - 0.12), "drop": DROP, "ritim": (DROP, END_AT[0] - 0.5), "son": END_AT[0],
             "kisilma": 14.8}
    return {"bolumler": parts, "olaylar": sorted(ev, key=lambda e: e[0])}


FLASH = Image.new("RGBA", (W, H), LIME + (255,))


def frames(ep, hits):
    for i in range(round(TOTAL * FPS)):
        t = i / FPS
        im = ep.frame(t)
        a = max([0.0] + [0.2 * size * math.exp(-(t - h) / 0.07) for h, size in hits if 0 <= t - h < 0.3])
        if a > 0.01:
            im = Image.blend(im, FLASH, a)
        yield im.convert("RGB")


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    ep = Episode(cfg)
    if len(sys.argv) > 2:  # preview stills
        for arg in sys.argv[2:]:
            out = repo(f"ivex-icerik/onizleme-{float(arg):05.2f}.jpg")
            ep.frame(float(arg)).convert("RGB").save(out, quality=88)
            print("önizleme:", out)
        return
    out = repo(cfg["cikti"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plan = sound_plan()
    hits = [(at, p.get("boy", 1.0)) for at, kind, p in plan["olaylar"] if kind == "darbe"]
    silent, raw, music = (out.replace(".mp4", suffix) for suffix in ("-sessiz.mp4", "-ham.wav", "-muzik.wav"))
    write_video(frames(ep, hits), silent, (W, H), FPS)
    ses.write(plan, TOTAL, raw)
    ses.master(raw, music)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", silent, "-i", music,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    for tmp in (silent, raw, music):
        os.remove(tmp)
    print("kaydedildi:", out, "(müzikli)")
    ep.cover().convert("RGB").save(repo(cfg["kapak"]), quality=92)
    print("kaydedildi:", repo(cfg["kapak"]))


if __name__ == "__main__":
    main()
