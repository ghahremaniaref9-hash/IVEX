"""Mekan Sizin - "Meze Kadrosu" serisi: her meze bir oyuncu gibi tanıtılır (1080x1350).

Kullanım:  python3 meze_kadrosu.py ayar.json
Gerçek fotoğraf + zarif serif ("Kartal'a Meze" konsepti) + oyuncu kartı satırı (Mevki / Forma).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from foto import crop_to, film_grain, grade
from mac_bileti import font, path
from zarif import draw_text, italic, serif, with_shadow

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350


def corner_shade(img, strength=0.6, radius=900):
    """Darken the top-left corner softly so the type block reads on any background."""
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.clip(1 - np.hypot(xx / 1.15, yy) / radius, 0, 1)
    alpha = strength * r * r * (3 - 2 * r)
    a = np.asarray(img).astype(np.float32)
    a = a * (1 - alpha[..., None]) + 8 * alpha[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def scarf_stripes(w=64, h=14, n=6):
    """Tiny black-and-white striped tab, like a Beşiktaş scarf."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    step = w / n
    for i in range(n):
        d.rectangle((round(i * step), 0, round((i + 1) * step) - 1, h - 1), fill=(255, 255, 255) if i % 2 else (16, 16, 16))
    d.rectangle((0, 0, w - 1, h - 1), outline=(255, 255, 255), width=1)
    return im


def main():
    cfg_path = sys.argv[1]
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    src = Image.open(path(cfg["foto"]["kaynak"])).convert("RGB")
    img = crop_to(src, (W, H), tuple(cfg["foto"].get("merkez", (0.5, 0.5))), cfg["foto"].get("yakinlik", 1.0))
    img = grade(img, sat=cfg["foto"].get("doygunluk", 0.9), warmth=0.4, fade=5, vignette=0.28, exposure=1.0)
    img = corner_shade(img, cfg.get("karartma", 0.6)).convert("RGBA")

    x = 76
    img.alpha_composite(scarf_stripes(), (x, 100))
    d = ImageDraw.Draw(img)
    draw_text(d, x + 84, 96, cfg["ust_satir"], font("Montserrat_700Bold.ttf", 20), (240, 234, 224), 6)

    size = cfg.get("baslik_boyut", 176)
    head_f = serif(size)
    sub = cfg.get("alt_boyut", 46)
    sub_lh = round(sub * 1.13)

    def headline(dr, col):
        draw_text(dr, x - 6, 138, cfg["baslik"], head_f, col or (255, 255, 255, 255), -0.025 * size, stroke=1)
        for i, line in enumerate(cfg["alt_satirlar"]):
            draw_text(dr, x, 138 + round(size * 1.12) + i * sub_lh, line, italic(sub), col or (246, 240, 230, 255), 0)

    img = with_shadow(img, headline, blur=14, opacity=150)

    # Player-card row: label above, value below, thin divider between fields
    d = ImageDraw.Draw(img)
    fy = 138 + round(size * 1.12) + len(cfg["alt_satirlar"]) * sub_lh + 46
    fx = x
    lab_f, val_f = font("Montserrat_700Bold.ttf", 15), serif(40)
    for i, (label, value) in enumerate(cfg["kart"]):
        if i:
            d.line((fx - 28, fy + 4, fx - 28, fy + 76), fill=(255, 255, 255, 110), width=1)
        draw_text(d, fx, fy, label, lab_f, (232, 224, 212, 230), 4)
        w = draw_text(d, fx, fy + 26, value, val_f, (255, 255, 255, 255), -0.5)
        fx += max(w, d.textlength(label, font=lab_f) + 4 * len(label)) + 56

    logo = Image.open(path("assets/mekan-sizin-plaka-logo.png")).convert("RGBA")
    lw = cfg.get("logo_genislik", 300)
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    lx, ly = cfg.get("logo_konum", (x, H - 76 - logo.height))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    s.putalpha(logo.getchannel("A").point(lambda v: int(v * 0.55)))
    sh.paste(s, (lx + 4, ly + 8))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(8)))
    img.alpha_composite(logo, (lx, ly))

    out = film_grain(img.convert("RGB"), cfg.get("gren", 5.0), seed=61)
    out.save(path(cfg["cikti"]))
    print("kaydedildi:", path(cfg["cikti"]))


if __name__ == "__main__":
    main()
