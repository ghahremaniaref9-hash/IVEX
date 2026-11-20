"""IVEX Medya - iş ilanı görselleri: fotoğrafçı, kurgucu, reklamcı.

Kullanım:  python3 ilan.py [ayar.json]
Metinler ayarlar/ilan.json'da. Çıktı (ivex-icerik/ilan/):
  ivex-ilan-1-kapak.jpg ... ivex-ilan-5-basvuru.jpg  Instagram karuseli, 1080x1350 (4:5)
  ivex-ilan-hikaye-1-kapak.jpg ... -5-basvuru.jpg    aynı 5 kare hikâye boyutunda, 1080x1920
  ivex-ilan-hikaye.jpg                               tek hikâyelik özet, 1080x1920
  (hikâyelerde Instagram'ın üst 250 / alt 340 pikseline yazı konmaz)
"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from marka import GREEN_DARK, INK, LIME, SOFT, WHITE, background, blend, font, logo, pill, repo  # noqa: E402

FW, FH = 1080, 1350
COLORS = {"beyaz": WHITE, "lime": LIME}
CARD = (10, 40, 18, 230)
LINE = (70, 120, 60, 255)
MUTED = (150, 178, 150)


def canvas(size, seed, glow, transparent):
    if transparent:
        return Image.new("RGBA", size, (0, 0, 0, 0))
    return background(size, seed=seed, glow=glow).convert("RGBA")


def wrap(d, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def centered(d, lines, y, size, weight="Black", gap=1.12, w=FW):
    f = font(weight, size)
    for i, (t, c) in enumerate(lines):
        d.text(((w - d.textlength(t, font=f)) / 2, y + i * size * gap), t, font=f, fill=COLORS.get(c, c))
    return y + len(lines) * size * gap


def card(im, box, radius=32, fill=CARD, outline=LINE):
    blend(im, lambda d: d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2))


def icon(d, kind, cx, cy, s, col=LIME, w=None):
    """Simple line icons: camera, video, chart (s = box size)."""
    w = w or max(3, round(s * 0.075))
    x0, y0 = cx - s / 2, cy - s / 2
    if kind == "kamera":
        d.rounded_rectangle((x0 + 0.06 * s, y0 + 0.28 * s, x0 + 0.94 * s, y0 + 0.86 * s), radius=0.12 * s, outline=col, width=w)
        d.rounded_rectangle((x0 + 0.30 * s, y0 + 0.14 * s, x0 + 0.56 * s, y0 + 0.30 * s), radius=0.05 * s, outline=col, width=w)
        r = 0.17 * s
        d.ellipse((cx - r, y0 + 0.57 * s - r, cx + r, y0 + 0.57 * s + r), outline=col, width=w)
    elif kind == "video":
        d.rounded_rectangle((x0 + 0.06 * s, y0 + 0.2 * s, x0 + 0.94 * s, y0 + 0.8 * s), radius=0.12 * s, outline=col, width=w)
        d.polygon([(x0 + 0.42 * s, y0 + 0.36 * s), (x0 + 0.42 * s, y0 + 0.64 * s), (x0 + 0.66 * s, y0 + 0.5 * s)], fill=col)
    else:  # grafik
        base = y0 + 0.86 * s
        for i, h in enumerate((0.25, 0.42, 0.6)):
            bx = x0 + (0.1 + i * 0.28) * s
            d.rounded_rectangle((bx, base - h * s, bx + 0.18 * s, base), radius=0.03 * s, fill=col)
        d.line([(x0 + 0.08 * s, y0 + 0.42 * s), (x0 + 0.42 * s, y0 + 0.22 * s), (x0 + 0.58 * s, y0 + 0.3 * s),
                (x0 + 0.9 * s, y0 + 0.08 * s)], fill=col, width=w, joint="curve")
        d.line([(x0 + 0.72 * s, y0 + 0.08 * s), (x0 + 0.9 * s, y0 + 0.08 * s), (x0 + 0.9 * s, y0 + 0.26 * s)],
               fill=col, width=w, joint="curve")


def head(im, label, top=78):
    lg = logo(40)
    im.alpha_composite(lg, ((im.width - lg.width) // 2, top))
    if label:
        pill(ImageDraw.Draw(im), im.width / 2, top + 72, label, font("ExtraBold", 26), LIME, INK, pad_x=28, h=58,
             tracking=3, anchor="m")


def role_row(im, n, title, sub, kind, y, x=110, w=860, h=126):
    card(im, (x, y, x + w, y + h), radius=30)
    d = ImageDraw.Draw(im)
    r = 42
    cx, cy = x + 30 + r, y + h / 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=LIME)
    icon(d, kind, cx, cy, 50, INK, 4)
    d.text((x + 140, y + 26), title, font=font("ExtraBold", 42), fill=WHITE)
    d.text((x + 142, y + 80), sub, font=font("Medium", 26), fill=SOFT)
    num = f"0{n}"
    f = font("Black", 40)
    d.text((x + w - 36 - d.textlength(num, font=f), y + 38), num, font=f, fill=(90, 140, 70))


def cover(cfg, roles, transparent=False, kaydir=None):
    im = canvas((FW, FH), 31, (0.75, 0.2), transparent)
    head(im, cfg["etiket"])
    d = ImageDraw.Draw(im)
    centered(d, cfg["baslik"], 250, 104)
    for k, r in enumerate(roles):
        role_row(im, k + 1, r["ad"], r["ek"], r["ikon"], 530 + k * 150)
    d = ImageDraw.Draw(im)
    f = font("Bold", 36)
    t = cfg["slogan"]
    d.text(((FW - d.textlength(t, font=f)) / 2, 1012), t, font=f, fill=LIME)
    nf = font("Medium", 28)
    d.text(((FW - d.textlength(cfg["not"], font=nf)) / 2, 1070), cfg["not"], font=nf, fill=SOFT)
    f2 = font("SemiBold", 26)
    t2 = (kaydir or cfg["kaydir"]) + "  →"
    d.text(((FW - d.textlength(t2, font=f2)) / 2, 1230), t2, font=f2, fill=MUTED)
    return im


def bullets(im, title, items, box, dot=LIME):
    card(im, box)
    d = ImageDraw.Draw(im)
    x0, y0, x1, _ = box
    d.text((x0 + 40, y0 + 30), title, font=font("ExtraBold", 30), fill=LIME)
    f = font("SemiBold", 32)
    y = y0 + 92
    for it in items:
        lines = wrap(d, it, f, x1 - x0 - 120)
        d.ellipse((x0 + 44, y + 13, x0 + 58, y + 27), fill=dot)
        for ln in lines:
            d.text((x0 + 80, y), ln, font=f, fill=WHITE)
            y += 42
        y += 14
    return y


def role(r, n, total, transparent=False):
    im = canvas((FW, FH), 40 + n, (0.2, 0.15), transparent)
    head(im, f"POZİSYON {n:02d} / {total:02d}")
    d = ImageDraw.Draw(im)
    tf = font("Black", 92)
    tw = d.textlength(r["ad"], font=tf)
    gx = (FW - (tw + 120)) / 2
    d.ellipse((gx, 230, gx + 96, 326), fill=LIME)
    icon(d, r["ikon"], gx + 48, 278, 58, INK, 5)
    d.text((gx + 120, 222), r["ad"], font=tf, fill=WHITE)
    sf = font("Medium", 32)
    d.text(((FW - d.textlength(r["ek"], font=sf)) / 2, 340), r["ek"], font=sf, fill=SOFT)
    of = font("Bold", 34)
    d.text(((FW - d.textlength(r["ozet"], font=of)) / 2, 400), r["ozet"], font=of, fill=LIME)
    y = bullets(im, "NELER YAPACAKSIN?", r["isler"], (90, 480, 990, 830))
    bullets(im, "ARADIĞIMIZ", r["aranan"], (90, 860, 990, 1135))
    d = ImageDraw.Draw(im)
    pill(d, FW / 2, 1180, "EKİPMAN BİZDEN, YETENEK SENDEN", font("ExtraBold", 26), LIME, INK, pad_x=30, h=62,
         tracking=2, anchor="m")
    return im


def step_card(n, title, sub, w=860, h=150):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=30, fill=CARD, outline=LINE, width=2)
    d.ellipse((30, h / 2 - 46, 122, h / 2 + 46), fill=LIME)
    f = font("Black", 40)
    num = f"{n:02d}"
    d.text((76 - d.textlength(num, font=f) / 2, h / 2 - 25), num, font=f, fill=INK)
    d.text((150, 34), title, font=font("ExtraBold", 40), fill=WHITE)
    d.text((152, 88), sub, font=font("Medium", 28), fill=SOFT)
    return im


def apply_slide(cfg, transparent=False):
    im = canvas((FW, FH), 55, (0.7, 0.3), transparent)
    head(im, cfg["etiket"])
    d = ImageDraw.Draw(im)
    centered(d, cfg["baslik"], 240, 100)
    for k, (t, s) in enumerate(cfg["adimlar"]):
        sc = step_card(k + 1, t, s)
        im.alpha_composite(sc, ((FW - sc.width) // 2, 500 + k * 175))
    d = ImageDraw.Draw(im)
    pill(d, FW / 2, 1050, cfg["buton"], font("ExtraBold", 32), LIME, INK, pad_x=40, h=84, tracking=2, anchor="m")
    f = font("Medium", 28)
    d.text(((FW - d.textlength(cfg["not"], font=f)) / 2, 1175), cfg["not"], font=f, fill=SOFT)
    return im


def story(cfg, roles):
    W, H = 1080, 1920
    im = background((W, H), seed=61, glow=(0.75, 0.25)).convert("RGBA")
    head(im, cfg["etiket"], top=290)
    d = ImageDraw.Draw(im)
    y = centered(d, cfg["baslik"], 530, 92, w=W)
    for k, r in enumerate(roles):
        role_row(im, k + 1, r["ad"], r["ek"], r["ikon"], round(y + 80 + k * 160))
    d = ImageDraw.Draw(im)
    yy = y + 80 + 3 * 160 + 30
    f = font("Bold", 36)
    d.text(((W - d.textlength(cfg["slogan"], font=f)) / 2, yy), cfg["slogan"], font=f, fill=LIME)
    pill(d, W / 2, yy + 90, cfg["buton"], font("ExtraBold", 32), LIME, INK, pad_x=40, h=84, tracking=2, anchor="m")
    return im


SLIDE_LOOK = [(31, (0.75, 0.2)), (41, (0.2, 0.15)), (42, (0.2, 0.15)), (43, (0.2, 0.15)), (55, (0.7, 0.3))]


def as_story(content, seed, glow, top=285):
    """Put a 4:5 slide's content on a 9:16 brand background, clear of Instagram's top 250 / bottom 340 px."""
    im = background((1080, 1920), seed=seed, glow=glow).convert("RGBA")
    im.alpha_composite(content, (0, top))
    return im


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else repo("ivex-icerik", "ayarlar", "ilan.json")
    cfg = json.load(open(path, encoding="utf-8"))
    out = repo(cfg["klasor"])
    os.makedirs(out, exist_ok=True)
    roles = cfg["pozisyonlar"]
    names = ["1-kapak", "2-fotografci", "3-kurgucu", "4-reklamci", "5-basvuru"]
    slides = [cover(cfg["kapak"], roles)] + [role(r, i + 1, len(roles)) for i, r in enumerate(roles)] + \
             [apply_slide(cfg["basvuru"])]
    for n, im in zip(names, slides):
        p = os.path.join(out, f"ivex-ilan-{n}.jpg")
        im.convert("RGB").save(p, quality=93)
        print("kaydedildi:", os.path.relpath(p, repo()))
    layers = [cover(cfg["kapak"], roles, True, cfg["kapak"].get("hikaye_kaydir"))] + \
             [role(r, i + 1, len(roles), True) for i, r in enumerate(roles)] + [apply_slide(cfg["basvuru"], True)]
    for n, lay, (seed, glow) in zip(names, layers, SLIDE_LOOK):
        p = os.path.join(out, f"ivex-ilan-hikaye-{n}.jpg")
        as_story(lay, seed, glow).convert("RGB").save(p, quality=93)
        print("kaydedildi:", os.path.relpath(p, repo()))
    p = os.path.join(out, "ivex-ilan-hikaye.jpg")
    story(cfg["hikaye"], roles).convert("RGB").save(p, quality=93)
    print("kaydedildi:", os.path.relpath(p, repo()))


if __name__ == "__main__":
    main()
