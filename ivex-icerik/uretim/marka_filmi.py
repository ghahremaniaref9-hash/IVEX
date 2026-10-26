"""IVEX Medya - marka filmi (1080x1920, ~29 sn, sessiz; müzik Instagram'da eklenir).

Kullanım:  python3 marka_filmi.py ayarlar/marka-filmi.json
Benzetme: Instagram'ın "+" (yeni gönderi) butonu. Boş bir profilde yanıp sönen "+" dolup bir akışa dönüşür,
sonra 45 derece dönüp IVEX logosundaki X olur. Sahneler: kanca, ızgara, logo, süreç, gerçek işler,
hizmetler, kelimeler, kapanış. Sahne geçişleri 0,5 sn'lik ritme oturur; hareketli bir parça kolayca uyar.
"""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from marka import (INK, LIME, SOFT, WHITE, background, end_card, font, logo, pill, repo, rounded, tracked,
                   write_video)

W, H, FPS = 1080, 1920, 30
XF = 0.25  # cross-fade between scenes
FAINT = (255, 255, 255, 46)


def clamp(x, a=0.0, b=1.0):
    return min(max(x, a), b)


def ease(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_io(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def prog(lt, start, dur):
    return ease(clamp((lt - start) / dur))


def faded(layer, a):
    if a >= 1:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: round(v * clamp(a))))
    return out


def text_img(text, fnt, fill=WHITE, stroke=0):
    """Tight RGBA image of one line; stroke > 0 draws an outline only."""
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, b = d.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    if stroke:
        dd.text((2 - l, 2 - t), text, font=fnt, fill=(0, 0, 0, 0), stroke_width=stroke, stroke_fill=fill)
    else:
        dd.text((2 - l, 2 - t), text, font=fnt, fill=fill)
    return im


def headline(text, size, lime_dot=True):
    """White heavy line; a trailing full stop is drawn lime, like the IVEX posts."""
    f = font("Black", size)
    body = text[:-1] if lime_dot and text.endswith(".") else text
    a = text_img(body, f)
    if body == text:
        return a
    dot = text_img(".", f, LIME)
    im = Image.new("RGBA", (a.width + dot.width - 4, a.height), (0, 0, 0, 0))
    im.alpha_composite(a, (0, 0))
    im.alpha_composite(dot, (a.width - 4, a.height - dot.height))
    return im


def put(canvas, layer, cx, y, a=1.0, dy=0.0, scale=1.0):
    """Composite `layer` centred on cx with its top at y, faded by `a`, nudged by dy, scaled about its centre."""
    if a <= 0:
        return
    if scale != 1:
        layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))),
                             Image.LANCZOS)
        y += (layer.height / scale - layer.height) / 2
    canvas.alpha_composite(faded(layer, a), (round(cx - layer.width / 2), round(y + dy)))


def reveal(canvas, layer, cx, y, lt, start, dur=0.4):
    """Fade + 24 px rise in, from `start` seconds."""
    p = prog(lt, start, dur)
    put(canvas, layer, cx, y, p, (1 - p) * 24)


def cover(path, size, zoom=1.0, drift=(0.0, 0.0)):
    """Image cropped to fill `size`, optionally zoomed in and drifted (fractions of the spare room)."""
    im = ImageOps.exif_transpose(Image.open(repo(path))).convert("RGB")
    w, h = size
    s = max(w / im.width, h / im.height) * zoom
    cw, ch = w / s, h / s
    x0 = (im.width - cw) / 2 * (1 + drift[0])
    y0 = (im.height - ch) / 2 * (1 + drift[1])
    return im.resize(size, Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))


def glow(size, color, radius, strength):
    """Soft radial glow layer (RGBA) of `size`, centred."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot(xx - w / 2, yy - h / 2) / radius
    a = np.clip(np.exp(-r ** 2 * 2.2) * strength, 0, 1) * 255
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = color
    out[..., 3] = a.astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def plus_sign(size, angle=0.0, color=LIME, bar=0.2):
    """The '+' of Instagram's new-post button, rotated by `angle` degrees (45 makes it an X)."""
    big = size * 4
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    t = big * bar
    d.rounded_rectangle(((big - t) / 2, 0, (big + t) / 2, big), radius=t / 2, fill=color)
    d.rounded_rectangle((0, (big - t) / 2, big, (big + t) / 2), radius=t / 2, fill=color)
    im = im.rotate(-angle, resample=Image.BICUBIC)
    return im.resize((size, size), Image.LANCZOS)


class Film:
    def __init__(self, cfg):
        self.cfg = cfg
        self.bg = background((W, H), seed=17, glow=(0.5, 0.45)).convert("RGBA")
        dark = np.asarray(self.bg).astype(np.float32)
        dark[..., :3] *= 0.42
        self.bg_dark = Image.fromarray(dark.astype(np.uint8), "RGBA")
        self.lime_glow = glow((900, 900), LIME, 330, 0.55)
        # the logo split into its white IVE and lime X
        lg = logo(180)
        arr = np.asarray(lg).copy()
        is_x = (arr[..., 2] < 140) & (arr[..., 1] > 150)
        x_part, ive_part = arr.copy(), arr.copy()
        x_part[~is_x, 3] = 0
        ive_part[is_x, 3] = 0
        self.logo = lg
        self.logo_x = Image.fromarray(x_part, "RGBA")
        self.logo_ive = Image.fromarray(ive_part, "RGBA")
        cols = np.where(is_x.any(axis=0))[0]
        rows = np.where(is_x.any(axis=1))[0]
        self.x_box = (cols[0], rows[0], cols[-1] + 1, rows[-1] + 1)
        tw, th = 274, 365
        self.tiles = [rounded(cover(p, (tw, th)), 12) for p in cfg["izgara"]]
        self.cards = [(rounded(cover(c["dosya"], (520, 650)), 22), c["etiket"]) for c in cfg["isler"]]

    # 1 ── kanca: boş profil, yanıp sönen +
    def hook(self, lt, dur):
        im = self.bg_dark.copy()
        a, b, c = self.cfg["kanca"]
        cy = 1010
        g = 0.55 + 0.45 * ease(lt / 2.5)
        put(im, self.lime_glow, W / 2, cy - 450, g * 0.8)
        reveal(im, headline(a, 92, False), W / 2, 430, lt, 0.3)
        reveal(im, text_img(b, font("Black", 92), WHITE, stroke=3), W / 2, 545, lt, 0.9)
        # the new-post button: rounded square with a +, breathing
        pulse = 1 + 0.035 * math.sin(lt * 2 * math.pi * 1.6)
        btn = Image.new("RGBA", (190, 190), (0, 0, 0, 0))
        ImageDraw.Draw(btn).rounded_rectangle((6, 6, 184, 184), radius=48, outline=LIME, width=9)
        btn.alpha_composite(plus_sign(86, 0, LIME, 0.17), (52, 52))
        put(im, btn, W / 2, cy - 95, prog(lt, 0.1, 0.5), scale=pulse)
        stats = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(stats), (W / 2, 8), "0 GÖNDERİ  ·  0 TAKİPÇİ", font("SemiBold", 26), SOFT, 6,
                anchor="m")
        reveal(im, stats, W / 2, cy + 150, lt, 1.4)
        reveal(im, headline(c, 92), W / 2, 1330, lt, 1.8)
        return im

    # 2 ── ızgara: gönderiler tek tek düşer
    def grid(self, lt, dur):
        im = self.bg.copy()
        reveal(im, headline(self.cfg["izgara_baslik"], 84), W / 2, 150, lt, 0.0)
        n = sum(1 for i in range(9) if lt >= 0.45 + i * 0.3)
        # profile header
        head = Image.new("RGBA", (W, 170), (0, 0, 0, 0))
        d = ImageDraw.Draw(head)
        d.ellipse((128, 22, 248, 142), outline=LIME, width=6)
        d.ellipse((142, 36, 234, 128), fill=(32, 74, 40))
        d.text((282, 34), self.cfg["izgara_profil"], font=font("Bold", 38), fill=WHITE)
        d.text((282, 88), f"{n} gönderi", font=font("Medium", 30), fill=LIME if n else SOFT)
        put(im, head, W / 2, 330, prog(lt, 0.15, 0.4))
        x0, y0, tw, th, gap = 123, 540, 274, 365, 6
        for i in range(9):
            x, y = x0 + (i % 3) * (tw + gap), y0 + (i // 3) * (th + gap)
            start = 0.45 + i * 0.3
            slot = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            ImageDraw.Draw(slot).rounded_rectangle((1, 1, tw - 2, th - 2), radius=12, outline=FAINT, width=2)
            im.alpha_composite(faded(slot, prog(lt, 0.1, 0.4)), (x, y))
            p = prog(lt, start, 0.28)
            if p > 0:
                put(im, self.tiles[i], x + tw / 2, y, p, scale=1.18 - 0.18 * p)
        band = Image.new("RGBA", (W, 80), (0, 0, 0, 0))
        pill(ImageDraw.Draw(band), W / 2, 4, self.cfg["izgara_alt"], font("ExtraBold", 28), LIME, INK, pad_x=30,
             h=68, tracking=3, anchor="m")
        reveal(im, band, W / 2, 1690, lt, 3.25)
        return im

    # 3 ── logo: + döner, X olur, IVE kayarak gelir
    def logo_reveal(self, lt, dur):
        im = self.bg_dark.copy()
        lw, lh = self.logo.size
        lx, ly = (W - lw) // 2, 820
        x0, y0, x1, y1 = self.x_box
        xc, yc = lx + (x0 + x1) / 2, ly + (y0 + y1) / 2
        burst = clamp(1 - abs(lt - 1.2) / 0.9)
        if burst > 0:
            rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(rays)
            for k in range(36):
                ang = k * 10 + lt * 8
                r0, r1 = 120, 120 + 900 * ease(burst)
                ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                d.line((xc + ca * r0, yc + sa * r0, xc + ca * r1, yc + sa * r1), fill=(218, 255, 46, 70), width=3)
            im.alpha_composite(faded(rays.filter(ImageFilter.GaussianBlur(2)), burst))
        put(im, self.lime_glow, xc, yc - 450, 0.35 + 0.5 * burst)
        turn = ease_io((lt - 0.35) / 0.6)
        morph = clamp((lt - 0.95) / 0.3)
        size = round((y1 - y0) * 1.25)
        if morph < 1:
            put(im, plus_sign(size, 45 * turn, LIME, 0.2), xc, yc - size / 2, prog(lt, 0.0, 0.3) * (1 - morph))
        if morph > 0:
            put(im, self.logo_x.crop(self.x_box), xc, ly + y0, morph)
        # IVE wipes in from behind the X
        wipe = ease((lt - 1.05) / 0.55)
        if wipe > 0:
            ive = self.logo_ive.crop((0, 0, x0, lh))
            vis = round(ive.width * wipe)
            if vis > 0:
                part = ive.crop((ive.width - vis, 0, ive.width, lh))
                im.alpha_composite(part, (lx + x0 - vis, ly))
        sub = Image.new("RGBA", (W, 50), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(sub), (W / 2, 6), self.cfg["unvan"], font("Bold", 28), SOFT, 9, anchor="m")
        reveal(im, sub, W / 2, ly + lh + 60, lt, 1.75)
        return im

    # 4 ── süreç: 5 adımlık halka
    def process(self, lt, dur):
        im = self.bg.copy()
        reveal(im, headline(self.cfg["surec_baslik"], 84), W / 2, 230, lt, 0.0)
        steps = self.cfg["surec"]
        cx, cy, r = W / 2, 990, 330
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ring)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 60), width=3)
        t0, step = 0.35, 0.8
        active = int(clamp((lt - t0) / step, 0, len(steps) - 0.001))
        arc_p = clamp((lt - t0) / (step * len(steps)))
        if arc_p > 0:
            d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * ease_io(arc_p), fill=LIME, width=7)
        for k in range(len(steps)):
            ang = math.radians(-90 + k * 360 / len(steps))
            nx, ny = cx + r * math.cos(ang), cy + r * math.sin(ang)
            on = lt >= t0 + k * step
            if k == active and on:
                d.ellipse((nx - 30, ny - 30, nx + 30, ny + 30), fill=(218, 255, 46, 60))
            d.ellipse((nx - 15, ny - 15, nx + 15, ny + 15), fill=LIME if on else (12, 40, 20),
                      outline=LIME if on else (255, 255, 255, 120), width=3)
            lx, ly = cx + (r + 62) * math.cos(ang), cy + (r + 62) * math.sin(ang)
            nf = font("Bold", 26)
            num = f"0{k + 1}"
            d.text((lx - d.textlength(num, font=nf) / 2, ly - 16), num, font=nf, fill=LIME if on else SOFT)
        im.alpha_composite(faded(ring, prog(lt, 0.05, 0.4)))
        # centre text of the active step, cross-fading as it changes
        local = (lt - t0) - active * step
        a = clamp(local / 0.15) * (1 if active == len(steps) - 1 else clamp((step - local) / 0.15))
        if lt >= t0:
            name, sub = steps[active]
            counter = Image.new("RGBA", (W, 50), (0, 0, 0, 0))
            tracked(ImageDraw.Draw(counter), (W / 2, 4), f"0{active + 1} / 0{len(steps)}", font("Bold", 28), LIME,
                    6, anchor="m")
            put(im, counter, W / 2, cy - 120, a)
            put(im, text_img(name, font("Black", 84)), W / 2, cy - 55, a, (1 - a) * 14)
            put(im, text_img(sub, font("Medium", 30), SOFT), W / 2, cy + 60, a)
        foot = Image.new("RGBA", (W, 50), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(foot), (W / 2, 6), self.cfg["surec_alt"], font("Bold", 28), WHITE, 9, anchor="m")
        reveal(im, foot, W / 2, 1440, lt, 3.7)
        return im

    # 5 ── gerçek işler: kart karuseli
    def works(self, lt, dur):
        im = self.bg.copy()
        top = Image.new("RGBA", (W, 50), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(top), (W / 2, 6), self.cfg["isler_ust"], font("SemiBold", 22), SOFT, 5, anchor="m")
        reveal(im, top, W / 2, 196, lt, 0.0)
        reveal(im, headline(self.cfg["isler_baslik"], 84), W / 2, 240, lt, 0.1)
        hop = 0.55
        k = int(lt // hop)
        pos = k + ease_io((lt - k * hop - 0.25) / 0.3)  # each card holds, then glides to the next
        pos = min(pos, len(self.cards) - 1)
        cy = 1000
        order = sorted(range(len(self.cards)), key=lambda i: -abs(i - pos))
        for i in order:
            o = i - pos
            if abs(o) > 2.2:
                continue
            card, _ = self.cards[i]
            s = 1 - 0.24 * min(abs(o), 1.6)
            c = card.resize((round(card.width * s), round(card.height * s)), Image.LANCZOS)
            dim = 1 - 0.55 * min(abs(o), 1)
            if dim < 1:
                shade = Image.new("RGBA", c.size, (5, 22, 11, round(255 * (1 - dim))))
                shade.putalpha(Image.fromarray(
                    (np.asarray(c.getchannel("A")).astype(np.float32) * (1 - dim)).astype(np.uint8)))
                c = Image.alpha_composite(c, shade)
            x = W / 2 + o * 400
            put(im, c, x, cy - c.height / 2, prog(lt, 0.0, 0.35) * clamp(2.2 - abs(o)))
        centre = int(round(pos))
        label = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(label)
        txt = self.cards[centre][1]
        f = font("ExtraBold", 30)
        tw = tracked(d, (W / 2 + 16, 10), txt, f, WHITE, 5, anchor="m")
        d.ellipse((W / 2 - tw / 2 - 12, 24, W / 2 - tw / 2 + 2, 38), fill=LIME)
        put(im, label, W / 2, 1360, prog(lt, 0.2, 0.3))
        return im

    # 6 ── hizmetler: eğik kayan şeritler
    def services(self, lt, dur):
        im = self.bg_dark.copy()
        items = self.cfg["hizmetler"]
        f = font("Black", 64)
        big = Image.new("RGBA", (1900, 1500), (0, 0, 0, 0))
        active = int(clamp(lt / 0.42, 0, len(items) - 0.001))
        for j, word in enumerate(items):
            unit = word + "   •   "
            on = j == active
            strip = text_img(unit * 6, f, WHITE if on else (255, 255, 255, 255), stroke=0 if on else 2)
            if on:
                d = ImageDraw.Draw(strip)  # lime bullets on the active band
                bw = d.textlength(unit, font=f)
                dot_x = d.textlength(word + "   ", font=f)
                for r in range(6):
                    cx = 2 + r * bw + dot_x + d.textlength("•", font=f) / 2
                    d.ellipse((cx - 11, strip.height / 2 - 6, cx + 11, strip.height / 2 + 16), fill=LIME)
            speed = 150 if j % 2 else -150
            shift = (lt * speed) % (strip.width / 6)
            y = 140 + j * 180
            big.alpha_composite(faded(strip, 1 if on else 0.28), (round(-shift - 200), y))
        rot = big.rotate(10, resample=Image.BICUBIC, expand=False)
        im.alpha_composite(faded(rot, prog(lt, 0.0, 0.3)), ((W - rot.width) // 2, (H - rot.height) // 2))
        top = Image.new("RGBA", (W, 50), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(top), (W / 2, 6), self.cfg["hizmetler_ust"], font("Bold", 26), LIME, 9, anchor="m")
        put(im, top, W / 2, 150, prog(lt, 0.0, 0.3))
        return im

    # 7 ── kelimeler: harflerin içinde gerçek işler
    def words(self, lt, dur):
        im = self.bg_dark.copy()
        items = self.cfg["kelimeler"]
        each = dur / len(items)
        k = min(int(lt // each), len(items) - 1)
        local = lt - k * each
        item = items[k]
        size = 260
        while font("Black", size).getlength(item["kelime"]) > 860:
            size -= 6
        mask = text_img(item["kelime"], font("Black", size))
        fill = cover(item["dosya"], mask.size, zoom=1.25 - 0.12 * ease(local / each), drift=(0, -0.2))
        word = ImageEnhance.Brightness(fill).enhance(1.12).convert("RGBA")
        alpha = mask.getchannel("A")
        word.putalpha(alpha)
        # thin white rim so the letters read on the dark background whatever the photo inside
        rim = ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(5)), alpha).point(lambda v: v * 3 // 4)
        edge = Image.new("RGBA", mask.size, WHITE + (0,))
        edge.putalpha(rim)
        word.alpha_composite(edge)
        dot = text_img(".", font("Black", size), LIME)
        whole = Image.new("RGBA", (word.width + dot.width, word.height), (0, 0, 0, 0))
        whole.alpha_composite(word, (0, 0))
        whole.alpha_composite(dot, (word.width - 6, word.height - dot.height))
        a = clamp(local / 0.12) * clamp((each - local) / 0.12) if k < len(items) - 1 else clamp(local / 0.12)
        put(im, whole, W / 2, 860 - whole.height / 2, a, scale=1.06 - 0.06 * ease(local / 0.5))
        cap = Image.new("RGBA", (W, 50), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(cap), (W / 2, 6), item["etiket"], font("SemiBold", 24), SOFT, 7, anchor="m")
        put(im, cap, W / 2, 860 + whole.height / 2 + 50, a)
        return im

    # 8 ── kapanış
    def ending(self, lt, dur):
        if not hasattr(self, "_end"):
            s = self.cfg["son"]
            colors = {"beyaz": WHITE, "lime": LIME}
            self._end = end_card(self.bg_dark, [(t, colors[c]) for t, c in s["satirlar"]], s["buton"], s["alt"])
        im = self.bg_dark.copy()
        put(im, self.lime_glow, W / 2, 140, 0.5 * prog(lt, 0.0, 0.8))
        p = prog(lt, 0.0, 0.6)
        layer = self._end.copy()
        layer.putalpha(255)
        im.alpha_composite(faded(layer, p), (0, round((1 - p) * 30)))
        return im


SCENES = [("hook", 3.6), ("grid", 4.0), ("logo_reveal", 3.4), ("process", 4.6), ("works", 4.0),
          ("services", 3.0), ("words", 2.4), ("ending", 4.0)]


def frames(film):
    starts, t = [], 0.0
    for name, dur in SCENES:
        starts.append((t, name, dur))
        t += dur
    total = t
    for i in range(round(total * FPS)):
        t = i / FPS
        k = max(j for j, (s, _, _) in enumerate(starts) if s <= t)
        s, name, dur = starts[k]
        im = getattr(film, name)(t - s, dur)
        if k > 0 and t - s < XF:
            ps, pname, pdur = starts[k - 1]
            prev = getattr(film, pname)(t - ps, pdur)
            im = Image.blend(prev, im, (t - s) / XF)
        yield im.convert("RGB")


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    film = Film(cfg)
    if len(sys.argv) > 2:  # preview: python3 marka_filmi.py cfg.json 1.0 5.5 ... -> stills
        starts, t = {}, 0.0
        for name, dur in SCENES:
            starts[name] = (t, dur)
            t += dur
        for arg in sys.argv[2:]:
            t = float(arg)
            name = next(n for n, (s, d) in starts.items() if s <= t < s + d)
            s, d = starts[name]
            out = repo(f"ivex-icerik/onizleme-{t:05.2f}.jpg")
            getattr(film, name)(t - s, d).convert("RGB").save(out, quality=88)
            print("önizleme:", out)
        return
    write_video(frames(film), repo(cfg["cikti"]), (W, H), FPS)
    kapak = film.hook(3.2, 3.6)
    lg = logo(58)
    kapak.alpha_composite(lg, ((W - lg.width) // 2, 300))  # inside the 3:4 profile-grid crop
    kapak.convert("RGB").save(repo(cfg["kapak"]), quality=92)
    print("kaydedildi:", repo(cfg["kapak"]))


if __name__ == "__main__":
    main()
