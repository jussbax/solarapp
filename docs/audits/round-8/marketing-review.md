# Round 8, marketing: line-by-line review of the copywriter's draft (63367fd)

From the marketing and sales specialist, 10 October 2026. Read-only: nothing in the repository or the worktree was
changed. Read as the customer reads it on a private server (http://127.0.0.1:8214, the worktree's backend and its built
`frontend/dist`, a scratch database, the real sun records) at 390 × 844 and 1280 × 900: the four cards, the result for the
battery goal at 400 kWh mostly evening, the other two goals, 250 kWh, 5,000 kWh with the cap warning, the scene's captions
sampled four times a second over a full day, the alternative in both states, the booking card, one booking under a made-up
name, the thank-you and the copied summary. Playwright script `walk.js`, the screenshots `phone-*.png` / `desk-*.png`, the
recorded texts `*.json`, the server log and `capcheck.py` (the caption rules replayed on the engine's typical days for
eleven houses) are in `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/review/`. Line
numbers are the worktree's files at 63367fd (`frontend/src/estimate/Estimate.tsx`, `Wizard.tsx`, `DayScene.tsx`,
`backend/solarapp/core/quick.py`); every line is quoted, so cite by string if they move. Checked against the round-8 brief,
my angle brief (`docs/audits/round-8/marketing-brief.md`), the round-7 facts and the copywriter's eleven departures.

One note on the object of the review. The worktree has moved past the draft while I read it: HEAD is now 999a7d0 (a
merge that brought c5fc888, which touches no estimate file) and at 06:29:01 the three estimate files, `estimate.css` and
four site pages gained uncommitted edits that read like the owner's later rulings (the teaser without sizes, the lifetime
tile and the CO₂ line, a "What the free visit settles" list, the "our own" lines off the site pages, the 5 AM caption
fixed); the `dist` was rebuilt on them at 06:29:33. My six walks finished at 06:26:42 and recorded 63367fd's words in every
field (the sizes, the lifetime tile, the CO₂ line are all there), so this review is of the draft the brief names. The
uncommitted edits are not reviewed here; where one of my four changes is already moot or still stands under them, I say so.

Verdict on each line: **accept**, **change to** (exact text), or **must go**. 58 lines: 54 accept, 4 change to, 0 must go.

---

## What was verified before the lines

- **Every figure, with its rounding.** The 400 kWh evening house with the battery: ₱4,803 → about ₱199, about ₱4,604 a
  month, 7.4 years, about ₱55,000, ₱308,000, about ₱957,000, 6 panels of 585 W (3.51 kWp), about 15 m², 6 kW, 11.7 kWh
  (the chip says the same since fc89f13), about 444 kWh a month, 111%, 96%, 3.8 tonnes; the alternative ₱180,000, about
  ₱1,252, 4.1 years, about ₱128,000 more, 30%, about ₱1.17 million. The 250 kWh house: "a small bill", 16.8 years, 4
  panels (2.34 kWp), 10 m², 10.24 kWh, 118%, 99%. The battery-first house: 9 panels (5.26 kWp), 23 m², 10.24 kWh, 666 kWh,
  166%, 100%, 5.7 tonnes, the import sentence hidden under 50 kWh as before. The 5,000 kWh house: 40 panels (23.40 kWp),
  103 m², "2 hybrid inverters of 12 kW", 2,960 kWh, 59%, 43%, 51.2 kWh with "about 9 hours of your evening use when the
  grid is down", about ₱733,000 more, 25.2 tonnes. The readout's kW hour by hour, the chips and "valid 15 days" unchanged.
  `php0`, `phpAbout`, `n0`, `years` untouched in the diff.
- **The honesty lines, inside the sentences.** "about" before every savings figure (the hero's three sub-lines, the first
  year, the lifetime, "about ₱128,000 more"); "This is an estimate, not a quotation" word for word in the foot (535, then a
  colon) and the summary (302, then a semicolon); the fixed charges and "the grid's hours in long rainy spells" as what
  still comes (385); the battery note in both of the engine's forms closing the sentence, no brackets ("enough for a
  typical night of your use when the grid is down" at 400 and 250 kWh, "about 9 hours of your evening use when the grid is
  down" at 5,000 kWh); the panels as the saving and the battery as the lights (437); the cap warning's substance (40,
  the visit).
- **The three kinds as the small label.** "Solar with net metering.", "Solar with a battery.", "Battery first, nothing sold
  back." open the three small texts (`phone-combination-400-card1.png`); "net metering" / "grid as backup" on the chip.
- **The one-visit promise in the owner's words.** "Book my free on-site assessment" on the hero button, the form button and
  the sticky bar; "one free visit" (462); "The only call you get is the one you book." (349); the step list intact: the
  visit with the test panel, the roof check card the same evening, the proposal within two working days, valid 15 days.
- **The profile's lines as they come from Settings.** "within one working day", the privacy line, the four warranty lines
  (once, since fc89f13), "Morning / Afternoon / Evening", "Show my estimate", "Working it out…", "Back", "Next", "1 of 4";
  the field labels; the aria-label's facts (only "a typical day" → "an ordinary day").
- **Register.** "assessment" in seven places, every one "on-site assessment" (302, 417, 455, 512, 535, 547, quick.py:241);
  "your electric company" (385–386, 426), never the utility; no financing word, no "from ₱", no guarantee, no brand, no
  town but the one the visitor picked, no date, no hours beyond the engine's note, no switch-over time ("takes over" is the
  word), no customer voice, no exclamation mark (a sweep of the six walks' recorded texts found none). No "our own" or
  "our home" anywhere in the widget: "your own power" (DayScene 187) and "their own power" (Wizard 13) are the
  customer's. The optional proof sentence of my brief (2.12, "Our own home in Pila, Laguna…") was not added, and under the
  owner's later ruling it is withdrawn.
- **Phone and desktop.** At 390 px the h1 takes two lines (the rail allows three), the lead four; at 1280 one and two. The
  goal titles one, two and one lines, the small texts six, seven and seven, no overflow, the page never wider than the
  viewport (the stage's 19 px clip of the choice buttons' right edge is the CSS matter the copywriter named, identical
  with the old words). The slider's three stops on one line. The longest caption (the battery evening) three lines at 390
  under the drawing (`phone-combination-400-scene-evening.png`). No console errors in any of the six walks.
- **Build and tests.** The worktree's `dist` served to my walks carried the new h1 and none of the old; `tests/test_quick.py`
  6 passed against the worktree with its two changed asserts ("outside the Philippines", "very small bill"); the
  copywriter reports the build clean, lint at the 7-warning baseline and 209 backend tests passing, which I did not rerun.

---

## Estimate.tsx

| Line | Element | Text | Verdict |
|---|---|---|---|
| 347 | h1 | Your new bill is a minute away. | accept (the band's "Your number is a minute away." kept on landing; two lines at 390) |
| 349 | lead | Four questions, then the bill you would pay instead, the price of the whole job, and how many panels it takes. The only call you get is the one you book. | accept (four lines at 390; the objection "they will call me" answered in the last sentence) |
| 368 | h2 | Your estimate for Pila, Laguna · a pin: Your estimate near Quezon City, Metro Manila · outside: Your estimate | accept |
| 385 | hero sub-line, small bill | about ₱4,803 a month stays in your pocket; what still comes is your electric company's fixed charges, and the grid's hours in long rainy spells | accept |
| 386 | hero sub-line, bill of ₱100 or more | about ₱4,604 a month stays in your pocket; what still comes is your electric company's fixed charges | **change to**: `about ${php0(e.savings_monthly)} a month stays in your pocket; what still comes is your electric company's fixed charges and the hours the grid covers`. Reason: this branch prints under ₱1,252 (the 400 kWh house without the battery, where the house takes 30% straight from the panels and the evening runs on the grid) and under ₱28,854 (the 5,000 kWh house, `phone-net_metering-5000-result-top.png`); neither is fixed charges, and a buyer who knows his fixed charges are a few hundred pesos reads the hero as glossing. The "What it does" line two screens down already says "the fixed charges and the hours the grid covers", and the site's Net metering page says "The fixed charges and the evening hours stay". My brief's words; the 5,000 kWh row showed it. About four lines at 390 (one more than the draft), two at 1280. Trust, in the most-read spot. S. |
| 398, 411 | price sub-line | the whole job: installed, permits and papers filed, VAT included | accept (the fact behind "papers filed" is the home page's tick "Permit and net metering papers filed by us"; for the battery-first house the permit papers alone, still true) |
| 418 | button | Try other answers | accept |
| 422 (39–46) | What you get | What you get: 6 panels of 585 W (3.51 kWp) on about 15 m² of roof, a 6 kW hybrid inverter and an 11.7 kWh lithium battery, enough for a typical night of your use when the grid is down. · panels only: …on about 15 m² of roof and a 6 kW hybrid inverter. · 5,000 kWh: 40 panels of 585 W (23.40 kWp) on about 103 m² of roof and 2 hybrid inverters of 12 kW. · with its battery: …a 51.2 kWh lithium battery, about 9 hours of your evening use when the grid is down. | accept (every figure of the old line inside one sentence; the battery note closes it) |
| 425 | What it does, first sentence | What it does: the panels make about 444 kWh a month, 111% of the 400 kWh you use. | accept |
| 426 | net-metering sentence (over 100%) | By day the panels run the house first; the extra goes to your electric company and comes back as credit at its generation rate, so what still comes is a small bill for the fixed charges and the hours the grid covers. | accept |
| 427 | battery-first sentence | Sized so the panels and the battery carry an ordinary day on their own; once the battery is full, the extra sun goes unused, because nothing is sold back. | accept |
| 428 | battery-first import | The grid still steps in for about N kWh a year, mostly in the rainy months. | accept (hidden under 50 kWh a year, as before; not seen in the 400 kWh walk, the branch unchanged) |
| 51 | coveredLine, net metering | The house takes 30% of what it uses straight from the panels; the rest of the day's sun goes back through the meter as credit on your bill. | accept |
| 52 | coveredLine, battery first | The panels and the battery cover 100% of what you use; the grid is only the spare. | accept |
| 53 | coveredLine, with the battery | Between them, the panels by day and the battery after dark cover 96% of what you use. | accept |
| 435–437 | alternative, battery shown | Panels only, without the battery: ₱180,000, the bill about ₱1,252 a month, pays for itself in 4.1 years. The panels do the saving either way; the battery is what keeps the lights on when the street goes dark. | accept |
| 439 | link | Show it without the battery | accept |
| 444–445 | alternative, battery not shown | Want the lights on when the street goes dark? An 11.7 kWh battery is about ₱128,000 more, enough for a typical night of your use when the grid is down; the bill about ₱199 a month, pays for itself in 7.4 years. · 250 kWh: …when the grid is down; a small bill, pays for itself in 16.8 years. · 5,000 kWh: A 51.2 kWh battery is about ₱733,000 more, about 9 hours of your evening use when the grid is down; the bill about ₱25,274 a month, pays for itself in 3.4 years. | accept (the comfort opens, the money follows, the note inside the sentence) |
| 447 | link | Show it with the battery | accept |
| 57 | billWords | the bill about ₱1,252 a month · a small bill | accept (the "bill small a month" slip gone in both branches) |
| 455 | booking h3 | The exact figure is one free visit away. | accept (two lines at 390) |
| 478 | booking hint | Most installers quote from a satellite photo. We put a test panel and meters on your roof, read the sun and the shade, and sit down with your bill. Then your proposal, exact to your roof, every peso and every part on paper. You decide after. | accept |
| 459 | thank-you, first paragraph | Thank you, Maria. We will message or call you within one working day to set the day; visits are usually within the week. That is all for now. Keep a recent bill where you can find it; it goes on the table at the visit. | accept (the owner's name and the promise still from the profile) |
| 462 | thank-you, second paragraph | What happens next: one free visit, with the test panel on the roof and your bill and appliances at the table; your roof check card the same evening; your proposal within two working days, valid 15 days. You decide with all of it in front of you. | accept |
| 533 | foot | Worked out for a house in Pila, Laguna using about 400 kWh a month, mostly in the evening. About 3.8 tonnes of CO₂ avoided a year. | accept |
| 535 | foot, law line | This is an estimate, not a quotation: on the free on-site assessment we measure your roof and the sun on it, and the proposal that follows is exact. | accept |
| 297 | summary, line 1 | Solar estimate from PL Development Inc. for Pila, Laguna: · a pin: Solar estimate from PL Development Inc. near Quezon City, Metro Manila: | **change to**: `Solar estimate from ${profile?.company_name || 'PL Development Inc.'} for a house${placeAfter(result.inputs.place, 'in')}:` → "Solar estimate from PL Development Inc. for a house in Pila, Laguna:" / "…for a house near Quezon City, Metro Manila:" / "…for a house:". Reason: with a pin the draft's line tells the spouse on Messenger where the company is, not whose house; the foot already says "a house in". Minor. S. |
| 298 | summary, bill | Bill ₱4,803 → about ₱199 a month; about ₱55,000 saved in the first year; pays for itself in 7.4 years. · small: Bill ₱3,002 → a small bill; … | accept (the bill first, as asked; "a small bill a month" gone) |
| 299 | summary, price | Price ₱308,000, installed, permits and VAT included. | accept (the proposal's own form) |
| 300 | summary, system | What it takes: 6 panels of 585 W (3.51 kWp), a 6 kW hybrid inverter and an 11.7 kWh lithium battery, enough for a typical night of your use when the grid is down. | accept |
| 302 | summary, law line | This is an estimate, not a quotation; the free on-site assessment makes it exact. | accept |
| 28, 34 | `an()`, `placeAfter()` | (code: the article as the figure is spoken; the place after "for" / "in") | accept |

## Wizard.tsx

| Line | Element | Text | Verdict |
|---|---|---|---|
| 11 | card 1, lower bill | I just want a lower bill. · Solar with net metering. The panels run the house by day, and the extra comes back as credit on your bill. A battery can come later, whenever you want lights in a brownout too. | accept (the home page's words; the kind opens the small text) |
| 12 | card 1, lights on | I want the lights on when the street goes dark. · Solar with a battery. The panels run the house by day and bring the bill down; the battery carries the evening and the brownouts. The extra still earns credit on your bill. | accept |
| 13 | card 1, roof runs the house | I want my roof to run my house. · Battery first, nothing sold back. More panels and a battery carry the house day and night, and the grid steps in only when both fall short. For homes that would rather keep their own power than sell it, and for places where net metering is out of reach. | accept |
| 17 | slider, morning | Cooking, laundry, the pump and aircon early in the day, when the panels are already at work. | accept |
| 18 | slider, all day | Someone is home most of the day, so the house uses the sun as the panels make it. | accept |
| 19 | slider, evening | The house is busiest after dark: aircon, TV, cooking. This is the evening a battery would carry. | accept |
| 222 | town hint, opening | Your town picks the sun records your estimate is built on. At the house? [Use my location] and the town fills in. | accept |
| 226 | town hint, close | Not in the list? Message us; we come to wherever the house is. | accept (About's "we travel to wherever yours is") |
| 241 | kWh hint | The kWh is printed on the bill, usually next to "consumption". It sets how many panels your house needs, so you buy only what the house uses. | accept |
| 329 | not-ready hint | Pick your town and type the kWh from your bill first. · Type the kWh from your bill first. | accept |

## DayScene.tsx

| Line | Element | Text | Verdict |
|---|---|---|---|
| 173 | caption, charging and exporting | The house runs on the sun; the extra fills tonight's battery, and the rest goes back through the meter as credit. | accept (seen 1–3 PM on the 400 kWh house, 12 NN–3 PM at 250 kWh) |
| 174 | caption, charging | The house runs on the sun; the extra fills tonight's battery. | accept |
| 175 | caption, exporting | The house runs on the sun; the extra goes back through the meter as credit. | accept |
| 176 | caption, battery full | The house runs on the sun; the battery is full for tonight. | accept (seen 1–3 PM on the battery-first house) |
| 180 | caption, sun rising | The sun is up and the panels are taking over. | **change to**: `The sun is up and the panels are starting to carry the house.` Reason: the caption shows only while the panels make less than the house uses, and the readout under it says who carries the rest: at 6 AM on the 400 kWh house "Sun 0.2 kW → house 0.2 kW · battery 0.1 kW → house · grid 0.1 kW → house"; on the 5,000 kWh morning house "Sun 1.1 kW … grid 11 kW → house" at 6 AM and "Sun 5.2 kW … grid 9.5 kW" at 7 AM. "Taking over" says the handover is done while the row shows it has barely begun. My brief's line; one or two seconds of the day. Minor. S. |
| 181 | caption, sun setting, battery | The sun goes down and the battery takes over. | accept |
| 181 | caption, sun setting, grid | The sun goes down and the grid takes over, as it does today. | accept |
| 187 | caption, evening on the battery | The battery carries the evening on your own power: the lights, the fan, the TV, the Wi-Fi. | **change to**, with one condition: keep the draft's sentence for the hours the battery alone feeds the house, and when the grid also feeds it in that hour (`r.import_kw >= MIN_KW`, a comparison of the kind line 189 already makes) show `The battery carries the evening as far as it goes; the grid tops up the rest.` Reason: the caption follows `discharge_kw` alone, and the engine's averaged day has the grid in the same hour more often than the 400 kWh walk shows (`capcheck.py`): an 800 kWh evening house (a bill of about ₱9,600, the brownout ad's buyer) reads "on your own power" at 10 PM, 11 PM and 12 MN over a readout of "grid 0.1–0.3 kW"; 1,500 and 3,000 kWh the same; the 5,000 kWh evening house at 8 PM shows "Battery 5.6 kW → house · grid 11 kW" under the same words; the 5,000 kWh morning house with its 51.2 kWh battery has the grid giving more than the battery from 7 PM to 10 PM. The readout contradicts the caption on the same line, and a comparing buyer sees it. If the coordinator will not add the condition, the words-only fallback is `The battery carries the evening: the lights, the fan, the TV, the Wi-Fi.`, which still overstates the 5,000 kWh evening, so the condition is the fix I ask for. Trust, for the larger evening house. S. |
| 190 | caption, evening on the grid, day exported | The evening runs on the grid, as it does today; the day's extra came back as credit. | accept (shown only when some hour sent power back) |
| 190 | caption, evening on the grid | The evening runs on the grid, as it does today. | accept |
| 477 | aria-label | …and the meter with net metering: an ordinary day, the sun up from 6 AM to 6 PM, … | accept |
| 657 | strip, build-up | Dawn · your house, fitted out piece by piece | accept |
| 658 | strip, build-up caption | Then an ordinary day, hour by hour. | accept |

## quick.py

| Line | Element | Text | Verdict |
|---|---|---|---|
| 38 | the too-little refusal | That is a very small bill; solar would not pay for itself at that use. If the kWh on your bill is higher, type that figure. | accept (my brief's optional line, taken; the test's assert follows it) |
| 241 | the cap warning | Your house would take more than 40 panels, so this estimate stops at 40; on the free on-site assessment we see how many your roof can hold. | accept (seen live, `phone-net_metering-5000-result-top.png`) |
| 243 | the off-map warning | That spot is outside the Philippines, where we install. Check the pin, or pick your town instead. | accept |

---

## The departures (the copywriter's eleven)

1. Town hint, "your estimate is built on" for "we size from": **accepted**; the customer's side of the verb, better than mine.
2. kWh hint, "It sets how many panels your house needs, so you buy only what the house uses": **accepted**; "how many panels" is what the lead promised.
3. "as it does today" for "like today" in the two grid captions: **accepted**; "like today" could be the day on the screen.
4. "The house takes 30%…" for "runs 30%": **accepted**; mine did not parse.
5. "2 hybrid inverters of 12 kW" for "2 × 12 kW": **accepted**; the panels' pattern, no "×" anywhere.
6. `an()` before the engine's figure ("an 11.7 kWh", "a 12 kWh"): **accepted**; my brief wrote "a 12 kWh" before fc89f13 made the line print the chip's figure.
7. `placeAfter()` for the pin's "near …" and "outside …": **accepted**; the foot and summary had "in near…" before; see change 4 for the summary's first line.
8. Thank-you, the full stop and the semicolon for my comma splice: **accepted**.
9. Foot, "This is an estimate, not a quotation:" without "from your answers": **accepted**; the rail wants the law line word for word and "Worked out for a house … using" says it.
10. "a small bill" in both alternative branches: **accepted**; the slip is gone.
11. The proof sentence not added: **accepted**, and now withdrawn under the owner's ruling that the installations carry no "our own" claim.

## What the draft missed from the angle brief

Nothing in words. Every "Run" line of sections 2.1–2.16 is in the diff or departed from as listed above; the three keeps
(2.8's labels, 2.12's labels and privacy line, 2.16's down notes and location errors) are kept; the three notes for the
coordinator (the warranties printed twice, the chip's kWh against the line's) were already settled by fc89f13 and the
"bill small a month" slip by this draft. Two matters outside the writer's remit, both logic:

1. The 5 AM caption in a morning house (the copywriter's own note: the cooking hour has begun, so 5 AM is not "night" and
   "The evening runs on the grid…" shows for a second before dawn; seen in my 5,000 kWh morning walk). The uncommitted
   edit in the worktree already counts `h < 6` as night.
2. The "own power" condition of change 3, not in the uncommitted edit, which keeps the draft's caption and its test.

## Notes that are not line changes

1. **Under the owner's later rulings.** Of my four changes, 1 (the hero sub-line), 2 and 3 (the two captions) and 4 (the
   summary's first line) all stand in the uncommitted teaser edit, whose text at those four places is the draft's. The
   draft's `an()`, `kwh2` and `coveredLine` go away with the sizes in that edit, so departures 4–6 become moot there;
   nothing in this review asks for a figure to be added or kept against the teaser.
2. **The hero sub-line at the capped house.** Beyond change 1, the 5,000 kWh result reads "₱60,033 → about ₱28,854 / about
   ₱31,179 a month stays in your pocket; what still comes is your electric company's fixed charges" under a warning that
   the estimate stopped at 40 panels. Change 1 makes the sentence true there too; no further words needed.
3. **The sticky bar's "Estimated price" and the hero's label still match**, as the rail asks; the uncommitted edit changes
   the bar to the new bill, which is the next round's call, not this draft's.
4. **Ask the owner** (unchanged from the angle brief's section 5, in priority): Settings' phone, Messenger and owner's name
   (the thank-you's "We", the summary's missing "Questions:" line, the booking card's missing human); the PEE's name and
   PRC number; the brands line; the inverter's switch-over time; the installation-day outage length.

---

## Verdict on the whole

Yes. The widget now speaks the voice the website brought the visitor in with: a promise on landing ("Your new bill is a
minute away."), the three wants in the customer's own words with the kind as the label, each question saying what the
house gets for the answer, a result that opens on the money that stays in the house, a system described as what it does
for the family with every engine figure inside the sentence, a battery sold as the evening when the street is dark and
left out without loss, a booking card that sells one calm visit and the decision afterwards, and a forwarded summary the
spouse can decide on in ten seconds. Nothing claims beyond the engine and the round-7 facts; the honesty lines are inside
the sentences; no figure or rounding moved.

The four changes are small and all S: the hero's "what still comes" line should name the hours the grid covers as well
as the fixed charges, because that is what the ₱1,252 and the ₱28,854 are; the dawn caption should say the panels are
starting, not taking over, over a readout that shows the grid carrying the house; the battery-evening caption should give
way to "the battery carries the evening as far as it goes; the grid tops up the rest" in any hour the grid also feeds the
house, which the engine's averaged day produces on the 800 to 5,000 kWh evening houses the brownout ad is aimed at; and
the summary's first line should read "for a house in / near …" so a pin never puts the company near Quezon City.

---

## Five lines for the coordinator

1. **Change, Estimate.tsx:386** → `about ${php0(e.savings_monthly)} a month stays in your pocket; what still comes is your electric company's fixed charges and the hours the grid covers` (the small-bill branch at 385 stays).
2. **Change, DayScene.tsx:180** → `The sun is up and the panels are starting to carry the house.`
3. **Change, DayScene.tsx:187** → keep the draft's sentence when the battery alone feeds the house; when `r.import_kw >= MIN_KW` in that hour, `The battery carries the evening as far as it goes; the grid tops up the rest.`
4. **Change, Estimate.tsx:297** → `Solar estimate from ${profile?.company_name || 'PL Development Inc.'} for a house${placeAfter(result.inputs.place, 'in')}:`
5. **Accepted departures:** all eleven, the proof sentence withdrawn under the owner's ruling. **Nothing must go.** 54 lines accepted as drafted.
