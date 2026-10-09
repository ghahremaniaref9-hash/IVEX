"""Mekan Sizin - maç günü story'si (1080x1920). Üç şablonun kartını dikey formata taşır.

Kullanım:  python3 story.py story.json
"tur":  "bilet"    -> lig iç saha (Maç Bileti, mac-bileti.json alanları)
        "kart"     -> lig deplasman (Biniş Kartı, deplasman.json alanları + sehirler.json)
        "pasaport" -> Avrupa (Kartal Pasaportu, avrupa.json alanları)
Instagram'ın üst (profil) ve alt (yanıt) şeritleri için ~220 px'lik boşluklar bırakılır.
Ortadaki "çıkartma alanı"na uygulamadan anket / geri sayım çıkartması konur.
"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

from avrupa import passport
from deplasman import HOME, boarding_pass, km_between, km_label
from foto import film_grain, process
from mac_bileti import CREAM, RED, fit_font, font, handwriting, path, stamp, ticket, tracked

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920


def darken(img, top=0.55, mid=0.42, bottom=0.75):
    """Darken the photo so the card and type read clearly (stronger at top and bottom)."""
    w, h = img.size
    grad = Image.new("L", (1, h))
    for y in range(h):
        t = y / (h - 1)
        if t < 0.5:
            v = top + (mid - top) * (t / 0.5)
        else:
            v = mid + (bottom - mid) * ((t - 0.5) / 0.5)
        grad.putpixel((0, y), round(v * 255))
    black = Image.new("RGB", (w, h), (8, 8, 9))
    return Image.composite(black, img, grad.resize((w, h)))


def hand_arrow(size, color, seed=4):
    """Hand-drawn curved arrow pointing down-right."""
    w, h = size
    im = Image.new("RGBA", size, color + (0,))
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    pts = []
    for i in range(41):
        t = i / 40
        x = 12 + (w - 40) * t
        y = 14 + (h - 44) * (t ** 1.8) + math.sin(t * math.pi) * -18
        pts.append((x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.8, 0.8)))
    d.line(pts, fill=color + (235,), width=6, joint="curve")
    ex, ey = pts[-1]
    px, py = pts[-4]
    ang = math.atan2(ey - py, ex - px)
    for da in (2.55, -2.55):
        d.line((ex, ey, ex + 34 * math.cos(ang + da), ey + 34 * math.sin(ang + da)), fill=color + (235,), width=6)
    return im


def card_for(cfg):
    tur = cfg["tur"]
    if tur == "bilet":
        return ticket(cfg)
    if tur == "kart":
        with open(os.path.join(HERE, "sehirler.json"), encoding="utf-8") as fh:
            opp = dict(json.load(fh)[cfg["rakip"]])
        opp.update(cfg.get("rakip_ozel", {}))
        cfg.setdefault("mesafe", km_label(km_between(HOME, (opp["lat"], opp["lon"]))))
        cfg.setdefault("mac", f"{opp['kisaltma']} – BJK")
        return boarding_pass(cfg, opp, Image.open(path("assets/bjk.png")).convert("RGBA"))
    if tur == "pasaport":
        km = km_label(km_between(HOME, (cfg["lat"], cfg["lon"]))) if cfg.get("deplasman_mi", True) else "—"
        return passport(cfg, cfg["rakip"], km)
    raise ValueError(f"bilinmeyen tur: {tur}")


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "story.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)

    foto = dict(cfg["foto"], boyut=[W, H], gren=0)
    img = darken(process(foto, (W, H)), *cfg.get("karartma", (0.55, 0.42, 0.75))).convert("RGBA")
    d = ImageDraw.Draw(img)

    logo = Image.open(path(cfg.get("logo", "assets/mekan-sizin-plaka-logo.png"))).convert("RGBA")
    lw = 440
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, 236))
    tracked(d, (W / 2, 338), cfg["ust_satir"], font("Montserrat_600SemiBold.ttf", 24), CREAM, 7, anchor_center=True)
    baslik = cfg["baslik"]
    bf = fit_font("Anton_400Regular.ttf", 236, baslik, 960)
    d.text((W / 2, 392), baslik, font=bf, fill=(250, 248, 244), anchor="ma")
    head_bottom = d.textbbox((W / 2, 392), baslik, font=bf, anchor="ma")[3]
    hw = handwriting(cfg["el_yazisi_baslik"], 64, RED, 4)
    img.alpha_composite(hw, (W - hw.width - 70, head_bottom - 6))

    card = card_for(cfg)
    scale = min(980 / card.width, 520 / card.height)
    card = card.resize((round(card.width * scale), round(card.height * scale)), Image.LANCZOS)
    cr = card.rotate(cfg.get("aci", -2.4), resample=Image.BICUBIC, expand=True)
    cx, cy = (W - cr.width) // 2, head_bottom + 124
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = Image.new("RGBA", cr.size, (0, 0, 0, 0))
    s.putalpha(cr.getchannel("A").point(lambda v: int(v * 0.8)))
    sh.paste(s, (cx + 10, cy + 20))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(18)))
    img.alpha_composite(cr, (cx, cy))
    card_bottom = cy + cr.height

    st = stamp("CANLI YAYIN", "MEKAN SİZİN'DE", seed=cfg.get("damga_seed", 17)).rotate(-8, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(st, (W - st.width - 40, card_bottom - 96))

    # Sticker zone: handwritten prompt + arrow pointing at the empty space
    note = handwriting(cfg["cikartma_notu"], 62, CREAM, 3)
    ny = card_bottom + 40
    img.alpha_composite(note, (86, ny))
    arrow = hand_arrow((210, 120), CREAM)
    img.alpha_composite(arrow, (96 + note.width - 60, ny + note.height // 2))

    d = ImageDraw.Draw(img)
    by = 1540
    d.text((W / 2, by), cfg["alt_baslik"], font=fit_font("Anton_400Regular.ttf", 74, cfg["alt_baslik"], 940), fill=(250, 248, 244), anchor="mt")
    adres = cfg["adres"]
    af = font("Montserrat_500Medium.ttf", 23)
    aw = d.textlength(adres, font=af)
    pin_x, pin_y = round(W / 2 - (aw + 34) / 2), by + 104
    d.ellipse((pin_x, pin_y, pin_x + 20, pin_y + 20), fill=RED)
    d.polygon([(pin_x + 2, pin_y + 13), (pin_x + 18, pin_y + 13), (pin_x + 10, pin_y + 30)], fill=RED)
    d.ellipse((pin_x + 6, pin_y + 6, pin_x + 14, pin_y + 14), fill=(20, 20, 20))
    d.text((pin_x + 34, pin_y + 1), adres, font=af, fill=(225, 222, 214))

    out = film_grain(img.convert("RGB"), 7.5, seed=5)
    out.save(path(cfg["cikti"]))
    print("kaydedildi:", path(cfg["cikti"]))


if __name__ == "__main__":
    main()
