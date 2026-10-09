# Mekan Sizin – maç günü şablonları

Dört şablon var. Hepsi 1080 px genişliğinde Instagram gönderisi üretir ve logoda **bira/rakı yoktur** (siyah plakalı "MEKAN SİZİN" logosu).

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

## Şablon 3 – "Deplasman Biniş Kartı" (Süper Lig deplasman maçları)

- Koyu harita dokulu zemin üstünde kırmızı başlıklı bir biniş kartı: İST → rakibin şehir kodu, stadyum, İstanbul'dan kuş uçuşu mesafe, koltuk "SENİN", kapı "MEKAN SİZİN".
- Rakibin şehri, semti, stadyumu, kodu ve koordinatları `sehirler.json` içinde hazır (2026-27'nin 17 rakibi). Mesafe otomatik hesaplanır.
- `deplasman.json` içinde değiştirilecekler: `rakip` (sehirler.json'daki adıyla, ör. "FENERBAHÇE"), `ust_satir`, `kicker_sag`, `sefer`, `tarih`, `saat`, `cikti`.
- Rakibin arması: `assets/` içine şeffaf PNG koyun ve `sehirler.json`'da o takıma `"arma": "assets/dosya.png"` ekleyin. Arma yoksa takım renklerinde harfli bir rozet çizilir.

```
python3 deplasman.py deplasman.json
```

## Şablon 4 – "Kartal Pasaportu" (UEFA Avrupa Ligi, iç saha ve deplasman)

- Gece stadyum ışıkları altında guilloche desenli bir pasaport sayfası: BJK arması "vesikalık" yerinde, maç/şehir/stadyum/tarih/saat alanları, rakibin ülke bayrağı, mavi giriş damgası, alttaki makinede okunur satırlar ve "CANLI YAYIN" damgası.
- `avrupa.json` içinde: `ev_sahibi`, `deplasman`, `rakip` (ad, kısaltma, renkler, isteğe bağlı arma), `sehir`, `ulke`, `stadyum`, `lat`/`lon`, `tarih`, `tarih_damga`, `tarih_mrz`, `saat`, `ust_satir`, metinler.
- Bayrak tipleri: `yatay` / `dikey` (şerit renkleri), `haç` (ör. İngiltere: beyaz + kırmızı), `çapraz` (ör. İskoçya: mavi + beyaz). Karmaşık bayraklar için `"bayrak": {}` bırakın.
- İç saha maçında: `ev_sahibi: "BEŞİKTAŞ"`, `sehir: "İSTANBUL"`, `ulke: "TÜRKİYE"`, `deplasman_mi: false` (mesafe "—" yazar), bayrağı boş bırakın.

```
python3 avrupa.py avrupa.json
```

### 2026-27 UEFA Avrupa Ligi lig aşaması (haberlere göre; UEFA'dan teyit edin)

| Tarih | Maç | Şehir / Stadyum | Bayrak |
|---|---|---|---|
| 17 Eylül | Beşiktaş – Marsilya | İstanbul | – |
| 15 Ekim | Hoffenheim – Beşiktaş | Sinsheim / SNP Arena (49.24, 8.89) | yatay: #000000 #DD0000 #FFCE00 |
| 22 Ekim | Beşiktaş – Crystal Palace | İstanbul | – |
| 5 Kasım | Celtic – Beşiktaş | Glasgow / Celtic Park (55.85, -4.21) | çapraz: #005EB8 #FFFFFF |
| 26 Kasım | Beşiktaş – Hapoel Beer-Sheva | İstanbul | – |
| 10 Aralık | Leverkusen – Beşiktaş | Leverkusen / BayArena (51.04, 7.00) | yatay: #000000 #DD0000 #FFCE00 |
| 21 Ocak | Beşiktaş – Union SG | İstanbul | – |
| 28 Ocak | Omonia – Beşiktaş | Lefkoşa / GSP Stadyumu (35.13, 33.33) | {} |

## Gereken paketler

`pip install pillow numpy opencv-python-headless`

## Klasörler

- `assets/`: plaka logo, orijinal logo, armalar, stadyum fotoğrafı, Şablon 1 tabanı
- `fonts/`: Anton, Oswald, Montserrat, Caveat Brush, Space Mono (Google Fonts, SIL Open Font License 1.1)
