# Mekan Sizin – maç günü şablonları

İki şablon var. İkisi de 1080 px genişliğinde Instagram gönderisi üretir ve logoda **bira/rakı yoktur** (siyah plakalı "MEKAN SİZİN" logosu).

## Şablon 1 – "Maç Günü Beşiktaş'ta!" (ChatGPT tasarımı)

- Taban: `assets/sablon1-taban.webp` (1122×1402). Alttaki yazı silinip yerine plaka logo konur.
- `sablon1.json` içinde `"mod"`:
  - `"birebir"`: sadece logo değişir, geri kalan tek piksel bile değişmez.
  - `"ekli"`: logonun üstüne tarih/saat etiketi ve altına adres eklenir.
- **Sınır:** Takım adları ve armalar taban görselin içine işlenmiş (Beşiktaş JK – Kocaelispor). Başka rakip için bu şablon uygun değil; onun yerine Şablon 2'yi kullanın.

```
python3 logo_degistir.py sablon1.json
```

## Şablon 2 – "Maç Bileti" (her maç için tekrar kullanılabilir)

- Gerçek stadyum fotoğrafı (siyah-beyaz, grenli), kâğıt dokulu eğik bir maç bileti, mürekkep izli "CANLI YAYIN" damgası ve el yazısı notlar.
- Her şey `mac-bileti.json` dosyasından okunur. Yeni maç için değiştirilecekler:
  - `deplasman.ad` ve `deplasman.arma` (rakibin armasını PNG olarak `assets/` içine koyun, arka planı şeffaf olsun)
  - `ust_satir`, `tarih`, `saat`, `cikti`
  - İstenirse: `tribun`, `el_yazisi_baslik`, `el_yazisi_alt`, `alt_baslik`, `alt_metin`, `adres`

```
python3 mac_bileti.py mac-bileti.json
```

## Gereken paketler

`pip install pillow numpy opencv-python-headless`

## Klasörler

- `assets/`: plaka logo, orijinal logo, armalar, stadyum fotoğrafı, Şablon 1 tabanı
- `fonts/`: Anton, Oswald, Montserrat, Caveat Brush (Google Fonts, SIL Open Font License 1.1)
