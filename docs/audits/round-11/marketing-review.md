# Rounds 10 and 11, marketing: the closing block and the hook, line by line

From the marketing and sales specialist, 10 October 2026. Read-only: nothing in the repository was changed. Read as the
customer reads it, on `claude/wonderful-maxwell-wawb8t` at cf88713 (37fb163 plus the hero's three lines, which the owner asked for after the four ticks: "These for me are too random to be there and doesn't makes sense."): the built site (`site/dist`, served on
http://127.0.0.1:8218, where the profile fetch 404s and only hides the profile spans) and the widget on a private server
(http://127.0.0.1:8219, `frontend/dist` as built, a scratch database, the real sun records), at 390 × 844 and 1280 × 900.
Walked: the home page's first screen, the band, the sticky bar, the footer, the header, the Brownouts, About and Net
metering heroes and bands, the 404, the estimate page's title; the widget's result for the battery goal at 400 kWh mostly
evening, the lower-bill goal and the battery-first goal, each with the alternative through its link, the closing block, the
booking card under it as the viewport shows it, one booking under a made-up name, the thank-you and the copied summary.
Scripts `shot11.js` and `walk10.js`, the screenshots `phone-*.png` / `desk-*.png`, the recorded texts `*.json` and both
server logs are in `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/review11/`. Line
numbers are the files' at cf88713 (`site/pages/index.html`, `site/layout.html`, `site/pages/net-metering.html`,
`site/pages/404.html`, `site/pages/estimate.html`, `docs/marketing.md`, `frontend/src/estimate/Estimate.tsx`); every line is
quoted, so cite by string if they move. Checked against the round-11 brief (mine), the round-7 facts, the engine's own run
through the API, the two copywriter reports and the owner's two rulings: "it should be what am I missing if I don't go
contact them? We sell FOMO here." and the visit yields the proposal only, never a roof check card or any reading.

Verdict on each changed line: **accept**, **change to** (exact text), or **must go**. 35 changed lines: 32 accept, 3 change
to, 0 must go. Two further asks on lines the rounds did not touch, where the funnel's thread shows a seam (part 3).

---

## What was verified before the lines

- **The hook's figures are the engine's.** The API on 8219 for `net_metering`, Tanauan, Batangas, 500 kWh, mostly evening,
  today's price list and tariff: bill before ₱6,003.29, after ₱1,893.36, saving about ₱4,110 a month, payback 3.84 years,
  7 panels, 4.095 kWp, ₱193,000, 68.5% off. So "A ₱6,000 bill, down to about ₱1,900." (both to the hundred), "about four
  years", and the net-metering tiles' "4.1 kWp / 7 panels / about ₱193,000 / under 4 years / about two thirds" are one run.
  The brief's ₱5,000 → ₱1,500 was a peso-amount run the widget no longer takes; the copywriter was right to re-run and
  right to change the figure rather than the house. The evening pattern is the most conservative of the three for this
  house (morning gives about ₱1,325 after, spread ₱1,487), so the hook understates rather than overstates.
  `tests/test_site.py` 12 passed on the branch, `test_home_hero_figures_match_the_engine` among them.
- **"About", the house and "panels only" beside the figure.** "about" before the after-bill and the payback in the h1, the
  lead, the title, the description, the net-metering lead, the ad line and both landing headlines. The house ("a house in
  Tanauan using about 500 kWh a month") and "panels only" sit beside the figure in the lead, the description (the share
  card's text under the og:title), the net-metering lead ("In our example below…", with the tiles, "Panels and inverter
  only" and the pinned small print) and the ad line. Two places carry the bare figure: the browser title (acceptable: a
  title, and on Facebook the description sits under it) and the first landing headline in `docs/marketing.md` (change 2).
- **No overreach on the home page.** A sweep of the built page's text: no "!", no "guarantee", no "will", no "best",
  "cheapest", "always"; "lowest" once, in the installations' "the lowest price of the three ways to go" (the company's own
  three offers); no "limited", "slots", "today only", "hurry", "deadline"; no utility name; no "our own" or "our home"
  (round 9 holds). The only urgency line on the site is the band's "Every month you wait is another month at the old
  bill". No "your bill will" anywhere (pinned).
- **The first screen at 390 × 844** (`phone-first.png`): header, the rib roof, the eyebrow one line at 399–421, the h1 two
  lines at 431–507 (33 px), the lead four lines at 521–627, the gold button at 647–703, then the three lines under it,
  the last ending about 820, all inside the 844 px screen; no overflow. At 1280 × 900: eyebrow one, h1 two, lead three,
  the button at 435–491, the three lines and the proof strip (₱33,000+, 2023, 3, 1) inside the first screen. The sticky bar appears after the hero with "Your new bill / Free, in a
  minute. / See my new bill" (`phone-sticky.png`).
- **The closing block, three goals, both branches.** Five items on every result that returns economics (the money line
  guarded by a positive saving; at 60 kWh it prints "about ₱629 a month", never a zero or a minus); the battery-first branch
  drops the net metering papers and the two-way meter; the panels-only branch carries the "if you want the lights on"
  battery line. "assessment" three times on the result, all "on-site assessment"; no "roof check" in the widget bundle, on
  any customer page of the built site (only the privacy notice's list of records kept), or in the thank-you; no scarcity,
  deadline, price-rise or competitor word; no exclamation mark; no page overflow; no console error in five walks.
- **The honesty lines, still inside the sentences.** "about" and "by this estimate" on the block's money line; "This is an
  estimate, not a quotation" word for word in the foot and the summary; the hero's "what still comes" lines as merged in
  round 8; the battery note in the engine's form; the one-visit promise ("Book my free on-site assessment" on the hero
  button, the form button and the sticky bar; "one free visit"; "the only call you get is the one you book").
- **The thread, end to end** (part 3): "See my new bill" → the widget's "Your new bill is a minute away." (in the current
  bundle) → "Your monthly bill ₱4,803 → about ₱199" → the sticky "Your new monthly bill / about ₱199" → "What you miss if
  you stop here" → "The exact figure is one free visit away." → "Your on-site assessment is booked, Maria." → the summary.

---

## Part 1. The hook (round 11)

**Does the first screen hook, on a phone from a Facebook link?** Yes, and for the reason the brief picked it: the visitor
who tapped an ad about a bill lands on a bill, before and after, with a house he can measure his own against (Tanauan,
500 kWh, panels only), a payback he can disbelieve, and a button that promises his own figure in the same minute. The
eyebrow tells him why the figure might be his, and the three lines under the button answer the three things he asks
before his thumb moves: what it costs him to find out ("Free, one minute, no sign-up"), whether he will be hassled ("The
only call you get is the one you book"), and why this number would be right for his roof ("Measured on your roof before
we quote"). On the desktop the strip's ₱33,000+ is the third-party figure directly under them. Nothing on the screen is
a claim the engine or the record does not carry.

**The three lines: three, or none?** Three, and these three. The four ticks were proofs (the record, the seal, the
papers), which is the strip's job one screen down and the owner was right that under a bill figure they read as a list
from somewhere else. These are not proofs but the terms of the offer the button makes, in the hook's own order (cost,
call, method), and each is a line the funnel already keeps: the footer's "no sign-up", the band's and the widget's "the
only call you get is the one you book", How-it-works' "We measure your roof before we price it." With none, the first
screen would end on the button with "free" nowhere on it (the ad copy says free; the landing should say it back) and the
objection "they will call me" unanswered until the band. The first line also withdraws the change I had drafted for the
lead ("Yours takes a minute, free."): with "Free" the first word under the button, the lead is right as it stands. One
note, not a change: on the desktop the third line and the strip's fourth tile both end "before we quote" in the same
screen; the tick is the promise and the tile is the count, and I would leave both.

**"Home solar, sized to your bill": does it earn the eyebrow?** Yes. The old eyebrow was a category label; this one is
the category plus the one differentiator the h1 then proves (a bill figure, for a stated kWh). "Sized to your bill" is
also the site's own method line (the Brownouts tick, the kWh card's hint), so it is a promise the funnel keeps. Moving
the service-area span to the band cost nothing: the band's "anywhere in the Philippines" and the footer carry it.

**The band's "Every month you wait is another month at the old bill": the right FOMO?** Yes. It is the only honest form of
urgency this site can carry: the cost of the status quo, true by definition, with no deadline, no slot, no price rise and
no competitor. It sits after the FAQ, where the visitor who read everything is deciding, and the clause after it ("the
only call you get is the one you book") takes the pressure off again. Nothing on the page overreaches.

### The changed lines

| Line | Element | Text | Verdict |
|---|---|---|---|
| index.html:1 | title | A ₱6,000 bill, down to about ₱1,900 · PL Development Inc. | accept (the figure travels alone here, but the share card and the tab both show the description with it) |
| index.html:2 | description | A ₱6,000 bill, down to about ₱1,900: our estimate for a house in Tanauan using about 500 kWh a month, panels only, paid back in about four years. Rooftop solar for homes anywhere in the Philippines, measured on your own roof before we quote. Four questions, one minute, free, no sign-up. | accept (the house, "panels only", "about", "free" all in the Facebook snippet) |
| index.html:16 | eyebrow | Home solar, sized to your bill | accept |
| index.html:17 | h1 | A ₱6,000 bill, down to about ₱1,900. | accept (two lines at 390; the engine's own figures, pinned) |
| index.html:18 | lead | Our estimate for a house in Tanauan using about 500 kWh a month, panels only. Pays for itself in about four years. Yours takes a minute. | accept (four lines at 390; I had drafted "Yours takes a minute, free." while the first screen carried no "free"; the first of the three lines now does, so the lead stands) |
| index.html:20 | hero button | See my new bill | accept (the thread's word, into the widget's "Your new bill is a minute away.") |
| index.html:23 | line 1 under the button | Free, one minute, no sign-up | accept (the cost of finding out, answered first; "no sign-up" is the footer's and the description's own phrase) |
| index.html:24 | line 2 | The only call you get is the one you book | accept (the objection a Facebook lead has before any other; the band and the widget's lead say it again, which is right) |
| index.html:25 | line 3 | Measured on your roof before we quote | accept (the method, in the words of How it works; two lines at 1280 in its column) |
| index.html:208 | band h2 | Your new bill is a minute away. | accept |
| index.html:209 | band p | Your bill, your town, when you use power. That is all it takes, anywhere in [the Philippines]. Every month you wait is another month at the old bill, and the only call you get is the one you book. | accept (the span's new home; the one urgency line, with its release) |
| index.html:210 | band button | See my new bill | accept |
| layout.html:68 | footer button | See my new bill | accept |
| layout.html:79 | sticky text | Your new bill / Free, in a minute. | accept |
| layout.html:80 | sticky button | See my new bill | accept |
| 404.html:8 | lead | Your new bill is right here, one minute, free. | accept (see part 3 for its button) |
| estimate.html:1 | title | Your new bill in a minute · PL Development Inc. | accept |
| net-metering.html:18 | lead | In our example below, a ₱6,000 bill comes down to about ₱1,900, about two thirds off. By day the panels run the house; the extra comes back as credit on your bill. Panels and inverter only: the lowest price of the three ways to go. | accept (six lines at 390 under a two-line h1; the tiles and the dated small print under it carry the house) |
| marketing.md:108–110 | ad angle 2 | A ₱6,000 bill, down to about ₱1,900: our estimate for a house in Tanauan using about 500 kWh a month, panels only, paid back in about four years. See your own number in a minute, free. | accept ("then runs for 20 more" gone, rightly) |
| marketing.md:112–120 | the note | The figures are the engine's for a house in Tanauan using 500 kWh a month, mostly evening, net metering without a battery (10 Oct 2026: ₱6,003 → about ₱1,893 a month, 3.8 years, 7 panels, ₱193,000): the same run as the net-metering page's tiles and the home page's h1, and `backend/tests/test_site.py` pins the hero, the net-metering lead and this line to it. When the price list or the tariff moves, re-run it and update … together; run it again on the day you post the ad and keep "about". | accept (the brief's fifth ask, met in words and in the test) |
| marketing.md:128–129 | parenthetical | (the estimate page's own heading is "Your new bill is a minute away.") | accept |
| marketing.md:131 | landing headline 1 | "A ₱6,000 bill, down to about ₱1,900. Yours takes a minute." | **change to**: `"A ₱6,000 bill, down to about ₱1,900, panels only, for a house using about 500 kWh a month. Yours takes a minute."` Reason: this is the one line the owner would paste as a headline on its own, and the brief's rail is that the figure never travels without the house and "panels only". The test's assert `f"{hook}. Yours takes a minute."` becomes `f"{hook}, panels only, for a house using about 500 kWh a month. Yours takes a minute."`. S. |
| marketing.md:132 | landing headline 2 | "Your new bill is a minute away." | accept |
| test_site.py:260–280 | `test_home_hero_figures_match_the_engine` | (code: the h1, title, description, lead, net-metering lead and ad line derived from the engine's run) | accept, and the best thing in the round: the hook can no longer outlive its price |

## Part 2. The closing block (round 10)

**Does the loss framing land, or read as pressure?** It lands. Each of the five lines is a fact about the status quo
read from the side where nothing has been done: the money the hero said stays in the pocket keeps leaving; the roof is
unmeasured so the exact figures are unknown; the battery is sized to a typical house until the appliances are on the
table; nobody is filing anything; the calendar is empty. None names a slot, a deadline, a rising price or another
installer; the money line carries "about" and "by this estimate"; the heading is the owner's own question in the
visitor's moment. The "no… no… no…" of the fourth and fifth lines does pile up on a phone (the block runs some 1,300 px
at 390, `phone-combination-400-visit.png`), but it is the owner's ask and the lines are short. The one line that could
read as a push is the panels-only battery line (a battery the visitor did not ask for, in a list of what he misses); it is
conditional ("if you want the lights on in a brownout") and the alternative line above it already showed the price, so I
let it stand.

**Is the safety valve placed right?** Yes: "The visit is free, and nothing is decided until you say so" opens the closing
paragraph, immediately after the fifth "no" and before the ask, so the reader who felt the pile-up gets the release
before he is asked for anything; then the sentence lands on the button and names the proposal as the one thing the
visit leads to (the second ruling, kept everywhere: the block, the thank-you, the summary, the foot, the home steps). The
booking card's "You decide after." eight lines below is not a redundancy: the sticky bar's button lands a reader on the
card without the block, and the form needs its own valve at the moment a name is typed. Keep both. The one thing the
close gets wrong is a date: "within two working days" reads, from "book it below", as two days from booking; the
thank-you says the visit is usually within the week and the proposal two working days after it (change 3).

### The changed lines (`frontend/src/estimate/Estimate.tsx`)

| Line | Element | Text | Verdict |
|---|---|---|---|
| 443 | h3 | What you miss if you stop here | accept |
| 444 | lead | Close this page and nothing changes. Next month's bill comes as it does today, and this estimate stays a typical roof's, not yours. What you are left with: | accept (the strongest sentence in the block, and true) |
| 446 | the money | about ₱4,604 a month, by this estimate, paid to your electric company instead of kept in your pocket · panels only: about ₱3,551 · battery first: about ₱4,803 | accept (the hero's own figure turned around; printed only when positive) |
| 447 | the roof | a roof nobody has measured for the panels it holds and the shade on it, so the exact price and the exact bill stay unknown | accept (the two unknowns named are the two the proposal delivers; nothing from the visit is promised) |
| 448 | the battery, with one | a battery sized to a typical house, not to your fridge, fans, Wi-Fi and aircon, until your appliances are on the table | accept |
| 448 | the battery, panels only | a battery, if you want the lights on in a brownout, sized to a typical house until your own fridge, fans, Wi-Fi and aircon are on the table | accept (conditional; four lines at 390) |
| 449 | the papers | no plans signed and sealed, no permit, no net metering papers, and nobody filing them · battery first: no plans signed and sealed, no permit, and nobody filing them | accept ("nobody filing them" is the calm point) |
| 450 | the dates | no dates on the calendar: not the permit, not the installation, not the switch-on, not the two-way meter · battery first: …not the switch-on | accept |
| 452 | the close | The visit is free, and nothing is decided until you say so; book it below and every line above is answered in your proposal, within two working days. | **change to**: `The visit is free, and nothing is decided until you say so. Book it below: every line above is answered in your proposal, within two working days of the visit.` Reason: read after "book it below", "within two working days" promises the proposal two days after booking; the thank-you says visits are usually within the week and the proposal two working days after. A buyer who books on a Monday and reads the proposal ten days later remembers the line. The full stop also gives the valve its own sentence. S. |
| 46–51 | `summarySystem` | 6 panels and a battery, enough for a typical night of your use when the grid is down; sized to a typical roof and a typical house until the free on-site assessment, and fitted to yours in the proposal. · panels only: 6 panels, and a battery can be added later; sized to a typical roof until the free on-site assessment, and fitted to yours in the proposal. | **change to** (the battery form only; `typical` = `'a typical roof'` in both branches): `6 panels and a battery, enough for a typical night of your use when the grid is down; sized to a typical roof until the free on-site assessment, and fitted to yours in the proposal.` Reason: in one forwarded sentence "a typical night of your use" and "a typical house" contradict each other, and the engine does size the battery from the visitor's own kWh; the block can say "a typical house" because its next words ("not to your fridge, fans, Wi-Fi and aircon") say what is typical about it, and the summary has no such words. S. |
| 463 | thank-you, second paragraph | What happens next: one free visit, with the test panel on the roof and your bill and appliances at the table; then your proposal within two working days, valid 15 days. You decide with all of it in front of you. | accept (the roof check card gone, the proposal the only thing promised) |

The copywriter's three departures: the positive-saving guard (**accepted**, it prevents a nonsense line); four items on a
price-only result (**accepted**; do not add a sixth line to reach five); "net metering papers" unhyphenated (**accepted**).

## Part 3. What the two rounds did to the funnel's thread

Walked end to end on a phone: the Facebook snippet (title and description) → the hero "A ₱6,000 bill, down to about
₱1,900." and "See my new bill" → the estimate page's title "Your new bill in a minute" → the widget's "Your new bill is a
minute away." and "Four questions, then the bill you would pay instead…" → "Your monthly bill ₱4,803 → about ₱199" with
the sticky "Your new monthly bill / about ₱199 / Book my free on-site assessment" → "What you miss if you stop here" →
"The exact figure is one free visit away." → "Your on-site assessment is booked, Maria." → the summary with "fitted to
yours in the proposal". One word, "bill", carries from the ad to the thank-you, and the proposal is the only deliverable
named after the visit on every page and in the kit. Nothing broke. Two seams on lines the rounds did not touch:

1. **404.html:9**, the button under the new lead "Your new bill is right here, one minute, free." still says `Get my free
   estimate`. Change to `See my new bill` (the "Home" link beside it stays). S.
2. **about.html:109–111**, the band is the old home band word for word: "Your number is a minute away." / "…and the only
   call you get is the one you book." / "Get my free estimate". The home band became "Your new bill is a minute away." and
   "See my new bill"; About's should follow (the h2 and the button; the paragraph stays, it has no "another month" line
   and needs none). The Brownouts and Net metering bands keep their own lines ("See your two prices, with and without the
   battery." / "Your bill, your town, one minute.") and their hero buttons keep "Get my free estimate", which carries the
   word "free" on those pages; the brief said so and I hold to it. S.

The header's nav button stays "Free estimate" (a navigation label, unchanged by the round, and right).

---

## Notes that are not line changes

1. **The static estimate page** on 8218 shows "Loading the estimate…" because the widget script is served by the app
   host; on the public site the website process serves it. Not a finding; the widget was read on 8219.
2. **DECISIONS.md** carries an uncommitted "Rounds 10 and 11" entry (the coordinator's, in progress); its description of
   both rounds matches what I read. It should record change 3's "of the visit" if taken.
3. **The hook's figure and the pattern.** The pinned run is "mostly evening", the most conservative of the three load
   shapes for this house; if the owner ever asks why the home page says ₱1,900 while a morning house in Tanauan gets
   about ₱1,325, that is the reason, and it is the right side to err on.
4. **The battery-first money line** prints the whole bill as the loss ("about ₱4,803 a month … paid to your electric
   company") while the hero says a small bill still comes; both are the engine's `savings_monthly`, and the hero's own
   sub-line says the same figure "stays in your pocket". Consistent; noted so nobody "fixes" one without the other.
5. **Ask the owner** (unchanged from the round-11 brief, in order of value): a real before-and-after bill from the 2023
   installation, which would replace the engine's example as the strongest hook the site could carry; a photo of a lit
   house on a dark street (unlocks the Brownouts hook on the home hero's image); the inverter's switch-over time; Settings'
   owner's name, phone and Messenger (a human within reach of the hook; the footer's "Talk to us" is still blank); the
   usual length of the visit, for "free, and about an hour on the roof".

---

## Verdict on the whole

Yes on both. The home page now opens on the one thing a Laguna or Batangas homeowner came for, a bill with a before and
an after, stated as an estimate for a named house, with "about" on every figure, the proofs under it and his own figure
one tap away, with the three terms of the offer under the button; the test makes the hook as honest next year as it is
today. The result closes on what the visitor loses by closing the tab, said as five facts about his present with the
free visit and his own say as the release, and the visit now leads to the proposal and to nothing else on every page.
The three changes are small: the landing headline with its house, the close dated from the visit, and the summary's "a
typical house" gone.

## Five lines for the coordinator

1. **Change, docs/marketing.md:131** → `"A ₱6,000 bill, down to about ₱1,900, panels only, for a house using about 500 kWh a month. Yours takes a minute."` with the test's last assert changed to match.
2. **Change, Estimate.tsx:452** → `The visit is free, and nothing is decided until you say so. Book it below: every line above is answered in your proposal, within two working days of the visit.`
3. **Change, Estimate.tsx:50** → `typical` is `'a typical roof'` in both branches, so the summary reads `…; sized to a typical roof until the free on-site assessment, and fitted to yours in the proposal.`
4. **Thread seams (unchanged lines):** 404.html:9 button → `See my new bill`; about.html:109 and :111 → `Your new bill is a minute away.` and `See my new bill`.
5. **Accepted:** 32 of the 35 changed lines, the hero's three lines (three is the right count, and these three), all three round-10 departures, the ₱6,000 figure over the brief's ₱5,000; my lead change withdrawn by the first of the three lines. **Nothing must go.**
