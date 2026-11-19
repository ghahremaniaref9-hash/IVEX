"""IVEX Medya - vitrin, delikli kova ve iki senaryo Reels'lerinin seslendirmeli sürümleri.

Kullanım:  python3 anlatim.py [vitrin|kova|fark]   (ad verilmezse üçü de üretilir)
Seslendirme cümleleri ayarlar/seslendirme.json'da, her cümle bir sahneye ait; ses dosyaları
kaynak/seslendirme/<ses>/NN.mp3 (Higgsfield, ElevenLabs). Ses hızlandırılmaz, görüntü sese uydurulur:
cümlesi sahneye sığmayan sahne, cümle bitene kadar orantılı uzatılır (sahnedeki animasyonlar aynı oranda
yavaşlar, video klipler kare harmanlanarak akıcı kalır). Müzik ve efektler yeni zaman çizelgesiyle yeniden
üretilir, konuşma sırasında müzik kısılır; ses -14 LUFS'a getirilir ve tepeler sınırlanır.
Ekrandaki yazılar aynen kalır, video sessiz izlense de anlaşılır.
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kavramlar  # noqa: E402
import ses  # noqa: E402
import vitrin  # noqa: E402
from marka import repo  # noqa: E402

FF, FPS, W, H, SR = vitrin.FF, vitrin.FPS, vitrin.W, vitrin.H, ses.SR
TAIL = 0.4          # pause after a sentence before the next scene starts
VOICE_RMS = 0.12    # every sentence at the same level
MUSIC_RMS = 0.075   # music bed level between sentences
DUCK = 0.38         # music gain while someone speaks (about -8.4 dB)


def scenes(name):
    if name == "vitrin":
        return [0.0, vitrin.T_PROBLEM, vitrin.T_METHOD, vitrin.T_WORK, vitrin.T_SERV, vitrin.T_END, vitrin.TOTAL]
    if name == "kova":
        k = kavramlar.Kova
        return [0.0, k.T_HOLES, k.T_PROB, k.T_FIX, k.T_END, k.TOTAL]
    k = kavramlar.Fark
    return [0.0, k.T_A, k.T_B, k.T_LESSON, k.T_END, k.TOTAL]


def load_voice(path):
    raw = subprocess.run([FF, "-loglevel", "error", "-i", path, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    loud = np.nonzero(np.abs(x).max(axis=1) > 0.01)[0]       # -40 dBFS
    x = x[max(0, loud[0] - int(0.02 * SR)): loud[-1] + int(0.08 * SR)]
    fade = np.minimum(1, np.arange(len(x))[::-1] / (0.03 * SR))
    x = x * fade[:, None]
    return x * (VOICE_RMS / (np.sqrt(np.mean(x[np.abs(x).max(axis=1) > 0.01] ** 2)) + 1e-9))


class Warp:
    """Piecewise-linear map between the original (visual) timeline and the stretched (output) one."""

    def __init__(self, old, new):
        self.old, self.new = np.array(old, float), np.array(new, float)

    def to_visual(self, t):
        return float(np.interp(t, self.new, self.old))

    def to_output(self, t):
        return float(np.interp(t, self.old, self.new))


def plan(name):
    """Stretch each scene that its sentence overruns; return the warp, the voice clips and their output times."""
    vcfg = json.load(open(repo("ivex-icerik", "ayarlar", "seslendirme.json"), encoding="utf-8"))
    voice_dir = repo("ivex-icerik", "kaynak", "seslendirme", vcfg["ses"]["ad"].lower())
    order = list(vcfg["videolar"])
    first = sum(len(vcfg["videolar"][n]["satirlar"]) for n in order[: order.index(name)])
    lines = vcfg["videolar"][name]["satirlar"]
    old = scenes(name)
    assert len(lines) == len(old) - 1, f"{name}: {len(lines)} cümle, {len(old) - 1} sahne"
    clips, new = [], [0.0]
    for k, (start, _slot, text) in enumerate(lines):
        clip = load_voice(os.path.join(voice_dir, f"{first + k:02d}.mp3"))
        offset = start - old[k]
        length = max(old[k + 1] - old[k], offset + len(clip) / SR + TAIL)
        clips.append((new[-1] + offset, clip))
        print(f"  sahne {k + 1}: {old[k + 1] - old[k]:.2f} -> {length:.2f} sn  | {text}")
        new.append(new[-1] + length)
    return Warp(old, new), clips, vcfg["videolar"][name]


def warp_sound_plan(p, warp):
    ev = []
    for t, kind, par in p["olaylar"]:
        if kind in ("yukselis", "rulo"):  # a build-up keeps its length and still lands on its hit
            ev.append([warp.to_output(t + par["sure"]) - par["sure"], kind, dict(par)])
        else:
            ev.append([warp.to_output(t), kind, dict(par)])
    b = p["bolumler"]
    parts = {"insa": tuple(map(warp.to_output, b["insa"])), "drop": warp.to_output(b["drop"]),
             "ritim": tuple(map(warp.to_output, b["ritim"])), "son": warp.to_output(b["son"]),
             "kisilma": warp.to_output(b["kisilma"])}
    return {"bolumler": parts, "olaylar": sorted(ev, key=lambda e: e[0])}


def mix(music, clips, total):
    n = int(total * SR)
    music = music[:n] * (MUSIC_RMS / (np.sqrt(np.mean(music[:n] ** 2)) + 1e-9))
    voice = np.zeros((n, 2))
    for at, clip in clips:
        i = int(at * SR)
        j = min(n, i + len(clip))
        voice[i:j] += clip[: j - i]
    # speech gate on 10 ms frames, held through short pauses, then smoothed (soft attack and release)
    hop = int(0.01 * SR)
    frames = np.abs(voice[: n // hop * hop]).max(axis=1).reshape(-1, hop).max(axis=1) > 0.01
    gate = np.convolve(frames, np.ones(45), mode="same") > 0                 # hold about 0.22 s each side
    gate = np.convolve(gate.astype(float), np.ones(15) / 15, mode="same")    # 0.15 s ramps
    gain = np.interp(np.arange(n), np.arange(len(gate)) * hop, 1 - (1 - DUCK) * gate)
    return music * gain[:, None] + voice


def smooth_clip(self, frames, t, start):
    """Base.clip with blending between neighbouring frames, so a slowed clip does not stutter."""
    x = max(0.0, (t - start) * FPS)
    i = min(int(x), len(frames) - 1)
    j, a = min(i + 1, len(frames) - 1), x - int(x)
    f = frames[i] if a < 0.05 or i == j else Image.blend(frames[i].convert("RGB"), frames[j].convert("RGB"), a)
    f = f.convert("RGBA")
    f.alpha_composite(self.shade)
    return f


kavramlar.Base.clip = smooth_clip


def render(name):
    print(f"{name}:")
    warp, clips, vcfg = plan(name)
    total = warp.new[-1]
    if name == "vitrin":
        cfg = json.load(open(repo("ivex-icerik", "ayarlar", "vitrin.json"), encoding="utf-8"))
        reel, p = vitrin.Reel(cfg), vitrin.sound_plan(cfg)
    else:
        cfg = json.load(open(repo("ivex-icerik", "ayarlar", "kavramlar.json"), encoding="utf-8"))[name]
        reel = (kavramlar.Kova if name == "kova" else kavramlar.Fark)(cfg)
        p = reel.sound()
    audio = mix(ses.score(warp_sound_plan(p, warp), total), clips, total)
    raw, loud, final = (repo("ivex-icerik", f".{name}-anlatim{s}") for s in (".wav", "-yuksek.wav", ".m4a"))
    sf.write(raw, (audio / max(1e-6, np.abs(audio).max()) * 0.9).astype(np.float32), SR)
    ses.master(raw, loud)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", loud, "-af",
                    "alimiter=limit=0.74:level=false,afade=t=in:d=0.03", "-c:a", "aac", "-b:a", "192k", final],
                   check=True)
    out = repo(vcfg["cikti"])
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", final, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    count = round(total * FPS)
    for i in range(count):
        enc.stdin.write(reel.frame(warp.to_visual(i / FPS)).tobytes())
        if i % 150 == 0:
            print(f"  kare {i}/{count}", flush=True)
    enc.stdin.close()
    enc.wait()
    for f in (raw, loud, final):
        os.remove(f)
    print(f"  kaydedildi: {vcfg['cikti']} ({total:.1f} sn)")


def main():
    for name in [a for a in sys.argv[1:] if a in ("vitrin", "kova", "fark")] or ["vitrin", "kova", "fark"]:
        render(name)


if __name__ == "__main__":
    main()
