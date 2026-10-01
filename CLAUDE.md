# IVEX Lead Finder

Sektör + bölge bazında Google Places API (New) ile esnaf listesi çıkarır, her
işletmenin website'ini kontrol edip "aranmalı mı?" önceliği atar. Kullanıcı
Türkçe konuşur; yanıtlar ve kullanıcıya görünen metinler Türkçe olmalı.

## İki sürüm var

- `lead_finder.py` — Python CLI sürümü. Config: `config.json`
  (`config.example.json`'dan kopyalanır), API anahtarı `.env` içinde
  `GOOGLE_MAPS_API_KEY`. Çıktı CSV.
- `sheets-version/Code.gs` — Google Apps Script sürümü (Google Sheets içinde
  çalışır, terminal gerekmez). Ayarlar "Ayarlar" sayfasından okunur, sonuçlar
  sektör başına ayrı sayfaya yazılır, `_Görülenler` sayfası tekrarları engeller.
  Bu dosya yerelde çalıştırılamaz; değişiklikler kullanıcı tarafından Apps Script
  editörüne yapıştırılır.

## Komutlar

```
pip install -r requirements.txt
python3 lead_finder.py --config config.example.json --dry-run --out ornek.csv   # API anahtarı olmadan test
python3 lead_finder.py --config config.json                                     # gerçek çalıştırma (API kotası harcar)
```

Windows'ta `python3` yerine `python` kullanılır.

## Kurallar

- Değişiklikten sonra `--dry-run` ile test et; gerçek API çağrısı yapan komutu
  kullanıcı istemeden çalıştırma (ücretli kota).
- `.env`, `config.json` ve `*.csv` git'e girmez (`.gitignore`); API anahtarını
  asla commit'leme veya ekrana yazdırma.
- Python ve Apps Script sürümleri aynı mantığı paylaşır (website kontrolü,
  sosyal medya tespiti, öncelik puanı). Birinde mantık değişirse diğerinin de
  güncellenmesi gerekip gerekmediğini kullanıcıya sor.
