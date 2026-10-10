# Round 7, marketing: line-by-line review of the merged site

From the marketing and sales specialist, 10 October 2026. Read-only: nothing in the repository was changed and
`site/dist` was not rebuilt (its files still carry the 03:21:06 stamp). Read as the customer reads it at
http://127.0.0.1:8195 (phone 390 × 844, desktop 1280 × 800; Playwright scripts `shots.js`, `scrolled.js`, `rm.js` and
the screenshots `r-*.png`, `s-*.png` in this folder) and in source (`site/pages/*.html`, `site/partials/proof.html`,
`site/layout.html`; line numbers are the source files'). Checked against the round-7 brief's facts, my audit
(`docs/audits/round-7/marketing-audit.md`) and the copywriter's list of departures.

Verdict on each line: **accept**, **change to** (exact text), or **must go**. Nothing must go.

---

## What was verified before the lines

- **Claims.** Every figure, time, town, kind and year on the six pages is in the brief: 13.75 / 4.56 / 9.12 kWp, the
  30 kWh battery, ₱33,000+, 2023, early 2026, Pila, Fairview (Quezon City), Tanauan, the engine's 500 kWh example
  (4.1 kWp, 7 panels, about ₱193,000, under 4 years, about two thirds), "one minute", "the same evening", "within
  two working days", "one or two days" (the last three were on the baseline's step list). No brand, no guarantee, no
  customer voice, no financing word, no utility name, no "assessment", no exclamation mark, no superlative beyond
  "the lowest price of the three ways to go" and "oldest" (a fact). A regex sweep of the served text found only
  "Engineer" (matching "engine"), "started" (matching "star") and the allowed law lines.
- **Honesty lines, inside the sentences.** "An estimate, not a quotation" (index FAQ, footer); "the panels bring the
  bill down; the battery buys the comfort" (home card 2, Brownouts cost card, About tick); "the roof visit makes it
  exact" (How-it-works lead, two FAQ answers, Brownouts, both bands); "as the safety rules require" (index FAQ,
  Net metering); "about" before every savings figure; "a small bill still comes" (Net metering, index FAQ).
- **Register.** No "no/not" except the law line ("Without a battery, the panels pause…"), the pinned kind name
  "Battery first, nothing sold back", "no sign-up" in the footer and the share snippets, and "not a quotation".
- **The three homes.** Each card is headed by whose house and where, with the kWp on a chip; the section lead says
  "photographed by us from the air"; the caption of the owner's own home carries the credit and the brownouts.
  Nothing on any page could read as grabbed photos.
- **The proof strip.** `₱33,000+` / `2023` / `3` / `1` with their labels are true to the brief; the year does not
  count up; the two counters end on the text written in the page (checked after the animation and with JS off).
- **The phone's first screen** (`r-phone-index-first.png`): header, the rib roof 63–483 px, the eyebrow in one line,
  the h1 (three lines, 431–545), the lead (four lines), the gold button at 685–741 px, then the first two ticks.
  Roof, promise, button, all above the 844 px fold. The sticky bar appears after the hero and hides over the band
  and the footer. No horizontal scroll on any page.
- **Hooks and pins.** `backend/tests/test_site.py`: 9 passed (it builds into pytest's temp folder). On the static
  server all `is-empty` fragments stay hidden (11 on the home page, 13 on About, 9 on Brownouts and Net metering);
  the placeholders are stripped from `dist`; every `data-profile`, `data-profile-hide-if-empty` and
  `data-warranty-wrap` of the baseline is still there, and the pinned strings ("How it works", "What you get on
  paper", "Our installations", "Solar engineering for homes", the four tiles and labels, the small print, the photo
  file names, `data-count="33000"`, "₱33,000+", "2023", the placeholder markers) all survive.
- **Motion rules.** Under `prefers-reduced-motion: reduce`: no count-up, no reveal class, the hero photo's animation
  is `none`. With JavaScript off: nothing hidden, final figures in the page.

---

## Home (`site/pages/index.html`)

| Line | Element | Text | Verdict |
|---|---|---|---|
| 1 | share title | The bill goes down. With a battery, the lights stay on. · PL Development Inc. | accept |
| 2 | description | Rooftop solar for homes anywhere in the Philippines, measured on your own roof before we quote. Our own home has run on it since 2023. Four questions, one minute, free, no sign-up. | accept |
| 16 | eyebrow | Home solar in [the Philippines] | accept (departure: kept on the phone; one line, the button still lands at 685–741 px) |
| 17 | h1 | The bill goes down. With a battery, the lights stay on. | accept (departure from "comes down": "goes down" is the customer's own phrase and it wraps better) |
| 18 | lead | Panels sized to your bill bring it down every month; add a battery and the house runs through brownouts. A minute here shows you the price and your new bill. | accept |
| 20 | button | Get my free estimate | accept |
| 23–26 | ticks | Our own home on solar since 2023 / A test panel on your roof before we quote / Plans sealed by a Professional Electrical Engineer / Permit and net metering papers filed by us | accept (departure: shown on the phone too, under the button; they replace my single proof line and push nothing) |
| proof 3 | tile | ₱33,000+ / of net metering credit on the owner's own bill | accept |
| proof 4 | tile | 2023 / our own home went solar, and it has stood through every typhoon season since | accept |
| proof 5 | tile | 3 / family homes of our own, in Laguna and Quezon City | accept |
| proof 6 | tile | 1 / free visit: a test panel on your roof and your bill on the table, before we quote | accept |
| 37–38 | eyebrow, h2 | What do you want from solar? / Which one is you? | accept |
| 42–44 | card 1 | I just want a lower bill. / Solar with net metering / The bill stops being the thing you dread. The panels run the house by day, and the extra power goes to your electric company as credit on your bill. A battery can come later, whenever you want lights in a brownout too. | accept |
| 47–49 | card 2 | I want the lights on when the street goes dark. / Solar with a battery / The street goes dark and your windows stay lit. Solar by day, the battery at night and through brownouts, and the extra power still earns credit on your bill. The panels bring the bill down; the battery buys the comfort. | accept |
| 52–54 | card 3 | I want my roof to run my house. / Battery first, nothing sold back / Your roof runs the house; the grid is only the spare. More panels and a battery carry the house day and night, and the grid steps in only when both fall short. For homes that would rather keep their own power than sell it, and for places where net metering is out of reach. | accept |
| 63–64 | eyebrow, h2 | Our installations / We live with what we sell. | accept |
| 65 | lead | The owner's home, the owner's parents' house and the owner's wife's family house, photographed by us from the air. Three family roofs in Laguna and Quezon City; the first has run since 2023. | **change to**: `The owner's home, the owner's parents' house and the owner's wife's family house, photographed by us from the air. Three family roofs in Laguna and Quezon City; the oldest has run since 2023.` Reason: "the first" reads as the company's first job, which the facts do not say; the coordinator already ruled "oldest, not first" on About. S. |
| 74, 77–78 | card | 13.75 kWp / The owner's own home, Pila, Laguna / Where the owner's family lives, on three roofs with a 30 kWh battery. The house runs through brownouts, and net metering has built up more than ₱33,000 of credit on the bill since 2023. | accept |
| 87, 90–91 | card | 4.56 kWp / The owner's parents' house, Pila, Laguna / Eight panels carry the house by day, fixed through the roof sheet to the framing beneath. Installed early 2026. | accept (departure: inverter size, rails and conduit off the card) |
| 100, 103–104 | card | 9.12 kWp / The owner's wife's family house, Fairview, Quezon City / Sixteen panels in three groups across three faces of the hip roof, and the inverter is ready for a battery whenever one is wanted. Installed early 2026. | accept |
| 108–114 | placeholder card | (stripped from the public build) | accept |
| 117 | hint | Swipe for the next roof. | accept (phone only) |
| 124–126 | eyebrow, h2, lead | How it works / We measure your roof before we price it. / Most installers quote from a satellite photo. We put a test panel and meters on your roof, read the sun and the shade, and size the panels to what your roof really makes. The proposal is exact to your roof; where it differs from the estimate, it shows you why. | accept (departure from my "A minute to a number…": the copywriter is right that "a day or two to switch-on" promised the whole timeline) |
| 129 | step 1 | Free estimate: Four questions here, one minute: what your bill becomes, the price and how many panels it takes. | accept |
| 130 | step 2 | One free visit: We come to the house once: a test panel and meters on the roof to read the sun and the shade, and your bill and appliances at the table to see what the house really uses. | accept |
| 131 | step 3 | Your roof check: The same evening you get a card with what your roof can hold and what it can make. | accept (baseline's "Same day") |
| 132 | step 4 | Your proposal: Within two working days: the design fitted to your house, the price, the savings and the schedule, with the plans signed and sealed. You decide with all of it in front of you. | accept |
| 133 | step 5 | Installation and net metering: We file the papers with your electric company as soon as you sign, install in one or two days, and the two-way meter follows the inspection on the dates in the proposal. | accept |
| 141–142 | eyebrow, h2 | What you get on paper / Every peso and every part on paper before you sign. | accept |
| 145 | paper | Your roof check: The readings we took on your roof, what it can hold and what it can make, month by month. | accept |
| 146 | paper | Your design: Panels, inverter and battery sized to your bill and to the hours you use power: a design for your house, on paper. | accept |
| 147 | paper | The parts list: Every panel, rail, cable, breaker and box, with quantities, so you know exactly what is going on your roof before you sign. | accept |
| 148 | paper | The schedule: Permit, delivery, installation day by day, switch-on and the two-way meter, with dates. | accept |
| 149 | paper | The savings, and what is due when: Your bill before and after, when it pays for itself, and the payment steps of the job, each with its date. | accept ("payment plan" gone) |
| 150 | paper | The plans for the permit: Electrical plans signed and sealed by a Professional Electrical Engineer [(name)], filed with the permit and the net metering application. All in the price, all filed by us. | accept, hooks intact |
| 152–155 | warranty line | Warranties in writing / [list] / Printed on every proposal. | accept, hidden until the profile loads |
| 161–166 | brands placeholder | (stripped) | accept |
| 172–173 | eyebrow, h2 | Your questions / Answered before you ask. | accept |
| 177–178 | FAQ | What happens in a brownout? / With a battery, it takes over by itself: lights, fans, the fridge, TV and Wi-Fi run through a typical evening while the rest of the street waits for the grid. Aircon draws the most, so the hours come down with it on; the estimate says whether yours holds a typical night, and the visit makes it exact. Without a battery, the panels pause during a brownout, as the safety rules require, and restart on their own when the grid returns; a battery can be added later. | accept |
| 181–182 | FAQ | How does net metering work? / The daytime power the house leaves over goes to the grid, … | **change to**: `Daytime power the house leaves unused goes to the grid, and your electric company credits it on your bill at its generation rate, the part of your tariff it pays for power. Power you use yourself is worth more than power you send, so we size the panels to what you use rather than to the roof. A smaller bill still comes, and the estimate shows about what yours would be.` Reason: "leaves over" is not a phrase a Laguna reader parses; the rest is unchanged. S. |
| 185–186 | FAQ | Who handles the permits and the papers? / We do. The electrical plans, the permit and the final inspection, the ERC certificate of compliance and the net metering application with your electric company are in the price. You sign two forms. | accept |
| 189–190 | FAQ | What if we move house? / The system stays with the house. Net metering is tied to the service connection, so the new owner continues it with the electric company; we help with the paperwork. | accept |
| 193–194 | FAQ | What does the installation do to the roof? / The rails clamp through the roof sheet to the framing with sealed fasteners, and our own workmanship warranty covers those points against leaks. Installation takes one or two days. | accept (see the note on the workmanship warranty below) |
| 197–198 | FAQ | What about typhoons? / Our oldest installation, from 2023, has stood through every typhoon season since. The rails are fixed through the sheet to the roof framing with sealed fasteners, on plans a Professional Electrical Engineer signs and seals. | accept |
| 200–202 | FAQ | Who do we talk to after the installation? / Us, the same people who installed it. [after_sales] Workmanship is covered by our own warranty, printed on the proposal. | accept, hidden while `after_sales` is blank |
| 205–206 | FAQ | How exact is the estimate? / An estimate, not a quotation: it comes from your answers and a typical roof, through the same calculation that prices the proposal. … | **change to**: `It is an estimate, not a quotation: it comes from your answers and a typical roof, through the same calculation that prices the proposal. The free roof visit measures your roof and the sun on it, and the proposal that follows is exact.` Reason: the only fragment left on the page opens the last answer before the band, and fragments were the owner's complaint. S. |
| 214–216 | band | Your number is a minute away. / Your bill, your town, when you use power. That is all it takes, and the only call you get is the one you book. / Get my free estimate | accept (departure: the call line moved here from the lead) |

## Brownouts (`site/pages/brownouts.html`)

| Line | Element | Text | Verdict |
|---|---|---|---|
| 1–2 | title, description | Lights on in a brownout · Solar with a battery · PL Development Inc. / The street goes dark and your windows stay lit. Solar with a battery for homes anywhere in the Philippines: lights, fans, fridge, TV and Wi-Fi through a brownout, and the panels still bring the bill down. Free one-minute estimate. | accept |
| 16–18 | eyebrow, h1, lead | Solar with a battery / Lights on, fans running, when the whole street is dark. / The street goes dark and your windows stay lit. The battery takes over by itself and carries what you want to keep on; by day the panels run the house, refill the battery and bring the bill down. | accept |
| 37 | caption | The owner's own home in Pila, Laguna: a 30 kWh battery, and the house runs through brownouts. | accept |
| 41–43 | eyebrow, h2, p | In a brownout / What you keep on when the street goes dark. / The battery takes over by itself. The fan keeps turning at 2 a.m., the fridge stays cold, the children finish their homework with the lights on, and the Wi-Fi stays up for whoever is working from home. We size the battery to the evening you want to keep: lights, fans, fridge, TV and Wi-Fi through a typical night, and the aircon too when you size for it. The estimate tells you whether yours holds a typical night or how many hours of your evening it carries, and the visit makes it exact. | accept |
| 55 | caption | The owner's wife's family house in Fairview, Quezon City: solar by day, and the inverter is ready for a battery whenever one is wanted. | accept |
| 59–61 | eyebrow, h2, p | Every other day / On an ordinary evening, the battery is quietly at work too. / With the grid up, it stores the afternoon's extra solar and spends it after sunset, so more of your evening runs on your own power. What is left over still earns credit on your bill. | accept |
| 71 | eyebrow | Sized to your house | **change to**: `Your house, your evening`. Reason: the eyebrow and the h2 under it both open "Sized to"; on the desktop they stack as a stutter. S, minor. |
| 72–73 | h2, lead | Sized to the evening you want to keep. / Every family keeps a different evening. We size the panels to your bill and the battery to the evening you want to keep: for one house the lights, the fans and the fridge; for another the Wi-Fi and the aircon too. | accept |
| 75–80 | ticks | Panels sized to your bill, so you buy only what the house uses / Battery sized to the evening you want to keep: lights, fans, fridge, TV, Wi-Fi, with or without aircon / Switches over by itself (a hybrid inverter does it) / Extra power still earns credit on your bill, through the two-way meter from your electric company / A lithium battery (the LiFePO4 kind), named by brand on your proposal / [warranty tick, hidden] | accept |
| 85–86 | card | What it costs, and what it buys / The battery is roughly a third to nearly half of the price. It buys you the comfort and the backup; the panels do the saving. The estimate shows both prices, with and without the battery, so you decide. | accept |
| 98–99 | band | See your two prices, with and without the battery. / Four questions, one minute, free. Then a free roof visit for the exact figure. | accept |

## Net metering (`site/pages/net-metering.html`)

| Line | Element | Text | Verdict |
|---|---|---|---|
| 1–2 | title, description | The bill you stop dreading · Solar with net metering · PL Development Inc. / The bill you stop dreading. Solar with net metering for homes anywhere in the Philippines: the panels run the house by day and what you do not use comes back as credit on your bill. Free one-minute estimate. | accept |
| 16–18 | eyebrow, h1, lead | Solar with net metering / The bill you stop dreading. / In our example below, about two thirds of the bill goes away. By day the panels run the house; the extra comes back as credit on your bill. Panels and inverter only: the lowest price of the three ways to go. | accept |
| 29–30 | eyebrow, h2 | How it works / Your meter runs both ways. | accept |
| 33–36 | steps | By day … / At night … / On the bill: Your electric company credits every kWh you sent at its generation rate, the part of your tariff it pays for power. The fixed charges and the evening hours stay, so a small bill still comes, and the estimate shows about what yours would be. / The papers: We file the net metering application, the ERC certificate of compliance (the net metering certificate) and the meter request. You sign two forms. Between switch-on and the two-way meter the panels already cut your daytime bill. | accept |
| 45–48 | eyebrow, h2, lead, small | The numbers / What the numbers look like. / A house using about 500 kWh a month in Tanauan, Batangas comes out at: / From our own estimate at today's prices (500 kWh a month, mostly in the evening, net metering without a battery). For that house the panels pay for themselves in under four years. Every house is different: your estimate uses your bill, your town's sun records and our current prices, and counts your savings over 25 years. | accept (pinned string intact) |
| 52–56 | tiles | 4.1 kWp / 7 panels; about ₱193,000 / installed, VAT included; under 4 years / pays for itself; about two thirds / off the bill; [25 years tile, hidden until the profile loads] | accept (test passes) |
| 74 | caption | The owner's own home in Pila, Laguna: net metered since 2023, with a 30 kWh battery for the brownouts. | accept |
| 78–81 | eyebrow, h2, lead, link | Brownouts / Want lights in a brownout too? / Add a battery and the house runs through brownouts. Without one, the panels pause while the grid is down, as the safety rules require, and restart on their own when it returns. The estimate shows both prices, and a battery can be added later. / Read about solar with a battery | accept |
| 91–92 | band | Your bill, your town, one minute. / Free, and it asks only for your bill and your town. Like the number? Book the free roof visit on the same page. | accept |

## About (`site/pages/about.html`)

| Line | Element | Text | Verdict |
|---|---|---|---|
| 1–2 | title, description | About us · PL Development Inc. / PL Development Inc. designs and installs rooftop solar for homes anywhere in the Philippines from Pila, Laguna. We go to the house and measure the roof before we design, size the panels to your bill, and hand you the plans, the parts list and the schedule, signed and sealed by a Professional Electrical Engineer. | accept |
| 16–18 | eyebrow, h1, lead | About us / Our oldest roof is our own. / Our own home has run on what we sell since 2023. [PL Development Inc.] designs and installs rooftop solar for homes from [Pila, Laguna], across [the Philippines]. | accept (the coordinator's "oldest", the right word) |
| 37 | caption | The owner's own home in Pila, Laguna: three roofs and a 30 kWh battery, net metered since 2023, with more than ₱33,000 of credit on the bill. | accept |
| 41–42 | eyebrow, h2 | Why we measure / We started with a simple complaint. | accept |
| 43 | p | Solar quotes that came from a satellite photo and a price list, and systems that never made what the brochure promised. So we measure first. … | **change to** (first sentence only): `Solar quotes came from a satellite photo and a price list, and the systems never made what the brochure promised. So we measure first. We go to the house, put a test panel and meters on the roof, read the sun and the shade, and size the panels and the battery to what that roof really makes and what that house really uses. The proposal that follows is exact to your roof; where it differs from the first estimate, it shows you why.` Reason: the opening is a fragment, the owner's complaint. S. |
| 60 | caption | The owner's parents' house in Pila, Laguna: eight panels fixed through the roof sheet to the framing, installed early 2026. | accept |
| 70–71 | eyebrow, h2 | Who you will meet / The owner on every visit, an engineer on every plan. | accept, with one ask: the sentence that backs "on every visit" (line 72) is hidden until `owner_name` is filled in Settings, so the heading now says on its own what the hidden line said; the owner should confirm it in one word. |
| 72–73 | profile lines | [owner_name] runs the company and is on every roof visit and every proposal. / [after_sales] | accept, hidden while blank |
| 74 | p | The roof is yours, and we leave it the way we found it: our crew of a team lead, skilled technicians and helpers installs in one or two days, every fastener sealed and covered against leaks by our own workmanship warranty. Electrical plans are signed and sealed by a Professional Electrical Engineer[, name (PRC No. …)]. | accept |
| 84–85 | eyebrow, h2 | How we work / Installers sell you panels. We hand you the engineering. | accept (departure: demoted from the home page; "then install it ourselves" lives on in tick 3) |
| 87–90 | ticks | One calculation from estimate to proposal. … / Straight about the battery. The battery buys comfort and backup through brownouts; the panels bring the bill down. We show both prices and you choose. / Everything in the price, installed by our own crew. … / [Warranties in writing, hidden] | accept ("calculation" for "engine" is the better word) |
| 95–97 | card | Where we install / Anywhere in [the Philippines]. / We are based in [Pila, Laguna], our own roofs are in Laguna and Quezon City, and we travel to wherever yours is. | accept |
| 109–110 | band | Your number is a minute away. / Your bill, your town, when you use power. That is all it takes, and the only call you get is the one you book. | accept |

## Estimate, 404, frame

| File, line | Text | Verdict |
|---|---|---|
| estimate.html 1–2 | Free solar estimate for your home · PL Development Inc. / Four questions, one minute, no sign-up. A straight estimate of what solar would cost and save at your house, from PL Development Inc., Pila, Laguna. | accept |
| estimate.html 8–9 | Loading the estimate… / The estimate needs JavaScript. Please enable it, or message us on Messenger with your latest bill and your town and we will work it out for you. | accept (baseline; "Messenger" assumes the link is set in Settings) |
| 404.html 7–9 | That page has moved on. / Your estimate is right here, one minute, free. / Get my free estimate · Home | accept |
| layout.html 31 | Solar engineering for homes | accept (pinned) |
| layout.html 53–54 | [Pila, Laguna] Installs in [the Philippines]. / Electrical plans signed and sealed by [pee_name], Professional Electrical Engineer, PRC No. […]. | accept, hidden while blank |
| layout.html 56–65 | Talk to us: [owner_name] / [phone] / Messenger / Facebook / [email] | accept as code; the Critical data item from the audit stands: until Settings has a phone or Messenger link, no page has a human to call |
| layout.html 67–69 | Start here / Get my free estimate / Four questions, one minute, no sign-up. You get an estimate to decide with; the free roof visit turns it into an exact proposal. | accept |
| layout.html 79–80 | Free estimate / One minute. / Get my free estimate | accept |

---

## Notes that are not line changes

1. **The workmanship warranty outside the hooks.** index.html:194 ("our own workmanship warranty covers those points
   against leaks"), index.html:202 ("Workmanship is covered by our own warranty, printed on the proposal") and
   about.html:74 ("covered against leaks by our own workmanship warranty") assert the warranty unconditionally, while
   the years stay in the profile (default 2, "including leak-free roof penetrations"). The baseline already said
   "Workmanship is covered by our own warranty" in the same two FAQ answers, so nothing new is claimed and no year is
   typed. If the owner ever blanks the workmanship years in Settings these three sentences would need the
   `data-profile-hide-if-empty="warranty_workmanship_years"` wrap; optional, M, not for this round.
2. **The band's muted line** (my audit's section 2: "Warranties in writing on every proposal." + the after-sales
   hook under the home band) was not taken. The after-sales line is in the FAQ and on About; acceptable.
3. **The full-page screenshots** show the fixed header printed mid-page and blank reveal sections until scrolled;
   both are screenshot artefacts, not layout faults (`s-*.png` are the scrolled-through versions).
4. **Ask the owner** (unchanged from the audit, section 6, in priority): Settings phone, Messenger, owner's name;
   PEE name and PRC number; confirm "on every visit" (about.html:71); the 25-year performance warranty on the
   datasheet; the inverter's switch-over time; the brand logo files; the three photos for the placeholders.

---

## Verdict on the whole

Yes. A homeowner in Laguna or Quezon City coming from a Facebook link now sees, in this order, a roof, a promise in
his own words ("The bill goes down. With a battery, the lights stay on."), a free button, four specific proofs
(₱33,000+, 2023, 3 family homes, 1 free visit), the three wants in his own voice, three named family roofs with their
kWp on the photo, a five-step path, the six things on paper, seven answers and the button again, with the button
pinned to the phone's thumb the whole way. The honesty is inside the sentences and nothing on the pages is a claim
the owner cannot back. It reads as a company that lives on what it sells and measures before it prices, which is the
whole pitch.

The single change that would raise it most is not a sentence: it is the human. On every page the "Talk to us"
block, the owner's name on About and the engineer's name on the plans card are blank until Settings carries a phone
or Messenger link, the owner's name and the PEE's name and PRC number. A Quezon City buyer comparing two quotes checks
whether he can message a person before he reads the price; today the only path is the estimate form. Fill those
five fields (minutes) and every page gains a person without a word changing. On the words side, the runner-up is
the owner's own photo in the About placeholder.

---

## Ten lines for the coordinator

1. **Must change, index.html:65** "the first has run since 2023" → `the oldest has run since 2023` ("first" claims the company's first job; About already says "oldest").
2. **Must change, index.html:182** "The daytime power the house leaves over goes to the grid," → `Daytime power the house leaves unused goes to the grid,` (rest of the answer unchanged).
3. **Must change, index.html:206** "An estimate, not a quotation: it comes from…" → `It is an estimate, not a quotation: it comes from your answers and a typical roof, through the same calculation that prices the proposal. The free roof visit measures your roof and the sun on it, and the proposal that follows is exact.` (the last fragment on the page).
4. **Must change, about.html:43** first sentence → `Solar quotes came from a satellite photo and a price list, and the systems never made what the brochure promised. So we measure first.` (fragment → sentence; the rest unchanged).
5. **Minor, brownouts.html:71** eyebrow "Sized to your house" → `Your house, your evening` (eyebrow and h2 both open "Sized to").
6. **Accepted departures:** h1 "goes down"; the two-sentence lead with "free" on the button; the call line in the band; the eyebrow "Home solar in the Philippines" kept on the phone (one line, button at 685–741 px of 844); How-it-works h2 "We measure your roof before we price it." with the Why-us lead; "Installers sell you panels. We hand you the engineering." to About; "calculation" for "engine"; inverter sizes, rails and conduit off the home cards; "the owner's" three times and "Our oldest roof is our own."; the four ticks under the hero button on the phone; no small line under the hero button; the band without the warranty/after-sales line.
7. **Nothing must go.** No claim beyond the brief's facts anywhere; no guarantee, financing word, utility name, brand, customer voice, exclamation mark or "assessment"; the honesty lines survive inside the sentences on every page they belong to.
8. **Hooks and pins:** `tests/test_site.py` 9 passed (built to pytest's temp folder; `site/dist` untouched); all `is-empty` fragments hidden on the static server; placeholders stripped; reduced motion stops the count-up, the reveal and the breathing photo; JS off hides nothing.
9. **Verdict:** yes, this is a marketing website a Laguna or Quezon City homeowner would trust and act on: roof, promise, button on the first screen; proof by ownership, specific and true; the kind as the small label; the button on every screen.
10. **The one change that would raise it most:** fill Settings (phone, Messenger, owner's name, PEE name and PRC No.) so the footer's "Talk to us", the About owner line and the engineer's name appear; until then no page has a person to message, and that is what the comparing buyer looks for before the price. Three open asks for the owner follow it: confirm "on every visit" (about.html:71), the datasheet's 25 years, and the three photos.
