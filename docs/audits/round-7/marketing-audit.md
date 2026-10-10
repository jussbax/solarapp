# Round 7, marketing: the anti-sales audit

From the marketing and sales specialist. 10 October 2026. Read-only: nothing in the repository was changed, `site/dist`
was not rebuilt. Read as the customer reads it: the site built into my scratch folder and served at
http://127.0.0.1:8201 (phone 390 px and desktop 1280 px, Playwright screenshots `phone-*.png`, `desktop-*.png` in this
folder), and the estimate widget live on a scratch copy of the backend at http://127.0.0.1:8211/estimate with the real
sun records (five estimates, one booking, the thank-you, the copied summary; `widget-*.png`, scripts `walk.js`,
`walk2.js`). Line numbers are the source files' (`site/pages/*.html`, `site/layout.html`,
`frontend/src/estimate/Estimate.tsx`, `backend/solarapp/profile.py`, `backend/solarapp/core/quick.py`); every item
also quotes the string, so cite by string if lines move. Both servers were stopped at the end.

The owner's test, applied to every line: would this sentence make the buyer go with someone else? The round-6
honesty lines are kept in substance (an estimate is not a quotation; the battery is for comfort, the panels for the
bill; nothing guaranteed; the safety rule in a brownout) and said the way a confident seller says them: as what the
customer gets, inside the sentence, never as a warning after a promise.

Severity: Critical (a buyer leaves or the law is touched) / Major (a buyer hesitates, or the sale's strongest card is
not played) / Minor (register). Effort S (minutes, text only) / M (an hour, structure) / L (half a day).

---

## 1. The lines that make a buyer walk away, ranked by lost sales

### 1. Estimate.tsx:18, the first option on the first question: "No battery, so no power during a brownout."
What is wrong: the first thing every visitor reads on the estimate is what the cheapest option takes away. The home
card (index.html:37) already lost this clause ("A battery can be added later if you want lights in a brownout too"),
so a visitor who clicks through meets the loss sentence one screen later. The moment of choosing is where the sale
starts; a loss word there colours all three options.
Why it costs a sale: the no-battery buyer (the ad-angle-2 audience, the strongest numbers) is told "no power" before
seeing a price; the battery buyer reads that the cheaper option is a trap, and distrusts the comparison.
Replace with: `Solar runs the house by day. Extra power goes to your electric company as credit on your bill (net metering). A battery can be added later for brownouts.`
Severity Major. Effort S.

### 2. index.html:76, "The savings and payment plan"
What is wrong: in Filipino retail "payment plan" means instalments. The card is the milestone schedule ("what is due
when"), and financing is on the must-not list (no instalments, no "from ₱X a month"); this is the one place on the
site that says the forbidden thing by accident.
Why it costs a sale: a buyer who books expecting instalments walks away at the proposal, after the free visit has
been spent on them; a buyer who knows there is no financing reads the card as a bluff.
Replace with: h3 `The savings, and what is due when` and p `Your bill before and after, when it pays for itself, and the payment steps of the job, each with its date.`
Severity Major. Effort S.

### 3. index.html:9–10, the hero: an instruction and a 70-word lead ending in a disclaimer
Now: h1 "See what solar would do to your bill." and the lead "Type in your bill and your town, and a minute later you
know what solar would cost at your house and what your bill would become. Free, no sign-up, and nobody calls unless
you ask. If you like the number, we come to the house, put a test panel on the roof and measure, so the proposal is
exact. No cost, no obligation."
What is wrong: the h1 tells the visitor to do something; it promises nothing. The lead is four sentences and 70 words
(on a 390 px phone it fills eight lines and pushes the button under the fold; the roof photo lands at 908 px, on the
second screen: `phone-index-first.png`). "If you like the number" hedges; "nobody calls unless you ask" and "No cost,
no obligation" are two "no" constructions in a row at the end, the brochure's apology.
Why it costs a sale: the Facebook visitor decides on the first screen, and the first screen has no roof, no promise
and a button under text.
Replace with: h1 `The bill comes down. With a battery, the lights stay on.` Lead: `Panels sized to your bill bring it down every month; add a battery and the house runs through brownouts. One minute here gives you the price and what your bill becomes, free, no sign-up; then we put a test panel on your own roof and measure, so the proposal is exact. The only call you get is the one you book.` For the phone the UX may cut the lead to its first sentence; the second lives in the proof strip and step 2.
Alternative h1 if the coordinator wants the relief line alone: `A bill you stop dreading, from a roof we measured ourselves.`
Severity Major. Effort S (text); M with the UX's first-screen rebuild (section 4).

### 4. Estimate.tsx:587, the biggest number on the page is hidden under "How we worked this out"
Now: the result hero shows the bill before and after, the payback and the price; "Saved over 25 years: about
₱941,000, after paying for the system, upkeep and replacement parts" (the ₱4,000 Pila house, with the battery) is
inside a closed `<details>`.
What is wrong: the visitor sees "₱304,000" and "8.7 years" and never the sum those years are worth. It is the engine's
own modelled figure, already carries "about" and "after paying for the system", and the round-6 brief allowed the
pages to echo it.
Why it costs a sale: a ₱304,000 price with no lifetime figure beside it reads as a cost; beside "about ₱941,000 saved
over 25 years" it reads as a purchase.
Replace with: a third cell in `.pld-hero-grid` after "Estimated price": label `Saved over 25 years`, figure
`about {phpAbout(e.lifetime_net)}`, sub `after paying for the system, its upkeep and replacement parts`. Keep the
sentence in the details too. Add the same figure to the copied summary (line 269):
`Bill ₱4,002 → about ₱166 a month; about ₱46,000 saved in the first year; pays for itself in 8.7 years.` and a line
`Saved over 25 years: about ₱941,000, after paying for the system and its upkeep.`
Severity Major. Effort S for the text, M for the grid (three cells wrap at 420 px; `estimate.css:55`).

### 5. about.html:10, "So we do it the slow way." and the honesty line as a warning (also index.html:89)
Now: "...systems that never made what the brochure promised. So we do it the slow way. We go to the house... The
proposal that follows is exact. It can come out lower or higher than the first estimate, and it shows you why."
What is wrong: "slow" is the one word no buyer wants from a contractor, and it is the company's own description of
itself. "It can come out lower or higher" is the honesty fact (the price moves after measurement) bolted on after
"exact", so the reader hears "exact, except not".
Why it costs a sale: the comparing buyer's second visit is About; "slow" and "higher" are the two words he carries
back to the other quote.
Replace with (about.html:10): `...systems that never made what the brochure promised. So we measure first. We go to the house, put a test panel and meters on the roof, read the sun and the shade, and size the panels and the battery to what that roof really makes and what that house really uses. The proposal that follows is exact to your roof; where it differs from the first estimate, it shows you why.`
And index.html:89: `Most installers quote from a satellite photo. We put a test panel and meters on your roof, read the sun and the shade, and size the panels to what your roof really makes. The proposal is exact to your roof; where it differs from the estimate, it shows you why.` ("the system" → "the panels": the engineer's word out of the lead.)
Severity Major. Effort S.

### 6. index.html:146, the strongest proof on the site is the last card's muted small print
Now, card 3 of "Our installations": "Where the owner's family lives: 13.75 kWp across three roofs with a 30 kWh
battery, so the house runs through every brownout, and net metering has built up more than ₱33,000 of credit on the
bill since 2023." in `muted small`, third of three, 7,000 px down the phone.
What is wrong: this is the only before-and-after the company can honestly show (three years, ₱33,000 of credit, a
house that runs through brownouts) and it is set as a caption. "every brownout" also goes one word past the fact in
force ("the house runs through brownouts").
Why it costs a sale: the visitor who asked "does it work?" never reaches it; the one who does reads it as a footnote.
Replace with: make this the first card, headed `The owner's own home in Pila, Laguna`, caption in body size (not
`muted small`): `Where the owner's family lives. Three roofs, 13.75 kWp and a 30 kWh battery: the house runs through brownouts, and net metering has built up more than ₱33,000 of credit on the bill since 2023.` and lift the two figures to the proof strip (section 2).
Severity Major. Effort S (order and text); M with the UX's testimony cards.

### 7. index.html:195–197, the last FAQ answer is the word "No."
Now: "Is the estimate a quotation?" / "No. It is an estimate from your answers and typical-roof assumptions. The free
roof visit measures your roof and the sun on it, and the proposal that follows is exact."
What is wrong: the question is written to be answered "No", and it is the last thing before the call to action.
Why it costs a sale: the reader's last impression before the band is a refusal; the band then asks for a minute.
Replace with: summary `How exact is the estimate?` and p `It is an estimate, not a quotation: it comes from your answers and a typical roof, from the same engine that prices the proposal. The free roof visit measures your roof and the sun on it, and the proposal that follows is exact.` ("the same engine" is About's own fact, line 34.)
Severity Major. Effort S.

### 8. The brownout fact said as a loss, three times: index.html:169, brownouts.html:22, net-metering.html:46
Now: "...running aircon shortens that. Without a battery, a net-metered system switches off during a brownout, as the
safety rules require..." (index:169); "...through a typical night; running aircon shortens that." (brownouts:22); "A
net-metered system without a battery switches off during a brownout, as the safety rules require, and restarts on
its own when the grid returns. If brownouts matter to you, read about solar with a battery..." (net-metering:46).
What is wrong: "shortens", "switches off", "without" lead; the law line ("as the safety rules require") must stay,
but it can follow what the customer gets.
Why it costs a sale: the battery buyer reads that aircon breaks the promise; the no-battery buyer reads "switches
off" as the headline of the section meant to upsell him.
Replace with:
- index.html:169: `With a battery, it takes over by itself: lights, fans, the fridge, TV and Wi-Fi run through a typical evening while the rest of the street waits for the grid. Aircon draws the most, so the hours come down with it on; the estimate says whether yours holds a typical night, and the energy audit at the table makes it exact. Without a battery, the panels pause during a brownout, as the safety rules require, and restart on their own when the grid returns; a battery can be added later.`
- brownouts.html:22: `...We size the battery to the evening you want to keep: lights, fans, fridge, TV and Wi-Fi through a typical night, and the aircon too when you size for it. The estimate tells you whether yours holds a typical night or how many hours of your evening it carries; the energy audit at the table makes it exact.` (the tick on line 42 already says "with or without aircon"; the audit sentence is the engine's own assumption line.)
- net-metering.html:46: `Add a battery and the house runs through brownouts. Without one, the panels pause while the grid is down, as the safety rules require, and restart on their own when it returns. The estimate shows both prices, and a battery can be added later.`
Severity Major. Effort S.

### 9. Net metering explained as a shortfall: net-metering.html:22, index.html:173, Estimate.tsx:42 and :462
Now: "...at its generation rate (the rate it pays for power, lower than the rate you pay). That is why the bill
shrinks but does not reach zero." (net-metering:22); "...lower than the rate you pay per kWh). That is why a bill does
not reach zero..." (index:173); "...the surplus is credited by your electric company at its generation rate, which is
why the bill does not reach zero." (Estimate.tsx:462); "Used straight from the panels: 30% of your usage; the rest of
the day's solar goes to the grid and is credited on your bill." (Estimate.tsx:42).
What is wrong: three "lower than", "does not reach zero" constructions for one fact (the credit is at the generation
rate; a small bill stays). "surplus" and "usage" are the engineer's words in the customer's result.
Why it costs a sale: the net-metering buyer is told three times what he will still pay and never what he keeps.
Replace with:
- net-metering.html:22: `<b>On the bill</b> Your electric company credits every kWh you sent at its generation rate, the part of your tariff it pays for power. The fixed charges and the evening hours stay, so a small bill still comes, and the estimate shows about what yours would be.`
- index.html:173: `Power you do not use by day goes to the grid, and your electric company credits it on your bill at its generation rate, the part of your tariff it pays for power. Power you use yourself is worth more than power you send, so we size the panels to what you use rather than to the roof. A smaller bill still comes, and the estimate shows about what yours would be.`
- Estimate.tsx:462: `" Daytime power runs the house first; the extra goes to your electric company and comes back as credit at its generation rate, so a small bill stays for the fixed charges and the grid's hours."`
- Estimate.tsx:42–44: `Used straight from the panels: ${pct}% of what you use; the rest of the day's solar goes to the grid and comes back as credit on your bill.` / `Covered by the panels and the battery: ${pct}% of what you use.` / `Covered by solar, by day and from the battery: ${pct}% of what you use.`
Severity Major. Effort S.

### 10. The battery talked down at the moment of the add-on: Estimate.tsx:473, about.html:35, brownouts.html:30
Now: "The battery is for brownouts; it adds little to the savings." (the widget, beside the ₱133,000 add-on);
"Honest about the battery. A battery is for brownouts and comfort; it adds little to the savings." (About); "It buys
comfort and backup more than savings" (Brownouts).
What is wrong: the owner's rule (battery = comfort, the panels = the bill) is right and stays; "adds little" and
"more than savings" say it as a shortfall of the product the page is selling.
Why it costs a sale: the ₱133,000 add-on is introduced with "little"; a buyer who wanted the comfort now feels he must
justify it.
Replace with: Estimate.tsx:473 `The battery buys the brownout comfort; the panels do the saving.`; about.html:35
`<b>Straight about the battery.</b> The battery buys comfort and backup through brownouts; the panels bring the bill down. We show both prices and you choose.`; brownouts.html:30 `The battery is roughly a third to nearly half of the price. It buys you the comfort and the backup; the panels do the saving. The estimate shows both prices, with and without the battery, so you decide.` (the h3 may become `What it costs, and what it buys`).
Severity Major. Effort S.

### 11. "Nobody calls", "No cost, no obligation": Estimate.tsx:315 and :514 (index.html:10 is item 3)
Now: "Nobody calls unless you book the free roof visit, which gives the exact figure." (315); "...and quote exactly.
No cost, no obligation." (514).
Replace with: 315 `Four questions, about a minute: your bill before and after, the price, and how many panels it takes. The only call you get is the free roof visit you book, and that one makes the figure exact.`; 514 `Most installers quote from a satellite photo. We put a test panel and meters on your roof, measure the sun and the shade, and quote exactly. The visit is free, and you decide after.`
Severity Minor. Effort S.

### 12. Estimate.tsx:491 and :495, the thank-you sits under a heading that is still asking
Now: after a booking the card still reads "Want the exact figure? We come and measure. The visit is free." above
"Thank you, Maria. We will message or call you within one working day... Nothing more to do for now; keep a recent
bill where you can find it." (`widget-thanks.png`).
What is wrong: the heading (line 491) is outside the `leadSent` branch, so the booked visitor is asked again to want
what she just booked; "Nothing more to do" is the one "nothing" on the page.
Replace with: `<h3 className="pld-h3">{leadSent ? `Your roof visit is booked, ${firstName(lead.name)}.` : 'Want the exact figure? We come and measure. The visit is free.'}</h3>` and in 495 `...visits are usually within the week. That is all for now: keep a recent bill where you can find it.` (with the owner's name blank the line reads "We will message or call you"; the owner's name in Settings makes it a person: ask.)
Severity Minor. Effort S.

### 13. net-metering.html:54, "asks for nothing but... Booking the roof visit is optional."
What is wrong: "optional" undersells the visit, which is the product (the measured roof); "nothing but" is a "no".
Replace with: `Free, and it asks only for your bill and your town. Like the number? Book the free roof visit on the same page.`
Severity Minor. Effort S.

### 14. index.html:135–136, the hip roof opens with "No single big face" and belongs to nobody
Now: h3 "The family's house in Fairview, Quezon City"; caption "No single big face to this hip roof, and it still
carries a full system..."
What is wrong: whose family? The owner said it is his wife's family house, inherited from her mother; "The family's"
is the vagueness that made him suspect "grabbed photos". The caption's first word is "No".
Replace with: h3 `The owner's wife's family house in Fairview, Quezon City`; caption `A hip roof with small faces, and it still carries a full system: sixteen panels, 9.12 kWp, in three groups on three faces, each on its own rails, the cables in conduit. The 12 kW hybrid inverter takes a battery whenever one is wanted. Installed early 2026.`
Severity Minor. Effort S.

### 15. index.html:47 and Estimate.tsx:20, "For homes that cannot or do not want to apply for net metering."
What is wrong: the third option is framed as the fallback for the unable; "cannot or do not want" is two negatives.
Replace with (both places, in step): `For homes that would rather keep their own power than sell it, and for places where net metering is out of reach.`
Severity Minor. Effort S.

### 16. "Not a package", "not to the roof": index.html:73, brownouts.html:38, brownouts.html:41
Replace with: index.html:73 `Panels, inverter and battery sized to your bill and to the hours you use power: a design for your house, on paper.`; brownouts.html:38 h2 `Sized to the evening you want to keep.`; brownouts.html:41 `Panels sized to your bill, so you buy only what the house uses`.
Severity Minor. Effort S.

### 17. layout.html:69, the footer's "An estimate, not a quotation" bolted on
Now: "Four questions, one minute, no sign-up. An estimate, not a quotation; the free roof visit gives the exact figure."
Replace with: `Four questions, one minute, no sign-up. You get an estimate to decide with; the free roof visit turns it into an exact proposal.` (The law line "This is an estimate, not a quotation" stays word for word where the number is: Estimate.tsx:270 and :595.)
Severity Minor. Effort S.

### 18. net-metering.html:9 and :31, "No battery, so..." and "you want a real number before you type anything in"
Replace with: in line 9, `Panels and inverter only, so this is the lowest price of the three ways to go, and a battery can be added later.` for the sentence "No battery, so this is the lowest price of the three ways to go."; line 31 whole: `A house using about 500 kWh a month in Tanauan, Batangas comes out at:` (the small print on line 39 and the pinned tiles stay; "Every house is different..." moves into the small print's second sentence, which already says it).
Severity Minor. Effort S.

### 19. "no open holes" and the typhoon answer's order: index.html:185, :189, about.html:23
Replace with: index.html:185 `The rails clamp to the roof framing through the sheet with sealed fasteners, and our workmanship warranty covers those roof penetrations against leaks. Installation takes one or two days.` (the profile's own warranty wording, "including leak-free roof penetrations"); index.html:189 `Our oldest installation, from 2023, has stood through every typhoon season since. The rails are fixed through the sheet to the roof framing with sealed fasteners, on plans a Professional Electrical Engineer signs and seals.`; about.html:23 `The roof is yours, and we leave it the way we found it: our crew of a team lead, skilled technicians and helpers installs in one or two days, every fastener sealed and the roof penetrations covered by our workmanship warranty.`
Severity Minor. Effort S.

### 20. profile.py:40, the after-sales default "you are not on your own"; index.html:192–193
Now: "After switch-on you are not on your own: call or message us and we answer as soon as humanly possible."
What is wrong: the owner asked for "we provide after sales support" and "respond in the earliest humanly possible";
the default says it as a "not". The FAQ question "Who do we talk to after the installation?" is answered by the line
without a "who".
Replace with: profile default `We provide after-sales support: call or message us any time after switch-on and we answer as soon as humanly possible.` (`backend/tests/test_api.py:678` pins the old opening and changes with it; a deployment that saved Settings keeps its own value until the owner retypes it.) index.html:193: `<p>Us, the same people who installed it. <span data-profile="after_sales"></span> Workmanship is covered by our own warranty, printed on the proposal.</p>`
Severity Minor. Effort S.

### 21. "the whole Philippines" in caps across the first screen: index.html:8, profile.py:26
Now: the eyebrow "Solar engineering for homes in the whole Philippines" is two lines of gold capitals above the h1 on
a phone; the footer says "Installs in the whole Philippines."; About "Anywhere in the whole Philippines."
Replace with: the profile default (and the owner's saved value, Settings › Where you install) `the Philippines`, so the
eyebrow reads "Solar engineering for homes in the Philippines", the footer "Installs in the Philippines.", About
"across the Philippines" and "Anywhere in the Philippines." On the phone's first screen the eyebrow goes (section 4).
Severity Minor. Effort S.

### 22. The result's caveats, said as what stays: Estimate.tsx:431–432, quick.py:222
Now: "about ₱3,837 less each month, before any fixed charges on your bill"; small-bill case "...your electric
company's fixed charges remain, and the grid still bills the hours it steps in during long rainy spells"; the cap
warning "Your usage needs more than 40 panels. We capped the estimate at 40. On the roof visit we'll see how many your
roof can really take."
Replace with: 432 `about ${php0(e.savings_monthly)} less each month; your electric company's fixed charges stay on the bill`; 431 `about ${php0(e.savings_monthly)} less each month; what stays is your electric company's fixed charges and the grid's hours in long rainy spells`; quick.py:222 `Your house needs more than {q.max_panels} panels; we capped the estimate there, and on the roof visit we see how many your roof really takes.`
Severity Minor. Effort S.

### 23. Estimate.tsx:554–560, the booking card's trust list has no warranty and no human
Now (embedded, as the website shows it): "PL Development Inc., Pila, Laguna" and "Installs in the whole Philippines";
the PEE line only when the profile names the engineer; the warranty lines only in the standalone footer (621–627).
Replace with: append `...status.warranty` to the `trust` list for the embedded card, so the 25-year line prints at the
moment of booking; and when `profile.owner_name` and `profile.phone` are set, a line `${owner_name}, ${phone}`. (Until
the owner fills phone, Messenger, owner's name, PEE name and PRC number in Settings, these lines are blank on the
live site and the footer's whole "Talk to us" block (layout.html:56–65) is hidden: no page has a human to call. Ask.)
Severity Minor as code; Critical as data if the live profile is blank. Effort S.

### 24. 404.html:7–8
Replace with: h1 `That page has moved on.` lead `Your estimate is right here, one minute, free.`
Severity Minor. Effort S.

Verified clean (no change): the two prices with and without the battery (Estimate.tsx:467–488) and both "Show..."
links; "Book my free roof visit" everywhere; the sticky price bar; the questions 2–4; the copied summary's "This is
an estimate, not a quotation." and "Run your own: .../estimate"; the privacy line; "Pick the one that sounds like
you." and the three feeling cards; the How-it-works steps; "Installers sell you panels. We hand you the engineering,
then install it ourselves."; the papers card (index:93) and the FAQ "We do... You sign two forms."; the moving-house
answer; the net-metering tiles; the whole Brownouts hero; the About photo caption; the privacy page. No utility name,
no financing word but item 2, no "assessment", no exclamation mark, no customer voice, no transfer time, no typhoon
rating, no brand anywhere.

---

## 2. The proof the site is not yet using, and where each line goes

Every fact below is in the round-7 brief; nothing else is claimed. "Two provinces" is not printed: Quezon City is in
Metro Manila, not a province, and a Quezon City reader notices. Say "Laguna and Quezon City".

**The proof strip under the hero (four tiles, read in two seconds; `figures`/`figure` markup as net-metering:32–38):**

| Big | Label |
|---|---|
| `Since 2023` | `our own home on solar, through every typhoon season since` |
| `₱33,000+` | `credit built up on the owner's own bill` |
| `3 family roofs` | `ours, in Laguna and Quezon City` |
| `1 free visit` | `a test panel on your roof before we quote` |

A fifth tile when the profile loads, `25 years` / `the maker's performance warranty on the panels`, with the hooks
exactly as net-metering.html:37 (`class="figure is-empty" data-warranty-wrap data-profile-hide-if-empty="warranty_panels_performance_years"`);
the strip must look complete with four, because on a static server the fifth never shows.

**In the hero itself:** the roof photo (the rib roof stays: the cleanest frame; the three-roof home is the strongest
story but the palms' shade needs a caption), the h1 of item 3, the gold button, and one proof line under the button:
`Our own homes have run on what we sell since 2023.` On desktop the four ticks become four proofs:
`Our own homes on solar since 2023` / `A test panel on your roof before we quote` / `Plans sealed by a Professional Electrical Engineer` / `Permit and net metering papers filed by us`.
("Measured on your roof, not from a satellite photo" is the competitor contrast; it moves to the Why-us card, index:89,
where it already lives.)

**The installations as testimony (index:116–117):** h2 `We live with what we sell.` lead `The owner's home, his parents' house and his wife's family house, photographed by us from the air: three family roofs in Laguna and Quezon City, the oldest running since 2023.` The owner's home first (item 6), then the parents' house (`His parents' house in Pila, Laguna` / `Eight panels, 4.56 kWp, carry the house by day, on rails fixed through the sheet to the roof framing, on a 6 kW grid-tie inverter. Installed early 2026.`), then the wife's family house (item 14).

**The engineer's seal:** hero tick 3, the Why-us card (index:93), the footer (layout:54) and the widget's trust list all
print the name and PRC number from the profile and say only "a Professional Electrical Engineer" while it is blank.
The named seal is worth more than the unnamed one: ask the owner for `pee_name` and `pee_license`.

**The papers filed by us, you sign two forms:** hero tick 4, step 5, the FAQ (index:177). Already in place; keep.

**One free visit:** step 2, the proof strip, the booking card heading. Add the reason once, in the Why-us card (it is
there: "Most installers quote from a satellite photo").

**The 25-year panel performance warranty (profile default 25; the owner must verify it on the panel datasheet):**
the fifth tile, the Warranties card (index:95–99, which prints "Panels: 12-year product warranty and 25-year
performance warranty from the maker." when loaded), and the band (below). Never typed into a page: hooks only.

**The after-sales line:** About (line 22), the FAQ (item 20), and the band.

**The band at the foot (index:203–208):** h2 `Your number is a minute away.` p `Your bill, your town, when you use power. That is all it takes.` button unchanged, then one muted line with the hooks: `<span class="is-empty" data-warranty-wrap>Warranties in writing on every proposal. </span><span data-profile="after_sales"></span>` so it reads "Warranties in writing on every proposal. We provide after-sales support: call or message us any time after switch-on and we answer as soon as humanly possible."

**The credit on the bill, the plain sentence for ads and the About lead (optional):** `Our own home has been net metered since 2023 and has built up more than ₱33,000 of credit on the bill.`

---

## 3. The headline that asks for the feeling, per page

Register of round 6 (picture, fact, step), now confident, concrete, no hedge, no exclamation mark.

**Home (index.html)**
- hero h1 (9): `The bill comes down. With a battery, the lights stay on.`
- eyebrow (8): drop on the phone; on desktop `Solar engineering for homes in the Philippines`.
- the three wants (31–32): eyebrow `What do you want from solar?` keep; h2 `Which one is you?`
- How it works (55–56): h2 `A minute to a number, a visit to the exact price, a day or two to switch-on.`
- What you get on paper (69–70): h2 `Every peso and every part on paper before you sign.`; the current h2 "Installers sell you panels. We hand you the engineering, then install it ourselves." becomes the section's lead sentence.
- Why people choose us (84–85): h2 `We measure your roof before we price it.`
- Our installations (115–116): h2 `We live with what we sell.`
- Your questions (164–165): h2 `Answered before you ask.` keep.
- band (205): h2 `Your number is a minute away.`

**Brownouts (brownouts.html)**
- h1 (8): keep `Lights on, fans running, when the whole street is dark.`
- h2 (18): `What you keep on when the street goes dark.`
- h2 (38): `Sized to the evening you want to keep.`
- band (53): `See your two prices, with and without the battery.`

**Net metering (net-metering.html)**
- h1 (8): keep `The bill you stop dreading.`
- h2 (18): `Your meter runs both ways.`
- h2 (30): `What the numbers look like.`
- h2 (45): keep `Want lights in a brownout too?`
- band (53): keep `Your bill, your town, one minute.`

**About (about.html)**
- h1 (8): `The first roof we did was our own.` (the oldest installation, 2023, is the owner's home: the fact carries it)
- h2 (20, 32, 40): keep `Who you will meet`, `How we work`, `Where we install`.

**The frame and 404**
- layout.html:31 `Solar engineering for homes` (pinned) keep; 67 `Start here` keep.
- 404.html:7 `That page has moved on.`

**The estimate widget (Estimate.tsx)**
- h1 (313): keep `What would your bill be with solar?` (it is the question the visitor came with).
- question 1 (319): keep `1. What do you want from solar?`; the three options become the home cards' feeling lines with the kind as the small text, so the funnel speaks one language: title `I just want a lower bill.` small `Solar with net metering. The panels run the house by day; extra power becomes credit on your bill. A battery can be added later for brownouts.` / title `I want the lights on when the street goes dark.` small `Solar with a battery. Solar by day, the battery at night and through brownouts; extra power still earns credit on your bill.` / title `I want my roof to run my house.` small `Battery first, nothing sold back. More panels and a bigger battery carry the house day and night; the grid is only the spare. For homes that would rather keep their own power than sell it, and for places where net metering is out of reach.` (The three kinds keep their names, now as the first words of the small text; `GOAL_LABEL` in quick.py and the lead e-mail's "Wants:" are untouched.)
- result h2 (415): `Your estimate for {result.inputs.place}` ("Your estimate for Pila, Laguna").
- the result's first figure (425): keep `Your monthly bill` and the arrow; it is the relief line and it is the engine's.
- booking h3 (491): keep `Want the exact figure? We come and measure. The visit is free.`; after booking `Your roof visit is booked, Maria.` (item 12).
- thank-you (498): keep `What happens next: ...`.

---

## 4. The first screen on a phone from a Facebook link (390 × 844)

Today (`phone-index-first.png`): header (60 px), the eyebrow in two lines of gold capitals, the h1 in three lines, the
70-word lead in eight lines, the gold button, the white "How it works" button, three of the four ticks. The roof photo
starts at 908 px: the second screen. The share card (og:title, layout.html:9) says "See what solar would do to your
bill · PL Development Inc." over the rib roof.

Must be on it, in this order:
1. The roof: the rib-roof photo full width under the header, about 230 px tall (the 4:3 frame cropped to about 16:10 for the phone; `site/tools/photos.py` cuts it), the panels in the top half of the crop.
2. The promise: the h1 of item 3, two lines at most (`The bill comes down. With a battery, the lights stay on.` is 9 words; 34 px fits two lines at 390 px).
3. The button: `Get my free estimate`, gold, full width, with `Four questions, one minute, free` as the small line under it.
4. One proof: `Our own homes have run on what we sell since 2023.` (one line, 15.5 px), or the first tile of the proof strip if the strip starts above the fold.
Then, on the next screens: the proof strip, the three wants, how it works, the questions, the button again; the sticky
call to action on the phone (the UX's part).

Must not be on it: the eyebrow (the header already says "Solar engineering for homes"); the four ticks; the second
button; any sentence with "no", "not", "unless" or "obligation"; "an estimate, not a quotation" (the footer and the
widget carry it); the service-area sentence; anything the profile fills in (it is blank until the fetch answers and
blank on a failed fetch: the first screen must stand without it).

The share card: `og:title` follows `{{title}}`, so index.html:1 becomes `<!-- title: The bill comes down. With a battery, the lights stay on. · PL Development Inc. -->` and the description (index.html:2) `Rooftop solar for homes anywhere in the Philippines, measured on your own roof before we quote. Our own homes have run on it since 2023. Four questions, one minute, free, no sign-up.` ("no sign-up" is the one "no" worth keeping in a snippet: it is what stops the thumb.)

---

## 5. The must-not list that still holds (for the copywriter)

1. No financing: no "payment plan", "instalment", "from ₱X a month", "zero down", "loan", "pay monthly". The proposal's own frame ("about N months of your bill today") is the only money-over-time line, and it is not on the website.
2. No guaranteed savings: "about" before every savings figure; never "will save", "guaranteed", "zero bill", "your bill becomes ₱X" without "about"; the only figures are the engine's example (500 kWh, Tanauan: 4.1 kWp, 7 panels, about ₱193,000, under 4 years, about two thirds) and the visitor's own result.
3. No utility name or colours anywhere: "your electric company".
4. No figure or claim beyond the brief's facts: no before-and-after bill for any of the three homes (none exists); no panel count or kWp summed across the homes; no "first customers", "hundreds of roofs", "N installations" (there are three homes on record); "since 2023" belongs to the owner's home and the oldest installation, never to the company's founding; no switch-over time ("instant", "seamless", "milliseconds", "you won't notice": "by itself" stays until the inverter datasheet gives the figure); no typhoon rating, signal number, wind speed or code; no battery life beyond the maker's 5-year warranty; no panel life beyond the 25-year performance warranty, and that only through the profile hooks; no "measured first" or "after switch-on" for the three homes (the test-panel visit did not exist when they were designed); no installation-day outage length; no brownout frequency; no "lowest price" except "the lowest price of the three ways to go".
5. No customer voice: no quote, no "the family says", no star, no review, no "trusted by". The owner's homes are proof by ownership ("we live with what we sell"), never a testimonial.
6. No brand names, logos or "Tier 1" until the owner sends the logo files; the profile's `brands` line is for the proposal.
7. The words: "estimate", "roof check", "proposal", "roof visit", "energy audit"; never "assessment", "quotation" outside "an estimate, not a quotation", "package", "hassle-free", "premium", "best", "cheapest", kWp/hybrid/grid-tie outside the installation cards, the widget's system line and the Brownouts ticks.
8. The three kinds keep their names, as the small label on the home cards and as the opening words of the widget's option texts: "Solar with net metering", "Solar with a battery", "Battery first, nothing sold back".
9. No towns beyond Pila (Laguna), Fairview (Quezon City) and the engine's Tanauan; no address, no name of a family member, no date beyond "early 2026" and "since 2023".
10. The profile-driven fragments stay hooks (`data-profile`, `data-profile-hide-if-empty`, `data-warranty-wrap`): never type the PEE's name, a phone number, a Messenger link, the owner's name or a warranty year into a page; the `is-empty` build rule and the placeholder markers stay; the strings `backend/tests/test_site.py` pins stay ("How it works", "What you get on paper", "Our installations", "Solar engineering for homes", the four net-metering tiles and labels, the small print's "500 kWh a month, mostly in the evening, net metering without a battery", "Photo: the test panel", "Photo: the owner").
11. No exclamation marks; no superlative without a figure; no sentence that starts with "No."; the law lines stay in substance: a brownout pauses a net-metered system without a battery "as the safety rules require"; "This is an estimate, not a quotation." in the widget's details and the copied summary; the privacy notice untouched.

---

## 6. Ask the owner (each unlocks a line the site cannot carry yet)

1. Settings › phone, Messenger link, Facebook page, e-mail, owner's name: while blank, the footer's "Talk to us", the About "Who you will meet" line, the thank-you's "[Owner] will message or call you" and the widget's trust list have no person in them. The live site must be checked for this first.
2. Settings › the PEE's name and PRC number: the named seal on the hero tick, the Why-us card, the footer and the booking card.
3. Settings › Where you install: `the Philippines` (item 21); After-sales line: the owner's words (item 20).
4. The 25-year performance warranty: confirm on the panel datasheet (the profile already says 25).
5. The inverter's switch-over time from the datasheet: unlocks "the fan does not even stop" on Brownouts.
6. The installation-day outage length: unlocks "your power is off for about an hour on the second morning" in step 5.
7. Brand logo files and the makers' names: the logo strip.
8. Three photos: the owner on a roof visit with the test panel, the crew on an installation day, the two-way meter: the About placeholders and the "roof visit" card.
9. One sentence from a photographed family member, with their yes: the first voice on the site.

---

## Ten lines for the coordinator

1. Nothing Critical in the words themselves; the only Critical is data: if the live profile's phone, Messenger and owner's name are blank, no page on the site has a human to call (layout.html:56–65 hides the whole "Talk to us" block). Verify in Settings before anything else.
2. The one forbidden word on the site is "payment plan" (index.html:76): it reads as instalments; replace with "The savings, and what is due when".
3. The widget's first option still says "No battery, so no power during a brownout." (Estimate.tsx:18), the clause the home card already lost; the funnel contradicts itself a click later.
4. The hero is an instruction over a 70-word lead ending in "No cost, no obligation"; the roof photo is on the phone's second screen. New h1 "The bill comes down. With a battery, the lights stay on."; lead in section 1 item 3; first-screen order in section 4.
5. "So we do it the slow way." (about.html:10) and "It can come out lower or higher than the estimate" (about:10, index:89) are the two sentences a comparing buyer carries to the other quote; replacements in item 5.
6. The strongest proof (₱33,000+ credit since 2023, a house that runs through brownouts) is the third card's muted caption; it becomes the first card and two tiles of a four-tile proof strip (Since 2023 / ₱33,000+ / 3 family roofs / 1 free visit), the 25-year warranty as the profile-driven fifth.
7. The engine's "Saved over 25 years: about ₱941,000" is hidden under "How we worked this out"; it belongs in the result hero as the third figure, and in the copied summary.
8. Every "not / no / does not reach zero / switches off / shortens / adds little" construction has a replacement that keeps the fact (24 items, all S effort, 21 text-only); the honesty lines survive inside the sentences; nothing new is claimed.
9. Headlines per page in section 3; the widget's three options become the home cards' feeling lines with the kind's name as the first words of the small text, so the funnel speaks one language. Pinned strings and hooks untouched; test_api.py:678 changes with the after-sales default if that is taken.
10. The must-not list for the copywriter is section 5; the owner's ask list is section 6 (nine items; the first three are Settings fields, minutes each). Servers on 8201 and 8211 stopped; screenshots and scripts in this folder.
