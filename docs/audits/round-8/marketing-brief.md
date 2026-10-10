# Round 8, marketing: the angle brief for the estimate widget

From the marketing and sales specialist to the copywriter, 10 October 2026. Read as the customer reads it on a private
server (http://127.0.0.1:8211, scratch database, the real sun records) at 390 × 844 and 1280 × 900: every card, the
result with the day scene (every caption over a full day, three goals, five sizes), the booking card, one booking under a
made-up name, the thank-you and the copied summary. Screenshots `phone-*.png`, `desk-*.png` and `walk.js` are in
`/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/marketing/`. Line numbers are the files'
as of 05:33 today (`frontend/src/estimate/Estimate.tsx`, `Wizard.tsx`, `DayScene.tsx`, `backend/solarapp/core/quick.py`); every
line is also quoted, so cite by string if they move. The figures quoted are the engine's for a Pila, Laguna house using
400 kWh a month, mostly in the evening: with the battery ₱4,803 → about ₱199, ₱308,000, 7.4 years, about ₱55,000 the first
year, about ₱957,000 over 25 years; without it ₱180,000, about ₱1,252, 4.1 years, about ₱1.17 million. Nothing here is a
new fact: every proof is the engine's figure or a line in the round-7 brief.

## 1. The widget's job in the funnel

The visitor arrives from a Facebook link or the home page's "Get my free estimate" button carrying one feeling (the bill
that hurts every month, or the evening the whole street went dark) and one question: how much lower, and what does it
cost. The estimate is the first thing the company gives them, before it asks for anything: in a minute, their own bill
before and after, the price of the whole job and the panels on their roof, in the voice the website used to bring them
here. The booking is the sale: the one free visit that turns the number into an exact proposal, and every line after the
result exists to make that visit feel like the calm, obvious next step rather than a sales call.

## 2. Section by section, in the order the visitor meets them

Each section: the feeling to sell, the outcome to name, the proof at hand, the objection to pre-empt, the words to avoid;
then the line as it runs today and the words I would run. "Keep" means the line already does its job.

### 2.1 The intro (Estimate.tsx:329–332)
Today: h1 "What would your bill be with solar?"; the lead "Four questions, about a minute: … and that one makes the figure
exact." runs six lines at 390 px (`phone-combination-card1.png`); the rail allows four.
Feeling: the bill in the drawer, the dark street; the visitor was just promised a number and wants it before giving
anything. Outcome: the bill you would pay instead, the price of the whole job, the panels, in a minute. Proof: the figures
a minute later; the band line "the only call you get is the one you book". Objection: "they will call me", "it will be a
pitch". Avoid: "sign-up", "obligation", "quote", "assessment" (the visit's word belongs on the booking card).
Run: h1 `Your new bill is a minute away.` (the band the visitor just left says "Your number is a minute away."; the hero
lead says "your new bill"; the promise is kept word for word). Lead: `Four questions, then the bill you would pay instead,
the price of the whole job, and how many panels it takes. The only call you get is the one you book.` (150 characters,
four lines.) If the coordinator keeps the question h1, change the lead alone.

### 2.2 Card 1, the three wants (Wizard.tsx:10–14, 21)
Today: "What do you want from solar?" over "A lower bill" / "A lower bill, and lights in a brownout" / "Battery first,
nothing sold back". Feeling: the moment of choice, and the home page already asks it in the customer's voice
(index.html:42–54); one tap later the widget answers in the engine's, and the funnel changes voice exactly where the sale
starts. Outcome: the title is the want; the small text names the kind (the label stays) and what the house gets.
Objection: "which one is me?" (the small text says who it is for); "is the battery worth it?" (not here: the result shows
both prices). Avoid: "no battery", "no power", "cannot", "only", "hybrid", "grid-tie", "kWp".
Run (question stays; `<b>` title, `<small>` text; the kind name opens the small text so the label stays on the card):
- `<b>I just want a lower bill.</b>` `<small>Solar with net metering. The panels run the house by day, and the extra comes
  back as credit on your bill. A battery can come later, whenever you want lights in a brownout too.</small>`
- `<b>I want the lights on when the street goes dark.</b>` `<small>Solar with a battery. The panels run the house by day and
  bring the bill down; the battery carries the evening and the brownouts. The extra still earns credit on your bill.</small>`
- `<b>I want my roof to run my house.</b>` `<small>Battery first, nothing sold back. More panels and a battery carry the
  house day and night, and the grid steps in only when both fall short. For homes that would rather keep their own power
  than sell it, and for places where net metering is out of reach.</small>`
(The walk scripts click the second card by its title; `flow2.js` and my `walk.js` follow the new one.)

### 2.3 Card 2, the town (Wizard.tsx:21, 179, 197, 217–227)
Today: "Where is your house?"; hint "At the house? Use my location and the town fills in. Not in the list? Message us."
Feeling: the sun over your own town; a company that drives to you. Outcome: the estimate uses your town's sun records
(the engine's method, quick.py:255). Objection: "do they even come to us?" (About: "we travel to wherever yours is").
Avoid: "pin", "coordinates", "PVGIS", "cell", "service area".
Run: hint (221–227) `Your town picks the sun records we size from. At the house? Use my location and the town fills in.
Not in the list? Message us; we come to wherever the house is.` The question, labels and the two location hints keep.

### 2.4 Card 3, the kWh (Wizard.tsx:21, 237–241)
Today: "How much electricity do you use in a month?", "kWh on your latest bill", "e.g. 338", hint "The kWh is printed on
the bill, usually near "consumption"." Feeling: the bill in the hand, the number that hurts; the one card that asks the
visitor to get up and find something. Outcome: the panels sized to that number, so you buy only what the house uses (the
site's Brownouts tick; the engine sizes from consumption). Objection: "I don't have it with me". Avoid: "consumption" on
its own, "load", "usage", "monthly use".
Run: question, label, placeholder keep. Hint (241) `The kWh is printed on the bill, usually next to "consumption". It
sizes the panels to what your house uses, so you buy only what the house needs.`

### 2.5 Card 4, the slider (Wizard.tsx:16–20, 21, 268, 321, 329)
Today: "When does your house use the most power?"; "Mostly morning" / "All day" / "Mostly evening" with "Cooking, laundry,
the pump and aircon early in the day." / "Someone is home most of the day." / "The house is busiest after dark: aircon,
TV, cooking."; the not-ready hint "Pick your town and enter your monthly use first." Feeling: the household's rhythm; the
question is about the people in the little house above it, and the texts already live there. Outcome: the day the scene
will play; for an evening house, the evening a battery would carry. Avoid: "load profile", "pattern", "peak".
Run: stops keep (three titles on one line at 390). Texts: morning `Cooking, laundry, the pump and aircon early in the day,
when the panels are already at work.`; all day `Someone is home most of the day, so the house uses the sun as the panels
make it.`; evening `The house is busiest after dark: aircon, TV, cooking. This is the evening a battery would carry.`
"Show my estimate", "Working it out…", "Back", "Next", "1 of 4" keep. Hint (329): `Pick your town and type the kWh from
your bill first.` / `Type the kWh from your bill first.`

### 2.6 The result heading (Estimate.tsx:350)
Today "Your estimate". Run `Your estimate for {result.inputs.place}`: the word the rails want, and it is theirs, named.

### 2.7 The day scene (DayScene.tsx:149–162 readout, 165–188 captions, 471–474 aria-label, 654–655 strip, the chips)
Today, every caption seen in the walk: "Dawn · your system, piece by piece" / "Then a typical day, hour by hour."; "The
panels wake up."; "The house runs on the sun; the extra fills the battery." / "…fills the battery and goes out as credit."
/ "…goes out as credit." / "…the battery is full." / "The house runs on the sun."; "The sun goes down; the battery picks up
the rest." / "…the grid picks up the rest."; "The battery carries the evening." / "The grid steps in for the evening.";
"Everyone asleep, the fridge on the battery." / "…on the grid."
Feeling: watching your own house live one ordinary day: the morning the panels take over, the afternoon the battery fills
for tonight and the extra goes back through the meter, the evening on the battery, the night with the fridge humming.
Outcome: the family's day, with the engine's kW under it as the proof (the readout stays exactly as it is). Objection:
"does it really run my house?" (the hour-by-hour readout); "what about at night?" (the night captions). Avoid: "export",
"import", "discharge", "surplus", "load"; "seamless", "instant", "you won't notice" (no switch-over time on file); the
aircon in an evening caption.
Run:
- 654 `Dawn · your house, fitted out piece by piece`; 655 `Then an ordinary day, hour by hour.`
- 180 `The sun is up and the panels are taking over.`
- 173 `The house runs on the sun; the extra fills tonight's battery, and the rest goes back through the meter as credit.`;
  174 `The house runs on the sun; the extra fills tonight's battery.`; 175 `The house runs on the sun; the extra goes back
  through the meter as credit.`; 176 `The house runs on the sun; the battery is full for tonight.`; 177 keep.
- 181 battery `The sun goes down and the battery takes over.`; grid `The sun goes down and the grid takes over, like today.`
- 187 battery `The battery carries the evening on your own power: the lights, the fan, the TV, the Wi-Fi.` (the site's
  accepted picture; the caption follows the row, so it shows only in hours the battery really carries); grid `The evening
  runs on the grid, like today; the day's extra came back as credit.` (the second clause only when the day exported
  anything, a condition of the kind `caption()` already uses; otherwise the first clause alone).
- 186 keep both. The readout's words and figures, the chips and the aria-label's facts keep ("a typical day" → "an
  ordinary day" in the aria-label, for one voice).

### 2.8 The hero (Estimate.tsx:361–394)
Today: "Your monthly bill" / "₱4,803 → about ₱199" / "about ₱4,604 less each month; your electric company's fixed charges
stay on the bill" (small bill: "…; what stays is your electric company's fixed charges and the grid's hours in long rainy
spells"); "Pays for itself in" / "7.4 years" / "about ₱55,000 saved in the first year"; "Estimated price" / "₱308,000" /
"installed, with permits, VAT included"; "Saved over 25 years" / "about ₱957,000" / "after paying for the system, its
upkeep and replacement parts". Feeling: relief first, then the years, then the price as the whole thing. Outcome: money
that stays in the house every month; what the years add up to; a price with nothing behind it. Proof: the engine's figures
with "about" in front. Objection: "what's not in the price?"; "why is a bill left?" (said as what still comes). Avoid:
"less" as the headline verb, "net", "ROI", any savings figure without "about".
Run: 361, 363, 373–375, 383–385 keep. 368 `about ${php0(e.savings_monthly)} a month stays in your pocket; what still comes
is your electric company's fixed charges`; 367 `about ${php0(e.savings_monthly)} a month stays in your pocket; what still
comes is your electric company's fixed charges, and the grid's hours in long rainy spells`; 380 and 393 `the whole job:
installed, permits and papers filed, VAT included`.

### 2.9 The two actions (Estimate.tsx:399–400)
"Book my free on-site assessment" keeps (the owner's word, the same on the sticky bar and the form). "Estimate another one"
→ `Try other answers` (it says what happens, the cards come back, and invites the second run for the parents' house or
the other goal).

### 2.10 "What goes in" / "What it makes" (Estimate.tsx:26–39, 404–412)
Today: "What goes in: 6 × 585 W panels (3.51 kWp), 6 kW hybrid inverter, 12 kWh lithium battery (enough for a typical night
of your use when the grid is down). Needs about 15 m² of roof." / "What it makes: about 444 kWh a month, 111% of the 400 kWh
you use. Daytime power runs the house first; … Covered by solar, by day and from the battery: 96% of what you use."
Feeling: an inventory read to a customer, with the one sentence a buyer repeats to his wife in brackets. Outcome: what
goes on the house and what it does for it, every figure inside the sentence. Objection: "will it fit my roof?" (the m²);
"is it enough?" (the coverage as what the house gets). Avoid: "×", brackets around the battery note, "surplus", "usage".
Run: 404 `<b>What you get:</b> 6 panels of 585 W (3.51 kWp) on about 15 m² of roof, a 6 kW hybrid inverter and a 12 kWh
lithium battery, enough for a typical night of your use when the grid is down.` (the battery note, in either of its two
forms, closes the sentence; `systemLine` keeps every figure.) 407 `<b>What it does:</b> the panels make about 444 kWh a
month, 111% of the 400 kWh you use.` then, by goal: 408 `By day the panels run the house first; the extra goes to your
electric company and comes back as credit at its generation rate, so what still comes is a small bill for the fixed
charges and the hours the grid covers.`; 409 `Sized so the panels and the battery carry an ordinary day on their own; once
the battery is full the extra sun goes unused, because nothing is sold back.`; 410 `The grid still steps in for about
${n0(prod.annual_import_kwh)} kWh a year, mostly in the rainy months.`; `coveredLine` (36–38): net metering `The house
runs ${pct}% of what it uses straight from the panels; the rest of the day's sun goes back through the meter as credit on
your bill.`; with the battery `Between them, the panels by day and the battery after dark cover ${pct}% of what you use.`;
battery first `The panels and the battery cover ${pct}% of what you use; the grid is only the spare.`

### 2.11 The battery alternative (Estimate.tsx:413–434)
Today, battery shown: "Without the battery: ₱180,000, bill about ₱1,252 a month, pays for itself in 4.1 years. The battery
buys the brownout comfort; the panels do the saving. Show without the battery". Not shown: "Add a battery for brownouts:
about ₱128,000 more (12 kWh, enough for a typical night of your use when the grid is down), bill about ₱199 a month, pays
for itself in 7.4 years. Show with the battery" (and at 250 kWh the slip "bill small a month"). Feeling: the add-on opens
with the money and the comfort is in brackets; leaving the battery out reads like giving something up. Outcome: adding it
buys the evening when the street is dark; leaving it out keeps the saving whole. Proof: both prices, bills and paybacks,
the battery note. Avoid: "adds little", "only", "insurance", any hours the note does not give.
Run, battery shown (417–421): `<b>Panels only, without the battery:</b> ₱180,000, the bill about ₱1,252 a month, pays for
itself in 4.1 years. The panels do the saving either way; the battery is what keeps the lights on when the street goes
dark.` button `Show it without the battery`. Not shown (426–429): `<b>Want the lights on when the street goes dark?</b> A
12 kWh battery is about ₱128,000 more, enough for a typical night of your use when the grid is down; the bill about ₱199 a
month, pays for itself in 7.4 years.` button `Show it with the battery`. In both, the small-bill case reads `a small bill`
in place of "the bill about ₱… a month".

### 2.12 The booking card (Estimate.tsx:436–511)
Today: h3 "Want the exact figure? We come and measure. The visit is free."; hint "Most installers quote from a satellite
photo. We put a test panel and meters on your roof, measure the sun and the shade, and quote exactly. The visit is free,
and you decide after."; the labels, the button, "Your name and a number or Messenger name are enough.", the profile's
privacy line. Feeling: calm and control: one visit, free, the test panel on the roof, every peso and every part on paper,
you decide after. Outcome: the exact figure. Proof: the test panel and meters (the company's method); "every peso and
every part on paper" (the site's h2). Objection: "a visit means a salesman in my house" (it is a measurement, and you
decide after); "what do they want from me?" (a name and a number). Avoid: "quotation" outside the law line, "free of
charge", "no obligation", "assessment" anywhere but the visit's name.
Run: 437 (not yet sent) `The exact figure is one free visit away.`; 460 `Most installers quote from a satellite photo. We
put a test panel and meters on your roof, read the sun and the shade, and sit down with your bill. Then your proposal,
exact to your roof, every peso and every part on paper. You decide after.` Labels, button, "…are enough." and the privacy
line keep. Optional, the coordinator's call (it would hard-code a round-7 fact in a widget where every fact comes from the
profile): a last sentence `Our own home in Pila, Laguna has run on what we sell since 2023.`

### 2.13 The thank-you (Estimate.tsx:437–455)
Today: h3 "Your on-site assessment is booked, Maria."; "Thank you, Maria. We will message or call you within one working
day to pick a day; visits are usually within the week. That is all for now: keep a recent bill where you can find it.";
"What happens next: one free visit, … your proposal within two working days, valid 15 days."; "Open Messenger" (when set),
"Copy my estimate" / "Copied". Feeling: relief that it is done, control over what comes. Outcome: a person's name and a
day; the three papers in order. Avoid: "nothing", "no further action", "our team".
Run: h3 keep. 441 `Thank you, ${firstName}. ${owner_name || 'We'} will message or call you ${callback_promise} to set the
day; visits are usually within the week. That is all for now: keep a recent bill where you can find it, it goes on the
table at the visit.` 444 `What happens next: one free visit, with the test panel on the roof and your bill and appliances
at the table; your roof check card the same evening; your proposal within two working days, valid ${validDays} days. You
decide with all of it in front of you.` The buttons keep.

### 2.14 The foot and the sticky bar (Estimate.tsx:514–518, 522–531)
Today: "Sized for a house using about 400 kWh a month, mostly in the evening, in Pila, Laguna. About 3.8 tonnes of CO₂
avoided a year. This is an estimate from your answers, not a quotation. On the free on-site assessment we measure your
roof and the sun on it, then give you an exact proposal."; sticky "Estimated price ₱308,000 / Book my free on-site
assessment". Feeling: the small print as a confident company's last word. Avoid: "sized", "assume", "subject to".
Run: 515–517 `Worked out for a house in ${place} using about ${kWh} kWh a month, ${pattern}. About ${co2} tonnes of CO₂
avoided a year. This is an estimate from your answers, not a quotation: on the free on-site assessment we measure your
roof and the sun on it, and the proposal that follows is exact.` The sticky bar keeps (its label matches the hero's).

### 2.15 The copied summary (Estimate.tsx:274–289)
Today, in this order: the company and place; the system line; "Estimated price ₱308,000 installed, VAT included."; the bill
line; the lifetime line; "This is an estimate, not a quotation."; the links. Feeling: this is read by the spouse or the
parent who decides, on Messenger, in ten seconds; the bill is what they asked about and it is the fourth line. Avoid: "×",
brackets, anything that needs the page to make sense.
Run (plain text, the same seven parts, the bill first):
```
Solar estimate from ${company} for ${place}:
Bill ${before} → ${after} a month; about ${year1} saved in the first year; pays for itself in ${years}.
Price ${price}, installed, permits and VAT included.
What it takes: 6 panels of 585 W (3.51 kWp), a 6 kW hybrid inverter and a 12 kWh lithium battery, enough for a typical night of your use when the grid is down.
Saved over 25 years: about ₱957,000, after paying for the system and its upkeep.
This is an estimate, not a quotation; the free on-site assessment makes it exact.
Questions: m.me/… · Run your own: …/estimate
```

### 2.16 The warnings and the error notes (quick.py:241, 243, 38; Estimate.tsx:88–93, 132, 141, 158)
Today: "Your house needs more than 40 panels; we capped the estimate there, and on the on-site assessment we see how many
your roof really takes."; "This location is off the map of the Philippines, where we install. Check the pin, or pick your
town instead."; the too-little error "That's very little usage; …"; "The estimate is taking a break. Message us on
Facebook and we'll work it out for you."; the location errors. Feeling: a person explaining, not a system refusing.
Avoid: "capped", "usage", "invalid", "error".
Run: 241 `Your house would take more than 40 panels, so this estimate stops at 40; on the free on-site assessment we see
how many your roof can hold.`; 243 `That spot is outside the Philippines, where we install. Check the pin, or pick your
town instead.`; 38 (optional, outside the brief's named lines) `That is a very small bill; solar would not pay for itself
at that use. If the kWh on your bill is higher, type that figure.` The down notes and the location errors keep.
`profile.py:37` ("within one working day") and `:41` (the privacy line) fight nothing; keep.

## 3. The lines that cost a sale today, in rank order (the replacement is in the section named)

1. **Wizard.tsx:11–13**, "A lower bill" / "A lower bill, and lights in a brownout" / "Battery first, nothing sold back". The
   home page asked "I want the lights on when the street goes dark"; one tap later the funnel changes voice at the moment
   of choice and the visitor feels handed to a machine. Run the three "I want" titles (2.2).
2. **Estimate.tsx:404–412**, "What goes in: 6 × 585 W panels (3.51 kWp), …" / "What it makes: about 444 kWh a month, 111% of
   the 400 kWh you use…". The inventory, with what the battery carries in brackets. Run "What you get" / "What it does" (2.10).
3. **Estimate.tsx:426**, "Add a battery for brownouts: about ₱128,000 more (12 kWh, enough for…)". The add-on opens with the
   money; the comfort it buys is the bracket. Run "Want the lights on when the street goes dark? A 12 kWh battery is about
   ₱128,000 more, enough for a typical night of your use when the grid is down; …" (2.11).
4. **Estimate.tsx:329–332**, the question h1 and the six-line lead ending on "exact". The visitor was promised a number a
   minute away and meets a question and a paragraph. Run "Your new bill is a minute away." and the four-line lead (2.1).
5. **Estimate.tsx:367–368**, "about ₱4,604 less each month; your electric company's fixed charges stay on the bill". The
   relief line said as a subtraction, chased by what stays. Run "about ₱4,604 a month stays in your pocket; what still
   comes is your electric company's fixed charges" (2.8).
6. **DayScene.tsx:173–175, 181, 187**, "goes out as credit", "the grid picks up the rest", "The grid steps in for the
   evening." The engine narrating an energy balance over the family's house; for the no-battery buyer the evening reads as
   a loss. Run the day captions (2.7).
7. **Estimate.tsx:417–419**, "Without the battery: ₱180,000 … The battery buys the brownout comfort; the panels do the
   saving." Leaving it out is "without"; the comfort is abstract. Run "Panels only, without the battery: … the battery is
   what keeps the lights on when the street goes dark." (2.11).
8. **Estimate.tsx:437, 460**, "Want the exact figure? We come and measure. The visit is free." and "…quote exactly. The visit
   is free, and you decide after." The booking asks a question and sells a measurement; it should sell calm and control.
   Run "The exact figure is one free visit away." and the hint (2.12).
9. **Estimate.tsx:279–285**, the copied summary with the bill on the fourth line and "6 × 585 W panels" on the second. The
   forwarded reader decides on the bill. Run the order of 2.15.
10. **Estimate.tsx:380, 393**, "installed, with permits, VAT included": true and flat; the buyer comparing two quotes wants to
    hear it is the whole thing. Run "the whole job: installed, permits and papers filed, VAT included" (2.8).
11. **Estimate.tsx:515**, "Sized for a house using about 400 kWh a month…": the engine's assumption as the last word. Run
    "Worked out for a house in Pila, Laguna using about 400 kWh a month, mostly in the evening." (2.14).
12. **Estimate.tsx:400** "Estimate another one" → "Try other answers"; **Wizard.tsx:329** "enter your monthly use" → "type
    the kWh from your bill" (2.9, 2.5).
13. **DayScene.tsx:654–655**, "your system, piece by piece" / "Then a typical day, hour by hour." → "your house, fitted out
    piece by piece" / "Then an ordinary day, hour by hour." (2.7).
14. **Wizard.tsx:241, 221–227, 17–19**, the kWh hint, the town hint and the three stop texts: each can say why the question
    matters to the house (2.3–2.5). **Estimate.tsx:441, 444**: the thank-you closes the loop (2.13).

## 4. What must not change

- Every figure the widget shows, with its rounding (`php0`, `phpAbout`, `n0`, `years`): the bill before and after, the
  monthly, first-year and lifetime savings, the payback, the price, the panels and kWp, the inverter kW, the battery kWh,
  the roof m², the kWh made and its percentage, the coverage, the import kWh, the CO₂, the readout's kW hour by hour, the
  chips, the valid days.
- The honesty lines, inside the sentences: "about" before every savings figure; "This is an estimate, not a quotation" in
  the foot and the summary, word for word; the fixed charges and the rainy-spell hours as what still comes; the battery
  note in its two forms exactly as the engine gives it ("enough for a typical night of your use when the grid is down" /
  "about N hours of your evening use when the grid is down"); the battery as comfort and backup, the panels as the saving;
  the cap warning's substance.
- The three kinds as the small label: "Solar with net metering", "Solar with a battery", "Battery first, nothing sold back"
  open the three small texts; "net metering" / "grid as backup" stay on the chip.
- The one-visit promise in the owner's word: "Book my free on-site assessment" on both buttons and the sticky bar; "one
  free visit"; "the only call you get is the one you book"; the step list (the visit, the roof check card the same evening,
  the proposal within two working days, valid N days).
- The profile's lines as they come from Settings (callback promise, privacy line, trust and warranty lines, the owner's
  name when set); the field labels; "Morning / Afternoon / Evening"; "Show my estimate", "Working it out…", "Back", "Next",
  "1 of 4"; the aria-label's facts.
- No "assessment" but the visit's name; "your electric company", never the utility; no financing word; no exclamation mark;
  no hours, brand, town, date, switch-over time or customer voice the engine or the round-7 brief does not give.

## 5. What I wanted to say and cannot until the owner supplies it

1. A person's name in the thank-you and the booking card's trust list: Settings › owner's name and phone. Until then the
   thank-you says "We" and the trust list has no human.
2. A Messenger link: the summary's "Questions: m.me/…", the thank-you's "Open Messenger" and the down note's "Message us on
   Facebook" exist only when Settings › Messenger (or Facebook) is filled.
3. The PEE's name and PRC number: the booking card prints the engineer's line only when they are set.
4. The brands line in Settings: the battery could be "named by brand on your proposal" in the add-on line.
5. The inverter's switch-over time from the datasheet: unlocks "before anyone notices" in the evening caption; until then
   "takes over" and "by itself" are the words.
6. The installation-day outage length: unlocks "your power is off for about an hour on the second morning" in the
   thank-you's "what happens next".
7. The owner's yes to one proof line typed into the widget ("Our own home in Pila, Laguna has run on what we sell since
   2023"), since every other fact on the result comes from the profile.

## Notes for the coordinator (not words)

- The standalone page's foot prints the four warranty lines twice (Estimate.tsx:306 adds `status.warranty` to `trust`, then
  543–549 prints it again; `phone-combination-card1.png`, bottom). The embedded card is fine.
- The battery chip says "11.7 kWh" ("10.24 kWh" for the battery-first house) while the line and the summary say "12 kWh" /
  "10 kWh": two figures for one battery on one screen (`DayScene.tsx` `trim()` against `toFixed(0)`). The rails freeze
  rounding, so this is your call, not the writer's. "bill small a month" (Estimate.tsx:418, 427) is a live grammar slip.
- The assumptions ("How we worked this out") no longer render in the widget, so the trip in the price and the tariff reach
  the customer nowhere; the price sub-line is now the only "what's in it" line. The round-7 ask stands: fill Settings
  (phone, Messenger, owner's name, PEE name and PRC number) and the widget gains a person without a word changing.
