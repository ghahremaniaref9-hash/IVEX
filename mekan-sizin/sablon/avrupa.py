"""Mekan Sizin - Avrupa maçları afişi: 'Kartal Pasaportu' (1080x1350). İç saha ve deplasman için tek şablon.

Kullanım:  python3 avrupa.py avrupa.json
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from deplasman import HOME, crest, hex_rgb, km_between, km_label
from mac_bileti import CREAM, INK, RED, font, grain, handwriting, noise, path, stamp, tracked

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
BLUE_INK = (34, 70, 140)


def night_background():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.dstack([np.full((H, W), 9.0), np.full((H, W), 12.0), np.full((H, W), 20.0)])
    # two floodlight beams from the top corners
    for (sx, sy, ang) in ((-60, -80, 0.95), (W + 60, -80, math.pi - 0.95)):
        dx, dy = xx - sx, yy - sy
        a = np.arctan2(dy, dx)
        beam = np.exp(-((a - ang) ** 2) / 0.012) * np.exp(-np.hypot(dx, dy) / 1300)
        base += beam[..., None] * np.array([70, 78, 95])
    glow = np.exp(-(((xx - W / 2) / 520) ** 2 + ((yy + 60) / 330) ** 2))
    base += glow[..., None] * np.array([26, 30, 40])
    base += ((noise((W, H), 3, 51) - 0.5) * 8)[..., None]
    base *= (1 - 0.4 * np.clip((yy - 1050) / 300, 0, 1))[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def guilloche(size):
    """Security-paper rosettes and waves, like a real passport page."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    col = (120, 150, 180, 70)
    for k, (cx, cy, R, r, dd) in enumerate([(w * 0.70, h * 0.48, 150, 37, 70), (w * 0.70, h * 0.48, 105, 29, 55)]):
        pts = []
        for i in range(4000):
            t = i / 4000 * 2 * math.pi * r
            x = (R - r) * math.cos(t) + dd * math.cos((R - r) / r * t)
            y = (R - r) * math.sin(t) - dd * math.sin((R - r) / r * t)
            pts.append((cx + x, cy + y))
        d.line(pts, fill=col, width=1)
    for j in range(14):
        y0 = 40 + j * (h - 80) / 13
        pts = [(x, y0 + 6 * math.sin(x / 38 + j * 0.7) + 3 * math.sin(x / 11 + j)) for x in range(0, w, 4)]
        d.line(pts, fill=(120, 150, 180, 38), width=1)
    return layer


def flag(spec, size):
    w, h = size
    im = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(im)
    cols = [hex_rgb(c) for c in spec.get("renkler", [])]
    if spec.get("tip") == "yatay":
        for i, c in enumerate(cols):
            d.rectangle((0, i * h / len(cols), w, (i + 1) * h / len(cols)), fill=c)
    elif spec.get("tip") == "dikey":
        for i, c in enumerate(cols):
            d.rectangle((i * w / len(cols), 0, (i + 1) * w / len(cols), h), fill=c)
    elif spec.get("tip") == "haç":  # e.g. England: white field, red cross
        d.rectangle((0, 0, w, h), fill=cols[0])
        t = h * 0.2
        d.rectangle((w / 2 - t / 2, 0, w / 2 + t / 2, h), fill=cols[1])
        d.rectangle((0, h / 2 - t / 2, w, h / 2 + t / 2), fill=cols[1])
    elif spec.get("tip") == "çapraz":  # e.g. Scotland: blue field, white saltire
        d.rectangle((0, 0, w, h), fill=cols[0])
        d.line((0, 0, w, h), fill=cols[1], width=round(h * 0.2))
        d.line((0, h, w, 0), fill=cols[1], width=round(h * 0.2))
    else:
        return None
    ImageDraw.Draw(im).rectangle((0, 0, w - 1, h - 1), outline=(60, 60, 60))
    return im


def circle_stamp(top, bottom, center1, center2, diameter=230, seed=61):
    s = Image.new("L", (diameter, diameter), 0)
    d = ImageDraw.Draw(s)
    r = diameter / 2
    d.ellipse((3, 3, diameter - 4, diameter - 4), outline=255, width=5)
    d.ellipse((30, 30, diameter - 31, diameter - 31), outline=255, width=2)
    f = font("Montserrat_700Bold.ttf", 17)

    def arc_text(text, radius, start_deg, clockwise=True):
        tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
        widths = [tmp.textlength(c, font=f) + 2 for c in text]
        total = sum(widths) / radius * 180 / math.pi
        ang = start_deg - (total / 2 if clockwise else -total / 2)
        for c, cw in zip(text, widths):
            step = cw / radius * 180 / math.pi
            mid = ang + (step / 2 if clockwise else -step / 2)
            g = Image.new("L", (40, 40), 0)
            ImageDraw.Draw(g).text((20, 20), c, font=f, fill=255, anchor="mm")
            g = g.rotate(-(mid + 90) if clockwise else -(mid - 90), resample=Image.BICUBIC)
            x = r + radius * math.cos(math.radians(mid)) - 20
            y = r + radius * math.sin(math.radians(mid)) - 20
            s.paste(255, (round(x), round(y)), g)
            ang += step if clockwise else -step

    arc_text(top, r - 18, -90, clockwise=True)
    arc_text(bottom, r - 18, 90, clockwise=False)
    d.text((r, r - 14), center1, font=font("Anton_400Regular.ttf", 34), fill=255, anchor="mm")
    d.text((r, r + 22), center2, font=font("Montserrat_700Bold.ttf", 16), fill=255, anchor="mm")
    patch = noise((diameter, diameter), 14, seed) * 0.6 + noise((diameter, diameter), 3, seed + 1) * 0.4
    ink = np.asarray(s).astype(np.float32) / 255 * np.clip((patch - 0.08) * 2.4, 0.3, 1)
    out = Image.new("RGBA", s.size, BLUE_INK + (0,))
    out.putalpha(Image.fromarray((ink * 220).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)))
    return out


def passport(cfg, opp, km):
    pw, ph = 900, 560
    arr = np.dstack([np.full((ph, pw), c, np.float32) for c in (226, 232, 236)])
    arr += ((noise((pw, ph), 2, 71) - 0.5) * 8)[..., None]
    page = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    page = Image.alpha_composite(page, guilloche((pw, ph)))
    d = ImageDraw.Draw(page)
    grey = (96, 108, 120)
    lab = font("Montserrat_700Bold.ttf", 12)

    tracked(d, (36, 30), "KARTAL PASAPORTU · EAGLE PASSPORT", font("Montserrat_700Bold.ttf", 16), (40, 52, 66), 4)
    tracked(d, (pw - 36 - 170, 31), "No 1903 / 2026-27", font("Montserrat_600SemiBold.ttf", 14), grey, 2)
    d.line((36, 58, pw - 36, 58), fill=(150, 165, 180), width=1)

    # "Photo": the BJK crest on a pale card, like an ID photo
    d.rectangle((36, 78, 236, 318), fill=(244, 246, 247), outline=(150, 165, 180), width=2)
    bjk = crest({"arma": "assets/bjk.png"}, 200)
    page.alpha_composite(bjk, (136 - bjk.width // 2, 98))
    tracked(d, (36, 330), "HAMİL / HOLDER", lab, grey, 3)
    d.text((36, 346), "KARTAL", font=font("Oswald_700Bold.ttf", 26), fill=INK)

    fx, fy = 270, 80
    rows = [
        ("MAÇ / MATCH", f"{cfg['ev_sahibi']} – {cfg['deplasman']}"),
        ("ŞEHİR / CITY", f"{cfg['sehir']}, {cfg['ulke']}"),
        ("STADYUM / STADIUM", cfg["stadyum"]),
        ("TARİH / DATE", cfg["tarih"]),
    ]
    for k, v in rows:
        tracked(d, (fx, fy), k, lab, grey, 3)
        d.text((fx, fy + 15), v, font=font("Oswald_700Bold.ttf", 27), fill=INK)
        fy += 62
    fl = flag(cfg.get("bayrak", {}), (54, 34))
    if fl is not None:
        x = fx + d.textlength(f"{cfg['sehir']}, {cfg['ulke']}", font=font("Oswald_700Bold.ttf", 27)) + 14
        page.paste(fl, (round(x), 80 + 62 + 18))
    tracked(d, (fx, fy), "SAAT / TIME (TSİ)", lab, grey, 3)
    d.text((fx, fy + 12), cfg["saat"], font=font("Anton_400Regular.ttf", 54), fill=RED)
    tracked(d, (fx + 200, fy), "KUŞ UÇUŞU", lab, grey, 3)
    d.text((fx + 200, fy + 20), km, font=font("Oswald_700Bold.ttf", 30), fill=INK)
    oc = crest(opp, 70)
    page.alpha_composite(oc, (pw - 36 - oc.width, fy + 4))

    # Machine readable zone
    mono = font("SpaceMono_700Bold.ttf", 21)
    def mrz(s):
        s = s.upper().translate(str.maketrans("ÇĞİIÖŞÜ ", "CGIIOSU<"))
        return (s + "<" * 44)[:44]
    d.rectangle((0, ph - 92, pw, ph), fill=(214, 222, 228))
    d.text((36, ph - 80), mrz(f"P<TUR{cfg['deplasman']}<<KARTAL<<{cfg['ev_sahibi']}"), font=mono, fill=(40, 48, 58))
    d.text((36, ph - 46), mrz(f"1903<{cfg['tarih_mrz']}<{cfg['sehir']}<<CANLI<YAYIN"), font=mono, fill=(40, 48, 58))

    stamp_c = circle_stamp(f"{cfg['sehir']} · {cfg['ulke']}", "GİRİŞ · ENTRY", cfg["tarih_damga"], "AVRUPA GECESİ")
    stamp_c = stamp_c.rotate(-14, resample=Image.BICUBIC, expand=True)
    page.alpha_composite(stamp_c, (pw - stamp_c.width - 40, 70))
    corner = Image.new("L", page.size, 0)
    ImageDraw.Draw(corner).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=16, fill=255)
    page.putalpha(corner)
    return page


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "avrupa.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    opp = cfg["rakip"]
    km = km_label(km_between(HOME, (cfg["lat"], cfg["lon"]))) if cfg.get("deplasman_mi", True) else "—"

    img = night_background().convert("RGBA")
    d = ImageDraw.Draw(img)
    logo = Image.open(path("assets/mekan-sizin-plaka-logo.png")).convert("RGBA")
    lw = 380
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, 56))
    tracked(d, (W / 2, 142), cfg["ust_satir"], font("Montserrat_600SemiBold.ttf", 21), CREAM, 6, anchor_center=True)
    d.text((W / 2, 290), "AVRUPA GECESİ", font=font("Anton_400Regular.ttf", 150), fill=(250, 248, 244), anchor="mm")
    hw = handwriting(cfg["el_yazisi_baslik"], 58, RED, 4)
    img.alpha_composite(hw, (W - hw.width - 90, 350))

    page = passport(cfg, opp, km)
    pr = page.rotate(-2.2, resample=Image.BICUBIC, expand=True)
    px, py = (W - pr.width) // 2, 452
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = Image.new("RGBA", pr.size, (0, 0, 0, 0))
    s.putalpha(pr.getchannel("A").point(lambda v: int(v * 0.8)))
    sh.paste(s, (px + 10, py + 20))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(18)))
    img.alpha_composite(pr, (px, py))

    st = stamp("CANLI YAYIN", "MEKAN SİZİN'DE", seed=13).rotate(-8, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(st, (W - st.width - 30, 930))

    d = ImageDraw.Draw(img)
    d.text((70, 1084), cfg["alt_baslik"], font=font("Anton_400Regular.ttf", 56), fill=(250, 248, 244))
    d.text((72, 1158), cfg["alt_metin"], font=font("Montserrat_500Medium.ttf", 24), fill=(205, 208, 214))
    d.line((70, 1216, W - 70, 1216), fill=(255, 255, 255, 70), width=1)
    pin_x, pin_y = 72, 1240
    d.ellipse((pin_x, pin_y, pin_x + 20, pin_y + 20), fill=RED)
    d.polygon([(pin_x + 2, pin_y + 13), (pin_x + 18, pin_y + 13), (pin_x + 10, pin_y + 30)], fill=RED)
    d.ellipse((pin_x + 6, pin_y + 6, pin_x + 14, pin_y + 14), fill=(20, 20, 20))
    d.text((pin_x + 34, pin_y + 2), cfg["adres"], font=font("Montserrat_500Medium.ttf", 21), fill=(222, 224, 228))
    hw2 = handwriting(cfg["el_yazisi_alt"], 50, CREAM, 3)
    img.alpha_composite(hw2, (W - hw2.width - 70, 1270))

    out = grain(img.convert("RGB"))
    out.save(path(cfg["cikti"]))
    print("kaydedildi:", path(cfg["cikti"]), "| mesafe:", km)


if __name__ == "__main__":
    main()
