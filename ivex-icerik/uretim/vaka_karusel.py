"""IVEX Medya - case-study carousel built from a client's real feed (1080x1350 slides).

Kullanım:  python3 vaka_karusel.py ayarlar/gun2-vaka-mekan-sizin.json
Metinlerde *yıldız* arasındaki kısım lime renkte yazılır.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageOps

from marka import INK, LIME, SOFT, WHITE, background, blend, drop_shadow, font, pill, repo, rounded, tracked, logo

W, H = 1080, 1350
M = 84  # side margin; the 3:4 profile crop removes 34 px per side


def rich(d, x, y, text, fnt, color=WHITE, hi=LIME, anchor="l"):
    """One line where *starred* parts are drawn in the highlight colour."""
    parts = text.split("*")
    total = sum(d.textlength(p, font=fnt) for p in parts)
    if anchor == "m":
        x -= total / 2
    for i, p in enumerate(parts):
        d.text((x, y), p, font=fnt, fill=hi if i % 2 else color)
        x += d.textlength(p, font=fnt)


def wrap(d, text, fnt, max_w):
    """Greedy word wrap on plain spaces; a no-break space (U+00A0) keeps words on one line."""
    lines, cur = [], ""
    for word in text.split(" "):
        t = (cur + " " + word).strip()
        if d.textlength(t.replace("*", ""), font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def paragraph(d, x, y, text, fnt, color, max_w, lh, anchor="l"):
    """Wrapped text; a *highlight* must not span a line break. Returns the y below the last line."""
    for line in wrap(d, text, fnt, max_w):
        rich(d, x, y, line, fnt, color, anchor=anchor)
        y += lh
    return y


def post(path, w, radius=22):
    im = ImageOps.exif_transpose(Image.open(repo(path))).convert("RGB")
    h = round(w * im.height / im.width)
    return rounded(im.resize((w, h), Image.LANCZOS), radius)


def tilted(card, angle):
    return card.rotate(angle, resample=Image.BICUBIC, expand=True)


def frame(n, total, kicker):
    """Inner-slide chrome: logo, page number, kicker. Returns (image, draw)."""
    im = background((W, H), seed=20 + n, glow=(0.85, 0.08)).convert("RGBA")
    lg = logo(36)
    im.alpha_composite(lg, (M, 76))
    d = ImageDraw.Draw(im)
    tracked(d, (W - M, 80), f"{n:02d} / {total:02d}", font("Bold", 22), SOFT, 3, anchor="r")
    tracked(d, (M, 168), kicker, font("ExtraBold", 22), LIME, 5)
    return im, d


def title(d, lines, y=208, size=66):
    f = font("Black", size)
    for line in lines:
        rich(d, M, y, line, f)
        y += round(size * 1.16)
    return y


def arrow(d, x, y, color, length=46):
    d.line((x, y, x + length, y), fill=color, width=5)
    d.polygon([(x + length + 4, y), (x + length - 12, y - 11), (x + length - 12, y + 11)], fill=color)


def cover(cfg, total):
    k = cfg["kapak"]
    im = background((W, H), seed=11, glow=(0.75, 0.62)).convert("RGBA")
    lg = logo(42)
    im.alpha_composite(lg, (M, 78))

    def chip(d):
        f = font("ExtraBold", 20)
        tw = sum(d.textlength(c, font=f) for c in k["etiket"]) + 4 * (len(k["etiket"]) - 1) + 48
        pill(d, W - M - tw, 74, k["etiket"], f, (255, 255, 255, 30), LIME, pad_x=24, tracking=4, h=48)

    blend(im, chip)
    d = ImageDraw.Draw(im)
    y = 196
    f = font("Black", 84)
    for line in k["baslik"]:
        rich(d, M, y, line, f)
        y += 98
    d.text((M, y + 18), k["alt"], font=font("Medium", 30), fill=SOFT)

    # fan of three real posts
    cw = 372
    left, mid, right = (post(p, cw) for p in k["gorseller"])
    base_y = 640
    for card, angle, dx, dy in ((left, 8, -250, 60), (right, -8, 250, 60)):
        t = tilted(card, angle)
        drop_shadow(im, t, (round(W / 2 + dx - t.width / 2), base_y + dy), blur=26, offset=(0, 18), opacity=170)
    drop_shadow(im, mid, (round(W / 2 - mid.width / 2), base_y - 40), blur=30, offset=(0, 22), opacity=190)

    def swipe(d):
        d.rounded_rectangle((W - M - 236, H - 132, W - M, H - 72), radius=30, fill=LIME)

    blend(im, swipe)
    d = ImageDraw.Draw(im)
    tracked(d, (W - M - 208, H - 117), "KAYDIR", font("ExtraBold", 24), INK, 4)
    arrow(d, W - M - 76, H - 102, INK, 40)
    return im


def rules_slide(cfg, n, total):
    s = cfg["kurallar"]
    im, d = frame(n, total, s["ust"])
    y = title(d, s["baslik"]) + 56
    for i, (head, body) in enumerate(s["maddeler"]):
        d.line((M, y, W - M, y), fill=(255, 255, 255), width=1)
        y += 50
        d.text((M, y - 8), f"{i + 1:02d}", font=font("Black", 66), fill=LIME)
        d.text((M + 134, y), head, font=font("ExtraBold", 42), fill=WHITE)
        y = paragraph(d, M + 134, y + 64, body, font("Medium", 31), SOFT, W - 2 * M - 134, 45) + 50
    return im


def grid_slide(cfg, n, total):
    s = cfg["izgara"]
    im, d = frame(n, total, s["ust"])
    y = title(d, s["baslik"])
    y = paragraph(d, M, y + 10, s["metin"], font("Medium", 28), SOFT, W - 2 * M, 40) + 34
    gap, tw = 4, 238
    th = round(tw * 4 / 3)
    gw = 3 * tw + 2 * gap
    grid = Image.new("RGB", (gw, 3 * th + 2 * gap), (255, 255, 255))
    for i, f in enumerate(s["gonderiler"]):
        t = ImageOps.exif_transpose(Image.open(repo(f))).convert("RGB")
        cw = round(t.height * 3 / 4)
        x0 = (t.width - cw) // 2
        t = t.crop((x0, 0, x0 + cw, t.height)).resize((tw, th), Image.LANCZOS)
        grid.paste(t, ((i % 3) * (tw + gap), (i // 3) * (th + gap)))
    scale = min(1.0, (H - 70 - y) / grid.height)
    grid = grid.resize((round(gw * scale), round(grid.height * scale)), Image.LANCZOS)
    drop_shadow(im, rounded(grid, 18), ((W - grid.width) // 2, y), blur=26, offset=(0, 16), opacity=170)
    return im


def concepts_slide(cfg, n, total):
    s = cfg["konseptler"]
    im, d = frame(n, total, s["ust"])
    y = title(d, s["baslik"]) + 28
    cw, gap_x = 290, 70
    xs = ((W - 2 * cw - gap_x) // 2, (W + gap_x) // 2)
    for i, (label, name, path) in enumerate(s["kartlar"]):
        card = post(path, cw, 18)
        x = xs[i % 2]
        cy = y + (i // 2) * (card.height + 100)
        drop_shadow(im, card, (x, cy), blur=20, offset=(0, 12), opacity=160)
        d = ImageDraw.Draw(im)
        tracked(d, (x, cy + card.height + 18), label, font("ExtraBold", 21), LIME, 3)
        d.text((x, cy + card.height + 48), name, font=font("SemiBold", 27), fill=WHITE)
    return im


def feature_slide(spec, n, total):
    im, d = frame(n, total, spec["ust"])
    y = title(d, spec["baslik"])
    y = paragraph(d, M, y + 10, spec["metin"], font("Medium", 29), SOFT, W - 2 * M, 42) + 40
    cw = min(560, round((H - 80 - y) * 4 / 5))
    card = post(spec["gorsel"], cw)
    drop_shadow(im, card, ((W - card.width) // 2, y), blur=28, offset=(0, 18), opacity=180)
    return im


def checklist_slide(cfg, n, total):
    s = cfg["algoritma"]
    im, d = frame(n, total, s["ust"])
    y = title(d, s["baslik"]) + 56
    for head, body in s["maddeler"]:
        d.rounded_rectangle((M, y + 2, M + 52, y + 54), radius=12, fill=LIME)
        d.line((M + 12, y + 29, M + 23, y + 41, M + 41, y + 15), fill=INK, width=7, joint="curve")
        d.text((M + 84, y), head, font=font("ExtraBold", 40), fill=WHITE)
        y = paragraph(d, M + 84, y + 58, body, font("Medium", 30), SOFT, W - 2 * M - 84, 42) + 46
    return im


def cta_slide(cfg, n, total):
    s = cfg["son"]
    im = background((W, H), seed=40, glow=(0.5, 0.35)).convert("RGBA")
    lg = logo(104)
    im.alpha_composite(lg, ((W - lg.width) // 2, 250))
    d = ImageDraw.Draw(im)
    y = 250 + lg.height + 90
    f = font("Black", 64)
    for line in s["baslik"]:
        rich(d, W / 2, y, line, f, anchor="m")
        y += 76
    pill(d, W / 2, y + 50, s["buton"], font("ExtraBold", 32), LIME, INK, pad_x=38, h=84, tracking=2, anchor="m")
    y = paragraph(d, W / 2, y + 170, s["metin"], font("Medium", 29), SOFT, 820, 42, anchor="m")
    tracked(d, (W / 2, H - 150), s["not"], font("SemiBold", 24), WHITE, 1, anchor="m")
    tracked(d, (W / 2, H - 100), "WWW.İVEX.COM.TR", font("Bold", 22), (196, 214, 198), 6, anchor="m")
    return im


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    makers = [lambda n, t: cover(cfg, t), lambda n, t: rules_slide(cfg, n, t), lambda n, t: grid_slide(cfg, n, t),
              lambda n, t: concepts_slide(cfg, n, t)]
    makers += [lambda n, t, s=s: feature_slide(s, n, t) for s in cfg["ozellikler"]]
    makers += [lambda n, t: checklist_slide(cfg, n, t), lambda n, t: cta_slide(cfg, n, t)]
    total = len(makers)
    for n, make in enumerate(makers, start=1):
        out = repo(f"{cfg['cikti_oneki']}-{n}.png")
        make(n, total).convert("RGB").save(out)
        print("kaydedildi:", out)


if __name__ == "__main__":
    main()
