"""Mekan Sizin - 'Maç Bileti' maç günü afişi (1080x1350).

Kullanım:  python3 mac_bileti.py mac-bileti.json
Takım adları, armalar, tarih, saat ve metinler JSON dosyasından okunur.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
RED = (200, 16, 46)
INK = (24, 22, 20)
PAPER = (238, 231, 216)
CREAM = (242, 236, 224)


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def path(p):
    return p if os.path.isabs(p) else os.path.join(HERE, p)


def tracked(d, xy, text, fnt, fill, tracking, anchor_center=False):
    """Draw letter-spaced text; returns its width."""
    width = sum(d.textlength(c, font=fnt) for c in text) + tracking * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= width / 2
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill)
        x += d.textlength(c, font=fnt) + tracking
    return width


def fit_font(name, size, text, max_w):
    """Largest font (up to `size`) that keeps `text` within `max_w` pixels."""
    f = font(name, size)
    while size > 40 and f.getlength(text) > max_w:
        size -= 4
        f = font(name, size)
    return f


def noise(size, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.random((max(1, size[1] // scale), max(1, size[0] // scale)))
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize(size, Image.BICUBIC)).astype(np.float32) / 255


def background(cfg):
    # Concrete-like charcoal wall: a few noise octaves, very low contrast
    tex = 0.5 * noise((W, H), 3, 1) + 0.3 * noise((W, H), 14, 2) + 0.2 * noise((W, H), 60, 3)
    base = 16 + (tex - 0.5) * 22
    bg = np.dstack([base, base, base * 0.97])

    # Real stadium photo at the bottom, black & white with punchy contrast
    photo = Image.open(path(cfg["arka_plan"])).convert("L")
    photo = ImageOps.autocontrast(photo, cutoff=1)
    photo = ImageEnhance.Contrast(photo).enhance(1.25)
    ph = photo.height * W // photo.width
    photo = photo.resize((W, ph), Image.LANCZOS)
    p = np.asarray(photo).astype(np.float32) * 0.62
    y0 = H - ph
    t = np.clip((np.arange(ph) - 40) / 260, 0, 1)[:, None]  # fade the photo's top into the wall
    t = t * t * (3 - 2 * t)
    region = bg[y0:H]
    bg[y0:H] = region * (1 - t[..., None]) + np.dstack([p, p, p]) * t[..., None]

    # Bottom darkening for the text block
    g = np.clip((np.arange(H) - 1020) / 330, 0, 1)[:, None, None]
    bg = bg * (1 - 0.55 * g)
    return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))


def paper_texture(size, seed):
    tex = 0.6 * noise(size, 2, seed) + 0.4 * noise(size, 25, seed + 1)
    fibers = noise((size[0], size[1]), 1, seed + 2)
    arr = np.dstack([np.full(size[::-1], c, np.float32) for c in PAPER])
    arr += ((tex - 0.5) * 14 + (fibers - 0.5) * 6)[..., None]
    # slightly warmer, worn edges
    yy, xx = np.mgrid[0:size[1], 0:size[0]]
    edge = np.minimum.reduce([xx, yy, size[0] - xx, size[1] - yy]).astype(np.float32)
    arr -= (np.clip(1 - edge / 22, 0, 1) ** 2 * 18)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def barcode(d, x, y, w, h, seed):
    rng = random.Random(seed)
    cx = x
    while cx < x + w:
        bw = rng.choice([2, 2, 3, 4, 6])
        if rng.random() > 0.35:
            d.rectangle((cx, y, cx + bw - 1, y + h), fill=INK)
        cx += bw + rng.choice([2, 3, 4])


def ticket(cfg):
    tw, th, stub = 900, 400, 250
    main_w = tw - stub
    t = paper_texture((tw, th), 7).convert("RGBA")
    d = ImageDraw.Draw(t)

    # Inner frame + perforation line between the main part and the stub
    d.rounded_rectangle((16, 16, tw - 17, th - 17), radius=10, outline=(70, 66, 60), width=2)
    for yy in range(30, th - 30, 16):
        d.ellipse((main_w - 4, yy, main_w + 4, yy + 8), fill=(205, 198, 184))

    # Header strip
    tracked(d, (40, 34), "MAÇ BİLETİ", font("Montserrat_700Bold.ttf", 17), (60, 56, 50), 6)
    tracked(d, (main_w - 40 - 150, 34), cfg["seri_no"], font("Montserrat_600SemiBold.ttf", 15), (110, 104, 96), 2)
    d.line((40, 64, main_w - 40, 64), fill=(120, 114, 104), width=1)

    # Crests, VS and team names
    crest_h = 196
    centers = (172, main_w - 172)
    names = font("Oswald_700Bold.ttf", 30)
    for (team, cx) in zip((cfg["ev_sahibi"], cfg["deplasman"]), centers):
        c = Image.open(path(team["arma"])).convert("RGBA")
        c = c.resize((round(c.width * crest_h / c.height), crest_h), Image.LANCZOS)
        shadow = Image.new("RGBA", t.size, (0, 0, 0, 0))
        s = Image.new("RGBA", c.size, (40, 30, 20, 0))
        s.putalpha(c.getchannel("A").point(lambda v: int(v * 0.35)))
        shadow.paste(s, (round(cx - c.width / 2) + 3, 82 + 5))
        t = Image.alpha_composite(t, shadow.filter(ImageFilter.GaussianBlur(4)))
        t.alpha_composite(c, (round(cx - c.width / 2), 82))
        d = ImageDraw.Draw(t)
        d.text((cx, 300), team["ad"], font=names, fill=INK, anchor="mt")
    d.text((main_w / 2, 178), "VS", font=font("Anton_400Regular.ttf", 72), fill=RED, anchor="mm")

    # Stub: date / time / tribune + barcode
    sx = main_w + 30
    label = font("Montserrat_700Bold.ttf", 13)
    tracked(d, (sx, 40), "TARİH", label, (120, 114, 104), 4)
    d.text((sx, 58), cfg["tarih"], font=font("Oswald_700Bold.ttf", 28), fill=INK)
    tracked(d, (sx, 112), "SAAT", label, (120, 114, 104), 4)
    d.text((sx - 2, 126), cfg["saat"], font=font("Anton_400Regular.ttf", 66), fill=RED)
    tracked(d, (sx, 222), "TRİBÜN", label, (120, 114, 104), 4)
    d.text((sx, 240), cfg["tribun"], font=font("Oswald_700Bold.ttf", 28), fill=INK)
    barcode(d, sx, 300, stub - 60, 56, 11)

    # Notches at the perforation (top and bottom)
    cut = Image.new("L", t.size, 255)
    cd = ImageDraw.Draw(cut)
    cd.ellipse((main_w - 18, -18, main_w + 18, 18), fill=0)
    cd.ellipse((main_w - 18, th - 18, main_w + 18, th + 18), fill=0)
    corner = Image.new("L", t.size, 0)
    ImageDraw.Draw(corner).rounded_rectangle((0, 0, tw - 1, th - 1), radius=14, fill=255)
    t.putalpha(ImageChops.multiply(ImageChops.multiply(t.getchannel("A"), cut), corner))
    return t


def stamp(text_top, text_bottom, seed=5):
    sw, sh = 380, 136
    s = Image.new("L", (sw, sh), 0)
    d = ImageDraw.Draw(s)
    d.rounded_rectangle((4, 4, sw - 5, sh - 5), radius=14, outline=255, width=6)
    d.rounded_rectangle((16, 16, sw - 17, sh - 17), radius=8, outline=255, width=2)
    d.text((sw / 2, 56), text_top, font=font("Anton_400Regular.ttf", 60), fill=255, anchor="mm")
    tracked(d, (sw / 2, 94), text_bottom, font("Montserrat_700Bold.ttf", 16), 255, 4, anchor_center=True)
    # Uneven ink: speckles and patchy pressure
    patch = noise((sw, sh), 18, seed) * 0.6 + noise((sw, sh), 3, seed + 1) * 0.4
    ink = np.asarray(s).astype(np.float32) / 255 * np.clip((patch - 0.06) * 2.6, 0.25, 1)
    a = Image.fromarray((ink * 235).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    out = Image.new("RGBA", (sw, sh), RED + (0,))
    out.putalpha(a)
    return out


def handwriting(text, size, color, angle):
    f = font("CaveatBrush_400Regular.ttf", size)
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    w = int(tmp.textlength(text, font=f)) + 20
    im = Image.new("RGBA", (w, int(size * 1.4)), color + (0,))
    a = Image.new("L", im.size, 0)
    ImageDraw.Draw(a).text((10, 0), text, font=f, fill=255)
    im.putalpha(a)
    return im.rotate(angle, resample=Image.BICUBIC, expand=True)


def grain(img, amount=9, seed=3):
    rng = np.random.default_rng(seed)
    arr = np.asarray(img).astype(np.float32)
    n = rng.normal(0, amount, arr.shape[:2])[..., None]
    return Image.fromarray(np.clip(arr + n, 0, 255).astype(np.uint8))


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "mac-bileti.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    img = background(cfg).convert("RGBA")
    d = ImageDraw.Draw(img)

    # Logo + kicker + headline
    logo = Image.open(path(cfg["logo"])).convert("RGBA")
    lw = 380
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, 56))
    tracked(d, (W / 2, 142), cfg["ust_satir"], font("Montserrat_600SemiBold.ttf", 22), CREAM, 7, anchor_center=True)
    baslik = cfg.get("baslik", "MAÇ GÜNÜ")
    d.text((W / 2, 318), baslik, font=fit_font("Anton_400Regular.ttf", 190, baslik, 940), fill=(250, 248, 244), anchor="mm")
    hw = handwriting(cfg["el_yazisi_baslik"], 58, RED, 4)
    img.alpha_composite(hw, (W - hw.width - 92, 382))

    # Ticket, slightly rotated with a soft shadow
    t = ticket(cfg)
    angle = -2.6
    tr = t.rotate(angle, resample=Image.BICUBIC, expand=True)
    tx, ty = (W - tr.width) // 2, 492
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = Image.new("RGBA", tr.size, (0, 0, 0, 0))
    s.putalpha(tr.getchannel("A").point(lambda v: int(v * 0.75)))
    sh.paste(s, (tx + 10, ty + 18))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(16)))
    img.alpha_composite(tr, (tx, ty))

    # 'CANLI YAYIN' rubber stamp over the ticket's lower-right corner
    st = stamp("CANLI YAYIN", "MEKAN SİZİN'DE").rotate(-9, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(st, (W - st.width - 22, 872))

    # Bottom block
    d = ImageDraw.Draw(img)
    d.text((70, 1060), cfg["alt_baslik"], font=font("Anton_400Regular.ttf", 66), fill=(250, 248, 244))
    d.text((72, 1148), cfg["alt_metin"], font=font("Montserrat_500Medium.ttf", 25), fill=(210, 206, 198))
    d.line((70, 1212, W - 70, 1212), fill=(255, 255, 255, 70), width=1)
    pin_x, pin_y = 72, 1238
    d.ellipse((pin_x, pin_y, pin_x + 20, pin_y + 20), fill=RED)
    d.polygon([(pin_x + 2, pin_y + 13), (pin_x + 18, pin_y + 13), (pin_x + 10, pin_y + 30)], fill=RED)
    d.ellipse((pin_x + 6, pin_y + 6, pin_x + 14, pin_y + 14), fill=(20, 20, 20))
    d.text((pin_x + 34, pin_y + 2), cfg["adres"], font=font("Montserrat_500Medium.ttf", 21), fill=(225, 222, 214))
    hw2 = handwriting(cfg["el_yazisi_alt"], 52, CREAM, 3)
    img.alpha_composite(hw2, (W - hw2.width - 70, 1268))

    out = grain(img.convert("RGB"))
    out_path = path(cfg["cikti"])
    out.save(out_path)
    print("kaydedildi:", out_path)


if __name__ == "__main__":
    main()
