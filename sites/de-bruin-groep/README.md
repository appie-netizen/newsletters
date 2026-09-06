# De Bruin Groep

Dutch B2B contractor for temporary/permanent traffic measures (verkeersmaatregelen) on
road, water and ground-construction projects. Original site: https://www.debruingroep.nl/

## Status

Code built directly (skipped v0.dev per user request — see decisions log). Real
image assets (logo, photos, partner logos, certificate scans, favicon) extracted
from debruingroep.nl and wired in — all placeholders gone except the "Advies &
ontwerp" service tile (no matching photo on the live site). Locally verified
(build clean, home/certificaten/contact at 1440/768/375), pushed to GitHub.
Waiting on Vercel import.

## Links

- **Live audit** (3-framework: brand/anti-slop, UI principles, UX — 8 pages crawled):
  https://claude.ai/code/artifact/fa2203ad-313d-47ab-b607-eafaf2667d50
- **Mockup** (Claude Design canvas — editable, home desktop/mobile + certificaten + contact):
  https://claude.ai/code/artifact/ee523302-a8e8-4641-811b-7796ed948296
- **Code**: `de-bruin-groep-website/` in this folder — own GitHub repo at
  https://github.com/appie-netizen/de-bruin-groep-website (private)
- **Deploy**: not yet imported to Vercel

## Real facts pulled from the client's own live-site HTML (not fabricated)

- Address: Zwanenburgerdijk 22d, 2141 BM Vijfhuizen
- Office phone: 085-0817520 · Emergency: 06-29282881
- Email: info@debruingroep.nl
- KvK 78403588 · BTW NL861378593B01
- These are wired into `lib/site.ts` and a live Google Maps embed on `/contact`
  (no API key needed — uses the public `maps?q=...&output=embed` form)

## Brand direction

**Like-for-like redesign, not a rebrand.** Unlike De Jonge Admiraal, this client keeps
their existing brand as-is: orange `#DE5307` + black + white, the existing wordmark/logo,
their real photography (trucks, cones, controllers) and all existing content/copy
(services, five stated values, certifications, partner names). The audit found the brand
itself is fine — the site built on top of it (Jouwweb template) is not: broken font
loading, empty H1, no real hierarchy, 3+3 accessibility hard-gate failures across 8 pages,
a cookie banner that overlaps content everywhere, and a mobile trust-bar that breaks.

## Decisions log

- **Skipped v0.dev entirely for the build.** User asked to have Claude write the
  production code directly instead of routing through v0 — the local Node/build/
  screenshot/verify loop (proven on De Jonge Admiraal) makes this workable now.
  Structure copied from the De Jonge Admiraal project's proven skeleton
  (Next.js 16.3.3 + Tailwind v4 `@theme` tokens + TypeScript), content/design from
  this project's own audit and canvas mockup.
- Logo placeholder replaced: `components/logo.tsx` now renders the real
  `public/logo.png` (extracted from the live site, 1200×151). Favicon set via
  `app/icon.png`.
- Image assets extracted from `.tmp/audit_de-bruin-groep/html/*.html` → downloaded
  → optimised → placed under `public/{photos,partners,certificaten}/`. The live
  "Onze relaties" = 3 auto-rotating fotorama carousels holding **24 logos total**
  (NOT 6 — the captured DOM only had the 2 loaded frames per carousel; re-scraped
  by watching the carousels cycle ~40s with Playwright, see
  `scratchpad/partners_all/`). All 24 placed under `public/partners/` (flattened
  onto white), rendered as a CSS marquee (`components/partners.tsx` +
  `marquee-track` in globals.css; pauses on hover; reduced-motion stops it).
  Lesson: a fotorama/slick/swiper carousel only puts a couple of slides in the
  DOM — cycle it live to get the full set.
  Certificate files are full Kiwa document scans (not badges), shown as
  thumbnails on `/certificaten` that link to the full-size image. Some work photos
  carry visible licence plates / faint watermarks — acceptable, they're the
  client's own published imagery.
- Pinned `next` to `16.3.3` specifically — an earlier guess at `15.1.3` carried a
  known CVE (npm flagged 2 high + 1 critical on install); always check `npm install`
  output for vulnerability warnings before treating a fresh scaffold as done.
- **Art-direction pass (commit `aec545a`).** Client benchmarked against
  malverkeersservice.nl (holds up / we're ahead) and versluysverkeerstechniek.nl
  (we were behind). Captured both with `capture_site.py` (`.tmp/audit_comp-mal`,
  `.tmp/audit_comp-versluys`). Chosen direction: **industrieel/stoer**.
  - Typography: dropped Quicksand + Open Sans for **Archivo** variable via
    `next/font/google` with `axes: ['wdth']` (this DOES build under Next 16 /
    next-font — no `weight` when you request an axis). Headings weight 800 at
    `font-variation-settings: 'wdth' 122`, tight tracking. `@utility eyebrow`
    (uppercase, wdth 110, 0.16em) + uppercase buttons = the industrial signal.
  - Layout: full-bleed photo hero w/ gradient scrim + `clamp()` headline to
    4.75rem; every home section a full-width band with its own ground for
    chapter rhythm; `--shadow-card`/`--shadow-lift` tokens + hover-lift on
    service cards; new full-orange `CtaBand` pre-footer; sticky translucent
    header; `/certificaten` rebuilt as a 2-col card grid (was sparse rows).
- **Typeface swap (commit `2158ede`).** Archivo felt characterless / off-brand
  to the client. Now **Oswald** (condensed) for display + **Barlow** for body.
  Oswald in caps = roadwork/traffic-signage register, right for this sector.
  h1/h2 uppercase via globals; card titles are h3 (sentence case so "96b"
  stays lowercase). Removed the `wdth`-axis / `display-x` expansion logic.
- **Kiwa attribution (same commit).** The certs are Kiwa-issued but that only
  showed inside the scans. Cropped the Kiwa mark from `iso.png` →
  `public/kiwa.png`; "Afgegeven door [Kiwa]" credit on `/certificaten` hero
  and the home certifications band.
- **Polish pass (commit `eef29f7`).** Client wanted the Versluys-level finish.
  Added: staggered `rise-in` hero entrance (settles ~1s, off under
  prefers-reduced-motion); `background-attachment: fixed` photo behind the
  certifications band under an 82% scrim (parallax "image stays put"); the
  24-logo relaties marquee. Logo cone glyph knocked fully **transparent**
  (was black) so it needs no per-background variant.

## Key facts (from the audit, for reuse in the mockup/build)

- Services: Advies & ontwerp, Uitvoering Tijdelijke Verkeersmaatregelen, Calamiteiten
  (emergency response), Inzet Verkeersregelaars (traffic-controller staffing)
- Certifications: ISO 9001, BRL 9101 96b, VCA, CO2-Prestatieladder, Safety Culture Ladder
  Trede 2; works under CROW 96a/96b and RAW/EMVI procurement frameworks
- Five values: Snel, Meedenkend, Samenwerken, Ontzorgen, "Nee bestaat niet"
- Emergency line: 06-29282881 (after 17:00 and weekends)
- Partners named: Fronik, R. Breure, Van Voskuilen Infratechniek
- Measured brand orange: `#DE5307`
