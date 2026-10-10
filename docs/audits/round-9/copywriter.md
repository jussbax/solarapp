# Round 9 copywriter report: the installations without "ours", the estimate as a teaser

From the copywriter to the coordinator and the marketing and sales specialist, 10 October 2026, on top of the round-8 draft in
the same worktree and branch (main merged at c5fc888). Two owner rulings: the installations as proof with ownership dropped
entirely, and the estimate as a teaser that leaves the visitor wanting the visit. Version A (the price stays), the kWp off the
scene's chip and counter too. The marketing review of the round-8 draft (54 accept, 4 change to, all departures accepted) is
folded in here, in the same commit.

Files: `site/pages/index.html`, `about.html`, `brownouts.html`, `net-metering.html`, `site/partials/proof.html`;
`frontend/src/estimate/Estimate.tsx`, `DayScene.tsx`, `Wizard.tsx`, `estimate.css`. Nothing in the engine, the lead payload,
the lead e-mail or the tests changed; every hook, class, id, `data-profile`, `data-count`, `aria-*`, handler and the
`#pld-book` anchor stays, and the strings `backend/tests/test_site.py` pins all survive ("Our installations", "₱33,000+",
"2023", `data-count="33000"`, the two photo placeholders, the net-metering small print).

Checks: `npm run build` clean; `npm run lint` at the 7-warning baseline, none in `src/estimate`; backend 211 passed (the merge
brought two tests); `tests/test_site.py` 11 passed; `site/build.py` built seven pages. Read back as the customer at 390 × 844 and
1280 × 900: the four site pages on the public website process (port 8213, `SOLARAPP_SITE_DIR` on the worktree's `site/dist`,
proxying to the app host on 8212 with the worktree's `frontend/dist`), the estimate for three goals and five sizes with a
booking under a made-up name and the copied summary. Screenshots and recorded texts in
`/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/copy/r9/` (`phone-home-installations.png`,
`phone-home-proof.png`, `phone-about-top.png`, the `desk-*` pair, `*-result-full.png`, `*-lines-sticky.png`, `*-visit.png`,
`*-hero.png`, `*-alt-b.png`, `*-basis.png`, `*-thanks.png`, `*-card1-at-once.png`, the `*.json` files with every text). The
walk's sweep for the words that had to go found none on any page or snippet (its one regex hit is "your own roof").

## Part 1. The pages: before and after

**index.html**
- Description and share snippet: "…measured on your own roof before we quote. Our own home has run on it since 2023. Four
  questions…" → "…measured on your own roof before we quote. The oldest installation has been on net metering since 2023.
  Four questions, one minute, free, no sign-up."
- Hero tick: "Our own home on solar since 2023" → "The oldest installation on net metering since 2023".
- Installations h2: "We live with what we sell." → "Three roofs in service. Which one is like yours?" Lead: "Our home, our
  parents' house and our family's house in Quezon City, photographed by us from the air. Three family roofs in Laguna and
  Quezon City; the oldest has run since 2023." → "Photographed from the air by us, with the size on each photo: a three-roof
  house with a 30 kWh battery, a daytime house on eight panels, and a hip roof carrying sixteen. The oldest has been on net
  metering since 2023, with more than ₱33,000 of credit on its bill since, and has stood through every typhoon season."
  `aria-label` "Our own roofs" → "Three installations".
- Card 1: "Our home" / "Where our family lives, on three roofs with a 30 kWh battery. The house runs through brownouts, and net
  metering has built up more than ₱33,000 of credit on the bill since 2023." → "Three roofs, one battery" / "13.75 kWp across
  three roofs, with a 30 kWh battery, a 12 kW hybrid inverter and a 6 kW grid-tie inverter: sized to run the house through
  brownouts, and it does. On net metering since 2023; the electric company's bill has carried more than ₱33,000 of credit
  since."
- Card 2: "Our parents' house" / "Eight panels carry the house by day, fixed through the roof sheet to the framing beneath.
  Installed early 2026." → "Eight panels, panels only" / "4.56 kWp on a 6 kW grid-tie inverter, panels only: the lowest price of
  the three ways to go, and the eight panels carry the house by day. Fixed through the roof sheet to the framing beneath.
  Installed early 2026."
- Card 3: "Our family's house" / "Sixteen panels in three groups across three faces of the hip roof, and the inverter is ready
  for a battery whenever one is wanted. Installed early 2026." → "Sixteen panels, hip roof" / "9.12 kWp in three groups across
  three faces of the hip roof, each on its own rails, on a 12 kW hybrid inverter that takes a battery whenever one is wanted.
  Installed early 2026."
- Typhoon FAQ: "Our oldest installation, from 2023, has stood through every typhoon season since. …" → "The 2023 installation in
  Pila, Laguna has stood through every typhoon season since. …" The eyebrow "Our installations" (pinned; the company's work),
  the chips, the placeholder card and "Swipe for the next roof." stay.

**site/partials/proof.html** (figures, `data-count` and "2023" unchanged)
- "of net metering credit on our own bill" → "of net metering credit on one bill since 2023, as the electric company prints it"
- "our own home went solar, and it has stood through every typhoon season since" → "the oldest installation went on net
  metering, and has stood through every typhoon season since"
- "family homes of our own, in Laguna and Quezon City" → "installations photographed from the air, in Laguna and Quezon City"
- "free visit: a test panel on your roof and your bill on the table, before we quote" keeps.

**about.html**
- h1 "Our oldest roof is our own." → "Measured first. In service since 2023." Lead: "Our own home has run on what we sell since
  2023. PL Development Inc. designs and installs rooftop solar for homes from Pila, Laguna, across the Philippines." → "PL
  Development Inc. designs and installs rooftop solar for homes from Pila, Laguna, across the Philippines: the roof measured
  before it is priced, the plans sealed by a Professional Electrical Engineer, and the oldest installation on net metering
  since 2023." (the three `data-profile` spans as before).
- Figcaptions: "Our home in Pila, Laguna: three roofs and a 30 kWh battery, net metered since 2023, with more than ₱33,000 of
  credit on the bill." → "Pila, Laguna: 13.75 kWp on three roofs with a 30 kWh battery, on net metering since 2023, with more
  than ₱33,000 of credit on the bill since."; "Our parents' house in Pila, Laguna: eight panels fixed through the roof sheet to
  the framing, installed early 2026." → "Pila, Laguna: eight panels, 4.56 kWp, fixed through the roof sheet to the framing,
  installed early 2026."
- Where we install: "We are based in Pila, Laguna, our own roofs are in Laguna and Quezon City, and we travel to wherever yours
  is." → "We are based in Pila, Laguna; the installations on these pages are in Laguna and Quezon City, and we travel to
  wherever your roof is."

**brownouts.html**: "Our home in Pila, Laguna: a 30 kWh battery, and the house runs through brownouts." → "Pila, Laguna: 13.75
kWp with a 30 kWh battery; the house runs through brownouts."; "Our family's house in Fairview, Quezon City: solar by day, and
the inverter is ready for a battery whenever one is wanted." → "Fairview, Quezon City: 9.12 kWp on a hip roof, solar by day,
with the inverter ready for a battery whenever one is wanted."

**net-metering.html**: "Our home in Pila, Laguna: net metered since 2023, with a 30 kWh battery for the brownouts." → "Pila,
Laguna: on net metering since 2023, with a 30 kWh battery for the brownouts."; the small print's "From our own estimate at
today's prices" → "From this website's estimate at today's prices" (the optional item, taken: "our own" is the phrase the
owner reacted to; the pinned substring is untouched).

The company's own lines stay as the brief lists them ("our own workmanship warranty", "our own crew", "ours on the installation",
"photographed by us from the air", "our own server"). Nothing names or implies a customer.

## Part 2. The result, top to bottom: before and after

1. Heading: "Your estimate for Pila, Laguna" (unchanged; the warning under it when it applies).
2. The day scene: motion, geometry and the hourly readout untouched. The counter "6 panels · 3.51 kWp" → "6 panels" (the number
   in gold); the chips "6 panels · 3.51 kWp" / "6 kW inverter" / "11.7 kWh battery" / "net metering" → "6 panels" / "inverter" /
   "battery" / "net metering" ("grid as backup" for battery first); the desktop labels "6 kW inverter" / "11.7 kWh battery" →
   "inverter" / "battery"; the aria-label "6 panels (3.51 kWp) on the roof, a 6 kW inverter, a 11.7 kWh battery and the meter
   with net metering: …" → "6 panels on the roof, an inverter, a battery and the meter with net metering: an ordinary day, the
   sun up from 6 AM to 6 PM, the power flowing between the panels, the house, the battery and the grid."
3. The hero: the bill row unchanged (the sub-line now carries the review's remainder, below); the grid "Pays for itself in" /
   "Estimated price" / "Saved over 25 years" → two cells, "Pays for itself in" / "7.4 years" / "about ₱55,000 saved in the
   first year" and "Estimated price" / "₱308,000" / "the whole job: installed, permits and papers filed, VAT included". The
   25-year cell goes (it returns as a promise in block 7). `estimate.css`: the grid to two columns, one at 420 px and under.
4. The two actions unchanged.
5. "What you get: 6 panels of 585 W (3.51 kWp) on about 15 m² of roof, a 6 kW hybrid inverter and an 11.7 kWh lithium battery,
   enough for a typical night of your use when the grid is down." → "What you get: 6 panels on the roof, a hybrid inverter on
   the wall and a lithium battery, enough for a typical night of your use when the grid is down." (the note in whichever form
   the engine gives; panels only: "6 panels on the roof and a hybrid inverter on the wall; a battery can be added whenever you
   want lights in a brownout too.").
   "What it does: the panels make about 444 kWh a month, 111% of the 400 kWh you use. By day the panels run the house first; …
   Between them, the panels by day and the battery after dark cover 96% of what you use." → by goal: with a battery "By day the
   panels run the house and fill the battery; the battery carries the evening; the extra goes to your electric company and
   comes back as credit at its generation rate, so what still comes is a small bill for the fixed charges and the hours the
   grid covers."; net metering "By day the panels run the house; the rest of the day's sun goes back through the meter as
   credit on your bill, at your electric company's generation rate; the evening runs on the grid, as it does today, so what
   still comes is a smaller bill."; battery first "The panels and the battery carry an ordinary day on their own, and the grid
   is only the spare; nothing is sold back, so once the battery is full the extra sun goes unused. In long rainy spells the
   grid still steps in; your proposal says how much."
6. The alternative: battery shown unchanged; not shown "Want the lights on when the street goes dark? An 11.7 kWh battery is
   about ₱128,000 more, …" → "…? A battery is about ₱128,000 more, enough for a typical night of your use when the grid is
   down; the bill about ₱199 a month, pays for itself in 7.4 years." (small bill: "; a small bill, pays for itself in 16.8
   years.").
7. New closing block before the booking card (`pld-line pld-visit`: h3, lead, six items, close): "What the free visit settles" /
   "This estimate comes from your answers and a typical roof. One free visit, with the test panel and meters on your roof and
   your bill on the table, settles:" / how many panels the roof holds and where; what your battery carries on a brownout night
   from your own appliances (panels only: "what a battery would carry on a brownout night, from your own appliances, if you
   want one"); the exact price, every panel, rail, cable and breaker, what is due when; the savings year by year and what 25
   years add up to; the plans, the permit and the net metering papers, filed by us (battery first: "the plans signed and
   sealed by a Professional Electrical Engineer and the permit, filed by us"); the dates: permit, installation day by day,
   switch-on and the two-way meter (battery first: "…and switch-on") / "Then your proposal, within two working days, every
   peso and every part on paper, and you decide with all of it in front of you." `estimate.css`: four plain rules for the
   block's spacing and list.
8. The booking card and the thank-you: the round-8 words.
9. The foot: the CO₂ sentence goes; "Worked out for a house in Pila, Laguna using about 400 kWh a month, mostly in the evening.
   This is an estimate, not a quotation: on the free on-site assessment we measure your roof and the sun on it, and the
   proposal that follows is exact."
10. The sticky bar: "Estimated price / ₱308,000" → "Your new monthly bill / about ₱199" ("a small bill" under ₱100; the price
    with its old label when the engine returns no economics); the button unchanged.
11. The copied summary (version A):
    ```
    Solar estimate from PL Development Inc. for a house in Pila, Laguna:
    Bill ₱4,803 → about ₱199 a month; about ₱55,000 saved in the first year; pays for itself in 7.4 years.
    Price ₱308,000, installed, permits and VAT included.
    6 panels and a battery, enough for a typical night of your use when the grid is down; the exact layout and sizes come from the free on-site assessment.
    This is an estimate, not a quotation; the free on-site assessment makes it exact.
    Questions: m.me/… · Run your own: …/estimate
    ```
    (panels only: "6 panels, and a battery can be added later; the exact layout and sizes come from the free on-site
    assessment."; the lifetime line goes).

What left the page: the watts per panel, the kWp, the roof m², the inverter kW, the battery kWh (both variants), the kWh made
a month and its percentage, the coverage, the import kWh, the CO₂, the 25-year total. What stays: the bill before and after,
the monthly and first-year savings, the payback, the price, the panel count, both prices and bills with and without the
battery, the battery note in words, the hourly kW in the scene. The lead payload still carries the kWp and the battery kWh for
the owner's e-mail.

## The marketing review of round 8, folded in (the four "change to" items, exact texts)

1. The hero sub-line for a bill of ₱100 or more: "…what still comes is your electric company's fixed charges" → "…your electric
   company's fixed charges and the hours the grid covers". The small-bill branch unchanged.
2. `caption()`, the panels waking: "The sun is up and the panels are taking over." → "The sun is up and the panels are
   starting to carry the house."
3. `caption()`, the evening on battery: "The battery carries the evening on your own power: the lights, the fan, the TV, the
   Wi-Fi." only when the battery alone feeds the house in that hour; with `r.import_kw >= MIN_KW` the hour reads "The battery
   carries the evening as far as it goes; the grid tops up the rest." (No walked case had such an hour outside the night;
   the branch follows the row.)
4. The summary's first line: "Solar estimate from PL Development Inc. for Pila, Laguna:" → "…for a house in Pila, Laguna:" (a
   pin: "for a house near Quezon City, Metro Manila:").

## The two reported defects

- The goal cards' right border. Measured at rest in the browser (`diag.js`): the stage's scrollWidth equals its clientWidth at
  390 and 1280, and no element lies past its edge. The 19 px and the clipped border in both agents' screenshots were the
  card's 320 ms entry slide (`pld-wz-enter-next`, from `translateX(36px)`) caught under the stage's overflow clip within the
  first frames after load; the h2 in those screenshots is shifted by the same amount. There was no width to fix in
  `wizard.css`; what was wrong was the first card sliding in on page load, from nowhere. `Wizard.tsx` now gives the enter
  class only after a change of card (a `slid` state set in `go()`); the first card is simply there. The walk now reads the
  stage at once and after 600 ms: equal widths, no transform, no enter class; after the first choice the next card slides
  as before (`stageAtOnce`, `stageSettled`, `stageAfterSlide` in the json files; `*-card1-at-once.png`).
- `caption()` before dawn: `night` now holds for `h < 6` whatever the load, so a morning house at 5 AM reads "Everyone asleep,
  the fridge on the grid." instead of the evening line (seen in the 5,000 kWh, morning walk).

## Departures from the marketing brief (both texts, one line of reasoning)

1. The sticky bar. Brief: label "Your new bill", value "about ₱199 a month". Run: label "Your new monthly bill", value "about
   ₱199". At 390 px the brief's value wrapped to two lines beside the two-line button, and to three for a five-figure bill
   ("about ₱28,854 a month"); "a month" in the label, as the hero's own label says it, keeps the value on one line.
2. "What it does", net metering. Brief: "…the evening runs on the grid, like today, so…". Run: "as it does today", as in the
   scene's captions (the round-8 departure the review accepted), so the two do not say it two ways.
3. "What it does", with a battery. Brief: "…so what still comes is a small bill for the fixed charges and the hours the grid
   covers." Run: that clause only where the panels make more than the house uses (`makesPct > 100`, the round-8 guard);
   otherwise "…so what still comes is a smaller bill." A house whose 40-panel cap leaves a ₱25,000 bill must not read "a small
   bill" under a hero that prints the figure.
4. The closing block's fourth line. Brief: "what 25 years add up to". Run: the engine's `analysis_years` ("what 25 years add up
   to on your roof"), "the years" when no economics came back, so the figure never disagrees with the proposal's horizon.
5. The scene's counter. Brief: "6 panels". Run: "6 panels" with the number in gold, as the kWp was, so the build-up still has
   its one bright figure while the count climbs.
6. The hero grid. Brief: two cells. Run: two columns at every width above 420 px, one column under (the old 560 px rule that
   spanned the last cell is gone, since there is no third cell to span).

## Checks at 390 × 844 (and 1280 × 900)

- The home page's installations section (`phone-home-installations.png`, `desk-home-installations.png`): the h2 two lines, the
  lead nine, the three cards with their chips and the size-first captions, no customer and no owner anywhere; the proof strip
  (`phone-home-proof.png`, `desk-home-proof.png`) with the four labels; About's top (`phone-about-top.png`, `desk-about-top.png`)
  with the new h1 and lead; the Brownouts and Net metering captions in the json files.
- The estimate: the h1 two lines and the lead four; the stage without overflow at once, settled and after the slide; the result
  heading one line; the hero's two cells (one column at 390, two at 1280); the lines; the alternative in both states; the
  closing block (`*-visit.png`) in its three forms (with a battery, panels only, battery first); the booking card and the
  thank-you; the foot without the CO₂; the sticky bar one line (`*-lines-sticky.png`); the copied summary read back through the
  clipboard shim; no page overflow; no console errors; the sweep for size units on the result finds only the readout's kW and
  the foot's "400 kWh".
- The scene's captions sampled four times a second over 31 s for three goals and five sizes: every branch seen except the
  review's "as far as it goes" hour, which none of the walked days produced.

## For the coordinator

- `DECISIONS.md` "Quick estimate" / "Shown to the visitor" needs the one-line update the brief names (what the result prints
  now, what waits for the proposal).
- The public website process is where `SOLARAPP_SITE_DIR` matters; the app host's `/about` answers 200 only because of the
  SPA fallback. The walk ran the public process on 8213 (`uvicorn solarapp.public:create_public_app --factory` with
  `SOLARAPP_UPSTREAM` on 8212) to read the pages as a visitor would.
