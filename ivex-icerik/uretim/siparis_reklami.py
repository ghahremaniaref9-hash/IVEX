"""IVEX Medya - "Siparişlerin Türkiye'nin dört bir yanına" Reels reklamı (1080x1920, 15 sn, kendi müziğiyle).

Kullanım:  python3 siparis_reklami.py ../ayarlar/siparis-reklami.json [önizleme saniyeleri ...]
Akış:
  0-3 sn   kanca; Türkiye haritası noktalar halinde batıdan doğuya belirir.
  3-8 sn   haritanın ortasında işletme noktası; altı şehre ışıklı yollar, uçlarında paket ve sipariş bildirimi.
  8-12 sn  yollar çoğalır, harita merkezden dışa doğru yanar, temsili sipariş sayacı.
  12-15 sn IVEX kapanışı.
Harita il sınırlarından (kaynak/harita/tr-iller.json) çizilir. Kamera haritaya eğik bir açıdan bakar; yollar
haritanın üstünde yükselen yaylar olarak gerçek perspektifte çizilir. Kesmeler 120 BPM ızgarasındadır;
müzik (ses.py) aynı zaman çizelgesinden üretilir.
"""
import json
import math
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import ses
from marka import INK, LIME, SOFT, WHITE, background, font, logo, pill, repo, tracked, write_video
from marka_filmi import clamp, ease, ease_io, faded, glow, headline, prog, put, text_img

W, H, FPS = 1080, 1920, 30
TOTAL = 15.0
BEAT = ses.BEAT
HOOK_AT = (0.5, 1.0, 1.5)  # hook lines
DROP = 3.0  # the business dot lands
LAUNCH0, LAUNCH_STEP, FLIGHT = 3.5, 0.5, 0.5  # one city per beat, each route lands on the next beat
GROW = 8.0  # routes multiply
MSG_AT = (8.0, 8.5, 9.0)
COUNT_AT, COUNT_DUR = 8.5, 3.0
END = 12.0
END_AT = (12.0, 12.25, 12.5, 13.0, 13.5, 13.75)  # logo, title, line 1, line 2, button, small print

LAT0, LON0 = 39.0, 35.2
KX = math.cos(math.radians(LAT0))
UNIT = 64.0  # px per projected degree at zoom 1
DIST = 1700.0  # camera distance (px) for the perspective
LAND = (14, 46, 25, 255)
DIM_DOT = np.array((196, 222, 200), np.float32)
LIME_F = np.array(LIME, np.float32)
GLOW_SCALE = 0.5

# camera keys: time, zoom, focus x, focus y (projected units), tilt (degrees), screen y of the focus
KEYS = [(0.0, 1.12, -0.4, 0.2, 40, 1250), (3.0, 1.04, 0.0, 0.0, 31, 1180), (8.0, 1.0, 0.0, 0.0, 28, 1150),
        (12.0, 0.95, 0.0, 0.0, 25, 1140), (12.8, 0.92, 0.0, 0.0, 30, 1500), (15.0, 0.9, 0.0, 0.0, 31, 1520)]


def project(lon, lat):
    return np.stack([(np.asarray(lon, np.float64) - LON0) * KX, np.asarray(lat, np.float64) - LAT0], -1)


class Camera:
    """Looks at the map plane from above at `tilt`: the north recedes, the south comes closer."""

    def __init__(self, t):
        k = next((i for i in range(len(KEYS) - 1) if t <= KEYS[i + 1][0]), len(KEYS) - 2)
        (t0, *a), (t1, *b) = KEYS[k], KEYS[k + 1]
        u = ease_io(clamp((t - t0) / (t1 - t0)))
        z, fx, fy, tilt, ay = (x + (y - x) * u for x, y in zip(a, b))
        if t >= DROP:
            z *= 1 + 0.035 * math.exp(-(t - DROP) / 0.18)  # punch on the drop
        fx += 0.10 * math.sin(t * 0.55)
        self.s, self.f, self.ay = UNIT * z, np.array((fx, fy)), ay
        self.sin, self.cos = math.sin(math.radians(tilt)), math.cos(math.radians(tilt))

    def screen(self, p, h=0.0):
        """Map points (N, 2) lifted `h` px off the plane -> screen points (N, 2) and their local scale (N,)."""
        p = np.atleast_2d(p)
        x = (p[:, 0] - self.f[0]) * self.s
        y = (p[:, 1] - self.f[1]) * self.s
        h = np.broadcast_to(np.asarray(h, np.float64), x.shape)
        depth = DIST + y * self.sin - h * self.cos
        k = DIST / depth
        return np.stack([W / 2 + x * k, self.ay - (y * self.cos + h * self.sin) * k], -1), k


class TurkeyMap:
    def __init__(self, path):
        with open(repo(path), encoding="utf-8") as fh:
            feats = json.load(fh)["features"]
        self.rings, self.provinces = [], {}
        for f in feats:
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            rings = [project(*np.asarray(poly[0]).T) for poly in polys if len(poly[0]) >= 4]
            self.rings += rings
            big = max(rings, key=len)
            self.provinces[f["properties"]["name"]] = big.mean(axis=0)
        pts = np.concatenate(self.rings)
        x0, y0 = pts.min(0)
        x1, y1 = pts.max(0)
        # dot grid inside the land, from a rasterised mask
        res = 60
        mask = Image.new("L", (math.ceil((x1 - x0) * res) + 2, math.ceil((y1 - y0) * res) + 2), 0)
        d = ImageDraw.Draw(mask)
        for r in self.rings:
            d.polygon([((x - x0) * res, (y1 - y) * res) for x, y in r], fill=255)
        step = 0.125
        gx, gy = np.meshgrid(np.arange(x0 + step / 2, x1, step), np.arange(y0 + step / 2, y1, step))
        m = np.asarray(mask)[((y1 - gy) * res).astype(int), ((gx - x0) * res).astype(int)] > 0
        self.dots = np.stack([gx[m], gy[m]], -1)
        self.x0, self.x1 = x0, x1
        rng = np.random.default_rng(5)
        self.jitter = rng.random(len(self.dots))


class Route:
    """A light trail from `a` to `b` (projected units) that rises off the map as an arc."""

    def __init__(self, a, b, start, flight, main=False):
        self.a, self.b = np.asarray(a), np.asarray(b)
        self.start, self.flight, self.main = start, flight, main
        self.arrive = start + flight
        self.lift = 0.30 * float(np.hypot(*(self.b - self.a)))  # arc height as a share of its length

    def points(self, cam, u0, u1, n=40):
        u = np.linspace(u0, u1, n)
        p = self.a[None] + (self.b - self.a)[None] * u[:, None]
        return cam.screen(p, self.lift * cam.s * np.sin(np.pi * u))[0]


def package_icon(size, outline_only=False, color=INK):
    """Isometric parcel: lime faces (or just INK lines for the notification badge)."""
    big = size * 4
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, w, hh, side, y0 = big / 2, big * 0.40, big * 0.21, big * 0.36, big * 0.12
    top = [(cx, y0), (cx + w, y0 + hh), (cx, y0 + 2 * hh), (cx - w, y0 + hh)]
    left = [(cx - w, y0 + hh), (cx, y0 + 2 * hh), (cx, y0 + 2 * hh + side), (cx - w, y0 + hh + side)]
    right = [(cx, y0 + 2 * hh), (cx + w, y0 + hh), (cx + w, y0 + hh + side), (cx, y0 + 2 * hh + side)]
    tape = [(cx - w / 2 - big * 0.05, y0 + hh / 2 + big * 0.02), (cx - w / 2 + big * 0.05, y0 + hh / 2 - big * 0.02),
            (cx + w / 2 + big * 0.05, y0 + 1.5 * hh - big * 0.02), (cx + w / 2 - big * 0.05, y0 + 1.5 * hh + big * 0.02)]
    lw = max(2, round(big * 0.045))
    if outline_only:
        for face in (top, left, right):
            d.line(face + [face[0]], fill=color, width=lw, joint="curve")
        mid = [((tape[0][0] + tape[1][0]) / 2, (tape[0][1] + tape[1][1]) / 2),
               ((tape[2][0] + tape[3][0]) / 2, (tape[2][1] + tape[3][1]) / 2)]
        d.line(mid, fill=color, width=lw)
    else:
        d.polygon(top, fill=(232, 255, 120))
        d.polygon(left, fill=(150, 196, 30))
        d.polygon(right, fill=(190, 232, 40))
        d.polygon(tape, fill=(250, 255, 215))
        for face in (top, left, right):
            d.line(face + [face[0]], fill=(10, 30, 14, 160), width=max(1, lw // 2))
    return im.resize((size, size), Image.LANCZOS)


def notice_card(title, city):
    w, h = 840, 116
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=32, fill=(9, 32, 17, 238), outline=(218, 255, 46, 70), width=2)
    d.rounded_rectangle((22, 22, 94, 94), radius=20, fill=LIME)
    icon = package_icon(56, outline_only=True)
    im.alpha_composite(icon, (30, 28))
    d.text((120, 24), title, font=font("Bold", 31), fill=WHITE)
    d.text((120, 66), f"{city} · şimdi", font=font("Medium", 25), fill=SOFT)
    plus = font("ExtraBold", 36)
    d.text((w - 34 - d.textlength("+1", font=plus), 36), "+1", font=plus, fill=LIME)
    return im


def thousands(n):
    return f"{n:,}".replace(",", ".")


class Ad:
    def __init__(self, cfg):
        self.cfg = cfg
        bg = background((W, H), seed=23, glow=(0.5, 0.55)).convert("RGBA")
        dark = np.asarray(bg).astype(np.float32)
        dark[..., :3] *= 0.45
        self.bg = Image.fromarray(dark.astype(np.uint8), "RGBA")
        self.lime_glow = glow((900, 900), LIME, 330, 0.5)
        self.map = TurkeyMap(cfg["harita"])
        self.origin = project(*cfg["merkez"]["konum"])
        self.d0 = np.hypot(*(self.map.dots - self.origin).T)
        # the six named cities, one per beat
        self.cities = []
        for i, (name, lon, lat) in enumerate(cfg["sehirler"]):
            r = Route(self.origin, project(lon, lat), LAUNCH0 + i * LAUNCH_STEP, FLIGHT, main=True)
            label = text_img(name.upper(), font("Bold", 23))
            self.cities.append((name, r, label, notice_card(cfg["bildirim"], name)))
        main_names = {c[0] for c in cfg["sehirler"]}
        others = [(n, p) for n, p in self.map.provinces.items() if n not in main_names]
        rng = np.random.default_rng(11)
        rng.shuffle(others)
        self.growth = []
        n = len(others)
        for i, (name, p) in enumerate(others):
            start = GROW + 0.15 + 3.0 * (i / n) ** 0.55  # ever faster: the network multiplies
            src = self.origin if i % 3 else self.cities[i % len(self.cities)][1].b  # some hop city to city
            self.growth.append(Route(src, p, start, 0.42))
        self.near_main = [np.hypot(*(self.map.dots - c[1].b).T) for c in self.cities]
        self.near_growth = [np.hypot(*(self.map.dots - r.b).T) for r in self.growth]
        self.parcel = package_icon(64)
        self.plus_one = text_img("+1", font("ExtraBold", 34), LIME)
        self.origin_chip = self._chip(cfg["merkez"]["etiket"])
        self.hook = [headline(cfg["kanca"][0], 100, False), text_img(cfg["kanca"][1], font("Black", 100), LIME),
                     headline(cfg["kanca"][2], 100, False)]
        m = cfg["mesaj"]
        self.message = [headline(m[0], 98, False), headline(m[1], 98, False), text_img(m[2], font("Black", 98), LIME)]
        self.logo = logo(112)
        self.counter_bg = self._counter_bg()

    @staticmethod
    def _chip(text):
        f = font("ExtraBold", 24)
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        w = round(sum(d.textlength(c, font=f) for c in text) + 3 * (len(text) - 1) + 44)
        im = Image.new("RGBA", (w, 50), (0, 0, 0, 0))
        pill(ImageDraw.Draw(im), 0, 0, text, f, LIME, INK, pad_x=22, h=50, tracking=3)
        return im

    def _counter_bg(self):
        w, h = 640, 150
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=(9, 32, 17, 238), outline=(218, 255, 46, 70), width=2)
        tracked(d, (34, 28), self.cfg["sayac"]["etiket"], font("Bold", 22), SOFT, 4)
        return im

    # ── per-frame layers ─────────────────────────────────────────────────────────────────────────────
    def dot_light(self, t):
        a = np.zeros(len(self.map.dots))
        for (name, r, _, _), dist in zip(self.cities, self.near_main):
            if t > r.arrive:
                a = np.maximum(a, np.clip((0.85 - dist) / 0.5, 0, 1) * prog(t, r.arrive, 0.5))
        for r, dist in zip(self.growth, self.near_growth):
            if t > r.arrive:
                a = np.maximum(a, np.clip((0.45 - dist) / 0.3, 0, 1) * prog(t, r.arrive, 0.4))
        if t > GROW:
            reach = 9.6 * ease_io(clamp((t - GROW) / 3.6))
            a = np.maximum(a, np.clip((reach - self.d0) / 1.1, 0, 1))
        return a

    def map_layer(self, t, cam, gl):
        land = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(land)
        polys = [cam.screen(r)[0] for r in self.map.rings]
        for p in polys:
            d.polygon([tuple(q) for q in p], fill=LAND)
        mask = land.getchannel("A")
        db = ImageDraw.Draw(land, "RGBA")
        for p in polys:
            db.line([tuple(q) for q in p] + [tuple(p[0])], fill=(255, 255, 255, 24), width=1)
        # coastline / border: the edge of the land mask, crisp plus a lime glow
        edge = ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(3)))
        coast = Image.new("RGBA", (W, H), (214, 246, 150, 0))
        coast.putalpha(edge.point(lambda v: v * 200 // 255))
        land.alpha_composite(coast)
        gl.paste(ImageChops.lighter(gl, edge.resize(gl.size, Image.BILINEAR).point(lambda v: v * 150 // 255)))
        # dots: appear west to east in the hook, then light up lime with the reach
        pts, k = cam.screen(self.map.dots)
        xn = (self.map.dots[:, 0] - self.map.x0) / (self.map.x1 - self.map.x0)
        appear = np.clip((t - (0.05 + 1.15 * xn + 0.18 * self.map.jitter)) / 0.3, 0, 1)
        lit = self.dot_light(t)
        col = DIM_DOT[None] + (LIME_F - DIM_DOT)[None] * lit[:, None]
        alpha = appear * (70 + 175 * lit)
        rad = (1.55 + 0.9 * lit) * k * cam.s / UNIT
        for (x, y), c, al, r in zip(pts, col, alpha, rad):
            if al > 3:
                db.ellipse((x - r, y - r, x + r, y + r), fill=(int(c[0]), int(c[1]), int(c[2]), int(al)))
        return land

    def routes_layer(self, t, cam, gl):
        fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(fx, "RGBA")
        g = ImageDraw.Draw(gl)
        s = GLOW_SCALE
        routes = [c[1] for c in self.cities] + self.growth
        for r in routes:
            if t < r.start:
                continue
            p = ease_io(clamp((t - r.start) / r.flight))
            pts = r.points(cam, 0.0, max(p, 0.02))
            width = 4 if r.main else 3
            core = 235 if r.main else 170
            if t > r.arrive:  # settle to a quieter trail
                core = round(core * (1 - 0.45 * prog(t, r.arrive, 0.8)))
            line = [tuple(q) for q in pts]
            d.line(line, fill=(218, 255, 46, core), width=width, joint="curve")
            g.line([(x * s, y * s) for x, y in line], fill=190 if r.main else 120, width=5 if r.main else 3)
            if p < 1:  # glowing head with an arrow tip
                hx, hy = pts[-1]
                dx, dy = pts[-1] - pts[-3]
                n = math.hypot(dx, dy) or 1
                dx, dy = dx / n, dy / n
                sz = 16 if r.main else 11
                tip = [(hx + dx * sz, hy + dy * sz), (hx - dy * sz * 0.6, hy + dx * sz * 0.6),
                       (hx + dy * sz * 0.6, hy - dx * sz * 0.6)]
                d.polygon(tip, fill=(240, 255, 170, 255))
                g.ellipse((hx * s - 9, hy * s - 9, hx * s + 9, hy * s + 9), fill=255)
            else:  # a pulse keeps travelling along the settled route
                u = ((t - r.arrive) / (1.6 if r.main else 1.2) + (r.start * 0.37) % 1) % 1
                q = r.points(cam, u, u, 1)[0]
                d.ellipse((q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4), fill=(240, 255, 170, 220))
                g.ellipse((q[0] * s - 5, q[1] * s - 5, q[0] * s + 5, q[1] * s + 5), fill=200)
            if t >= r.arrive:  # city marker: dot and an expanding ring
                cx, cy = cam.screen(r.b)[0][0]
                rr = 7 if r.main else 5
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(218, 255, 46, 255))
                ring_t = ((t - r.arrive) % 2.0) / 0.9
                if ring_t < 1:
                    R = rr + 34 * ease(ring_t) * (1 if r.main else 0.6)
                    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(218, 255, 46, round(200 * (1 - ring_t))),
                              width=3)
        return fx

    def markers(self, im, t, cam, gl):
        """The business at the centre, and parcels + labels on the six cities (upright, screen space)."""
        if t >= DROP:
            (pt,), (k,) = cam.screen(self.origin)
            x, y = pt
            a = prog(t, DROP, 0.25)
            g = ImageDraw.Draw(gl)
            g.ellipse((x * GLOW_SCALE - 22, y * GLOW_SCALE - 22, x * GLOW_SCALE + 22, y * GLOW_SCALE + 22), fill=255)
            d = ImageDraw.Draw(im, "RGBA")
            for ph in (0.0, 0.5):
                u = ((t - DROP) / 1.0 + ph) % 1
                R = 14 + 60 * ease(u)
                d.ellipse((x - R, y - R, x + R, y + R), outline=(218, 255, 46, round(180 * (1 - u) * a)), width=3)
            R = 13 * (0.6 + 0.4 * a) * (1 + 0.5 * math.exp(-max(0, t - DROP) / 0.12))
            d.ellipse((x - R, y - R, x + R, y + R), fill=(218, 255, 46, round(255 * a)))
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 255, 255, round(255 * a)))
            pop = prog(t, DROP + 0.1, 0.3)
            put(im, self.origin_chip, x, y + 30, pop, (1 - pop) * -16)  # below: the routes rise upwards
        for name, r, label, _ in self.cities:
            if t < r.arrive:
                continue
            (pt,), (k,) = cam.screen(r.b)
            x, y = pt
            u = clamp((t - r.arrive) / 0.35)
            pop = 1.25 * math.sin(u * math.pi * 0.75) / math.sin(math.pi * 0.75) if u < 1 else 1.0
            pop = min(pop, 1.25)
            size = 0.9 * k
            put(im, self.parcel, x, y - 70 * size * max(pop, 0.01), clamp(u * 3), 0, size * max(pop, 0.01))
            put(im, label, x, y + 16, prog(t, r.arrive + 0.05, 0.3))
            fly = clamp((t - r.arrive) / 0.9)  # a "+1" rises off the parcel and fades
            if fly < 1:
                px = min(max(x + 40 * size, 40), W - 40)
                put(im, self.plus_one, px, y - 104 * size - 40 * ease(fly), 1 - fly ** 2)

    def notices(self, im, t):
        arr = [c[1].arrive for c in self.cities]
        out = 1 - prog(t, GROW - 0.25, 0.3)
        if out <= 0:
            return
        for i, (_, r, _, card) in enumerate(self.cities):
            if t < r.arrive:
                continue
            slot = sum(prog(t, arr[j], 0.3) for j in range(i + 1, len(arr)))
            a = prog(t, r.arrive, 0.25) * clamp(3 - slot) * out
            y = 340 + 132 * slot - (1 - prog(t, r.arrive, 0.3)) * 40 - (1 - out) * 60
            put(im, card, W / 2, y, a)

    def text_layer(self, im, t):
        if t < DROP:
            out = 1 - prog(t, DROP - 0.3, 0.3)
            for i, (layer, at) in enumerate(zip(self.hook, HOOK_AT)):
                p = prog(t, at - 0.5, 0.35)
                put(im, layer, W / 2, 380 + i * 122, p * out, (1 - p) * 40 - (1 - out) * 50, 0.92 + 0.08 * p)
        elif GROW - 0.05 <= t < END:
            out = 1 - prog(t, END - 0.3, 0.3)
            for i, (layer, at) in enumerate(zip(self.message, MSG_AT)):
                p = prog(t, at, 0.35)
                put(im, layer, W / 2, 340 + i * 118, p * out, (1 - p) * 36, 0.9 + 0.1 * p)
            self.counter(im, t, out)

    def counter(self, im, t, out):
        a = prog(t, COUNT_AT, 0.4) * out
        if a <= 0:
            return
        c = self.cfg["sayac"]
        card = self.counter_bg.copy()
        d = ImageDraw.Draw(card)
        u = ease_io(clamp((t - COUNT_AT) / COUNT_DUR))
        n = round(c["baslangic"] + (c["bitis"] - c["baslangic"]) * u ** 1.6)
        d.text((34, 60), thousands(n), font=font("ExtraBold", 62), fill=WHITE)
        # mini bar chart rising with the count
        for i in range(7):
            hgt = (18 + 9 * i ** 1.35) * clamp(u * 1.4 - i * 0.08)
            x = 400 + i * 30
            d.rounded_rectangle((x, 122 - hgt, x + 18, 122), radius=5, fill=LIME if i == 6 else (150, 196, 30))
        y = 1385
        put(im, card, W / 2, y, a, (1 - a) * 24)
        note = text_img(c["not"], font("Medium", 21), (180, 200, 184))
        put(im, note, W / 2, y + 164, a * 0.85)

    def ending(self, im, t):
        if t < END:
            return
        s = self.cfg["son"]
        put(im, self.lime_glow, W / 2, 140, 0.55 * prog(t, END, 0.8))
        p = prog(t, END_AT[0], 0.35)
        put(im, self.logo, W / 2, 470, p, 0, 0.85 + 0.15 * p)
        f = font("Bold", 24)
        title = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(title), (W / 2, 4), s["unvan"], f, SOFT, 6, anchor="m")
        put(im, title, W / 2, 612, prog(t, END_AT[1], 0.35))
        colors = {"beyaz": WHITE, "lime": LIME}
        for i, (line, col) in enumerate(s["satirlar"]):
            layer = text_img(line, font("Black", 70), colors[col])
            pp = prog(t, END_AT[2 + i], 0.35)
            put(im, layer, W / 2, 712 + i * 88, pp, (1 - pp) * 30)
        pb = prog(t, END_AT[4], 0.3)
        if pb > 0:
            btn = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
            pill(ImageDraw.Draw(btn), W / 2, 4, s["buton"], font("ExtraBold", 31), LIME, INK, pad_x=36, h=80,
                 tracking=2, anchor="m")
            put(im, btn, W / 2, 940, pb, 0, 0.8 + 0.2 * ease(pb) + 0.06 * math.sin(clamp(pb) * math.pi))
        ps = prog(t, END_AT[5], 0.4)
        for i, line in enumerate(s["alt"]):
            put(im, text_img(line, font("Medium", 28), SOFT), W / 2, 1062 + i * 40, ps)
        web = Image.new("RGBA", (W, 34), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(web), (W / 2, 2), "WWW.İVEX.COM.TR", font("Bold", 22), (196, 214, 198), 6, anchor="m")
        put(im, web, W / 2, 1120 + 40 * (len(s["alt"]) - 1), ps)

    def frame(self, t):
        cam = Camera(t)
        im = self.bg.copy()
        gl = Image.new("L", (round(W * GLOW_SCALE), round(H * GLOW_SCALE)), 0)
        map_a = 1 - 0.68 * prog(t, END, 0.7)
        land = self.map_layer(t, cam, gl)
        fx = self.routes_layer(t, cam, gl)
        self.markers(fx, t, cam, gl)
        im.alpha_composite(faded(land, map_a))
        haze = Image.new("RGBA", gl.size, LIME + (0,))
        haze.putalpha(gl.filter(ImageFilter.GaussianBlur(7)).point(lambda v: round(v * 0.85 * map_a)))
        im.alpha_composite(haze.resize((W, H), Image.BILINEAR))
        im.alpha_composite(faded(fx, map_a))
        self.notices(im, t)
        self.text_layer(im, t)
        self.ending(im, t)
        return im


def sound_plan(ad):
    ev = [[at, "whoosh", {"sure": 0.4}] for at in HOOK_AT]
    ev += [[HOOK_AT[-1] + 0.5, "dijital", {}], [DROP - 1.0, "yukselis", {"sure": 0.95}],
           [DROP - 0.5, "rulo", {"sure": 0.45}], [DROP, "darbe", {"boy": 1.2}]]
    for i, (_, r, _, _) in enumerate(ad.cities):
        ev += [[r.arrive, "nota", {"i": (0, 2, 4, 5, 7, 8)[i % 6]}], [r.arrive, "kaydir", {}]]
    ev += [[GROW - 0.5, "yukselis", {"sure": 0.45}], [GROW, "gecis", {}]]
    ev += [[at, "vurgu", {"i": i}] for i, at in enumerate(MSG_AT)]
    ev.append([COUNT_AT, "dijital", {}])
    # the multiplying routes: a pluck on every eighth note that a route lands on, rising as they speed up
    ticks = sorted({round(r.arrive / (BEAT / 2)) * BEAT / 2 for r in ad.growth if 9.25 <= r.arrive < END - 0.6})
    ev += [[at, "nota", {"i": 2 + i}] for i, at in enumerate(ticks)]
    ev += [[END - 1.0, "yukselis", {"sure": 0.95}], [END - 0.5, "rulo", {"sure": 0.45}], [END, "darbe", {"boy": 1.4}],
           [END_AT[2], "parilti", {}], [END_AT[3], "vurgu", {"i": 0}], [END_AT[4], "pop", {}]]
    parts = {"insa": (0.0, DROP - 0.12), "drop": DROP, "ritim": (DROP, END), "son": END, "kisilma": 13.6}
    return {"bolumler": parts, "olaylar": sorted(ev, key=lambda e: e[0])}


FLASH = Image.new("RGBA", (W, H), LIME + (255,))


def frames(ad, hits):
    for i in range(round(TOTAL * FPS)):
        t = i / FPS
        im = ad.frame(t)
        a = max([0.0] + [0.2 * size * math.exp(-(t - h) / 0.07) for h, size in hits if 0 <= t - h < 0.3])
        if a > 0.01:
            im = Image.blend(im, FLASH, a)
        yield im.convert("RGB")


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    ad = Ad(cfg)
    if len(sys.argv) > 2:  # preview stills: python3 siparis_reklami.py cfg.json 1.5 5.2 ...
        for arg in sys.argv[2:]:
            out = repo(f"ivex-icerik/onizleme-{float(arg):05.2f}.jpg")
            ad.frame(float(arg)).convert("RGB").save(out, quality=88)
            print("önizleme:", out)
        return
    plan = sound_plan(ad)
    hits = [(at, p.get("boy", 1.0)) for at, kind, p in plan["olaylar"] if kind == "darbe"]
    out = repo(cfg["cikti"])
    silent, raw, music = (out.replace(".mp4", suffix) for suffix in ("-sessiz.mp4", "-ham.wav", "-muzik.wav"))
    write_video(frames(ad, hits), silent, (W, H), FPS)
    ses.write(plan, TOTAL, raw)
    ses.master(raw, music)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", silent, "-i", music,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    for tmp in (silent, raw, music):
        os.remove(tmp)
    print("kaydedildi:", out, "(müzikli)")
    kapak = ad.frame(2.7)
    lg = logo(58)
    kapak.alpha_composite(lg, ((W - lg.width) // 2, 1580))  # inside the 3:4 profile-grid crop
    kapak.convert("RGB").save(repo(cfg["kapak"]), quality=92)
    print("kaydedildi:", repo(cfg["kapak"]))


if __name__ == "__main__":
    main()
