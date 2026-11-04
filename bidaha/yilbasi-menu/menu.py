"""Bidaha - yılbaşı menü görseli: 9:16 hikaye (1080x1920) ve 4:5 gönderi (1080x1350).

Kullanım:  python3 menu.py [menu.json]
Kırmızı kadife zemin (davet videosuyla aynı), ampul çerçeveli koyu bir menü kartı, üstte asılı yılbaşı süsleri,
yıldız ve konfeti. Kartın içinde logo, "10. YIL · 2027" şeridi, giriş metni, "Yeni Menümüz" başlığı, iki sütunda
menü (solda soğuk ve sıcak başlangıçlar, sağda ana yemek ve tatlı), iki fiyat kartı ve rezervasyon satırı.
Menü yazıları Playfair Display, başlık Great Vibes, fiyatlar Montserrat (Playfair'de ₺ işareti yok).
Görsel iki kat büyük çizilip küçültülür; yazı kartın dışına taşarsa betik durur.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FONTS = os.path.join(REPO, "ivex-icerik", "uretim", "fonts")
K = 2  # drawn at twice the size

CREAM = (255, 243, 214)
GOLD = (246, 196, 92)
GOLD_L = (255, 228, 160)
MUTED = (222, 196, 160)
RNG = np.random.default_rng(2027)

STORY = dict(W=1080, H=1920, card=(50, 70, 1030, 1850), logo_w=520, logo_top=150, gap_logo=26, ribbon=24,
             intro=30, intro_lh=45, intro_w=840, gap_intro=46, heading=118, gap_heading=6, cols=(300, 780),
             col_w=440, title=31, note=23, item=33, item_lh=47, sec_gap=34, gap_menu=40, price_title=24,
             price_label=26, price_val=33, price_row=54, price_pad=26, gap_price=34, foot=(26, 22),
             baubles=[(118, 215, 44, "gold"), (212, 108, 26, "red"), (868, 112, 26, "red"), (962, 230, 44, "gold")])
POST = dict(W=1080, H=1350, card=(36, 36, 1044, 1314), logo_w=380, logo_top=78, gap_logo=16, ribbon=20,
            intro=23, intro_lh=33, intro_w=900, gap_intro=26, heading=84, gap_heading=0, cols=(290, 790),
            col_w=440, title=25, note=19, item=26, item_lh=36, sec_gap=20, gap_menu=24, price_title=20,
            price_label=21, price_val=26, price_row=40, price_pad=18, gap_price=20, foot=(21, 18),
            baubles=[(104, 150, 34, "gold"), (186, 76, 20, "red"), (896, 82, 20, "red"), (976, 158, 34, "gold")])


def repo(p):
    return os.path.join(REPO, p)


def tr_upper(text):
    return str(text).replace("i", "İ").replace("ı", "I").upper()


def playfair(size, weight=400, italic=False):
    name = "PlayfairDisplay_Italic_Variable.ttf" if italic else "PlayfairDisplay_Variable.ttf"
    f = ImageFont.truetype(os.path.join(FONTS, name), round(size * K))
    f.set_variation_by_axes([weight])
    return f


def mont(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat_{weight}.ttf"), round(size * K))


def vibes(size):
    return ImageFont.truetype(os.path.join(FONTS, "GreatVibes_400Regular.ttf"), round(size * K))


def price(n):
    return "₺" + f"{n:,}".replace(",", ".")


# ---------------------------------------------------------------- drawing helpers

def text_layer(text, fnt, fill, track=0.0):
    """Text on its own transparent layer; fill is a colour or "gold" for a warm metallic gradient."""
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    widths = [d0.textlength(c, font=fnt) for c in text]
    tw = sum(widths) + track * K * (len(text) - 1)
    asc, desc = fnt.getmetrics()
    pad = 20 * K
    mask = Image.new("L", (round(tw) + 2 * pad, asc + desc + 2 * pad), 0)
    d = ImageDraw.Draw(mask)
    x = pad
    for c, w in zip(text, widths):
        d.text((x, pad), c, font=fnt, fill=255)
        x += w + track * K
    if fill == "gold":
        h = mask.height
        yy = np.linspace(0, 1, h)[:, None]
        top, mid, bot = np.array([255, 238, 178.0]), np.array([246, 196, 92.0]), np.array([205, 132, 50.0])
        g = np.where(yy < 0.5, top + (mid - top) * yy / 0.5, mid + (bot - mid) * (yy - 0.5) / 0.5)
        rgb = np.repeat(g[:, None, :], mask.width, axis=1)
    else:
        rgb = np.zeros((mask.height, mask.width, 3)) + np.array(fill, float)
    img = Image.fromarray(np.dstack([rgb, np.asarray(mask)]).astype(np.uint8), "RGBA")
    return img, (pad, pad, asc)


def put_text(base, xy, text, fnt, fill, anchor="mm", track=0.0, glow=0, shadow=True):
    """Draw text at base coordinates (1080-wide units). anchor: m=centre, l=left, r=right (vertical: centre)."""
    img, (px, py, asc) = text_layer(text, fnt, fill, track)
    bbox = img.getbbox()
    if not bbox:
        return 0
    x, y = xy[0] * K, xy[1] * K
    ink_w = bbox[2] - bbox[0]
    # centre on the capital height, so accents (İ) and descenders do not move a line up or down
    cap = fnt.getbbox("H")
    ink_cy = py + (cap[1] + cap[3]) / 2
    if anchor[0] == "m":
        ox = x - (bbox[0] + ink_w / 2)
    elif anchor[0] == "l":
        ox = x - bbox[0]
    else:
        ox = x - bbox[2]
    oy = y - ink_cy
    ox, oy = round(ox), round(oy)
    if shadow:
        sh = Image.new("RGBA", img.size, (15, 0, 3, 0))
        sh.putalpha(img.getchannel("A").point(lambda v: v * 0.75))
        sh = sh.filter(ImageFilter.GaussianBlur(4 * K))
        base.alpha_composite(sh, (ox, oy + 3 * K))
    if glow:
        gl = Image.new("RGBA", img.size, (255, 190, 90, 0))
        gl.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(glow * K)).point(lambda v: v * 0.55))
        base.alpha_composite(gl, (ox, oy))
    base.alpha_composite(img, (ox, oy))
    return ink_w / K


def text_width(text, fnt, track=0.0):
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    return (sum(d0.textlength(c, font=fnt) for c in text) + track * K * (len(text) - 1)) / K


def wrap(text, fnt, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if text_width(trial, fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def balanced(text, fnt, width):
    """As few lines as a greedy wrap needs, but with the lines as even as possible."""
    n = len(wrap(text, fnt, width))
    if n == 1:
        return [text]
    w = text_width(text, fnt) / n
    while len(wrap(text, fnt, w)) > n:
        w += 4
    return wrap(text, fnt, w)


def velvet(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lo = RNG.standard_normal((12, 7)).astype(np.float32)
    lo = np.asarray(Image.fromarray(lo).resize((w, h), Image.BICUBIC), np.float32)
    folds = (0.5 + 0.5 * np.sin(xx / (150 * K) * 2 * np.pi + lo * 1.4 + yy / (900 * K))) ** 1.6
    grain = np.asarray(Image.fromarray(RNG.standard_normal((h // 2, w // 2)).astype(np.float32)).resize((w, h)),
                       np.float32)
    shade = 0.42 + 0.48 * folds + 0.035 * grain
    r = np.hypot((xx - w / 2) / w, (yy - h * 0.42) / h)
    vig = np.clip(1.15 - r * 1.25, 0.25, 1.0)
    rgb = (shade * vig)[..., None] * np.array([0.43, 0.035, 0.07], np.float32)
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")


def radial(size, inner, outer, hl=True):
    """A shaded ball: colour from `inner` (lit side) to `outer` (rim), with a soft highlight."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) - size / 2 + 0.5
    r = size / 2
    d = np.hypot(xx, yy) / r
    dl = np.hypot(xx + r * 0.32, yy + r * 0.36) / r
    t = np.clip(dl / 1.35, 0, 1)[..., None]
    rgb = np.array(inner, np.float32) * (1 - t) + np.array(outer, np.float32) * t
    if hl:
        spot = np.exp(-((xx + r * 0.38) ** 2 + (yy + r * 0.42) ** 2) / (2 * (r * 0.16) ** 2))[..., None]
        rgb = rgb + (255 - rgb) * spot * 0.9
    a = np.clip((1 - d) * r, 0, 1) * 255
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a]).astype(np.uint8), "RGBA")


def bauble(base, cx, length, r, kind):
    """A hanging ornament: string from the top edge, a gold cap, a shiny ball."""
    d = ImageDraw.Draw(base)
    x, y1 = cx * K, length * K
    d.line([(x, 0), (x, y1)], fill=(232, 190, 110, 230), width=max(1, round(1.6 * K)))
    cap_w, cap_h = r * 0.42 * K, r * 0.3 * K
    d.rounded_rectangle((x - cap_w / 2, y1, x + cap_w / 2, y1 + cap_h), radius=2 * K, fill=(214, 162, 72, 255))
    colors = {"gold": ((255, 226, 140), (150, 92, 22)), "red": ((236, 70, 80), (92, 6, 18))}
    ball = radial(round(2 * r * K), *colors[kind])
    sh = Image.new("RGBA", ball.size, (10, 0, 2, 0))
    sh.putalpha(ball.getchannel("A").point(lambda v: v * 0.6))
    sh = sh.filter(ImageFilter.GaussianBlur(8 * K))
    top = round(y1 + cap_h * 0.8)
    base.alpha_composite(sh, (round(x - r * K + 6 * K), top + 10 * K))
    base.alpha_composite(ball, (round(x - r * K), top))
    # a thin band around the ball
    band = Image.new("RGBA", ball.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.ellipse((0, ball.height * 0.42, ball.width, ball.height * 0.58), outline=(255, 236, 190, 120), width=K * 2)
    band.putalpha(Image.fromarray(np.minimum(np.asarray(band.getchannel("A")), np.asarray(ball.getchannel("A")))))
    base.alpha_composite(band, (round(x - r * K), top))


def sparkle(d, cx, cy, s, color=(255, 230, 160, 255)):
    x, y, s = cx * K, cy * K, s * K
    w = s * 0.18
    d.polygon([(x, y - s), (x + w, y - w), (x + s, y), (x + w, y + w), (x, y + s), (x - w, y + w), (x - s, y),
               (x - w, y - w)], fill=color)


def confetti(base, area, n):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = area
    cols = [(246, 196, 92), (255, 236, 170), (214, 40, 60), (255, 243, 214)]
    for _ in range(n):
        x, y = RNG.uniform(x0, x1) * K, RNG.uniform(y0, y1) * K
        w, h, a = RNG.uniform(5, 11) * K, RNG.uniform(2.5, 5) * K, RNG.uniform(0, math.pi)
        ca, sa = math.cos(a), math.sin(a)
        pts = [(x + ca * px - sa * py, y + sa * px + ca * py) for px, py in
               ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
        d.polygon(pts, fill=cols[RNG.integers(0, 4)] + (int(RNG.uniform(150, 240)),))
    base.alpha_composite(layer)


def bulbs(base, rect, step, r):
    """Marquee bulbs along a rectangle, with a warm glow."""
    x0, y0, x1, y1 = rect
    pts = []
    nx, ny = round((x1 - x0) / step), round((y1 - y0) / step)
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        pts += [(x, y0), (x, y1)]
    for j in range(1, ny):
        y = y0 + (y1 - y0) * j / ny
        pts += [(x0, y), (x1, y)]
    glow = Image.new("RGBA", base.size, (255, 170, 70, 0))
    gd = ImageDraw.Draw(glow)
    for x, y in pts:
        gd.ellipse(((x - r * 2.6) * K, (y - r * 2.6) * K, (x + r * 2.6) * K, (y + r * 2.6) * K), fill=(255, 170, 70, 120))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(r * 1.6 * K)))
    d = ImageDraw.Draw(base)
    d.rectangle((x0 * K, y0 * K, x1 * K, y1 * K), outline=(236, 186, 92, 255), width=max(1, round(1.5 * K)))
    ball = radial(round(2 * r * K), (255, 252, 226), (246, 196, 92))
    for x, y in pts:
        base.alpha_composite(ball, (round((x - r) * K), round((y - r) * K)))


def ornament(d, cx, cy, half):
    """Gold rule with a diamond in the middle."""
    c = (232, 186, 96, 255)
    d.line([((cx - half) * K, cy * K), ((cx - 14) * K, cy * K)], fill=c, width=max(1, round(1.2 * K)))
    d.line([((cx + 14) * K, cy * K), ((cx + half) * K, cy * K)], fill=c, width=max(1, round(1.2 * K)))
    s = 7 * K
    d.polygon([(cx * K, cy * K - s), (cx * K + s, cy * K), (cx * K, cy * K + s), (cx * K - s, cy * K)], fill=c)


# ---------------------------------------------------------------- the menu

def section(base, cx, y, sec, L):
    t = playfair(L["title"], 700)
    put_text(base, (cx, y + L["title"] * 0.62), tr_upper(sec["baslik"]), t, "gold", track=3.2)
    y += L["title"] * 1.35
    if sec.get("not"):
        put_text(base, (cx, y + L["note"] * 0.55), sec["not"], playfair(L["note"], 400, True), GOLD_L)
        y += L["note"] * 1.45
    y += L["item"] * 0.15
    item = playfair(L["item"], 500)
    for it in sec["ogeler"]:
        if it.startswith("~"):
            put_text(base, (cx, y + L["item_lh"] * 0.4), it[1:], playfair(L["note"], 400, True), GOLD_L)
            y += L["item_lh"] * 0.78
            continue
        for line in balanced(it, item, L["col_w"]):
            put_text(base, (cx, y + L["item_lh"] / 2), line, item, CREAM)
            y += L["item_lh"]
    return y


def price_card(base, rect, data, L):
    x0, y0, x1, y1 = rect
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((x0 * K, y0 * K, x1 * K, y1 * K), radius=18 * K, fill=(18, 2, 6, 170),
                        outline=(232, 186, 96, 255), width=max(1, round(1.4 * K)))
    pad = L["price_pad"]
    put_text(base, ((x0 + x1) / 2, y0 + pad + L["price_title"] * 0.55), tr_upper(data["baslik"]),
             mont("700Bold", L["price_title"]), "gold", track=3)
    y = y0 + pad + L["price_title"] * 1.5 + L["price_row"] * 0.45
    lab, val = playfair(L["price_label"], 500), mont("700Bold", L["price_val"])
    for label, amount in data["satirlar"]:
        lw = put_text(base, (x0 + pad, y), label, lab, CREAM, anchor="lm")
        txt = price(amount)
        vw = put_text(base, (x1 - pad, y), txt, val, "gold", anchor="rm")
        # dotted leader between label and price
        a, b = x0 + pad + lw + 10, x1 - pad - vw - 10
        x = a
        while x < b:
            d.ellipse(((x - 1.3) * K, (y + L["price_label"] * 0.28 - 1.3) * K, (x + 1.3) * K,
                       (y + L["price_label"] * 0.28 + 1.3) * K), fill=(214, 172, 100, 200))
            x += 9
        y += L["price_row"]
    return y


def render(cfg, L, out, save=True):
    W, H = L["W"], L["H"]
    base = velvet(W * K, H * K)
    cx0, cy0, cx1, cy1 = L["card"]
    # the card
    d = ImageDraw.Draw(base)
    card = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(card).rectangle((cx0 * K, cy0 * K, cx1 * K, cy1 * K), fill=(14, 1, 4, 178))
    base.alpha_composite(card)
    inner = (cx0 + 22, cy0 + 22, cx1 - 22, cy1 - 22)
    d = ImageDraw.Draw(base)
    d.rectangle(tuple(v * K for v in inner), outline=(214, 168, 86, 200), width=max(1, round(1.0 * K)))
    bulbs(base, L["card"], 46 if H > 1500 else 42, 9 if H > 1500 else 8)

    # festive scatter: confetti and sparkles around the top and bottom
    side = (W - L["logo_w"]) / 2 - 24
    top_band = L["logo_top"] + L["logo_w"] * 0.29
    for x0, x1 in ((cx0 + 30, side), (W - side, cx1 - 30)):
        confetti(base, (x0, cy0 + 30, x1, top_band + 40), 20)
    confetti(base, (cx0 + 30, cy1 - 95 * H / 1920, cx1 - 30, cy1 - 30), 30)
    d = ImageDraw.Draw(base)
    for x0, x1 in ((cx0 + 40, side - 10), (W - side + 10, cx1 - 40)):
        for _ in range(7):
            sparkle(d, RNG.uniform(x0, x1), RNG.uniform(cy0 + 40, top_band + 30), RNG.uniform(4, 11))

    # header
    logo = Image.open(repo(cfg["logo"])).convert("RGBA")
    a = np.asarray(logo.getchannel("A"), np.float32)
    logo.putalpha(Image.fromarray(np.clip((a - 16) * 255 / 239, 0, 255).astype(np.uint8)))
    lw = L["logo_w"] * K
    logo = logo.resize((round(lw), round(logo.height * lw / logo.width)), Image.LANCZOS)
    glow = Image.new("RGBA", logo.size, (255, 150, 60, 0))
    glow.putalpha(logo.getchannel("A").filter(ImageFilter.GaussianBlur(14 * K)).point(lambda v: v * 0.5))
    lx, ly = round(W * K / 2 - logo.width / 2), round(L["logo_top"] * K)
    base.alpha_composite(glow, (lx, ly))
    base.alpha_composite(logo, (lx, ly))
    y = L["logo_top"] + logo.height / K + L["gap_logo"]

    rib = mont("600SemiBold", L["ribbon"])
    rw = put_text(base, (W / 2, y + L["ribbon"] / 2), cfg["serit"], rib, "gold", track=5)
    d = ImageDraw.Draw(base)
    for sgn in (-1, 1):
        x_in = W / 2 + sgn * (rw / 2 + 16)
        d.line([(x_in * K, (y + L["ribbon"] / 2) * K), ((x_in + sgn * 90) * K, (y + L["ribbon"] / 2) * K)],
               fill=(232, 186, 96, 255), width=max(1, round(1.2 * K)))
    y += L["ribbon"] + L["gap_logo"] * 1.3

    it = playfair(L["intro"], 400, True)
    for line in balanced(cfg["giris"], it, L["intro_w"]):
        put_text(base, (W / 2, y + L["intro_lh"] / 2), line, it, CREAM)
        y += L["intro_lh"]
    y += L["gap_intro"]

    hd = vibes(L["heading"])
    put_text(base, (W / 2, y + L["heading"] * 0.45), cfg["baslik"], hd, "gold", glow=10)
    hw = text_width(cfg["baslik"], hd)
    d = ImageDraw.Draw(base)
    for sgn in (-1, 1):
        sparkle(d, W / 2 + sgn * (hw / 2 + 34), y + L["heading"] * 0.42, L["heading"] * 0.11)
    y += L["heading"] * 1.12 + L["gap_heading"]

    # two menu columns with a thin divider
    top = y
    ys = []
    for col, cx in zip(("sol", "sag"), L["cols"]):
        yy = top
        for k, sec in enumerate(cfg[col]):
            if k:
                yy += L["sec_gap"]
            yy = section(base, cx, yy, sec, L)
        ys.append(yy)
    y = max(ys)
    d = ImageDraw.Draw(base)
    d.line([(W / 2 * K, (top + 8) * K), (W / 2 * K, (y - 8) * K)], fill=(214, 168, 86, 150),
           width=max(1, round(1.0 * K)))
    y += L["gap_menu"] * 0.5
    ornament(d, W / 2, y, 200)
    y += L["gap_menu"] * 0.7

    # prices
    pts = cfg["fiyatlar"]
    ph = L["price_pad"] * 2 + L["price_title"] * 1.5 + L["price_row"] * len(pts[0]["satirlar"])
    margin = 70 if W == 1080 and H > 1500 else 76
    gap = 30
    pw = (W - 2 * margin - gap) / 2
    for k, p in enumerate(pts):
        x0 = margin + k * (pw + gap)
        price_card(base, (x0, y, x0 + pw, y + ph), p, L)
    y += ph + L["gap_price"]

    f1, f2 = L["foot"]
    put_text(base, (W / 2, y + f1 / 2), cfg["alt"]["rezervasyon"], mont("600SemiBold", f1), CREAM)
    y += f1 * 1.5
    put_text(base, (W / 2, y + f2 / 2), cfg["alt"]["adres"], mont("500Medium", f2), MUTED)
    y += f2

    limit = cy1 - 30
    if y > limit:
        sys.exit(f"{os.path.basename(out)}: içerik kartı {y - limit:.0f} px aşıyor")
    if not save:
        return limit - y
    print(f"{os.path.basename(out)}: kartın altında {limit - y:.0f} px boşluk")

    # ornaments hang over the top of the card, drawn last so they sit in front
    for bx, length, r, kind in L["baubles"]:
        bauble(base, bx, length, r, kind)

    img = base.convert("RGB")
    full = img.resize((W, H), Image.LANCZOS)
    os.makedirs(os.path.dirname(repo(out)), exist_ok=True)
    full.save(repo(out), quality=95, subsampling=0)
    img.save(repo(out).replace(".jpg", "-yuksek.jpg"), quality=94, subsampling=0)
    print("kaydedildi:", out)


def fill(cfg, L, out, bottom):
    """Measure the free space under the content and share it between the gaps, leaving `bottom` px."""
    global RNG
    RNG = np.random.default_rng(2027)
    spare = render(cfg, L, out, save=False) - bottom
    L = dict(L)
    if spare > 0:
        for key, share in (("logo_top", 0.10), ("gap_intro", 0.16), ("gap_heading", 0.10), ("sec_gap", 0.11),
                           ("gap_menu", 0.18), ("gap_price", 0.13)):
            L[key] += spare * share
    RNG = np.random.default_rng(2027)
    render(cfg, L, out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "menu.json")
    cfg = json.load(open(path, encoding="utf-8"))
    fill(cfg, STORY, cfg["cikti"]["hikaye"], 70)
    fill(cfg, POST, cfg["cikti"]["gonderi"], 50)


if __name__ == "__main__":
    main()
