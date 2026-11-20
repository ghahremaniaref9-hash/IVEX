"""IVEX Medya - etkileşim odaklı 6 Instagram hikâyesi (1080x1920).

Kullanım:  python3 hikayeler.py [ayar.json]
Metinler ve günler ayarlar/hikayeler.json'da. Her hikâye bir Instagram etiketi için boş alan bırakır
(anket, geri sayım, test, A/B anketi, emoji kaydırıcı, soru kutusu); etiket paylaşırken uygulamada eklenir.
Ayrıca etiketlerin nereye konacağını gösteren bir yerleşim rehberi üretir (paylaşmak için değil).
Instagram'ın üst 250 ve alt 340 piksellik alanına yazı konmaz.
"""
import io
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from marka import INK, LIME, SOFT, WHITE, background, drop_shadow, font, logo, pill, repo, rounded  # noqa: E402
from vitrin import FF, Reel, cover  # noqa: E402

W, H = 1080, 1920
SAFE_TOP, SAFE_BOTTOM = 250, H - 340
COLORS = {"beyaz": WHITE, "lime": LIME}


def clip_frame(path, at):
    png = subprocess.run([FF, "-loglevel", "error", "-ss", str(at), "-i", repo(path), "-frames:v", "1",
                          "-f", "image2pipe", "-c:v", "png", "-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGB")


def shade(img, top=(0, 640, 0.62), bottom=(900, H, 0.9)):
    """Darken the top and bottom of a photo so text stays readable."""
    y = np.arange(H, dtype=np.float32)
    a = np.zeros(H, np.float32)
    t0, t1, ta = top
    a = np.maximum(a, ta * np.clip((t1 - y) / (t1 - t0), 0, 1) ** 1.3)
    b0, b1, ba = bottom
    a = np.maximum(a, ba * np.clip((y - b0) / (b1 - b0), 0, 1) ** 0.9)
    arr = np.asarray(img.convert("RGB"), np.float32) * (1 - a[:, None, None])
    return Image.fromarray(arr.astype(np.uint8)).convert("RGBA")


def text_lines(canvas, lines, y, size, weight="Black", shadow=False, gap=1.14):
    """Centred lines of (text, colour); returns the y below the block."""
    f = font(weight, size)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    step = round(size * gap)
    for i, (text, colour) in enumerate(lines):
        x = (W - d.textlength(text, font=f)) / 2
        d.text((x, y + i * step), text, font=f, fill=COLORS.get(colour, colour))
    if shadow:
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sh.putalpha(layer.getchannel("A").point(lambda v: v * 170 // 255))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (0, 6))
    canvas.alpha_composite(layer)
    return y + len(lines) * step


def head(canvas, label=None, logo_h=46):
    lg = logo(logo_h)
    canvas.alpha_composite(lg, ((W - lg.width) // 2, 286))
    if label:
        pill(ImageDraw.Draw(canvas), W / 2, 372, label, font("ExtraBold", 28), LIME, INK, pad_x=28, h=64, tracking=3,
             anchor="m")


def small(canvas, lines, y, size=36, colour=SOFT, weight="SemiBold", shadow=False):
    return text_lines(canvas, [(t, colour) for t in lines], y, size, weight, shadow, gap=1.35)


def story_photo(s):
    img = shade(cover(clip_frame(s["klip"], s["an"]), (W, H)))
    head(img, s.get("etiket"))
    y = text_lines(img, s["baslik"], s["baslik_y"], s["boyut"], shadow=True)
    if s.get("alt"):
        small(img, s["alt"], y + 22, 38, WHITE, shadow=True)
    return img


def big_mark(img, char, cx, cy, size, alpha):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font("Black", size)
    d.text((cx, cy), char, font=f, fill=LIME + (alpha,), anchor="mm")
    img.alpha_composite(layer)


def story_quiz(s):
    img = background((W, H), seed=21, glow=(0.3, 0.32)).convert("RGBA")
    big_mark(img, "?", 860, 1180, 1100, 16)
    head(img, s["etiket"])
    text_lines(img, s["baslik"], s["baslik_y"], s["boyut"])
    small(img, s["alt"], s["alt_y"], 36, LIME, "Bold")
    return img


def story_pair(s):
    img = background((W, H), seed=33, glow=(0.5, 0.4)).convert("RGBA")
    head(img, None, 40)
    y = text_lines(img, s["baslik"], s["baslik_y"], s["boyut"])
    y = small(img, s["alt"], y + 8, 32)
    pw, ph = 452, 800
    top = round(y + 26)
    for k, side in enumerate(("a", "b")):
        p = s[side]
        panel = cover(clip_frame(p["klip"], p["an"]), (pw, ph)).convert("RGBA")
        rows = p["yazi"].split("|")
        f = font("Bold", 31)
        d = ImageDraw.Draw(panel)
        tw = max(d.textlength(r, font=f) for r in rows)
        lh = 40
        if side == "a":   # the plain ad: a white sticker-like caption box
            bx, by = (pw - tw) / 2 - 22, ph - 80 - lh * len(rows) - 24
            d.rounded_rectangle((bx, by, bx + tw + 44, by + lh * len(rows) + 24), radius=16, fill=(255, 255, 255, 238))
            for i, r in enumerate(rows):
                d.text((pw / 2, by + 12 + i * lh + lh / 2), r, font=f, fill=INK, anchor="mm")
        else:             # the story ad: subtitle text over a dark fade
            fade = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            ys = np.clip((np.arange(ph) - ph * 0.55) / (ph * 0.45), 0, 1) * 190
            fade.putalpha(Image.fromarray(np.repeat(ys[:, None], pw, 1).astype(np.uint8)))
            panel.alpha_composite(fade)
            d = ImageDraw.Draw(panel)
            for i, r in enumerate(rows):
                d.text((pw / 2, ph - 92 - lh * (len(rows) - 1) + i * lh), r, font=f, fill=WHITE, anchor="mm")
        card = rounded(panel, 36)
        x = 52 + k * (pw + 24)
        drop_shadow(img, card, (x, top), blur=24, offset=(0, 14), opacity=140)
        d = ImageDraw.Draw(img)
        r = 42
        cx, cy = x + 30 + r, top + 30 + r
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE if side == "a" else LIME)
        d.text((cx, cy + 2), side.upper(), font=font("Black", 48), fill=INK, anchor="mm")
    s["alan"] = [top + ph + 22, max(top + ph + 22 + 150, s["alan"][1])]
    return img


def story_method(s):
    img = background((W, H), seed=8, glow=(0.75, 0.22)).convert("RGBA")
    head(img, s["etiket"])
    y = text_lines(img, s["baslik"], s["baslik_y"], s["boyut"])
    y += 50
    for k, (title, sub) in enumerate(s["adimlar"]):
        card = Reel.step_card(k + 1, title, sub)
        card = card.resize((round(card.width * 0.94), round(card.height * 0.94)), Image.LANCZOS)
        img.alpha_composite(card, ((W - card.width) // 2, round(y)))
        y += card.height + 26
    return img


def story_questions(s):
    img = background((W, H), seed=5, glow=(0.5, 0.18)).convert("RGBA")
    lg = logo(96)
    img.alpha_composite(lg, ((W - lg.width) // 2, 340))
    y = text_lines(img, s["baslik"], s["baslik_y"], s["boyut"])
    small(img, s["alt"], y + 20, 36)
    small(img, [s["dipnot"]], s["alan"][1] + 60, 30, (196, 214, 198), "Medium")
    return img


BUILD = {"foto": story_photo, "test": story_quiz, "ikili": story_pair, "yontem": story_method, "soru": story_questions}


def guide(images, stories, path):
    """Contact sheet with dashed boxes where each sticker goes; for the person posting, not for Instagram."""
    tw, th, gap = 360, 640, 28
    sheet = Image.new("RGB", (3 * tw + 4 * gap, 2 * (th + 140) + gap), (244, 246, 242))
    d = ImageDraw.Draw(sheet)
    for k, (im, s) in enumerate(zip(images, stories)):
        x, y = gap + (k % 3) * (tw + gap), gap + (k // 3) * (th + 140)
        thumb = im.convert("RGB").resize((tw, th), Image.LANCZOS)
        td = ImageDraw.Draw(thumb, "RGBA")
        y0, y1 = (v * th / H for v in s["alan"])
        td.rectangle((28, y0, tw - 28, y1), fill=(218, 255, 46, 60))
        for xx in range(28, tw - 28, 14):
            td.line((xx, y0, min(xx + 7, tw - 28), y0), fill=LIME, width=3)
            td.line((xx, y1, min(xx + 7, tw - 28), y1), fill=LIME, width=3)
        for yy in range(int(y0), int(y1), 14):
            td.line((28, yy, 28, min(yy + 7, y1)), fill=LIME, width=3)
            td.line((tw - 28, yy, tw - 28, min(yy + 7, y1)), fill=LIME, width=3)
        lab = s["alan_adi"] + " BURAYA"
        f = font("ExtraBold", 18)
        lw = td.textlength(lab, font=f)
        td.rounded_rectangle(((tw - lw) / 2 - 12, (y0 + y1) / 2 - 18, (tw + lw) / 2 + 12, (y0 + y1) / 2 + 18),
                             radius=18, fill=INK + (235,))
        td.text((tw / 2, (y0 + y1) / 2), lab, font=f, fill=LIME, anchor="mm")
        sheet.paste(thumb, (x, y))
        d.text((x, y + th + 14), f"{k + 1}. {s['gun']}", font=font("Bold", 21), fill=INK)
        words, line, rows = s["sticker"].split(), "", []
        for wd in words:
            if d.textlength(line + " " + wd, font=font("Medium", 17)) > tw and line:
                rows.append(line)
                line = wd
            else:
                line = (line + " " + wd).strip()
        rows.append(line)
        for i, r in enumerate(rows[:3]):
            d.text((x, y + th + 46 + i * 22), r, font=font("Medium", 17), fill=(60, 70, 60))
    sheet.save(path, quality=92)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else repo("ivex-icerik", "ayarlar", "hikayeler.json")
    cfg = json.load(open(path, encoding="utf-8"))
    out_dir = repo(cfg["klasor"])
    os.makedirs(out_dir, exist_ok=True)
    images = []
    for s in cfg["hikayeler"]:
        im = BUILD[s["tur"]](s)
        out = os.path.join(out_dir, f"ivex-hikaye-{s['ad']}.jpg")
        im.convert("RGB").save(out, quality=93)
        images.append(im)
        print("kaydedildi:", os.path.relpath(out, repo()))
    g = os.path.join(out_dir, "ivex-hikaye-etiket-rehberi.jpg")
    guide(images, cfg["hikayeler"], g)
    print("kaydedildi:", os.path.relpath(g, repo()))


if __name__ == "__main__":
    main()
