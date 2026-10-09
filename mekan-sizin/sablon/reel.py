"""Mekan Sizin - metinsiz fotoğraftan sessiz Reels videosu (1080x1920, yavaş yakınlaşma + film greni).

Kullanım:  python3 reel.py kaynak.jpg cikti.mp4 [saniye]
Ses eklenmez: Instagram'da trend bir müzik seçmek erişimi artırır.
"""
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image

from foto import crop_to, grade

W, H, FPS = 1080, 1920, 30


def main():
    src, dst = sys.argv[1], sys.argv[2]
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 7.0
    base = grade(crop_to(Image.open(src).convert("RGB"), (W + 120, H + 214)))  # margin for the zoom
    bw, bh = base.size
    frames = round(secs * FPS)
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "slow", "-crf", "23", "-movflags", "+faststart", dst]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    rng = np.random.default_rng(7)
    # A small pool of grain plates, switched every 2 frames: looks like film, compresses far better
    grain_pool = [rng.normal(0, 3.5, (H, W)).astype(np.float32)[..., None] for _ in range(6)]
    for i in range(frames):
        t = i / max(1, frames - 1)
        e = t * t * (3 - 2 * t)  # ease in-out
        z = 1.0 + 0.10 * e
        cw, ch = W * (bw / W) / z, H * (bh / H) / z
        cx, cy = bw / 2, bh / 2 - 40 * e
        frame = base.crop((cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).resize((W, H), Image.BICUBIC)
        arr = np.asarray(frame).astype(np.float32)
        arr += grain_pool[(i // 2) % len(grain_pool)]
        proc.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    print("kaydedildi:", dst, f"({secs:.0f} sn)")


if __name__ == "__main__":
    main()
