"""Mutfella - feed gönderileri ve profil ızgarası önizlemesi.

Kullanım:  python3 feed.py ../feed-9-gun/ayarlar.json
Gönderiler 1080x1440 çıkar: Instagram profil ızgarasının 3:4 oranıyla birebir. Yazılar, uygulama 4:5'e
kırparsa da kesilmeyecek alanda (üstten ve alttan 45 px içeride) durur.
Hikâyeler 1080x1920 çıkar; yazılar üstteki profil çubuğunun altında, alttaki mesaj çubuğunun üstünde kalır,
ortadaki boşluk uygulamada eklenecek anket / soru / kaydırıcı çıkartması içindir.
Tasarım önceki Mutfella gönderilerinin çizgisini izler: kırmızı etiket, kalın beyaz başlık, kırmızı nokta;
altta yuvarlak Mutfella logosu, "MUTFELLA CATERING · Kurumsal Yemek Hizmeti" ve web adresi.
"video" olan günler ızgarada boş, numaralı kutu olarak kalır; videolar gelince yerlerine girer.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

W, H = 1080, 1440
SH = 1920  # story height
MARGIN = 64
RED = (200, 16, 46)
WHITE = (255, 255, 255)
HEAD_MAX, HEAD_MIN = 104, 72
LOGO = os.path.join(ROOT, "mutfella-icerik", "marka", "mutfella-logo.png")
SITE = "mutfella.com.tr"


def repo(p):
    return os.path.join(ROOT, p)


def font(weight, size):
    num = {"Medium": 500, "Bold": 700, "ExtraBold": 800}[weight]
    return ImageFont.truetype(os.path.join(HERE, "fonts", f"Montserrat_{num}{weight}.ttf"), size)


def crop_to(img, size, center=(0.5, 0.5)):
    """Largest window with the target aspect ratio around `center`, resized to `size`."""
    tw, th = size
    sw, sh = img.size
    ratio = tw / th
    cw, ch = (sw, sw / ratio) if sw / sh < ratio else (sh * ratio, sh)
    cx = min(max(center[0] * sw, cw / 2), sw - cw / 2)
    cy = min(max(center[1] * sh, ch / 2), sh - ch / 2)
    box = (round(cx - cw / 2), round(cy - ch / 2), round(cx + cw / 2), round(cy + ch / 2))
    return img.crop(box).resize(size, Image.LANCZOS)


def grade(img, contrast=0.10, warmth=1.0, vignette=0.24):
    """Light touch: the footage is already graded. A soft S-curve, warm highlights and an edge falloff."""
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255
    a = a + contrast * (a - 0.5) * (1 - np.abs(2 * a - 1))
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    a[..., 0] += 0.018 * lum * warmth
    a[..., 2] -= 0.018 * lum * warmth
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) / np.sqrt(2)
    a *= (1 - vignette * np.clip(r - 0.3, 0, 1) ** 1.6 / 0.7 ** 1.6)[..., None]
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))


def shade(img, top=None, bottom=None, curve=1.4):
    """Darken towards the top and/or bottom edge so white type stays legible. (start, strength) per edge."""
    a = np.asarray(img).astype(np.float32)
    y = np.linspace(0, 1, img.height, dtype=np.float32)
    k = np.zeros(img.height, np.float32)
    if bottom:
        start, strength = bottom
        t = np.clip((y - start) / (1 - start), 0, 1)
        k = np.maximum(k, strength * t ** curve)
    if top:
        end, strength = top
        t = np.clip((end - y) / end, 0, 1)
        k = np.maximum(k, strength * t ** curve)
    a *= (1 - k)[:, None, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def tracked(draw, xy, text, fnt, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x - tracking


def tracked_width(draw, text, fnt, tracking):
    return sum(draw.textlength(ch, font=fnt) for ch in text) + tracking * (len(text) - 1)


def pill(draw, x, y, text):
    fnt = font("Bold", 27)
    tw = tracked_width(draw, text, fnt, 3)
    h = 56
    draw.rounded_rectangle((x, y, x + tw + 56, y + h), radius=h // 2, fill=RED)
    top = fnt.getbbox("ÜMA")[1]
    cap = fnt.getbbox("MA")[3] - fnt.getbbox("MA")[1]
    tracked(draw, (x + 28, y + (h - cap) / 2 - fnt.getbbox("MA")[1] + 1), text, fnt, WHITE, 3)
    return y + h, top


def headline_size(draw, lines, top=HEAD_MAX):
    size = top
    while size > HEAD_MIN and max(draw.textlength(l, font=font("ExtraBold", size)) for l in lines) > W - 2 * MARGIN - 20:
        size -= 2
    return size


def headline(draw, x, y, lines, size):
    """Lines top-down from `y`; a trailing . ? ! on the last line is drawn in the brand red."""
    fnt = font("ExtraBold", size)
    step = round(size * 1.04)
    for i, line in enumerate(lines):
        last = i == len(lines) - 1
        if last and line[-1:] in ".?!":
            draw.text((x, y), line[:-1], font=fnt, fill=WHITE)
            draw.text((x + draw.textlength(line[:-1], font=fnt), y), line[-1], font=fnt, fill=RED)
        else:
            draw.text((x, y), line, font=fnt, fill=WHITE)
        y += step
    return y - step + fnt.getbbox("Hg")[3]


def subline(draw, x, y, items):
    fnt = font("Medium", 34)
    for i, item in enumerate(items):
        if i:
            r = 6
            cy = y + fnt.getbbox("a")[1] + (fnt.getbbox("a")[3] - fnt.getbbox("a")[1]) / 2
            draw.ellipse((x + 16, cy - r, x + 16 + 2 * r, cy + r), fill=RED)
            x += 16 + 2 * r + 16
        draw.text((x, y), item, font=fnt, fill=WHITE)
        x += draw.textlength(item, font=fnt)


def wrap_lines(draw, text, fnt, width):
    """Word-wrap `text` to `width`; a newline in the text forces a break."""
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=fnt) > width and line:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines


def wrapped(draw, x, y, text, fnt, width, fill=WHITE, leading=1.3):
    """Draw `text` word-wrapped to `width`; returns the y below the last line."""
    step = round(fnt.size * leading)
    for line in wrap_lines(draw, text, fnt, width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += step
    return y


def footer(ink, y_line=H - 45 - 140):
    """Brand band under a hairline: round logo, name and service line on the left, web address on the right."""
    draw = ImageDraw.Draw(ink)
    draw.line((MARGIN, y_line, W - MARGIN, y_line), fill=(255, 255, 255, 90), width=2)
    d = 92
    logo = Image.open(LOGO).convert("RGBA").resize((d, d), Image.LANCZOS)
    top = y_line + 24
    ink.alpha_composite(logo, (MARGIN, top))
    cy = top + d / 2
    brand, tag, site = font("Bold", 26), font("Medium", 23), font("Bold", 30)
    x = MARGIN + d + 24
    tracked(draw, (x, cy - 31 - brand.getbbox("M")[1]), "MUTFELLA CATERING", brand, WHITE, 7)
    draw.text((x, cy + 7 - tag.getbbox("K")[1]), "Kurumsal Yemek Hizmeti", font=tag, fill=(255, 255, 255, 225))
    box = site.getbbox(SITE)
    draw.text((W - MARGIN - draw.textlength(SITE, font=site), cy - (box[1] + box[3]) / 2), SITE, font=site, fill=WHITE)
    return y_line


def post(item, size):
    img = Image.open(repo(item["kaynak"])).convert("RGB")
    img = grade(crop_to(img, (W, H), tuple(item.get("merkez", (0.5, 0.5)))))
    dark = item.get("koyuluk", 1.0)
    if item["duzen"] == "alt":
        img = shade(img, top=(0.16, 0.30), bottom=(0.40, min(0.86 * dark, 0.95)))
    else:
        img = shade(img, top=(0.52, min(0.70 * dark, 0.95)), bottom=(0.80, 0.62))
    # type goes on its own layer so it can cast a soft shadow onto the photo
    ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ink)
    pill(draw, MARGIN, 45 + 40, item["seri"])
    lines = item["baslik"]
    fnt = font("ExtraBold", size)
    step = round(size * 1.04)
    asc = fnt.getbbox("H")[1]
    y_line = footer(ink)
    if item["duzen"] == "alt":
        # "alt" is either a list of short items (one line, red dots between) or a sentence that may wrap
        sub_font = font("Medium", 34)
        sentence = isinstance(item["alt"], str)
        extra = len(wrap_lines(draw, item["alt"], sub_font, W - 2 * MARGIN)) - 1 if sentence else 0
        sub_y = y_line - 46 - 40 - extra * round(34 * 1.3)
        head_bottom = sub_y - 34
        head_y = head_bottom - (step * (len(lines) - 1) + fnt.getbbox("Hg")[3])
        draw.rectangle((MARGIN, head_y + asc - 44, MARGIN + 96, head_y + asc - 34), fill=RED)
        headline(draw, MARGIN, head_y, lines, size)
        if sentence:
            wrapped(draw, MARGIN, sub_y, item["alt"], sub_font, W - 2 * MARGIN)
        else:
            subline(draw, MARGIN, sub_y, item["alt"])
    else:
        head_y = 45 + 40 + 56 + 92 - asc
        draw.rectangle((MARGIN, head_y + asc - 44, MARGIN + 96, head_y + asc - 34), fill=RED)
        bottom = headline(draw, MARGIN, head_y, lines, size)
        subline(draw, MARGIN, bottom + 30, item["alt"])
    return with_shadow(img, ink)


def with_shadow(img, ink):
    """Composite the type layer over the photo with a soft drop shadow under it."""
    shadow = Image.new("RGBA", ink.size, (0, 0, 0, 0))
    shadow.putalpha(ink.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: round(v * 0.5)))
    return Image.alpha_composite(Image.alpha_composite(img.convert("RGBA"), shadow), ink).convert("RGB")


def story(item, size):
    """1080x1920 story: label and headline under the profile bar, brand line above the reply bar."""
    img = Image.open(repo(item["kaynak"])).convert("RGB")
    img = grade(crop_to(img, (W, SH), tuple(item.get("merkez", (0.5, 0.5)))))
    dark = item.get("koyuluk", 1.0)
    img = shade(img, top=(0.48, min(0.78 * dark, 0.95)), bottom=(0.60, 0.85), curve=1.0)
    ink = Image.new("RGBA", (W, SH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ink)
    pill(draw, MARGIN, 250, item["seri"])
    fnt = font("ExtraBold", size)
    head_y = 250 + 56 + 92 - fnt.getbbox("H")[1]
    draw.rectangle((MARGIN, 250 + 56 + 48, MARGIN + 96, 250 + 56 + 58), fill=RED)
    bottom = headline(draw, MARGIN, head_y, item["baslik"], size)
    wrapped(draw, MARGIN, bottom + 30, item["alt"], font("Medium", 40), W - 2 * MARGIN)
    footer(ink, SH - 340 - 130)
    return with_shadow(img, ink)


def placeholder(item, tw, th, numbered):
    """Empty grid tile where a video goes."""
    tile = Image.new("RGB", (tw, th), (236, 236, 234))
    d = ImageDraw.Draw(tile)
    d.rectangle((10, 10, tw - 11, th - 11), outline=(196, 196, 192), width=2)
    cx, cy = tw // 2, th // 2 - 40
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), outline=(150, 150, 146), width=3)
    d.polygon([(cx - 10, cy - 16), (cx - 10, cy + 16), (cx + 17, cy)], fill=(150, 150, 146))
    for text, fnt, col, dy in ((f"VİDEO {item['video']}", font("Bold", 26), (90, 90, 88), 62),
                               (item["seri"], font("Medium", 18), (120, 120, 116), 100),
                               (item["tarih"], font("Medium", 18), (120, 120, 116), 128)):
        d.text((cx - d.textlength(text, font=fnt) / 2, cy + dy), text, font=fnt, fill=col)
    return tile


def grid(items, out, numbered):
    tw, th, gap = 360, 480, 4
    order = sorted(items, key=lambda i: -i["gun"])  # newest first: top-left
    canvas = Image.new("RGB", (tw * 3 + gap * 2, th * 3 + gap * 2), (255, 255, 255))
    for n, item in enumerate(order):
        if item.get("video"):
            tile = placeholder(item, tw, th, numbered)
        else:
            tile = Image.open(item["_png"]).convert("RGB").resize((tw, th), Image.LANCZOS)
        if numbered:
            d = ImageDraw.Draw(tile)
            label = f"{item['gun']}. GÜN"
            fnt = font("Bold", 20)
            w = d.textlength(label, font=fnt)
            d.rounded_rectangle((tw - w - 34, 14, tw - 12, 48), radius=17, fill=(20, 20, 20))
            d.text((tw - w - 23, 21), label, font=fnt, fill=WHITE)
        canvas.paste(tile, ((n % 3) * (tw + gap), (n // 3) * (th + gap)))
    canvas.save(repo(out), quality=92)
    print("kaydedildi:", out)


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    items = cfg["gunler"]
    photos = [i for i in items if not i.get("video")]
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    size = min(headline_size(probe, i["baslik"]) for i in photos)  # one headline size across the grid
    os.makedirs(repo(cfg["cikti"]), exist_ok=True)
    for item in photos:
        path = os.path.join(repo(cfg["cikti"]), item["ad"] + ".jpg")
        post(item, size).save(path, quality=93, subsampling=0)
        item["_png"] = path
        print("kaydedildi:", os.path.relpath(path, ROOT))
    grid(items, cfg["izgara"], numbered=False)
    grid(items, cfg["izgara_sirali"], numbered=True)
    stories = cfg.get("hikayeler", [])
    if stories:
        size = min(headline_size(probe, i["baslik"], top=112) for i in stories)
        os.makedirs(repo(cfg["hikaye_cikti"]), exist_ok=True)
        for item in stories:
            path = os.path.join(repo(cfg["hikaye_cikti"]), item["ad"] + ".jpg")
            story(item, size).save(path, quality=93, subsampling=0)
            print("kaydedildi:", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
