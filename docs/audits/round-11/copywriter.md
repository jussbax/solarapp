# Round 11 copywriter report: the hook

From the copywriter to the coordinator and the marketing and sales specialist, 10 October 2026, in the worktree after
`git merge claude/wonderful-maxwell-wawb8t` (main at 03b71ec, clean). The owner, verbatim: "check and work on the marketing, I am
not seeing any hook on the website, I need a solid hook." The marketing brief (`docs/audits/round-11/marketing-brief.md`) picks
candidate A, the number: the engine's own example, a house in Tanauan using about 500 kWh a month, panels only with net
metering, which the net-metering page's tiles already carry.

Files: `site/pages/index.html` (the title and description comments, the hero's eyebrow, h1, lead and button, the band),
`site/layout.html` (the sticky bar, the footer's button), `site/pages/estimate.html` (the title comment), `site/pages/404.html`
(the lead), `site/pages/net-metering.html` (the hero lead's echo), `docs/marketing.md` (ad angle 2, its note, the landing
headlines), `backend/tests/test_site.py` (the hero pinned to the engine). Brownouts and About untouched. Every hook, class, id,
`data-profile`, `data-count` and `data-nav` attribute stays; the four ticks, the proof strip and its order, the rib-roof photo,
the header's "Free estimate" nav button and the pinned strings all stay.

## The figures, as the engine gave them

The brief's h1 was "A ₱5,000 bill, down to about ₱1,500." on "₱5,003 → about ₱1,460, 4.0 years, run 9 October". That run was a
₱5,000-bill input (`docs/marketing.md`'s old note says "for a ₱5,000 bill"), which the widget no longer takes. The rule for this
round is the engine's figures for the page's example itself, through the same call as
`test_net_metering_page_figures_match_the_engine` (`goal=net_metering, town=Tanauan, province=Batangas, monthly_kwh=500,
pattern=evening`, today's price list and tariff, the real PVGIS weather). That call, 10 October 2026, gives:

- bill before ₱6,003.29 a month; bill after ₱1,893.36; saving about ₱4,110 a month, about ₱49,000 in the first year
- payback 3.84 years, over the engine's 25-year horizon; 68.5% off the bill
- 7 panels, 4.095 kWp, no battery, ₱193,000 installed with VAT (the tiles' own figures, unchanged)

So the hook is **"A ₱6,000 bill, down to about ₱1,900."** (the two bills to the nearest hundred peso, as the widget's `phpAbout`
rounds a figure under ₱10,000) and **"about four years"** (3.84 to the year; the tile's "under 4 years" stays true beside it).
The ₱5,000 of the brief would have been a figure the engine does not return for the house the sentence names. The script that
printed the run is `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/copy/r11/engine_example.py`.

The new test `test_home_hero_figures_match_the_engine` sits beside the tiles test and shares its engine call (now
`_engine_example()`, which skips on synthetic weather as before). It derives "₱6,000", "₱1,900" and "four" from the run the
same way and asserts them in the home h1, the title comment, the description, the lead ("Pays for itself in about four
years."), the net-metering lead's echo and the ad line and landing headline in `docs/marketing.md`; it also asserts the lead
opens on "Our estimate for a house in Tanauan using about 500 kWh a month, panels only.", that "your bill will" is nowhere on
the page, and that the h1 and lead carry no exclamation mark. A price or tariff change now fails the test instead of leaving a
stale hook on the hero. `tests/test_site.py`: 12 passed (11 before, plus this one, on the real weather).

## Every place the hook lives: before and after

**Home hero** (`index.html`)
- Eyebrow: "Home solar in [the Philippines]" → "Home solar, sized to your bill". The `data-profile="service_area"` span left the
  eyebrow; it now sits in the band's paragraph (the fallback, below).
- h1: "The bill goes down. With a battery, the lights stay on." → "A ₱6,000 bill, down to about ₱1,900."
- Lead: "Panels sized to your bill bring it down every month; add a battery and the house runs through brownouts. A minute here
  shows you the price and your new bill." → "Our estimate for a house in Tanauan using about 500 kWh a month, panels only. Pays
  for itself in about four years. Yours takes a minute."
- Button: "Get my free estimate" → "See my new bill". The four ticks stay.
- **The fallback was applied.** The brief's lead ("…Yours takes a minute, anywhere in [the Philippines].") measured five lines at
  390 × 844 (17 px, 521–653). Without "anywhere in …" it is four lines (521–627), and the span moved into the band's paragraph.

**Title and description** (`index.html:1–2`): "The bill goes down. With a battery, the lights stay on. · PL Development Inc." →
"A ₱6,000 bill, down to about ₱1,900 · PL Development Inc."; "Rooftop solar for homes anywhere in the Philippines, measured on
your own roof before we quote. The oldest installation has been on net metering since 2023. Four questions, one minute, free, no
sign-up." → "A ₱6,000 bill, down to about ₱1,900: our estimate for a house in Tanauan using about 500 kWh a month, panels only,
paid back in about four years. Rooftop solar for homes anywhere in the Philippines, measured on your own roof before we quote.
Four questions, one minute, free, no sign-up." The share snippets follow (templated in `layout.html`); the og:image and its alt
stay.

**Sticky bar** (`layout.html`): "Free estimate / One minute." + "Get my free estimate" → "Your new bill / Free, in a minute." +
"See my new bill". **Footer** "Start here": the button "Get my free estimate" → "See my new bill"; its paragraph stays.

**Band at the foot of the home page** (`index.html`): h2 "Your number is a minute away." → "Your new bill is a minute away.";
p "Your bill, your town, when you use power. That is all it takes, and the only call you get is the one you book." → "Your bill,
your town, when you use power. That is all it takes, anywhere in [the Philippines]. Every month you wait is another month at
the old bill, and the only call you get is the one you book." (the span's new home; "That is all it takes" kept so the span has
a sentence to sit in); button → "See my new bill".

**Estimate page title** (`estimate.html:1`): "Free solar estimate for your home · PL Development Inc." → "Your new bill in a
minute · PL Development Inc." (its description stays). **404** (`404.html`): "Your estimate is right here, one minute, free." →
"Your new bill is right here, one minute, free."

**Net-metering lead** (`net-metering.html`): "In our example below, about two thirds of the bill goes away. By day the panels
run the house; …" → "In our example below, a ₱6,000 bill comes down to about ₱1,900, about two thirds off. By day the panels run
the house; the extra comes back as credit on your bill. Panels and inverter only: the lowest price of the three ways to go."
Its h1, tiles and the pinned small print stay.

**docs/marketing.md**
- Ad angle 2: "A ₱5,000 bill becomes about ₱1,500, and the system pays for itself in about 4 years, then runs for 20 more. See
  your own number in one minute, free." → "A ₱6,000 bill, down to about ₱1,900: our estimate for a house in Tanauan using about
  500 kWh a month, panels only, paid back in about four years. See your own number in a minute, free." ("then runs for 20 more"
  goes; Tanauan added, per the rail that the house and the kWh always sit beside the figure.)
- Its note: now records the 10 October run (₱6,003 → about ₱1,893, 3.8 years, 7 panels, ₱193,000), that the hero, the tiles
  and this line are one run pinned by the test, and the list of what to update together when the price list or the tariff
  moves; "run it again on the day you post the ad and keep "about"" stays.
- Landing headlines: "See what solar would do to your bill…" / "Your ₱4,000 bill, down to a few hundred…" → "A ₱6,000 bill,
  down to about ₱1,900. Yours takes a minute." / "Your new bill is a minute away."; the parenthetical now quotes the estimate
  page's own heading, "Your new bill is a minute away." Ad angles 1 and 3 and the Messenger templates untouched.

## The measurements (site/dist on 8217, the profile fetch 404s so the span shows its default text)

390 × 844: eyebrow one line (14.5 px, 399–421); h1 two lines (33 px, 431–507); lead four lines (17 px, 521–627); the button
673–703, inside the first screen, with the first two ticks under it; no overflow; the sticky bar visible after the hero with
"Your new bill / Free, in a minute. / See my new bill". 1280 × 900: eyebrow one line, h1 two lines (48 px), lead three lines, the
button at 435–491, the four ticks and the proof strip (₱33,000+, 2023, 3, 1) in the first screen. The net-metering lead six lines
at 390. Screenshots and texts in `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/copy/r11/`
(`phone-first.png`, `desk-first.png`, `*-band.png`, `*-sticky.png`, `*-net-metering-hero.png`, `phone.json`, `desk.json`).

Checks: `site/build.py` built seven pages; `tests/test_site.py` 12 passed; the sweep of the changed pages finds no "your bill
will", no utility name, and every "!" in a comment, the doctype or code.

## What I could not do, and for the coordinator

- The hook's figure is ₱6,000, not the brief's ₱5,000: the engine's own number for the house the sentence names. If the owner
  wants a ₱5,000 headline, the house has to change with it (a lower kWh), and the net-metering tiles and small print with the
  house; say the word and I re-run it.
- Brownouts, About and the net-metering page keep their own hero buttons and bands ("Get my free estimate", "Your number is a
  minute away.") as the brief says they stay; only the shared sticky bar and footer changed on those pages. If the thread should
  run through every page, those are the lines.
- The marketing brief's list of what the owner could supply for a stronger hook (a real before-and-after bill from the 2023
  installation, a lit house on a dark street, the inverter's switch-over time, the owner's contact in Settings, the date and
  price list of the run) stands; the fifth is now partly met by the note in `docs/marketing.md` and the test.
- `DECISIONS.md` may want one line: the home hero carries the net-metering example's figures and the test pins them to the
  engine.
