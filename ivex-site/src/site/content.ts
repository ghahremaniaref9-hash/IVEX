// Shared site content: contact details and the service catalogue. The service
// pages, the home/about service lists and the menus are all rendered from here.

export const SITE_URL = "https://ivexco.com.tr";
export const WHATSAPP = "905010623794";
export const EMAIL = "ivex.co.tr@gmail.com";
export const INSTAGRAM = "https://www.instagram.com/ivex.tr/";
export const ADDRESS_HTML = "Fulya Mah., Şişli,<br />İstanbul, Türkiye";

// Particle shapes drawn by src/gl.ts.
export const SHAPES = ["helix", "cloud", "ring", "stairs", "mark", "aperture", "target", "browser", "play", "network", "chat"] as const;
export type Shape = (typeof SHAPES)[number];

export type Service = {
  slug: string;
  name: string;
  /** One line for lists. */
  short: string;
  /** Opening paragraph on the service page. */
  lead: string;
  items: string[];
  audience: string;
  shape: Shape;
};

export const SERVICES: Service[] = [
  {
    slug: "sosyal-medya-yonetimi",
    name: "Sosyal Medya Yönetimi",
    short: "İçerik takvimi, paylaşım ve topluluk yönetimi tek elden.",
    lead: "Hesaplarınızı stratejiden paylaşıma, topluluk yönetiminden raporlamaya kadar tek elden yönetiyoruz. Siz işinize odaklanırken markanız her gün doğru yerde, doğru dille görünür.",
    items: [
      "Aylık içerik takvimi ve paylaşım planı",
      "Instagram, TikTok, Facebook ve LinkedIn hesap yönetimi",
      "Gönderi, hikâye ve Reels kurgusu",
      "Yorum ve mesaj takibi, topluluk yönetimi",
      "Profil düzeni, biyografi ve öne çıkanlar",
      "Aylık performans raporu ve öneriler",
    ],
    audience: "Düzenli paylaşım yapmak isteyen ama buna zaman ayıramayan işletmeler ve hesabını profesyonel bir görünüme kavuşturmak isteyen markalar.",
    shape: "ring",
  },
  {
    slug: "icerik-uretimi",
    name: "İçerik Üretimi",
    short: "Markanızın diline uygun görsel, metin ve video içerikler.",
    lead: "Markanızın diline uygun fotoğraf, video, grafik tasarım ve metinler üretiyoruz. Her içerik, yayınlanacağı platforma ve hedef kitlenize göre kurgulanır.",
    items: [
      "Ürün, mekân ve ekip fotoğraf çekimleri",
      "Reels ve kısa video prodüksiyonu",
      "Sosyal medya grafik tasarımları",
      "Gönderi metinleri ve açıklamalar",
      "Kampanya ve özel gün içerikleri",
      "Marka diline uygun görsel şablonlar",
    ],
    audience: "Sosyal medyada kaliteli ve tutarlı içerikle görünmek isteyen; ürününü, mekânını ya da hizmetini doğru anlatmak isteyen markalar.",
    shape: "aperture",
  },
  {
    slug: "reklam",
    name: "Reklam",
    short: "Hedef kitlenize göre kurgulanan ve düzenli takip edilen reklam kampanyaları.",
    lead: "Instagram, Facebook, Google ve TikTok'ta hedef kitlenize göre kurgulanan reklam kampanyaları hazırlıyoruz. Bütçenizi düzenli takip ediyor, işe yarayanı büyütüyoruz.",
    items: [
      "Hedef kitle ve bütçe planlaması",
      "Instagram ve Facebook (Meta) reklamları",
      "Google Arama ve Haritalar reklamları",
      "TikTok reklamları",
      "Reklam görseli ve metni hazırlığı",
      "WhatsApp, arama ve form dönüşümlerinin takibi, raporlama",
    ],
    audience: "Daha fazla müşteriye ulaşmak, WhatsApp ya da telefondan daha çok talep almak isteyen işletmeler.",
    shape: "target",
  },
  {
    slug: "marka-stratejisi",
    name: "Marka Stratejisi",
    short: "Konumlandırma, ton ve mesajın netleştiği yol haritası.",
    lead: "Markanızın kim olduğunu, kime ve nasıl konuştuğunu netleştiren bir yol haritası çıkarıyoruz. Tüm iletişiminiz bu temel üzerine kurulur.",
    items: [
      "Pazar ve rakip analizi",
      "Hedef kitle çalışması",
      "Konumlandırma ve marka mesajı",
      "Marka dili ve iletişim tonu",
      "Görsel kimlik yönlendirmesi",
      "Uygulanabilir iletişim planı",
    ],
    audience: "Yeni kurulan, yenilenmek isteyen ya da rakiplerinden net biçimde ayrışmak isteyen markalar.",
    shape: "helix",
  },
  {
    slug: "web-tasarim",
    name: "Web Tasarım",
    short: "Markanızı doğru anlatan, mobil uyumlu web siteleri.",
    lead: "Markanızı doğru anlatan, hızlı açılan ve mobil uyumlu web siteleri tasarlıyoruz. Ziyaretçiyi WhatsApp'a, aramaya ya da forma yönlendiren, satışa odaklı sayfalar kuruyoruz.",
    items: [
      "Kurumsal web sitesi ve tanıtım sayfaları",
      "Mobil uyumlu, hızlı açılan tasarım",
      "WhatsApp butonu ve iletişim formu",
      "Alan adı bağlantısı ve yayına alma",
      "Google'da bulunabilirlik için temel SEO",
      "Google Ads etiketi ve dönüşüm takibi kurulumu",
    ],
    audience: "İlk web sitesini yaptırmak isteyen ya da mevcut sitesini daha modern ve satış odaklı hale getirmek isteyen işletmeler.",
    shape: "browser",
  },
  {
    slug: "video-ve-tiktok",
    name: "Video ve TikTok",
    short: "Kısa formatlı videolar ve TikTok'a özel içerik kurgusu.",
    lead: "Kısa formatlı videolar ve TikTok'a özel içerik kurgusuyla markanızı akışta fark edilir kılıyoruz. Fikirden çekime, kurgudan paylaşıma kadar süreci birlikte yürütüyoruz.",
    items: [
      "Reels ve TikTok video çekimleri",
      "Trend ve akım takibi",
      "Senaryo ve kurgu",
      "Altyazı, müzik ve efektler",
      "Ürün ve hizmet tanıtım videoları",
      "Yayın takvimi ve hesap yönetimi",
    ],
    audience: "Kısa videolarla daha geniş kitlelere ulaşmak ve sosyal medyada etkileşimini artırmak isteyen markalar.",
    shape: "play",
  },
  {
    slug: "influencer-marketing",
    name: "Influencer Marketing",
    short: "Markanıza uygun içerik üreticileriyle iş birlikleri.",
    lead: "Markanıza uygun içerik üreticilerini bulup iş birliklerini baştan sona yönetiyoruz. Doğru kişiyle, doğru kitleye, güvenilir bir dille ulaşırsınız.",
    items: [
      "Markaya uygun içerik üreticisi seçimi",
      "İş birliği kurgusu ve içerik brifi",
      "Anlaşma ve süreç takibi",
      "İçerik onayı ve yayın planı",
      "Kampanya sonrası sonuç raporu",
    ],
    audience: "Ürününü ya da hizmetini güvenilir bir tavsiyeyle yeni kitlelere tanıtmak isteyen markalar.",
    shape: "network",
  },
];

export const servicePath = (s: Service) => `/hizmetler/${s.slug}/`;
