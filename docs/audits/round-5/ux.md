# UX audit, round 5: the first real photos on the website

Agent "ux". Scope per the brief: the public website only (home, about, brownouts, net-metering, the estimate page frame, privacy, 404) at 1280×900 and 390×844 (DPR 2, touch), the home page also at 560, 639, 640, 760, 899, 900, 1024 and 1600 px, the header across 740–1000 px in 20 px steps, and the preview build with placeholders. Read first: `docs/audits/round-5/brief.md`, DECISIONS.md "Guard rails" (the 390 px no-sideways-scroll promise, the wording glossary, the website sticky bar), and the round-4 UX report for its website findings (it has none beyond the Settings › Website page; round 3 recorded the website at both widths as clean, the 404 page with a way back and the estimate's sticky bar hidden while the form is in view; none of those are repeated here).

## Setup and method

- Baseline: `site/dist` as served read-only on 127.0.0.1:8195, commit `9fbcf5f` ("The website's first real photos…"). The md5 of the served `index.html` matched `site/dist/index.html` at the start and the end of the audit, so every number below is for that build. While the audit ran, another agent edited the working tree (`site/pages/index.html`, `site/layout.html`, `site/static/site.css`, `site/build.py`, the hip-roof crop, `og-home.jpg`): the first installations card now uses the angle shot, the captions changed, `og:image:alt` and a per-page `og_image` were added, and a `.photo-card.wide` rule appeared. Findings those edits already close are marked **in hand**. Nothing in the repository was modified by me; `site/dist` was not rebuilt.
- Preview with placeholders: `backend/.venv/bin/python site/build.py <scratch>/dist-preview --with-placeholders`, served on 127.0.0.1:8196 (stopped at the end).
- Production-like run: `/api/quick/status` answered by Playwright with a filled profile (name, phone, Messenger, Facebook, e-mail, PEE and license, brands, four warranty lines) after a 600 ms delay, to see what visitors see while the fetch is in flight and the shift when it lands. The console 404s on the static server are out of scope as the brief says; what the markup shows before the fetch answers is not, because production shows the same thing for the duration of the round trip.
- Scripts (NODE_PATH=/opt/node22/lib/node_modules, run from /home/user/solarapp): `lib.js` (the in-page audit: scroll width, elements past the viewport, text under 16 px, tap targets under 44 px, WCAG contrast of every text leaf, meta tags, image choice; a `PerformanceObserver` for `layout-shift` installed before navigation; transferred bytes from the response events; a Tab walk), `walk.js` (every page × both widths), `widths.js` (the home page at the eight widths), `preview.js` (8196, home and about at 1280, 390 and 760), `profile.js` (the production-like run), `extra.js` (sticky header and menu shots with smooth scrolling off, focus rings, the header sweep). Results in `walk-report.json`, `widths-report.json`, `preview-report.json`, `profile-report.json`, `extra-report.json`. Image and font experiments in `imgtest/`.
- Screenshots in `shots/` (prefixes: `d-` desk 1280×900, `p-` phone 390×844 DPR 2, `w<width>-` the sweep, `pv-` the preview build, `pf-` the production-like run; `view/` holds downscaled contact sheets of the full pages and the crops named below). All paths in this report are under `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents5/ux/`.
- Note for whoever re-runs the scripts: `html { scroll-behavior: smooth }` animates `window.scrollTo` too, so a screenshot taken 300 ms after a programmatic scroll is mid-flight; `extra.js` injects `scroll-behavior: auto` first.

## Verdict in one paragraph

The photo work itself is sound. Every page is exactly the viewport wide at every width tried (1280, 390, 560, 639, 640, 760, 899, 900, 1024, 1600); the hero and the three cards keep their 4:3 slot (`width`/`height` plus `aspect-ratio`) so the images contribute nothing to layout shift; the `<picture>` picks WebP in Chromium, the 480 file on a 1x desk (card slot 301 px) and the 960 on the phone (332 CSS px at DPR 2); every photo carries an alt; the cards are lazy and the hero is `fetchpriority="high"`; the three cards are the same height in a row (382 px at 1280) and their caption text aligns with the text of the plain cards (21 px from the card edge in both). What is wrong sits next to the photos rather than in them: the two most prominent gold texts fail contrast (the header's "Free estimate" is white on gold at 2.42:1 because `.nav a` outranks `.btn-gold`; the hero eyebrow is the white-page gold on black at 3.66:1), the header breaks into two-line links between 760 and 859 px (iPad portrait), the "How it works" anchor lands under the sticky header, every page shows dangling punctuation ("signed and sealed by , Professional Electrical Engineer, PRC No. .") until the profile fetch answers, the font swap moves the prose by 24–30 px (CLS 0.17 on About, 0.27 with the profile fill), the hero photo's frame renders as a light hairline over a shadow that is invisible on black, and the phone downloads 721 KB for the home page where 430 KB would do. All of it is CSS and HTML, and most of it is one line each.

## Measurements

| Page | 1280×900: scrollWidth / height / CLS at load / bytes | 390×844: scrollWidth / height / CLS / bytes first screen → whole page |
|---|---|---|
| Home | 1280 / 4,371 / 0.016 / 518 KB | 390 / 8,155 / 0.000 / 370 KB → 721 KB |
| About | 1280 / 1,513 / **0.168** (0.273 with the profile) / 193 KB | 390 / 2,334 / 0.000 (0.014 with the profile) / 193 KB |
| Brownouts | 1280 / 1,856 / 0.001 / 192 KB | 390 / 2,880 / 0.000 / 192 KB |
| Net metering | 1280 / 2,418 / 0.042 / 193 KB | 390 / 3,340 / 0.000 / 193 KB |
| Estimate (frame) | 1280 / 900 / 0.000 / 190 KB | 390 / 844 / 0.000 / 190 KB |
| Privacy | 1280 / 1,729 / 0.011 / 193 KB | 390 / 2,731 / 0.000 / 193 KB |
| 404 | 1280 / 900 / 0.002 / 189 KB | 390 / 884 / 0.000 / 189 KB |

Home page bytes by type at 1280: WebP 316 KB (hero 960: 169 KB; cards 480: 46 + 52 + 49 KB), fonts 146 KB (three TTFs of 47–48 KB), logo PNG 26 KB (1083×1079 for a 36 px slot), HTML 17 KB, CSS 10 KB, JS 2.5 KB. At 390: hero 960 WebP 169 KB in the first screen; the three card WebPs (169, 169, 181 KB) load on scroll. The other pages are the fonts and the logo plus 5–8 KB of HTML.

Image choice (`img.currentSrc`): cards `*-480.webp` at 640–1280 (1x), `*-960.webp` at 390 DPR 2 and at 1600; hero `rib-roof-eight-960.webp` at 390, 560–899, 1280 and 1600, `-480.webp` at 900–1024. Hero slot: 450×338 px at 1280 and 1600, 443×332 at 1024, 385×289 at 900, 867×650 at 899, 728×546 at 760, 358×269 at 390. Hero band height: 603 px at 1280, 700 at 900, 1,191 at 899, 1,117 at 760, 1,031 at 390. Header: 63 px; 75 px with wrapped links at 760–859.

Contrast (computed from the rendered colors): header "Free estimate" white on #C9A227 **2.42:1**; hero eyebrow #856a14 on #111 **3.66:1**; eyebrow on the off-white 4.73:1 and on white 5.16:1 (pass); gold #C9A227 on #111 7.81:1; muted #6b6b66 on white 5.36:1, on the off-white 4.91:1; footer muted #b8b8b2 on #111 9.47:1; placeholder label #6b6b66 on the stripes 4.05–4.40:1 (preview only).

Tap targets under 44 px: FAQ `summary` 33 px (six rows, 8 px apart) on both widths; footer "Privacy notice" 21 px; "Read about solar with a battery" (net-metering) 19 px; the footer contact links 19 px with 6 px gaps once the profile fills; the brand link 36 px. The Menu button is 77×44, the open menu's rows 45 px and the gold button 48 px (`p-home-menu.png`).

Text under 16 px on the phone (unique): brand tag 10.5 px; `.card .tag` 12 px; eyebrows 12.5 px; `.steps .when` and `.figure .lab` 13 px; `.small` 13.5 px (the photo captions, the footer copy, the copyright, the Privacy notice link, the net-metering note); brand name 14 px; hero points 14.5 px; footer headings 15 px.

Focus: Tab order on every page is skip link → brand → Home → Brownouts → Net metering → About us → Free estimate → the page's first button (on the phone: skip → brand → Menu → page button); the browser's default ring is visible on the dark header, the gold buttons, the cards and the summaries (`d-focusring-1…10.png`), but it is the 1 px two-tone ring and the site sets none of its own.

## Defects, ranked (A blocks a task, B confuses, C cosmetic; effort S an hour, M half a day)

Nothing blocks a visitor from reaching the estimate; there is no A. The B items are the ones a visitor would notice or trip on.

### B1. The header's "Free estimate" button is white on gold, 2.42:1 (every page, both widths, and the open phone menu)
- Screens: `view/crop-d-header.png`, `p-home-menu.png`, `d-home-top.png`.
- Element: `.nav a.btn.btn-gold` (`site/layout.html:35`), `site/static/site.css:34` and `:45`.
- Cause: `.nav a { color: #fff }` (specificity 0,1,1) beats `.btn-gold { color: var(--ink) }` (0,1,0). The footer already carries the correction (`.site-foot .btn-gold { color: var(--ink) }`, css:144); the header does not.
- Fix: `.nav .btn-gold { color: var(--ink); }` next to the footer rule, or raise `.btn-gold` to `a.btn-gold`. Dark on gold is 7.81:1. S.

### B2. The hero eyebrow is the white-page gold on black, 3.66:1 at 12.5 px (home, brownouts, net-metering; on the phone it wraps to two lines and is the first line a visitor reads)
- Screens: `d-home-top.png`, `p-home-top.png`, `d-brownouts-top.png`, `p-net-metering-top.png`.
- Element: `.hero .eyebrow` (`site/pages/index.html:8`, `brownouts.html:7`, `net-metering.html:7`); css:57–58.
- Cause: `.eyebrow` uses `--gold-text` (tuned to pass on white) and only `.section.dark .eyebrow` switches to `--gold`; the hero is `.hero`, not `.section.dark`.
- Fix: `.hero .eyebrow { color: var(--gold); }` (7.81:1). S.

### B3. The header breaks between 760 and 859 px: links wrap to two lines, the brand tag wraps, the bar grows to 75 px (iPad portrait is 768)
- Screens: `w780-header.png`, `w760-home-top.png`, `view/w760-home-full-sheet.png`; the sweep in `extra-report.json` (`nav`): wrapped at 760, 780, 800, 820, 840; clean from 860.
- Element: `.nav` at `@media (min-width: 760px)` (css:38–41); `.brand-tag` (css:32).
- Cause: the nav shows at 760 but the brand (267 px) plus five items with 22 px gaps need about 860 px.
- Fix: either move the breakpoint to 860 (the Menu button serves 760–859) or, at 760–859, `.nav { gap: 14px } .nav a { white-space: nowrap } .brand-tag { display: none }`. Match the hero's 900 if the two should turn together. S.

### B4. "How it works" scrolls the section under the sticky header
- Screens: `d-home-how-anchor.png`, `p-home-how-anchor.png`; `walk-report.json` → `anchor`: section top 0, eyebrow 41–60, header bottom 63, h2 top 68.
- Element: `a[href="#how"]` (`index.html:13`) → `#how` (`index.html:53`); the header is `position: sticky` (css:28).
- Cause: no `scroll-margin-top` for the 63 px sticky header; the eyebrow is hidden and the heading touches the gold rule.
- Fix: `[id] { scroll-margin-top: 76px; }` (covers `#how`, `#work`, `#main` for the skip link). S.

### B5. Profile-dependent fragments render empty until the fetch answers, and stay empty when it fails
- Screens: `view/crop-d-home-footer-static.png` ("Electrical plans signed and sealed by , Professional Electrical Engineer, PRC No. ."), `view/crop-d-home-why-static.png` ("Professional Electrical Engineer ()"), `view/crop-d-about-prose-static.png` (" runs the company and is on every roof visit…", "Engineer, (PRC No. )"), `view/crop-d-privacy-contact-static.png` ("Phone . Email ."), `p-404-top.png`, `d-estimate-top.png`.
- Elements: every `[data-profile-hide-if-empty]` except the footer's "Talk to us" column and the warranty wrappers: 50 tags across the seven built pages start without `class="is-empty"` (`layout.html:50`, `index.html:93`, `about.html:13–14`, `privacy.html:28,31`, and the five footer `<li>`s on every page). `site.js:33–37` only adds `is-empty` after the fetch.
- Cause: the hide-on-empty rule is applied by JavaScript after a network round trip, so the first paint shows the punctuation around empty spans; on a mobile connection that is 0.3–1 s on every page, and permanently whenever the app is unreachable from the site. The fill then moves everything below (About: a 25 px shift, 0.105 of the 0.273 CLS in `pf-d-about`).
- Fix: start them hidden. Either add `class="is-empty"` to every such tag in the pages (what the footer column already does), or let `build.py` do it in `render_page` (`re.sub(r'<(\w+)(?![^>]*\bclass=)([^>]*data-profile-hide-if-empty)', r'<\1 class="is-empty"\2', body)`, plus the `class="…"` case), so a page never shows dangling commas and the only change on fetch is text appearing. Keep the defaults inside the `data-profile` spans ("Pila, Laguna", "the whole Philippines"), which already read well without a profile. S.

### B6. At 760–899 px the hero photo is full width (728–867 px wide, 546–650 px tall) and the dark band is 1,117–1,191 px tall
- Screens: `w899-home-top.png`, `w760-home-top.png`, `view/w760-home-full-sheet.png`.
- Element: `.hero-grid` turns at 900 (css:72); `.hero-photo` has no max-width in the single-column state (css:71).
- Cause: below 900 the grid is one column and the `<picture>` fills it; the photo becomes larger than the text block and pushes "What do you want from solar?" to 1,250 px on a 1,024 px tablet screen. The call to action stays in the first screen at every width (`widths-report.json` → `ctaInView: true`), so this is balance, not reach.
- Fix: `@media (min-width: 640px) and (max-width: 899px) { .hero-photo { max-width: 560px; } }` (left-aligned under the text, 420 px tall), or turn the grid at 760 with `.hero h1 { font-size: 40px }` until 1024. S.
- Related, C: at 900–1023 the balance flips the other way: the text column is 566 px tall at 900 and the photo 289 px, floating in the middle of the band (`w900-home-top.png`). `@media (min-width: 900px) and (max-width: 1023px) { .hero h1 { font-size: 40px } .hero .lead { font-size: 17px } }`. S.

### B7. The font swap moves the prose: CLS 0.168 on About at 1280 (0.273 with the profile fill), 0.042 on net-metering, 0.016 on home
- Screens: none (a shift); `walk-report.json` → `clsLoad.entries` name the sources (h2, p, ul, li moving 24–30 px at 36–83 ms; on the home page `.hero-cta` 391→421, `.hero-points` 461→491, `.hero-photo` 138→153).
- Element: the three `@font-face` rules (css:2–4, TTF, `font-display: swap`); the fallback stack `system-ui, -apple-system, 'Segoe UI', Roboto` (css:13).
- Cause: the text paints in the fallback, Montserrat (wider) arrives, every line re-wraps. The phone measured 0.000 only because on localhost the 146 KB of fonts arrived before first paint; on a 3–5 Mbps mobile connection they arrive one to two seconds after the text, so the phone shifts more, not less. Google's "good" line is 0.1.
- Fix, in order of payoff: (a) convert the three TTFs to WOFF2: measured 47 → 18 KB each (`imgtest/Montserrat-*.woff2`), 146 → 54 KB; (b) `<link rel="preload" as="font" type="font/woff2" crossorigin href="/static/fonts/Montserrat-400.woff2">` and the 700 in `layout.html`; (c) a metric-matched fallback so the swap does not re-wrap: `@font-face { font-family: 'Montserrat Fallback'; src: local('Arial'); size-adjust: 112%; ascent-override: 97%; descent-override: 25%; line-gap-override: 0%; }` and `font-family: 'Montserrat', 'Montserrat Fallback', …` (tune the three numbers once with a side-by-side). (a)+(b) S; (c) M.

### C8. Page weight: 518 KB on the desk, 721 KB on the phone for the home page; the other pages 189–193 KB of which 146 KB is fonts
- Screens: none; `walk-report.json` → `items`; `imgtest/`.
- On a Philippine 4G at an effective 3–5 Mbps: the first screen of the home page (370 KB) in 0.8–1.2 s, the whole page in about 2 s; usable, but 300 KB is avoidable with no visible loss:
  - Fonts to WOFF2: −92 KB on every page (B7a).
  - The phone cards load the 960 WebPs (169–181 KB each, quality 80) for a 332 CSS px slot (664 device px). A 720 px variant measures 97–103 KB each at q80 (299 KB for the three vs 490) and 79–83 KB at q72 (242 KB). Add `720` to the sizes loop in `site/tools/photos.py:51`, a `720w` candidate to the two `srcset`s, and a `sizes` that states the slot instead of `33vw`: `(min-width: 1072px) 302px, (min-width: 640px) calc(31vw - 24px), calc(100vw - 56px)`. M (the tool, the HTML, the six new files).
  - The hero's `sizes="(min-width: 900px) 45vw, 100vw"` overstates the slot (450 px at ≥1072 because of the 1040 px wrap), so a 1x desk fetches the 960 file for a 450 px box: −122 KB with `sizes="(min-width: 1072px) 450px, (min-width: 900px) 43vw, 100vw"` (2x screens still get the 960). S.
  - `brand/logo-mark-white.png` is 1083×1079 (26 KB) for a 36 px slot, requested on every page: a 72 px PNG (about 3 KB) or an inline SVG. S.

### C9. The hero photo's frame: a light hairline and an invisible shadow
- Screens: `view/crop-d-hero-photo-edge.png`; pixel samples in the `extra.js` run: band #111 = (17,17,17), under the photo (12–15,12–15,12–15), the border pixel (231,228,214).
- Element: `.hero-photo` (css:71) over `.shot` (css:102).
- Cause: the 1 px `rgba(255,255,255,.14)` border is painted over the element's own background (`background-clip: border-box` by default), and `.shot` has the beige `#e4e0d0` loading background, so the border renders as a near-white hairline around the photo; the `0 12px 40px rgba(0,0,0,.4)` shadow darkens #111 by 2–5 levels and cannot be seen.
- Fix: `.hero-photo { background-clip: padding-box; box-shadow: none; }` and, if a lift is wanted on black, `box-shadow: 0 0 0 1px rgba(255,255,255,.08), 0 24px 48px rgba(0,0,0,.6)` (or a 2 px gold edge that matches the band's rule). The same `background-clip` keeps the cards clean if they ever get a border. S.

### C10. The installations cards against the plain cards
- Screens: `d-home-work.png`, `p-home-work.png`; `walk-report.json` → `home.cards` / `home.otherCards`.
- Measured: figure padding 12 / 12 / 18 px vs 20 px (fine: the photo bleeds to 12 px and the caption text lands 21 px from the edge, the same as the plain cards); heights equal in a row (382 px ×3 at 1280; 374 at 760; 388 at 900); caption `h3` **17 px** while every other `h3` on the site is 18 px (css:106 vs :19); the photo's 12 px radius inside a 14 px card with 12 px padding (concentric would be 2 px, or 8 px for a soft inner corner); the caption `p.muted.small` is 13.5 px on the phone, the only body copy under 14 px, under a 332 px photo. The `figcaption` padding `0 8px` and the `h3` margin `14px 0 6px` read well.
- Fix: `.photo-card h3 { font-size: 18px }`; `.photo-card p { font-size: 14.5px }` (16 px would be better on the phone; see C11); `.photo-card .shot { border-radius: 8px }`. S.
- **In hand**: the same photo (25) was the hero and the first card on one page; the working tree uses the angle shot for the card.

### C11. Text under 16 px on the phone (one media block closes all of it)
- Screens: `p-home-top.png` (brand tag 10.5 px, eyebrow 12.5), `p-home-work.png` (captions 13.5), `p-net-metering-top.png`, `view/crop-p-home-footer-static.png`.
- Elements: `.brand-tag` 10.5 px (css:32), `.card .tag` 12 px (:79), `.eyebrow` 12.5 px (:57), `.steps .when` 13 px (:88), `.figure .lab` 13 px (:96), `.small` 13.5 px (:23), `.brand-name` 14 px (:31), `.hero-points` 14.5 px (:67), `.foot-h` 15 px (:128).
- Fix: `@media (max-width: 759px) { .small { font-size: 14.5px } .hero-points { font-size: 15.5px } .eyebrow, .card .tag { font-size: 13px } .brand-tag { font-size: 11.5px } .steps .when, .figure .lab { font-size: 14px } }`. The uppercase tracked labels can stay under 16 px; the captions and footer copy are the ones that matter. S.

### C12. Tap targets under 44 px
- Screens: `d-home-band-foot.png` (summaries), `pf-d-home-footer.png` and `pf-p-home-footer.png` (contact links 19 px, 6 px apart).
- Elements: `.faq summary` 33 px (css:111); `.foot-bottom a` 21 px; `.contact-list a` 19 px (css:134); the inline link on net-metering 19 px; `.brand` 36 px (css:30).
- Fix: `.faq summary { padding: 10px 0 }`; `.contact-list { gap: 12px } .contact-list a, .foot-bottom a, .prose p > a { display: inline-block; padding: 8px 0 }`; `.brand { min-height: 44px }`. S.

### C13. Three gold rules in 45 px at the page foot (home, brownouts, net-metering)
- Screens: `d-home-band-foot.png`, `p-home-band-foot.png`; `walk-report.json` → `junction` (band bottom 4,038, footer top 4,078).
- Elements: `.cta-band { border-top/bottom: 2px gold }` (css:120), `.site-foot { margin-top: 40px; border-top: 3px gold }` (css:127).
- Cause: the band's bottom rule, a 40 px off-white strip, the footer's top rule: the strip reads as a stray band.
- Fix: `.cta-band { border-bottom: 0 }` and `body:has(main > .cta-band:last-child) .site-foot { margin-top: 0 }` (or give the band `margin-bottom: 0` and drop the footer margin on those pages). S.

### C14. The header button is cramped: 48 px in a 60 px bar, 6 px from the gold rule
- Screen: `view/crop-d-header.png`.
- Fix: `.nav .btn { min-height: 40px; padding: 6px 16px }`. S.

### C15. "Why people choose us" shows two cards and an orphan until the warranties arrive
- Screen: `view/crop-d-home-why-static.png` (Brands alone on the second row); with the profile, four cards 2×2 (`pf-d-home-warranty.png`).
- Element: `index.html:95` (`data-warranty-wrap` starts hidden, correctly) and `:100`; css:76.
- Cause: the grid holds three visible cards until the fetch; if the owner never fills the warranty years it stays an orphan.
- Fix: put Brands third and Warranties fourth, or `.cards.two > .card:last-child:nth-child(odd) { grid-column: 1 / -1 }`. S.

### C16. The preview build: the fourth, placeholder card is an orphan built from the old card structure
- Screens: `pv-d-home-cards.png` (1280: three photo cards, the placeholder alone on row two at 355 px tall vs 382), `pv-p-home-cards.png`, `pv-w760-home-full.png`, `pv-d-about-cards.png` (the two About placeholders in a two-column grid are fine).
- Element: `index.html:145–151` (`.card > .photo.placeholder + h3[style] + p`).
- Measured: 20 px padding so the striped photo is 285 px wide against 301 for the real photos; `h3` 18 px with an inline `margin-top:12px` against the figures' 17 px; the label 13 px muted on the stripes at 4.05–4.40:1 (fails 4.5 for text that small).
- Fix: give the placeholder the figure structure so the preview is faithful: `<figure class="card photo-card"><div class="shot placeholder">Photo: …</div><figcaption><h3>…</h3><p class="muted small">…</p></figcaption></figure>` with `.shot.placeholder { display:flex; align-items:flex-end; padding:12px; color: var(--ink); font-size: 14px; background: repeating-linear-gradient(…) }`. Then decide the grid for four: `.cards.two` (2×2) or publish six (web versions already exist for `rib-roof-eight-angle`, `hip-roof-town-wide`, `three-roofs-above`): a three-column grid only closes at three or six. S.

### C17. The estimate page frame has no height and no loading state
- Screens: `d-estimate-top.png`, `p-estimate-top.png` (header, a 20 px gap, footer: what a visitor sees until `quick.js` mounts; the widget itself is out of scope).
- Element: `estimate.html:6–9`, `.estimate-wrap` (css:124).
- Fix: `.estimate-wrap { min-height: 60vh }` and a `<p class="muted" id="pld-solar-estimate-loading">Loading the estimate…</p>` inside the mount that the widget replaces, so the page does not look empty for a second or two and the footer does not jump down when the form appears. S.

### C18. Share tags and titles
- Measured: `og:image` absolute (`https://pldevinc.com/static/photos/og-home.jpg`, 1200×630, 191 KB, the 25 roof; `og-home.jpg` viewed: a clean crop with the eight panels centred), `og:image:width/height`, `og:url` per page; no `twitter:card` (X, Telegram and some chat apps then show a small thumbnail or none); About's `<title>` is 83 characters ("About PL Development Inc. · Solar engineering for homes anywhere in the Philippines"; tabs and search cut at about 60), home 70, brownouts 68; descriptions 55–230 characters and specific per page; the 404 page carries `og:url …/404` (harmless).
- **In hand**: `og:image:alt` and a per-page `og_image` are in the working tree.
- Fix: `<meta name="twitter:card" content="summary_large_image" />` in `layout.html`; About's title to "About us · PL Development Inc." (the description carries the rest). S.

### C19. Focus styling and the phone menu
- Screens: `d-focusring-1.png` (brand), `-2` (Home), `-3` (header button), `-5` (hero button), `-7` (card), `-8` (summary), `-10` (Privacy notice), `p-focusring-4.png` (Menu); `p-home-menu.png`, `p-home-menu-scrolled.png`.
- The order is right and the default ring is visible everywhere, but it is the browser's 1 px two-tone ring and differs per browser; the skip link works (`.skip:focus` over the header). The open menu (45 px rows, `aria-expanded` toggles, travels with the sticky header) has no scrim and does not close on a tap outside or on Escape.
- Fix: `:focus-visible { outline: 3px solid var(--gold); outline-offset: 3px } .site-head :focus-visible, .btn-gold:focus-visible { outline-color: #fff }`; `document.addEventListener('keydown', e => e.key === 'Escape' && close())` in `site.js`. S.

### Checked and clean (no defect)
- Scroll width: every page at exactly the viewport on both widths and across the sweep; the only element past the edge is the off-screen skip link, by design.
- Layout shift from the photos: none (the hero slot and the card slots are reserved by `width`/`height` and `aspect-ratio`; the CLS entries name only text and the profile fill).
- `srcset`/`sizes`: the 480 file on a 1x desk at 640–1280, the 960 on the phone and at 1600; WebP chosen in every case; the JPEG fallbacks are never fetched by Chromium.
- Alt texts present on the hero and the three cards (the panel counts in them are the solar engineer's to confirm); lazy loading on the cards, `fetchpriority="high"` and `decoding="async"` on the hero.
- The sticky header over the photos: the 3 px gold rule separates it cleanly as the photo passes under (`d-home-sticky-photo.png`, `p-home-sticky-photo.png`); no shadow needed.
- The hero on the phone: the call to action sits at 465–513 px, inside the first screen; the four points end at 751 and the photo runs 779–1,048, so the first screen shows a 65 px sliver of green at the bottom, a scroll cue rather than a push. The photo does not move the button; it adds 297 px of dark band after it. The 159 px of hero points are the larger push, and the only picture a phone visitor meets before the cards at 5,343 px (the seventh screen). It earns its place; if the band is to be shorter, cut the points to two lines on the phone before touching the photo (`.hero-cta .btn { flex: 1 1 150px }` also lets the two buttons share one row instead of stacking 217 + 152 px).
- The 404 page: heading, one line, the gold estimate button and Home side by side on both widths (`p-404-top.png`). On the static server only `/404.html` serves it and the extensionless nav links 404, which the production host rewrites; not a site defect.
- Wording: US spelling throughout; "estimate", "roof check", "proposal" to the visitor; "assessment" appears once, in the privacy notice's retention list ("A customer's assessment, proposal and installation records"), which the copy glossary would call "roof check and proposal records". C, S.

## Grouped by cause: what one change closes

| Cause | Items | The change |
|---|---|---|
| Gold text on the dark band and bar | B1, B2 | two rules: `.nav .btn-gold { color: var(--ink) }`, `.hero .eyebrow { color: var(--gold) }` |
| The sticky header | B3, B4, C14 | the nav breakpoint (860/900), `[id] { scroll-margin-top: 76px }`, a 40 px header button |
| Profile-dependent markup | B5, C15, part of B7 | every `data-profile-hide-if-empty` starts `is-empty` (pages or `build.py`); card order in "Why people choose us" |
| The fonts | B7, C8 | WOFF2 + preload + a metric-matched fallback |
| The photo pipeline | C8, C9, C10, C16 | a 720 px size and honest `sizes`, `background-clip: padding-box` and no shadow on the hero frame, `h3` 18 px, the placeholder as a figure |
| The phone type scale and targets | C11, C12 | one `@media (max-width: 759px)` block and padding on inline links and summaries |
| Rules at the page foot | C13 | drop the band's bottom border and the footer margin after a band |
| Head tags | C18, C19 | `twitter:card`, a shorter About title, a site `:focus-visible` rule |

## For the coordinator

1. B1 header "Free estimate" white on gold 2.42:1 on every page: `.nav .btn-gold { color: var(--ink) }` (S).
2. B2 hero eyebrow 3.66:1 on black (home, brownouts, net-metering): `.hero .eyebrow { color: var(--gold) }` (S).
3. B3 header wraps to two-line links at 760–859 px (iPad portrait), bar 75 px: nav breakpoint to 860/900 or nowrap + hide the brand tag (S).
4. B4 "How it works" lands under the 63 px sticky header (eyebrow hidden): `[id] { scroll-margin-top: 76px }` (S).
5. B5 50 profile-dependent tags paint "signed and sealed by , … PRC No. ." and "()" until the fetch answers: start them `is-empty` (S).
6. B6 at 760–899 the hero photo is 728–867 px wide and the band 1,117–1,191 px tall: `max-width: 560px` on the photo below 900 (S).
7. B7 font swap CLS 0.168 on About (0.273 with the profile), 0.042 net-metering, 0.016 home; phone 0.000 only on localhost: WOFF2 (47 → 18 KB each) + preload (S), metric fallback (M).
8. C8 weight: home 518 KB desk, 370 KB first screen and 721 KB whole on the phone, other pages 189–193 KB; a 720 px variant (490 → 299 KB for the three cards), honest hero `sizes` (−122 KB on 1x desks), WOFF2 (−92 KB), a small logo (−23 KB) bring the phone to about 430 KB (M).
9. C9–C16 cosmetic, grouped above: the hero frame's beige hairline and invisible shadow, caption h3 17 vs 18 px and 13.5 px captions on the phone, 33 px summaries and 19–21 px links, three gold rules at the foot, the orphan Brands card, the placeholder card built differently from the real ones (S each).
10. Clean: scroll width = viewport on all 7 pages × 2 widths and 8 sweep widths; images cause 0 layout shift; 480 WebP on 1x desks, 960 on the phone; alts, lazy, sticky header over photos all fine; in hand in the working tree: the angle shot for card 1 and `og:image:alt`.

## Files

- Report: `report.md` (this file).
- Scripts: `lib.js`, `walk.js`, `widths.js`, `preview.js`, `profile.js`, `extra.js`; results `walk-report.json`, `widths-report.json`, `preview-report.json`, `profile-report.json`, `extra-report.json`; `imgtest/` (the 720/480/960 WebP experiments and the WOFF2 conversions); `dist-preview/` (the placeholder build); `http8196.log`.
- Screenshots (`shots/`): `d-{home,about,brownouts,net-metering,estimate,privacy,404}-{top,full,focus-2,focus-last}`, `d-{home,brownouts,net-metering}-band-foot`, `d-home-{work,how-anchor,faq-open,sticky-photo}`, `d-focusring-1…10`; the same with `p-` plus `p-home-menu`, `p-home-menu-scrolled`, `p-focusring-*`; `w{560,639,640,760,899,900,1024,1600}-home-{top,work,full}`, `w{780,820,860}-header`; `pv-{d,p,w760}-{home,about}-{cards,full}`; `pf-{d,p}-{home,about,net-metering,privacy}-{top,full,footer}`, `pf-{d,p}-home-warranty`; `view/*-sheet.png` (downscaled full pages) and `view/crop-*.png` (the footer, header, hero edge, About prose, privacy contact, phone hero band and footer).
