"""Minah Tekstil - Meta (Facebook / Instagram) reklam görselleri.

Kullanım:  python3 reklam.py [ayarlar.json]
Her ürün için üç görsel üretir:
  - akis/    4:5, 1080x1350: akış reklamı. Üstte iki fotoğraf yan yana (ya da tek fotoğraf), altta krem panelde ürün adı,
             başlık, özellikler, logo ve "Trendyol'da incele" düğmesi.
  - hikaye/  9:16, 1080x1920: hikaye ve Reels. Ya iki fotoğraf yan yana ve altta lacivert kart, ya tek fotoğraf ve
             üstüne krem kart. Yazılar Meta'nın üstteki ve alttaki arayüz şeritlerinin dışında kalır.
  - kart/    1:1, 1080x1080: kaydırmalı (karusel) reklamın kartları; sonuncusu marka kartı.
Ayarlardaki "gizle" kutuları (eşofmandaki başka markanın yazısı) hiçbir kadraja girmez; girerse betik durur.
Fiyat, indirim, kargo gibi bilgiler bilinmediği için görsellere yazılmaz.
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FONTS = os.path.join(REPO, "ivex-icerik", "uretim", "fonts")
LOGO = os.path.join(REPO, "minah-tekstil", "marka", "minah-tekstil-logo.png")

CREAM = (246, 244, 238)
WHITE = (255, 255, 255)
TEAL = (27, 61, 73)
BRONZE = (136, 104, 70)
TAN = (198, 160, 114)
SOFT = (226, 218, 204)  # light text on teal

_fonts, _photos = {}, {}


def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONTS, f"Montserrat_{weight}.ttf"), size)
    return _fonts[key]


def repo(path):
    return os.path.join(REPO, path)


# ---------------------------------------------------------------- photos

class Blocked(Exception):
    pass


def crop_box(size, roi, aspect):
    """Smallest box of the given aspect around the region of interest, kept inside the photo."""
    W, H = size
    x0, y0, x1, y1 = roi[0] * W, roi[1] * H, roi[2] * W, roi[3] * H
    w, h = x1 - x0, y1 - y0
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    if w > W:
        w, h = W, W / aspect
    if h > H:
        h, w = H, H * aspect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    left = min(max(cx - w / 2, 0), W - w)
    top = min(max(cy - h / 2, 0), H - h)
    return (left, top, left + w, top + h)


def photo(cfg, name, roi, size, covered=None):
    """Crop `name` to `size` around `roi`. A hidden box may only land inside `covered` (canvas-space rectangle
    relative to this photo's top-left), otherwise it must stay out of frame."""
    if name not in _photos:
        _photos[name] = Image.open(repo(os.path.join(cfg["kaynak"], name))).convert("RGB")
    img = _photos[name]
    box = crop_box(img.size, roi, size[0] / size[1])
    hidden = cfg.get("gizle", {}).get(name)
    if hidden:
        W, H = img.size
        hx0, hy0, hx1, hy1 = hidden[0] * W, hidden[1] * H, hidden[2] * W, hidden[3] * H
        if hx1 > box[0] and hx0 < box[2] and hy1 > box[1] and hy0 < box[3]:
            s = size[0] / (box[2] - box[0])
            mapped = ((hx0 - box[0]) * s, (hy0 - box[1]) * s, (hx1 - box[0]) * s, (hy1 - box[1]) * s)
            ok = covered and mapped[0] >= covered[0] and mapped[1] >= covered[1] and mapped[2] <= covered[2] \
                and mapped[3] <= covered[3]
            if not ok:
                raise Blocked(f"{name}: gizlenecek alan kadraja giriyor ({[round(v) for v in mapped]})")
    out = img.crop(tuple(round(v) for v in box)).resize(size, Image.LANCZOS)
    out = ImageEnhance.Contrast(out).enhance(1.03)
    out = ImageEnhance.Color(out).enhance(1.03)
    if size[0] > box[2] - box[0]:  # upscaled: a light sharpen
        out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=45, threshold=2))
    return out


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


# ---------------------------------------------------------------- drawing helpers

def tracked_width(text, fnt, track):
    return sum(fnt.getlength(c) for c in text) + track * (len(text) - 1)


def tracked(d, xy, text, fnt, fill, track):
    x, y = xy
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill)
        x += fnt.getlength(c) + track


def wrap(text, fnt, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if fnt.getlength(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(text, weight, sizes, width, max_lines):
    """Largest size from `sizes` at which `text` fits in one line or, if allowed, two balanced lines."""
    if "|" in text:  # line breaks chosen by hand, used whenever the text needs more than one line
        parts = [t.strip() for t in text.split("|")]
        joined = " ".join(parts)
        for s in sizes:
            f = font(weight, s)
            if f.getlength(joined) <= width:
                return f, [joined]
            if len(parts) <= max_lines and all(f.getlength(t) <= width for t in parts):
                return f, parts
        text = joined
    words = text.split()
    for s in sizes:
        f = font(weight, s)
        if f.getlength(text) <= width:
            return f, [text]
        if max_lines >= 2:
            splits = [(" ".join(words[:k]), " ".join(words[k:])) for k in range(1, len(words))]
            splits = [sp for sp in splits if max(f.getlength(x) for x in sp) <= width]
            if splits:
                return f, list(min(splits, key=lambda sp: max(f.getlength(x) for x in sp)))
    f = font(weight, sizes[-1])
    return f, wrap(text, f, width)


def fit_track(text, weight, size, track, width):
    while size > 12 and tracked_width(text, font(weight, size), track) > width:
        size -= 1
    return font(weight, size)


def shadow(im, box, radius, strength=70, blur=18, dy=8):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((box[0], box[1] + dy, box[2], box[3] + dy), radius=radius,
                                            fill=(20, 30, 35, strength))
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def badge(im, center, size):
    lg = Image.open(LOGO).convert("RGBA").resize((size, size), Image.LANCZOS)
    x, y = round(center[0] - size / 2), round(center[1] - size / 2)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    a = lg.getchannel("A").point(lambda v: v * 0.35)
    sh.paste((20, 30, 35, 255), (x, y + 6), a)
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    im.alpha_composite(lg, (x, y))


def arrow(d, x, cy, color, w=26, t=4):
    d.line([(x, cy), (x + w, cy)], fill=color, width=t)
    d.line([(x + w - 11, cy - 10), (x + w, cy), (x + w - 11, cy + 10)], fill=color, width=t, joint="curve")


def button(im, box, text, bg, fg):
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=(y1 - y0) // 2, fill=bg)
    h = y1 - y0
    f = fit_track(text, "700Bold", round(h * 0.32), 1.5, (x1 - x0) - h * 0.9 - 40)
    tw = tracked_width(text, f, 1.5)
    total = tw + 16 + 26
    tx = x0 + ((x1 - x0) - total) / 2
    top, bottom = f.getbbox("Hİ")[1], f.getbbox("H")[3]
    tracked(d, (tx, y0 + h / 2 - (top + bottom) / 2), text, f, fg, 1.5)
    arrow(d, tx + tw + 16, y0 + h / 2, fg)


def tag(im, xy, text):
    """Small cream label on a photo, e.g. "Önden"."""
    d = ImageDraw.Draw(im)
    f = font("700Bold", 24)
    w = tracked_width(text.upper(), f, 2) + 40
    x, y = xy
    d.rounded_rectangle((x, y, x + w, y + 46), radius=23, fill=CREAM)
    tracked(d, (x + 20, y + 10), text.upper(), f, TEAL, 2)


def stitch(d, x0, x1, y, color=TAN, dash=14, gap=10, width=3):
    x = x0
    while x < x1:
        d.line([(x, y), (min(x + dash, x1), y)], fill=color, width=width)
        x += dash + gap


def features(d, xy, items, fnt, color, dot):
    x, y = xy
    for i, item in enumerate(items):
        if i:
            cy = y + fnt.getbbox("x")[3] * 0.62
            d.polygon([(x + 12, cy - 5), (x + 17, cy), (x + 12, cy + 5), (x + 7, cy)], fill=dot)
            x += 30
        d.text((x, y), item, font=fnt, fill=color)
        x += fnt.getlength(item)


def features_width(items, fnt):
    return sum(fnt.getlength(i) for i in items) + 30 * (len(items) - 1)


# ---------------------------------------------------------------- formats

def feed(cfg, p):
    """4:5 feed ad."""
    W, H, PH = 1080, 1350, 1000
    im = Image.new("RGBA", (W, H), CREAM + (255,))
    slots = p["akis"]
    boxes = [(0, 0, 536, PH), (544, 0, W, PH)] if len(slots) == 2 else [(0, 0, W, PH)]
    for s, b in zip(slots, boxes):
        im.paste(photo(cfg, s["foto"], s["alan"], (b[2] - b[0], b[3] - b[1])), b[:2])
        if s.get("not"):
            tag(im, (b[0] + 24, b[1] + 24), s["not"])
    d = ImageDraw.Draw(im)
    stitch(d, 40, 760, 1022)
    badge(im, (880, PH), 196)
    d = ImageDraw.Draw(im)
    x = 60
    f = fit_track(p["etiket"], "600SemiBold", 22, 2.5, 640)
    tracked(d, (x, 1046), p["etiket"], f, BRONZE, 2.5)
    hf, lines = fit(p["baslik"], "800ExtraBold", (54, 52, 50, 48, 46, 44), 640, 2)
    y = 1082
    for line in lines:
        d.text((x - 2, y), line, font=hf, fill=TEAL)
        y += round(hf.size * 1.14)
    ff = font("500Medium", 26)
    while features_width(p["ozellikler"], ff) > 640 and ff.size > 18:
        ff = font("500Medium", ff.size - 1)
    features(d, (x, max(y + 22, 1236)), p["ozellikler"], ff, TEAL, TAN)
    button(im, (712, 1148, 1048, 1220), cfg["buton"], TEAL, CREAM)
    sf = font("500Medium", 21)
    d = ImageDraw.Draw(im)
    d.text((880 - sf.getlength(cfg["magaza"]) / 2, 1242), cfg["magaza"], font=sf, fill=BRONZE)
    return im.convert("RGB")


def story_text(p, inner, lines_max):
    """Fonts, lines and the height of the story card for this product."""
    hf, lines = fit(p["baslik"], "800ExtraBold", (60, 58, 56, 54, 52, 50, 48, 46, 44), inner, lines_max)
    ff = font("500Medium", 27)
    while features_width(p["ozellikler"], ff) > inner and ff.size > 18:
        ff = font("500Medium", ff.size - 1)
    lh = round(hf.size * 1.12)
    height = 76 + len(lines) * lh + 16 + round(ff.size * 1.25) + 28 + 72 + 38
    return hf, lines, lh, ff, height


def story(cfg, p):
    """9:16 story / reels ad. Text stays between the top 250 px and the bottom 340 px that Meta covers."""
    W, H = 1080, 1920
    s = p["hikaye"]
    pair = s["tur"] == "ikili"
    card_x0, card_x1, bottom = (36, 1044, 1572) if pair else (48, 1032, 1566)
    hf, lines, lh, ff, height = story_text(p, card_x1 - card_x0 - 80, 1 if pair else 2)
    card = (card_x0, bottom - height, card_x1, bottom)
    if pair:
        im = Image.new("RGBA", (W, H), CREAM + (255,))
        top, low = 180, card[1] - 28
        for ph, x0 in zip(s["fotolar"], (36, 544)):
            b = (x0, top, x0 + 500, low)
            img = photo(cfg, ph["foto"], ph["alan"], (b[2] - b[0], b[3] - b[1]))
            im.alpha_composite(rounded(img, 28), b[:2])
            if ph.get("not"):
                tag(im, (b[0] + 20, b[1] + 20), ph["not"])
        bg, ink, sub, label, btn_bg, btn_fg = TEAL, CREAM, SOFT, TAN, CREAM, TEAL
    else:
        im = photo(cfg, s["foto"], s["alan"], (W, H), covered=card).convert("RGBA")
        bg, ink, sub, label, btn_bg, btn_fg = CREAM, TEAL, TEAL, BRONZE, TEAL, CREAM
    shadow(im, card, 34)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(card, radius=34, fill=bg)
    badge(im, (card[0] + 112, card[1]), 164)
    d = ImageDraw.Draw(im)
    x = card[0] + 40
    f = fit_track(p["etiket"], "600SemiBold", 22, 2.5, card[2] - card[0] - 250)
    tracked(d, (card[0] + 216, card[1] + 24), p["etiket"], f, label, 2.5)
    y = card[1] + 76
    for line in lines:
        d.text((x - 2, y), line, font=hf, fill=ink)
        y += lh
    features(d, (x, y + 16), p["ozellikler"], ff, sub, TAN)
    by = card[3] - 38 - 72
    button(im, (x, by, x + 400, by + 72), cfg["buton"], btn_bg, btn_fg)
    sf = font("500Medium", 22)
    d = ImageDraw.Draw(im)
    d.text((x + 430, by + 24), cfg["magaza"], font=sf, fill=label)
    return im.convert("RGB")


def carousel_card(cfg, p):
    """1:1 carousel card: the photo, a small logo and the product name."""
    S = 1080
    k = p["kart"]
    im = photo(cfg, k["foto"], k["alan"], (S, S)).convert("RGBA")
    badge(im, (98, 98), 132)
    name = p["etiket"].replace(" · ", " – ")
    title = fit_track(name, "700Bold", 34, 1, 880)
    ff = font("500Medium", 24)
    w = max(tracked_width(name, title, 1), features_width(p["ozellikler"], ff)) + 64
    box = (40, S - 40 - 132, 40 + w, S - 40)
    shadow(im, box, 26, strength=55, blur=14, dy=6)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, radius=26, fill=CREAM)
    tracked(d, (box[0] + 32, box[1] + 26), name, title, TEAL, 1)
    features(d, (box[0] + 32, box[1] + 80), p["ozellikler"], ff, BRONZE, TAN)
    return im.convert("RGB")


def brand_card(cfg):
    S = 1080
    im = Image.new("RGBA", (S, S), CREAM + (255,))
    d = ImageDraw.Draw(im)
    r, n = 500, 120  # a stitched ring, like the one in the logo
    for i in range(0, n, 2):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 0.6) / n
        d.line([(S / 2 + r * math.cos(a0), S / 2 + r * math.sin(a0)),
                (S / 2 + r * math.cos(a1), S / 2 + r * math.sin(a1))], fill=TAN, width=3)
    badge(im, (S / 2, 360), 470)
    d = ImageDraw.Draw(im)
    m = cfg["marka_karti"]
    hf = font("800ExtraBold", 50)
    y = 640
    for line in m["satirlar"]:
        d.text((S / 2 - hf.getlength(line) / 2, y), line, font=hf, fill=TEAL)
        y += 62
    button(im, (S / 2 - 210, y + 34, S / 2 + 210, y + 108), cfg["buton"], TEAL, CREAM)
    sf = font("500Medium", 24)
    d = ImageDraw.Draw(im)
    d.text((S / 2 - sf.getlength(m["alt"]) / 2, y + 132), m["alt"], font=sf, fill=BRONZE)
    return im.convert("RGB")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "ayarlar.json")
    cfg = json.load(open(path, encoding="utf-8"))
    out = repo(cfg["cikti"])
    for sub in ("akis", "hikaye", "kart"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    made = []
    for i, p in enumerate(cfg["urunler"], 1):
        for sub, fn, suffix in (("akis", feed, "4x5"), ("hikaye", story, "9x16"), ("kart", carousel_card, "1x1")):
            name = os.path.join(out, sub, f"{p['kod']}-{suffix}.jpg")
            fn(cfg, p).save(name, quality=92, subsampling=0)
            made.append(name)
    name = os.path.join(out, "kart", f"{len(cfg['urunler']) + 1:02d}-marka-karti-1x1.jpg")
    brand_card(cfg).save(name, quality=92, subsampling=0)
    made.append(name)
    for m in made:
        print("kaydedildi:", os.path.relpath(m, REPO))


if __name__ == "__main__":
    main()
