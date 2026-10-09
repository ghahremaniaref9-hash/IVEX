"""Mekan Sizin - maç günü 'Skor Tahmini' gönderisi (1080x1350). Lig ve Avrupa maçlarında kullanılır.

Kullanım:  python3 skor_tahmini.py skor-tahmini.json
Eski stat skorbordu: iki takım, boş "?" plakaları. Takipçi tahminini yorumlara yazar.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from deplasman import crest
from foto import film_grain, process
from mac_bileti import CREAM, RED, fit_font, font, handwriting, noise, path, stamp, tracked
from story import darken

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1350


def team_crest(team, size):
    if team.get("arma") and os.path.exists(path(team["arma"])):
        c = Image.open(path(team["arma"])).convert("RGBA")
        return c.resize((round(c.width * size / c.height), size), Image.LANCZOS)
    return crest(team, size)


def flip_card(w, h, text):
    """One flip-number plate with a split line, like an old stadium scoreboard."""
    ss = 2
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius=12 * ss, fill=(34, 35, 36))
    d.rounded_rectangle((0, 0, w * ss - 1, h * ss // 2), radius=12 * ss, fill=(44, 45, 46))
    d.rectangle((0, h * ss // 2 - 14 * ss, w * ss - 1, h * ss // 2), fill=(44, 45, 46))
    d.text((w * ss / 2, h * ss / 2 + 4 * ss), text, font=font("Anton_400Regular.ttf", round(h * 0.78) * ss), fill=CREAM, anchor="mm")
    d.rectangle((0, h * ss // 2 - 2 * ss, w * ss - 1, h * ss // 2 + 2 * ss), fill=(12, 12, 12))
    for x in (6 * ss, w * ss - 14 * ss):  # hinge pins
        d.rectangle((x, h * ss // 2 - 7 * ss, x + 8 * ss, h * ss // 2 + 7 * ss), fill=(90, 90, 88))
    return im.resize((w, h), Image.LANCZOS)


def scoreboard(cfg):
    bw, bh = 920, 480
    arr = np.dstack([np.full((bh, bw), c, np.float32) for c in (22, 27, 24)])
    arr += ((noise((bw, bh), 2, 81) - 0.5) * 9 + (noise((bw, bh), 30, 82) - 0.5) * 10)[..., None]
    board = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(board)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=18, outline=(70, 74, 70), width=4)
    d.rounded_rectangle((14, 14, bw - 15, bh - 15), radius=10, outline=(48, 52, 48), width=2)
    for (x, y) in ((30, 30), (bw - 30, 30), (30, bh - 30), (bw - 30, bh - 30)):
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(96, 98, 94))
        d.ellipse((x - 3, y - 4, x + 2, y + 1), fill=(150, 150, 146))

    # Header plate
    tracked(d, (bw / 2, 40), cfg["skorbord_baslik"], font("Montserrat_700Bold.ttf", 18), (200, 196, 186), 7, anchor_center=True)
    d.line((60, 76, bw - 60, 76), fill=(60, 64, 60), width=2)

    rows = [cfg["ev_sahibi"], cfg["deplasman"]]
    for i, team in enumerate(rows):
        y = 100 + i * 170
        c = team_crest(team, 116)
        board.alpha_composite(c, (64 + (116 - c.width) // 2, y + 16))
        d.text((214, y + 74), team["ad"], font=fit_font("Oswald_700Bold.ttf", 60, team["ad"], 440), fill=(240, 236, 226), anchor="lm")
        fc = flip_card(150, 150, "?")
        board.alpha_composite(fc, (bw - 64 - 150, y))
        if i == 0:
            d.line((64, y + 162, bw - 64, y + 162), fill=(50, 54, 50), width=2)

    # Footer: kick-off time with a 'live' lamp
    fy = bh - 62
    d.ellipse((64, fy, 84, fy + 20), fill=RED)
    d.ellipse((69, fy + 5, 75, fy + 11), fill=(255, 160, 170))
    tracked(d, (100, fy - 1), cfg["skorbord_alt"], font("Montserrat_700Bold.ttf", 18), (200, 196, 186), 5)
    return board


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "skor-tahmini.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)

    img = darken(process(dict(cfg["foto"], gren=0), (W, H)), *cfg.get("karartma", (0.45, 0.5, 0.8))).convert("RGBA")
    d = ImageDraw.Draw(img)

    logo = Image.open(path("assets/mekan-sizin-plaka-logo.png")).convert("RGBA")
    lw = 380
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, 56))
    tracked(d, (W / 2, 142), cfg["ust_satir"], font("Montserrat_600SemiBold.ttf", 21), CREAM, 6, anchor_center=True)
    baslik = cfg["baslik"]
    d.text((W / 2, 290), baslik, font=fit_font("Anton_400Regular.ttf", 170, baslik, 960), fill=(250, 248, 244), anchor="mm")
    hw = handwriting(cfg["el_yazisi_baslik"], 58, RED, 4)
    img.alpha_composite(hw, (W - hw.width - 90, 356))

    board = scoreboard(cfg)
    br = board.rotate(1.4, resample=Image.BICUBIC, expand=True)
    bx, by = (W - br.width) // 2, 470
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = Image.new("RGBA", br.size, (0, 0, 0, 0))
    s.putalpha(br.getchannel("A").point(lambda v: int(v * 0.85)))
    sh.paste(s, (bx + 10, by + 22))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(18)))
    img.alpha_composite(br, (bx, by))

    st = stamp("CANLI YAYIN", "MEKAN SİZİN'DE", seed=cfg.get("damga_seed", 29)).rotate(-8, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(st, (W - st.width - 34, 902))
    hw3 = handwriting(cfg["el_yazisi_orta"], 56, CREAM, 5)
    img.alpha_composite(hw3, (84, 968))

    d = ImageDraw.Draw(img)
    d.text((70, 1084), cfg["alt_baslik"], font=fit_font("Anton_400Regular.ttf", 56, cfg["alt_baslik"], 940), fill=(250, 248, 244))
    d.text((72, 1158), cfg["alt_metin"], font=font("Montserrat_500Medium.ttf", 24), fill=(205, 208, 214))
    d.line((70, 1216, W - 70, 1216), fill=(255, 255, 255, 70), width=1)
    pin_x, pin_y = 72, 1240
    d.ellipse((pin_x, pin_y, pin_x + 20, pin_y + 20), fill=RED)
    d.polygon([(pin_x + 2, pin_y + 13), (pin_x + 18, pin_y + 13), (pin_x + 10, pin_y + 30)], fill=RED)
    d.ellipse((pin_x + 6, pin_y + 6, pin_x + 14, pin_y + 14), fill=(20, 20, 20))
    d.text((pin_x + 34, pin_y + 2), cfg["adres"], font=font("Montserrat_500Medium.ttf", 21), fill=(222, 224, 228))
    hw2 = handwriting(cfg["el_yazisi_alt"], 50, CREAM, 3)
    img.alpha_composite(hw2, (W - hw2.width - 70, 1270))

    out = film_grain(img.convert("RGB"), 7.5, seed=8)
    out.save(path(cfg["cikti"]))
    print("kaydedildi:", path(cfg["cikti"]))


if __name__ == "__main__":
    main()
