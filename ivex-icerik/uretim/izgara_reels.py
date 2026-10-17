"""IVEX Medya - "Profili kuruyoruz" Reels: a client's posts drop into the profile grid one by one (1080x1920).

Kullanım:  python3 izgara_reels.py ayarlar/gun3-izgara-reels.json
Gönderiler paylaşım sırasıyla verilir (en eski önce); her yeni gönderi sol üste girer, diğerleri kayar,
tıpkı Instagram profilinde olduğu gibi. Sonda karelere gün numaraları gelir (1 = ilk paylaşım).
Başlık satırları [metin, "beyaz" | "lime"] çiftleridir.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageOps

from marka import (INK, LIME, WHITE, background, blend, drop_shadow, end_card, font, pill, repo, rounded,
                   logo, write_video)

W, H, FPS = 1080, 1920, 30
TW, TH, GAP = 270, 360, 8
GX = (W - (3 * TW + 2 * GAP)) // 2
GY = 492
STEP, MOVE = 0.62, 0.36
INTRO, HOLD, NUMBERS, END = 0.5, 1.4, 3.2, 3.0


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_back(t):
    """Ease-out with a small overshoot, for the number badges."""
    t = min(max(t, 0.0), 1.0)
    return 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2


def slot(i):
    return GX + (i % 3) * (TW + GAP), GY + (i // 3) * (TH + GAP)


def tile(path):
    im = ImageOps.exif_transpose(Image.open(repo(path))).convert("RGB")
    cw = round(im.height * 3 / 4)
    x0 = (im.width - cw) // 2
    return rounded(im.crop((x0, 0, x0 + cw, im.height)).resize((TW, TH), Image.LANCZOS), 14)


COLORS = {"beyaz": WHITE, "lime": LIME}


def headline(text_lines):
    im = Image.new("RGBA", (W, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Black", 58)
    for i, (line, col) in enumerate(text_lines):
        d.text(((W - d.textlength(line, font=f)) / 2, i * 70), line, font=f, fill=col)
    return im


def fade(layer, a):
    if a >= 1:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: round(v * max(a, 0))))
    return out


def badge(n, scale=1.0):
    s = max(1, round(64 * scale))
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=LIME, outline=INK, width=max(1, round(3 * scale)))
    f = font("Black", max(8, round(34 * scale)))
    t = str(n)
    d.text(((s - d.textlength(t, font=f)) / 2, s * 0.16), t, font=f, fill=INK)
    return im


def base(bg, client):
    im = bg.copy()
    lg = logo(40)
    im.alpha_composite(lg, ((W - lg.width) // 2, 118))

    def draw(d):
        pill(d, W / 2, 192, client, font("Bold", 22), (255, 255, 255, 26), LIME, pad_x=26, tracking=5, h=48,
             anchor="m")
        for i in range(9):
            x, y = slot(i)
            d.rounded_rectangle((x, y, x + TW, y + TH), radius=14, outline=(255, 255, 255, 46), width=2)

    blend(im, draw)
    return im


def day_pill(canvas, text, a):
    if a <= 0:
        return
    layer = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
    pill(ImageDraw.Draw(layer), W / 2, 4, text, font("ExtraBold", 24), LIME, INK, pad_x=28, h=50, tracking=3,
         anchor="m")
    canvas.alpha_composite(fade(layer, a), (0, 410))


def frames(cfg):
    bg = background((W, H), seed=9, glow=(0.2, 0.15)).convert("RGBA")
    posts = cfg["gonderiler"]
    tiles = [tile(p["dosya"]) for p in posts]
    plate = base(bg, cfg["musteri"])
    h_build = headline([(t, COLORS[c]) for t, c in cfg["baslik_kurulum"]])
    h_done = headline([(cfg["baslik_bitti"], LIME)])
    h_final = headline([(t, COLORS[c]) for t, c in cfg["son_baslik"]])

    def grid(canvas, k, t_in):
        """Grid after k posts; the newest is mid-animation with progress t_in (0..1)."""
        e = ease(t_in / (MOVE / STEP))
        for j in range(k):
            idx = k - 1 - j
            if j == k - 1:  # newest: pops in at the top-left slot
                sc = 0.86 + 0.14 * e
                t = tiles[j].resize((round(TW * sc), round(TH * sc)), Image.BILINEAR)
                t = fade(t, e)
                x, y = slot(0)
                drop_shadow(canvas, t, (round(x + (TW - t.width) / 2), round(y + (TH - t.height) / 2)),
                            blur=14, offset=(0, 8), opacity=round(150 * e))
            else:
                (x0, y0), (x1, y1) = slot(idx - 1), slot(idx)
                x, y = x0 + (x1 - x0) * e, y0 + (y1 - y0) * e
                drop_shadow(canvas, tiles[j], (round(x), round(y)), blur=14, offset=(0, 8), opacity=150)

    # intro: empty grid with the hook
    for k in range(round(INTRO * FPS)):
        c = plate.copy()
        c.alpha_composite(h_build, (0, 262))
        yield c.convert("RGB")
    # build: one post per step
    step_frames = round(STEP * FPS)
    for k in range(1, len(tiles) + 1):
        for f in range(step_frames):
            c = plate.copy()
            c.alpha_composite(h_build, (0, 262))
            grid(c, k, f / step_frames)
            day_pill(c, posts[k - 1]["etiket"], min(1, f / 4))
            yield c.convert("RGB")
    full = plate.copy()
    grid(full, len(tiles), 1)
    # hold the finished profile
    for f in range(round(HOLD * FPS)):
        c = full.copy()
        a_out, a_in = ease(f / 6), ease((f - 5) / 8)
        c.alpha_composite(fade(h_build, 1 - a_out), (0, round(262 - 30 * a_out)))
        c.alpha_composite(fade(h_done, a_in), (0, round(292 - 30 * a_in)))
        yield c.convert("RGB")
    # numbers pop onto the tiles: "which one is your favourite?"
    for f in range(round(NUMBERS * FPS)):
        c = full.copy()
        a_out, a_in = ease(f / 6), ease((f - 5) / 8)
        c.alpha_composite(fade(h_done, 1 - a_out), (0, round(262 - 30 * a_out)))
        c.alpha_composite(fade(h_final, a_in), (0, round(292 - 30 * a_in)))
        for i in range(9):
            t = (f - 6 - i * 2) / 8
            if t <= 0:
                continue
            b = badge(len(tiles) - i, max(0.05, ease_back(t)))  # slot 0 holds the newest post
            x, y = slot(i)
            c.alpha_composite(b, (round(x + 18 + (64 - b.width) / 2), round(y + 18 + (64 - b.height) / 2)))
        yield c.convert("RGB")
    last = c
    end = end_card(bg, [(cfg["son"][0], WHITE), (cfg["son"][1], LIME)], cfg["buton"], cfg["alt"])
    for f in range(round(END * FPS)):
        a = ease(f / 12)
        yield Image.blend(last, end, a).convert("RGB")


def cover(cfg, path):
    bg = background((W, H), seed=9, glow=(0.2, 0.15)).convert("RGBA")
    im = base(bg, cfg["musteri"])
    tiles = [tile(p["dosya"]) for p in cfg["gonderiler"]]
    for i, t in enumerate(reversed(tiles)):
        drop_shadow(im, t, slot(i), blur=14, offset=(0, 8), opacity=150)
        im.alpha_composite(badge(len(tiles) - i), (slot(i)[0] + 18, slot(i)[1] + 18))
    im.alpha_composite(headline([(t, COLORS[c]) for t, c in cfg["son_baslik"]]), (0, 262))
    im.convert("RGB").save(path, quality=93)
    print("kaydedildi:", path)


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    write_video(frames(cfg), repo(cfg["cikti"]), (W, H), FPS)
    cover(cfg, repo(cfg["kapak"]))


if __name__ == "__main__":
    main()
