# Minah Tekstil – Trendyol toplu ürün yükleme

Kaynak: `kaynak/urun-olusturma-1489888_1.xlsx`. Bu, mağazanın Trendyol'dan indirip doldurduğu şablon. Bütün ürünler "Tayt (531)" sayfasına girilmişti.

## Yüklemeye hazır: `minah-trendyol-yukleme-1.xlsx` (61 satır)

| Sayfa | Ürünler |
|---|---|
| Tayt (531) | Antrasit gri ve siyah yüksek bel tayt (8) |
| Gömlek (597) | Ekose oversize gömlek; mint ve sarı gömlek ceket; pembe ve mor crop gömlek ceket (25) |
| Sweatshirt (601) | Kapüşonlu kanguru cepli sweatshirt; gri ve kahve yarım fermuarlı üst (12) |
| Kumaş Pantolon (3902) | Turuncu ve fuşya bol paça pantolon (12) |
| Spor Eşofman Takımı (3189) | Siyah fermuarlı crop üst + bol paça pantolon takım (4) |

Yapılan düzeltmeler:

- **Kategori:** Kod her satırda 531'den 664'e kadar artıyordu. Artık her satır kendi sayfasının kodunu taşıyor.
- **Başlık:** 11. sütunun başlığı yeniden "Stok Kodu". Bu sütuna barkod yazıldı.
- **Barkod:** `MNH-MODEL-RENK-BEDEN` biçimine çevrildi (yalnızca A-Z, 0-9 ve tire). Eski barkodlarda boşluk ve Türkçe harf vardı. Taytların eski barkodlarında da renkler ters yazılmıştı.
- **Ürün adı:** Tek satıra indirildi. Sarı gömlek ceketin adı yanlışlıkla "Triko Hırka" yazılmıştı, düzeltildi.
- **Görseller:** İlk bedenin görselleri diğer bedenlere kopyalandı. Görsel hücrelerindeki eski köprüler (hyperlink) temizlendi.
- **Açıklamalar:** İç notlar çıkarıldı. Örnek: "test edilmeli", "etiketten doğrulanmalı", "Görselde 38-48 beden…". Mint gömlek cekette hırkanın açıklaması duruyordu; ürüne göre yeniden yazıldı.
- **Özellikler:** Her kategorinin zorunlu özellikleri dolduruldu ve şablonun izinli değer listesine göre kontrol edildi (Kalıp, Materyal, Bel, Boy).
- **Fazla satır:** 141. satırdaki tek tırnak silindi.

## Bekleyen: 73 satır

Bu ürünlerin kategorileri şablonda yok. Panelden şu kategorilerle yeni bir şablon indirilmeli: **Kazak, Hırka, Bluz, Eşofman Altı, Atlet, Ceket, Takım**. Satır listesi ve notlar `urunler.json` dosyasının `bekleyen` bölümünde. Şablon gelince bu ürünler `urunler` listesine eklenir ve dosya yeniden üretilir.

## Yeniden üretme

```
python3 duzelt.py urunler.json
```

Bir alan şablonun izinli listesinde yoksa ya da zorunlu bir alan boşsa betik dosyayı kaydetmez, sorunlu alanları listeler.
