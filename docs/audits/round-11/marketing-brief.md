# Round 11, marketing: the hook

From the marketing and sales specialist to the copywriter, 10 October 2026. Read against `claude/wonderful-maxwell-wawb8t`
at d8f3f31: the site built from that commit into my scratch folder and served on 127.0.0.1:8216 (now stopped),
measured on a 390 × 844 phone and a 1280 × 800 desktop (`r11/phone-first.png`, `r11/desk-first.png`, `r11/shot.js` in
`/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/marketing/`). Line numbers are
`site/pages/index.html`, `site/layout.html`, `site/partials/proof.html`, `docs/marketing.md` at that commit. Facts: the
round-7 brief, the engine's own example (a house in Tanauan, Batangas using about 500 kWh a month, panels only: 4.1 kWp,
7 panels, about ₱193,000, under four years, about two thirds off; the same house as a ₱5,000 bill: ₱5,003 → about
₱1,460, 4.0 years, run 9 October, `docs/marketing.md:112–114`), nothing more. The measurements that bound the words: at
390 px the h1 is 33 px and wraps at about 19 characters, so three lines is about 55 characters; the lead is 17 px at
about 40 characters a line, so four lines is about 160; the eyebrow holds about 34 characters on one line.

## Why the first screen does not hook

Today a visitor from a Facebook link sees, in order (`phone-first.png`): the header, eight panels on a rib roof in
daylight, "HOME SOLAR IN THE PHILIPPINES" at 399 px, "The bill goes down. With a battery, the lights stay on." in three
lines at 431–545, a four-line lead ending "A minute here shows you the price and your new bill." at 559–665, the gold
button at 685–741, then two of the four ticks. The eyebrow is a category label, not a reason to stop. The h1 promises
two outcomes every installer's page promises, with no "before" to make the "after" mean anything, no figure to
disbelieve, no face or dark street to feel, and nothing that is lost by scrolling on. The lead restates the h1 with the
mechanism and reaches the one true pull, "your new bill in a minute", in its fourth line. The photo shows the product,
not the outcome. Every number the site owns that could stop a thumb (₱33,000+, 2023, 500 kWh → about two thirds off,
under four years) begins at 969 px, under the fold. A hook is a specific, checkable gap: a figure the visitor wants to
be true for his own house and can close in the next minute. The first screen has the minute and the house; it has no
figure.

## 1. Five candidate hooks

Each: eyebrow / h1 / lead, then the feeling, the proof, the objection pre-empted, and the risk (what a sceptical Laguna
homeowner says back). Every figure is the engine's or the record's; no deadline, no scarcity, no superlative.

### A. The number (the engine's example, the bill in the drawer)
Eyebrow `Home solar, sized to your bill`. h1 `A ₱5,000 bill, down to about ₱1,500.` (37 characters, two lines at 390).
Lead `Our estimate for a house in Tanauan using about 500 kWh a month, panels only. Pays for itself in about four
years. Yours takes a minute.`
Feeling: disbelief turning into "what is mine?", relief with a number on it. Proof: the engine's example, through the
same calculation that prices the proposal (about.html:76); the net-metering tiles (4.1 kWp, 7 panels, about ₱193,000,
under 4 years, about two thirds); the strip's first tile (₱33,000+ of credit on one bill since 2023) directly under
it. Objection pre-empted: "how much, really?" and "for a house like mine?" (the kWh and the town are named). Risk:
"my bill is ₱3,000, not ₱5,000" (answered by "Yours takes a minute"); "every installer says that" (this one is dated,
sized and placed); "says who?" (the same calculation prices the proposal, and the strip's credit is the electric
company's figure). Maintenance: the figure is today's prices; it must be re-run with the net-metering tiles whenever
the price list or the tariff moves (the small print at net-metering.html:48 already carries that liability).

### B. The record (the 2023 installation's credit)
Eyebrow `On net metering since 2023`. h1 `₱33,000 of credit on one electric bill, since 2023.` (49 characters).
Lead `A 2023 installation in Pila, Laguna runs the house by day and sends the extra back through the meter; the
electric company has credited more than ₱33,000 since. See what your own bill would become, in a minute.`
Feeling: aspiration, the bill that owes you. Proof: the electric company's own print on the bill; three typhoon seasons
stood. Objection pre-empted: "does net metering really pay here?" Risk: the sceptic divides ₱33,000 by the months and
says "₱1,000 a month, is that all?" (the credit is what the roof sent back on top of running the house, not the
saving, and a headline cannot carry that distinction); "that is a 13.75 kWp roof on three faces, mine is one"; and the
bill itself cannot be shown on the site today, so the headline claims a document the visitor cannot see.

### C. The dark street (the brownout picture the site already uses)
Eyebrow `Solar with a battery`. h1 `The street goes dark. Your windows stay lit.` (44 characters).
Lead `The battery takes over by itself: fridge, fans, Wi-Fi and lights through the evening; by day the panels bring
the bill down. Your two prices, with and without it, in a minute.`
Feeling: comfort and relief, with the tension built in (dark street, lit windows). Proof: the 2023 installation runs
through brownouts (index.html:78); the hybrid inverter switches by itself (brownouts.html:77); the estimate's battery
note per house. Objection pre-empted: "what happens in a brownout?" Risk: it is already the Brownouts page's own hook
(brownouts.html:17–18), so the home page would repeat a page one click away; it narrows the door to the battery buyer
while the price roughly doubles with the battery (in my round-8 walk, ₱180,000 → ₱308,000 for the same 400 kWh
house), so the no-battery buyer with the strongest numbers reads "not for me"; "for how long, with the aircon on?"
(only the estimate may answer, per house); and there is no photo of a lit house on a dark street, so the hero would
show panels in daylight under a night headline.

### D. The satellite photo (the quote from a picture)
Eyebrow `Measured before it is priced`. h1 `A quote from a satellite photo is a guess. We measure.` (54 characters).
Lead `A test panel and meters on your roof read the sun and the shade, so the proposal is exact to your house. Start
with the free estimate: your new bill in a minute.`
Feeling: distrust of the others turned into trust; control. Proof: the method (the test panel, the meters); the
engineer's seal; one calculation from estimate to proposal. Objection pre-empted: "why would your figure be right?"
Risk: it opens on a why-us before the visitor has a want; "a guess" is a fight picked with competitors in the headline
(index.html:126 says the same thing calmly, where it belongs); a Laguna buyer may not know other quotes come from a
satellite photo, so the contrast lands flat; "test panel" sounds like a delay; and it carries no number.

### E. The typhoon seasons (the record of the fixing)
Eyebrow `Engineered, sealed and filed`. h1 `Standing since 2023, through every typhoon season.` (49 characters).
Lead `Rails fixed through the sheet to the roof framing, plans sealed by a Professional Electrical Engineer, the permit
and the net metering papers filed by us. Your new bill in a minute.`
Feeling: safety and calm about the roof; pride in an engineered job. Proof: the 2023 installation; the fixing; the
seal. Objection pre-empted: "will it leak, will it fly?" Risk: it opens on a fear the visitor has not voiced instead
of the want he came with; three seasons is a short record to headline; every roofer claims the typhoon; the FAQ
(index.html:191–192) already answers it where it is asked.

## 2. The pick: A, the number

The reason: it is the only candidate with a figure the visitor can disbelieve and then check, on the same page, in the
next minute, so the hook and the button are one motion. It is universal (every visitor has a bill; the dark street is
the battery buyer's), it needs no data the owner has not supplied (the engine's example is already on the net-metering
page, so it adds no claim), and it threads straight through the funnel the rounds have built: the hero says "a ₱5,000
bill, down to about ₱1,500", the button says "See my new bill", the estimate's h1 says "Your new bill is a minute
away.", the result says "Your monthly bill ₱4,803 → about ₱199", the sticky bar says "Your new monthly bill". The other
four do not go away: B is the proof under the hook (the strip's first tile), C stays the Brownouts hook and the second
home card, D stays at How it works (index.html:125–126), E stays in the FAQ. The site then says one thing: the bill,
before and after, and a minute to see yours.

Rails on the pick: "about" on the after-bill and the payback; "for a house using about 500 kWh a month"; Tanauan
named; "panels only"; never "your bill will", never the ₱5,000 without the 500 kWh beside it; no utility name; no
exclamation mark; the only FOMO is "another month at the old bill". The h1's figure is the engine's at today's prices:
whenever the price list or the tariff moves, re-run the 500 kWh Tanauan estimate and update, together, index.html:1,
:13, the description, net-metering.html:18 and its tiles, and the ad line.

### The exact words, every place the hook lives

**Home hero (index.html:12–16)**
- 12, eyebrow: `Home solar, sized to your bill` (30 characters, one line). The `data-profile="service_area"` span
  moves to the lead's last sentence (below); if the lead then runs five lines at 390, drop "anywhere in …" from the
  lead and put the span in the band's paragraph instead. Fallback if the coordinator wants the eyebrow untouched: keep
  `Home solar in <span data-profile="service_area">the Philippines</span>` and change only the h1, lead and button.
- 13, h1: `A ₱5,000 bill, down to about ₱1,500.`
- 14, lead: `Our estimate for a house in Tanauan using about 500 kWh a month, panels only. Pays for itself in about
  four years. Yours takes a minute, anywhere in <span data-profile="service_area">the Philippines</span>.` (about 160
  characters, four lines at 390; verify at build.)
- 16, button: `See my new bill` (the thread's word; "free" moves to the sticky bar's text and the band). The four
  ticks (19–22) stay: the record, the test panel, the seal, the papers are the four proofs under the number.

**Sticky bar (layout.html:78–80)**: `<div class="sticky-text"><b>Your new bill</b>Free, in a minute.</div>` and the
button `See my new bill`. The header's nav button (layout.html:39) stays `Free estimate` (a navigation label, and it
keeps the word "free" on every screen). The footer's "Start here" button (layout.html:68) becomes `See my new bill`;
its paragraph (69) stays.

**Title, meta description, share snippets**: `og:title` and `og:description` are templated from each page's comments
(layout.html:9–10), so nothing changes in layout.html. index.html:1 → `<!-- title: A ₱5,000 bill, down to about
₱1,500 · PL Development Inc. -->`; index.html:2 → `<!-- description: A ₱5,000 bill, down to about ₱1,500: our estimate
for a house in Tanauan using about 500 kWh a month, panels only, paid back in about four years. Rooftop solar for
homes anywhere in the Philippines, measured on your own roof before we quote. Four questions, one minute, free, no
sign-up. -->`. The og:image and its alt (the rib roof) stay. estimate.html:1 → `<!-- title: Your new bill in a minute ·
PL Development Inc. -->` (its description stays). 404.html:8, optional: `Your new bill is right here, one minute,
free.`

**Proof strip (proof.html:3–6)**: the order stays (₱33,000+, 2023, 3, 1). The hook leans on the engine's example,
which is not a tile; the first tile is its third-party proof and already leads. No label changes.

**Band at the foot of the home page (index.html:206–210)**: h2 `Your new bill is a minute away.`; p `Your bill, your
town, when you use power. Every month you wait is another month at the old bill, and the only call you get is the
one you book.`; button `See my new bill`.

**docs/marketing.md**
- 106–110, ad angle 2, the quoted copy → `A ₱5,000 bill, down to about ₱1,500: our estimate for a house using about
  500 kWh a month, panels only, paid back in about four years. See your own number in a minute, free.` ("then runs for
  20 more" goes: a life claim the facts do not carry.) The note at 112–114 (re-run on the day you post) stays and now
  also governs the hero.
- 99–104, ad angle 1 (the brownout) stays as written: it lands on /brownouts, whose hero is candidate C.
- 116–120, ad angle 3 stays.
- 122–126, the landing-page headline options → `A ₱5,000 bill, down to about ₱1,500. Yours takes a minute.` and `Your
  new bill is a minute away.`; the parenthetical becomes "(the estimate page's own heading is "Your new bill is a
  minute away.")". The Messenger templates (the posts after a booking) are untouched; the three ad angles double as
  the post copy.

**Other pages' heroes**: net-metering.html:18 echoes the number so both pages carry the same example: `In our example
below, a ₱5,000 bill comes down to about ₱1,500, about two thirds off. By day the panels run the house; the extra comes
back as credit on your bill. Panels and inverter only: the lowest price of the three ways to go.` (its h1 "The bill you
stop dreading." and the tiles stay; the pinned small print stays). brownouts.html, about.html: no change; the Brownouts
hero is candidate C for the battery audience and the About h1 is the company's.

## 3. What stays, and what the owner would have to supply

Stays, and why: the rib-roof photo (the only real hero photo; a night photo would unlock C); the four ticks (the proofs
under the number); the proof strip and its order; the three wants cards (the feeling lines that follow the number);
"We measure your roof before we price it." and its lead (candidate D, in its place); the FAQ's typhoon answer
(candidate E, in its place); the Brownouts hero (candidate C, for its audience, and ad angle 1 lands there); the
net-metering tiles (the hook's source, with the dated small print where the liability lives); the estimate widget's
h1 "Your new bill is a minute away." and its sticky "Your new monthly bill" (the thread already runs through them).

To make a stronger hook possible, in order of value:
1. A before-and-after bill from the 2023 installation (two bills, account details covered, the electric company's
   print visible). No before-and-after exists on record today, and the ₱33,000 credit is not one; a real "₱X → ₱Y" as
   the electric company printed it would replace the engine's example as the h1 and is the strongest hook this site
   could carry. Owner to confirm it exists and may be shown.
2. A photo of a lit house on a dark street (one of the installations during a brownout, from the street or the air):
   unlocks candidate C as the home hero's image and headline, which is the only hook with a picture in it.
3. The inverter's switch-over time from the datasheet: unlocks "the fan does not even stop" under C and on Brownouts.
4. Settings › owner's name, phone and Messenger: a human within reach of the hook (the footer's "Talk to us" is
   hidden while they are blank).
5. The date and price list the ₱5,000 example was last run on, kept with the site: the rule for re-running the h1's
   figure, so the hook never outlives its price.
