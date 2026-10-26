"""IVEX Medya - videolar için müzik ve ses efektleri, tamamen kodla üretilir (telifsiz, IVEX'e ait).

score(plan, sure) bir sahne planından stereo bir müzik çıkarır:
- Giriş: koyu bir zemin sesi ve kalp atışı.
- Gerilim: yükselen bir ses.
- Logo: büyük bir vuruş ("drop").
- Devamı: yarım tempolu bir ritim, son vuruştan sonra yavaşça kısılır.
Yazılar, kartlar ve geçişler için plandaki zamanlarda kısa efektler çalar; böylece müzik görüntüye birebir oturur.
Referans: Rast Creative marka filmi (yaklaşık 128 BPM yarım tempo, baskın alt bas, sahne başlarında vuruş).

Plan: {"bolumler": {...}, "olaylar": [[saniye, tür, {parametreler}], ...]}
"""
import json
import subprocess

import imageio_ffmpeg
import numpy as np
import soundfile as sf

SR = 48000
BPM = 120
BEAT = 60 / BPM
RNG = np.random.default_rng(7)

A1, C2, D2, E2, F1, G1 = 55.0, 65.41, 73.42, 82.41, 43.65, 49.0
# i - VI - III - VII in A minor, one chord per bar
CHORDS = [("Am", A1, (110.0, 130.81, 164.81, 220.0)), ("F", F1, (87.31, 110.0, 130.81, 174.61)),
          ("C", C2, (130.81, 164.81, 196.0, 261.63)), ("G", G1, (98.0, 123.47, 146.83, 196.0))]


# ── building blocks ────────────────────────────────────────────────────────────────────────────────
def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def osc(freq, sec, kind="sine", phase=0.0):
    """Oscillator; `freq` may be an array for glides."""
    n = int(sec * SR)
    f = np.broadcast_to(np.asarray(freq, np.float64), (n,)) if np.ndim(freq) else np.full(n, float(freq))
    ph = 2 * np.pi * np.cumsum(f) / SR + phase
    if kind == "sine":
        return np.sin(ph)
    saw = 2 * ((ph / (2 * np.pi)) % 1.0) - 1
    return saw if kind == "saw" else 2 * np.abs(saw) - 1


def noise(sec, ch=2):
    return RNG.standard_normal((int(sec * SR), ch))


def fft_filter(x, lo=None, hi=None):
    """Static 4th-order-like high/low pass in the frequency domain."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = np.ones_like(f)
    if lo:
        g /= 1 + (lo / np.maximum(f, 1e-3)) ** 4
    if hi:
        g /= 1 + (f / hi) ** 4
    X = np.fft.rfft(x, axis=0)
    return np.fft.irfft(X * (g[:, None] if x.ndim > 1 else g), n=n, axis=0)


def sweep(x, hi_start, hi_end, lo=None, frame=2048):
    """Low pass whose cutoff glides from hi_start to hi_end (overlap-add), for risers and whooshes."""
    mono = x.ndim == 1
    x = x[:, None] if mono else x
    hop, win = frame // 2, np.hanning(frame)
    n = len(x)
    pad = np.vstack([x, np.zeros((frame, x.shape[1]))])
    out, norm = np.zeros_like(pad), np.zeros(len(pad))
    f = np.fft.rfftfreq(frame, 1 / SR)
    starts = list(range(0, n, hop))
    for k, s in enumerate(starts):
        cut = hi_start * (hi_end / hi_start) ** (k / max(1, len(starts) - 1))
        g = 1 / (1 + (f / cut) ** 4)
        if lo:
            g = g / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
        seg = pad[s:s + frame] * win[:, None]
        out[s:s + frame] += np.fft.irfft(np.fft.rfft(seg, axis=0) * g[:, None], n=frame, axis=0) * win[:, None]
        norm[s:s + frame] += win ** 2
    out = (out / np.maximum(norm, 1e-3)[:, None])[:n]
    return out[:, 0] if mono else out


def stereo(mono, pan=0.0, width=0.0):
    """Mono to stereo; width > 0 adds a few ms of offset to one side for space."""
    l, r = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
    s = np.stack([mono * l, mono * r], axis=1)
    if width:
        d = int(width * SR)
        s[d:, 1] = s[:-d, 1].copy()
    return s


def layered(*sigs):
    """Sum stereo signals of different lengths."""
    out = np.zeros((max(len(s) for s in sigs), 2))
    for s in sigs:
        out[: len(s)] += s
    return out


def decay(sec, tau, attack=0.002):
    t = t_axis(sec)
    return np.minimum(t / attack, 1) * np.exp(-t / tau)


# ── instruments ────────────────────────────────────────────────────────────────────────────────────
def kick():
    t = t_axis(0.5)
    body = osc(44 + 120 * np.exp(-t / 0.035), 0.5) * np.exp(-t / 0.26)
    click = fft_filter(noise(0.5, 1)[:, 0], lo=1800) * np.exp(-t / 0.004) * 0.25
    return stereo(np.tanh(1.6 * (body + click)))


def clap():
    t = t_axis(0.45)
    n = fft_filter(noise(0.45), lo=1100, hi=7000)
    env = sum(np.where(t >= o, np.exp(-(t - o) / 0.009), 0) for o in (0, 0.011, 0.023)) + 0.5 * np.exp(-t / 0.14)
    tone = osc(185, 0.45) * np.exp(-t / 0.06) * 0.35
    return n * env[:, None] * 0.55 + stereo(tone)


def hat(open_=False):
    sec = 0.35 if open_ else 0.08
    return fft_filter(noise(sec), lo=7500) * decay(sec, 0.18 if open_ else 0.022)[:, None] * 0.35


def heartbeat():
    t = t_axis(0.3)
    low = osc(58 + 30 * np.exp(-t / 0.02), 0.3) * np.exp(-t / 0.09)
    tick = osc(3200, 0.3) * np.exp(-t / 0.006) * 0.08
    return stereo(low + tick)


def sub_hit(f0=72, f1=31, tau=1.6):
    t = t_axis(tau * 3)
    f = f1 + (f0 - f1) * np.exp(-t / 0.18)
    return stereo(np.tanh(1.4 * osc(f, tau * 3) * decay(tau * 3, tau, 0.004)))


def impact(size=1.0):
    """Cinematic hit: falling sub, a burst of filtered noise, a short metallic ring for the light."""
    sec = 3.2 * size
    t = t_axis(sec)
    out = sub_hit(78, 30, 1.1 * size)[: len(t)]
    out = np.vstack([out, np.zeros((len(t) - len(out), 2))]) if len(out) < len(t) else out
    burst = sweep(noise(sec), 5200, 900) * decay(sec, 0.55 * size, 0.003)[:, None] * 0.55
    ring = sum(stereo(osc(f * (1 + 0.004 * RNG.standard_normal()), sec), p)
               for f, p in ((1567.98, -0.5), (2093.0, 0.4), (2637.0, -0.2), (3520.0, 0.6)))
    ring = ring * decay(sec, 1.2 * size, 0.01)[:, None] * 0.035
    return out * 0.9 + burst + ring


def whoosh(sec=0.42, rising=True):
    """Swell of filtered air that peaks at its end (rising) or starts there."""
    x = noise(sec)
    x = sweep(x, 500, 7000, lo=250) if rising else sweep(x, 7000, 500, lo=250)
    t = t_axis(sec) / sec
    env = (t ** 2.2 if rising else (1 - t) ** 2.2)
    pan = np.linspace(-0.6, 0.6, len(t))
    return x * env[:, None] * np.stack([np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))], axis=1) * 0.5


def riser(sec):
    t = t_axis(sec)
    p = t / sec
    air = sweep(noise(sec), 300, 9000, lo=200) * (p ** 2)[:, None] * 0.45
    tone = osc(220 * 4 ** p, sec, "saw")
    tone = fft_filter(tone, hi=2400) * (p ** 2.5) * 0.12 * (1 + 0.5 * np.sin(2 * np.pi * (4 + 20 * p) * t))
    return air + stereo(tone, 0, 0.012)


def snare_roll(sec):
    """Accelerating claps under the riser."""
    out = np.zeros((int(sec * SR) + SR, 2))
    t, step = 0.0, 0.125
    while t < sec:
        c = clap() * (0.25 + 0.6 * (t / sec) ** 2)
        i = int(t * SR)
        out[i:i + len(c)] += c[: len(out) - i]
        t += step
        step = max(0.03, step * 0.86)
    return out


def pluck(freq):
    sec = 0.9
    t = t_axis(sec)
    x = sum(osc(freq * k, sec) * np.exp(-t / (0.5 / k ** 0.8)) / k for k in range(1, 8))
    return stereo(x * np.minimum(t / 0.003, 1) * 0.28, RNG.uniform(-0.35, 0.35), 0.008)


def blip(freq, sec=0.4):
    t = t_axis(sec)
    x = (osc(freq, sec) + 0.4 * osc(freq * 2, sec)) * np.exp(-t / 0.08)
    return stereo(x * 0.25, 0, 0.006)


def digital():
    out = np.zeros((int(0.5 * SR), 2))
    for k, o in enumerate((0, 0.06, 0.12)):
        b = blip(2400 + 300 * k, 0.2) * 0.6
        i = int(o * SR)
        out[i:i + len(b)] += b
    return out


def shimmer(sec=1.6):
    t = t_axis(sec)
    out = np.zeros((len(t), 2))
    for f in (1760.0, 2217.46, 2637.0, 3520.0, 4434.92):
        out += stereo(osc(f, sec, phase=RNG.uniform(0, 6)) * (1 - np.exp(-t / 0.05)) * np.exp(-t / 0.6),
                      RNG.uniform(-0.8, 0.8))
    return out * 0.05


def tom(freq):
    t = t_axis(0.6)
    x = osc(freq * (1 + 0.6 * np.exp(-t / 0.03)), 0.6) * np.exp(-t / 0.22)
    return stereo(np.tanh(1.5 * x) * 0.7)


def stab(freqs, sec=0.5):
    t = t_axis(sec)
    x = sum(osc(f * d, sec, "saw") for f in freqs for d in (0.997, 1.003))
    x = fft_filter(x, hi=2600) * np.exp(-t / 0.16) * np.minimum(t / 0.004, 1)
    return stereo(x * 0.08, 0, 0.01)


def pad(freqs, sec, hi=1500):
    t = t_axis(sec)
    x = np.zeros((len(t), 2))
    for f in freqs:
        for side, det in ((0, 0.996), (1, 1.004)):
            x[:, side] += osc(f * det, sec, "saw", RNG.uniform(0, 6))
    x = fft_filter(x, hi=hi) * 0.06
    env = np.minimum(t / 0.25, 1) * np.minimum((sec - t) / 0.3, 1)
    return x * env[:, None]


def bass(freq, sec):
    t = t_axis(sec)
    x = 0.8 * osc(freq, sec) + 0.6 * fft_filter(osc(freq, sec, "saw"), hi=420)
    env = np.minimum(t / 0.01, 1) * np.minimum((sec - t) / 0.05, 1)
    return stereo(np.tanh(1.3 * x) * env * 0.55)


def drone(sec):
    t = t_axis(sec)
    x = pad((A1, 82.41, 110.0), sec, hi=520) * 2.2
    wobble = 1 + 0.15 * np.sin(2 * np.pi * 0.25 * t)
    return x * wobble[:, None]


def reverb(x, sec=2.2):
    """Convolution with decaying, darkened stereo noise."""
    n = int(sec * SR)
    t = np.arange(n) / SR
    ir = fft_filter(RNG.standard_normal((n, 2)), hi=5000) * np.exp(-t / (sec / 5))[:, None]
    ir[: int(0.018 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(axis=0))
    m = len(x) + n
    size = 1 << (m - 1).bit_length()
    X = np.fft.rfft(x, size, axis=0)
    out = np.fft.irfft(X * np.fft.rfft(ir, size, axis=0), size, axis=0)[: len(x)]
    return out


# ── arrangement ───────────────────────────────────────────────────────────────────────────────────
class Mix:
    def __init__(self, sec):
        n = int(sec * SR)
        self.music = np.zeros((n, 2))  # ducked by the kick
        self.fx = np.zeros((n, 2))
        self.send = np.zeros((n, 2))

    def add(self, at, sig, gain=1.0, bus="fx", send=0.0):
        i = int(round(at * SR))
        if i >= len(self.fx):
            return
        sig = sig[: len(self.fx) - i] * gain
        getattr(self, bus)[i:i + len(sig)] += sig
        if send:
            self.send[i:i + len(sig)] += sig * send


PLUCK_NOTES = [440.0, 523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.51]
STEP_NOTES = [110.0, 130.81, 146.83, 164.81, 196.0]


def score(plan, sec):
    b = plan["bolumler"]
    mix = Mix(sec + 1)
    kicks = []

    # intro drone up to the drop, the build's pumping bass, then chords from the drop to the end
    mix.add(0, drone(b["drop"] + 0.6) * np.minimum(t_axis(b["drop"] + 0.6) / 1.5, 1)[:, None], 0.9, "music", 0.3)
    t = b["insa"][0]
    while t < b["insa"][1] - 0.05:
        p = (t - b["insa"][0]) / (b["insa"][1] - b["insa"][0])
        mix.add(t, bass(A1, 0.2) * decay(0.2, 0.08, 0.005)[:, None], 0.5 + 0.5 * p, "music")
        t += BEAT / 2
    bar = 2 * BEAT * 2
    t, k = b["drop"], 0
    while t < b["son"] - 1e-6:
        name, root, tones = CHORDS[k % 4]
        mix.add(t, pad(tones, bar + 0.3, 900 if t < b["ritim"][0] else 1300), 2.8, "music", 0.35)
        mix.add(t, bass(root, bar), 0.95, "music")
        t += bar
        k += 1
    mix.add(b["son"], pad((110.0, 164.81, 220.0, 246.94, 329.63), sec - b["son"] + 0.5, 1400), 1.2, "music", 0.5)
    mix.add(b["son"], bass(A1, 2.6) * decay(2.6, 1.2, 0.01)[:, None], 0.9, "music")

    # half-time groove: kick on 1 and the "and" of 2, clap on 3, closed hats on eighths
    t0, t1 = b["ritim"]
    t = t0
    while t < t1 - 1e-6:
        pos = round(((t - b["drop"]) % bar) / (BEAT / 2))  # eighth note within the bar, 0..7
        if pos in (0, 3):
            mix.add(t, kick(), 0.9)
            kicks.append(t)
        if pos == 4:
            mix.add(t, clap(), 0.55, send=0.25)
        mix.add(t, hat(open_=pos == 7), 0.26 if pos % 2 else 0.16)
        t += BEAT / 2

    sounds = {
        "kalp": lambda p: (heartbeat(), 0.8, 0.1),
        "whoosh": lambda p: (whoosh(p.get("sure", 0.42)), 0.55, 0.3),
        "parilti": lambda p: (shimmer(), 0.7, 0.6),
        "dijital": lambda p: (digital(), 0.5, 0.2),
        "boom": lambda p: (layered(sub_hit(64, 34, 0.9), whoosh(0.3, False) * 0.4), 0.9, 0.35),
        "gecis": lambda p: (layered(impact(0.55) * 0.75, kick() * 0.6), 0.85, 0.35),
        "nota": lambda p: (pluck(PLUCK_NOTES[p["i"] % len(PLUCK_NOTES)]), 0.9, 0.45),
        "pop": lambda p: (blip(1760, 0.3) + blip(2637, 0.3) * 0.5, 0.6, 0.3),
        "darbe": lambda p: (impact(p.get("boy", 1.0)), 1.0, 0.45),
        "adim": lambda p: (layered(tom(STEP_NOTES[p["i"] % 5]), blip(STEP_NOTES[p["i"] % 5] * 8, 0.25) * 0.5), 0.8,
                           0.3),
        "kaydir": lambda p: (whoosh(0.3), 0.32, 0.2),
        "kart": lambda p: (tom(98.0) * 0.5, 0.55, 0.15),
        "vurgu": lambda p: (stab([f * (1.5 if p["i"] % 2 else 1) for f in CHORDS[0][2]]), 0.9, 0.35),
    }
    for at, kind, params in plan["olaylar"]:
        if kind == "yukselis":
            mix.add(at, riser(params["sure"]), 0.8, send=0.2)
        elif kind == "rulo":
            mix.add(at, snare_roll(params["sure"]), 0.45, send=0.2)
        else:
            sig, gain, send = sounds[kind](params)
            # a whoosh is built to peak at its end: start it early so the peak lands on the cue
            start = at - len(sig) / SR if kind in ("whoosh", "kaydir") else at
            mix.add(start, sig, gain, send=send)

    # sidechain: the music bus dips under every kick and big hit
    duck = np.ones(len(mix.music))
    t = np.arange(len(duck)) / SR
    for kt in kicks + [at for at, kind, _ in plan["olaylar"] if kind in ("darbe", "gecis")]:
        i = int(kt * SR)
        seg = t[i:i + int(0.4 * SR)] - kt
        duck[i:i + len(seg)] = np.minimum(duck[i:i + len(seg)], 1 - 0.45 * np.exp(-seg / 0.12))
    out = mix.music * duck[:, None] + mix.fx + reverb(mix.send) * 0.6
    # warm tilt like the reference (spectral centroid ~1 kHz): pull the top end down, keep the lows
    out = 0.4 * out + 0.6 * fft_filter(out, hi=2600)
    # drop the drones to silence just before the drop, so the hit lands out of a breath
    gap = (t >= b["drop"] - 0.12) & (t < b["drop"])
    out[gap] *= np.linspace(1, 0, gap.sum())[:, None] if gap.any() else 1
    fade = np.clip((sec - t) / max(1e-3, sec - b["kisilma"]), 0, 1)
    out *= fade[:, None]
    return np.tanh(out[: int(sec * SR)] * 0.9)


def master(wav, out_m4a_or_wav):
    """Two-pass EBU R128 loudness to -14 LUFS (Instagram) with a -1.5 dBTP ceiling."""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    probe = subprocess.run([ff, "-hide_banner", "-i", wav, "-af",
                            "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(probe[probe.rindex("{"):probe.rindex("}") + 1])
    af = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:"
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", wav, "-af", af, "-ar", str(SR), out_m4a_or_wav],
                   check=True)


def write(plan, sec, path):
    sf.write(path, score(plan, sec).astype(np.float32), SR)
