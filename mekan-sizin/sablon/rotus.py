"""Mekan Sizin - ham fotoğraflarda küçük leke temizliği (yağ damlası, kırıntı), doğallığı bozmadan.

Kullanım:  python3 rotus.py rotus.json
Her kayıt: {"kaynak": ham foto, "cikti": temiz foto, "lekeler": [[x, y, yarıçap], ...], "dondur": 90}
"lekeler" piksel cinsinden ve döndürülmüş fotoğraf üzerindedir; "dondur" yan çekilmiş kareyi saat yönünde
90/180/270 derece çevirir.
Her leke için yakındaki en uygun temiz doku aranır (çevre halkası en çok benzeyen yer) ve yumuşak kenarla
üstüne kopyalanır; tabak sırrının benekli dokusu korunur, geri kalan her piksel aynen kalır.
"""
import json
import sys

import numpy as np
from PIL import Image

from mac_bileti import path


def best_source(arr, x, y, r):
    """Offset of the nearby patch whose surrounding ring looks most like the ring around the spot."""
    h, w = arr.shape[:2]
    R = round(r * 1.6)
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
    dist = np.hypot(xx, yy)
    ring = (dist > r * 1.15) & (dist <= R)
    tgt = arr[y - R:y + R + 1, x - R:x + R + 1].astype(np.float32)
    best, best_d = None, None
    step = max(2, round(r / 3))
    for dy in range(-4 * R, 4 * R + 1, step):
        for dx in range(-4 * R, 4 * R + 1, step):
            if np.hypot(dx, dy) < 2.2 * R:
                continue
            sx, sy = x + dx, y + dy
            if sx - R < 0 or sy - R < 0 or sx + R >= w or sy + R >= h:
                continue
            src = arr[sy - R:sy + R + 1, sx - R:sx + R + 1].astype(np.float32)
            d = float(((src - tgt)[ring] ** 2).mean())
            if best_d is None or d < best_d:
                best, best_d = (dx, dy), d
    return best


def clean(img, spots):
    arr = np.asarray(img.convert("RGB")).copy()
    out = arr.astype(np.float32)
    for x, y, r in spots:
        x, y, r = round(x), round(y), float(r)
        dx, dy = best_source(arr, x, y, r)
        R = round(r * 1.6)
        yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
        m = np.clip((r * 1.35 - np.hypot(xx, yy)) / (r * 0.35), 0, 1)[..., None]  # soft-edged disc
        src = arr[y + dy - R:y + dy + R + 1, x + dx - R:x + dx + R + 1].astype(np.float32)
        tgt = out[y - R:y + R + 1, x - R:x + R + 1]
        out[y - R:y + R + 1, x - R:x + R + 1] = tgt * (1 - m) + src * m
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        items = json.load(fh)
    for item in items:
        img = Image.open(path(item["kaynak"]))
        turn = {90: Image.ROTATE_270, 180: Image.ROTATE_180, 270: Image.ROTATE_90}.get(item.get("dondur", 0))
        if turn is not None:
            img = img.transpose(turn)
        out = clean(img, item.get("lekeler", [])) if item.get("lekeler") else img.convert("RGB")
        out.save(path(item["cikti"]), quality=95, subsampling=0)
        print("kaydedildi:", path(item["cikti"]), f"({len(item.get('lekeler', []))} leke)")


if __name__ == "__main__":
    main()
