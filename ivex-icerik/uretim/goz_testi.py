"""IVEX Medya - "Göz testi" Reels'i (1080x1920, 22 sn): reklam gibi başlamayan, sonda ajansa dönen video.

Kullanım:  python3 goz_testi.py ../ayarlar/goz-testi.json
Kurgu (Rast Creative'in bukalemun videosunun mantığı, IVEX'e özgü içerikle):
- Bir göz testi: gri sürünün ortasında lime renkli tek bir koyun. Liste: gri – normal, beyaz – gözlük zamanı,
  yeşil – çok geç. Herkes önce yeşil koyunu görür, yani herkes "çok geç" grubundadır.
- Sert kesme: koyun kameraya döner ve kalın bir sesle konuşur. Asıl mesaj burada çıkar: sürüde fark edilen
  hep farklı olandır; işletmen de öyle fark edilsin mi? DM'den YEŞİL yaz.
- Sonda lime nokta IVEX logosundaki X'e dönüşür. Logo yalnızca burada görünür: izleyici sona kadar bunun bir
  ajans videosu olduğunu anlamaz.
Seslendirme seslendir.py ile üretilip ses_klasoru'nde durur. Koyunun sesi anlatıcının kalınlaştırılmış hâli.
Müzik ve efektler ses.py'den, yazılar konuşmanın ölçülmüş zamanlarına göre çıkar.
"""
import json
import math
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter

import ses
from marka import INK, LIME, SOFT, WHITE, font, logo, pill, repo, tracked, write_video
from marka_filmi import clamp, ease, ease_io, glow, put, text_img

W, H, FPS = 1080, 1920, 30
GREY = (176, 180, 176)
SHADOW = (0, 0, 0)


def shadowed(layer, blur=14, strength=0.75):
    """Text layer with a soft dark halo so it reads over a bright, misty photo."""
    pad = blur * 2
    out = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, SHADOW + (0,))
    a = Image.new("L", out.size, 0)
    a.paste(layer.getchannel("A"), (pad, pad))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: round(v * strength)))
    out.alpha_composite(sh)
    out.alpha_composite(layer, (pad, pad))
    return out


def baseline_img(text, fnt, fill):
    """One line on a fixed ascent/descent box, so pieces set side by side share the same baseline."""
    asc, desc = fnt.getmetrics()
    im = Image.new("RGBA", (round(fnt.getlength(text)) + 8, asc + desc + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, asc + 4), text, font=fnt, fill=fill, anchor="ls")
    return im


def pop(canvas, layer, cx, y, lt, start, end=None):
    """Pop in (scale 1.12 -> 1 with fade) at `start`, cut out at `end`."""
    if lt < start or (end is not None and lt >= end):
        return
    p = ease((lt - start) / 0.14)
    put(canvas, layer, cx, y, p, scale=1.12 - 0.12 * p)


def words(lines, size, colors, max_w=960):
    """Stacked heavy lines, each shrunk to fit max_w; returns one RGBA layer."""
    imgs = []
    for line, col in zip(lines, colors):
        s = size
        while font("Black", s).getlength(line) > max_w:
            s -= 4
        imgs.append(text_img(line, font("Black", s), col))
    gap = round(size * 0.08)
    out = Image.new("RGBA", (max(i.width for i in imgs), sum(i.height for i in imgs) + gap * (len(imgs) - 1)),
                    (0, 0, 0, 0))
    y = 0
    for im in imgs:
        out.alpha_composite(im, ((out.width - im.width) // 2, y))
        y += im.height + gap
    return out


class GozTesti:
    def __init__(self, cfg):
        self.cfg = cfg
        self.suru = Image.open(repo(cfg["gorsel_suru"])).convert("RGB")
        self.yakin = Image.open(repo(cfg["gorsel_yakin"])).convert("RGB")
        lg = logo(180)
        arr = np.asarray(lg).copy()
        is_x = (arr[..., 2] < 140) & (arr[..., 1] > 150)
        xs, ive = arr.copy(), arr.copy()
        xs[~is_x, 3] = 0
        ive[is_x, 3] = 0
        self.logo, self.logo_x, self.logo_ive = lg, Image.fromarray(xs, "RGBA"), Image.fromarray(ive, "RGBA")
        cols, rows = np.where(is_x.any(axis=0))[0], np.where(is_x.any(axis=1))[0]
        self.x_box = (cols[0], rows[0], cols[-1] + 1, rows[-1] + 1)
        self.lime_glow = glow((900, 900), LIME, 330, 0.55)
        self.texts = {}

    def photo(self, im, zoom, focus):
        """Push-in on `focus` (fractions of the image), filling the frame."""
        iw, ih = im.size
        s = max(W / iw, H / ih) * zoom
        cw, ch = W / s, H / s
        x0 = clamp(focus[0] * iw - cw / 2, 0, iw - cw)
        y0 = clamp(focus[1] * ih - ch / 2, 0, ih - ch)
        return im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert("RGBA")

    def text(self, item):
        key = id(item)
        if key in self.texts:
            return self.texts[key]
        kind = item["tur"]
        if kind == "baslik":
            out = shadowed(text_img(item["metin"], font("Black", 118)))
        elif kind == "alt":
            out = shadowed(text_img(item["metin"], font("SemiBold", 40)), 10)
        elif kind == "liste":
            col = {"GRİ": GREY, "BEYAZ": WHITE, "YEŞİL": LIME}[item["renk"]]
            a = baseline_img(item["metin"], font("ExtraBold", 54), col)
            b = baseline_img(item["sonuc"], font("ExtraBold", 54), WHITE)
            out = (shadowed(a, 10), shadowed(b, 10), a.width + 34)
        else:
            lines = item["metin"]
            colors = [LIME if item.get("lime") else WHITE] * len(lines)
            if kind == "dm":
                colors = [WHITE, LIME, WHITE]
                out = [shadowed(words([l], 150, [c])) for l, c in zip(lines, colors)]
            else:
                out = shadowed(words(lines, 132, colors))
                if item.get("ek"):
                    ek = shadowed(text_img(item["ek"], font("SemiBold", 46)), 10)
                    both = Image.new("RGBA", (max(out.width, ek.width), out.height + ek.height - 30), (0, 0, 0, 0))
                    both.alpha_composite(out, ((both.width - out.width) // 2, 0))
                    both.alpha_composite(ek, ((both.width - ek.width) // 2, out.height - 30))
                    out = both
        self.texts[key] = out
        return out

    def frame(self, t):
        cfg = self.cfg
        cut, end_at = cfg["kesme"], cfg["logo"]
        if t < cut:
            # slow push-in, quicker over the last second as the lime sheep is singled out
            z = 1.0 + 0.06 * (t / cut) + 0.16 * ease_io((t - (cut - 1.2)) / 1.2)
            im = self.photo(self.suru, z, cfg["odak"])
        elif t < end_at:
            lt = t - cut
            z = 1.0 + 0.07 * lt / (end_at - cut) + 0.14 * (1 - ease(lt / 0.3))  # punch in on the cut
            im = self.photo(self.yakin, z, (0.5, 0.42))
        else:
            return self.ending(t - end_at)
        # darken the top so the text sits on it
        im.alpha_composite(self.top_shade())
        for item in cfg["yazilar"]:
            if not (item["t"] <= t < item["bitis"]):
                continue
            kind = item["tur"]
            if kind == "baslik":
                pop(im, self.text(item), W / 2, 150, t, item["t"])
            elif kind == "alt":
                pop(im, self.text(item), W / 2, 300, t, item["t"])
            elif kind == "liste":
                a, b, w = self.text(item)
                total = w + b.width - 2 * 10
                x0 = W / 2 - total / 2
                y = 380 + item["satir"] * 82
                pop(im, a, x0 + a.width / 2, y, t, item["t"])
                if t >= item["sonuc_t"]:
                    pop(im, b, x0 + w + b.width / 2 - 20, y, t, item["sonuc_t"])
            elif kind == "dm":
                y = 170
                for layer, at in zip(self.text(item), item["zamanlar"]):
                    pop(im, layer, W / 2, y, t, at)
                    y += layer.height - 50
            else:
                pop(im, self.text(item), W / 2, 170, t, item["t"])
        return im

    def top_shade(self):
        if not hasattr(self, "_shade"):
            a = np.zeros((H, W), np.float32)
            y = np.arange(H)[:, None]
            a += np.clip(1 - y / 820, 0, 1) ** 1.6 * 150
            a += np.clip((y - 1500) / 420, 0, 1) ** 2 * 120
            sh = np.zeros((H, W, 4), np.uint8)
            sh[..., 3] = np.broadcast_to(a, (H, W)).astype(np.uint8)
            self._shade = Image.fromarray(sh, "RGBA")
        return self._shade

    def ending(self, lt):
        """Black; a lime dot appears, swells into the X of the logo, IVE slides in, then the call to action."""
        im = Image.new("RGBA", (W, H), (4, 10, 6, 255))
        lw, lh = self.logo.size
        lx, ly = (W - lw) // 2, 820
        x0, y0, x1, y1 = self.x_box
        xc, yc = lx + (x0 + x1) / 2, ly + (y0 + y1) / 2
        put(im, self.lime_glow, xc, yc - 450, 0.15 + 0.55 * ease((lt - 0.55) / 0.5))
        dot_r = 14 * ease(lt / 0.12)
        grow = ease_io((lt - 0.5) / 0.35)
        if grow < 1 and dot_r > 0:
            r = dot_r + grow * 60
            d = ImageDraw.Draw(im)
            d.ellipse((xc - r, yc - r, xc + r, yc + r), fill=LIME + (round(255 * (1 - grow)),))
        if grow > 0:
            put(im, self.logo_x.crop(self.x_box), xc, ly + y0, grow, scale=0.6 + 0.4 * grow)
        wipe = ease((lt - 0.75) / 0.45)
        if wipe > 0:
            ive = self.logo_ive.crop((0, 0, x0, lh))
            vis = round(ive.width * wipe)
            if vis > 0:
                im.alpha_composite(ive.crop((ive.width - vis, 0, ive.width, lh)), (lx + x0 - vis, ly))
        sub = Image.new("RGBA", (W, 50), (0, 0, 0, 0))
        tracked(ImageDraw.Draw(sub), (W / 2, 6), self.cfg["son"]["unvan"], font("Bold", 28), SOFT, 9, anchor="m")
        put(im, sub, W / 2, ly + lh + 60, ease((lt - 1.3) / 0.4))
        btn = Image.new("RGBA", (W, 100), (0, 0, 0, 0))
        pill(ImageDraw.Draw(btn), W / 2, 10, self.cfg["son"]["buton"], font("ExtraBold", 32), LIME, INK, pad_x=38,
             h=80, tracking=2, anchor="m")
        p = ease((lt - 1.7) / 0.35)
        put(im, btn, W / 2, ly + lh + 170 + (1 - p) * 20, p)
        return im


# ── ses ─────────────────────────────────────────────────────────────────────────────────────────────
VOICE_FX = {
    # anlatıcı: temiz, hafif sıkıştırılmış
    "anlatici": "aresample=48000,highpass=f=90,acompressor=threshold=-20dB:ratio=3:attack=5:release=90,volume=3dB",
    # koyun: ~4 yarım ton kalın, kısa yankılı, biraz sert
    "koyun": "asetrate=22050*0.8,aresample=48000,atempo=1.25,highpass=f=70,"
             "acompressor=threshold=-22dB:ratio=4:attack=3:release=80,aecho=0.8:0.55:35|62:0.22|0.14,volume=7dB",
}


def voice_track(cfg, sec, tmp_dir):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    out = np.zeros((int(sec * ses.SR), 2))
    for line in cfg["satirlar"]:
        src = os.path.join(repo(cfg["ses_klasoru"]), line["ad"] + ".wav")
        dst = os.path.join(tmp_dir, line["ad"] + "-islenmis.wav")
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", src, "-af", VOICE_FX[line["kim"]], "-ac", "2", dst],
                       check=True)
        x, _ = sf.read(dst, dtype="float32")
        os.remove(dst)
        # every line at the same speaking level (-16 dBFS RMS over its voiced part), well above the music
        voiced = np.abs(x).mean(axis=1) > 0.01
        x = x * (10 ** (-16 / 20) / np.sqrt((x[voiced] ** 2).mean()))
        i = int(line["basla"] * ses.SR)
        x = x[: len(out) - i]
        out[i:i + len(x)] += x
    return out


def score(cfg, sec, voice):
    cut, logo_at = cfg["kesme"], cfg["logo"]
    mix = ses.Mix(sec + 1)
    # before the cut: a calm, slightly uneasy bed with a heartbeat that speeds up
    bed = ses.drone(cut + 0.3) * np.minimum(ses.t_axis(cut + 0.3) / 1.2, 1)[:, None]
    mix.add(0, bed, 0.5, "music", 0.2)
    t, step = 0.2, 0.75
    while t < cut - 0.2:
        mix.add(t, ses.heartbeat(), 0.55 if t < 5.5 else 0.8)
        t += step
        step = max(0.32, step * (0.97 if t < 5.5 else 0.88))
    for item in cfg["yazilar"]:
        if item["tur"] == "liste":
            mix.add(item["t"], ses.blip(880 + 220 * item["satir"], 0.3), 0.35)
    green = next(i for i in cfg["yazilar"] if i["tur"] == "liste" and i["renk"] == "YEŞİL")
    mix.add(green["sonuc_t"], ses.layered(ses.sub_hit(66, 34, 0.7)), 0.8, send=0.3)
    mix.add(cut - 1.0, ses.riser(0.92), 0.7, send=0.2)
    # the cut: big hit, then a low, detuned and wavering bed under the sheep
    mix.add(cut, ses.impact(0.9), 0.95, send=0.35)
    n = logo_at - cut + 0.4
    low = ses.pad((55.0, 58.27, 82.41), n, hi=420) * 2.6
    wav = 1 + 0.25 * np.sin(2 * np.pi * 3.2 * ses.t_axis(n))
    mix.add(cut, low * wav[:, None] * np.minimum(ses.t_axis(n) / 0.6, 1)[:, None], 0.45, "music", 0.3)
    big = [i for i in cfg["yazilar"] if i["tur"] == "buyuk" and i["metin"] in (["ÇOK GEÇ"],)]
    for item in big:
        mix.add(item["t"], ses.layered(ses.sub_hit(70, 32, 0.8)), 0.75, send=0.3)
    mix.add(logo_at - 0.7, ses.riser(0.62), 0.55, send=0.2)
    # the ending: dot, then the logo hit and a long chord
    mix.add(logo_at + 0.05, ses.blip(1760, 0.3), 0.4, send=0.3)
    mix.add(logo_at + 0.5, ses.impact(1.0), 0.95, send=0.45)
    mix.add(logo_at + 0.5, ses.pad((110.0, 164.81, 220.0, 246.94, 329.63), sec - logo_at, 1300), 1.1, "music", 0.4)
    mix.add(logo_at + 0.6, ses.shimmer(), 0.7, send=0.5)

    t = np.arange(len(mix.music)) / ses.SR
    # duck the music under the voice
    v = np.abs(voice).mean(axis=1)
    k = int(0.08 * ses.SR)
    c = np.cumsum(np.concatenate([[0.0], v]))
    env = np.pad((c[k:] - c[:-k]) / k, (k // 2, 0))[: len(mix.music)]  # 80 ms moving average
    env = np.pad(env, (0, len(mix.music) - len(env)))
    duck = 1 - 0.6 * np.clip(env / 0.03, 0, 1)
    # everything but the voice steps back while someone speaks
    out = (mix.music + mix.fx + ses.reverb(mix.send) * 0.55) * duck[:, None]
    out = 0.45 * out + 0.55 * ses.fft_filter(out, hi=2800)
    for gap_end in (cut, logo_at + 0.05):  # a breath of silence right before each hit
        g = (t >= gap_end - 0.1) & (t < gap_end)
        out[g] *= np.linspace(1, 0.05, g.sum())[:, None]
    out = out[: len(voice)] + voice
    fade = np.clip((sec - t[: len(out)]) / 1.2, 0, 1)
    return np.tanh(out * fade[:, None] * 0.9)


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    film = GozTesti(cfg)
    if len(sys.argv) > 2:  # stills for a quick look: python3 goz_testi.py cfg.json 2.5 8 ...
        for arg in sys.argv[2:]:
            out = repo(f"ivex-icerik/onizleme-goz-{float(arg):05.2f}.jpg")
            film.frame(float(arg)).convert("RGB").save(out, quality=88)
            print("önizleme:", out)
        return
    sec = cfg["sure"]
    out = repo(cfg["cikti"])
    silent, raw, music = (out.replace(".mp4", s) for s in ("-sessiz.mp4", "-ham.wav", "-ses.wav"))
    write_video((film.frame(i / FPS).convert("RGB") for i in range(round(sec * FPS))), silent, (W, H), FPS)
    voice = voice_track(cfg, sec, os.path.dirname(out))
    sf.write(raw, score(cfg, sec, voice).astype(np.float32), ses.SR)
    ses.master(raw, music)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", silent, "-i", music,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    for tmp in (silent, raw, music):
        os.remove(tmp)
    print("kaydedildi:", out)
    cover_at = next(i for i in cfg["yazilar"] if i["tur"] == "liste" and i["renk"] == "YEŞİL")["sonuc_t"] + 0.6
    film.frame(cover_at).convert("RGB").save(repo(cfg["kapak"]), quality=92)
    print("kaydedildi:", repo(cfg["kapak"]))


if __name__ == "__main__":
    main()
