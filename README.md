# IVEX Lead Finder

Sektör + mahalle bazında Google Maps'ten esnaf listesi çıkarır ve her işletme için
website'in aktif olup olmadığını otomatik kontrol eder. Sosyal medya varlığını
website'den bulabildiği kadar otomatik işaretler; bulamadıklarında hızlı bir
manuel kontrol linki üretir. Arama kısmı sizde kalır — bu araç sadece listeyi
ve önceliklendirmeyi otomatikleştirir.

## Kurulum (bir kere yapılır)

0. **Kodu bilgisayarınıza indirin:** GitHub'da bu repo sayfasında yeşil
   "Code" butonuna basıp "Download ZIP" seçin, indirilen dosyayı bir klasöre
   çıkarın (örn. Masaüstü'nde `IVEX` klasörü). Git kullanmayı biliyorsanız
   `git clone` ile de indirebilirsiniz.
1. **Python 3.9+ kurun** (yoksa): https://www.python.org/downloads/ adresinden
   indirip kurun. **Windows'ta kurulum ekranında "Add python.exe to PATH"
   kutucuğunu mutlaka işaretleyin**, yoksa terminalden çalışmaz.
2. **Terminali açıp klasöre gidin:**
   - **Mac:** Spotlight'tan (Cmd+Space) "Terminal" yazıp açın, sonra:
     ```
     cd ~/Desktop/IVEX
     ```
   - **Windows:** Başlat menüsünden "PowerShell" yazıp açın, sonra:
     ```
     cd Desktop\IVEX
     ```
     (klasörü nereye çıkardıysanız yolu ona göre değiştirin)
3. Bağımlılığı yükleyin:
   ```
   pip install -r requirements.txt
   ```
   (Mac'te `pip` çalışmazsa `pip3` deneyin)
4. Google Places API anahtarı alın:
   - https://console.cloud.google.com/ adresinde bir proje açın.
   - "Places API (New)" servisini etkinleştirin.
   - Bir API anahtarı oluşturun ve kopyalayın.
   - Google her ay $200'a kadar ücretsiz kredi veriyor; düşük hacimde (birkaç
     yüz sorgu/ay) genelde ücretsiz kalır. Kesin fiyat için Google Places
     API fiyatlandırma sayfasını kontrol edin.
5. `.env.example` dosyasını `.env` olarak kopyalayıp içine API anahtarınızı yazın:
   ```
   cp .env.example .env
   ```
   `.env` dosyasını bir metin editörüyle açıp şu satırı düzenleyin:
   ```
   GOOGLE_MAPS_API_KEY=AIza...sizin_gercek_anahtariniz
   ```
   Script her çalıştığında bu dosyayı otomatik okur, terminale tekrar
   yazmanıza gerek yok.
6. `config.example.json` dosyasını `config.json` olarak kopyalayıp kendi
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

Mac/Linux:
```
python3 lead_finder.py --config config.json
```

Windows (PowerShell):
```
python lead_finder.py --config config.json
```

API anahtarınız olmadan, örnek veriyle önce nasıl çalıştığını görmek isterseniz:

```
python3 lead_finder.py --config config.example.json --dry-run --out ornek.csv
```
(Windows'ta `python3` yerine `python` yazın.)

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
