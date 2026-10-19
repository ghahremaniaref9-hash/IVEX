"""Mekan Sizin - 'Maç Sonu' story'si (1080x1920): skorbordda gerçek skor, sonuca göre el yazısı mesaj.

Kullanım:  python3 mac_sonu.py mac-sonu.json EV_SKOR DEPLASMAN_SKOR
Örnek:     python3 mac_sonu.py ../haftalik-feed-2/ayarlar/1b-trabzonspor-mac-sonu.json 1 2
"bjk" alanı Beşiktaş'ın hangi satırda olduğunu söyler ("ev_sahibi" ya da "deplasman"); mesaj buna göre
"galibiyet", "beraberlik" ya da "maglubiyet" olarak seçilir. Alttaki boşluk doğru tahmin edenleri
etiketlemek için bırakıldı (Instagram'da "Bahset" çıkartması).
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFilter

from foto import film_grain, process
from mac_bileti import CREAM, RED, fit_font, font, handwriting, path, stamp, tracked
from skor_tahmini import scoreboard
from story import darken, hand_arrow

W, H = 1080, 1920


def result(cfg, home, away):
    bjk, other = (home, away) if cfg["bjk"] == "ev_sahibi" else (away, home)
    return "galibiyet" if bjk > other else "beraberlik" if bjk == other else "maglubiyet"


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    home, away = int(sys.argv[2]), int(sys.argv[3])
    cfg["ev_sahibi"]["skor"], cfg["deplasman"]["skor"] = home, away
    sonuc = result(cfg, home, away)

    foto = dict(cfg["foto"], boyut=[W, H], gren=0)
    img = darken(process(foto, (W, H)), *cfg.get("karartma", (0.4, 0.4, 0.8))).convert("RGBA")
    d = ImageDraw.Draw(img)

    logo = Image.open(path("assets/mekan-sizin-plaka-logo.png")).convert("RGBA")
    lw = 440
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, 236))
    tracked(d, (W / 2, 338), cfg["ust_satir"], font("Montserrat_600SemiBold.ttf", 24), CREAM, 7, anchor_center=True)
    baslik = cfg.get("baslik", "MAÇ SONU")
    bf = fit_font("Anton_400Regular.ttf", 236, baslik, 960)
    d.text((W / 2, 392), baslik, font=bf, fill=(250, 248, 244), anchor="ma")
    head_bottom = d.textbbox((W / 2, 392), baslik, font=bf, anchor="ma")[3]
    hw = handwriting(cfg["mesajlar"][sonuc], 66, RED, 4)
    img.alpha_composite(hw, (W - hw.width - 70, head_bottom - 6))

    board = scoreboard(cfg)
    board = board.resize((round(board.width * 0.98), round(board.height * 0.98)), Image.LANCZOS)
    br = board.rotate(1.2, resample=Image.BICUBIC, expand=True)
    bx, by = (W - br.width) // 2, head_bottom + 130
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    s = Image.new("RGBA", br.size, (0, 0, 0, 0))
    s.putalpha(br.getchannel("A").point(lambda v: int(v * 0.85)))
    sh.paste(s, (bx + 10, by + 22))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(18)))
    img.alpha_composite(br, (bx, by))
    board_bottom = by + br.height

    st = stamp(cfg.get("damga_ust", "TAM SKOR"), "MEKAN SİZİN'DE", seed=cfg.get("damga_seed", 37))
    st = st.rotate(-8, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(st, (W - st.width - 40, board_bottom - 96))

    # Next match + address right under the board
    d = ImageDraw.Draw(img)
    by2 = board_bottom + 56
    d.text((W / 2, by2), cfg["alt_baslik"], font=fit_font("Anton_400Regular.ttf", 74, cfg["alt_baslik"], 940),
           fill=(250, 248, 244), anchor="mt")
    d.text((W / 2, by2 + 92), cfg["alt_metin"], font=font("Montserrat_500Medium.ttf", 26), fill=(214, 214, 218),
           anchor="mt")
    adres = cfg["adres"]
    af = font("Montserrat_500Medium.ttf", 23)
    aw = d.textlength(adres, font=af)
    pin_x, pin_y = round(W / 2 - (aw + 34) / 2), by2 + 146
    d.ellipse((pin_x, pin_y, pin_x + 20, pin_y + 20), fill=RED)
    d.polygon([(pin_x + 2, pin_y + 13), (pin_x + 18, pin_y + 13), (pin_x + 10, pin_y + 30)], fill=RED)
    d.ellipse((pin_x + 6, pin_y + 6, pin_x + 14, pin_y + 14), fill=(20, 20, 20))
    d.text((pin_x + 34, pin_y + 1), adres, font=af, fill=(225, 222, 214))

    # Empty space at the bottom for mention stickers: who guessed the score right
    note = handwriting(cfg["cikartma_notu"], 60, CREAM, 3)
    ny = by2 + 218
    img.alpha_composite(note, (86, ny))
    img.alpha_composite(hand_arrow((210, 120), CREAM), (96 + note.width - 60, ny + note.height // 2))

    out = film_grain(img.convert("RGB"), 7.5, seed=9)
    out.save(path(cfg["cikti"]))
    print("kaydedildi:", path(cfg["cikti"]), f"({home}-{away}, {sonuc})")


if __name__ == "__main__":
    main()
