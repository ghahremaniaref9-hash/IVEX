"""Mekan Sizin - meze fotoğraflarını afişlerle aynı dile sokan çerçeve (1080x1350).

Kullanım:  python3 cerceve.py cerceve.json
Fotoğraf, afişlerdeki koyu beton duvar zeminine kenarlardan yumuşakça solarak oturur; dışında ince krem
bir çerçeve çizgisi, alt ortasında çizgiyi kesen küçük plaka logo vardır. Çerçeve, profil ızgarasının 3:4
kırpmasında da (yanlardan 34 px) görünecek kadar içeridedir.
Her kayıt: {"kaynak": renk ayarı yapılmış foto, "cikti": ..., "merkez": [x, y], "yakinlik": 1.0}
"""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw

from foto import crop_to, film_grain
from mac_bileti import CREAM, noise, path

W, H = 1080, 1350
LINE = 48      # frame line inset from the canvas edge
INSET = 70     # photo area inset
FADE = 120     # width of the edge fade inside the photo area


def wall():
    """Same charcoal concrete texture as the match posters."""
    tex = 0.5 * noise((W, H), 3, 1) + 0.3 * noise((W, H), 14, 2) + 0.2 * noise((W, H), 60, 3)
    base = 16 + (tex - 0.5) * 22
    return np.dstack([base, base, base * 0.97])


def fade_mask(w, h):
    """1 in the middle, easing to 0 at every edge; corners fade softly (product of both axes)."""
    def ramp(n):
        t = np.clip(np.minimum(np.arange(n), np.arange(n)[::-1]) / FADE, 0, 1)
        return t * t * (3 - 2 * t)
    return np.outer(ramp(h), ramp(w)).astype(np.float32)


def frame(item):
    photo = Image.open(path(item["kaynak"])).convert("RGB")
    pw, ph = W - 2 * INSET, H - 2 * INSET
    photo = crop_to(photo, (pw, ph), tuple(item.get("merkez", (0.5, 0.5))), item.get("yakinlik", 1.0))
    base = wall()
    canvas = base.copy()
    m = fade_mask(pw, ph)[..., None]
    region = canvas[INSET:INSET + ph, INSET:INSET + pw]
    canvas[INSET:INSET + ph, INSET:INSET + pw] = region * (1 - m) + np.asarray(photo, np.float32) * m
    img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).convert("RGBA")

    logo = Image.open(path("assets/mekan-sizin-plaka-logo.png")).convert("RGBA")
    lw = item.get("logo_genislik", 200)
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    lx, ly = (W - lw) // 2, H - LINE - logo.height // 2

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle((LINE, LINE, W - 1 - LINE, H - 1 - LINE), outline=CREAM + (150,), width=2)
    img.alpha_composite(layer)
    # the line stops a little before the logo on both sides
    gap = (lx - 18, H - LINE - 4, lx + lw + 18, H - LINE + 4)
    wall_img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    img.paste(wall_img.crop(gap), gap[:2])
    img.alpha_composite(logo, (lx, ly))
    return film_grain(img.convert("RGB"), item.get("gren", 4.5), seed=item.get("seed", 51))


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        items = json.load(fh)
    for item in items:
        frame(item).save(path(item["cikti"]), quality=93, subsampling=0)
        print("kaydedildi:", path(item["cikti"]))


if __name__ == "__main__":
    main()
