"""Minah Tekstil - mağaza logosunun yüksek çözünürlüklü yeniden çizimi.

Kullanım:  python3 logo.py
Kaynak: Trendyol mağaza sayfasındaki ~120 px'lik profil logosu (kaynak-trendyol-magaza.jpg). Her parça o görsel
üzerinde rozet yarıçapına göre ölçülüp aynı yere çizildi (birim: rozet yarıçapı = 1, y aşağı doğru):
  - krem rozet, ince petrol mavisi halka (altında makara ve kumaş simgesi için iki boşluk), yanlarda kesik çizgili
    bej dikiş halkası;
  - arkada dokuma (alt-üst örgülü) bej baklava;
  - önde içi boş, çizgili şeritlerden oluşan petrol mavisi "M": sol şerit sağ şeridin üstünden geçer;
  - iki yanda kıvrık uçlu iplik dalgaları: soldakiler (mavi) sol bacağın üstünden, sağdakiler (bej) sağ bacağın
    altından geçer, yani iplik M'nin içinden dokunur;
  - "MİNAH" (mavi), "TEKSTİL" (bronz), altta makara ve dokuma kumaş simgeleri.
Kaynakta "TEKSTİL"in altındaki iki küçük satır okunamayacak kadar küçük; metni bilinirse SLOGAN'a yazılır.
Çıktılar: şeffaf köşeli 2000 px PNG ve Trendyol profiline yüklemek için krem zeminli kare JPG.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "..", "ivex-icerik", "uretim", "fonts")
OUT = 2000
SS = 2  # draw at twice the size, then downsample for clean edges
S = OUT * SS
C = S / 2
R = S / 2 * 0.995  # badge radius

CREAM = (246, 244, 238)
TEAL = (27, 61, 73)
BRONZE = (136, 104, 70)
TAN = (198, 160, 114)
LAT_BG = (248, 240, 228)
INK = (64, 64, 64)

SLOGAN = []  # the two small lines under TEKSTİL, e.g. ["...", "..."] once the wording is known

LINE = 0.024  # outline weight of the M
STRIPE = 0.014  # stripes inside the M's ribbons
WAVE = 0.017
WAVE_GAP = 0.012  # cream halo either side of each wave line


def P(u, v):
    return (C + u * R, C + v * R)


def px(w):
    return max(1, round(w * R))


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat_{weight}.ttf"), size)


def dot(d, p, w, fill):
    x, y = P(*p)
    r = w * R / 2
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def line(d, pts, w, fill, caps=True):
    """Thick polyline with round joins (PIL's own joints leave notches on dense curves)."""
    q = [P(*p) for p in pts]
    r = w * R / 2
    for a, b in zip(q, q[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        if n == 0:
            continue
        nx, ny = -dy / n * r, dx / n * r
        d.polygon([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)],
                  fill=fill)
    for x, y in (q if caps else q[1:-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def outline(d, pts, w, fill):
    q = [P(*p) for p in pts]
    d.line(q + q[:2], fill=fill, width=px(w), joint="curve")


def polygon(d, pts, fill):
    d.polygon([P(*p) for p in pts], fill=fill)


def mask_of(pts):
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).polygon([P(*p) for p in pts], fill=255)
    return m


def spline(pts, n=20):
    """Catmull-Rom curve through the points."""
    q = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * (2 * p1[j] + (p2[j] - p0[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (3 * p1[j] - p0[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    out.append(pts[-1])
    return out


def meet(a, b, c, e):
    """Intersection of line a-b with line c-e."""
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = a, b, c, e
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def y_on(a, b, x):
    return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])


# ---------------------------------------------------------------- rings

def rings(im):
    d = ImageDraw.Draw(im)
    r, w = 0.845, 0.02
    box = (C - (r + w / 2) * R, C - (r + w / 2) * R, C + (r + w / 2) * R, C + (r + w / 2) * R)
    # angles clockwise from 3 o'clock; gaps at 40-60 and 120-140 hold the two small icons
    for a0, a1 in ((60, 120), (140, 360), (0, 40)):
        d.arc(box, a0, a1, fill=TEAL, width=px(w))
    for a in (40, 60, 120, 140):
        dot(d, (r * math.cos(math.radians(a)), r * math.sin(math.radians(a))), w, TEAL)
    # stitched inner ring, only on the two sides
    r, dash, gap = 0.775, 0.026, 0.02
    for a0, a1 in ((142, 228), (-48, 38)):
        a = math.radians(a0)
        while a < math.radians(a1):
            b = a + dash / r
            pts = [(r * math.cos(a + (b - a) * k / 6), r * math.sin(a + (b - a) * k / 6)) for k in range(7)]
            line(d, pts, 0.011, TAN)
            a = b + gap / r


# ---------------------------------------------------------------- woven diamond

def lattice(im):
    """Kilim diamond: a heavy double rim and evenly spaced nested diamonds inside it."""
    cy0, h = -0.397, 0.368
    x0, y0 = P(-h - 0.02, cy0 - h - 0.02)
    x1, y1 = P(h + 0.02, cy0 + h + 0.02)
    x0, y0, x1, y1 = int(x0), int(y0), int(x1) + 1, int(y1) + 1
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    u, v = (xx - C) / R, (yy - C) / R
    depth = (h - np.maximum(np.abs(u + v - cy0), np.abs(v - cy0 - u))) / math.sqrt(2)  # distance in from the rim
    img = np.empty(u.shape + (3,), np.float32)
    img[:] = LAT_BG
    ink = (depth <= 0.015) | ((depth >= 0.029) & (depth <= 0.039))
    ink |= (depth > 0.039) & (np.mod(depth - 0.039, 0.045) >= 0.033)
    img[ink] = TAN
    alpha = ((depth >= -1e-4) * 255).astype(np.uint8)
    layer = Image.fromarray(img.astype(np.uint8), "RGB").convert("RGBA")
    layer.putalpha(Image.fromarray(alpha))
    im.alpha_composite(layer, (x0, y0))


# ---------------------------------------------------------------- the M

STEM_IN, STEM_OUT, TOP, FOOT = 0.245, 0.415, -0.645, -0.04
NOTCH = (0.0, -0.42)  # where the two upper ribbon edges meet
TIP = (0.0, -0.21)  # bottom point of the V


def stem_box(sx):
    return [(sx * STEM_IN, TOP), (sx * STEM_OUT, TOP), (sx * STEM_OUT, FOOT), (sx * STEM_IN, FOOT)]


def stem_lines(d, sx):
    outline(d, stem_box(sx), LINE, TEAL)
    corner = (sx * STEM_OUT, TOP)
    x = 0.318
    start = (sx * x, y_on(corner, TIP, sx * x))
    pts = [start, (sx * 0.322, -0.35), (sx * 0.332, -0.19), (sx * 0.342, -0.16), (sx * 0.36, -0.134),
           (sx * 0.366, -0.1), (sx * 0.366, -0.078)]
    line(d, spline(pts), STRIPE, TEAL)


def ribbons():
    """Polygons of the two diagonal ribbons; the left one lies on top."""
    lu0, lc = (-STEM_IN, TOP), (-STEM_OUT, TOP)
    ru0, rc = (STEM_IN, TOP), (STEM_OUT, TOP)
    x = meet(lu0, NOTCH, rc, TIP)  # left ribbon's end, cut along the right ribbon's lower edge
    left = [lc, lu0, x, TIP]
    right = [rc, ru0, NOTCH, x]
    return left, right, (lu0, NOTCH, lc, TIP), (ru0, NOTCH, rc, TIP)


def ribbon(im, poly, edges, sx):
    d = ImageDraw.Draw(im)
    polygon(d, poly, CREAM)
    upper_a, upper_b, lower_a, lower_b = edges
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    xs = (sx * STEM_IN, -sx * 0.05)
    for f in (1 / 3, 2 / 3):
        p = [(x, y_on(upper_a, upper_b, x) * (1 - f) + y_on(lower_a, lower_b, x) * f) for x in xs]
        far = -sx * 0.25  # run on past the end; the mask trims it
        p.append((far, p[0][1] + (p[1][1] - p[0][1]) * (far - p[0][0]) / (p[1][0] - p[0][0])))
        dl.line([P(*q) for q in (p[0], p[2])], fill=TEAL, width=px(STRIPE))
    clip = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    clip.paste(layer, (0, 0), mask_of(poly))
    im.alpha_composite(clip)
    outline(ImageDraw.Draw(im), poly, LINE, TEAL)


# ---------------------------------------------------------------- thread waves (drawn for the left side)

WAVES = [
    [(-0.505, -0.428), (-0.553, -0.432), (-0.585, -0.405), (-0.583, -0.37), (-0.555, -0.348), (-0.51, -0.342),
     (-0.46, -0.344), (-0.40, -0.357), (-0.33, -0.383), (-0.26, -0.415), (-0.19, -0.455)],
    [(-0.607, -0.368), (-0.598, -0.333), (-0.565, -0.31), (-0.51, -0.302), (-0.45, -0.306), (-0.38, -0.322),
     (-0.31, -0.348), (-0.24, -0.38), (-0.17, -0.42)],
    [(-0.648, -0.328), (-0.636, -0.293), (-0.60, -0.275), (-0.54, -0.268), (-0.47, -0.27), (-0.40, -0.283),
     (-0.33, -0.305), (-0.26, -0.337), (-0.18, -0.38), (-0.12, -0.42)],
    [(-0.685, -0.29), (-0.672, -0.258), (-0.635, -0.24), (-0.57, -0.233), (-0.50, -0.233), (-0.43, -0.243),
     (-0.36, -0.262), (-0.29, -0.29), (-0.21, -0.33), (-0.13, -0.38)],
    [(-0.648, -0.222), (-0.63, -0.207), (-0.58, -0.2), (-0.51, -0.199), (-0.44, -0.205), (-0.37, -0.222),
     (-0.30, -0.248), (-0.22, -0.285), (-0.14, -0.33), (-0.08, -0.37)],
    [(-0.575, -0.157), (-0.52, -0.158), (-0.46, -0.164), (-0.40, -0.178), (-0.33, -0.202), (-0.26, -0.235),
     (-0.18, -0.28), (-0.10, -0.33), (-0.05, -0.37)],
]


def waves(im, sx, color):
    d = ImageDraw.Draw(im)
    curves = [spline([(sx * -x, y) for x, y in w]) for w in WAVES]
    for c in curves:
        line(d, c, WAVE + 2 * WAVE_GAP, CREAM)
    for c in curves:
        line(d, c, WAVE, color)


# ---------------------------------------------------------------- lettering

def spaced(d, text, fnt, cx, baseline, width, fill):
    """Draw `text` letter-spaced so its ink spans `width` (badge units), centred on cx."""
    adv = [fnt.getlength(ch) for ch in text]
    first, last = fnt.getbbox(text[0], anchor="ls"), fnt.getbbox(text[-1], anchor="ls")
    natural = sum(adv[:-1]) + last[2] - first[0]
    gap = (width * R - natural) / (len(text) - 1)
    x = C + cx * R - width * R / 2 - first[0]
    y = C + baseline * R
    for ch, a in zip(text, adv):
        d.text((x, y), ch, font=fnt, fill=fill, anchor="ls")
        x += a + gap


def sized(weight, cap):
    """Montserrat at the size whose capital H is `cap` badge units tall."""
    probe = font(weight, 1000)
    b = probe.getbbox("H", anchor="ls")
    return font(weight, round(1000 * cap * R / (b[3] - b[1])))


# ---------------------------------------------------------------- small icons

def spool(im, cx, cy):
    d = ImageDraw.Draw(im)
    q = lambda x, y: (cx + x, cy + y)
    body = [q(-0.04, -0.06), q(0.04, -0.06), q(0.04, 0.06), q(-0.04, 0.06)]
    polygon(d, body, TAN)
    for k in range(9):  # wound thread
        y = -0.052 + k * 0.013
        line(d, [q(-0.04, y), q(0.04, y + 0.004)], 0.005, BRONZE, caps=False)
    for x in (-0.04, 0.04):
        line(d, [q(x, -0.06), q(x, 0.06)], 0.01, BRONZE)
    for y in (-0.069, 0.069):  # flanges
        a, b = P(*q(-0.066, y - 0.011))
        e, f = P(*q(0.066, y + 0.011))
        d.rounded_rectangle((a, b, e, f), radius=0.008 * R, fill=BRONZE)
    # the loose end of the thread, running off as a few stitches
    line(d, spline([q(0.036, -0.03), q(0.06, -0.036), q(0.078, -0.02), q(0.082, 0.0)]), 0.008, BRONZE)
    for p in ((0.088, 0.024), (0.104, 0.038), (0.128, 0.04)):
        dot(d, q(*p), 0.014, BRONZE)


def swatch(im, cx, cy):
    """A small piece of woven cloth: four warp and four weft threads."""
    d = ImageDraw.Draw(im)
    offs = (-0.0525, -0.0175, 0.0175, 0.0525)
    w, reach = 0.019, 0.078
    for o in offs:
        line(d, [(cx + o, cy - reach), (cx + o, cy + reach)], w, BRONZE)
        line(d, [(cx - reach, cy + o), (cx + reach, cy + o)], w, BRONZE)


# ---------------------------------------------------------------- assembly

def draw():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((C - R, C - R, C + R, C + R), fill=CREAM)
    rings(im)
    lattice(im)
    d = ImageDraw.Draw(im)
    for sx in (-1, 1):
        polygon(d, stem_box(sx), CREAM)
    waves(im, 1, TAN)  # right-hand threads pass under the right leg ...
    d = ImageDraw.Draw(im)
    stem_lines(d, 1)
    stem_lines(d, -1)
    waves(im, -1, TEAL)  # ... and over the left one
    left, right, le, re = ribbons()
    ribbon(im, right, re, 1)
    ribbon(im, left, le, -1)

    d = ImageDraw.Draw(im)
    spaced(d, "MİNAH", sized("600SemiBold", 0.229), 0.0, 0.295, 1.216, TEAL)
    spaced(d, "TEKSTİL", sized("500Medium", 0.155), 0.0, 0.515, 0.96, BRONZE)
    for i, text in enumerate(SLOGAN[:2]):
        f = sized("600SemiBold", 0.034)
        width = d.textlength(text, font=f) / R * 1.18
        spaced(d, text, f, 0.0, 0.64 + i * 0.062, width, INK)
    spool(im, -0.535, 0.652)
    swatch(im, 0.525, 0.645)
    return im.resize((OUT, OUT), Image.LANCZOS)


def main():
    im = draw()
    im.save(os.path.join(HERE, "minah-tekstil-logo.png"))
    sq = Image.new("RGB", (OUT, OUT), CREAM)
    sq.paste(im, (0, 0), im)
    sq.resize((1200, 1200), Image.LANCZOS).save(os.path.join(HERE, "minah-tekstil-logo-kare.jpg"), quality=95)
    print("kaydedildi:", os.path.join(HERE, "minah-tekstil-logo.png"), "ve -kare.jpg")


if __name__ == "__main__":
    main()
