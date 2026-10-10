# Round 8 copywriter report: the estimate widget in the website's voice

From the copywriter to the coordinator and the marketing and sales specialist, 10 October 2026. Four files and one test:
`frontend/src/estimate/Estimate.tsx`, `Wizard.tsx`, `DayScene.tsx`, `backend/solarapp/core/quick.py`, and the two asserts in
`backend/tests/test_quick.py` that pinned the strings `quick.py` changed. Every figure, its rounding, every class, id, `aria-*`,
`data-*`, handler, state and enabled rule stays; the day scene's drawing, `readout()`, the chips and the geometry are untouched.
Read back as the customer on a private server (port 8212, scratch database, the worktree's backend and build) at 390 × 844 and
1280 × 900: the four cards, the result with the scene over a full day for the three goals, the alternative in both states, the
booking card, one booking under a made-up name, the thank-you and the copied summary. Screenshots and the recorded texts are in
`/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/copy/` (`phone-*`, `desk-*`, `*.json`, `walk.js`).
The figures quoted are the engine's for a Pila, Laguna house using 400 kWh a month, mostly in the evening.

Checks: `npm run build` clean; `npm run lint` at the 7-warning baseline, none in `src/estimate`; backend 209 passed.

## Section by section: before, after, the angle

### 2.1 The intro
- Before: h1 "What would your bill be with solar?"; lead "Four questions, about a minute: your bill before and after, the price,
  and how many panels it takes. The only call you get is the free on-site assessment you book, and that one makes the figure
  exact." (six lines at 390).
- After: h1 "Your new bill is a minute away."; lead "Four questions, then the bill you would pay instead, the price of the whole
  job, and how many panels it takes. The only call you get is the one you book." (two lines and four).
- Angle: the promise the band made ("Your number is a minute away") kept word for word on landing; the objection "they will call
  me" answered in the last sentence.

### 2.2 Card 1, the three wants (`<b>` title, `<small>` text; the kind's name opens the small text)
- Before: "A lower bill" / "A lower bill, and lights in a brownout" / "Battery first, nothing sold back", each with the engine's
  sentence under it ("Solar runs the house by day. Extra power goes to your electric company as credit on your bill (net
  metering)…").
- After: "I just want a lower bill." · "Solar with net metering. The panels run the house by day, and the extra comes back as
  credit on your bill. A battery can come later, whenever you want lights in a brownout too." / "I want the lights on when the
  street goes dark." · "Solar with a battery. The panels run the house by day and bring the bill down; the battery carries the
  evening and the brownouts. The extra still earns credit on your bill." / "I want my roof to run my house." · "Battery first,
  nothing sold back. More panels and a battery carry the house day and night, and the grid steps in only when both fall short.
  For homes that would rather keep their own power than sell it, and for places where net metering is out of reach."
- Angle: the home page's three wants, in the same words, so the funnel keeps one voice at the moment of choice; the kind stays
  on the card as the label.

### 2.3 Card 2, the town
- Before: "At the house? Use my location and the town fills in. Not in the list? Message us."
- After: "Your town picks the sun records your estimate is built on. At the house? Use my location and the town fills in. Not in
  the list? Message us; we come to wherever the house is."
- Angle: why the question matters (the sun over their own town) and the About page's promise that the company drives to them.

### 2.4 Card 3, the kWh
- Before: "The kWh is printed on the bill, usually near "consumption"."
- After: "The kWh is printed on the bill, usually next to "consumption". It sets how many panels your house needs, so you buy
  only what the house uses."
- Angle: control: the one card that asks the visitor to get up and find something says what they get for it.

### 2.5 Card 4, the slider (stops keep: "Mostly morning" / "All day" / "Mostly evening", one line at 390)
- Before: "Cooking, laundry, the pump and aircon early in the day." / "Someone is home most of the day." / "The house is busiest
  after dark: aircon, TV, cooking."; the not-ready hint "Pick your town and enter your monthly use first." / "Enter your monthly
  use first."
- After: "Cooking, laundry, the pump and aircon early in the day, when the panels are already at work." / "Someone is home most
  of the day, so the house uses the sun as the panels make it." / "The house is busiest after dark: aircon, TV, cooking. This is
  the evening a battery would carry."; hint "Pick your town and type the kWh from your bill first." / "Type the kWh from your
  bill first."
- Angle: the household's rhythm tied to what the panels (and, for an evening house, a battery) do with it.

### 2.6 The result heading
- Before: "Your estimate". After: "Your estimate for Pila, Laguna" (a pin reads "Your estimate near Quezon City, Metro Manila";
  a pin outside the Philippines reads "Your estimate", the warning under it saying where it fell).
- Angle: theirs, named.

### 2.7 The day scene (strings only: `caption()`, the two strip captions, "a typical day" in the `aria-label`)
- Strip, before: "Dawn · your system, piece by piece" / "Then a typical day, hour by hour." After: "Dawn · your house, fitted out
  piece by piece" / "Then an ordinary day, hour by hour."
- "The panels wake up." → "The sun is up and the panels are taking over."
- "The house runs on the sun; the extra fills the battery and goes out as credit." → "…the extra fills tonight's battery, and the
  rest goes back through the meter as credit."; "…the extra fills the battery." → "…the extra fills tonight's battery.";
  "…the extra goes out as credit." → "…the extra goes back through the meter as credit."; "…the battery is full." → "…the battery
  is full for tonight."; "The house runs on the sun." keeps.
- "The sun goes down; the battery picks up the rest." → "The sun goes down and the battery takes over."; "…the grid picks up the
  rest." → "The sun goes down and the grid takes over, as it does today."
- "The battery carries the evening." → "The battery carries the evening on your own power: the lights, the fan, the TV, the
  Wi-Fi."; "The grid steps in for the evening." → "The evening runs on the grid, as it does today; the day's extra came back as
  credit." when any hour of the day sent power back (`day.some((x) => x.export_kw >= MIN_KW)`), otherwise "The evening runs on
  the grid, as it does today."
- "Everyone asleep, the fridge on the battery." / "…on the grid." keep. The aria-label: "a typical day" → "an ordinary day".
- Angle: the family's day with the engine's kW under it as the proof; for the no-battery buyer the evening is what they have
  now, paid for by the day's credit, not a loss. Seen over a full 24-second day for the three goals, five sizes
  (`phone-*-400.json`, `phone-combination-250.json`, `phone-net_metering-5000.json`, the `scene` arrays).

### 2.8 The hero
- Before: "about ₱4,604 less each month; your electric company's fixed charges stay on the bill" (small bill: "…less each month;
  what stays is your electric company's fixed charges and the grid's hours in long rainy spells"); price sub-line "installed,
  with permits, VAT included".
- After: "about ₱4,604 a month stays in your pocket; what still comes is your electric company's fixed charges" (small bill:
  "…stays in your pocket; what still comes is your electric company's fixed charges, and the grid's hours in long rainy
  spells"); price sub-line "the whole job: installed, permits and papers filed, VAT included" (both places). The labels, the big
  figures, "Pays for itself in", "about ₱55,000 saved in the first year", "Saved over 25 years", "after paying for the system,
  its upkeep and replacement parts" keep.
- Angle: relief said as money that stays, the honest remainder as what still comes; the price as the whole thing for the buyer
  comparing two quotes.

### 2.9 The two actions
- "Book my free on-site assessment" keeps (the hero button, the form button and the sticky bar). "Estimate another one" → "Try
  other answers".
- Angle: it says what happens (the cards come back) and invites the second run.

### 2.10 What goes in / what it makes
- Before: "What goes in: 6 × 585 W panels (3.51 kWp), 6 kW hybrid inverter, 11.7 kWh lithium battery (enough for a typical night
  of your use when the grid is down). Needs about 15 m² of roof." / "What it makes: about 444 kWh a month, 111% of the 400 kWh you
  use. Daytime power runs the house first; the extra goes to your electric company and comes back as credit at its generation
  rate, so a small bill stays for the fixed charges and the grid's hours. Covered by solar, by day and from the battery: 96% of
  what you use."
- After: "What you get: 6 panels of 585 W (3.51 kWp) on about 15 m² of roof, a 6 kW hybrid inverter and an 11.7 kWh lithium
  battery, enough for a typical night of your use when the grid is down." (panels only: "…on about 15 m² of roof and a 6 kW
  hybrid inverter."; two inverters: "2 hybrid inverters of 12 kW") / "What it does: the panels make about 444 kWh a month, 111%
  of the 400 kWh you use. By day the panels run the house first; the extra goes to your electric company and comes back as credit
  at its generation rate, so what still comes is a small bill for the fixed charges and the hours the grid covers." then by goal:
  with the battery "Between them, the panels by day and the battery after dark cover 96% of what you use."; net metering "The
  house takes 30% of what it uses straight from the panels; the rest of the day's sun goes back through the meter as credit on
  your bill."; battery first "Sized so the panels and the battery carry an ordinary day on their own; once the battery is full,
  the extra sun goes unused, because nothing is sold back. The grid still steps in for about N kWh a year, mostly in the rainy
  months. The panels and the battery cover 100% of what you use; the grid is only the spare."
- Angle: what goes on the house and what it does for it, every figure inside the sentence, the battery note closing it rather
  than bracketed.

### 2.11 The battery alternative (the "bill small a month" slip fixed in both branches)
- Before, battery shown: "Without the battery: ₱180,000, bill about ₱1,252 a month, pays for itself in 4.1 years. The battery
  buys the brownout comfort; the panels do the saving. Show without the battery". Not shown: "Add a battery for brownouts: about
  ₱128,000 more (11.7 kWh, enough for a typical night of your use when the grid is down), bill about ₱199 a month, pays for
  itself in 7.4 years. Show with the battery".
- After, battery shown: "Panels only, without the battery: ₱180,000, the bill about ₱1,252 a month, pays for itself in 4.1 years.
  The panels do the saving either way; the battery is what keeps the lights on when the street goes dark. Show it without the
  battery". Not shown: "Want the lights on when the street goes dark? An 11.7 kWh battery is about ₱128,000 more, enough for a
  typical night of your use when the grid is down; the bill about ₱199 a month, pays for itself in 7.4 years. Show it with the
  battery". Small bill (250 kWh): "…when the grid is down; a small bill, pays for itself in 16.8 years." The hours form of the
  note prints as the engine gives it ("about 9 hours of your evening use when the grid is down", the 5,000 kWh case).
- Angle: adding it buys the evening when the street is dark; leaving it out keeps the saving whole.

### 2.12 The booking card
- Before: h3 "Want the exact figure? We come and measure. The visit is free."; hint "Most installers quote from a satellite
  photo. We put a test panel and meters on your roof, measure the sun and the shade, and quote exactly. The visit is free, and
  you decide after."
- After: h3 "The exact figure is one free visit away."; hint "Most installers quote from a satellite photo. We put a test panel
  and meters on your roof, read the sun and the shade, and sit down with your bill. Then your proposal, exact to your roof,
  every peso and every part on paper. You decide after." Labels, placeholders, the button, "Your name and a number or Messenger
  name are enough." and the profile's privacy line keep. The proof sentence of the marketing brief's option was not added
  (the coordinator's call: it would live in code).
- Angle: calm and control: one free visit, the measurement, every peso and every part on paper, the decision theirs.

### 2.13 The thank-you
- Before: "Thank you, Maria. We will message or call you within one working day to pick a day; visits are usually within the
  week. That is all for now: keep a recent bill where you can find it." / "What happens next: one free visit, with the test
  panel on the roof and your bill and appliances at the table; your roof check card the same evening; your proposal within two
  working days, valid 15 days."
- After: "Thank you, Maria. We will message or call you within one working day to set the day; visits are usually within the
  week. That is all for now. Keep a recent bill where you can find it; it goes on the table at the visit." / "…valid 15 days.
  You decide with all of it in front of you." The h3, "Open Messenger" (when set) and "Copy my estimate" / "Copied" keep; the
  owner's name and the callback promise come from the profile as before.
- Angle: relief that it is done, and the three papers in order, closing on the customer's control.

### 2.14 The foot and the sticky bar
- Before: "Sized for a house using about 400 kWh a month, mostly in the evening, in Pila, Laguna. About 3.8 tonnes of CO₂
  avoided a year. This is an estimate from your answers, not a quotation. On the free on-site assessment we measure your roof
  and the sun on it, then give you an exact proposal."
- After: "Worked out for a house in Pila, Laguna using about 400 kWh a month, mostly in the evening. About 3.8 tonnes of CO₂
  avoided a year. This is an estimate, not a quotation: on the free on-site assessment we measure your roof and the sun on it,
  and the proposal that follows is exact." The sticky bar keeps ("Estimated price ₱308,000 / Book my free on-site assessment").
- Angle: the small print as a confident company's last word, the law line word for word.

### 2.15 The copied summary (plain text, the same seven parts, the bill first)
- Before: company and place; "6 × 585 W panels (3.51 kWp), 6 kW hybrid inverter, 11.7 kWh lithium battery (enough for…).";
  "Estimated price ₱308,000 installed, VAT included."; the bill line; the lifetime line; "This is an estimate, not a quotation.";
  the links.
- After:
  ```
  Solar estimate from PL Development Inc. for Pila, Laguna:
  Bill ₱4,803 → about ₱199 a month; about ₱55,000 saved in the first year; pays for itself in 7.4 years.
  Price ₱308,000, installed, permits and VAT included.
  What it takes: 6 panels of 585 W (3.51 kWp), a 6 kW hybrid inverter and an 11.7 kWh lithium battery, enough for a typical night of your use when the grid is down.
  Saved over 25 years: about ₱957,000, after paying for the system and its upkeep.
  This is an estimate, not a quotation; the free on-site assessment makes it exact.
  Questions: m.me/… · Run your own: …/estimate
  ```
  (the last line only when Settings carry the links; the scratch database has none). The small-bill form reads "Bill ₱3,002 →
  a small bill; …" (the old text printed "a small bill a month").
- Angle: the spouse or the parent on Messenger decides on the bill, so it is the second line.

### 2.16 The warnings and the error notes (`quick.py`)
- "Your house needs more than 40 panels; we capped the estimate there, and on the on-site assessment we see how many your roof
  really takes." → "Your house would take more than 40 panels, so this estimate stops at 40; on the free on-site assessment we
  see how many your roof can hold." (seen live in the 5,000 kWh walk.)
- "This location is off the map of the Philippines, where we install. Check the pin, or pick your town instead." → "That spot
  is outside the Philippines, where we install. Check the pin, or pick your town instead."
- The optional too-little line, taken: "That's very little usage; a solar system would not pay for itself. If the kWh on your
  bill is higher, enter that figure." → "That is a very small bill; solar would not pay for itself at that use. If the kWh on
  your bill is higher, type that figure."
- `backend/tests/test_quick.py` pinned two of these ("off the map of the Philippines", "very little usage"); the asserts now read
  "outside the Philippines" and "very small bill". The down notes and the location errors keep. `profile.py` untouched.
- Angle: a person explaining, not a system refusing.

## Departures from the marketing brief (both texts, one line of reasoning)

1. 2.3, the town hint. Brief: "Your town picks the sun records we size from." Run: "Your town picks the sun records your
   estimate is built on." "Size from" is the installer's verb; the customer reads what the record does for their estimate.
2. 2.4, the kWh hint. Brief: "It sizes the panels to what your house uses, so you buy only what the house needs." Run: "It sets
   how many panels your house needs, so you buy only what the house uses." Same verb; "how many panels" is the figure the lead
   promised.
3. 2.7, the grid captions. Brief: "…the grid takes over, like today." / "The evening runs on the grid, like today; …". Run: "as
   it does today" in both. "Like today" can be read as the day on the screen; "as it does today" says the arrangement the house
   has now.
4. 2.10, the net-metering coverage line. Brief: "The house runs 30% of what it uses straight from the panels; …". Run: "The
   house takes 30% of what it uses straight from the panels; …". "Runs a percentage" does not parse; "takes" keeps the subject
   and the figure.
5. 2.10, several inverters. The old "2 × 12 kW hybrid inverters" is now "2 hybrid inverters of 12 kW" (the brief rules out "×"
   for the panels; the inverters follow the same pattern as "6 panels of 585 W").
6. 2.10 and 2.11, the article before the engine's number. Brief: "a 12 kWh lithium battery", "A 12 kWh battery". Since fc89f13
   the battery prints as the chip does (11.7), so the line read "a 11.7 kWh"; a four-line helper (`an()`) picks "a" or "an" the
   way the figure is spoken (an 8 kW, an 11.7 kWh, an 18 kWh, a 12 kWh, a 51.2 kWh). The brief's words, said right aloud.
7. 2.6, 2.14, 2.15, the place. Brief: "Your estimate for {place}". The engine's place for a pin starts with "near" ("near Quezon
   City, Metro Manila") or reads "outside the Philippines", so "for near…" and "in outside…" would print. A helper
   (`placeAfter()`) bends the phrase: "Your estimate for Pila, Laguna" / "Your estimate near Quezon City, Metro Manila" / "Your
   estimate" when the pin fell outside (the warning says where); the same for the foot's "a house in…" and the summary's "for…".
   The old foot and summary had the "in near…" form already.
8. 2.13, the thank-you's first paragraph. Brief: "That is all for now: keep a recent bill where you can find it, it goes on the
   table at the visit." Run: "That is all for now. Keep a recent bill where you can find it; it goes on the table at the visit."
   The comma spliced two sentences; the full stop and the semicolon keep the three beats.
9. 2.14, the foot's law line. Brief: "This is an estimate from your answers, not a quotation: …". Run: "This is an estimate, not
   a quotation: …". The coordinator's rail wants the line word for word; "from your answers" is already said by "Worked out for
   a house … using about 400 kWh a month".
10. 2.11, the coordinator's call: "a small bill" in place of "the bill about ₱… a month" in both branches (the brief's words).
11. 2.12, the coordinator's call: the proof sentence ("Our own home in Pila, Laguna…") not added.

## Phone-width checks (390 × 844; the desktop at 1280 × 900 alongside)

- The h1 two lines (the rail allows three), the lead four; at 1280 one and two.
- The three goal cards: titles one, two and one lines; the small texts six, seven and seven lines; no text overflow; the page
  never wider than the viewport (`pageOverflow: false` in every walk). The choice buttons' right border is clipped by the stage
  at both widths exactly as before the words changed (the marketing's `phone-combination-card1.png` shows the same edge; the
  stage's scrollWidth is 19 px over its clientWidth with the old words and the new): a CSS matter for the coordinator, not a
  text one.
- The slider's three stops on one line, no overflow; the stop text two lines.
- The result: the h2 one line; the hero's bill sub-line three lines, the price sub-line two; the actions stacked; the three
  lines; the alternative in both states (`phone-combination-400-alt-a.png`, `-alt-b.png`, `-lines-alt.png`); the booking h3 two
  lines; the booking card (`-book.png`, `-book-filled.png`); the thank-you (`-thanks.png`, `-thanks-viewport.png`); the foot
  (`-basis.png`); the sticky bar two lines on the button as before; the copied summary read back through the clipboard shim
  (`copied` in `phone-combination-400.json` and `desk-combination-400.json`).
- The scene's captions sampled four times a second over 31 s for three goals and five sizes: every branch of `caption()` seen
  (`scene` in the json files). The longest caption (the battery evening) takes three lines at 390 under the drawing; the strip
  grows, the drawing does not move (`-scene-noon.png`, `-scene-evening.png`). No console errors in any walk.
- A note outside my remit: in a morning house, 5 AM is not "night" by `caption()`'s load test (the cooking hour has begun), so the
  evening caption shows for one second before dawn ("The evening runs on the grid…"; the old words had "The grid steps in for
  the evening." there). One condition (`h < 6` counted as night) would end it; the logic is the coordinator's.

## What I wanted to say and could not (what exactly to ask for)

1. A person's name in the thank-you and on the booking card: "Juan will message or call you…" prints as soon as Settings › owner's
   name and phone are filled; until then it is "We" and the trust list has no human.
2. The summary's "Questions: m.me/…" line, the thank-you's "Open Messenger" button and the down note's "Message us on Facebook"
   link: Settings › Messenger (or Facebook).
3. "named by brand on your proposal" in the battery add-on line: Settings › brands, and the owner's yes to naming them in the
   widget.
4. "before anyone notices" in the evening caption: the inverter's switch-over time from its datasheet; until then "takes over"
   and "by itself" are the words.
5. "your power is off for about an hour on the second morning" in the thank-you's what-happens-next: the installation-day outage
   length.
6. One proof line on the result ("Our own home in Pila, Laguna has run on what we sell since 2023"): the owner's yes, and a
   profile field for it so it comes from Settings like every other fact on the result, not from code.
7. The engineer's line on the booking card: the PEE's name and PRC number in Settings.
