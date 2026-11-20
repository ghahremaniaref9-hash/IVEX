// Markup shared by every page: <head>, menu, footer, CTAs, the service list and
// the "Sizi arayalım" form. Hand-written pages pull these in through
// <!--ivx:...--> placeholders (see vite.config.ts); generated pages call them directly.

import { LOGO_WHITE_D, LOGO_X_D, WAVE_A_D, WAVE_B_D } from "./art";
import { ADDRESS_HTML, EMAIL, INSTAGRAM, SERVICES, SITE_URL, WHATSAPP, servicePath, type Service } from "./content";

export type NavKey = "home" | "hizmetler" | "hakkimizda" | "iletisim";

const NAV: [NavKey, string, string][] = [
  ["hizmetler", "/hizmetler/", "Hizmetler"],
  ["hakkimizda", "/hakkimizda/", "Hakkımızda"],
  ["iletisim", "/iletisim/", "İletişim"],
];

export const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export const waUrl = (text?: string) => `https://wa.me/${WHATSAPP}${text ? `?text=${encodeURIComponent(text)}` : ""}`;

export const serviceWaText = (s: Service) => `Merhaba, ${s.name} hakkında bilgi almak istiyorum.`;

export const logo = () =>
  `<svg class="ivx-logo" viewBox="0 0 644 208" role="img" aria-label="IVEX"><path class="ivx-logo__ink" fill-rule="evenodd" d="${LOGO_WHITE_D}"/><path class="ivx-logo__x" fill-rule="evenodd" d="${LOGO_X_D}"/></svg>`;

const logoX = () =>
  `<svg class="ivx-logo-x" viewBox="439 0 205 208" aria-hidden="true" focusable="false"><path class="ivx-logo__x" fill-rule="evenodd" d="${LOGO_X_D}"/></svg>`;

export type Meta = { title: string; description: string; path: string; jsonLd?: object };

export function head({ title, description, path, jsonLd }: Meta) {
  const url = `${SITE_URL}${path}`;
  const t = esc(title);
  const d = esc(description);
  return `<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${t}</title>
    <meta name="description" content="${d}" />
    <meta name="theme-color" content="#07100C" />
    <link rel="canonical" href="${url}" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="IVEX Medya" />
    <meta property="og:locale" content="tr_TR" />
    <meta property="og:url" content="${url}" />
    <meta property="og:title" content="${t}" />
    <meta property="og:description" content="${d}" />
    <meta property="og:image" content="${SITE_URL}/og.jpg" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="805" />
    <meta property="og:image:alt" content="IVEX logosu, yeşil cam basamaklardan yükselen DNA sarmalının önünde" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="${t}" />
    <meta name="twitter:description" content="${d}" />
    <meta name="twitter:image" content="${SITE_URL}/og.jpg" />
    <link rel="icon" href="/favicon.ico" sizes="48x48" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32" />
    <link rel="icon" href="/favicon-16.png" type="image/png" sizes="16x16" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180" />
    <link rel="manifest" href="/site.webmanifest" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Outfit:wght@300..700&display=swap" />
    <script type="module" src="/src/main.ts"></script>${jsonLd ? `\n    <script type="application/ld+json">${JSON.stringify(jsonLd)}</script>` : ""}
  </head>`;
}

const navLinks = (active: NavKey) =>
  NAV.map(([key, href, label]) => `<a href="${href}"${key === active ? ' aria-current="page"' : ""}>${label}</a>`).join("");

export function header(active: NavKey) {
  return `<a class="ivx-skip" href="#icerik">İçeriğe geç</a>
    <canvas id="gl" aria-hidden="true"></canvas>
    <div class="gl-vignette" aria-hidden="true"></div>
    <header class="ivx-nav">
      <div class="ivx-wrap ivx-nav__inner">
        <nav aria-label="Ana menü" class="ivx-nav__links">${navLinks(active)}</nav>
        <a class="ivx-nav__logo" href="/" aria-label="IVEX, ana sayfa">${logo()}</a>
        <div class="ivx-nav__end">
          <a href="${waUrl()}" target="_blank" rel="noopener noreferrer" class="ivx-scramble" aria-label="WhatsApp'tan Yaz"><span aria-hidden="true" data-scramble>WhatsApp'tan Yaz</span></a>
          <a href="${waUrl()}" target="_blank" rel="noopener noreferrer" class="ivx-nav__wa">WhatsApp</a>
        </div>
      </div>
    </header>`;
}

export function footer() {
  return `<footer class="ivx-footer">
      <div class="ivx-wrap ivx-footer__inner">
        <a class="ivx-footer__logo" href="/" aria-label="IVEX, ana sayfa">${logo()}</a>
        <nav aria-label="Alt menü" class="ivx-footer__links">${navLinks("home")}<a href="${INSTAGRAM}" target="_blank" rel="noopener noreferrer">Instagram</a></nav>
        <small>© 2026 IVEX Medya</small>
      </div>
    </footer>`;
}

/** The hero CTA: label over a double-helix waveform that runs on hover. */
export function helixCta(label: string, href: string) {
  return `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer" class="ivx-helix-cta">
              <span class="ivx-helix-cta__label">${label}<span class="ivx-helix-cta__arrow" aria-hidden="true">→</span></span>
              <span class="ivx-helix-cta__wave" aria-hidden="true"><svg viewBox="0 0 240 12" preserveAspectRatio="none" focusable="false"><path d="${WAVE_A_D}" /><path d="${WAVE_B_D}" /></svg></span>
            </a>`;
}

/** The solid WhatsApp slab whose label rolls up on hover. */
export function waSlab(href = waUrl(), label = "WhatsApp'tan Yaz") {
  return `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer" class="ivx-wa-slab" aria-label="${label}">
                <span class="ivx-wa-slab__roll" aria-hidden="true"><span>${label}</span><span>${label}</span></span>
                <span aria-hidden="true">↗</span>
              </a>`;
}

/** Numbered service rows linking to each service page. */
export function serviceList(services: Service[] = SERVICES) {
  const rows = services
    .map((s) => {
      const n = String(SERVICES.indexOf(s) + 1).padStart(2, "0");
      return `<li>
              <a class="ivx-svc__row" href="${servicePath(s)}">
                <span class="ivx-svc__idx" aria-hidden="true">${n}</span>
                <span class="ivx-svc__name">${s.name}</span>
                <span class="ivx-svc__go" aria-hidden="true">→</span>
                <span class="ivx-svc__desc">${s.short}</span>
              </a>
            </li>`;
    })
    .join("\n            ");
  return `<ol class="ivx-svc">
            ${rows}
          </ol>`;
}

/** WhatsApp, e-mail, address and Instagram, side by side. */
export function contactGrid() {
  return `<div class="ivx-contact__grid">
            <div class="ivx-contact__cell">
              ${waSlab()}
            </div>
            <div class="ivx-contact__cell">
              <span class="ivx-cap">E-posta</span>
              <a href="mailto:${EMAIL}" class="ivx-viewfinder"><span class="ivx-viewfinder__c ivx-viewfinder__c--tl" aria-hidden="true"></span><span class="ivx-viewfinder__c ivx-viewfinder__c--tr" aria-hidden="true"></span><span class="ivx-viewfinder__c ivx-viewfinder__c--bl" aria-hidden="true"></span><span class="ivx-viewfinder__c ivx-viewfinder__c--br" aria-hidden="true"></span>${EMAIL}</a>
            </div>
            <div class="ivx-contact__cell">
              <span class="ivx-cap">Adres</span>
              <address>${ADDRESS_HTML}</address>
            </div>
            <div class="ivx-contact__cell">
              <a href="${INSTAGRAM}" target="_blank" rel="noopener noreferrer" class="ivx-igbadge" aria-label="Instagram: @ivex.tr">
                <svg class="ivx-igbadge__ring" viewBox="0 0 100 100" aria-hidden="true" focusable="false">
                  <defs><path id="ivx-ig-ring" d="M50,50 m-38,0 a38,38 0 1,1 76,0 a38,38 0 1,1 -76,0" /></defs>
                  <text><textPath href="#ivx-ig-ring" textLength="236" lengthAdjust="spacing">@ivex.tr • Instagram • @ivex.tr • Instagram • </textPath></text>
                </svg>
                <span class="ivx-igbadge__core" aria-hidden="true">${logoX()}</span>
              </a>
            </div>
          </div>`;
}

/** "Sizi arayalım": Netlify form (forwarded to WhatsApp by submission-created) and its thank-you state. */
export function applyForm() {
  return `<div class="ivx-apply__panel">
              <form name="basvuru" method="POST" data-netlify="true" netlify-honeypot="bot-field" class="ivx-form" data-ivx-form novalidate>
                <input type="hidden" name="form-name" value="basvuru" />
                <p class="sr-only" aria-hidden="true"><label>Bu alanı boş bırakın <input name="bot-field" tabindex="-1" autocomplete="off" /></label></p>
                <div class="ivx-form__grid">
                    <div class="ivx-field">
                      <label for="f-ad">Ad</label>
                      <input id="f-ad" name="ad" type="text" autocomplete="given-name" required aria-describedby="f-ad-err" />
                      <p class="ivx-field__err" id="f-ad-err"></p>
                    </div>
                    <div class="ivx-field">
                      <label for="f-soyad">Soyad</label>
                      <input id="f-soyad" name="soyad" type="text" autocomplete="family-name" required aria-describedby="f-soyad-err" />
                      <p class="ivx-field__err" id="f-soyad-err"></p>
                    </div>
                    <div class="ivx-field">
                      <label for="f-telefon">Telefon</label>
                      <input id="f-telefon" name="telefon" type="tel" autocomplete="tel" required aria-describedby="f-telefon-err" inputmode="tel" placeholder="0 5xx xxx xx xx" />
                      <p class="ivx-field__err" id="f-telefon-err"></p>
                    </div>
                    <div class="ivx-field">
                      <label for="f-eposta">E-posta</label>
                      <input id="f-eposta" name="eposta" type="email" autocomplete="email" required aria-describedby="f-eposta-err" inputmode="email" placeholder="ornek@mail.com" />
                      <p class="ivx-field__err" id="f-eposta-err"></p>
                    </div>
                </div>
                <div class="ivx-consent">
                  <input id="f-onay" name="onay" type="checkbox" value="evet" required aria-describedby="f-onay-err" />
                  <label for="f-onay">Bilgilerimin benimle iletişime geçilmesi amacıyla kullanılmasını ve bu amaçla WhatsApp bildirim servisi (CallMeBot) üzerinden IVEX’e iletilmesini kabul ediyorum.</label>
                  <p class="ivx-field__err" id="f-onay-err"></p>
                </div>
                <button type="submit" class="ivx-submit"><span data-submit-label>Beni Arayın</span><span aria-hidden="true">→</span></button>
                <p class="ivx-form__note">Bilgileriniz yalnızca sizinle iletişime geçmek için kullanılır.</p>
                <p class="ivx-form__status" data-status role="status" aria-live="polite"></p>
              </form>
              <div class="ivx-sent" data-sent hidden>
                <svg class="ivx-sent__icon" viewBox="0 0 48 48" aria-hidden="true" focusable="false"><circle cx="24" cy="24" r="22" /><path d="M14 24.5l7 7 13-14" /></svg>
                <h3 class="ivx-sent__title" tabindex="-1">Teşekkürler<span data-sent-name></span>.</h3>
                <p>Bilgileriniz bize ulaştı, en kısa sürede sizi arayacağız.</p>
                <p>Beklemek istemezseniz bilgilerinizi WhatsApp'tan da gönderebilirsiniz.</p>
                <a class="ivx-wa-send" data-sent-wa href="${waUrl()}" target="_blank" rel="noopener noreferrer">WhatsApp'tan Gönder <span aria-hidden="true">↗</span></a>
              </div>
            </div>`;
}

/** Preview of the light theme: ?tema=beyaz switches it on for the rest of the visit, ?tema=koyu back off. */
export const THEME_SCRIPT = `try{var q=new URLSearchParams(location.search).get("tema");if(q)sessionStorage.setItem("ivx-tema",q);if((q||sessionStorage.getItem("ivx-tema"))==="beyaz")document.documentElement.dataset.theme="light"}catch(e){}`;

/** Swap <!--ivx:name--> / <!--ivx:header=key--> placeholders in a hand-written page. */
export function fillPlaceholders(html: string) {
  return html
    .replace(/<!--ivx:header=(\w+)-->/g, (_, key: NavKey) => header(key))
    .replace(/<!--ivx:footer-->/g, () => footer())
    .replace(/<!--ivx:services-->/g, () => serviceList())
    .replace(/<!--ivx:contact-->/g, () => contactGrid())
    .replace(/<!--ivx:form-->/g, () => applyForm());
}
