"""Mekan Sizin - Süper Lig deplasman afişi: 'Deplasman Biniş Kartı' (1080x1350).

Kullanım:  python3 deplasman.py deplasman.json
Rakibin şehir/stadyum/mesafe bilgisi sehirler.json'dan otomatik gelir.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from mac_bileti import CREAM, INK, RED, barcode, fit_font, font, grain, handwriting, noise, path, stamp, tracked

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
HOME = (41.043, 29.007)  # Beşiktaş Çarşı


def km_between(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def km_label(km):
    if km < 50:
        return f"≈ {round(km)} km"
    step = 10 if km < 1000 else 50
    return "≈ " + f"{round(km / step) * step:,}".replace(",", ".") + " km"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def monogram(text, colors, size):
    """Simple lettered roundel used when no crest file is provided."""
    ss = 3
    s = size * ss
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c1, c2 = hex_rgb(colors[0]), hex_rgb(colors[1])
    d.ellipse((0, 0, s - 1, s - 1), fill=c1)
    d.ellipse((s * 0.07, s * 0.07, s * 0.93, s * 0.93), outline=c2, width=round(s * 0.035))
    f = ImageFont.truetype(os.path.join(HERE, "fonts", "Anton_400Regular.ttf"), round(s * (0.42 if len(text) <= 2 else 0.30)))
    d.text((s / 2, s / 2), text, font=f, fill=c2, anchor="mm")
    return im.resize((size, size), Image.LANCZOS)


def crest(team, size):
    if team.get("arma") and os.path.exists(path(team["arma"])):
        c = Image.open(path(team["arma"])).convert("RGBA")
        return c.resize((round(c.width * size / c.height), size), Image.LANCZOS)
    return monogram(team["kisaltma"], team["renkler"], size)


def contour_background():
    """Dark map-like background: topographic contour lines from smooth noise."""
    field = 0.55 * noise((W, H), 90, 21) + 0.3 * noise((W, H), 40, 22) + 0.15 * noise((W, H), 15, 23)
    bands = (field * 18) % 1.0
    lines = np.clip(1 - np.abs(bands - 0.5) / 0.035, 0, 1)  # thin iso-lines
    base = 15 + (noise((W, H), 3, 24) - 0.5) * 10
    v = base + lines * 40
    bg = np.dstack([v, v, v * 0.98])
    yy = np.arange(H)[:, None, None]
    bg *= 1 - 0.45 * np.clip((yy - 1000) / 350, 0, 1)
    return Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8))


def boarding_pass(cfg, opp, bjk_crest):
    bw, bh = 940, 420
    card = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=22, fill=(246, 244, 239))
    # paper grain
    g = (noise((bw, bh), 2, 31) - 0.5) * 10
    arr = np.asarray(card).astype(np.float32)
    arr[..., :3] += g[..., None]
    card = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(card)

    # Header band
    d.rounded_rectangle((0, 0, bw - 1, 70), radius=22, fill=RED)
    d.rectangle((0, 40, bw - 1, 70), fill=RED)
    tracked(d, (34, 24), "DEPLASMAN BİNİŞ KARTI", font("Montserrat_700Bold.ttf", 20), (255, 255, 255), 6)
    tracked(d, (bw - 34 - 230, 26), cfg["kicker_sag"], font("Montserrat_600SemiBold.ttf", 16), (255, 222, 226), 3)

    stub = 250
    main_w = bw - stub
    for yy in range(86, bh - 20, 16):
        d.ellipse((main_w - 4, yy, main_w + 4, yy + 8), fill=(200, 196, 188))

    # Route: FROM -> TO
    big = font("Anton_400Regular.ttf", 104)
    lab = font("Montserrat_700Bold.ttf", 13)
    grey = (120, 116, 108)
    tracked(d, (40, 94), "NEREDEN", lab, grey, 4)
    d.text((38, 108), "İST", font=big, fill=INK)
    d.text((40, 236), "İSTANBUL", font=font("Oswald_700Bold.ttf", 24), fill=INK)
    d.text((40, 268), "Beşiktaş Çarşı", font=font("Montserrat_500Medium.ttf", 17), fill=grey)
    rx = main_w - 40
    tracked(d, (rx - 70, 94), "NEREYE", lab, grey, 4)
    d.text((rx, 108), opp["kod"], font=big, fill=RED, anchor="ra")
    d.text((rx, 236), opp["sehir"], font=font("Oswald_700Bold.ttf", 24), fill=INK, anchor="ra")
    d.text((rx, 268), opp["stadyum"], font=font("Montserrat_500Medium.ttf", 17), fill=grey, anchor="ra")
    # dashed flight path with an arrow head
    x0, x1, yl = 250, rx - 230, 172
    for x in range(x0, x1, 18):
        d.line((x, yl, x + 9, yl), fill=(60, 58, 54), width=3)
    d.polygon([(x1 + 6, yl), (x1 - 12, yl - 10), (x1 - 12, yl + 10)], fill=(60, 58, 54))
    tracked(d, ((x0 + x1) / 2, 192), "KUŞ UÇUŞU " + cfg["mesafe"], font("Montserrat_700Bold.ttf", 14), grey, 3, anchor_center=True)

    # Bottom field row
    d.line((40, 306, main_w - 40, 306), fill=(200, 196, 188), width=1)
    fields = [("MAÇ", cfg["mac"]), ("TARİH", cfg["tarih"]), ("SAAT", cfg["saat"]), ("KAPI", "MEKAN SİZİN")]
    fx = 40
    widths = [250, 160, 80, 150]
    for (k, v), fw in zip(fields, widths):
        tracked(d, (fx, 320), k, lab, grey, 4)
        d.text((fx, 338), v, font=font("Oswald_700Bold.ttf", 24), fill=RED if k == "SAAT" else INK)
        fx += fw

    # Stub: both crests + seat + barcode
    sx = main_w + 24
    c_size = 92
    oc = crest(opp, c_size)
    card.alpha_composite(oc, (sx + 6, 94))
    d.text((sx + 6 + oc.width + 14, 140), "×", font=font("Montserrat_700Bold.ttf", 28), fill=grey, anchor="lm")
    bc = bjk_crest.resize((round(bjk_crest.width * c_size / bjk_crest.height), c_size), Image.LANCZOS)
    card.alpha_composite(bc, (main_w + stub - 24 - bc.width, 94))
    tracked(d, (sx, 214), "KOLTUK", lab, grey, 4)
    d.text((sx, 232), "SENİN", font=font("Oswald_700Bold.ttf", 28), fill=INK)
    tracked(d, (sx + 110, 214), "SEFER", lab, grey, 4)
    d.text((sx + 110, 232), cfg["sefer"], font=font("Oswald_700Bold.ttf", 28), fill=INK)
    barcode(d, sx, 300, stub - 48, 76, 41)

    # notches at the perforation
    a = card.getchannel("A")
    ad = ImageDraw.Draw(a)
    ad.ellipse((main_w - 16, -16, main_w + 16, 16), fill=0)
    ad.ellipse((main_w - 16, bh - 16, main_w + 16, bh + 16), fill=0)
    card.putalpha(a)
    return card


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "deplasman.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    with open(os.path.join(HERE, "sehirler.json"), encoding="utf-8") as fh:
        teams = json.load(fh)
    opp = dict(teams[cfg["rakip"]])
    opp.update(cfg.get("rakip_ozel", {}))
    km = km_between(HOME, (opp["lat"], opp["lon"]))
    cfg.setdefault("mesafe", km_label(km))
    cfg.setdefault("mac", f"{opp['kisaltma']} – BJK")

    img = contour_background().convert("RGBA")
    d = ImageDraw.Draw(img)

    logo = Image.open(path("assets/mekan-sizin-plaka-logo.png")).convert("RGBA")
    lw = 380
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, 56))
    tracked(d, (W / 2, 142), cfg["ust_satir"], font("Montserrat_600SemiBold.ttf", 22), CREAM, 7, anchor_center=True)
    baslik = cfg.get("baslik", "DEPLASMAN")
    d.text((W / 2, 300), baslik, font=fit_font("Anton_400Regular.ttf", 172, baslik, 960), fill=(250, 248, 244), anchor="mm")
    hw = handwriting(cfg["el_yazisi_baslik"], 60, RED, 4)
    img.alpha_composite(hw, (W - hw.width - 96, 372))

    bjk = Image.open(path("assets/bjk.png")).convert("RGBA")
    card = boarding_pass(cfg, opp, bjk)
    cr = card.rotate(1.6, resample=Image.BICUBIC, expand=True)
    cx, cy = (W - cr.width) // 2, 486
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = Image.new("RGBA", cr.size, (0, 0, 0, 0))
    s.putalpha(cr.getchannel("A").point(lambda v: int(v * 0.75)))
    sh.paste(s, (cx + 8, cy + 18))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(16)))
    img.alpha_composite(cr, (cx, cy))

    st = stamp("CANLI YAYIN", "MEKAN SİZİN'DE", seed=9).rotate(7, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(st, (56, 918))

    d = ImageDraw.Draw(img)
    d.text((70, 1062), cfg["alt_baslik"], font=font("Anton_400Regular.ttf", 58), fill=(250, 248, 244))
    d.text((72, 1140), cfg["alt_metin"], font=font("Montserrat_500Medium.ttf", 24), fill=(210, 206, 198))
    d.line((70, 1206, W - 70, 1206), fill=(255, 255, 255, 70), width=1)
    pin_x, pin_y = 72, 1232
    d.ellipse((pin_x, pin_y, pin_x + 20, pin_y + 20), fill=RED)
    d.polygon([(pin_x + 2, pin_y + 13), (pin_x + 18, pin_y + 13), (pin_x + 10, pin_y + 30)], fill=RED)
    d.ellipse((pin_x + 6, pin_y + 6, pin_x + 14, pin_y + 14), fill=(20, 20, 20))
    d.text((pin_x + 34, pin_y + 2), cfg["adres"], font=font("Montserrat_500Medium.ttf", 21), fill=(225, 222, 214))
    hw2 = handwriting(cfg["el_yazisi_alt"], 50, CREAM, 3)
    img.alpha_composite(hw2, (W - hw2.width - 70, 1266))

    out = grain(img.convert("RGB"))
    out.save(path(cfg["cikti"]))
    print("kaydedildi:", path(cfg["cikti"]), "| mesafe:", cfg["mesafe"], f"({km:.0f} km)")


if __name__ == "__main__":
    main()
