"""IVEX Medya - iki kavram Reels'i (1080x1920, 30 fps): "Delikli kova" ve "Aynı ürün, iki senaryo".

Kullanım:  python3 kavramlar.py [kova|fark] [ayarlar/kavramlar.json]   (ad verilmezse ikisi de üretilir)
İkisi de IVEX'in ana fikrini farklı bir yoldan anlatır: önce güçlü senaryo ve organik ilgi, sonra doğru reklam.
Sinematik sahneler Higgsfield'de (Kling 3.0 Pro) üretildi; yazılar, kartlar, kapanış ve müzik burada kodla eklenir.

Delikli kova (21,5 sn)
   0,0 -  4,5  Delikli kovaya altın dökülüyor, paralar akıp gidiyor. "Her ay reklama bütçe döküyorsun, / ama kova delik."
   4,5 -  9,0  "Delikler nerede?" üç delik.
   9,0 - 13,0  "Daha çok para dökmek deliği kapatmaz." - "Önce deliği kapat."
  13,0 - 17,5  Sağlam kova doluyor: "Önce senaryo: delik kapanır. / Sonra reklam: kova dolar."
  17,5 - 21,5  Kapanış, DM'den "KOVA".
Aynı ürün, iki senaryo (21,5 sn)
   0,0 -  3,0  "Aynı kazak. Aynı bütçe. İki farklı video."
   3,0 -  7,5  A · Sıradan: askıda kazak, sıradan bir metin. "Sonuç: kaydırılır."
   7,5 - 12,5  B · Senaryolu: vapurda kırmızı kazak, hikâyeli metin. "Sonuç: izlenir."
  12,5 - 17,0  "Fark ürün değil, senaryo." ve üç malzeme.
  17,0 - 21,5  Kapanış, DM'den "FARK".
Rakam ya da sonuç vaadi yoktur.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ses  # noqa: E402
from marka import INK, LIME, SOFT, WHITE, background, end_card, font, repo  # noqa: E402
from vitrin import FF, FPS, H, W, Reel, back, ease, put, ramp, text_layer, video_frames  # noqa: E402

RED = (236, 72, 64)


def slowed(path, src_sec, out_sec, size):
    """The first `src_sec` seconds of a clip stretched to `out_sec` (avoids a flawed tail)."""
    w, h = size
    raw = subprocess.run([FF, "-loglevel", "error", "-t", str(src_sec), "-i", path, "-vf",
                          f"setpts=PTS*{out_sec / src_sec:.4f},fps={FPS},scale={w}:{h}:force_original_aspect_ratio="
                          f"increase,crop={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return [Image.frombytes("RGB", (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3]) for i in range(n)]


def col(name):
    return LIME if name == "lime" else WHITE


def shade(top=960, span=620, strength=235):
    a = np.clip((np.arange(H)[:, None] - top) / span, 0, 1) ** 1.3 * strength
    im = Image.new("RGBA", (W, H), (2, 10, 4, 0))
    im.putalpha(Image.fromarray(np.repeat(a, W, axis=1).astype(np.uint8)))
    return im


def label_pill(text, bg, fg):
    return Reel.pill_layer(text, font("ExtraBold", 30), bg, fg, 30, 68)


class Base:
    TOTAL = 21.5

    def __init__(self, cfg):
        self.cfg = cfg
        self.bg = background((W, H), seed=11, glow=(0.7, 0.25)).convert("RGBA")
        e = cfg["son"]
        self.end = end_card(background((W, H), seed=11, glow=(0.5, 0.3)).convert("RGBA"),
                            [(t, col(c)) for t, c in e["satirlar"]], e["buton"], e["alt"])
        self.flash = Image.new("RGBA", (W, H), LIME + (255,))
        self.shade = shade()

    def end_scene(self, t, start):
        lt = t - start
        f = self.end.copy()
        if lt < 0.35:
            base = self.bg.copy()
            put(base, f, W / 2, H / 2, ease(lt / 0.35), 1.04 - 0.04 * ease(lt / 0.35))
            f = base
        return f

    def clip(self, frames, t, start):
        i = min(int((t - start) * FPS), len(frames) - 1)
        f = frames[i].convert("RGBA")
        f.alpha_composite(self.shade)
        return f

    def finish(self, f, t):
        a = max([0.0] + [0.22 * s * math.exp(-(t - h) / 0.07) for h, s in self.HITS if 0 <= t - h < 0.3])
        if a > 0.01:
            f = Image.blend(f, self.flash, a)
        return f.convert("RGB")


# ---------------------------------------------------------------- Delikli kova

class Kova(Base):
    T_HOLES, T_PROB, T_FIX, T_END = 4.5, 9.0, 13.0, 17.5
    HOLE_AT = (5.05, 5.95, 6.85)
    HOOK2, ANSWER, FIX2 = 1.9, 10.7, 14.7
    HITS = [(4.5, 1.0), (10.7, 0.8), (17.5, 1.2)]

    def __init__(self, cfg):
        super().__init__(cfg)
        self.leak = video_frames(repo(cfg["klip_delik"]), 0, self.T_HOLES + 0.2, (W, H))
        # the generated clip's last second shows coins passing through the bucket wall: use 3.6 s, slowed
        self.full = slowed(repo(cfg["klip_dolu"]), 3.6, self.T_END - self.T_FIX + 0.2, (W, H))
        k1, k2 = cfg["kanca"]
        self.k1 = text_layer(k1, font("Black", 50), WHITE)
        self.k2 = text_layer(k2, font("Black", 92), LIME)
        self.h_title = label_pill(cfg["delikler_baslik"], LIME, INK)
        self.holes = [self.hole_card(txt) for txt in cfg["delikler"]]
        s1, s2 = cfg["sorun"]
        self.s1 = text_layer(s1, font("ExtraBold", 60), SOFT)
        self.s2 = text_layer(s2, font("ExtraBold", 60), SOFT)
        self.ans = text_layer(cfg["cevap"], font("Black", 92), LIME)
        c1, c2 = cfg["cozum"]
        self.c1 = text_layer(c1, font("Black", 58), WHITE)
        self.c2 = text_layer(c2, font("Black", 58), LIME)

    @staticmethod
    def hole_card(text):
        w, h = 880, 170
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=30, fill=(10, 40, 18, 235), outline=(70, 120, 60, 255),
                            width=2)
        cx, cy = 92, h / 2  # a dark hole with a torn red rim
        pts = [(cx + (44 + 7 * math.sin(k * 2.1)) * math.cos(k * math.pi / 9),
                cy + (44 + 7 * math.sin(k * 2.1)) * math.sin(k * math.pi / 9)) for k in range(18)]
        d.polygon(pts, fill=RED)
        d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=(4, 8, 4))
        f = font("Bold", 40)
        d.text((170, h / 2 - 25), text, font=f, fill=WHITE)
        return im

    def frame(self, t):
        if t < self.T_HOLES:
            f = self.clip(self.leak, t, 0)
            put(f, self.k1, W / 2, 1290 + 30 * (1 - ease((t - 0.3) / 0.4)), ramp(t, 0.3, 0.6))
            put(f, self.k2, W / 2, 1410, ramp(t, self.HOOK2, self.HOOK2 + 0.2),
                0.85 + 0.15 * back((t - self.HOOK2) / 0.4))
        elif t < self.T_PROB:
            f = self.bg.copy()
            lt = t - self.T_HOLES
            put(f, self.h_title, W / 2, 460 - 20 * (1 - ease(lt / 0.35)), ramp(lt, 0, 0.3))
            for k, (card, at) in enumerate(zip(self.holes, self.HOLE_AT)):
                p = ease((t - at) / 0.4)
                put(f, card, W / 2 - 120 * (1 - p), 680 + k * 230, ramp(t, at, at + 0.25))
        elif t < self.T_FIX:
            f = self.bg.copy()
            lt = t - self.T_PROB
            dim = 1 - 0.45 * ramp(t, self.ANSWER, self.ANSWER + 0.3)
            put(f, self.s1, W / 2, 760, ramp(lt, 0.05, 0.35) * dim)
            put(f, self.s2, W / 2, 850, ramp(lt, 0.45, 0.75) * dim)
            if t >= self.ANSWER - 0.02:
                put(f, self.ans, W / 2, 1040, ramp(t, self.ANSWER, self.ANSWER + 0.2),
                    0.85 + 0.15 * back((t - self.ANSWER) / 0.4))
        elif t < self.T_END:
            f = self.clip(self.full, t, self.T_FIX)
            lt = t - self.T_FIX
            put(f, self.c1, W / 2, 1300 + 30 * (1 - ease((lt - 0.3) / 0.4)), ramp(lt, 0.3, 0.6))
            put(f, self.c2, W / 2, 1400, ramp(t, self.FIX2, self.FIX2 + 0.25), 0.9 + 0.1 * back((t - self.FIX2) / 0.4))
        else:
            f = self.end_scene(t, self.T_END)
        return self.finish(f, t)

    def sound(self):
        ev = [[0.3, "pop", {}], [self.HOOK2, "boom", {}], [self.HOOK2, "vurgu", {"i": 0}],
              [self.T_HOLES - 1.0, "yukselis", {"sure": 1.0}], [self.T_HOLES - 0.45, "rulo", {"sure": 0.45}],
              [self.T_HOLES, "darbe", {"boy": 1.0}]]
        ev += [[at, "adim", {"i": k}] for k, at in enumerate(self.HOLE_AT)]
        ev += [[self.T_PROB, "gecis", {}], [self.T_PROB + 0.5, "kart", {}], [self.ANSWER, "darbe", {"boy": 0.8}],
               [self.ANSWER, "vurgu", {"i": 1}], [self.T_FIX, "gecis", {}], [self.T_FIX + 0.1, "parilti", {}],
               [self.FIX2, "vurgu", {"i": 0}]]
        ev += [[self.T_END - 0.95, "yukselis", {"sure": 0.95}], [self.T_END - 0.45, "rulo", {"sure": 0.45}],
               [self.T_END, "darbe", {"boy": 1.3}], [self.T_END + 0.1, "parilti", {}],
               [self.T_END + 0.5, "vurgu", {"i": 1}], [self.T_END + 0.9, "pop", {}]]
        parts = {"insa": (0.0, self.T_HOLES - 0.12), "drop": self.T_HOLES, "ritim": (self.T_HOLES, self.T_END - 0.5),
                 "son": self.T_END, "kisilma": self.TOTAL - 1.6}
        return {"bolumler": parts, "olaylar": sorted(ev, key=lambda e: e[0])}

    COVER = 4.2


# ---------------------------------------------------------------- Aynı ürün, iki senaryo

class Fark(Base):
    T_A, T_B, T_LESSON, T_END = 3.0, 7.5, 12.5, 17.0
    HOOK_AT = (0.2, 0.95, 1.7)
    A_RESULT, B_LINE2, B_RESULT, LESSON2 = 5.7, 9.4, 10.9, 13.55
    ING_AT = (14.5, 15.0, 15.5)
    HITS = [(1.7, 0.8), (7.5, 0.9), (13.55, 0.9), (17.0, 1.2)]

    def __init__(self, cfg):
        super().__init__(cfg)
        self.plain = video_frames(repo(cfg["klip_siradan"]), 0, self.T_B - self.T_A + 0.2, (W, H))
        self.story = video_frames(repo(cfg["klip_senaryo"]), 0, self.T_LESSON - self.T_B + 0.2, (W, H))
        self.hook = [text_layer(t, font("Black", 92), col(c)) for t, c in cfg["kanca"]]
        a, b = cfg["a"], cfg["b"]
        self.a_pill = label_pill(a["etiket"], WHITE, INK)
        self.b_pill = label_pill(b["etiket"], LIME, INK)
        self.a_caption = self.caption_box(a["aciklama"])
        self.a_res = text_layer(a["sonuc"], font("Black", 70), (255, 140, 130))
        self.b1 = text_layer(b["hikaye"][0], font("Bold", 54), WHITE)
        self.b2 = text_layer(b["hikaye"][1], font("Bold", 54), WHITE)
        self.b_res = text_layer(b["sonuc"], font("Black", 70), LIME)
        l1, l2 = cfg["ders"]
        self.l1 = text_layer(l1, font("ExtraBold", 66), SOFT)
        self.l2 = text_layer(l2, font("Black", 120), LIME)
        self.ings = [self.ingredient(k + 1, txt) for k, txt in enumerate(cfg["malzemeler"])]
        self.plain_shade = shade(1050, 600, 200)

    @staticmethod
    def caption_box(text):
        """A bland, typical post caption, like a phone screenshot."""
        f = font("Medium", 38)
        d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
        w = round(d0.textlength(text, font=f)) + 70
        im = Image.new("RGBA", (w, 96), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, 95), radius=22, fill=(255, 255, 255, 235))
        d.text((35, 24), text, font=f, fill=(40, 40, 40))
        return im

    @staticmethod
    def ingredient(n, text):
        w, h = 760, 120
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=60, fill=(10, 40, 18, 235), outline=(70, 120, 60, 255),
                            width=2)
        d.ellipse((22, 18, 106, 102), fill=LIME)
        f = font("Black", 40)
        d.text((64 - d.textlength(str(n), font=f) / 2, 33), str(n), font=f, fill=INK)
        d.text((136, 36), text, font=font("Bold", 42), fill=WHITE)
        return im

    def frame(self, t):
        if t < self.T_A:
            f = self.bg.copy()
            for k, (layer, at) in enumerate(zip(self.hook, self.HOOK_AT)):
                put(f, layer, W / 2, 760 + k * 140, ramp(t, at, at + 0.2), 0.85 + 0.15 * back((t - at) / 0.35))
        elif t < self.T_B:
            lt = t - self.T_A
            i = min(int(lt * FPS), len(self.plain) - 1)
            f = self.plain[i].convert("RGBA")
            f.alpha_composite(self.plain_shade)
            put(f, self.a_pill, 60 + self.a_pill.width / 2, 320, ramp(lt, 0, 0.25))
            put(f, self.a_caption, W / 2, 1220, ramp(lt, 0.5, 0.8))
            if t >= self.A_RESULT:
                put(f, self.a_res, W / 2, 1390, ramp(t, self.A_RESULT, self.A_RESULT + 0.2),
                    0.85 + 0.15 * back((t - self.A_RESULT) / 0.35))
                # a thumb flicking the post away
                p = ease((t - self.A_RESULT - 0.6) / 0.6)
                if p > 0:
                    d = ImageDraw.Draw(f)
                    x, y = W / 2, 1560 - 70 * p  # under the result line, clear of the text
                    d.line([(x, y + 40), (x, y - 20)], fill=WHITE, width=8)
                    d.line([(x - 26, y + 6), (x, y - 20), (x + 26, y + 6)], fill=WHITE, width=8, joint="curve")
        elif t < self.T_LESSON:
            f = self.clip(self.story, t, self.T_B)
            lt = t - self.T_B
            put(f, self.b_pill, 60 + self.b_pill.width / 2, 320, ramp(lt, 0, 0.25))
            put(f, self.b1, W / 2, 1180, ramp(lt, 0.4, 0.7))
            put(f, self.b2, W / 2, 1260, ramp(t, self.B_LINE2, self.B_LINE2 + 0.3))
            if t >= self.B_RESULT:
                put(f, self.b_res, W / 2, 1410, ramp(t, self.B_RESULT, self.B_RESULT + 0.2),
                    0.85 + 0.15 * back((t - self.B_RESULT) / 0.35))
        elif t < self.T_END:
            f = self.bg.copy()
            lt = t - self.T_LESSON
            put(f, self.l1, W / 2, 560, ramp(lt, 0.05, 0.35))
            if t >= self.LESSON2 - 0.02:
                put(f, self.l2, W / 2, 720, ramp(t, self.LESSON2, self.LESSON2 + 0.2),
                    0.85 + 0.15 * back((t - self.LESSON2) / 0.4))
            for k, (card, at) in enumerate(zip(self.ings, self.ING_AT)):
                put(f, card, W / 2 + 100 * (1 - ease((t - at) / 0.4)), 960 + k * 150, ramp(t, at, at + 0.25))
        else:
            f = self.end_scene(t, self.T_END)
        return self.finish(f, t)

    def sound(self):
        ev = [[at, "nota", {"i": k}] for k, at in enumerate(self.HOOK_AT[:2])]
        ev += [[self.HOOK_AT[2], "vurgu", {"i": 0}], [self.T_A, "gecis", {}], [self.T_A + 0.5, "kart", {}],
               [self.A_RESULT, "boom", {}], [self.A_RESULT + 0.6, "kaydir", {}],
               [self.T_B - 0.9, "yukselis", {"sure": 0.9}], [self.T_B, "darbe", {"boy": 0.9}],
               [self.T_B + 0.1, "parilti", {}], [self.B_RESULT, "vurgu", {"i": 1}], [self.T_LESSON, "gecis", {}],
               [self.LESSON2, "darbe", {"boy": 0.9}]]
        ev += [[at, "adim", {"i": k}] for k, at in enumerate(self.ING_AT)]
        ev += [[self.T_END - 0.95, "yukselis", {"sure": 0.95}], [self.T_END - 0.45, "rulo", {"sure": 0.45}],
               [self.T_END, "darbe", {"boy": 1.3}], [self.T_END + 0.1, "parilti", {}],
               [self.T_END + 0.5, "vurgu", {"i": 1}], [self.T_END + 0.9, "pop", {}]]
        # the beat drops with the story video: version A plays over the bare intro pulse
        parts = {"insa": (0.0, self.T_B - 0.12), "drop": self.T_B, "ritim": (self.T_B, self.T_END - 0.5),
                 "son": self.T_END, "kisilma": self.TOTAL - 1.6}
        return {"bolumler": parts, "olaylar": sorted(ev, key=lambda e: e[0])}

    COVER = 2.9


def render(reel, cfg, name):
    raw, music = repo("ivex-icerik", f".{name}-ham.wav"), repo("ivex-icerik", f".{name}-muzik.m4a")
    ses.write(reel.sound(), reel.TOTAL, raw)
    ses.master(raw, music)
    os.remove(raw)
    out = repo(cfg["cikti"])
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", music, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(round(reel.TOTAL * FPS)):
        enc.stdin.write(reel.frame(i / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    os.remove(music)
    reel.frame(reel.COVER).save(repo(cfg["kapak"]), quality=93)
    print("kaydedildi:", cfg["cikti"], "ve", cfg["kapak"])


def main():
    names = [a for a in sys.argv[1:] if a in ("kova", "fark")] or ["kova", "fark"]
    paths = [a for a in sys.argv[1:] if a.endswith(".json")]
    cfg = json.load(open(paths[0] if paths else repo("ivex-icerik", "ayarlar", "kavramlar.json"), encoding="utf-8"))
    for name in names:
        reel = (Kova if name == "kova" else Fark)(cfg[name])
        render(reel, cfg[name], name)


if __name__ == "__main__":
    main()
