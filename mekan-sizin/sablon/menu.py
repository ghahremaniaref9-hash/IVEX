"""Mekan Sizin - menü ve kampanya karuseli (1080x1350, birden çok kare).

Kullanım:  python3 menu.py menu.json
1. kare: kampanya kapağı (adisyon fişi).  Sonraki kareler: masada duran basılı menü kartı.
Fiyatlar ve kampanya menu.json içinden değişir; tasarıma dokunmadan güncellenir.
"""
import json
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from foto import film_grain, process
from mac_bileti import CREAM, INK, RED, barcode, fit_font, font, handwriting, noise, paper_texture, path, stamp, tracked
from story import darken

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
GREY = (112, 106, 98)


def tl(v):
    return f"{v:,}".replace(",", ".") + " TL"


def drop(img, layer, xy, angle, blur=16, alpha=0.8, offset=(10, 18)):
    """Rotate `layer`, cast a soft shadow and composite it at `xy` (top-left of the rotated layer)."""
    r = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    x, y = xy if xy[0] is not None else ((W - r.width) // 2, xy[1])
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = Image.new("RGBA", r.size, (0, 0, 0, 0))
    s.putalpha(r.getchannel("A").point(lambda v: int(v * alpha)))
    sh.paste(s, (x + offset[0], y + offset[1]))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(blur)))
    img.alpha_composite(r, (x, y))
    return img, (x, y, r.width, r.height)


def table_background(seed=91):
    """Dark, slightly warm table top (no photo) for the menu pages."""
    tex = 0.5 * noise((W, H), 3, seed) + 0.3 * noise((W, H), 14, seed + 1) + 0.2 * noise((W, H), 60, seed + 2)
    base = 20 + (tex - 0.5) * 22
    bg = np.dstack([base * 1.04, base, base * 0.94])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / W, (yy - H / 2) / H)
    bg *= (1 - 0.5 * np.clip(r - 0.2, 0, 1))[..., None]
    return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))


def leader_row(d, x0, x1, y, left, right, fl, fr, color=INK, price_color=INK, dot_color=(150, 142, 130)):
    d.text((x0, y), left, font=fl, fill=color, anchor="ls")
    rw = d.textlength(right, font=fr)
    d.text((x1, y), right, font=fr, fill=price_color, anchor="rs")
    lw = d.textlength(left, font=fl)
    x = x0 + lw + 14
    while x < x1 - rw - 14:
        d.ellipse((x, y - 5, x + 3, y - 2), fill=dot_color)
        x += 11


# --------------------------------------------------------------------------- cover

def receipt(cfg):
    k = cfg["kampanya"]
    rw, rh = 560, 600
    arr = np.dstack([np.full((rh, rw), c, np.float32) for c in (245, 243, 237)])
    arr += ((noise((rw, rh), 2, 101) - 0.5) * 7)[..., None]
    rc = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(rc)
    mono = font("SpaceMono_700Bold.ttf", 21)
    mono_s = font("SpaceMono_700Bold.ttf", 16)
    ink = (52, 50, 48)

    d.text((rw / 2, 34), "MEKAN SİZİN", font=font("Oswald_700Bold.ttf", 40), fill=INK, anchor="mt")
    d.text((rw / 2, 92), "BEŞİKTAŞ ÇARŞI", font=mono_s, fill=ink, anchor="mt")
    d.text((rw / 2, 116), "ADİSYON No 1903 · MASA: SENİN", font=mono_s, fill=ink, anchor="mt")

    def dashes(y):
        for x in range(36, rw - 36, 16):
            d.line((x, y, x + 8, y), fill=(120, 116, 110), width=2)

    dashes(150)
    rows = [("RAKI", "TÜM BOYLAR"), ("GÜN", k["gun_kisa"]), ("SAAT", k["saat"]) if k.get("saat") else ("MAÇ", "DEV EKRAN")]
    y = 188
    for left, right in rows:
        leader_row(d, 40, rw - 40, y, left, right, mono, mono, color=ink, price_color=ink, dot_color=(160, 156, 150))
        y += 34
    dashes(y - 8)
    tracked(d, (rw / 2, y + 8), "İNDİRİM", font("Montserrat_700Bold.ttf", 19), ink, 8, anchor_center=True)
    d.text((rw / 2, y + 36), k["oran"], font=font("Anton_400Regular.ttf", 150), fill=RED, anchor="mt")
    yb = rh - 100
    dashes(yb - 14)
    barcode(d, 110, yb, rw - 220, 36, 77)
    d.text((rw / 2, yb + 50), "AFİYET OLSUN · TEŞEKKÜRLER", font=mono_s, fill=ink, anchor="mt")

    # Torn zig-zag edges on top and bottom
    mask = Image.new("L", (rw, rh), 255)
    md = ImageDraw.Draw(mask)
    rng = random.Random(5)
    for edge_y, sign in ((0, 1), (rh - 1, -1)):
        pts = [(0, edge_y)]
        x = 0
        while x < rw:
            pts.append((x + 7, edge_y + sign * rng.uniform(7, 11)))
            x += 14
            pts.append((x, edge_y))
        pts.append((rw, edge_y))
        md.polygon(pts, fill=0)
    rc.putalpha(ImageChops.multiply(rc.getchannel("A"), mask))
    return rc


def cover(cfg):
    k = cfg["kampanya"]
    img = darken(process(dict(cfg["kapak_foto"], gren=0), (W, H)), *cfg.get("kapak_karartma", (0.5, 0.55, 0.85))).convert("RGBA")
    d = ImageDraw.Draw(img)
    logo = Image.open(path("assets/mekan-sizin-plaka-logo.png")).convert("RGBA")
    lw = 380
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, 56))
    tracked(d, (W / 2, 142), k["ust_satir"], font("Montserrat_600SemiBold.ttf", 22), CREAM, 7, anchor_center=True)
    d.text((W / 2, 290), k["baslik"], font=fit_font("Anton_400Regular.ttf", 170, k["baslik"], 960), fill=(250, 248, 244), anchor="mm")
    hw = handwriting(k["el_yazisi_baslik"], 58, RED, 4)
    img.alpha_composite(hw, (W - hw.width - 90, 356))

    img, (rx, ry, rwid, rht) = drop(img, receipt(cfg), (None, 456), 2.0)
    st = stamp(k["damga_ust"], k["damga_alt"], seed=37).rotate(-11, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(st, (rx + rwid - 150, ry + rht - 250))

    d = ImageDraw.Draw(img)
    d.text((70, 1110), k["alt_baslik"], font=fit_font("Anton_400Regular.ttf", 54, k["alt_baslik"], 940), fill=(250, 248, 244))
    d.text((72, 1176), k["alt_metin"], font=font("Montserrat_500Medium.ttf", 23), fill=(214, 208, 198))
    d.line((70, 1224, W - 70, 1224), fill=(255, 255, 255, 70), width=1)
    pin_x, pin_y = 72, 1246
    d.ellipse((pin_x, pin_y, pin_x + 20, pin_y + 20), fill=RED)
    d.polygon([(pin_x + 2, pin_y + 13), (pin_x + 18, pin_y + 13), (pin_x + 10, pin_y + 30)], fill=RED)
    d.ellipse((pin_x + 6, pin_y + 6, pin_x + 14, pin_y + 14), fill=(20, 20, 20))
    d.text((pin_x + 34, pin_y + 2), cfg["adres"], font=font("Montserrat_500Medium.ttf", 21), fill=(225, 222, 214))
    hw2 = handwriting(k["el_yazisi_alt"], 50, CREAM, 3)
    img.alpha_composite(hw2, (W - hw2.width - 70, 1276))
    return film_grain(img.convert("RGB"), 7.0, seed=21)


# --------------------------------------------------------------------------- menu pages

def taped_photo(item, size):
    ph = process(dict(item, boyut=list(size), gren=0, vinyet=0.2), size).convert("RGBA")
    border = 14
    framed = Image.new("RGBA", (size[0] + border * 2, size[1] + border * 2), (250, 248, 242, 255))
    framed.alpha_composite(ph, (border, border))
    return framed


def tape(w=150, h=46, seed=3):
    arr = np.dstack([np.full((h, w), c, np.float32) for c in (232, 224, 200)])
    arr += ((noise((w, h), 2, seed) - 0.5) * 12)[..., None]
    t = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    t.putalpha(150)
    return t


def menu_page(cfg, page, index, total):
    img = table_background(91 + index).convert("RGBA")
    cw, ch = 960, 1250
    card = paper_texture((cw, ch), 40 + index).convert("RGBA")
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((18, 18, cw - 19, ch - 19), radius=8, outline=(96, 90, 82), width=2)
    d.rounded_rectangle((28, 28, cw - 29, ch - 29), radius=6, outline=(160, 152, 140), width=1)

    logo = Image.open(path("assets/mekan-sizin-plaka-logo.png")).convert("RGBA")
    lw = 300
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    card.alpha_composite(logo, ((cw - lw) // 2, 58))
    tracked(d, (cw / 2, 128), "MENÜ · BEŞİKTAŞ ÇARŞI", font("Montserrat_700Bold.ttf", 16), GREY, 7, anchor_center=True)
    d.text((cw - 64, 72), f"{index + 1}/{total}", font=font("SpaceMono_700Bold.ttf", 18), fill=GREY, anchor="ra")

    y = 176
    if page.get("foto"):
        pw, ph = 760, page.get("foto_yukseklik", 400)
        fr = taped_photo(page["foto"], (pw, ph))
        fr = fr.rotate(-1.6, resample=Image.BICUBIC, expand=True)
        sx = (cw - fr.width) // 2
        sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
        s = Image.new("RGBA", fr.size, (0, 0, 0, 0))
        s.putalpha(fr.getchannel("A").point(lambda v: int(v * 0.35)))
        sh.paste(s, (sx + 5, y + 8))
        card = Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(6)))
        card.alpha_composite(fr, (sx, y))
        for tx, ang in ((sx - 40, 28), (sx + fr.width - 110, -24)):
            tp = tape(seed=tx).rotate(ang, resample=Image.BICUBIC, expand=True)
            card.alpha_composite(tp, (tx, y - 26))
        d = ImageDraw.Draw(card)
        y += fr.height + 40

    item_f = font("Montserrat_600SemiBold.ttf", 25)
    price_f = font("Oswald_700Bold.ttf", 28)
    x0, x1 = 84, cw - 84
    sections = cfg["bolumler"]
    for name in page["bolumler"]:
        sec = sections[name]
        d.text((x0, y), name, font=font("Anton_400Regular.ttf", 62), fill=INK)
        hb = d.textbbox((x0, y), name, font=font("Anton_400Regular.ttf", 62))
        d.rectangle((x0, hb[3] + 10, x0 + 90, hb[3] + 16), fill=RED)
        if sec.get("not"):
            note = handwriting(sec["not"], 46, RED, 3)
            card.alpha_composite(note, (x1 - note.width + 6, y + 4))
            d = ImageDraw.Draw(card)
        y = hb[3] + 42
        cols = sec.get("sutunlar")
        if cols:
            for cx_, label in zip((x1 - 170, x1), cols):
                d.text((cx_, y), label, font=font("Montserrat_700Bold.ttf", 14), fill=GREY, anchor="ra")
            y += 30
        for group in sec.get("gruplar", [{"ad": None, "urunler": sec.get("urunler", [])}]):
            if group["ad"]:
                tracked(d, (x0, y - 4), group["ad"], font("Oswald_700Bold.ttf", 26), RED, 3)
                y += 40
            for it in group["urunler"]:
                label, price = it[0], it[1]
                ry = y + 26
                if isinstance(price, list) and sec.get("indirim"):
                    leader_row(d, x0, x1 - 190, ry, label, tl(price[0]), item_f, price_f)
                    d.text((x1, ry), tl(price[1]), font=price_f, fill=RED, anchor="rs")
                elif isinstance(price, list):
                    leader_row(d, x0, x1, ry, label, " · ".join(tl(p) for p in price), item_f, price_f)
                else:
                    leader_row(d, x0, x1, ry, label, tl(price), item_f, price_f)
                y += sec.get("satir", 50)
            y += 8
        y += 34
    if page.get("dipnot"):
        d.text((x0, ch - 92), page["dipnot"], font=font("Montserrat_600SemiBold.ttf", 19), fill=GREY)
    if page.get("imza", True):
        hw = handwriting(cfg.get("el_yazisi_menu", "Afiyet olsun!"), 52, RED, 4)
        card.alpha_composite(hw, (cw - hw.width - 70, ch - 128))

    corner = Image.new("L", card.size, 0)
    ImageDraw.Draw(corner).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=10, fill=255)
    card.putalpha(corner)
    img, _ = drop(img, card, (None, 38), -0.8 + 0.6 * (index % 2), blur=20, alpha=0.85)
    return film_grain(img.convert("RGB"), 6.0, seed=31 + index)


def with_discount(cfg):
    """Fill discounted prices for sections marked 'indirim' (e.g. weekday rakı -20%)."""
    oran = cfg["kampanya"]["indirim_yuzde"]
    for sec in cfg["bolumler"].values():
        if not sec.get("indirim"):
            continue
        for g in sec.get("gruplar", []):
            g["urunler"] = [[n, [p, round(p * (100 - oran) / 100)]] for n, p in g["urunler"]]


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "menu.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    with_discount(cfg)
    prefix = path(cfg["cikti_oneki"])
    cover(cfg).save(f"{prefix}-1-kapak.png")
    print("kaydedildi:", f"{prefix}-1-kapak.png")
    if cfg.get("sadece_kapak"):
        return
    pages = cfg["sayfalar"]
    total = len(pages) + 1
    for i, page in enumerate(pages, start=1):
        out = f"{prefix}-{i + 1}-{page['dosya']}.png"
        menu_page(cfg, page, i, total).save(out)
        print("kaydedildi:", out)


if __name__ == "__main__":
    main()
