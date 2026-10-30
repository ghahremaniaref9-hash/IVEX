"""IVEX & CO - tek sayfalık hizmet / paket teklifi (1920x1080 PNG + PDF).

Kullanım:  python3 teklif.py ../ayarlar/teklif-mercyla.json
Tasarım, IVEX & CO "GROW Paket" sunumunu izler: lime zemin, sol üstte IVEX & CO logosu (şablon görselinden
kesilir), turuncudan turkuaza geçişli çizgi ve rakamlar, Montserrat başlık ve maddeler, Arial ölçülerinde
(Liberation Sans) bölüm başlıkları, sağ altta siyah toplam kutusu. Bölüm sayısı 2 ya da 3 olabilir.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from marka import LIME, font, repo, tracked

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1920, 1080
X0, X1 = 108, 1812
BLACK = (0, 0, 0)
NOTE = (24, 84, 76)
# the template's gradient: orange -> brown -> teal
STOPS = [(0.0, (228, 128, 5)), (0.5, (138, 51, 0)), (1.0, (20, 204, 151))]


def sans(size, italic=False):
    return ImageFont.truetype(os.path.join(HERE, "fonts", f"LiberationSans-{'Italic' if italic else 'Bold'}.ttf"),
                              size)


def gradient(w, h):
    x = np.linspace(0, 1, max(w, 2))
    rgb = np.zeros((len(x), 3))
    for (p0, c0), (p1, c1) in zip(STOPS, STOPS[1:]):
        m = (x >= p0) & (x <= p1)
        u = ((x[m] - p0) / (p1 - p0))[:, None]
        rgb[m] = np.array(c0) * (1 - u) + np.array(c1) * u
    return Image.fromarray(np.repeat(rgb[None].astype(np.uint8), h, 0), "RGB")


def gradient_text(im, xy, text, fnt):
    d = ImageDraw.Draw(im)
    l, t, r, b = (round(v) for v in d.textbbox(xy, text, font=fnt))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=fnt, fill=255)
    im.paste(gradient(r - l, b - t), (l, t), mask.crop((l, t, r, b)))


def logo_from_template(path):
    """The IVEX & CO wordmark cut from the template, black ink turned into alpha so it sits on any lime."""
    src = Image.open(repo(path)).convert("RGB").crop((104, 68, 502, 136))
    a = np.asarray(src).astype(np.float32)
    ink = np.clip((np.array(LIME, np.float32) - a).mean(axis=2) / 150, 0, 1)
    out = np.zeros(a.shape[:2] + (4,), np.uint8)
    out[..., 3] = (ink * 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def wrap(d, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if d.textlength(trial, font=fnt) > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    im = Image.new("RGB", (W, H), LIME)
    d = ImageDraw.Draw(im)
    if cfg.get("logo", True):
        mark = logo_from_template(cfg["sablon"])
        im.paste(mark, (104, 68), mark)
        tracked(d, (X1, 90), cfg["ust_not"], font("Bold", 22), BLACK, 4, anchor="r")
    else:  # no wordmark: the note takes its place on the left, the client's web address goes right
        tracked(d, (X0, 90), cfg["ust_not"], font("Bold", 22), BLACK, 4)
        if cfg.get("site"):
            tracked(d, (X1, 90), cfg["site"], font("Bold", 22), BLACK, 4, anchor="r")
    im.paste(gradient(X1 - X0, 3), (X0, 155))
    d.text((X0 - 4, 188), cfg["baslik"], font=font("Bold", 84), fill=BLACK)

    parts = cfg["bolumler"]
    gap = 60
    col_w = (X1 - X0 - gap * (len(parts) - 1)) / len(parts)
    body = font("Medium", 25)
    lowest = 0  # bottom of the columns the total box sits under
    for i, part in enumerate(parts):
        x = round(X0 + i * (col_w + gap))
        d.text((x, 318), part["baslik"], font=sans(32), fill=BLACK)
        gradient_text(im, (x - 4, 360), f"{i + 1:02d}", sans(84))
        y = 472
        for item in part["maddeler"]:
            lines = wrap(d, item, body, col_w - 56)
            d.ellipse((x + 26, y + 13, x + 36, y + 23), fill=BLACK)
            for line in lines:
                d.text((x + 54, y), line, font=body, fill=BLACK)
                y += 32
            y += 13
        if x + col_w > 1000:
            lowest = max(lowest, y)
    if cfg.get("vurgu"):
        d.rectangle((X0, 868, X0 + 6, 908), fill=BLACK)
        d.text((X0 + 24, 872), cfg["vurgu"], font=font("Bold", 28), fill=BLACK)

    total = cfg["toplam"]
    top = max(lowest + 12, 808)
    box = (1000, top, X1, top + 150)
    d.rounded_rectangle(box, radius=34, fill=BLACK)
    cx = (box[0] + box[2]) / 2
    lab = sans(32)
    d.text((cx - d.textlength(total["etiket"], font=lab) / 2, box[1] + 20), total["etiket"], font=lab, fill=LIME)
    price, per = sans(84), font("Medium", 32)
    pw, qw = d.textlength(total["fiyat"], font=price), d.textlength(total["donem"], font=per)
    px = cx - (pw + 18 + qw) / 2
    d.text((px, box[1] + 58), total["fiyat"], font=price, fill=LIME)
    d.text((px + pw + 18, box[1] + 96), total["donem"], font=per, fill=LIME)

    d.text((X0, max(box[3] + 16, 1000)), cfg["dipnot"], font=sans(24, italic=True), fill=NOTE)
    if max(box[3] + 16, 1000) + 30 > H:
        print("UYARI: içerik sayfaya sığmıyor; madde sayısını azaltın.")
    out = repo(cfg["cikti"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out)
    im.save(repo(cfg["pdf"]), "PDF", resolution=144.0)
    print("kaydedildi:", out, "ve", repo(cfg["pdf"]))


if __name__ == "__main__":
    main()
