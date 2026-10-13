"""Mekan Sizin - "Kartal'a Meze" konsepti: gerçek fotoğraf + zarif serif başlık (1080x1350 karusel).

Kullanım:  python3 zarif.py zarif.json
1. kare: tam sayfa fotoğraf, iki satırlık serif başlık (sol / sağ), altta küçük bilgi satırı.
Sonraki kareler: üstte fotoğraf bandı, altta krem zemin üzerinde serif menü.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from foto import crop_to, film_grain, grade
from mac_bileti import RED, path

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350
CREAM = (245, 240, 232)
CHARCOAL = (32, 29, 27)
MUTED = (128, 112, 98)


def serif(size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", "GildaDisplay_400Regular.ttf"), size)


def italic(size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", "CormorantGaramond_500Medium_Italic.ttf"), size)


def advance(c, fnt, tracking):
    # Gilda's "%" carries a wide right side bearing; pull the figures that follow it closer
    return fnt.getlength(c) + tracking - (0.09 * fnt.size if c == "%" else 0)


def text_width(text, fnt, tracking):
    return sum(advance(c, fnt, tracking) for c in text) - tracking


def draw_text(d, x, y, text, fnt, fill, tracking=0.0, align="left", stroke=0):
    """Letter-spaced text; `x` is the left edge, right edge or centre depending on `align`."""
    w = text_width(text, fnt, tracking)
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=fill)
        x += advance(c, fnt, tracking)
    return w


def photo(spec, size):
    img = Image.open(path(spec["kaynak"])).convert("RGB")
    img = crop_to(img, size, tuple(spec.get("merkez", (0.5, 0.5))), spec.get("yakinlik", 1.0))
    # Light, natural grade: the concept is bright and airy, unlike the dark match posts
    return grade(img, sat=spec.get("doygunluk", 0.95), warmth=spec.get("sicaklik", 0.5), fade=4,
                 vignette=spec.get("vinyet", 0.18), exposure=spec.get("pozlama", 1.03))


def shade(img, top, bottom, top_h=560, bottom_h=380):
    """Soft dark gradients at the top and bottom so white type reads on bright plates."""
    w, h = img.size
    yy = np.arange(h, dtype=np.float32)[:, None]
    t = np.clip(1 - yy / top_h, 0, 1)
    b = np.clip((yy - (h - bottom_h)) / bottom_h, 0, 1)
    alpha = np.maximum(top * t * t * (3 - 2 * t), bottom * b * b * (3 - 2 * b))
    a = np.asarray(img).astype(np.float32)
    a = a * (1 - alpha[..., None]) + 12 * alpha[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def with_shadow(img, draw_fn, blur=10, opacity=150):
    """Run `draw_fn(draw, colour)` twice: once blurred and dark as a shadow, once on top."""
    img = img.convert("RGBA")
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(sh), (0, 0, 0, opacity))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(blur)))
    draw_fn(ImageDraw.Draw(img), None)
    return img


def cover(cfg):
    k = cfg["kapak"]
    img = shade(photo(k["foto"], (W, H)), k.get("ust_karartma", 0.5), k.get("alt_karartma", 0.62), top_h=640)
    size = k.get("baslik_boyut", 112)
    f = serif(size)
    tr = -0.03 * size
    line1, line2 = k["baslik"]

    def title(d, col):
        c1 = col or (255, 255, 255, 255)
        draw_text(d, 78, 118, line1, f, c1, tr, stroke=1)
        draw_text(d, W - 78, 118 + round(size * 1.12), line2, f, c1, tr, align="right", stroke=1)

    img = with_shadow(img, title, blur=14, opacity=120)

    def footer(d, col):
        draw_text(d, W / 2, H - 150, k["alt_satir"], italic(44), col or (250, 246, 240, 255), 0, align="center")
        draw_text(d, W / 2, H - 82, k["imza"], serif(22), col or (240, 234, 226, 230), 4.5, align="center")

    img = with_shadow(img, footer, blur=8, opacity=140)
    return film_grain(img.convert("RGB"), 3.5, seed=41)


def menu_page(cfg, page, number, total):
    img = Image.new("RGB", (W, H), CREAM)
    band_h = page.get("foto_yukseklik", 450)
    img.paste(photo(page["foto"], (W, band_h)), (0, 0))
    d = ImageDraw.Draw(img)
    y = band_h + 56
    for sec_name in page["bolumler"]:
        sec = cfg["bolumler"][sec_name]
        draw_text(d, W / 2, y, sec["baslik"], serif(78), CHARCOAL, -1.5, align="center")
        y += 96
        if sec.get("alt"):
            draw_text(d, W / 2, y, sec["alt"], italic(36), MUTED, 0, align="center")
            y += 52
        d.rectangle((W / 2 - 34, y + 6, W / 2 + 34, y + 8), fill=RED)
        y += 42
        items = sec["urunler"]
        name_f, price_f = serif(31), serif(28)
        row = sec.get("satir", 56)
        if sec.get("iki_sutun"):
            half = (len(items) + 1) // 2
            cols = [(90, 506, items[:half]), (574, 990, items[half:])]
            d.line((W / 2, y + 4, W / 2, y + row * half - 18), fill=(222, 213, 200), width=1)
            for x0, x1, col_items in cols:
                for i, (name, price) in enumerate(col_items):
                    draw_text(d, x0, y + i * row, name, name_f, CHARCOAL, -0.3)
                    draw_text(d, x1, y + i * row + 2, f"{price} TL", price_f, MUTED, 0, align="right")
            y += row * half
        else:
            x0, x1 = 210, 870
            for i, (name, price) in enumerate(items):
                draw_text(d, x0, y + i * row, name, name_f, CHARCOAL, -0.3)
                draw_text(d, x1, y + i * row + 2, f"{price} TL", price_f, MUTED, 0, align="right")
            y += row * len(items)
        y += page.get("bolum_arasi", 54)
    draw_text(d, 90, H - 74, cfg["kapak"]["imza"], serif(20), MUTED, 4)
    draw_text(d, 990, H - 76, f"{number} / {total}", serif(22), MUTED, 1, align="right")
    return film_grain(img, 2.5, seed=43 + number)


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "zarif.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    prefix = path(cfg["cikti_oneki"])
    total = len(cfg["sayfalar"]) + 1
    out = f"{prefix}-1-kapak.png"
    cover(cfg).save(out)
    print("kaydedildi:", out)
    for i, page in enumerate(cfg["sayfalar"], start=2):
        out = f"{prefix}-{i}-{page['dosya']}.png"
        menu_page(cfg, page, i, total).save(out)
        print("kaydedildi:", out)


if __name__ == "__main__":
    main()
