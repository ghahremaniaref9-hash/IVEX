"""Mutfella - satış odaklı ara paket: 4 gönderi, 8 hikâye, 2 Reels (yeni çekim gelene kadar).

Kullanım:  python3 satis_paketi.py [../satis-paketi/ayarlar.json] [gonderi|hikaye|video ...]
Çıktı: satis-paketi/gonderiler (1080x1440), satis-paketi/hikayeler (1080x1920), satis-paketi/videolar (1080x1920 MP4 + kapak).
Görsel dil feed.py ile aynı: kırmızı etiket, kalın beyaz başlık ve kırmızı nokta, altta logo bandı ve web adresi.
Videolar sessizdir; müzik Instagram'da, o haftanın popüler seslerinden eklenir.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feed  # noqa: E402
from feed import (LOGO, MARGIN, RED, SH, SITE, W, WHITE, crop_to, font, footer, grade, headline,  # noqa: E402
                  headline_size, pill, repo, shade, tracked)

FPS = 30
FF = "ffmpeg"


# ------------------------------------------------------------------ posts and stories (feed.py layouts)

def posts(cfg):
    out = repo(os.path.join(cfg["cikti"], "gonderiler"))
    os.makedirs(out, exist_ok=True)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    items = cfg["gonderiler"]
    size = min(headline_size(probe, i["baslik"]) for i in items)
    for it in items:
        p = os.path.join(out, it["ad"] + ".jpg")
        feed.post(it, size).save(p, quality=93, subsampling=0)
        print("kaydedildi:", os.path.relpath(p, repo("")))


def stories(cfg):
    out = repo(os.path.join(cfg["cikti"], "hikayeler"))
    os.makedirs(out, exist_ok=True)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    items = cfg["hikayeler"]
    size = min(headline_size(probe, i["baslik"], top=112) for i in items)
    for it in items:
        p = os.path.join(out, it["ad"] + ".jpg")
        feed.story(it, size).save(p, quality=93, subsampling=0)
        print("kaydedildi:", os.path.relpath(p, repo("")))


# ------------------------------------------------------------------ reels

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def shadowed(ink):
    """Type layer with its soft shadow baked underneath (same look as feed.with_shadow)."""
    sh = Image.new("RGBA", ink.size, (0, 0, 0, 0))
    sh.putalpha(ink.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: round(v * 0.5)))
    return Image.alpha_composite(sh, ink)


def faded(layer, a):
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: round(v * a)))
    return out


def plate(path, center):
    """Shot plate 10 % larger than the frame, so it can slowly push in."""
    img = Image.open(repo(path)).convert("RGB")
    big = grade(crop_to(img, (round(W * 1.1), round(SH * 1.1)), tuple(center)))
    return shade(big, top=(0.22, 0.55), bottom=(0.5, 0.88), curve=1.2)


def push(img, p, drift):
    """Ken Burns: from the full plate to the centre 1/1.1 of it; a small sideways drift."""
    bw, bh = img.size
    p = min(max(p, 0.0), 1.0)
    z = 1 + 0.1 * p
    cw, ch = bw / z, bh / z
    cx = bw / 2 + drift * (bw - cw) / 2 * (p - 0.5)
    box = (cx - cw / 2, bh / 2 - ch / 2, cx + cw / 2, bh / 2 + ch / 2)
    return img.resize((W, SH), Image.BILINEAR, box=box)


def top_pill(text):
    ink = Image.new("RGBA", (W, SH), (0, 0, 0, 0))
    pill(ImageDraw.Draw(ink), MARGIN, 250, text)
    return shadowed(ink)


def brand_band():
    ink = Image.new("RGBA", (W, SH), (0, 0, 0, 0))
    footer(ink, SH - 340 - 130)
    return shadowed(ink)


def caption(lines, size, y_bottom):
    """Headline (red full stop) sitting on `y_bottom`, with the short red rule above it."""
    ink = Image.new("RGBA", (W, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    fnt = font("ExtraBold", size)
    step = round(size * 1.04)
    asc = fnt.getbbox("H")[1]
    y = y_bottom - (step * (len(lines) - 1) + fnt.getbbox("Hg")[3])
    d.rectangle((MARGIN, y + asc - 44, MARGIN + 96, y + asc - 34), fill=RED)
    headline(d, MARGIN, y, lines, size)
    return shadowed(ink)


def list_item(text, y):
    ink = Image.new("RGBA", (W, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    f = font("Bold", 46)
    r = 9
    cy = y + f.getbbox("a")[1] + (f.getbbox("a")[3] - f.getbbox("a")[1]) / 2
    d.ellipse((MARGIN + 4, cy - r, MARGIN + 4 + 2 * r, cy + r), fill=RED)
    d.text((MARGIN + 44, y), text, font=f, fill=WHITE)
    return shadowed(ink)


def end_card(last_plate, cfg):
    bg = last_plate.resize((W, SH), Image.BILINEAR).filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new("RGB", (W, SH), (8, 8, 10)), 0.72)
    ink = Image.new("RGBA", (W, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    dlogo = 230
    logo = Image.open(LOGO).convert("RGBA").resize((dlogo, dlogo), Image.LANCZOS)
    ink.alpha_composite(logo, ((W - dlogo) // 2, 430))
    brand = font("Bold", 30)
    bw = sum(d.textlength(c, font=brand) for c in "MUTFELLA CATERING") + 8 * 16
    tracked(d, ((W - bw) / 2, 700), "MUTFELLA CATERING", brand, WHITE, 8)
    size = 92
    fnt = font("ExtraBold", size)
    y = 820
    for i, line in enumerate(cfg["baslik"]):
        lw = d.textlength(line, font=fnt)
        x = (W - lw) / 2
        if i == len(cfg["baslik"]) - 1 and line[-1:] in ".?!":
            d.text((x, y), line[:-1], font=fnt, fill=WHITE)
            d.text((x + d.textlength(line[:-1], font=fnt), y), line[-1], font=fnt, fill=RED)
        else:
            d.text((x, y), line, font=fnt, fill=WHITE)
        y += round(size * 1.06)
    y += 40
    bf = font("Bold", 34)
    tw = d.textlength(cfg["alt"], font=bf)
    d.rounded_rectangle(((W - tw) / 2 - 40, y, (W + tw) / 2 + 40, y + 86), radius=43, fill=RED)
    d.text(((W - tw) / 2, y + 43 - (bf.getbbox("Mg")[1] + bf.getbbox("Mg")[3]) / 2), cfg["alt"], font=bf, fill=WHITE)
    sf = font("Bold", 34)
    d.text(((W - d.textlength(SITE, font=sf)) / 2, y + 140), SITE, font=sf, fill=WHITE)
    tf = font("Medium", 28)
    tag = "Kurumsal Yemek Hizmeti"
    d.text(((W - d.textlength(tag, font=tf)) / 2, y + 196), tag, font=tf, fill=(255, 255, 255, 210))
    return bg.convert("RGBA"), shadowed(ink)


def reel(v, out_dir):
    scenes = v["sahneler"]
    first = v.get("ilk_sahne", v["sahne_suresi"])
    starts = [0.0]
    for k in range(1, len(scenes)):
        starts.append(first + (k - 1) * v["sahne_suresi"])
    end_at = first + (len(scenes) - 1) * v["sahne_suresi"]
    total = end_at + v["son"]["sure"]
    plates = [plate(p, c) for p, c, _ in scenes]
    pill_l, band = top_pill(v["ust"]), brand_band()
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    if v.get("liste"):
        hook = caption(v["kanca"], headline_size(probe, v["kanca"], top=96), SH - 340 - 130 - 70)
        items = [(starts[k], list_item(t, 1000 + (k - 1) * 82)) for k, (_, _, t) in enumerate(scenes) if t]
        label_ink = Image.new("RGBA", (W, SH), (0, 0, 0, 0))
        lf = font("Bold", 30)
        tracked(ImageDraw.Draw(label_ink), (MARGIN, 930), "YIL SONU MENÜNÜZDE", lf, (255, 255, 255, 230), 5)
        label = shadowed(label_ink)
        # dark band behind the list so it reads over bright shots (soup, steel)
        band_a = Image.new("L", (1, SH), 0)
        for yy in range(SH):
            band_a.putpixel((0, yy), round(185 * min(1, max(0, (yy - 820) / 140))))
        list_bg = Image.new("RGBA", (W, SH), (0, 0, 0, 255))
        list_bg.putalpha(band_a.resize((W, SH)))
        caps = []
    else:
        size = min(headline_size(probe, t.split("|")) for _, _, t in scenes)
        caps = [caption(t.split("|"), size, SH - 340 - 130 - 70) for _, _, t in scenes]
    end_bg, end_ink = end_card(plates[-1], v["son"])

    def shot_frame(k, t):
        dur = (starts[k + 1] if k + 1 < len(scenes) else end_at) - starts[k]
        return push(plates[k], (t - starts[k]) / dur, 1 if k % 2 else -1).convert("RGBA")

    def frame(t):
        if t >= end_at:
            a = ease((t - end_at) / 0.4)
            f = Image.blend(shot_frame(len(scenes) - 1, end_at - 0.001), end_bg, a) if a < 1 else end_bg.copy()
            f.alpha_composite(faded(end_ink, a), (0, round(30 * (1 - a))))
            return f.convert("RGB")
        k = max(i for i, s in enumerate(starts) if s <= t)
        f = shot_frame(k, t)
        if k > 0 and t - starts[k] < 0.18:  # short dissolve between shots
            f = Image.blend(shot_frame(k - 1, starts[k] - 0.001), f, (t - starts[k]) / 0.18)
        f.alpha_composite(faded(pill_l, ease(t / 0.3)))
        if v.get("liste"):
            if t < starts[1]:
                a = ease((t - 0.15) / 0.35) * (1 - ease((t - (starts[1] - 0.3)) / 0.3))
                f.alpha_composite(faded(hook, a), (0, round(40 * (1 - ease((t - 0.15) / 0.35)))))
            else:
                f.alpha_composite(faded(list_bg, ease((t - starts[1]) / 0.3)))
                f.alpha_composite(faded(label, ease((t - starts[1]) / 0.3)))
            for at, lay in items:
                if t >= at:
                    a = ease((t - at - 0.1) / 0.3)
                    f.alpha_composite(faded(lay, a), (round(-40 * (1 - a)), 0))
        else:
            a = ease((t - starts[k] - 0.12) / 0.3)
            f.alpha_composite(faded(caps[k], a), (0, round(36 * (1 - a))))
        f.alpha_composite(band)
        return f.convert("RGB")

    path = os.path.join(out_dir, v["ad"] + ".mp4")
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{SH}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
    n = round(total * FPS)
    for i in range(n):
        enc.stdin.write(frame(i / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    frame(v["kapak_an"]).save(os.path.join(out_dir, v["ad"] + "-kapak.jpg"), quality=93)
    print("kaydedildi:", os.path.relpath(path, repo("")), f"({total:.1f} sn) ve kapağı")


def videos(cfg):
    out = repo(os.path.join(cfg["cikti"], "videolar"))
    os.makedirs(out, exist_ok=True)
    for v in cfg["videolar"]:
        reel(v, out)


def main():
    args = sys.argv[1:]
    path = next((a for a in args if a.endswith(".json")),
                repo("mutfella-icerik/satis-paketi/ayarlar.json"))
    cfg = json.load(open(path, encoding="utf-8"))
    parts = [a for a in args if a in ("gonderi", "hikaye", "video")] or ["gonderi", "hikaye", "video"]
    if "gonderi" in parts:
        posts(cfg)
    if "hikaye" in parts:
        stories(cfg)
    if "video" in parts:
        videos(cfg)


if __name__ == "__main__":
    main()
