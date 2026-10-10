# Round 9, marketing: the installations without "ours", and the estimate as a teaser

From the marketing and sales specialist to the copywriter, 10 October 2026. Written against `claude/wonderful-maxwell-wawb8t`
at fc89f13: the site pages as merged in round 7 (line numbers are `site/pages/*.html`, `site/partials/proof.html`), and
the widget as it will stand after my round-8 brief, cited by role (the hero, the "What you get / What it does" lines,
the alternative, the booking card, the foot, the summary, the scene). Facts: the round-7 brief, nothing more. Rails:
no customer voice, no name, no address, no implied customer, no financing, no utility name, no new claim; every hook,
class, id and `data-profile` attribute stays; `backend/tests/test_site.py` pins "Our installations" (the eyebrow),
"₱33,000+", "2023", `data-count="33000"`, "Photo: the test panel", "Photo: the owner" and the net-metering small print,
all of which survive below.

## Part 1. The installations as proof, with ownership dropped entirely

The owner's ruling (10 October): "NO, we will drop ours entirely." Nothing on any page, strip, snippet or widget may
say or imply whose houses these are.

### The angle
Three installations as worked examples a buyer compares his own house to, each stated as what it is (kWp, panels,
inverter, battery, year, town) and what it was sized for, with the record doing the persuading: the oldest has been on
net metering since 2023, the electric company's bill has carried more than ₱33,000 of credit since, every typhoon
season since has been stood, and the drone photographs show the rails, the groups and the conduit. The reader is never
told to trust the company; he is shown a bill figure that an electric company printed, a date, a size and a photograph,
and invited to find the roof like his. This also answers the round-7 "grabbed photos" worry better than ownership did:
specifics and a record cannot be grabbed. One rule for every line: the subject is the installation or the house, never
a person; "the house runs through brownouts", never "the family".

Words that go, everywhere: "our home", "our own home", "our parents' house", "our family's house", "our own bill",
"our own roofs", "family homes of our own", "we live with what we sell", "our oldest roof is our own", "where our
family lives". Words that stay, because they are the company's and not the homes': "our own workmanship warranty"
(index 190, 198; about 64), "installed by our own crew" (about 78), "ours on the installation" (brownouts 80),
"photographed by us from the air". Also withdrawn: the optional line in my round-8 brief ("Our own home in Pila,
Laguna has run on what we sell since 2023"); it was not implemented on the branch and must not be.

### The replacements, in the exact words

**index.html**
- 2, description (and the og:description share snippet): `Rooftop solar for homes anywhere in the Philippines,
  measured on your own roof before we quote. The oldest installation has been on net metering since 2023. Four
  questions, one minute, free, no sign-up.`
- 23, hero tick "Our own home on solar since 2023" → `The oldest installation on net metering since 2023`
- 64, h2 "We live with what we sell." → `Three roofs in service. Which one is like yours?` (alternative: `Three
  installations, three sizes. Find the roof like yours.`)
- 65, lead → `Photographed from the air by us, with the size on each photo: a three-roof house with a 30 kWh battery,
  a daytime house on eight panels, and a hip roof carrying sixteen. The oldest has been on net metering since 2023,
  with more than ₱33,000 of credit on its bill since, and has stood through every typhoon season.`
- 67, `aria-label="Our own roofs"` → `aria-label="Three installations"` (an attribute's words, not a hook).
- 77, heading `<span class="who">Our home</span>` → `<span class="who">Three roofs, one battery</span>`; `.where`
  unchanged. 78, caption → `13.75 kWp across three roofs, with a 30 kWh battery, a 12 kW hybrid inverter and a 6 kW
  grid-tie inverter: sized to run the house through brownouts, and it does. On net metering since 2023; the electric
  company's bill has carried more than ₱33,000 of credit since.`
- 90, `Our parents' house` → `Eight panels, panels only`. 91, caption → `4.56 kWp on a 6 kW grid-tie inverter, panels
  only: the lowest price of the three ways to go, and the eight panels carry the house by day. Fixed through the roof
  sheet to the framing beneath. Installed early 2026.`
- 103, `Our family's house` → `Sixteen panels, hip roof`. 104, caption → `9.12 kWp in three groups across three faces
  of the hip roof, each on its own rails, on a 12 kW hybrid inverter that takes a battery whenever one is wanted.
  Installed early 2026.`
- 193–194, typhoon FAQ → `The 2023 installation in Pila, Laguna has stood through every typhoon season since. The rails
  are fixed through the sheet to the roof framing with sealed fasteners, on plans a Professional Electrical Engineer
  signs and seals.`
- The eyebrow "Our installations" (pinned) stays: it names the company's work, not a home. The chips (13.75 / 4.56 /
  9.12 kWp), the placeholder card and "Swipe for the next roof." stay.

**site/partials/proof.html** (the four labels; the figures, `data-count` and "2023" unchanged)
- 3: `of net metering credit on one bill since 2023, as the electric company prints it`
- 4: `the oldest installation went on net metering, and has stood through every typhoon season since`
- 5: `installations photographed from the air, in Laguna and Quezon City`
- 6: keep `free visit: a test panel on your roof and your bill on the table, before we quote`

**about.html**
- 13, h1 "Our oldest roof is our own." → `Measured first. In service since 2023.`
- 14, lead → `<span data-profile="company_name">PL Development Inc.</span> designs and installs rooftop solar for homes
  from <span data-profile="address">Pila, Laguna</span>, across <span data-profile="service_area">the Philippines</span>:
  the roof measured before it is priced, the plans sealed by a Professional Electrical Engineer, and the oldest
  installation on net metering since 2023.` (the three spans exactly as today).
- 30, figcaption → `Pila, Laguna: 13.75 kWp on three roofs with a 30 kWh battery, on net metering since 2023, with
  more than ₱33,000 of credit on the bill since.`
- 50, figcaption → `Pila, Laguna: eight panels, 4.56 kWp, fixed through the roof sheet to the framing, installed early
  2026.`
- 97 → `We are based in <span data-profile="address">Pila, Laguna</span>; the installations on these pages are in Laguna
  and Quezon City, and we travel to wherever your roof is.`
- 2 (description), 35–36, 61–64, 74–79: no ownership; keep.

**brownouts.html**
- 37, figcaption → `Pila, Laguna: 13.75 kWp with a 30 kWh battery; the house runs through brownouts.`
- 55, figcaption → `Fairview, Quezon City: 9.12 kWp on a hip roof, solar by day, with the inverter ready for a battery
  whenever one is wanted.`

**net-metering.html**
- 74, figcaption → `Pila, Laguna: on net metering since 2023, with a 30 kWh battery for the brownouts.`
- 48, small print, optional: "From our own estimate at today's prices" → `From this website's estimate at today's
  prices` (the pinned substring "500 kWh a month, mostly in the evening, net metering without a battery" untouched).

**The widget, layout.html, 404.html, privacy.html, estimate.html**: no line marks a home as the company's ("our own
server" on privacy is the company's); nothing to change. The share snippets follow each page's title and description
comments; only index.html:2 carried ownership.

**Not to be written anywhere** (the implied-customer rule): "a family in Pila", "the homeowner", "a client's roof",
"one of our customers", a first name, a street, a photo caption that reads as a testimonial. The subject of every
sentence is the installation, the roof or the house.

## Part 2. The estimate as a teaser that pulls the visitor into the visit

### The judgement
The site promises, on every page, "your new bill and the price in a minute" (the home lead, step 1 "what your bill
becomes, the price and how many panels it takes", the Brownouts band "See your two prices, with and without the
battery", the footer "an estimate to decide with"). The result today keeps that promise and then keeps going: the kWp
and the watts per panel, the roof m², the inverter kW, the battery kWh, the kWh made a month and its percentage, the
coverage, the import kWh, the CO₂, the 25-year total. Those are the proposal's figures, printed on a free widget from a
typical roof, and they do two kinds of harm: the visitor who reads "96% of what you use" and "₱957,000 over 25 years"
has nothing left to want from the visit, and the sceptic who reads them on a widget discounts them, where the same
figures under a sealed proposal with his roof's readings would convince him.

What the free result must show to keep the promise and the feeling: the bill before and after with the monthly
saving (the relief, the one number the visitor came for); the price (the owner's choice, below; my pick is that it
stays); how many panels (promised in step 1, and the honest size for a homeowner); the two prices and two bills with
and without the battery (promised on Brownouts); the payback (the "is it worth it" number); the battery as what it
carries, in the engine's words without its kWh; the day scene (the feeling of the house living a day, with the hourly
kW as its proof).

What the visit genuinely settles, so the result holds it back and says so: how many panels the roof really holds and
where (the test panel and meters, face by face); the kWp and the layout; the inverter and battery sizes (the energy
audit sizes the battery from the real appliances; the engine's own assumption says so); the kWh made and the coverage
(the roof's own sun); the roof area; the import kWh; the 25-year total and the year-by-year savings; the CO₂; every
part and peso and the dates. The result then ends on this list, under the booking card's heading, instead of on
everything already known.

The two risks, weighed: a result without the bill or the price loses the visitor who came for a number and reads the
company as the kind that hides it; a result with the whole proposal on it leaves no reason to book. The line between
them is the line between "what the house gets and what it costs" (shown) and "how the engineering gets there"
(the visit). Nothing in the engine, the lead payload, the lead e-mail ("Saw on the website: 5 panels, 2.92 kWp, …") or
the engineering app changes: only what the page prints. (`DECISIONS.md` "Quick estimate", "Shown to the visitor",
needs the coordinator's one-line update.)

### The owner's choices
1. **The price.** Version A (my pick): the price stays, as "₱308,000, the whole job: installed, permits and papers
   filed, VAT included". The promise on every page says "the price"; a Facebook visitor's first question is the cost;
   a company that shows the bill but hides the price looks like the ones that quote from a satellite photo and
   negotiate; and the breakdown is already gone, so a competitor learns one total he could get with one phone call.
   Version B: the price goes to the proposal ("The price, exact to your roof, is in your proposal."). Then the payback
   goes too (price ≈ payback × first-year saving, so it leaks), the sticky bar carries the bill (as in A), and these
   promises change: index.html:18 "shows you the price and your new bill" → "shows you your new bill"; index.html:129
   "what your bill becomes, the price and how many panels it takes" → "what your bill becomes and how many panels it
   takes"; brownouts.html:98 "See your two prices, with and without the battery." → "See your new bill, with and
   without the battery."; estimate.html:2 "what solar would cost and save at your house" → "what solar would save at
   your house"; the widget's intro lead drops "the price of the whole job"; the summary drops its price line.
2. **The kWp on the scene's chip.** My pick: it goes with the other sizes (the panel count carries the size for a
   homeowner; with the price shown, the kWp is the one figure that lets a competitor price per watt). If the owner
   wants the comparing buyer served now, keep "6 panels · 3.51 kWp" on the chip and the counter only, nowhere else.

### The result, top to bottom (version A; the words are the round-8 ones unless given here)
1. **Heading**: `Your estimate for Pila, Laguna`, the cap warning under it when it applies.
2. **The day scene**: unchanged in motion and words, the hourly readout kept exactly (it is the proof the day is
   computed for this house); the counter and the chips lose the sizes: `6 panels`, `inverter`, `battery`,
   `net metering` / `grid as backup`; the SVG labels `inverter` and `battery`; the aria-label `6 panels on the roof,
   an inverter, a battery and the meter with net metering: an ordinary day, the sun up from 6 AM to 6 PM, the power
   flowing between the panels, the house, the battery and the grid.`
3. **The hero**: `Your monthly bill` / `₱4,803 → about ₱199` / `about ₱4,604 a month stays in your pocket; what still
   comes is your electric company's fixed charges` (small-bill form as in round 8). Then two cells, not three: `Pays
   for itself in` / `7.4 years` / `about ₱55,000 saved in the first year`; `Estimated price` / `₱308,000` / `the whole
   job: installed, permits and papers filed, VAT included`. The "Saved over 25 years" cell goes (it returns as a
   promise in block 7). The no-economics hero (price only) unchanged.
4. **The two actions**: `Book my free on-site assessment` / `Try other answers`.
5. **What you get / What it does**, without the sizes and percentages:
   - with a battery: `What you get: 6 panels on the roof, a hybrid inverter on the wall and a lithium battery, enough
     for a typical night of your use when the grid is down.` (the note in whichever of its two forms the engine
     gives; the kWh, watts, kWp and m² go). Panels only: `What you get: 6 panels on the roof and a hybrid inverter on
     the wall; a battery can be added whenever you want lights in a brownout too.`
   - `What it does:` by goal. With a battery: `By day the panels run the house and fill the battery; the battery
     carries the evening; the extra goes to your electric company and comes back as credit at its generation rate,
     so what still comes is a small bill for the fixed charges and the hours the grid covers.` Net metering: `By day
     the panels run the house; the rest of the day's sun goes back through the meter as credit on your bill, at your
     electric company's generation rate; the evening runs on the grid, like today, so what still comes is a smaller
     bill.` Battery first: `The panels and the battery carry an ordinary day on their own, and the grid is only the
     spare; nothing is sold back, so once the battery is full the extra sun goes unused. In long rainy spells the
     grid still steps in; your proposal says how much.` (the kWh a month, the percentage of use, the coverage and the
     import kWh all go to the proposal).
6. **The alternative**, both prices, both bills, both paybacks, no kWh: battery shown, as round 8 (`Panels only,
   without the battery: ₱180,000, the bill about ₱1,252 a month, pays for itself in 4.1 years. The panels do the saving
   either way; the battery is what keeps the lights on when the street goes dark.` / `Show it without the battery`);
   not shown: `Want the lights on when the street goes dark? A battery is about ₱128,000 more, enough for a typical
   night of your use when the grid is down; the bill about ₱199 a month, pays for itself in 7.4 years.` / `Show it
   with the battery`.
7. **New closing block, before the booking card** (a `pld-line`-style block; h3 and a list; every line traces to
   "What you get on paper", "How it works" or the FAQ):
   h3 `What the free visit settles`
   lead `This estimate comes from your answers and a typical roof. One free visit, with the test panel and meters on
   your roof and your bill on the table, settles:`
   - `how many panels your roof really holds, and where they go: the sun and the shade read face by face`
   - `what your battery carries on a brownout night, from your own appliances rather than a typical house: the
     fridge, the fans, the Wi-Fi, the aircon if you size for it` (panels only: `what a battery would carry on a
     brownout night, from your own appliances, if you want one`)
   - `the exact price to your roof: every panel, rail, cable and breaker listed, and what is due when`
   - `your savings year by year, and what 25 years add up to on your roof`
   - `the plans signed and sealed by a Professional Electrical Engineer, the permit and the net metering papers,
     filed by us`
   - `the dates: permit, installation day by day, switch-on and the two-way meter`
   close `Then your proposal, within two working days, every peso and every part on paper, and you decide with all of
   it in front of you.`
8. **The booking card and the thank-you**: the round-8 words (`The exact figure is one free visit away.`, the hint,
   the fields, `Book my free on-site assessment`, the thank-you's two paragraphs). The thank-you's "Copy my estimate"
   copies the summary below.
9. **The foot**: `Worked out for a house in Pila, Laguna using about 400 kWh a month, mostly in the evening. This is an
   estimate from your answers, not a quotation: on the free on-site assessment we measure your roof and the sun on
   it, and the proposal that follows is exact.` (the CO₂ goes to the proposal).
10. **The sticky bar** (the `.pld-sticky-label` / `.pld-sticky-price` elements, the button unchanged): label
    `Your new bill`, value `about ₱199 a month` (small-bill form `a small bill`), button `Book my free on-site
    assessment`. The outcome rides down the page with the visitor; the cost sits in the hero where its sub-line is.

### The copied summary (version A; version B drops the price line and "pays for itself")
```
Solar estimate from ${company} for ${place}:
Bill ${before} → ${after} a month; about ${year1} saved in the first year; pays for itself in ${years}.
Price ${price}, installed, permits and VAT included.
6 panels and a battery, enough for a typical night of your use when the grid is down; the exact layout and sizes come from the free on-site assessment.
This is an estimate, not a quotation; the free on-site assessment makes it exact.
Questions: m.me/… · Run your own: …/estimate
```
(Panels only: `6 panels, and a battery can be added later; the exact layout and sizes come from the free on-site
assessment.`)

### What leaves the page, in one list (and lands in the proposal)
The watts per panel, the kWp, the roof m², the inverter kW, the battery kWh (both variants), the kWh made a month and
its percentage of use, the coverage percentage, the import kWh, the CO₂, the 25-year total. What stays: the bill
before and after, the monthly saving, the first-year saving, the payback, the price (owner's choice), the panel count,
the two prices and bills with and without the battery, the battery note in words, the hourly kW in the scene.

### Must not change
"This is an estimate, not a quotation" in the foot and the summary; "Book my free on-site assessment" on both buttons
and the sticky bar; "about" before every savings figure; the fixed charges and the rainy-spell hours as what still
comes; the battery as comfort and backup, the panels as the saving; no financing, no utility name, no new claim; the
three kind names on card 1 and the chip; every class, id, `aria-*`, `data-*`, handler and the `#pld-book` anchor.
