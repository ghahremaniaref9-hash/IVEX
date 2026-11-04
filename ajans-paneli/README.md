# IVEX Ajans Paneli

Ekibin ortak kullandığı tek sayfalık panel. Üç bölümü var:

- **Gelir / Gider:** Aylık gelir, gider ve net toplamı gösterir. Kayıtları
  Excel'de açılan CSV dosyası olarak indirebilirsiniz.
- **Hesaplar:** Müşteri ve ajans hesaplarının giriş bilgilerini tutar.
  Kullanıcı adı, şifre ve notlar ekibin ortak **kasa şifresiyle**, kayıt
  yapılan tarayıcıda şifrelenir (PBKDF2-SHA256 600.000 tur, AES-GCM 256).
  Sunucuda sadece şifreli hali durur. Kasa 10 dakika işlem yapılmazsa
  kendiliğinden kilitlenir.
- **İçerikler:** Drive linkleri, müşteri, tür, yayın tarihi ve durum
  (Hazırlanıyor, Müşteri onayında, Onaylandı, Yayınlandı) bilgilerini tutar.

Panel claude.ai Artifact olarak yayınlanıyor ve kayıtlar Artifact'ın ortak
veritabanında saklanıyor. Bu yüzden `ivex-ajans-paneli.html` dosyası
bilgisayarda doğrudan açılınca kayıt göstermez. Bu dosya sayfanın kaynak
kodunun yedeği.

## Erişim

- Paneli ekip arkadaşlarınızla sağ üstteki **Paylaş** menüsünden, e-posta
  adreslerini ekleyerek **Düzenleyen (Editor)** yetkisiyle paylaşın.
  Kurumsal (Team) planda aynı organizasyondaki üyeler **Katkıda bulunan
  (Contributor)** yetkisiyle de kayıt ekleyebilir.
- Herkese açık link ile paylaşmayın. Link ile gelen dış kullanıcılar sadece
  görüntüleme yetkisi alır ve bu panelde hiçbir kaydı göremez.
- Kasa şifresini ekip arkadaşlarınıza yüz yüze ya da telefonda söyleyin.
  Unutulursa kayıtlı şifreler geri getirilemez. Panelin sahibi kasayı
  sıfırlayabilir, ama bu kayıtlı bütün hesapları siler.
