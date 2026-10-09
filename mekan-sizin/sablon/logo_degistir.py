"""Şablon 1 - ChatGPT'nin 'Maç Günü Beşiktaş'ta' afişinde alttaki yazıyı Mekan Sizin plaka logosuyla değiştirir.

Kullanım:  python3 logo_degistir.py sablon1.json
'mod': "birebir" -> sadece logo değişir;  "ekli" -> tarih/saat etiketi ve adres de eklenir.
Not: Taban görseldeki takım adları ve armalar sabittir (Beşiktaş JK - Kocaelispor).
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REGION = (380, 1195, 742, 1365)  # eski 'MEKAN SİZİN' yazısının bölgesi
RED = (200, 16, 46)


def path(p):
    return p if os.path.isabs(p) else os.path.join(HERE, p)


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "sablon1.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    poster = Image.open(path(cfg["taban"])).convert("RGB")
    P = np.asarray(poster)
    W, H = poster.size

    x0, y0, x1, y1 = REGION
    bright = np.zeros((H, W), bool)
    bright[y0:y1, x0:x1] = P[y0:y1, x0:x1].min(axis=2) > 110
    ys, xs = np.where(bright)
    old = (xs.min(), ys.min(), xs.max(), ys.max())
    hole = Image.fromarray(bright.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(7))
    clean = Image.fromarray(cv2.inpaint(P[..., ::-1].copy(), np.asarray(hole), 7, cv2.INPAINT_TELEA)[..., ::-1]).convert("RGBA")

    logo = Image.open(path(cfg["logo"])).convert("RGBA")
    lw = 440
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    cx, cy = W / 2, (old[1] + old[3]) / 2 + 4
    lx, ly = round(cx - logo.width / 2), round(cy - logo.height / 2)
    extra = cfg.get("mod") == "ekli"
    if extra:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s = Image.new("RGBA", logo.size, (0, 0, 0, 0))
        s.putalpha(logo.getchannel("A").point(lambda v: int(v * 0.8)))
        sh.paste(s, (lx, ly + 6))
        clean = Image.alpha_composite(clean, sh.filter(ImageFilter.GaussianBlur(10)))
    clean.alpha_composite(logo, (lx, ly))

    m = 30
    box = (min(lx, old[0]) - m, min(ly, old[1]) - m, max(lx + logo.width, old[2]) + m, max(ly + logo.height, old[3]) + m)
    final = poster.copy()
    final.paste(clean.convert("RGB").crop(box), box[:2])

    if extra:
        d = ImageDraw.Draw(final)
        f = font("Oswald_700Bold.ttf", 26)
        left, right, gap = cfg["tarih"], cfg["saat"], 24
        tw = d.textlength(left, font=f) + gap + d.textlength(right, font=f)
        ph, padx = 38, 20
        top = ly - ph - 14
        d.rounded_rectangle((cx - tw / 2 - padx, top, cx + tw / 2 + padx, top + ph), radius=ph // 2, fill=(255, 255, 255))
        ty = top + (ph - f.getmetrics()[0]) / 2 - 3
        x = cx - tw / 2
        d.text((x, ty), left, font=f, fill=(15, 15, 15))
        x += d.textlength(left, font=f)
        d.ellipse((x + gap / 2 - 4, top + ph / 2 - 4, x + gap / 2 + 4, top + ph / 2 + 4), fill=RED)
        d.text((x + gap, ty), right, font=f, fill=(15, 15, 15))
        af = font("Montserrat_500Medium.ttf", 16)
        for i, line in enumerate(cfg["adres_satirlari"]):
            d.text((121, 1338 + 21 * i), line, font=af, fill=(205, 205, 205))

    out = path(cfg["cikti"])
    final.save(out)
    print("kaydedildi:", out)


if __name__ == "__main__":
    main()
