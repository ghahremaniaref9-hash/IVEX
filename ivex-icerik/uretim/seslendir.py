"""IVEX Medya - yerel Türkçe seslendirme: bir ayar dosyasındaki "satirlar"ı WAV olarak üretir.

Kullanım:  python3 seslendir.py ../ayarlar/goz-testi.json SHERPA_KLASORU MODELLER_KLASORU
Motor: sherpa-onnx 1.x (2.x sürümünde Türkçe için gereken espeak çıkarıldı). Kurulum:
    pip install --target SHERPA_KLASORU "sherpa-onnx<2"
Ses modeli: github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models içindeki
    vits-piper-tr_TR-dfki-medium.tar.bz2, MODELLER_KLASORU içine açılır.
Üretilen dosyalar depoda saklanır (ses_klasoru); videoyu yeniden kurmak için bu adım tekrar gerekmez.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

from marka import repo


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    sys.path.insert(0, sys.argv[2])
    import sherpa_onnx

    model = os.path.join(sys.argv[3], cfg["ses_modeli"])
    name = cfg["ses_modeli"].replace("vits-piper-", "")
    tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=f"{model}/{name}.onnx", tokens=f"{model}/tokens.txt",
                                                   data_dir=f"{model}/espeak-ng-data"), num_threads=4)))
    out_dir = repo(cfg["ses_klasoru"])
    os.makedirs(out_dir, exist_ok=True)
    for line in cfg["satirlar"]:
        a = tts.generate(line["metin"], sid=0, speed=line["hiz"])
        x = np.array(a.samples, np.float32)
        path = os.path.join(out_dir, line["ad"] + ".wav")
        sf.write(path, x, a.sample_rate)
        print(f"kaydedildi: {path} ({len(x) / a.sample_rate:.2f} sn)  {line['metin']}")


if __name__ == "__main__":
    main()
