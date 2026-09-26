# IVEX Medya website: handoff

## Status (2026-09-26): done, live and listed

- Live site: https://ivexmedya.higgsfield.app
- Community feed listing: https://higgsfield.ai/supercomputer/apps/406f54f6-8ac0-44e6-9f48-59b794f39ef2/view
- No credits spent in the finishing session (still 4 on the free plan).

What was built (in the Higgsfield site repo, not this GitHub repo):
`app/design-brief.md`, `app/src/routes/index.tsx` (nav, hero, about, services,
approach, contact, footer, JSON-LD), `app/src/routes/__root.tsx` (Turkish head kit,
no Quanta), `app/src/components/ivex/*` (wordmark, one component per CTA, C2
particle hero), brand tokens and section CSS appended to `app/src/styles.css`,
WebP images + favicons + `site.webmanifest` in `app/public/`, and
`app/src/app-meta.json` filled (title, description, OG image, cover, icon).

Follow-up (same day):

- Added `/hakkimizda` (Hakkımızda) with the user's text verbatim, a shared
  nav/footer (`app/src/components/ivex/site-chrome.tsx`) and a link from the home
  about section. Live.
- References section is built but hidden: fill `CLIENT_BRANDS` and
  `CLIENT_REVIEWS` in `app/src/components/ivex/references.tsx` with the user's
  REAL client names and reviews (never invented), then deploy.
- Custom domain: Higgsfield offers it only on paid plans (the account is on the
  free plan); it is set in Higgsfield's website settings, not via the tools.
  Once connected, update `SITE_URL` in `contact.ts` and `__root.tsx`.
- Open question to the user: switch the site name from "IVEX Medya" to
  "IVEX & CO" everywhere?

Notes for the next session:

- Site access now goes through the Higgsfield connector (brokered mode):
  `website_repo_access` checkout/push plus `sandbox_exec`. No CLI login or git
  token is needed. Edit only inside the Higgsfield sandbox checkout.
- The sandbox's Node 20.9 is too old for Vite 7: install bun with
  `npm i -g bun@1.2 --prefix /home/user/.bunroot`, then `bun run typecheck` and
  `HF_DESIGN_INSPECTOR=1 bun --bun x vite build` work.
- The cover script's hosted Inter font and logo glyph returned 403; Inter was
  pulled from google/fonts into `~/.cache/higgsfield-cover/Inter-Variable.ttf`.
  The cover lockup uses the user's brand (`Dijital Büyüme Ajansı` /
  `IVEX MEDYA` / `ivexmedya.higgsfield.app`), not the Higgsfield wordmark.
- Fonts load from Google Fonts (allowed by the template CSP), so no dependency
  or lockfile change was needed.

---

Continuation notes for the IVEX Medya marketing website, built with the
Higgsfield website builder (`higgsfield-websites` skill, `--type website`).
The previous session could not finish because its network policy blocked
`apps-repos.higgs.ai` (site repo) and `d8j0ntlcm91z4.cloudfront.net`
(generated images). Both hosts are now in the environment's allowed domains,
so a new session can pick up from here.

The user writes in Turkish and is not technical: reply in Turkish, speak in
product terms (no repo/commit/deploy jargon).

## Already done (do not redo)

- **Higgsfield site created.** `website_id` `b65aeea0-8f40-42a8-86ce-653c517c4e79`,
  type `website`, category `ads-marketing`, subdomain `ivexmedya`,
  live URL `https://ivexmedya.higgsfield.app` (still the empty scaffold).
  Do NOT run `higgsfield website create` again.
- **Three images generated** (nano_banana_pro, 2k, 2 credits each). Download
  them into `app/public/assets/`:
  - hero, 3:2: `https://d8j0ntlcm91z4.cloudfront.net/user_3JXawO4gix7o6qCVFZUSleeGhdV/hf_20260926_155047_7af10216-f45d-46a4-9c92-963d00a4a120.png`
    (glowing emerald particle double helix rising out of translucent green
    glass stairs, floating glass props: play-button prism, lens, heart gem,
    megaphone; empty dark-green space on the left third for the headline).
    Also reuse this as the cover art (saves credits).
  - services, 4:5: `https://d8j0ntlcm91z4.cloudfront.net/user_3JXawO4gix7o6qCVFZUSleeGhdV/hf_20260926_155047_b1bb2532-7e57-4add-bc33-49f55830cc14.png`
    (dark green glass phone-shaped slab in front of an emerald ring light,
    floating glass play button, heart, camera, speech bubble).
  - approach, 21:9: `https://d8j0ntlcm91z4.cloudfront.net/user_3JXawO4gix7o6qCVFZUSleeGhdV/hf_20260926_155047_d8a96f56-4102-4b79-a6f3-a010d5a34910.png`
    (white light beam through three ascending emerald glass prisms, ending in
    a green burst).
  Glance at them once for model-rendered text or glitches before using.
- **Credits:** 4 left on the free plan. Everything else must be built without
  new generations, except at most one re-roll if an image is unusable.

## New-session setup

1. Higgsfield login lives in the container, so it is gone. Run
   `higgsfield auth login` in the background; the browser cannot reach the
   container's `localhost:8765` callback, so give the user the authorize URL
   from the generated `sign-in.html`, have them approve, then paste back the
   full `http://localhost:8765/callback?code=...&state=...` URL, and forward it
   with `curl --noproxy localhost '<pasted url>'` before it expires.
2. `higgsfield workspace set 8d47e091-3328-45ec-aa89-d0459c014048` (the user's
   only workspace, "Private").
3. `higgsfield website repo-access b65aeea0-8f40-42a8-86ce-653c517c4e79 --json`,
   clone with a credential helper that reads the token from that JSON. Never
   print or commit the token.

## User decisions (final)

- Website only, no logo design.
- **Non-animated.** Brief line: `Animation mode: non-animated — user picked "Sade" (non-animated) at intake`.
  The user saw that the animated option needs more credits and chose "Sade".
- **Publish to the Higgsfield community feed: yes.** After deploy with cover +
  metadata filled, run `higgsfield website publish` without asking again.
- **Colors:** green, deep green, black, white (the user's explicit brand colors,
  so the "near-black + green accent" default ban is overridden; say so in the
  brief).
- **Style references the user sent** (inspiration only, never copy): a DNA
  helix dissolving into particles on black with warm/blue light; a Brazilian
  agency post with glowing lime glass stairs on black; a dark crypto landing
  page with lime accents, big geometric sans headlines and numbered cards; a
  black hero with huge spaced-out wordmark over a glass 3D blob; a black
  security site with huge lowercase type over glowing glass blobs. Common
  thread: dark ground, glowing glass/particle 3D, big confident geometric
  sans type, a single green accent.

## Exact user copy (keep verbatim)

- Brand as shown on Instagram: `IVΞX MEDYA | Dijital Büyüme Ajansı`
- Instagram bio services: `Sosyal Medya • Reklam • İçerik` / `Video • TikTok • Influencer marketing`
- Slogan: `Markanızı sadece görünür değil, fark edilir hale getiriyoruz.`
- About: `IVEX Medya; sosyal medya yönetimi, içerik üretimi, reklam, marka stratejisi, web tasarım ve influencer marketing hizmetleriyle markaların dijital dünyadaki gücünü büyütür.`
- Pillars: `Doğru strateji. Güçlü içerik. Gerçek etki.`
- Closing line: `IVEX Medya — Markan için daha fazlası.` The em-dash is banned on the
  page, so render it as two stacked lines: `IVEX Medya` / `Markan için daha fazlası.`

Contact (all visible on the site):

- Phone and WhatsApp: `+90 501 062 37 94` (`tel:+905010623794`, `https://wa.me/905010623794`)
- E-mail: `ivex.co.tr@gmail.com`
- Instagram: `@ivex.tr` (`https://www.instagram.com/ivex.tr/`)
- Address: `Fulya Mah., Mecidiyeköy, İstanbul, Türkiye`

No numbers, client counts, testimonials or client logos: the user gave none,
so invent none.

## Design plan (Phase 0 draft)

- **Concept spine:** "Markanın DNA'sı". IVEX reads a brand's DNA and grows
  it; the particle helix is the motif.
- **Tier:** editorial-leaning cinema, non-animated path.
- **Tier-1 technique:** `C2 — Particle dissolve` on the hero. Render the hero
  image as a normal `<img>` (SSR, always visible); on mount, for fine
  pointers without reduced motion, overlay a canvas that draws the image
  dimmed and samples the bright helix pixels into particles that scatter away
  from the cursor and spring back. Pause the RAF when off-screen. Coarse
  pointers and reduced motion keep the static image.
- **Palette:** ground `#07100C`, deep green surface `#0B2A1D`, deep green
  line `#123D2B`, accent green `#34D27B`, text `#F2F5F3`, muted `#9FB3A8`.
  One accent, dark page throughout.
- **Type:** Outfit (display and body) + IBM Plex Mono (small labels). Both
  cover Turkish (latin-ext). Self-host via `@fontsource`.
- **Wordmark:** text `IV` + a CSS/SVG "Ξ" drawn as three horizontal bars in
  the accent + `X`, then `MEDYA`. Favicon: the three-bar Ξ on the dark ground.
- **Corners:** soft 14px on image frames and panels, nothing else rounded
  except the circular Instagram badge.
- **Sections (distinct layout families):**
  1. Nav: wordmark, links Hizmetler / Yaklaşım / İletişim, WhatsApp CTA.
  2. Hero, split: slogan as headline (left), pillars as subtext, primary CTA
     `WhatsApp'tan Yaz`, secondary text link to Hizmetler; hero image right
     with the particle canvas.
  3. About, full-width statement: the about paragraph in large type.
  4. Services, index list + sticky image: seven rows (Sosyal Medya Yönetimi,
     İçerik Üretimi, Reklam, Marka Stratejisi, Web Tasarım, Video ve TikTok,
     Influencer Marketing), each with a one-line factual description; row
     hover shifts grade and slides an index digit; services image sticky on
     the right (stacks on mobile).
  5. Approach, full-bleed image band: the approach image with the three
     pillars as three steps (Strateji, İçerik, Etki) overlaid.
  6. Contact: closing line as two stacked lines, huge phone number as the
     hit area (tel link), WhatsApp CTA, e-mail as a mono readout, address,
     circular spinning `@ivex.tr • Instagram •` text-on-a-path badge.
  7. Footer: wordmark, contact links, `© 2026 IVEX Medya`.
- **CTA garments (each its own component):** nav WhatsApp link decodes its
  label on hover (mono scramble); hero CTA underline is an animated helix
  waveform; service rows shift grade with a sliding index digit; phone number
  is an oversized glyph hit area; e-mail uses a corner-bracket viewfinder;
  Instagram is the spinning circular badge. One label per intent:
  `WhatsApp'tan Yaz` everywhere for WhatsApp.
- **No contact form:** direct WhatsApp, phone and e-mail links only (no D1).

## Remaining steps

1. Write `app/design-brief.md` from the plan above and commit it.
2. Build the page to this plan (skip generated reference boards: no credits;
   the user's style references stand in for them).
3. Head kit: favicon (svg + png sizes drawn locally with Pillow),
   apple-touch-icon, 192/512 + maskable, `site.webmanifest`, `theme-color`,
   full OG/Twitter block with absolute URLs on `https://ivexmedya.higgsfield.app`.
4. Cover per `app-cover.md`: compose from the hero art (no new generation),
   upload `_og.png` and `_cover.png` with `higgsfield upload create`, fill
   `app/src/app-meta.json` (`og_title` `IVEX Medya`, Turkish
   `og_description`, `favicon_url`, `og_image_url`, `marketplace_cover_url`).
5. Mechanical gate (`review-rubric.md` §A), `bun run typecheck`, deploy,
   then publish to the community feed and send the user both links.
