"""Mekan Sizin - profil ızgarası önizlemesi (Instagram 3:4 kırpmasıyla).

Kullanım:  python3 izgara.py cikti.jpg en_yeni.png ... en_eski.png
Dosyaları profilde göründüğü sırayla verin: en son paylaşılan önce (sol üst).
"""
import sys

from PIL import Image

TW, TH, GAP = 360, 480, 4


def main():
    out, files = sys.argv[1], sys.argv[2:]
    rows = (len(files) + 2) // 3
    grid = Image.new("RGB", (TW * 3 + GAP * 2, TH * rows + GAP * (rows - 1)), (255, 255, 255))
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        cw = round(im.height * 3 / 4)
        x0 = (im.width - cw) // 2
        im = im.crop((x0, 0, x0 + cw, im.height)).resize((TW, TH), Image.LANCZOS)
        grid.paste(im, ((i % 3) * (TW + GAP), (i // 3) * (TH + GAP)))
    grid.save(out, quality=90)
    print("kaydedildi:", out)


if __name__ == "__main__":
    main()
