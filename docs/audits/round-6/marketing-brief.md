# Angle brief, round 6: the website sells the feeling

From the marketing and sales specialist to the copywriter. 10 October 2026. Read-only: nothing in the repository was
changed. The pages were read as served (http://127.0.0.1:8195, built site) and in source (`site/pages/*.html`,
`site/layout.html`); the estimate widget's texts in `frontend/src/estimate/Estimate.tsx` (the file was edited by
another session while this brief was written, for the location button; line numbers below are from the current
file, and every instruction also quotes the string, so cite by string if the lines move again).

The owner's instruction, verbatim: "instead of full solar terms let's make it so that it will sell emotions, for
example the battery = comfort is a good start."

The round's constraints in one line: nothing fabricated; no guaranteed savings, no "from ₱X a month", no financing;
no utility name (say "your electric company"); "estimate", "roof check", "proposal", never "assessment"; the three
system kinds keep the estimate's names; a battery is for comfort and backup, not savings, and the page says so; the
HTML structure, classes, ids and `data-profile` hooks stay; no town on any card.

## 0. The pages, ranked by lost sales, and the order of work

| Rank | Page | Why it ranks here | Leading feeling | Who edits |
|---|---|---|---|---|
| 1 | The estimate result, the two prices, the booking form, the thank-you (`Estimate.tsx`) | Every ad, post, Messenger reply and the card's QR land here; it is where a visitor becomes a lead or leaves | Control, then relief; the thank-you sells calm | The coordinator, from your report (file and line) |
| 2 | Home (`index.html`) | The front door and the share preview; most visitors read the hero and nothing else | Relief, with calm under it | You |
| 3 | Brownouts (`brownouts.html`) | The owner's own example ("battery = comfort"); the ad angle 1 audience (₱4,000 to ₱10,000 bills) | Comfort | You |
| 4 | Net metering (`net-metering.html`) | The strongest numbers on the site, and the one headline the engine does not support | Relief | You |
| 5 | About (`about.html`) | "Who are you?", the comparing buyer's second visit before they message | Calm, then pride | You |
| 6 | The frame (`layout.html`: tag line, footer) | On every page; the footer is the human to call | Calm | You (two lines at most) |
| 7 | 404 (`404.html`) | Rare; one word | Calm | You |
| – | Privacy (`privacy.html`) | Legal | – | Nobody |

Order of work: Home first (hero, three cards, the installation captions), then Brownouts, then Net metering (the
headline must go in this round), then About, then the two frame lines, then 404. Draft the widget's texts last and
put them in your report with file and line, not in the worktree. Leave alone: `privacy.html`; every `data-profile`
and `data-warranty` hook; the photo `alt` texts (they stay literal); the strings the site tests pin (section 5).

## 1. The register: how a feeling is sold without a claim

Three sentences, in this order, in nearly every paragraph: the picture (one sentence from the customer's day),
the fact (one sentence the facts in force allow), the step (where it leads: the estimate, the visit, the proposal).
Feeling words describe the customer's life, never the product: "a comfortable evening", not "a premium battery".
The headline says what the reader gets; the first sentence under it says what it feels like; the rest earns it.

The five feelings and the pictures that carry them (reuse these; do not invent customers or quotes):

- **Comfort** (the battery). The whole street dark and your windows lit. The fan still turning at 2 a.m. The fridge
  cold through a three-hour brownout. The children finishing homework with the lights on. The Wi-Fi up for whoever
  works from home. Rule: these are what the battery is sized for, so the sentence after the picture must say the
  estimate tells you whether yours "holds a typical night" or "how many hours of your evening" (the engine's own
  words), and that running aircon shortens it. Never "all night, guaranteed", never "you will not notice" (the
  owner has not given the inverter's transfer time; section 7).
- **Relief** (the bill). The bill that stops being the thing you dread at the end of the month. The money that
  stays in the house. The credit line on the bill (the three-roof house's "more than ₱33,000"). Rule: the only
  figures are the engine's example (net-metering page) and the visitor's own estimate; "about", never "will".
- **Pride** (the roof). A roof that works for the family. The neighbour looking up and asking who did it. Real
  roofs photographed from the air. Rule: a picture, never a testimonial; no customer said anything to us.
- **Calm** (the contractor). We come to the house. We put the test panel on the roof ourselves. We file the papers;
  you sign two forms. The owner is on every visit and every proposal. A name and a number in the footer. After the
  booking: nothing more to do now. Rule: every "we" claim is one the site already makes about the company's method.
- **Control** (the paper). Every peso and every part on paper before you sign. Two prices, with and without the
  battery. "An estimate, not a quotation." The proposal shows why the price moved. Rule: keep these lines verbatim.

Mechanics: short sentences, one idea each; no exclamation marks; no superlatives without a figure; English with a
Filipino word only where everyone uses it in English anyway ("brownout", "aircon" qualify; nothing else needed);
numbers as a person says them ("about two thirds", "under four years", "more than ₱33,000"); the next step at the
end of every section ("Get my free estimate" stays the button text everywhere).

## 2. The proof the facts allow, and what must not be claimed

Allowed, verbatim or paraphrased without adding anything (the round brief, 10 October):

- Card 1, the rib roof: 8 panels, 4.56 kWp, a 6 kW grid-tie inverter, no battery, not on net metering, installed
  early 2026. The orange run is the PV-wire conduit; the rails sit on L-feet fixed through the sheet.
- Card 2, the hip roof: 16 panels, 9.12 kWp, a 12 kW hybrid inverter with no battery attached, not on net metering,
  installed early 2026. The black runs are HDPE conduit, the final state.
- Card 3 and About, the three roofs: 13.75 kWp, a 30 kWh battery, a 12 kW hybrid inverter and a 6 kW grid-tie
  inverter carrying a 5.5 kWp part of the array; net metered since 2023 (three years in, as of October 2026);
  ₱33,568.72 of credit, printed as "more than ₱33,000"; photographed between nine and ten in the morning; "the
  design provided extra panels so that shadings will not bring the production down too much".
- All three are family homes. The owner flew the drone: "Our own installations, photographed by us from the air.
  No addresses, no names." (index.html:113, keep exactly).
- The engine's example (net-metering.html:31–39, pinned by `tests/test_site.py`): a house using about 500 kWh a
  month in Tanauan, Batangas, mostly in the evening, net metering without a battery: 4.1 kWp, 7 panels, about
  ₱193,000 installed VAT included, pays for itself in under 4 years, about two thirds off the bill. This is the
  one place a town is allowed, because it is the engine's example, not an installation.
- The engine's own sentences, which the result prints and the pages may echo: "enough for a typical night of your
  use when the grid is down" / "about N hours of your evening use when the grid is down"; "Saved over 25 years"
  (the analysis period, `analysis_years = 25`); "a small bill" when the modelled bill is under ₱100; the price
  "installed, with permits, VAT included".
- The warranties, from the profile at page load, never typed into a page: "Workmanship: 2 years on our
  installation, including leak-free roof penetrations." "Panels: 12-year product warranty from the maker."
  "Inverter: 5 years from the maker." "Battery: 5 years from the maker." A page may say "warranties in writing,
  printed on every proposal" and let the `data-warranty-list` print the years. The panel performance warranty is
  blank in the profile, so the net-metering page's fifth tile stays hidden and no page says how long panels last.
- The method, as the site already states it about the company (allowed on every page, never attached to the three
  photographed jobs, which were designed before the test-panel visit existed): we come to the house; a test panel
  and meters on the roof; sized to the bill and the hours you use power, not to a package; plans signed and sealed
  by a Professional Electrical Engineer (name and PRC number from the profile); the permit, the final inspection,
  the ERC certificate of compliance and the net metering application filed by us, "you sign two forms";
  installation in one or two days; rails through the sheet to the roof framing with sealed fasteners, no open holes.
- The pipeline's promises (home page and thank-you, keep consistent): one minute, free, no sign-up; the visit
  about an hour, free; the roof check card the same evening; the proposal within two working days, valid 15 days
  (the pricing setting); the owner messages or calls "within one working day" (profile default).

Must not be claimed anywhere (each one has cost a sale or a reputation somewhere; several are the law):

- Guaranteed savings, "will save", "your bill becomes ₱X" without "about", "from ₱X a month", instalments, loans,
  "zero down", any financing word. The safe frame is the proposal's "about N months of your bill today".
- The utility's name or colours. "Your electric company."
- A town, a customer's name, a street, a barangay, a date beyond "early 2026" and "since 2023", for any card.
- "Measured on the roof first" or "after switch-on" for the three photographed installations.
- A battery that saves money. The battery is for comfort and backup; the panels bring the bill down. On a page
  with both, attribute the saving to the panels in the same sentence.
- The inverter's switch-over time ("instant", "seamless", "you won't notice", "the lights never flicker"). Today the
  pages say "the moment the grid drops" (brownouts.html:9, index.html:165); keep no stronger than "takes over by
  itself" until the owner answers (section 7).
- A typhoon or wind rating, a "built for signal no. 3" line, any code reference. Nothing from the owner yet.
- Battery life beyond the maker's 5-year warranty; "lasts 10 years"; cycle counts. Panel life ("twenty more
  years", net-metering.html:9) beyond what the engine counts (25 years of savings in the estimate).
- A performance guarantee ("makes at least X kWh"). The estimate's line is "about N kWh a month".
- "The price never changes", "the price you sign is the price you pay". The site's honest line is "It can come out
  lower or higher than the estimate, and it shows you why." Never promise it comes out lower.
- A quote from a customer, a neighbour, a reviewer. There are none.
- "All installers" or "other installers cheat". Keep the existing "Most installers quote from a satellite photo."

## 3. Words: the customer's against the engineer's, and where a figure still belongs

| Avoid (the engineer's) | Use (the customer's) | Where the engineer's word still belongs |
|---|---|---|
| kWp, "the array", PV | "eight panels", "the panels on the roof", "what your roof makes" | The three installation cards (the buyer asks "ilang kW?"), the net-metering tiles (test-pinned), the estimate's system line |
| kWh (of a battery) | "enough for a typical night", "about N hours of your evening" | The bill's own kWh on question 3 ("kWh on your latest bill"), the battery size in the estimate's system line and the "Add a battery (N kWh…)" line, the card facts (30 kWh) |
| hybrid, grid-tie, "hybrid system" | "solar with a battery", "the battery system", "solar with net metering" | The card facts (the owner's words: "6 kW grid-tie inverter", "12 kW hybrid inverter"), once in the Brownouts ticks for the comparing buyer |
| inverter (in a headline or lead) | "the box on the wall that switches over by itself" is too cute; just keep "inverter" out of leads | The parts list card, the warranties, the card facts, the estimate's system line |
| DC/AC, MPPT, string, export limiter, anti-islanding, conduit sizes | never on a page | nowhere |
| "surplus", "export", "generation rate" | "extra power", "what you do not use", "credit on your bill", "the rate it pays, lower than the rate you pay" | The FAQ answer on net metering may keep "generation rate" once, with the plain gloss beside it |
| "the system" (as the subject of a sentence) | "the panels", "the battery", "your solar", "your roof" | The estimate's "The system:" label, the card facts |
| LiFePO4 | "lithium battery" | Once, in parentheses, in the Brownouts ticks: the buyer comparing two quotes asks for it |
| "ERC certificate of compliance" | keep, with "(the net metering certificate)" the first time on a page | The papers lists; it is a real paper the buyer will be asked about |
| "assessment" | never | nowhere |
| "quotation" | only inside "an estimate, not a quotation" | nowhere else |
| "refrigerator", "wifi" | "fridge", "Wi-Fi" (one spelling everywhere) | – |
| "package", "hassle-free", "revolutionary", "premium", "best" | nothing; a fact instead | – |
| "load(s)", "usage" (alone) | "what you use", "the hours you use power", "what you want to keep on" | The engine's sentences inside the result stay as they are |

Figures that must stay because the reader asks for them: on the installation cards the panel count, the kWp, the
inverter and the battery, the year; on the net-metering example all four tiles and the small print; in the estimate
the price, the bill before and after, the payback, the panel count, the roof area, the battery's kWh and what it
carries; in the pipeline the minutes, hours, days and the validity.

## 4. Page by page, section by section

### 4.1 Home (`site/pages/index.html`)

**The hero (lines 8–20).** Feeling: relief, with calm in the second sentence. Picture: the bill arriving and the
family not minding; then "we come to the house". Proof: one minute, free, no sign-up; "we come and measure your
roof"; the four tick points (16–19) are the method and stay. Objection: "Is this another installer that quotes
from a photo?" (tick 16 answers it) and "Will someone pester me?" (the estimate asks no name; say so: "nobody calls
unless you ask"). Keep: the eyebrow (8), the two buttons (12–13), the four ticks (16–19). Change: the h1 (9) and the
lead (10). The h1 today ("See what solar would do to your bill.") is a good relief line and may stay; if you replace
it, keep "bill" in it and no figure. Example in section 6.

**Three ways to go (31–49).** Feeling per card: relief (net metering), comfort (battery), independence or peace of
mind (battery first: for homes that cannot, or do not want to, apply for net metering). Keep exactly: the h2 (32,
"one honest estimate" is the brand), the three tags (35, 40, 45) and the three h3 names (36, 41, 46): they are the
estimate's own words, so the visitor meets the same three on the first question. Keep every sentence that is
there; add one picture sentence at the front of each paragraph. Card 1 must keep "No battery, so no power during a
brownout." Card 2 must keep "The battery is for comfort, not savings, and we say so." Card 3's text is the
estimate's text word for word (Estimate.tsx:20) and stays. Objection pre-empted here: "Which one is for me?"; the
tags answer it.

**How it works (53–65).** Feeling: calm (what happens when, and that we do it). Keep the eyebrow "How it works"
(55, test-pinned) and the five step names in bold and the `when` spans. Change line 58 "You see the system size,
the price and what it saves each month" to the customer's order: "You see what your bill becomes, the price, and how
many panels it takes." Line 61: "size the system to your usage" → "size it to what your house really uses". Line 62
stays (it is the papers promise). Objection: "What happens when?" is the section; "How long will I be without
power?" is not answered anywhere on the site (the proposal has the owner's `installation_outage_hours` setting;
the website says nothing, and should not until the owner gives the figure).

**What you get on paper (67–80).** Feeling: control. Keep the eyebrow (69, test-pinned) and the h2 (70; it is the
positioning: "Installers sell you panels. We hand you the engineering, then install it ourselves."). The six cards
are already in the customer's words; sharpen "not to a package" (73) and "so you know what is going on your roof"
(74), which are the control lines. Line 76 "The savings and payment plan" must not grow into financing: "what is due
when" is the milestone schedule, and that is all.

**Why people choose us (82–107).** Feeling: calm and control. Keep the h2 "We measure before we quote." (85) and
the whole of line 89, including "It can come out lower or higher than the estimate, and it shows you why." (the
honesty line a competitor cannot match). Line 93 keeps the paper names; add "(the net metering certificate)" after
"ERC certificate of compliance" if it is not already glossed on the page. Lines 97 and 100–103 are profile-driven;
do not touch the text inside `data-profile="brands"` or the warranty list; the fallback sentence "We name the
panel, inverter and battery brands on every proposal." stays. Objections pre-empted: brand and warranty (97–103),
papers (93), "is it exact?" (89).

**Our installations (109–156).** Feeling: pride. Picture: the neighbour looking up; "roofs like yours". Keep the
eyebrow "Our installations" (111, test-pinned), the h2 (112) and line 113 exactly. The captions: section 5 below.
Never add a town, a name, a date beyond the ones there, "measured first" or "after switch-on". The placeholder
block (145–153) is stripped from the public build; leave it.

**Your questions (158–189).** Feeling: calm (answered before you ask). Keep every answer's facts; the six questions
are the objection list and stay in this order. Edits allowed: 165 "refrigerator… wifi" → "fridge… Wi-Fi"; 165 "a
net-metered system switches off during a brownout, as the safety rules require" stays (it is the law and the
honesty line for the no-battery buyer); 169 may gloss "generation rate" ("the rate it pays for power, lower than
the rate you pay"); 173 keep "We do." and "You sign two forms."; 177 keep as is (it was corrected in round 3 and
claims no transfer rule); 181 keep as is (the roof objection, backed by the workmanship warranty "including
leak-free roof penetrations" that the profile prints); 185 keep as is (the "is this a quotation?" line). Do not add
a typhoon answer, a battery-life answer or an outage-length answer; the owner's facts are not there (section 7).

**The band (191–197).** Feeling: relief. Keep "Find out in a minute." (193) and the button. Line 194 may become
"Your bill, your town, when you use power. That is all it takes."

### 4.2 Brownouts (`site/pages/brownouts.html`)

This is the owner's example. The page already has the right headline (8, "Lights on, fans running, when the whole
street is dark."): keep it exactly. The rest reads like a spec sheet from line 9 down.

**The hero (7–13).** Feeling: comfort. Picture: the street dark, your windows lit; the fan at 2 a.m.; the fridge
cold; homework done; the Wi-Fi up. Proof: "the switch-over is automatic"; "by day the panels run the house and
recharge it"; the estimate shows both prices. Objection: "Does the battery pay for itself?" Answer it in the hero's
last sentence, attributing the saving to the panels: "and the panels still bring the bill down every month" (today
line 9 ends "And the bill still goes down every month.", which a reader attributes to the battery). Soften "A
battery takes over the moment the grid drops" to "the battery takes over by itself" until the owner gives the
transfer time. Keep the eyebrow "Solar with a battery" (7).

**What a battery does, plainly (16–34).** Keep the h2 (18) and the three card titles (21, 25, 29). Card "In a
brownout" (22): comfort; the picture leads, then the engine's two phrasings ("holds a typical night", "how many
hours of your evening"), then "running aircon shortens that" (keep), then "we size the battery to what you want to
keep on" (keep). Example in section 6. Card "Every other day" (26): calm; "the battery stores the afternoon's extra
solar and spends it after sunset" is good; replace "The rest of the surplus is still credited on your bill under
net metering" with "What is left over still earns credit on your bill." Card "What it costs" (30): control and
honesty; keep "roughly a third to nearly half" (the page's own figure) but say "of the price of solar with a
battery" instead of "of a hybrid system's price"; keep "It buys comfort and backup more than savings" (the owner's
rule) and "the estimate shows both prices, with and without the battery, so you can decide."

**Sized to your house, not a package (36–48).** Keep the h2 (38). The lead (39) must lose its second sentence
("Lithium (LiFePO4) batteries, a hybrid inverter that works with the grid and the battery, and a two-way meter from
your electric company."): it is the engineer talking in the one paragraph that should say "we size the battery to
the evening you want to keep". Move the equipment into the ticks, where the comparing buyer looks: 42 stays
("Battery sized to the evening you want to keep: lights, fans, fridge, TV, Wi-Fi, with or without aircon"); 43
"Hybrid inverter with automatic switch-over" → "Switches over by itself (a hybrid inverter does it)"; 44 "Net
metering credit for the surplus" → "Extra power still earns credit on your bill"; add one tick "A lithium battery
(the LiFePO4 kind), named by brand on your proposal" only if you keep the brand line profile-driven (the brands
line is on the home page; do not type a brand here). Line 45 is warranty-driven and stays as it is.

**The band (50–56).** Keep "See both prices, with and without the battery." (52): it is the control line that
closes the comfort page honestly. 53 stays.

Objections this page must pre-empt, in order: "Will the aircon run?" (shortens it; say so), "How long does it
last in a brownout?" (the estimate's two phrasings), "Is it worth it?" (comfort and backup, not savings; both
prices), "What about when the battery dies?" (only the maker's warranty, printed from the profile; nothing more).

### 4.3 Net metering (`site/pages/net-metering.html`)

**The hero (7–13).** Feeling: relief. Picture: the bill that stops being dreaded; the credit line on the bill.
Two lines must go:

- Line 8, h1 "A bill of thousands, down to a few hundred." Severity Critical, effort S. The page's own example
  (36) says "about two thirds off", and the engine's run behind the Facebook ad (docs/marketing.md, 9 October) says
  ₱5,003 → about ₱1,460: for the typical visitor the bill ends in the low thousands, not "a few hundred". A buyer
  who runs the estimate ten seconds later sees the headline contradicted by the site's own number, and a
  competitor screenshots the pair. Replacement headline: "The bill you stop dreading." (no figure), with the first
  sentence of the lead carrying the example's figure: "For the house in our example below, about two thirds of the
  bill goes away."
- Line 9, "the lowest price per kWp of the three options, and a system that typically pays for itself in a few
  years, then keeps producing for twenty more." Severity Major, effort S. "per kWp" is the engineer's measure in a
  lead; "twenty more" is a life claim the profile cannot back (the panel performance warranty is blank) and the
  engine does not make (it counts 25 years of savings in total). Replacement: "No battery, so this is the lowest
  price of the three ways to go. The estimate counts your savings over 25 years." Example in section 6.

**How net metering works, in four lines (16–26).** Feeling: calm (it is simple, and we do the papers). Keep the four
bold step names. 22: gloss "generation rate" once ("the rate it pays for power, lower than the rate you pay") and
keep "That is why the bill shrinks but does not reach zero." (the honesty line). 23: keep "You sign two forms." and
"Between switch-on and the two-way meter the system already cuts your daytime bill." (a real gap, honestly stated).

**What the numbers usually look like (28–41).** Feeling: control (a real number before you ask). Keep the h2 (30),
the four tiles (33–36) and the small print (39) exactly; the test pins "7 panels", "installed, VAT included", "pays
for itself", "off the bill" and "500 kWh a month, mostly in the evening, net metering without a battery". The lead
(31) may add the feeling before the figures: "Every house is different, which is why the estimate asks for your
bill and your town. As a feel for the scale…" is already right; leave it or add one picture sentence after it. The
fifth tile (37) is profile-driven and hidden; do not touch it.

**No battery means no backup (43–49).** Feeling: honesty as calm (we tell you before you buy). Keep the h2 (45) and
"switches off during a brownout, as the safety rules require, and restarts on its own when the grid returns."
Change the second sentence to point at the comfort page with the feeling: "If brownouts are what keep you up at
night, read about solar with a battery; the estimate shows that price too, and a battery can be added later."
(The "added later" clause is already on the page; keep it, it is true of the hip-roof installation: "ready for a
battery".)

**The band (51–57).** Keep "Your bill, your town, one minute." (53) and "Booking the roof visit is optional." (54):
the no-pressure line is part of the relief.

Objections this page must pre-empt: "Is it worth it?" (the example: under four years), "What about brownouts?"
(the section), "How long before the two-way meter?" (the gap line), "Do I have to deal with the electric company?"
("You sign two forms.").

### 4.4 About (`site/pages/about.html`)

**The opening (7–10).** Feeling: calm, then pride. Picture: "we go to the house"; the test panel on the roof; the
systems that "never made what the brochure promised" (keep that complaint: it is the origin story and it is the
customer's own experience). Keep the h1 (8) or warm it without losing "measures before it designs"; keep the lead
(9, profile-driven). Line 10 is good; keep "So we do it the slow way." and "It can come out lower or higher than
the first estimate, and it shows you why."

**The photo (12–18).** The caption: section 5.

**Who you will meet (20–22).** Feeling: calm (a person, not a call centre). Keep 21 as is (profile-driven: "runs
the company and is on every roof visit and every proposal"). Keep 22's facts (the PEE from the profile; "installs
in one or two days and leaves the roof the way it found it, with sealed fasteners and no open holes"); you may put
the roof picture first ("The roof is yours; we leave it the way we found it…"). Do not add "answers the phone
afterwards" or any after-sales promise until the owner says who answers and how fast (section 7).

**How we work (31–37).** Feeling: control. Keep all four bold leads; 34 "Honest about the battery. A battery is
for brownouts and comfort; it adds little to the savings. We show both prices and let you choose." stays word for
word (it is the owner's rule in one line). 35 keeps the papers list; gloss the ERC certificate once.

**Where we usually install (39–40).** Keep as is (round 5 wording, the service area rule).

Objections this page must pre-empt: "Who are you?" (the owner, the PEE, the base, the three real roofs), "Will
you still be around?" (nothing to claim yet; the warranties printed from the profile are the only honest answer).

### 4.5 The frame (`site/layout.html`)

Keep the header tag line "Solar engineering for homes" (31; test-pinned, and it is the positioning). Keep the
footer's "Start here" paragraph (69) word for word: "Four questions, one minute, no sign-up. An estimate, not a
quotation; the free roof visit gives the exact figure." Keep "Talk to us" (57): with the owner's name and number
from the profile it is the human to call on every page. The nav labels stay. Nothing else to do here.

### 4.6 The estimate page frame and 404

`estimate.html`: the `noscript` line is customer copy and stays ("…message us on Messenger with your latest bill
and your town and we will work it out for you."). `404.html`: keep; line 8 "The link may be old. The estimate is
one click away." is already calm.

### 4.7 The estimate widget (`frontend/src/estimate/Estimate.tsx`): propose in the report, by string and line

The widget is the sale. It is already honest and in the customer's words in most places; the changes are few.

- **The heading (313) and the lead (315).** Today: "How much solar does your house need?" and "Four questions,
  about a minute. You'll see the system size, the price and what it saves each month. For an exact figure, we
  measure your roof. The visit is free." The heading asks the engineer's question. Propose: h1 "What would your
  bill be with solar?"; lead "Four questions, about a minute. You'll see your bill before and after, the price, and
  how many panels it takes. Nobody calls unless you book the free roof visit, which gives the exact figure."
  (True: the estimate asks no name.) docs/marketing.md's landing options were written for this heading; update the
  note there in the report, not in the file.
- **Question 1 (319, GOALS 18–20).** Keep the three titles exactly ("A lower bill"; "A lower bill, and lights in a
  brownout"; "Battery first, nothing sold back"). Keep the three texts: at the moment of choosing the visitor wants
  the fact, and card 3 on the home page quotes this text. Only "(net metering)" in text 18 may go, since the home
  card drops it; your call, state it in the report either way.
- **Questions 2–4 (329–410).** Already the customer's words ("Cooking, laundry, the pump and aircon early in the
  day."). Keep. The location hint (372–379) was just reworked by another session; leave it.
- **The result's hero (415–452).** "Your monthly bill ₱X → about ₱Y", "about ₱Z less each month…", "Pays for
  itself in", "Estimated price … installed, with permits, VAT included": this is relief and control in four lines;
  keep every word, including "a small bill" and the fixed-charges sentence (431–432).
- **The system line (458) and what it makes (461).** Keep. If you touch the label, "The system:" may become "What
  goes in:"; the figures stay because the reader asks for them.
- **The two prices (467–488).** Keep exactly "The battery is for brownouts; it adds little to the savings." (473).
  For the no-battery visitor (480), put the feeling before the figure: "Add a battery for brownouts: about ₱X more
  (N kWh, enough for a typical night of your use when the grid is down)…" instead of the kWh inside the bold label.
  The engine's phrase stays as the engine prints it.
- **The booking card (491–551).** Keep "Want the exact figure? The roof visit is free." (491) or "Want the exact
  figure? We come and measure. The visit is free." Keep the hint (514: "Most installers quote from a satellite
  photo…No cost, no obligation."), the field labels, "Book my free roof visit" (548, also the sticky bar 607),
  "Your name and a number or Messenger name are enough." (550) and the privacy line (profile-driven).
- **The thank-you (495–498).** Feeling: calm; picture: nothing more to do. Today the two paragraphs are right in
  facts and order. Propose: "Thank you, Maria. [Owner] will message or call you within one working day to pick a
  day; visits are usually within the week. Nothing more to do for now; keep a recent bill where you can find it."
  then "What happens next: the roof visit, about an hour and free; your roof check card the same evening; the
  energy audit over your bill and appliances; your proposal within two working days, valid 15 days." The owner's
  name, the promise and the validity stay profile- and setting-driven as they are. Keep "Open Messenger" (503) and
  "Copy my estimate" (507).
- **The copied summary (264–270).** Keep exactly: it is forwarded to the spouse and it already carries "This is an
  estimate, not a quotation." and "Run your own: pldevinc.com/estimate".
- **How we worked this out (564–595).** The engine's sentences; keep. 595 ("This is an estimate from your answers,
  not a quotation…") stays word for word.

## 5. Lines to keep exactly, lines that must go, and the installation captions

**Keep word for word (the honesty lines, the names, the pinned strings):**

- Header "Solar engineering for homes" (layout.html:31); eyebrows "How it works" (index:55), "What you get on paper"
  (index:69), "Our installations" (index:111); the photo file names and `alt` texts; all `data-profile` fallbacks.
- The three kinds' names on the home cards (index:35–36, 40–41, 45–46) and in the widget (Estimate.tsx:18–20).
- "No battery, so no power during a brownout." (index:37; Estimate.tsx:18).
- "The battery is for comfort, not savings, and we say so." (index:42); "The battery is for brownouts; it adds
  little to the savings." (Estimate.tsx:473); "Honest about the battery…" (about:34); "It buys comfort and backup
  more than savings" (brownouts:30).
- "It can come out lower or higher than the estimate, and it shows you why." (index:89; about:10).
- "Our own installations, photographed by us from the air. No addresses, no names." (index:113).
- The six FAQ answers' facts (index:165–185), especially "as the safety rules require", "You sign two forms.",
  "The system stays with the house…", "sealed fasteners… no open holes", and the whole "Is the estimate a
  quotation?" answer.
- The net-metering tiles and small print (net-metering:33–39); "That is why the bill shrinks but does not reach
  zero." (22); "No battery means no backup." (45).
- "Lights on, fans running, when the whole street is dark." (brownouts:8); "See both prices, with and without the
  battery." (52).
- The footer "Start here" paragraph (layout:69); "Get my free estimate" on every button; "Book my free roof visit".
- "This is an estimate, not a quotation." (Estimate.tsx:270, 595); the privacy page entire.

**Must go (ranked):**

| # | Sev. | Eff. | Where | What is wrong | Replace with |
|---|---|---|---|---|---|
| 1 | Critical | S | net-metering.html:8 | "down to a few hundred": the engine's own example says about two thirds off; the visitor's estimate contradicts the headline | "The bill you stop dreading." + lead sentence with the example's "about two thirds" |
| 2 | Major | S | net-metering.html:9 | "lowest price per kWp"; "keeps producing for twenty more" (no performance warranty in the profile; engine counts 25 years of savings) | "No battery, so this is the lowest price of the three ways to go. The estimate counts your savings over 25 years." |
| 3 | Major | S | brownouts.html:39 | "Lithium (LiFePO4) batteries, a hybrid inverter that works with the grid and the battery, and a two-way meter…" in the lead of the comfort page | Picture sentence; equipment moves to the ticks (43–44) |
| 4 | Major | S | brownouts.html:9; index.html:165 | "takes over the moment the grid drops": a transfer-time promise the owner has not given | "takes over by itself" until the owner answers |
| 5 | Minor | S | brownouts.html:9 | "And the bill still goes down every month." reads as the battery's doing | "and the panels still bring the bill down every month" |
| 6 | Minor | S | brownouts.html:30 | "a hybrid system's price" | "the price of solar with a battery" |
| 7 | Minor | S | index.html:58; Estimate.tsx:315 | "the system size, the price and what it saves" (engineer's order) | "what your bill becomes, the price, and how many panels it takes" |
| 8 | Minor | S | index.html:165; brownouts.html:22, 42; brownouts meta line 2 | "refrigerator"/"fridge", "wifi"/"Wi-Fi" mixed | "fridge", "Wi-Fi" everywhere |
| 9 | Minor | S | Estimate.tsx:313 | "How much solar does your house need?" is the engineer's question | "What would your bill be with solar?" |

**The three installation cards (index.html:121–142) and the About photo (about.html:17).** The heading stays the
fact (panels, kWp, roof); the paragraph's first sentence carries the feeling; every fact that is there today stays
after it; the `alt` texts stay literal and are not touched.

- Card 1, the rib roof (121–122). Feeling: relief, "a house like yours". Heading unchanged: "Eight panels, 4.56
  kWp, on a rib-type roof". Paragraph: "A typical family home's daytime bill, carried by eight panels. Two rows of
  four on rails fixed through the sheet to the roof framing, the panel cable in conduit. A 6 kW grid-tie inverter
  runs the house by day; no battery, not on net metering. Installed early 2026." ("daytime bill" is what a grid-tie
  system without net metering does: it runs the house by day. Do not say what the bill became; nobody has said.)
- Card 2, the hip roof (131–132). Feeling: pride ("a roof with no single big face still carries a full system")
  and comfort to come ("ready for a battery"). Heading unchanged. Paragraph: "No single big face to this roof, and
  it still carries a full system: sixteen panels in three groups on three faces, each on its own rails, the cables
  in conduit. A 12 kW hybrid inverter, ready for a battery the day the family wants one; no battery yet, not on net
  metering. Installed early 2026."
- Card 3, the three roofs (141–142). Feeling: comfort through brownouts, relief on the bill, three years in.
  Heading unchanged: "13.75 kWp with a 30 kWh battery, across three roofs". Paragraph: "Three years in: a 30 kWh
  battery for comfort through the brownouts, and more than ₱33,000 of credit built up on the bill. Net metered
  since 2023. Photographed at nine in the morning, when the palms still shade part of the main array; the design
  carries extra panels so the shade costs little." ("for comfort" states the battery's purpose; do not write "the
  lights never went out": nobody has told us what their brownouts were like.)
- About (17). Same facts, the calm angle: "Three roofs, one property, coconut palms: the kind of roof we measure
  before we design. 13.75 kWp with a 30 kWh battery, net metered since 2023, more than ₱33,000 of credit on the
  bill." (The first clause is the process claim the site makes about the company, not a claim that this roof was
  measured with the test panel; keep it in that form.)

## 6. Three paragraphs in the register

**A hero paragraph (index.html:9–10).**
> **See what solar would do to your bill.**
> Picture the bill arriving and nobody minding. Type in your bill and your town, and a minute later you know what
> solar would cost at your house and what the bill would become. Free, no sign-up, nobody calls unless you ask.
> Then, if you like the number, we come to the house, put a test panel on the roof and measure, so the proposal is
> exact. No cost, no obligation.

(Relief in the first sentence, the pipeline's promise in the second, calm in the fourth; every fact is one the
page already makes. "Nobody calls unless you ask" is true because the estimate asks no name.)

**A battery paragraph (brownouts.html:22, the "In a brownout" card).**
> The whole street goes dark; in your house the battery takes over by itself. The fan keeps turning, the fridge
> stays cold, the children finish their homework with the lights on, and the Wi-Fi stays up for whoever is working
> from home. We size the battery to the evening you want to keep: lights, fans, fridge, TV and Wi-Fi through a
> typical night; running aircon shortens that, and we say so. Your estimate tells you whether yours holds a typical
> night or how many hours of your evening it carries.

(Comfort first, the engine's two phrasings last, the aircon caveat kept; "by itself" and not "the moment".)

**A net-metering paragraph (net-metering.html:8–9, the hero).**
> **The bill you stop dreading.**
> For the house in our example below, about two thirds of the bill goes away. By day the panels run the house, and
> what you do not use goes out through the meter and comes back as credit on your bill. The bill still arrives; it
> just stops being the thing you dread at the end of the month. No battery, so this is the lowest price of the
> three ways to go. For that house the panels pay for themselves in under four years, and the estimate counts your
> savings over 25 years.

(Relief, then the mechanism in the customer's words, then control; "about", "under four years" and "25 years" are
the engine's; nothing about "twenty more years".)

## 7. What to ask the owner (a stronger page needs these; do not write around them)

1. The inverter's switch-over time in a brownout, from the maker's sheet (milliseconds or seconds). With it, the
   comfort page can say "the fan keeps turning" as a fact; without it, "takes over by itself" is the ceiling.
2. Who answers after switch-on, and how fast (the owner's own number? a working day?). With it, About and the FAQ
   get the after-sales line every comparing buyer asks for.
3. The mounting system's rated wind speed from the maker's datasheet, and whether the PEE designs to the NSCP wind
   zone. With it, one typhoon line in the FAQ; without it, none.
4. How long the power is off at the panel board on installation day (the proposal's `installation_outage_hours`).
   With it, "How it works" step 5 can say "your power is off for about an hour on the second morning".
5. The panel performance warranty years (profile field blank). With it, the net-metering page's fifth tile appears
   by itself and "then keeps producing for N more years" becomes sayable.
6. For the three photographed homes: whether each customer agreed to one sentence about their experience (the
   three-roof family's brownouts; the hip-roof family's reason for the hybrid inverter). A yes gives the site its
   first real voice; without it, pictures only.
7. The towns, when the customers agree (round 5, still open); the cards carry none until then.

## 8. What I will check line by line in step 3

Every number and fact the pages carry today is still there, or the brief says it goes. No new figure, town, brand,
date, warranty year or customer voice. "About" before every savings figure. The battery sentence in every place it
appears still says comfort and backup, not savings, and attributes the saving to the panels. The three names
unchanged in both places. "Your electric company" everywhere. The hooks, ids and classes untouched (`python
site/build.py` and `pytest -q tests/test_site.py` pass). The feeling leads each section and the fact follows; no
exclamation marks; "fridge" and "Wi-Fi" one way. The thank-you still promises the owner's message, the card the
same evening, the proposal in two working days, the validity from the setting.

## 9. Summary for the coordinator

1. Ranked by lost sales: the estimate result and thank-you, Home, Brownouts, Net metering, About, the frame, 404; the copywriter works Home → Brownouts → Net metering → About → frame → 404 and hands the widget texts over by file and line.
2. The leading feeling per page: Home relief (calm under it); Brownouts comfort; Net metering relief; About calm then pride; the estimate result control then relief; the thank-you calm ("nothing more to do now").
3. The register is picture, fact, step, in that order, in every paragraph; feeling words describe the customer's life, never the product; the equipment is one plain sentence after the picture.
4. One Critical line must go: net-metering.html:8 "A bill of thousands, down to a few hundred" (the engine's own example says about two thirds); replacement "The bill you stop dreading." with the example's figure in the lead.
5. Three Major lines: net-metering.html:9 ("per kWp", "twenty more" years); brownouts.html:39 (LiFePO4, hybrid inverter, two-way meter in the comfort page's lead; moves to the ticks); "the moment the grid drops" (brownouts:9, index:165) softened to "by itself" until the owner gives the transfer time.
6. Keep word for word: the three kinds' names in both places, every battery honesty line, "It can come out lower or higher…", the installations lead, the six FAQ facts, the net-metering tiles and small print, the footer's "An estimate, not a quotation", the widget's "not a quotation" lines, the test-pinned eyebrows and tag line.
7. The captions: card 1 "A typical family home's daytime bill, carried by eight panels…"; card 2 "No single big face to this roof, and it still carries a full system… ready for a battery the day the family wants one"; card 3 "Three years in: a 30 kWh battery for comfort through the brownouts, and more than ₱33,000 of credit…"; About "the kind of roof we measure before we design"; every existing fact kept, alt texts untouched.
8. Widget proposals (coordinator applies): h1 "What would your bill be with solar?" and the lead in the customer's order; the battery add-on line puts "for brownouts" before the kWh; the thank-you adds "Nothing more to do for now; keep a recent bill where you can find it." and heads the path "What happens next:"; everything else stays.
9. Must-not list enforced: no guaranteed savings, financing, utility name, town, transfer time, typhoon rating, battery life, panel life, performance guarantee, customer quote; a battery sells comfort and backup, the panels bring the bill down.
10. Seven owner questions would unlock the next tier of copy: the inverter's switch-over time, who answers after switch-on, the mounting wind rating, the installation-day outage length, the panel performance warranty years, one agreed sentence from each photographed family, and the towns.
