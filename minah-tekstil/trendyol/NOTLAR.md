# Minah Tekstil – Trendyol toplu ürün yükleme

**Kaynak dosya:** `kaynak/urun-olusturma-1489888_1.xlsx`. Mağazanın Trendyol'dan indirip doldurduğu şablon. Bütün ürünler "Tayt (531)" sayfasına girilmişti.

## Dosyalar

Trendyol bir dosyada en fazla 8 kategori kabul ediyor, bu yüzden 12 kategori iki dosyaya bölündü. Her dosya indirilen şablonun kendisi; yazma işini `paket.py` XML düzeyinde yapıyor:

- **Korunanlar:** Stiller, açılır listeler, özellik sayfaları, ülke kodları ve yardım sayfası olduğu gibi kalıyor. Yalnızca ürün satırları değişiyor.
- **Metinler:** Excel'in kendi yaptığı gibi `sharedStrings.xml` tablosuna yazılıyor.
- **Neden:** İlk sürüm openpyxl ile kaydedilmişti. openpyxl metinleri satır içi (inlineStr) yazdığı için Trendyol "Excel dosyasında kayıt edilecek satır bulunamadı" hatası verdi.

İki dosya:

- **`minah-trendyol-dosya-1.xlsx`** – 5 kategori, 61 satır. Trendyol'un kendi şablonundaki kategoriler: Tayt, Spor Eşofman Takımı, Gömlek, Kumaş Pantolon, Sweatshirt. Önce bu dosya yüklenir.
- **`minah-trendyol-dosya-2.xlsx`** – 7 kategori, 73 satır. Betiğin açtığı kategoriler (aşağıda * ile işaretli). Bu kategorilerin özellik sayfaları da betik tarafından eklendi; listelerde yalnızca bilinen 6 kategorinin hepsinde ortak olan değerler var.

Boş gelen Polo Yaka T-shirt kategorisi iki dosyaya da konmadı.

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

## Marka

Kaynak dosyada marka "minah tekstil" yazıyordu. Trendyol bu adı çözemedi: "Excel satırı 2 için marka kimliği çözülemedi". "Minah Tekstil" mağazanın (satıcının) adı, marka değil. Mağazadaki mevcut ürünler **ixoskids club** markasıyla satılıyor, bu yüzden `urunler.json` dosyasında `"marka": "ixoskids club"` var. Ürünler "Minah Tekstil" markasıyla açılacaksa önce markanın panelde "Marka Ara ve Tanımla" ekranından tanımlatılması gerekiyor. Onaydan sonra `marka` değiştirilip dosyalar yeniden üretilir.

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
