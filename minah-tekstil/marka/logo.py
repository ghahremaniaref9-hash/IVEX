"""Minah Tekstil - mağaza logosunun yüksek çözünürlüklü yeniden çizimi.

Kullanım:  python3 logo.py
Kaynak: Trendyol satıcı panelindeki ~50 px'lik profil logosu. Yapı ve renkler oradan ölçüldü:
krem rozet, petrol mavisi dış halka ve ince bej iç halka, kilim desenli bej eşkenar dörtgen önünde dokuma
çizgili petrol mavisi "M", iki yanda başak dalı (sol mavi, sağ bej), altta "MİNAH" (mavi) ve "TEKSTİL" (bej),
en altta iki küçük kilim motifi. "TEKSTİL"in altındaki iki küçük satır kaynakta okunmadığı için çizilmedi.
Çıktılar: şeffaf köşeli 2000 px PNG ve Trendyol'a yüklemek için beyaz zeminli kare JPG.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "..", "ivex-icerik", "uretim", "fonts")
S = 2000
C = S / 2
R = 980  # badge radius
CREAM = (248, 246, 240)
TEAL = (26, 78, 92)
TAN = (196, 154, 110)
TAN_LIGHT = (232, 214, 190)


def P(x, y):
    """Badge units (radius = 1, y down) to pixels."""
    return (C + x * R, C + y * R)


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Montserrat_{weight}.ttf"), size)


def spaced(d, text, fnt, cx, cy, width, fill):
    """Draw `text` centred on (cx, cy), letter-spaced so it spans `width` px."""
    glyphs = [d.textlength(ch, font=fnt) for ch in text]
    gap = (width - sum(glyphs)) / (len(text) - 1)
    top, bottom = fnt.getbbox("MH")[1], fnt.getbbox("MH")[3]
    x, y = cx - width / 2, cy - (top + bottom) / 2
    for ch, w in zip(text, glyphs):
        d.text((x, y), ch, font=fnt, fill=fill)
        x += w + gap


def ring(d, r, width, fill):
    d.ellipse((C - r * R, C - r * R, C + r * R, C + r * R), outline=fill, width=round(width * R))


def diamond(im, cy, hw, hh):
    """Kilim lattice in a rhombus behind the M."""
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = [P(0, cy - hh), P(hw, cy), P(0, cy + hh), P(-hw, cy)]
    d.polygon(pts, fill=TAN_LIGHT)
    n = 7
    for k in range(1, n):
        u = k / n
        # lines parallel to the upper-right / lower-left edges, and to the other pair
        a0 = (0 - hw * u, cy - hh + hh * u)
        d.line([P(*a0), P(a0[0] + hw, a0[1] + hh)], fill=TAN, width=round(0.012 * R))
        b0 = (0 + hw * u, cy - hh + hh * u)
        d.line([P(*b0), P(b0[0] - hw, b0[1] + hh)], fill=TAN, width=round(0.012 * R))
    d.polygon(pts, outline=TAN, width=round(0.016 * R))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    layer.putalpha(Image.composite(layer.getchannel("A"), mask, mask))
    im.alpha_composite(layer)


M_SHAPE = [(-0.43, -0.06), (-0.43, -0.68), (-0.24, -0.68), (0.0, -0.38), (0.24, -0.68), (0.43, -0.68),
           (0.43, -0.06), (0.27, -0.06), (0.27, -0.44), (0.0, -0.17), (-0.27, -0.44), (-0.27, -0.06)]


def letter_m(im):
    d = ImageDraw.Draw(im)
    pts = [P(x, y) for x, y in M_SHAPE]
    d.polygon(pts, outline=CREAM, width=round(0.05 * R))  # a cream gap between the M and the lattice
    d.polygon(pts, fill=TEAL)
    w = round(0.011 * R)
    for sx in (-1, 1):  # woven lines: two per stem, two along each diagonal
        for x in (0.43 - 0.045, 0.27 + 0.045):
            d.line([P(sx * x, -0.63), P(sx * x, -0.11)], fill=CREAM, width=w)
        for off in (0.055, -0.055):
            d.line([P(sx * (0.255 + off), -0.63), P(sx * (0.02 + off * 0.2), -0.29 + off * 0.9)], fill=CREAM, width=w)
        zig = []  # a kilim zigzag down the middle of each stem
        for k in range(13):
            y = -0.61 + k * 0.04
            zig.append(P(sx * (0.35 + (0.03 if k % 2 else -0.03)), y))
        d.line(zig, fill=CREAM, width=round(w * 0.85), joint="curve")


def sprig(im, side, color):
    """A wheat/leaf branch growing outwards from the M at mid-height."""
    d = ImageDraw.Draw(im)
    x0, x1, y = 0.46, 0.64, -0.32
    stem = [P(side * (x0 + (x1 - x0) * u), y - 0.03 * math.sin(math.pi * u)) for u in [k / 20 for k in range(21)]]
    d.line(stem, fill=color, width=round(0.012 * R), joint="curve")

    def leaf(cx, cy, ang):
        img = Image.new("RGBA", (round(0.10 * R), round(0.032 * R)), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((0, 0, img.width - 1, img.height - 1), fill=color)
        img = img.rotate(ang, expand=True, resample=Image.BICUBIC)
        px, py = P(cx, cy)
        im.alpha_composite(img, (round(px - img.width / 2), round(py - img.height / 2)))

    # pairs of leaves along the stem, all leaning outwards, and one leaf at the tip
    for k in range(4):
        u = 0.08 + k * 0.25
        bx = x0 + (x1 - x0) * u
        by = y - 0.03 * math.sin(math.pi * u)
        for up in (-1, 1):
            ang = 40 if up < 0 else -40  # drawn for the right-hand sprig, mirrored below
            leaf(side * (bx + 0.03), by + up * 0.022, ang * side)
    leaf(side * (x1 + 0.04), y, 0)


def motif(im, x):
    """Small kilim block either side of the bottom of the badge."""
    d = ImageDraw.Draw(im)
    w, h, y = 0.065, 0.17, 0.66
    x0, y0 = P(x - w / 2, y - h / 2)
    x1, y1 = P(x + w / 2, y + h / 2)
    d.rounded_rectangle((x0, y0, x1, y1), radius=round(0.01 * R), fill=TAN)
    for k in range(3):
        cy = y0 + (y1 - y0) * (k + 1) / 4
        cx = (x0 + x1) / 2
        r = (x1 - x0) * 0.28
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=CREAM)


def main():
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((C - R, C - R, C + R, C + R), fill=CREAM)
    ring(d, 0.83, 0.022, TEAL)
    ring(d, 0.775, 0.009, TAN)
    diamond(im, -0.37, 0.36, 0.40)
    letter_m(im)
    sprig(im, -1, TEAL)
    sprig(im, 1, TAN)
    d = ImageDraw.Draw(im)
    spaced(d, "MİNAH", font("700Bold", 300), C, C + 0.16 * R, 1.23 * R, TEAL)
    spaced(d, "TEKSTİL", font("600SemiBold", 205), C, C + 0.43 * R, 0.97 * R, TAN)
    motif(im, -0.52)
    motif(im, 0.52)
    im.save(os.path.join(HERE, "minah-tekstil-logo.png"))
    sq = Image.new("RGB", (S, S), (255, 255, 255))
    sq.paste(im, (0, 0), im)
    sq.resize((1200, 1200), Image.LANCZOS).save(os.path.join(HERE, "minah-tekstil-logo-kare.jpg"), quality=95)
    print("kaydedildi:", os.path.join(HERE, "minah-tekstil-logo.png"), "ve -kare.jpg")


if __name__ == "__main__":
    main()
