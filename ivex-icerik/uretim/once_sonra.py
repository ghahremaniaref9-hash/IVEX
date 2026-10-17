"""IVEX Medya - "Önce / Sonra" Reels: each client's raw photo wipes into the finished post (1080x1920).

Kullanım:  python3 once_sonra.py ayarlar/gun1-once-sonra.json
Çıktı: MP4 (sessiz; müzik Instagram'da eklenir) ve aynı tasarımda kapak görseli.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageOps

from marka import (INK, LIME, WHITE, background, blend, drop_shadow, end_card, font, pill, repo, rounded,
                   wordmark, write_video)

W, H, FPS = 1080, 1920, 30
CW, CH = 840, 1050
CX, CY = (W - CW) // 2, 480
ZOOM = 0.04
SEG, WIPE_AT, WIPE_LEN = 4.2, 1.4, 0.6
END = 3.2


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def load(spec):
    """Load a photo/post and crop it to 4:5 at a slightly larger size, leaving room for the slow zoom."""
    im = ImageOps.exif_transpose(Image.open(repo(spec["dosya"]))).convert("RGB")
    fx, fy = spec.get("odak", (0.5, 0.5))
    bw, bh = round(CW * (1 + ZOOM)), round(CH * (1 + ZOOM))
    s = max(bw / im.width, bh / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = round((im.width - bw) * fx), round((im.height - bh) * fy)
    return im.crop((x, y, x + bw, y + bh))


def tag(text, lime):
    """ÖNCE / SONRA label that sits on the card's top edge."""
    f = font("ExtraBold", 24)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w = round(sum(probe.textlength(c, font=f) for c in text) + 3 * (len(text) - 1) + 52)
    im = Image.new("RGBA", (w, 50), (0, 0, 0, 0))
    pill(ImageDraw.Draw(im, "RGBA"), 0, 0, text, f, LIME if lime else (14, 30, 18), INK if lime else WHITE,
         pad_x=26, h=50, tracking=3)
    return im


def place_tags(canvas, edge, before_tag, after_tag):
    """Draw the tags clipped to the wipe: SONRA left of the edge, ÖNCE right of it."""
    y = CY - 25
    ax, bx = CX + 30, CX + CW - 30 - before_tag.width
    cut = CX + edge
    if cut > ax:
        canvas.alpha_composite(after_tag.crop((0, 0, min(after_tag.width, cut - ax), 50)), (ax, y))
    if cut < bx + before_tag.width:
        off = max(0, cut - bx)
        canvas.alpha_composite(before_tag.crop((off, 0, before_tag.width, 50)), (bx + off, y))


def view(big, p):
    """Crop for zoom progress p (0..1) and scale to the card size."""
    z = 1 + ZOOM * p
    cw, ch = big.width / z, big.height / z
    x, y = (big.width - cw) / 2, (big.height - ch) / 2
    return big.resize((CW, CH), Image.BILINEAR, box=(x, y, x + cw, y + ch))


def wrap(d, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def headline(text, color):
    im = Image.new("RGBA", (W, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Black", 62)
    for i, line in enumerate(wrap(d, text, f, 900)[:3]):
        tw = d.textlength(line, font=f)
        d.text(((W - tw) / 2, i * 74), line, font=f, fill=color)
    return im


def overlay(canvas, layer, y, alpha):
    if alpha <= 0:
        return
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: round(v * alpha)))
    canvas.alpha_composite(layer, (0, round(y)))


BAR_W, BAR_GAP = 120, 14


def bars(n):
    x0 = (W - (n * BAR_W + (n - 1) * BAR_GAP)) / 2
    return [(x0 + i * (BAR_W + BAR_GAP), CY + CH + 46) for i in range(n)]


def static_base(bg, logo, client, n):
    """Background + logo + client pill + progress track for one segment (no animated parts)."""
    base = bg.copy()
    base.alpha_composite(logo, ((W - logo.width) // 2, 118))

    def draw(d):
        pill(d, W / 2, 192, client, font("Bold", 22), (255, 255, 255, 26), LIME, pad_x=26, tracking=5, h=48,
             anchor="m")
        for x, y in bars(n):
            d.rounded_rectangle((x, y, x + BAR_W, y + 6), radius=3, fill=(255, 255, 255, 60))

    blend(base, draw)
    return base


def progress(d, idx, n, p):
    for i, (x, y) in enumerate(bars(n)):
        fill = 1 if i < idx else (p if i == idx else 0)
        if fill > 0:
            d.rounded_rectangle((x, y, x + max(6, BAR_W * fill), y + 6), radius=3, fill=LIME)


def frames(cfg):
    bg = background((W, H), seed=7, glow=(0.8, 0.12)).convert("RGBA")
    logo = wordmark(38, WHITE, x_color=LIME)
    segs = cfg["bolumler"]
    n = len(segs)
    prepared = []
    for s in segs:
        prepared.append((static_base(bg, logo, s["musteri"], n), load(s["once"]), load(s["sonra"]),
                         headline(s["once_metin"], WHITE), headline(s["sonra_metin"], LIME)))
    end = end_card(bg, [("Sıradaki önce / sonra", WHITE), ("senin işletmen olsun.", LIME)],
                   "YORUMLARA “İÇERİK” YAZ", ["Ücretsiz 3 içerik fikrini", "DM'den gönderelim."])
    before_tag, after_tag = tag("ÖNCE", False), tag("SONRA", True)

    seg_frames = round(SEG * FPS)
    for i, (base, before, after, h1, h2) in enumerate(prepared):
        for k in range(seg_frames):
            t = k / FPS
            p = k / seg_frames
            canvas = base.copy()
            b, a = view(before, p), view(after, p)
            w = ease((t - WIPE_AT) / WIPE_LEN)
            edge = round(CW * w)
            card = b.copy()
            if edge > 0:
                card.paste(a.crop((0, 0, edge, CH)), (0, 0))
            card = rounded(card, 30)
            drop_shadow(canvas, card, (CX, CY), blur=30, offset=(0, 20), opacity=170)
            d = ImageDraw.Draw(canvas)
            if 0 < w < 1:
                d.rectangle((CX + edge - 5, CY, CX + edge + 5, CY + CH), fill=LIME)
            place_tags(canvas, edge, before_tag, after_tag)
            # headline: the "before" line leaves upwards, then the "after" line rises in
            out_ = ease((t - WIPE_AT) / 0.24)
            in_ = ease((t - WIPE_AT - 0.2) / 0.3)
            overlay(canvas, h1, 262 - 36 * out_, 1 - out_)
            overlay(canvas, h2, 262 + 36 * (1 - in_), in_)
            progress(d, i, n, p)
            yield canvas.convert("RGB")
    # end card fades in over the last post
    last = canvas.convert("RGBA")
    for k in range(round(END * FPS)):
        a = ease(k / (0.45 * FPS))
        yield Image.blend(last, end, a).convert("RGB") if a < 1 else end.convert("RGB")


def cover(cfg, path):
    """Reels cover: the first client's photo split half before / half after, with the hook."""
    s = cfg["bolumler"][0]
    bg = background((W, H), seed=7, glow=(0.8, 0.12)).convert("RGBA")
    im = static_base(bg, wordmark(38, WHITE, x_color=LIME), s["musteri"], 0)
    b, a = view(load(s["once"]), 0), view(load(s["sonra"]), 0)
    card = b.copy()
    card.paste(a.crop((0, 0, CW // 2, CH)), (0, 0))
    drop_shadow(im, rounded(card, 30), (CX, CY), blur=30, offset=(0, 20), opacity=170)
    ImageDraw.Draw(im).rectangle((CX + CW // 2 - 5, CY, CX + CW // 2 + 5, CY + CH), fill=LIME)
    place_tags(im, CW // 2, tag("ÖNCE", False), tag("SONRA", True))
    overlay(im, headline(cfg["kapak_metin"], WHITE), 262, 1)
    im.convert("RGB").save(path, quality=93)
    print("kaydedildi:", path)


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    write_video(frames(cfg), repo(cfg["cikti"]), (W, H), FPS)
    cover(cfg, repo(cfg["kapak"]))


if __name__ == "__main__":
    main()
