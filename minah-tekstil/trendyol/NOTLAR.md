# Minah Tekstil – Trendyol toplu ürün yükleme

**Kaynak dosya:** `kaynak/urun-olusturma-1489888_1.xlsx`. Mağazanın Trendyol'dan indirip doldurduğu şablon. Bütün ürünler "Tayt (531)" sayfasına girilmişti.

## Dosyalar

- **`minah-trendyol-tum-urunler.xlsx`** – 134 satırın hepsi. Her ürün kendi kategori sayfasında.
- **`minah-trendyol-yukleme-1.xlsx`** – İlk teslim edilen dosya. Sadece Trendyol'un kendi şablonunda kategorisi olan 61 satırı içerir. Bu dosya artık betikle üretilmiyor; tüm-ürünler dosyası yüklenmezse yedek olarak kullanılır.

| Sayfa | Satır | Ürünler |
|---|---|---|
| Tayt (531) | 8 | Antrasit gri ve siyah yüksek bel tayt |
| Gömlek (597) | 25 | Ekose oversize gömlek; mint ve sarı gömlek ceket; pembe ve mor crop gömlek ceket |
| Sweatshirt (601) | 12 | Kapüşonlu sweatshirt; gri ve kahve yarım fermuarlı üst |
| Kumaş Pantolon (3902) | 12 | Turuncu ve fuşya bol paça pantolon |
| Spor Eşofman Takımı (3189) | 4 | Siyah fermuarlı crop üst + bol paça pantolon takım |
| Kazak (599)* | 12 | Polo yaka çizgili, fularlı, ajurlu ve bloklu triko kazaklar |
| Hırka (598)* | 14 | Kapüşonlu ekose hırka; V yaka triko hırka (ekru, turuncu) |
| Bluz (590)* | 15 | Kolsuz, uzun kollu ve kolsuz crop bluz |
| Eşofman Altı (525)* | 18 | Siyah, lacivert ve siyah-beyaz biyeli eşofman altı |
| Atlet (603)* | 4 | Fitilli crop atlet |
| Ceket (594)* | 8 | Kolej ceket (sarı, turuncu) |
| Alt - Üst Takım (2160)* | 2 | Simli bluz + maxi etek takım (gri, bej) |

\* İndirilen şablonda olmayan kategoriler. Sayfaları betik açtı.

**Kategori kodları:** [ArillaSoftOrg/arilla](https://github.com/ArillaSoftOrg/arilla) deposundaki `docs/reference/trendyol/product-categories.raw.json` dökümünden alındı. Bu döküm, şablondaki 6 bilinen kodun (531, 597, 601, 3189, 2949, 3902) hepsiyle birebir eşleşiyor.

**Bu sayfaların sınırı:** Sütunlar Trendyol'dan gelmedi, tahmine dayanıyor:
- Bilinen 6 kategorinin hepsinde ortak olan özellikler alındı.
- Üst giyime "Kalıp", eşofman altına "Bel" eklendi.
- Değerler, 6 kategorinin hepsinin izinli listesinde olanlardan seçildi.

Trendyol bu kategorilerde başka bir zorunlu özellik isterse ilgili satırlar hata raporunda çıkar.

## Yapılan düzeltmeler

- **Kategori:** Kod her satırda 531'den 664'e kadar artıyordu. Artık her satır kendi sayfasının kodunu taşıyor.
- **Başlık:** 11. sütunun başlığı yeniden "Stok Kodu". Bu sütuna barkod yazıldı.
- **Barkod:** `MNH-MODEL-RENK-BEDEN` biçimine çevrildi; yalnızca A-Z, 0-9 ve tire.
  - Eski barkodlarda boşluk ve Türkçe harf vardı.
  - Taytların eski barkodlarında renkler ters yazılmıştı.
- **Model kodu:** "TRIKO KAZAK" kodu iki farklı kazak modelini birleştiriyordu. Polo yaka çizgili kazaklar ve fularlı kazaklar ayrı model koduna ayrıldı.
- **Ürün adı:** Tek satıra indirildi.
  - Sarı gömlek ceketin adı yanlışlıkla "Triko Hırka" yazılmıştı, düzeltildi.
  - Adı sadece "TRIKO KAZAK" olan 3 ürüne tam ad yazıldı.
- **Renk:** Bloklu kazaklarda Renk alanına adındaki renkler yazıldı, Web Color "Çok Renkli" yapıldı. "KIEMIZI" yazım hatası "Kırmızı" olarak düzeltildi.
- **Görseller:** İlk bedenin görselleri diğer bedenlere kopyalandı. Görsel hücrelerindeki eski köprüler (hyperlink) temizlendi.
- **Açıklamalar:**
  - İç notlar çıkarıldı. Örnekler: "test edilmeli", "etiketten doğrulanmalı", "ÖN GÖRSEL EKSİK", "Görselde 38-48 beden…".
  - Mint gömlek cekette hırkanın açıklaması duruyordu; ürüne göre yeniden yazıldı.
  - Turuncu kolej ceketin yarıda kesilmiş açıklaması tamamlandı.
- **Fazla satır:** 141. satırdaki tek tırnak silindi.

## Mağazaya sorulacaklar

- Fularlı kazaklarda fular ürünle birlikte mi gönderiliyor? Açıklamada fular detayı geçiyor.
- Turuncu bloklu kazağın sadece arkadan fotoğrafı var; önden fotoğraf eklenmeli.
- Eski barkodlar ürün etiketlerine basıldıysa yeni barkodlarla eşleştirilmeli.

## Yeniden üretme

```
python3 duzelt.py urunler.json
```

Betik şu durumlarda dosyayı kaydetmez ve sorunlu alanları listeler:
- Bir değer izinli listede yoksa.
- Zorunlu bir alan boşsa.
- Bir barkod tekrar ediyorsa.
