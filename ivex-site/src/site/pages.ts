// Pages rendered from content.ts: the services index, one page per service and
// the contact page. vite.config.ts writes them to disk before Vite reads its inputs.

import { SERVICES, SITE_URL, servicePath, type Service, type Shape } from "./content";
import { applyForm, contactGrid, footer, head, header, helixCta, serviceList, serviceWaText, waSlab, waUrl, type Meta, type NavKey } from "./layout";

export type GeneratedPage = { file: string; html: string };

const PROVIDER = { "@type": "ProfessionalService", name: "IVEX Medya", url: `${SITE_URL}/` };

function page(meta: Meta, nav: NavKey, main: string) {
  return `<!doctype html>
<!-- Generated from src/site/pages.ts; edit the content there, not this file. -->
<html lang="tr">
  ${head(meta)}
  <body>
    ${header(nav)}
    <main id="icerik" class="ivx-page">
${main}
    </main>
    ${footer()}
  </body>
</html>
`;
}

const STEPS = [
  ["Tanışalım.", "WhatsApp'tan yazın ya da formu doldurun. Markanızı, hedefinizi ve bütçenizi dinleyelim."],
  ["Planlayalım.", "İhtiyacınıza uygun kapsamı ve size özel teklifimizi hazırlayıp onayınıza sunalım."],
  ["Başlayalım.", "Uygulamaya geçer, sonuçları düzenli takip eder ve size raporlarız."],
];

// Each service page walks through four shapes; keep neighbours distinct.
function shapeTrail(own: Shape): Shape[] {
  const second: Shape = own === "cloud" ? "helix" : "cloud";
  const third: Shape = own === "ring" ? "helix" : "ring";
  return [own, second, third, "mark"];
}

function servicePage(s: Service, i: number): GeneratedPage {
  const n = String(i + 1).padStart(2, "0");
  const [heroShape, scopeShape, flowShape, closeShape] = shapeTrail(s.shape);
  const others = SERVICES.filter((o) => o !== s);
  const items = s.items.map((item, k) => `<li><span class="ivx-scope__n" aria-hidden="true">${String(k + 1).padStart(2, "0")}</span>${item}</li>`).join("\n              ");
  const steps = STEPS.map(
    ([title, text], k) => `<li class="ivx-step">
              <span class="ivx-step__n">0${k + 1}</span>
              <h3>${title}</h3>
              <p>${text}</p>
            </li>`,
  ).join("\n            ");
  const wa = waUrl(serviceWaText(s));
  const main = `      <section class="ivx-hero ivx-sub-hero" data-shape="${heroShape}" data-side="right" data-x="0.5" aria-labelledby="svc-title">
        <div class="ivx-wrap ivx-hero__content">
          <nav class="ivx-crumbs ivx-rise" aria-label="Sayfa konumu"><a href="/hizmetler/">Hizmetler</a><span aria-hidden="true">/</span><span>${n}</span></nav>
          <h1 id="svc-title" class="ivx-sub-hero__title ivx-rise" style="--d: 80ms">${s.name}</h1>
          <p class="ivx-sub-hero__lead ivx-rise" style="--d: 180ms">${s.lead}</p>
          <div class="ivx-hero__ctas ivx-rise" style="--d: 280ms">
            ${helixCta("WhatsApp'tan Bilgi Al", wa)}
            <a href="#kapsam" class="ivx-textlink">Neler yapıyoruz <span aria-hidden="true">↓</span></a>
          </div>
        </div>
      </section>

      <section id="kapsam" class="ivx-chapter ivx-chapter--fit ivx-scope" data-shape="${scopeShape}" data-side="right" data-x="0.62" data-scale="0.8" data-dim="true" aria-labelledby="scope-title">
        <div class="ivx-wrap">
          <h2 id="scope-title" class="ivx-h2">Neler yapıyoruz?</h2>
          <ul class="ivx-scope__list">
              ${items}
          </ul>
          <div class="ivx-scope__for">
            <span class="ivx-cap">Kimler için</span>
            <p>${s.audience}</p>
          </div>
        </div>
      </section>

      <section class="ivx-chapter ivx-chapter--fit ivx-flow" data-shape="${flowShape}" data-side="right" data-x="0.62" data-scale="0.8" data-dim="true" aria-labelledby="flow-title">
        <div class="ivx-wrap">
          <h2 id="flow-title" class="ivx-h2">Nasıl çalışıyoruz?</h2>
          <ol class="ivx-steps ivx-steps--flat">
            ${steps}
          </ol>
        </div>
      </section>

      <section class="ivx-chapter ivx-chapter--fit ivx-svc-close" data-shape="${closeShape}" data-side="right" data-x="0.66" data-scale="0.8" aria-labelledby="close-title">
        <div class="ivx-wrap">
          <h2 id="close-title" class="ivx-closing"><span>${s.name}</span><span>için konuşalım.</span></h2>
          <div class="ivx-svc-close__cta">${waSlab(wa)}</div>
          <div class="ivx-others">
            <span class="ivx-cap">Diğer hizmetlerimiz</span>
            ${serviceList(others)}
          </div>
        </div>
      </section>`;
  const meta: Meta = {
    title: `${s.name} | IVEX Medya`,
    description: s.lead,
    path: servicePath(s),
    jsonLd: { "@context": "https://schema.org", "@type": "Service", name: s.name, description: s.lead, serviceType: s.name, areaServed: "TR", provider: PROVIDER, url: `${SITE_URL}${servicePath(s)}` },
  };
  return { file: `hizmetler/${s.slug}/index.html`, html: page(meta, "hizmetler", main) };
}

function servicesIndex(): GeneratedPage {
  const main = `      <section class="ivx-hero ivx-sub-hero" data-shape="ring" data-side="right" data-x="0.5" aria-labelledby="services-title">
        <div class="ivx-wrap ivx-hero__content">
          <p class="ivx-kicker ivx-rise">Hizmetler</p>
          <h1 id="services-title" class="ivx-sub-hero__title ivx-rise" style="--d: 80ms">Markanız için uçtan uca dijital hizmetler.</h1>
          <p class="ivx-sub-hero__lead ivx-rise" style="--d: 180ms">Tek bir hizmet ya da uçtan uca yönetim: ihtiyacınıza göre birlikte planlıyoruz. Detayları görmek için bir hizmet seçin.</p>
          <div class="ivx-hero__ctas ivx-rise" style="--d: 280ms">
            <a href="#liste" class="ivx-textlink">Hizmetlerimiz <span aria-hidden="true">↓</span></a>
          </div>
        </div>
      </section>

      <section id="liste" class="ivx-chapter ivx-chapter--fit" data-shape="helix" data-side="right" data-x="0.55" aria-labelledby="list-title">
        <div class="ivx-wrap">
          <h2 id="list-title" class="ivx-h2">Hizmetlerimiz</h2>
          ${serviceList()}
        </div>
      </section>

      <section class="ivx-chapter ivx-chapter--fit ivx-svc-close" data-shape="mark" data-side="right" data-x="0.66" data-scale="0.8" aria-labelledby="close-title">
        <div class="ivx-wrap">
          <h2 id="close-title" class="ivx-closing"><span>Hangisi size uygun?</span><span>Birlikte karar verelim.</span></h2>
          <div class="ivx-svc-close__cta">${waSlab()}</div>
        </div>
      </section>`;
  const meta: Meta = {
    title: "Hizmetler | IVEX Medya",
    description: "Sosyal medya yönetimi, içerik üretimi, reklam, marka stratejisi, web tasarım, video ve TikTok, influencer marketing.",
    path: "/hizmetler/",
  };
  return { file: "hizmetler/index.html", html: page(meta, "hizmetler", main) };
}

function contactPage(): GeneratedPage {
  const main = `      <section class="ivx-hero ivx-sub-hero ivx-contact-hero" data-shape="chat" data-side="right" data-x="0.62" data-scale="0.9" aria-labelledby="contact-page-title">
        <div class="ivx-wrap ivx-hero__content ivx-contact__inner">
          <p class="ivx-kicker ivx-rise">İletişim</p>
          <h1 id="contact-page-title" class="ivx-sub-hero__title ivx-rise" style="--d: 80ms">Markanız için konuşalım.</h1>
          <p class="ivx-sub-hero__lead ivx-rise" style="--d: 180ms">WhatsApp'tan yazın, formu doldurun ya da e-posta gönderin; en kısa sürede dönüş yapalım.</p>
          <div class="ivx-rise" style="--d: 280ms">
          ${contactGrid()}
          </div>
        </div>
      </section>

      <section id="basvuru" class="ivx-chapter ivx-chapter--fit ivx-apply" data-shape="ring" data-side="right" data-x="0.5" data-scale="0.9" aria-labelledby="apply-title">
        <div class="ivx-wrap">
          <div class="ivx-apply__col">
            <p class="ivx-kicker">Başvuru</p>
            <h2 id="apply-title" class="ivx-apply__title">Sizi arayalım.</h2>
            <p class="ivx-apply__lead">Adınızı ve iletişim bilgilerinizi bırakın, ekibimiz en kısa sürede size dönsün.</p>
            ${applyForm()}
          </div>
        </div>
      </section>`;
  const meta: Meta = {
    title: "İletişim | IVEX Medya",
    description: "IVEX Medya ile WhatsApp, e-posta ya da form üzerinden iletişime geçin. Fulya Mah., Şişli, İstanbul.",
    path: "/iletisim/",
  };
  return { file: "iletisim/index.html", html: page(meta, "iletisim", main) };
}

export function generatedPages(): GeneratedPage[] {
  return [servicesIndex(), ...SERVICES.map(servicePage), contactPage()];
}
