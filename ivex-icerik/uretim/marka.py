"""IVEX Medya - shared brand pieces: colours, fonts, the IVEX logo and the dark green background.

Palette and type follow the IVEX designs in Canva (www.ivex.com.tr post): deep green, neon lime, white,
heavy Montserrat headlines. The lime is sampled from the official logo (ivex-logo.png).
"""
import os
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

GREEN_DARK = (5, 22, 11)
GREEN = (12, 52, 24)
LIME = (218, 255, 46)
WHITE = (255, 255, 255)
SOFT = (214, 226, 214)
INK = (10, 24, 14)


def font(weight, size):
    """weight: Light, Medium, SemiBold, Bold, ExtraBold or Black."""
    num = {"Light": 300, "Medium": 500, "SemiBold": 600, "Bold": 700, "ExtraBold": 800, "Black": 900}[weight]
    return ImageFont.truetype(os.path.join(HERE, "fonts", f"Montserrat_{num}{weight}.ttf"), size)


def repo(*parts):
    return os.path.join(ROOT, *parts)


def logo(height):
    """The official IVEX logo (white inline IVE, lime X) scaled to `height` px, on transparency."""
    im = Image.open(os.path.join(HERE, "ivex-logo.png")).convert("RGBA")
    # the logo file carries a 6 px margin around the letters; scale so the letters are `height` tall
    scale = height / (im.height - 12)
    return im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)


def tracked(d, xy, text, fnt, fill, tracking=0.0, anchor="l"):
    """Letter-spaced text. anchor: l (left), m (centre) or r (right) of `xy`."""
    w = sum(d.textlength(c, font=fnt) for c in text) + tracking * (len(text) - 1)
    x, y = xy
    if anchor == "m":
        x -= w / 2
    elif anchor == "r":
        x -= w
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill)
        x += d.textlength(c, font=fnt) + tracking
    return w


def pill(d, x, y, text, fnt, bg, fg, pad_x=22, h=None, tracking=2, anchor="l"):
    """Rounded label; returns its width."""
    h = h or round(fnt.size * 2.0)
    tw = sum(d.textlength(c, font=fnt) for c in text) + tracking * (len(text) - 1)
    w = tw + 2 * pad_x
    if anchor == "m":
        x -= w / 2
    d.rounded_rectangle((x, y, x + w, y + h), radius=h / 2, fill=bg)
    asc, desc = fnt.getmetrics()
    tracked(d, (x + pad_x, y + (h - asc - desc) / 2 + desc * 0.35), text, fnt, fg, tracking)
    return w


def blend(canvas, draw_fn):
    """Run `draw_fn(draw)` on a transparent layer and composite it, so translucent fills blend on RGBA images."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    canvas.alpha_composite(layer)


def background(size, seed=3, glow=(0.78, 0.18)):
    """Deep green backdrop with a soft lime-green glow, two faint diagonal light bands and fine grain."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    gx, gy = glow
    r = np.hypot((xx - gx * w) / w, (yy - gy * h) / h)
    g = np.clip(1 - r / 0.9, 0, 1) ** 2
    base = np.array(GREEN_DARK, np.float32)
    mid = np.array(GREEN, np.float32)
    hi = np.array((40, 110, 34), np.float32)
    a = base + (mid - base) * np.clip(1 - yy / h * 0.6, 0, 1)[..., None] * 0.7
    a = a + (hi - a) * (g[..., None] * 0.55)
    # diagonal bands, like light through a window
    for off, width, k in ((0.62, 0.10, 0.06), (0.80, 0.05, 0.05)):
        t = (xx / w + yy / h * 0.55) - off - 0.25
        band = np.exp(-(t / width) ** 2)
        a = a + band[..., None] * k * 255 * np.array((0.35, 0.8, 0.3), np.float32)
    rng = np.random.default_rng(seed)
    a = a + rng.normal(0, 3.2, (h, w, 1)).astype(np.float32)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def drop_shadow(canvas, card, xy, blur=28, offset=(0, 18), opacity=150):
    """Paste an RGBA `card` onto `canvas` with a soft shadow underneath."""
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    a = card.getchannel("A").point(lambda v: v * opacity // 255)
    blob = Image.new("RGBA", card.size, (0, 0, 0, 255))
    blob.putalpha(a)
    sh.paste(blob, (xy[0] + offset[0], xy[1] + offset[1]))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    canvas.alpha_composite(card, xy)


def end_card(bg, lines, button, sub_lines):
    """Closing frame for vertical videos: logo, two-colour headline, lime button, small print."""
    w, _ = bg.size
    im = bg.copy()
    lg = logo(112)
    im.alpha_composite(lg, ((w - lg.width) // 2, 470))
    d = ImageDraw.Draw(im)
    f = font("Black", 66)
    y = 760
    for line, col in lines:
        d.text(((w - d.textlength(line, font=f)) / 2, y), line, font=f, fill=col)
        y += 82
    pill(d, w / 2, y + 60, button, font("ExtraBold", 30), LIME, INK, pad_x=34, h=78, tracking=2, anchor="m")
    sub = font("Medium", 28)
    for i, line in enumerate(sub_lines):
        d.text(((w - d.textlength(line, font=sub)) / 2, y + 178 + i * 40), line, font=sub, fill=SOFT)
    tracked(d, (w / 2, y + 300), "WWW.İVEX.COM.TR", font("Bold", 22), (196, 214, 198), 6, anchor="m")
    return im


def write_video(frames, path, size, fps):
    """Encode RGB PIL frames to an H.264 MP4 that Instagram accepts (silent; music is added in the app)."""
    w, h = size
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "slow", "-crf", "21", "-movflags", "+faststart", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for frame in frames:
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    print("kaydedildi:", path)
