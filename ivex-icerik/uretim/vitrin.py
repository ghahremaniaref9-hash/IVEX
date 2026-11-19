"""IVEX Medya - "Ne yapıyoruz?" vitrin Reels'i (1080x1920, 30 fps, 27 sn).

Kullanım:  python3 vitrin.py [ayarlar/vitrin.json]
Kurgu (IVEX'in farkı: pahalı reklamdan önce güçlü senaryo ve organik müşteri, sonra doğru yönetilen Meta reklamı):
   0,0 -  4,0  Kanca: Higgsfield'de üretilen sahne (boş butikte telefonuna bakıp iç çeken işletme sahibi),
               "Reklama para yakıyorsun, / ama satış gelmiyor mu?"
   4,0 -  7,0  "Sorun bütçe değil." - "Sorun senaryo."
   7,0 - 11,5  IVEX yöntemi: 01 güçlü senaryo, 02 organik izlenme, 03 doğru Meta reklamı.
  11,5 - 20,3  Gerçek işlerimizden: Mutfella feed'i, Minah Tekstil logosu (önce/sonra), Minah Meta reklamı
               (önce/sonra), Bidaha davet videosu. Her biri 2,2 sn.
  20,3 - 23,0  Hizmetler ve sektörler.
  23,0 - 27,0  Kapanış: "Önce organik, sonra doğru reklam." ve DM'den "SENARYO" yaz.
Sahnedeki işler müşterilere gerçekten teslim edilen dosyalardır; rakam ya da sonuç gösterilmez.
Müzik ve efektler ses.py ile aynı zaman çizelgesinden üretilir.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ses  # noqa: E402
from marka import (GREEN, GREEN_DARK, INK, LIME, SOFT, WHITE, background, end_card, font, pill, repo,  # noqa: E402
                   rounded, tracked)

import imageio_ffmpeg  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
T_PROBLEM, T_METHOD, T_WORK, WORK_LEN, T_SERV, T_END, TOTAL = 4.0, 7.0, 11.5, 2.2, 20.3, 23.0, 27.0
HOOK2 = 1.45
SCEN2 = 5.15
STEPS = (7.55, 8.45, 9.35)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def back(x, s=1.6):
    x = min(max(x, 0.0), 1.0)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def ramp(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


def text_layer(text, fnt, fill, shadow=True, track=0):
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw = sum(d0.textlength(c, font=fnt) for c in text) + track * (len(text) - 1)
    asc, desc = fnt.getmetrics()
    pad = 40
    im = Image.new("RGBA", (round(tw) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        tracked(ImageDraw.Draw(sh), (pad, pad + 5), text, fnt, (0, 8, 2, 210), track)
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    tracked(ImageDraw.Draw(im), (pad, pad), text, fnt, fill, track)
    return im.crop(im.getbbox())


def put(canvas, layer, cx, cy, opacity=1.0, scale=1.0):
    if opacity <= 0.003:
        return
    if abs(scale - 1) > 1e-3:
        layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))), Image.BILINEAR)
    if opacity < 0.999:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: round(v * opacity)))
    canvas.alpha_composite(layer, (round(cx - layer.width / 2), round(cy - layer.height / 2)))


def card_shadow(img, radius=34):
    """A rounded card with a soft shadow, returned on a slightly larger transparent canvas."""
    card = rounded(img.convert("RGB"), radius)
    m = 50
    out = Image.new("RGBA", (card.width + 2 * m, card.height + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 6, 2, 0))
    sh.putalpha(card.getchannel("A").point(lambda v: v * 0.7))
    out.alpha_composite(sh, (m, m + 20))
    out = out.filter(ImageFilter.GaussianBlur(22))
    out.alpha_composite(card, (m, m))
    return out


def cover(img, size):
    return ImageOps.fit(img.convert("RGB"), size, Image.LANCZOS, centering=(0.5, 0.45))


def video_frames(path, start, dur, size, fps=FPS):
    w, h = size
    raw = subprocess.run([FF, "-loglevel", "error", "-ss", str(start), "-t", str(dur), "-i", path, "-vf",
                          f"fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return [Image.frombytes("RGB", (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3]) for i in range(n)]


# ---------------------------------------------------------------- the reel

class Reel:
    def __init__(self, cfg):
        self.cfg = cfg
        self.bg = background((W, H), seed=7, glow=(0.75, 0.22)).convert("RGBA")
        # hook
        self.hook = video_frames(repo(cfg["acilis_klibi"]), 0, T_PROBLEM + 0.2, (W, H))
        shade = np.zeros((H, W), np.float32)
        yy = np.arange(H)[:, None]
        shade[:] = np.clip((yy - 980) / 600, 0, 1) ** 1.3 * 235
        self.hook_shade = Image.new("RGBA", (W, H), (2, 10, 4, 0))
        self.hook_shade.putalpha(Image.fromarray(shade.astype(np.uint8)))
        k1, k2 = cfg["kanca"]
        self.k1 = text_layer(k1, font("Black", 66), WHITE)
        self.k2 = text_layer(k2, font("Black", 66), LIME)
        # problem
        s = cfg["sorun"]
        self.p1 = text_layer(s["ilk"], font("ExtraBold", 64), SOFT)
        self.p2 = text_layer(s["ikinci"], font("Black", 104), LIME)
        # method
        m = cfg["yontem"]
        self.m_title = self.pill_layer(m["baslik"], font("ExtraBold", 30), LIME, INK, 34, 70)
        self.steps = [self.step_card(i + 1, a, b) for i, (a, b) in enumerate(m["adimlar"])]
        # work
        self.w_title = self.pill_layer(cfg["isler_baslik"], font("ExtraBold", 28), LIME, INK, 30, 64)
        self.works = [self.work(i, w) for i, w in enumerate(cfg["isler"])]
        # services
        self.s_title = self.pill_layer("HİZMETLERİMİZ", font("ExtraBold", 28), LIME, INK, 30, 64)
        self.c_title = self.pill_layer("KİMLERLE ÇALIŞIYORUZ", font("ExtraBold", 28), LIME, INK, 30, 64)
        self.serv = self.chip_rows(cfg["hizmetler"], 340)
        self.sect = self.chip_rows(cfg["sektorler"], 1060, outline=True)
        # end
        e = cfg["son"]
        lines = [(txt, LIME if col == "lime" else WHITE) for txt, col in e["satirlar"]]
        self.end = end_card(background((W, H), seed=7, glow=(0.5, 0.3)).convert("RGBA"), lines, e["buton"], e["alt"])
        self.flash = Image.new("RGBA", (W, H), LIME + (255,))

    @staticmethod
    def pill_layer(text, fnt, bg, fg, pad, h):
        d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
        w = sum(d0.textlength(c, font=fnt) for c in text) + 3 * (len(text) - 1) + 2 * pad
        im = Image.new("RGBA", (round(w) + 4, h + 4), (0, 0, 0, 0))
        pill(ImageDraw.Draw(im), 2, 2, text, fnt, bg, fg, pad_x=pad, h=h, tracking=3)
        return im

    @staticmethod
    def step_card(n, title, sub):
        w, h = 860, 210
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=32, fill=(10, 40, 18, 235), outline=(70, 120, 60, 255),
                            width=2)
        d.ellipse((36, h / 2 - 58, 152, h / 2 + 58), fill=LIME)
        f = font("Black", 50)
        num = f"{n:02d}"
        d.text((94 - d.textlength(num, font=f) / 2, h / 2 - 32), num, font=f, fill=INK)
        d.text((190, 46), title, font=font("ExtraBold", 50), fill=WHITE)
        d.text((192, 120), sub, font=font("Medium", 32), fill=SOFT)
        return im

    def chip_rows(self, items, top, outline=False):
        f = font("Bold", 36)
        d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
        chips = []
        for it in items:
            w = round(d0.textlength(it, font=f)) + 64
            im = Image.new("RGBA", (w, 84), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            if outline:
                d.rounded_rectangle((1, 1, w - 2, 82), radius=41, outline=LIME, width=3, fill=(8, 30, 14, 200))
                col = WHITE
            else:
                d.rounded_rectangle((0, 0, w - 1, 83), radius=42, fill=WHITE)
                col = INK
            d.text((32, 16), it, font=f, fill=col)
            chips.append(im)
        rows, cur, cw = [], [], 0
        for c in chips:
            if cur and cw + c.width + 18 > 920:
                rows.append(cur)
                cur, cw = [], 0
            cur.append(c)
            cw += c.width + 18
        rows.append(cur)
        placed = []
        y = top
        for r in rows:
            total = sum(c.width for c in r) + 18 * (len(r) - 1)
            x = (W - total) / 2
            for c in r:
                placed.append((c, x + c.width / 2, y + 42))
                x += c.width + 18
            y += 104
        return placed

    def work(self, i, w):
        lab = text_layer(w["etiket"], font("Black", 58), WHITE)
        client = text_layer(w["musteri"], font("SemiBold", 34), SOFT)
        item = {"tur": w["tur"], "lab": lab, "client": client}
        if w["tur"] == "telefon":
            # the client's published posts, two per row like a profile grid seen up close
            sw, sh, gap = 470, 930, 6
            cw, ch = (sw - gap) // 2, (sh - 2 * gap) // 3
            screen = Image.new("RGB", (sw, sh), (255, 255, 255))
            for k, g in enumerate(w["gorseller"][:6]):
                screen.paste(cover(Image.open(repo(g)), (cw, ch)), ((k % 2) * (cw + gap), (k // 2) * (ch + gap)))
            item["screen"] = screen
            item["size"] = (520, 980)
        elif w["tur"] == "once_sonra":
            rw, rh = w["oran"]
            size = (760, 760) if rw == rh else (700, 875)
            before = Image.open(repo(w["once"])).convert("RGB")
            if w.get("once_kirp"):
                before = before.crop(tuple(w["once_kirp"]))
                before = before.resize(size, Image.BICUBIC)  # the original tiny logo, simply enlarged
            else:
                before = cover(before, size)
            after = cover(Image.open(repo(w["sonra"])), size)
            item["before"], item["after"], item["size"] = before, after, size
        else:
            size = (540, 960)
            item["frames"] = video_frames(repo(w["video"]), w["baslangic"], WORK_LEN + 0.2, size)
            item["size"] = size
        return item

    # -------------------------------------------------------------- scenes

    def hook_scene(self, t):
        i = min(int(t * FPS), len(self.hook) - 1)
        f = self.hook[i].convert("RGBA")
        f.alpha_composite(self.hook_shade)
        put(f, self.k1, W / 2, 1300 + 30 * (1 - ease((t - 0.25) / 0.4)), ramp(t, 0.25, 0.55))
        a = ramp(t, HOOK2, HOOK2 + 0.25)
        put(f, self.k2, W / 2, 1395, a, 0.9 + 0.1 * back((t - HOOK2) / 0.35))
        return f

    def problem_scene(self, t):
        f = self.bg.copy()
        lt = t - T_PROBLEM
        a1 = ramp(lt, 0.05, 0.35)
        y1 = 820 if t < SCEN2 else 820 - 90 * ease((t - SCEN2) / 0.35)
        put(f, self.p1, W / 2, y1, a1 * (1 - 0.45 * ramp(t, SCEN2, SCEN2 + 0.3)))
        if t >= SCEN2 - 0.02:
            # a strike through "bütçe değil" once the real answer lands
            d = ImageDraw.Draw(f)
            k = ease((t - SCEN2) / 0.3)
            x0 = W / 2 - self.p1.width / 2 + 10
            d.line([(x0, y1 + 4), (x0 + (self.p1.width - 20) * k, y1 + 4)], fill=(230, 70, 60), width=7)
            put(f, self.p2, W / 2, 1010, ramp(t, SCEN2, SCEN2 + 0.2), 0.85 + 0.15 * back((t - SCEN2) / 0.4))
        return f

    def method_scene(self, t):
        f = self.bg.copy()
        lt = t - T_METHOD
        put(f, self.m_title, W / 2, 420 - 20 * (1 - ease(lt / 0.35)), ramp(lt, 0, 0.3))
        for k, (card, at) in enumerate(zip(self.steps, STEPS)):
            p = ease((t - at) / 0.4)
            cy = 640 + k * 290
            put(f, card, W / 2 + 120 * (1 - p), cy, ramp(t, at, at + 0.25))
            if k and t > at:
                d = ImageDraw.Draw(f)  # a small lime chevron between the cards
                y = cy - 145
                d.line([(W / 2 - 18, y - 9), (W / 2, y + 9), (W / 2 + 18, y - 9)], fill=LIME, width=6, joint="curve")
        return f

    def work_scene(self, t):
        f = self.bg.copy()
        lt = t - T_WORK
        put(f, self.w_title, W / 2, 300, ramp(lt, 0, 0.25))
        k = min(int(lt // WORK_LEN), len(self.works) - 1)
        st = lt - k * WORK_LEN
        it = self.works[k]
        enter = ease(st / 0.32)
        leave = ease((st - (WORK_LEN - 0.22)) / 0.22) if k < len(self.works) - 1 else 0.0
        dx = W * (1 - enter) - W * leave
        put(f, it["lab"], W / 2 + dx * 0.6, 400, enter * (1 - leave))
        cw, ch = it["size"]
        cy = 455 + 40 + ch / 2 if it["tur"] != "telefon" else 470 + ch / 2
        cx = W / 2 + dx
        if it["tur"] == "telefon":
            card = self.phone(it, st)
        elif it["tur"] == "once_sonra":
            card = self.before_after(it, st)
        else:
            fr = it["frames"][min(int(st * FPS), len(it["frames"]) - 1)]
            card = card_shadow(fr)
        put(f, card, cx, cy, enter * (1 - leave))
        put(f, it["client"], W / 2 + dx * 0.6, cy + ch / 2 + 62, ramp(st, 0.2, 0.45) * (1 - leave))
        return f

    @staticmethod
    def phone(it, st):
        w, h = it["size"]
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=64, fill=(14, 16, 14, 255))
        scr = it["screen"]
        sx, sy, sw, sh = 25, 25, w - 50, h - 50
        z = 1 + 0.06 * ease(st / WORK_LEN)  # a slow push into the grid
        zw, zh = round(sw / z), round(sh / z)
        view = scr.crop(((sw - zw) // 2, 0, (sw - zw) // 2 + zw, zh)).resize((sw, sh), Image.BILINEAR)
        im.paste(rounded(view, 42), (sx, sy), rounded(view, 42))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((w / 2 - 60, 36, w / 2 + 60, 62), radius=13, fill=(14, 16, 14, 255))
        return card_shadow_rgba(im)

    @staticmethod
    def before_after(it, st):
        w, h = it["size"]
        p = ease((st - 0.55) / 0.7)
        split = round(w * p)
        im = it["before"].copy()
        if split > 0:
            im.paste(it["after"].crop((0, 0, split, h)), (0, 0))
        d = ImageDraw.Draw(im)
        if 0 < split < w:
            d.rectangle((split - 3, 0, split + 3, h), fill=LIME)
        label = "SONRA" if p > 0.5 else "ÖNCE"
        f = font("ExtraBold", 26)
        pill(d, 24, 24, label, f, LIME if p > 0.5 else WHITE, INK, pad_x=20, h=54, tracking=3)
        return card_shadow(im)

    def end_scene(self, t):
        lt = t - T_END
        f = self.end.copy()
        if lt < 0.35:
            base = self.bg.copy()
            put(base, f, W / 2, H / 2, ease(lt / 0.35), 1.04 - 0.04 * ease(lt / 0.35))
            f = base
        return f

    def services_scene(self, t):
        f = self.bg.copy()
        lt = t - T_SERV
        put(f, self.s_title, W / 2, 270, ramp(lt, 0, 0.25))
        for k, (chip, x, y) in enumerate(self.serv):
            at = 0.15 + k * 0.1
            put(f, chip, x, y, ramp(lt, at, at + 0.2), 0.7 + 0.3 * back((lt - at) / 0.3))
        put(f, self.c_title, W / 2, 990, ramp(lt, 0.9, 1.15))
        for k, (chip, x, y) in enumerate(self.sect):
            at = 1.0 + k * 0.1
            put(f, chip, x, y, ramp(lt, at, at + 0.2), 0.7 + 0.3 * back((lt - at) / 0.3))
        return f

    def frame(self, t):
        if t < T_PROBLEM:
            f = self.hook_scene(t)
        elif t < T_METHOD:
            f = self.problem_scene(t)
        elif t < T_WORK:
            f = self.method_scene(t)
        elif t < T_SERV:
            f = self.work_scene(t)
        elif t < T_END:
            f = self.services_scene(t)
        else:
            f = self.end_scene(t)
        a = max([0.0] + [0.22 * s * math.exp(-(t - h) / 0.07) for h, s in HITS if 0 <= t - h < 0.3])
        if a > 0.01:
            f = Image.blend(f, self.flash, a)
        return f.convert("RGB")


def card_shadow_rgba(im):
    m = 50
    out = Image.new("RGBA", (im.width + 2 * m, im.height + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 6, 2, 0))
    sh.putalpha(im.getchannel("A").point(lambda v: v * 0.7))
    out.alpha_composite(sh, (m, m + 20))
    out = out.filter(ImageFilter.GaussianBlur(22))
    out.alpha_composite(im, (m, m))
    return out


HITS = [(T_PROBLEM, 1.0), (T_END, 1.2)]


def sound_plan(cfg):
    ev = [[0.25, "pop", {}], [HOOK2, "vurgu", {"i": 0}],
          [T_PROBLEM - 1.0, "yukselis", {"sure": 1.0}], [T_PROBLEM - 0.45, "rulo", {"sure": 0.45}],
          [T_PROBLEM, "darbe", {"boy": 1.1}], [SCEN2, "boom", {}], [SCEN2, "vurgu", {"i": 1}],
          [T_METHOD, "gecis", {}], [T_METHOD + 0.05, "pop", {}]]
    ev += [[at, "adim", {"i": k}] for k, at in enumerate(STEPS)]
    ev += [[T_WORK, "gecis", {}]]
    for k in range(len(cfg["isler"])):
        at = T_WORK + k * WORK_LEN
        ev += [[at + 0.3, "kaydir", {}], [at + 0.32, "kart", {}]]
        if cfg["isler"][k]["tur"] == "once_sonra":
            ev += [[at + 1.25, "whoosh", {"sure": 0.5}], [at + 1.25, "parilti", {}]]
    ev += [[T_SERV, "gecis", {}]]
    ev += [[T_SERV + 0.15 + k * 0.1, "nota", {"i": k}] for k in range(len(cfg["hizmetler"]))]
    ev += [[T_SERV + 1.0 + k * 0.1, "nota", {"i": k + 3}] for k in range(len(cfg["sektorler"]))]
    ev += [[T_END - 0.95, "yukselis", {"sure": 0.95}], [T_END - 0.45, "rulo", {"sure": 0.45}],
           [T_END, "darbe", {"boy": 1.3}], [T_END + 0.1, "parilti", {}], [T_END + 0.5, "vurgu", {"i": 1}],
           [T_END + 0.9, "pop", {}]]
    parts = {"insa": (0.0, T_PROBLEM - 0.12), "drop": T_PROBLEM, "ritim": (T_PROBLEM, T_END - 0.5), "son": T_END,
             "kisilma": TOTAL - 1.6}
    return {"bolumler": parts, "olaylar": sorted(ev, key=lambda e: e[0])}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else repo("ivex-icerik", "ayarlar", "vitrin.json")
    cfg = json.load(open(path, encoding="utf-8"))
    raw, music = repo("ivex-icerik", ".vitrin-ham.wav"), repo("ivex-icerik", ".vitrin-muzik.m4a")
    ses.write(sound_plan(cfg), TOTAL, raw)
    ses.master(raw, music)
    os.remove(raw)
    reel = Reel(cfg)
    out = repo(cfg["cikti"])
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", music, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n = round(TOTAL * FPS)
    for i in range(n):
        enc.stdin.write(reel.frame(i / FPS).tobytes())
        if i % 90 == 0:
            print(f"  kare {i}/{n}", flush=True)
    enc.stdin.close()
    enc.wait()
    os.remove(music)
    print("kaydedildi:", os.path.relpath(out, repo()))
    reel.frame(T_PROBLEM - 0.3).save(repo(cfg["kapak"]), quality=93)  # the hook, both lines on screen
    print("kaydedildi:", cfg["kapak"])


if __name__ == "__main__":
    main()
