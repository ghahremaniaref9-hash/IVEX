"""IVEX Medya - edit a talking-head video into a sales Reels (1080x1920, 30 fps).

Kullanım:  python3 konusma_kurgu.py ayarlar/ivex-tanitim-video.json

Ayar dosyasındaki "parcalar" sırayla kesilip birleştirilir (ilk parça soğuk açılış kancası),
her parçada yakınlaştırma noktaları uygulanır, "konusma" metninden kelime kelime altyazı,
"bolumler"den hizmet etiketleri üretilir; ses temizlenip -14 LUFS'a getirilir, sona satış kartı eklenir.
Kelime zamanları cümle içinde hece (ünlü) sayısına göre dağıtılır.
"""
import json
import os
import subprocess
import sys
import tempfile

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from marka import LIME, WHITE, end_card, font, repo, tracked, logo, write_video

W, H, FPS = 1080, 1920, 30
SR = 48000
FF = imageio_ffmpeg.get_ffmpeg_exe()
COLORS = {"beyaz": WHITE, "lime": LIME}
VOWELS = set("aeıioöuüAEIİOÖUÜ")
CAP_Y = 1360


def upper_tr(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def words_with_times(lines):
    """Spread each sentence's words over its time span by syllable (vowel) count."""
    out = []
    for ln in lines:
        words = ln["metin"].split()
        weights = [max(1, sum(c in VOWELS for c in w)) + (0.6 if w[-1] in ",." else 0) for w in words]
        span, t = ln["son"] - ln["bas"], ln["bas"]
        for w, k in zip(words, weights):
            d = span * k / sum(weights)
            out.append({"w": w, "bas": t, "son": t + d})
            t += d
    return out


def chunks(words):
    """Group words into caption chunks of at most 3 words / 20 letters, breaking after punctuation."""
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) == 3 or len(" ".join(x["w"] for x in cur + [w])) > 20):
            groups.append(cur)
            cur = []
        cur.append(w)
        if w["w"][-1] in ",.":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def read_frames(src, start, n):
    cmd = [FF, "-loglevel", "error", "-ss", f"{start:.3f}", "-i", src, "-frames:v", str(n), "-vf", f"fps={FPS}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    while len(frames) < n:  # pad the tail if the decoder returns a frame short
        frames = np.concatenate([frames, frames[-1:]])
    return frames


LUT = [min(255, max(0, round(128 + (v - 128) * 1.06 + 2))) for v in range(256)] * 3


def grade(im):
    return ImageEnhance.Color(im.point(LUT)).enhance(0.96)


def zoomed(frame, z, focus):
    """Punch in by factor z, keeping `focus` (the face) at the same spot on screen."""
    im = Image.fromarray(frame)
    if z <= 1.001:
        return im
    fx, fy = focus
    cw, ch = W / z, H / z
    x0 = min(max(fx - fx / z, 0), W - cw)
    y0 = min(max(fy - fy / z, 0), H - ch)
    return im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def caption_layer(group, active):
    """One caption chunk; the word being spoken is lime."""
    f = font("Black", 66)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    texts = [upper_tr(w["w"]) for w in group]
    space = probe.textlength(" ", font=f)
    widths = [probe.textlength(t, font=f) for t in texts]
    lines, cur, cur_w = [], [], 0
    for i, wd in enumerate(widths):
        if cur and cur_w + space + wd > 940:
            lines.append(cur)
            cur, cur_w = [], 0
        cur_w += (space if cur else 0) + wd
        cur.append(i)
    lines.append(cur)
    im = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for li, idx in enumerate(lines):
        lw = sum(widths[i] for i in idx) + space * (len(idx) - 1)
        x, y = (W - lw) / 2, 10 + li * 82
        for i in idx:
            col = LIME if i == active else WHITE
            d.text((x, y), texts[i], font=f, fill=col, stroke_width=7, stroke_fill=(8, 12, 20))
            x += widths[i] + space
    return im


def section_layout(sec):
    """Fixed chip positions for a section, so earlier chips never move when a new one appears."""
    f = font("Bold", 30)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    sizes = [probe.textlength(t, font=f) + 2 * 24 + 32 + 2 * (len(t) - 1) for t, _ in sec["etiketler"]]
    rows, cur, cur_w = [], [], 0
    for i, s in enumerate(sizes):
        if cur and cur_w + 14 + s > 960:
            rows.append(cur)
            cur, cur_w = [], 0
        cur_w += (14 if cur else 0) + s
        cur.append(i)
    rows.append(cur)
    pos = {}
    for r, idx in enumerate(rows):
        rw = sum(sizes[i] for i in idx) + 14 * (len(idx) - 1)
        x = (W - rw) / 2
        for i in idx:
            pos[i] = (x, 262 + r * 78, sizes[i])
            x += sizes[i] + 14
    return pos


def chip(text, w):
    f = font("Bold", 30)
    im = Image.new("RGBA", (round(w) + 4, 66), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w, 62), radius=31, fill=(10, 22, 14, 215), outline=LIME, width=2)
    d.line((22, 32, 30, 40, 43, 23), fill=LIME, width=4, joint="curve")
    tracked(d, (56, 14), text, f, WHITE, 2)
    return im


def pop(t, dur=0.18):
    """Scale for a pop-in that overshoots slightly."""
    if t >= dur:
        return 1.0
    x = max(t / dur, 0.0) - 1
    return 1 + 2.70158 * x ** 3 + 1.70158 * x ** 2


def paste_scaled(canvas, layer, center, s, alpha=1.0):
    if s <= 0.02:
        return
    if abs(s - 1) > 0.01:
        layer = layer.resize((max(1, round(layer.width * s)), max(1, round(layer.height * s))), Image.BICUBIC)
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: round(v * alpha)))
    canvas.alpha_composite(layer, (round(center[0] - layer.width / 2), round(center[1] - layer.height / 2)))


def hook_layer(lines):
    im = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Black", 84)
    for i, (text, col) in enumerate(lines):
        tw = d.textlength(text, font=f)
        d.text(((W - tw) / 2, 20 + i * 100), text, font=f, fill=COLORS[col], stroke_width=8,
               stroke_fill=(8, 12, 20))
    return im


def top_shade(strength):
    yy = np.linspace(0, 1, 620, dtype=np.float32)[:, None]
    a = (strength * 255 * np.clip(1 - yy, 0, 1) ** 1.6).astype(np.uint8)
    shade = Image.new("RGBA", (W, 620), (4, 8, 14, 0))
    shade.putalpha(Image.fromarray(np.repeat(a, W, axis=1)))
    return shade


def build(cfg):
    src = repo(cfg["kaynak"])
    focus = tuple(cfg["odak"])
    words = words_with_times(cfg["konusma"])
    pieces = []
    t_out = 0
    for p in cfg["parcalar"]:
        n = round((p["son"] - p["bas"]) * FPS)
        pieces.append(dict(p, n=n, out=t_out))
        t_out += n / FPS
    end_n = round(cfg["son_kart"]["sure"] * FPS)

    top_logo = logo(40)
    hook = hook_layer(cfg["kanca"])
    shade = top_shade(0.55)
    sections = []
    for sec in cfg["bolumler"]:
        pos = section_layout(sec)
        sections.append((sec, pos, {i: chip(t, pos[i][2]) for i, (t, _) in enumerate(sec["etiketler"])}))
    head_f = font("ExtraBold", 26)
    pops = []
    cap_cache = {}

    def frames():
        last = None
        for pi, p in enumerate(pieces):
            data = read_frames(src, p["bas"], p["n"])
            pw = [w for w in words if p["bas"] - 0.05 <= (w["bas"] + w["son"]) / 2 < p["son"]]
            groups = chunks(pw)
            for k in range(p["n"]):
                ts = p["bas"] + k / FPS
                kf = [z for z in p["zoom"] if z[0] <= ts + 1e-6][-1]
                z = kf[1] * (1 + 0.012 * (ts - kf[0]))
                im = grade(zoomed(data[k], z, focus)).convert("RGBA")
                im.alpha_composite(shade)
                im.alpha_composite(top_logo, ((W - top_logo.width) // 2, 100))
                if p.get("kanca"):
                    im.alpha_composite(hook, (0, 170))
                else:
                    for sec, pos, chips_ in sections:
                        if not (sec["bas"] <= ts < sec["son"]):
                            continue
                        a = min(1, (ts - sec["bas"]) / 0.15, (sec["son"] - ts) / 0.12)
                        hl = Image.new("RGBA", (W, 40), (0, 0, 0, 0))
                        tracked(ImageDraw.Draw(hl), (W / 2, 4), sec["baslik"], head_f, LIME, 5, anchor="m")
                        paste_scaled(im, hl, (W / 2, 222), 1, a)
                        for i, (text, t_chip) in enumerate(sec["etiketler"]):
                            if ts >= t_chip:
                                x, y, cw = pos[i]
                                paste_scaled(im, chips_[i], (x + cw / 2, y + 31), pop(ts - t_chip), a)
                # caption: chunk on screen from its first word until the next chunk starts
                for gi, g in enumerate(groups):
                    g_end = groups[gi + 1][0]["bas"] if gi + 1 < len(groups) else g[-1]["son"] + 0.3
                    first = gi == 0 and k < FPS  # show the opening chunk from the piece's first frame
                    if (g[0]["bas"] - 0.04 <= ts or first) and ts < g_end:
                        active = max([i for i, w in enumerate(g) if w["bas"] <= ts + 0.04] or [0])
                        key = (pi, gi, active)
                        if key not in cap_cache:
                            cap_cache[key] = caption_layer(g, active)
                        grow = 1.0 if pi == 0 else min(1.0, max(0.0, ts - g[0]["bas"] + 0.04) / 0.12)
                        paste_scaled(im, cap_cache[key], (W / 2, CAP_Y), 0.88 + 0.12 * grow)
                        break
                last = im
                yield im.convert("RGB")
        # sales card over a blurred, darkened last frame
        sk = cfg["son_kart"]
        base = last.convert("RGB").filter(ImageFilter.GaussianBlur(22))
        base = Image.blend(base, Image.new("RGB", (W, H), (6, 26, 12)), 0.62).convert("RGBA")
        card = end_card(base, [(t, COLORS[c]) for t, c in sk["satirlar"]], sk["buton"], sk["alt"])
        for k in range(end_n):
            a = min(1, k / (0.35 * FPS))
            yield Image.blend(last, card, a).convert("RGB") if a < 1 else card.convert("RGB")

    for sec in cfg["bolumler"]:
        for _, t_chip in sec["etiketler"]:
            for p in pieces:
                if p["bas"] <= t_chip < p["son"] and not p.get("kanca"):
                    pops.append(p["out"] + t_chip - p["bas"])
    whooshes = [pieces[1]["out"] - 0.18, t_out - 0.12]
    return pieces, t_out + end_n / FPS, frames, pops, whooshes


def sfx_track(total, pops, whooshes, path):
    """Quiet UI pops for the chips and two soft whooshes (hook cut, end card)."""
    n = round(total * SR)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(5)
    t = np.arange(round(0.06 * SR)) / SR
    pop_s = (np.sin(2 * np.pi * 1350 * t) * np.exp(-t * 70) * 0.05).astype(np.float32)
    wl = round(0.42 * SR)
    noise = rng.normal(0, 1, wl).astype(np.float32)
    env = np.sin(np.linspace(0, np.pi, wl)) ** 2
    cut = np.linspace(0.02, 0.25, wl) ** 1.5  # one-pole low-pass opening up = rising whoosh
    whoosh = np.zeros(wl, np.float32)
    y = 0.0
    for i in range(wl):
        y += cut[i] * (noise[i] - y)
        whoosh[i] = y
    whoosh = whoosh / np.abs(whoosh).max() * env * 0.07
    for at, s in [(p, pop_s) for p in pops] + [(w, whoosh) for w in whooshes]:
        i = round(max(at, 0) * SR)
        seg = s[: max(0, min(len(s), n - i))]
        out[i:i + len(seg)] += seg
    data = (np.clip(out, -1, 1) * 32767).astype(np.int16)
    with open(path, "wb") as fh:
        fh.write(data.tobytes())


def audio(cfg, pieces, total, sfx_raw, path):
    src = repo(cfg["kaynak"])
    parts = []
    for i, p in enumerate(pieces):
        d = p["n"] / FPS
        parts.append(f"[0:a]atrim=start={p['bas']:.4f}:end={p['bas'] + d:.4f},asetpts=PTS-STARTPTS,"
                     f"aresample={SR},afade=t=in:d=0.012,afade=t=out:st={d - 0.012:.4f}:d=0.012[a{i}]")
    graph = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(pieces)))
    graph += (f"concat=n={len(pieces)}:v=0:a=1,highpass=f=70,afftdn=nf=-28,"
              f"loudnorm=I=-14:TP=-1.5:LRA=9,aresample={SR},apad=whole_dur={total:.3f}[voice];"
              f"[1:a]aresample={SR}[fx];[voice][fx]amix=inputs=2:normalize=0:duration=first,"
              f"atrim=end={total:.3f}[out]")
    cmd = [FF, "-loglevel", "error", "-y", "-i", src, "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", sfx_raw,
           "-filter_complex", graph, "-map", "[out]", "-ac", "2", "-c:a", "aac", "-b:a", "192k", path]
    subprocess.run(cmd, check=True)


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    pieces, total, frames, pops, whooshes = build(cfg)
    with tempfile.TemporaryDirectory() as tmp:
        video = os.path.join(tmp, "v.mp4")
        sfx = os.path.join(tmp, "sfx.raw")
        sound = os.path.join(tmp, "a.m4a")
        cover_frame = []

        def tap():
            for i, f in enumerate(frames()):
                if i == 0:
                    cover_frame.append(f)
                yield f

        write_video(tap(), video, (W, H), FPS)
        sfx_track(total, pops, whooshes, sfx)
        audio(cfg, pieces, total, sfx, sound)
        out = repo(cfg["cikti"])
        subprocess.run([FF, "-loglevel", "error", "-y", "-i", video, "-i", sound, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", "-shortest", out], check=True)
        print("kaydedildi:", out, f"({total:.1f} sn)")
        cover_frame[0].save(repo(cfg["kapak"]), quality=93)
        print("kaydedildi:", repo(cfg["kapak"]))


if __name__ == "__main__":
    main()
