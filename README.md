# IVEX Lead Finder

Sektör + mahalle bazında Google Maps'ten esnaf listesi çıkarır ve her işletme için
website'in aktif olup olmadığını otomatik kontrol eder. Sosyal medya varlığını
website'den bulabildiği kadar otomatik işaretler; bulamadıklarında hızlı bir
manuel kontrol linki üretir. Arama kısmı sizde kalır — bu araç sadece listeyi
ve önceliklendirmeyi otomatikleştirir.

## Kurulum (bir kere yapılır)

1. Python 3.9+ kurulu olmalı.
2. Bağımlılığı yükleyin:
   ```
   pip install -r requirements.txt
   ```
3. Google Places API anahtarı alın:
   - https://console.cloud.google.com/ adresinde bir proje açın.
   - "Places API (New)" servisini etkinleştirin.
   - Bir API anahtarı oluşturun ve kopyalayın.
   - Google her ay $200'a kadar ücretsiz kredi veriyor; düşük hacimde (birkaç
     yüz sorgu/ay) genelde ücretsiz kalır. Kesin fiyat için Google Places
     API fiyatlandırma sayfasını kontrol edin.
4. Anahtarı ortam değişkeni olarak tanımlayın:
   ```
   export GOOGLE_MAPS_API_KEY=xxxxxxxx
   ```
5. `config.example.json` dosyasını `config.json` olarak kopyalayıp kendi
   sektör ve mahalle listenizle düzenleyin:
   ```
   cp config.example.json config.json
   ```
   ```json
   {
     "sectors": ["kuaför", "berber", "eczane"],
     "locations": ["Kadıköy, İstanbul", "Üsküdar, İstanbul"],
     "max_results_per_query": 40,
     "output_csv": "leads.csv"
   }
   ```
   Not: Google Text Search her sorgu için en fazla 60 sonuç (3 sayfa x 20)
   döner. Bir mahalle+sektör kombinasyonunda 60'tan fazla işletme varsa
   mahalleyi daha küçük bölgelere ayırmanız gerekebilir.

## Çalıştırma

```
python3 lead_finder.py --config config.json
```

API anahtarınız olmadan, örnek veriyle önce nasıl çalıştığını görmek isterseniz:

```
python3 lead_finder.py --config config.example.json --dry-run --out ornek.csv
```

## Çıktı

`leads.csv` dosyası (Excel'de doğrudan açılabilir) şu kolonları içerir:

| Kolon | Açıklama |
|---|---|
| Sektör / Bölge | Hangi arama sonucundan geldiği |
| Marka Adı / Telefon / Adres | Google Maps'ten |
| Google Puanı | Google Maps puanı |
| Website | Varsa website adresi |
| Website Durumu | Yok / Aktif / Pasif (HTTP hatası, SSL hatası, zaman aşımı vs.) |
| Sosyal Medya (Website'den Bulunan) | Website'in kaynak kodunda geçen Instagram/Facebook/TikTok vb. linkler |
| Sosyal Medya Manuel Kontrol Linki | Tek tıkla Google'da "işletme adı + instagram" araması açar (website'de bulunamayanlar için) |
| Google Maps Linki | Doğrudan Maps sayfası |
| **Öncelik** | Yüksek / Orta / Düşük — website yok veya pasifse Yüksek |
| **Aranmalı mı?** | Evet/Hayır — sizin mevcut "web sitesi olmayanı ara" kuralınızın otomatik işaretlenmiş hali |

Listeyi `Öncelik` veya `Aranmalı mı?` kolonuna göre sıralayıp/filtreleyip
doğrudan arama listesi olarak kullanabilirsiniz.

## Bilinen sınırlar

- **Sosyal medya tespiti** website'i olmayan işletmeler için tam otomatik
  değildir: Instagram/Facebook'un herkese açık "işletme adına göre ara" API'si
  yok, bu yüzden bu işletmeler için sadece hızlı bir manuel kontrol linki
  üretilir (tek tık, saniyeler sürer). Website'i olanlarda ise sosyal medya
  linkleri sayfa kaynağından otomatik taranır.
- Kalıcı olarak kapanmış (`CLOSED_PERMANENTLY`) işaretli işletmeler listeden
  otomatik çıkarılır.
- Website kontrolü bazı sitelerde bot koruması nedeniyle yanlışlıkla "Pasif"
  gösterebilir; "Pasif" çıkanları aramadan önce tarayıcıdan bir kez elle
  kontrol etmeniz önerilir.
