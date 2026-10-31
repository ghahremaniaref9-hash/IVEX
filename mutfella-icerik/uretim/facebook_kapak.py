"""Mutfella - Facebook sayfası kapak fotoğrafı (1640x924).

Kullanım:  python3 facebook_kapak.py
Facebook kapağı masaüstünde ortadaki yaklaşık 1640x610'luk şeridi, telefonda görselin tamamını gösterir; yazılar
bu yüzden ortadaki güvenli şeritte durur. Solda siyah zemin üstünde kırmızı etiket ve başlık, sağda çekimden üç
fotoğraf eğik paneller halinde. Sol alt köşe boş bırakılır (profil fotoğrafı ve sayfa notu oraya biner).
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from feed import RED, WHITE, crop_to, font, grade, repo, tracked

W, H = 1640, 924
SAFE = (157, 767)  # rows the desktop crop keeps
SLANT = 60
PANELS = [  # photo, focus (x, y) in the photo
    ("mutfella-icerik/feed-9-gun/kaynak/IMG_0562.jpg", (0.5, 0.62)),
    ("mutfella-icerik/feed-9-gun/kaynak/IMG_0575.jpg", (0.6, 0.36)),
    ("mutfella-icerik/feed-9-gun/kaynak/IMG_0547.jpg", (0.5, 0.6)),
]
OUT = "mutfella-icerik/facebook/mutfella-facebook-kapak.jpg"
PREVIEW = "mutfella-icerik/facebook/masaustu-onizleme.jpg"


def main():
    base = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - 360) / W, (yy - H / 2) / H)
    base[:] = np.array((16, 12, 12), np.float32)
    base += (np.clip(1 - r * 1.8, 0, 1) ** 2)[..., None] * np.array((46, 14, 16), np.float32)
    im = Image.fromarray(base.astype(np.uint8), "RGB").convert("RGBA")

    # three slanted photo panels on the right
    x0, x1 = 905, W + SLANT
    gap = 10
    pw = (x1 - x0 - gap * (len(PANELS) - 1)) / len(PANELS)
    edges = []
    for i, (path, focus) in enumerate(PANELS):
        left = x0 + i * (pw + gap)
        right = left + pw
        box_w = round(pw + 2 * SLANT)
        photo = grade(crop_to(Image.open(repo(path)).convert("RGB"), (box_w, H), focus), contrast=0.08, vignette=0.15)
        mask = Image.new("L", (W, H), 0)
        poly = [(left + SLANT, 0), (right + SLANT, 0), (right - SLANT, H), (left - SLANT, H)]
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.paste(photo.convert("RGBA"), (round(left - SLANT), 0))
        layer.putalpha(mask)
        im.alpha_composite(layer)
        edges.append(poly)
    # soften the photos towards the text side, then a red line along the first edge
    fade = Image.new("RGBA", (W, H), (16, 12, 12, 0))
    a = np.clip((1020 - xx - (H / 2 - yy) * SLANT * 2 / H) / 220, 0, 1) * 190
    fade.putalpha(Image.fromarray(a.astype(np.uint8)))
    im.alpha_composite(fade)
    d = ImageDraw.Draw(im)
    p = edges[0]
    d.line([p[0], p[3]], fill=RED, width=8)

    # text block, inside the desktop strip and clear of the bottom-left corner
    ink = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    x, y = 96, 250
    f = font("Bold", 26)
    label = "MUTFELLA CATERING"
    tw = sum(d.textlength(c, font=f) for c in label) + 4 * (len(label) - 1)
    d.rounded_rectangle((x, y, x + tw + 56, y + 56), radius=28, fill=RED)
    tracked(d, (x + 28, y + 13), label, f, WHITE, 4)
    head = font("ExtraBold", 88)
    for i, line in enumerate(("Her gün taze,", "her gün sıcak")):
        d.text((x - 4, y + 86 + i * 100), line, font=head, fill=WHITE)
    dot_x = x - 4 + d.textlength("her gün sıcak", font=head)
    d.text((dot_x, y + 186), ".", font=head, fill=RED)
    d.text((x, y + 316), "Ofislere ve etkinliklere ev tadında yemek", font=font("Medium", 34), fill=(235, 228, 224))
    d.rectangle((x, y + 382, x + 80, y + 388), fill=RED)
    d.text((x, y + 408), "Sipariş ve teklif için mesaj atın  ·  mutfella.com.tr", font=font("Bold", 26),
           fill=(235, 228, 224))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(ink.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: v // 2))
    im.alpha_composite(shadow)
    im.alpha_composite(ink)

    os.makedirs(os.path.dirname(repo(OUT)), exist_ok=True)
    out = im.convert("RGB")
    out.save(repo(OUT), quality=94, subsampling=0)
    print("kaydedildi:", repo(OUT))
    # how it sits on the desktop page: the middle strip, the profile picture just under its bottom-left
    strip = out.crop((0, SAFE[0], W, SAFE[1]))
    pv = Image.new("RGB", (W, strip.height + 300), (242, 243, 245))
    pv.paste(strip, (0, 0))
    lg = Image.open(repo("mutfella-icerik/marka/mutfella-logo.png")).convert("RGBA").resize((236, 236))
    ring = Image.new("RGBA", (252, 252), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, 251, 251), fill=(255, 255, 255, 255))
    pv.paste(ring, (64, strip.height + 30), ring)
    pv.paste(lg, (72, strip.height + 38), lg)
    ImageDraw.Draw(pv).text((352, strip.height + 70), "Kuzenler mutfak", font=font("Bold", 56), fill=(20, 20, 20))
    pv.save(repo(PREVIEW), quality=88)
    print("kaydedildi:", repo(PREVIEW))


if __name__ == "__main__":
    main()
