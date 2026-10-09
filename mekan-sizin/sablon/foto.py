"""Mekan Sizin - metinsiz feed fotoğrafları için ortak renk ayarı (film görünümü).

Kullanım:  python3 foto.py foto.json
Her fotoğraf aynı ayarla işlenir: hafif soluk renkler (kırmızılar korunur), sıcak ışıklar,
yumuşak siyahlar, kenar kararması ve film greni. Böylece profil ızgarası tek elden çıkmış gibi durur.
Gerçek mekân fotoğrafları geldiğinde aynı dosyaya eklemek yeterli.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

from mac_bileti import path

HERE = os.path.dirname(os.path.abspath(__file__))


def crop_to(img, size, center=(0.5, 0.5), zoom=1.0):
    """Crop the largest window with the target aspect ratio (divided by `zoom`) around `center`."""
    tw, th = size
    sw, sh = img.size
    ratio = tw / th
    cw, ch = (sw, sw / ratio) if sw / sh < ratio else (sh * ratio, sh)
    cw, ch = cw / zoom, ch / zoom
    cx = min(max(center[0] * sw, cw / 2), sw - cw / 2)
    cy = min(max(center[1] * sh, ch / 2), sh - ch / 2)
    box = (round(cx - cw / 2), round(cy - ch / 2), round(cx + cw / 2), round(cy + ch / 2))
    return img.crop(box).resize(size, Image.LANCZOS)


def film_grain(img, amount=7.0, seed=11):
    """Soft, luminance-dependent grain (stronger in mid-tones, like negative film)."""
    rng = np.random.default_rng(seed)
    arr = np.asarray(img).astype(np.float32)
    h, w = arr.shape[:2]
    n = rng.normal(0, 1, (h, w)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32)
    n = (n - 128) / 40 * 1.6
    lum = arr.mean(axis=2) / 255
    weight = 0.45 + 0.9 * lum * (1 - lum) * 4 / 2
    arr += (n * amount * weight)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def grade(img, sat=0.70, warmth=1.0, fade=12, vignette=0.38, exposure=1.0, cool=0.0):
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255
    a = np.clip(a * exposure, 0, 1)
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    # Mute colours but keep reds (team/brand accent) more saturated
    redness = np.clip((a[..., 0] - np.maximum(a[..., 1], a[..., 2])) * 3.0, 0, 1)
    s = sat + (1 - sat) * redness * 0.85
    a = lum[..., None] + (a - lum[..., None]) * s[..., None]
    # Gentle S-curve
    a = np.clip(a, 0, 1)
    a = a + 0.12 * (a - 0.5) * (1 - np.abs(2 * a - 1))
    # Split tone: warm highlights, neutral/cool shadows
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    a[..., 0] += 0.030 * lum * warmth
    a[..., 1] += 0.008 * lum * warmth
    a[..., 2] -= 0.028 * lum * warmth
    a[..., 2] += (0.022 + cool) * (1 - lum) * (1 - lum)
    a[..., 0] -= cool * 0.5 * (1 - lum)
    # Lifted, matte blacks
    a = fade / 255 + a * (1 - fade / 255)
    # Vignette
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) / np.sqrt(2)
    a *= (1 - vignette * np.clip(r - 0.25, 0, 1) ** 1.6 / 0.75 ** 1.6)[..., None]
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))


def process(item, default_size=(1080, 1350)):
    img = Image.open(path(item["kaynak"])).convert("RGB")
    size = tuple(item.get("boyut", default_size))
    img = crop_to(img, size, tuple(item.get("merkez", (0.5, 0.5))), item.get("yakinlik", 1.0))
    img = grade(img, sat=item.get("doygunluk", 0.70), warmth=item.get("sicaklik", 1.0), fade=item.get("soluk", 12),
                vignette=item.get("vinyet", 0.38), exposure=item.get("pozlama", 1.0), cool=item.get("soguk", 0.0))
    return film_grain(img, item.get("gren", 7.0), seed=item.get("seed", 11))


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "foto.json")
    with open(cfg_path, encoding="utf-8") as fh:
        items = json.load(fh)
    for item in items:
        out = process(item)
        out.save(path(item["cikti"]), quality=93, subsampling=0)
        print("kaydedildi:", path(item["cikti"]))


if __name__ == "__main__":
    main()
