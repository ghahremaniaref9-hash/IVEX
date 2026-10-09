# Mekan Sizin – maç günü şablonları

Dört maç afişi şablonu ve feed için yardımcı araçlar (story, skor tahmini, menü karuseli, fotoğraf renk ayarı, Reels) var. Hepsi 1080 px genişliğinde görsel üretir ve logoda **bira/rakı yoktur**: `assets/mekan-sizin-plaka-logo.png`, mekânın gönderdiği gerçek plaka logodan kesildi.

Dört afiş şablonunda `"baslik"` alanı büyük başlığı değiştirir (ör. hatırlatma için `"BU PAZAR"`); yazılmazsa varsayılan başlık kullanılır (MAÇ GÜNÜ / DEPLASMAN / AVRUPA GECESİ).

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

## Story – maç günü (1080×1920)

- Üç şablonun kartını (bilet, biniş kartı, pasaport) dikey story'ye taşır. Arka planda bir fotoğraf karartılarak kullanılır.
- `"tur"`: `"bilet"` (lig iç saha), `"kart"` (lig deplasman), `"pasaport"` (Avrupa). Kart alanları ilgili şablonun JSON alanlarıyla aynı.
- Üst ve alt ~220 px Instagram arayüzü için boş bırakılır. `cikartma_notu` (ör. "Geliyor musun?") ve el çizimi okun gösterdiği boşluğa uygulamadan anket/soru/geri sayım çıkartması konur.

```
python3 story.py ../haftalik-feed/ayarlar/03a-kocaelispor-story.json
```

## Skor Tahmini (maç günü gönderisi)

- Eski stat skorbordu: iki takım ve boş "?" plakaları; takipçi tahminini yorumlara yazar. Lig ve Avrupa maçlarında kullanılır.
- Rakibin arma dosyası yoksa takım renklerinde harfli rozet çizilir (`kisaltma`, `renkler`).

```
python3 skor_tahmini.py ../haftalik-feed/ayarlar/07b-hoffenheim-skor-tahmini.json
```

## Menü ve kampanya karuseli

- 1. kare: kampanya adisyon fişi. Sonraki kareler: masada duran basılı menü kartı (isteğe bağlı bantlı fotoğrafla).
- Fiyatlar, bölümler ve kampanya JSON'dan gelir. `"indirim": true` olan bölümde indirimli fiyat `indirim_yuzde` ile otomatik hesaplanır.
- `kampanya.saat` boş bırakılırsa fişteki saat satırı kalkar. `"sadece_kapak": true` yalnızca kapağı üretir.

```
python3 menu.py ../haftalik-feed/ayarlar/04-menu-raki-kampanya.json
```

## Metinsiz fotoğraflar ve Reels

- `foto.py`: Fotoğrafları 4:5'e kırpar ve hepsine aynı film görünümünü verir (soluk renkler, korunan kırmızılar, sıcak ışık, vinyet, gren). Gerçek mekân fotoğrafları da aynı dosyaya eklenebilir; ızgara tek elden çıkmış gibi durur.
- `reel.py`: Bir fotoğraftan 7 saniyelik sessiz, yavaş yakınlaşan 1080×1920 Reels videosu üretir. Müzik Instagram'da eklenir.

```
python3 foto.py ../haftalik-feed/ayarlar/metinsiz-fotolar.json
python3 reel.py kaynak.jpg cikti.mp4 7
```

## Gereken paketler

`pip install pillow numpy opencv-python-headless imageio-ffmpeg`

## Klasörler

- `assets/`: plaka logo, orijinal logo, armalar, stadyum fotoğrafı, Şablon 1 tabanı
- `fonts/`: Anton, Oswald, Montserrat, Caveat Brush, Space Mono (Google Fonts, SIL Open Font License 1.1)
