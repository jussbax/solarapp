# Round 10 copywriter report: the closing block as what the visitor misses

From the copywriter to the coordinator and the marketing and sales specialist, 10 October 2026, in a worktree branched from
`claude/wonderful-maxwell-wawb8t` at 5ad0e0f. Two owner rulings, verbatim: on the estimate result's closing block, "it should
be what am I missing if I don't go contact them? We sell FOMO here."; and on the visit, "For the on-site assessment, what we will
provide is the proposal, not the assessment results because they might fish and give our assessment to other installers."

One file: `frontend/src/estimate/Estimate.tsx`. Three places: the closing block (`pld-line pld-visit`: h3, lead, list, close), the
copied summary's system line (`summarySystem`), and the thank-you's second paragraph. Every class, id, handler, the `#pld-book`
anchor and the `hasBattery(shown)` / `shown.goal === 'off_grid'` branches stay. Nothing in the engine, the lead payload, the
e-mail, the site pages or the tests changed.

Checks: `npm run build` clean; `npm run lint` at the 7-warning baseline, none in `src/estimate`; `site/build.py` built seven
pages; `tests/test_site.py` 11 passed. Read back as the customer on a private server (port 8215, the worktree's `frontend/dist`)
at 390 × 844 and 1280 × 900 for the battery goal at 400 kWh mostly evening (with a booking and the copied summary), the
battery-first goal at 400 kWh (phone with a booking, desktop without) and the lower-bill goal at 400 kWh (phone), plus the
alternative variant of each through the "Show it without / with the battery" link. No page overflow, no console error; the
sweep of the result for a bare "assessment", "roof check", "face by face", "only N slots", the utility's name or an exclamation
mark found nothing ("assessment" appears three times, every one as "on-site assessment"). Screenshots and the recorded texts in
`/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/copy/r10/` (`*-visit.png` the block,
`*-visit-and-book.png` the block with the whole booking card under it, `*-visit-book-viewport.png` the same as the viewport
shows it, `*-visit-alt.png` the other variant, `*-thanks.png`, and `*.json` with every text including the copied summary).

## The block, line by line: before, after, the angle

Every line below traces to the engine (the monthly saving, the panel count, the battery note) or to the company's stated method
(a typical roof and a typical load shape until someone measures; the energy audit on the visit sizes the battery from the real
appliances; the plans signed and sealed by a Professional Electrical Engineer; the permit and the net metering papers filed by
us; the proposal within two working days). Nothing names a slot, a deadline, a price rise, a competitor, hours of backup or a
figure the engine does not return.

1. **h3.** Before: "What the free visit settles". After: "What you miss if you stop here". The owner's question in the reader's
   own moment: the thumb is on the way to closing the tab, and the line names what that costs.
2. **Lead.** Before: "This estimate comes from your answers and a typical roof. One free visit, with the test panel and meters
   on your roof and your bill on the table, settles:". After: "Close this page and nothing changes. Next month's bill comes as
   it does today, and this estimate stays a typical roof's, not yours. What you are left with:". The status quo as the loss:
   relief withheld, and the estimate's own limit (a typical roof) turned into the reason to book.
3. **The money (new; only when the engine returns economics and the saving is positive).** After: "about ₱4,604 a month, by
   this estimate, paid to your electric company instead of kept in your pocket" (`php0(e.savings_monthly)`, the hero's own
   figure, with "about" and "by this estimate" so it stays an estimate, never a guarantee). Relief, turned around: the number
   the hero says stays in the pocket is the number that keeps leaving the house every month nothing is done.
4. **The roof.** Before: "how many panels your roof really holds, and where they go: the sun and the shade read face by face".
   After: "a roof nobody has measured for the panels it holds and the shade on it, so the exact price and the exact bill stay
   unknown". Control: measuring is the method, and the only things named as unknown are the two the proposal delivers; nothing
   from the visit is promised as a handover (the second ruling). The old third line, "the exact price to your roof: every panel,
   rail, cable and breaker listed, and what is due when", is folded into this one; the parts list stays in the booking card's
   hint ("every peso and every part on paper").
5. **The battery.** Before (with a battery): "what your battery carries on a brownout night, from your own appliances rather
   than a typical house: the fridge, the fans, the Wi-Fi, the aircon if you size for it"; (panels only): "what a battery would
   carry on a brownout night, from your own appliances, if you want one". After (with a battery): "a battery sized to a typical
   house, not to your fridge, fans, Wi-Fi and aircon, until your appliances are on the table"; (panels only): "a battery, if you
   want the lights on in a brownout, sized to a typical house until your own fridge, fans, Wi-Fi and aircon are on the table".
   Comfort: the engine's own assumption ("the energy audit on the visit uses your real appliances") said as what the visitor is
   left with, with the appliances named so the reader pictures the night.
6. **The savings year by year.** Before: "your savings year by year, and what 25 years add up to on your roof". After: gone.
   The money line now carries the saving as the monthly loss; the horizon total left the page in round 9 and would come back
   only as a promise, and the list stays at five.
7. **The papers.** Before: "the plans signed and sealed by a Professional Electrical Engineer, the permit and the net metering
   papers, filed by us" (battery first: "the plans signed and sealed by a Professional Electrical Engineer and the permit, filed
   by us"). After: "no plans signed and sealed, no permit, no net metering papers, and nobody filing them" (battery first: "no
   plans signed and sealed, no permit, and nobody filing them"). Calm: the one contractor who files it all, read from the side
   where nobody is on it yet; the battery-first branch keeps no net metering papers and no two-way meter.
8. **The dates.** Before: "the dates: permit, installation day by day, switch-on and the two-way meter" (battery first: "…and
   switch-on"). After: "no dates on the calendar: not the permit, not the installation, not the switch-on, not the two-way
   meter" (battery first: "…not the switch-on"). Calm and control: the schedule is the proposal's, and without a booking the
   calendar is empty.
9. **Close.** Before: "Then your proposal, within two working days, every peso and every part on paper, and you decide with all
   of it in front of you." After: "The visit is free, and nothing is decided until you say so; book it below and every line
   above is answered in your proposal, within two working days." The safety valve inside the block, then one sentence that
   lands on the button and names the proposal as the one thing the visit leads to.

The block's final text, battery goal, 400 kWh mostly evening, Pila, Laguna:

```
What you miss if you stop here
Close this page and nothing changes. Next month's bill comes as it does today, and this estimate stays a typical roof's, not yours. What you are left with:
- about ₱4,604 a month, by this estimate, paid to your electric company instead of kept in your pocket
- a roof nobody has measured for the panels it holds and the shade on it, so the exact price and the exact bill stay unknown
- a battery sized to a typical house, not to your fridge, fans, Wi-Fi and aircon, until your appliances are on the table
- no plans signed and sealed, no permit, no net metering papers, and nobody filing them
- no dates on the calendar: not the permit, not the installation, not the switch-on, not the two-way meter
The visit is free, and nothing is decided until you say so; book it below and every line above is answered in your proposal, within two working days.
```

Battery first (400 kWh, spread): the money line "about ₱4,803 a month…", the papers "no plans signed and sealed, no permit, and
nobody filing them", the dates "…not the switch-on". Panels only (the lower-bill goal, or the battery goal's alternative): the
money line "about ₱3,551 a month…" and the battery line in its "if you want the lights on in a brownout" form.

## The summary and the thank-you

- **The copied summary's system line.** Before: "6 panels and a battery, enough for a typical night of your use when the grid is
  down; the exact layout and sizes come from the free on-site assessment." After: "6 panels and a battery, enough for a typical
  night of your use when the grid is down; sized to a typical roof and a typical house until the free on-site assessment, and
  fitted to yours in the proposal." Panels only: "6 panels, and a battery can be added later; sized to a typical roof until the
  free on-site assessment, and fitted to yours in the proposal." The same loss (typical, not yours) in a line a person forwards
  on Messenger, and the proposal as where it is fixed. The summary's other lines, including "This is an estimate, not a
  quotation; the free on-site assessment makes it exact.", are untouched.
- **The thank-you's second paragraph.** Before: "What happens next: one free visit, with the test panel on the roof and your bill
  and appliances at the table; your roof check card the same evening; your proposal within two working days, valid 15 days.
  You decide with all of it in front of you." After: "What happens next: one free visit, with the test panel on the roof and your
  bill and appliances at the table; then your proposal within two working days, valid 15 days. You decide with all of it in
  front of you." The second ruling: the visit leads to the proposal and to nothing else the customer is promised.
- **The booking card's h3 and hint**, unchanged. "The exact figure is one free visit away." now answers the block's "the exact
  price and the exact bill stay unknown" rather than repeating it, and the hint's job (the test panel and meters against the
  satellite photo, the proposal exact to the roof) is not in the block. Its last two words, "You decide after.", echo the
  block's valve from eight lines above; I kept them because the sticky bar's button lands the reader on the card without the
  block, and the form should carry its own valve at the moment a name is typed. If the review finds the echo too close, the
  cut is those two words alone.

## Departures from the brief, each with the reason

1. The money line is guarded by `e && e.savings_monthly > 0`, not `e` alone: a saving of zero or less would print as a loss
   of nothing or a negative peso figure. Every walked case shows it.
2. The list is five items where the engine returns economics (the brief's five: the money, the roof, the battery, the papers,
   the dates) and four on the price-only result, which has no monthly saving to print. If five is wanted there too, the line
   to add is the savings worked out on the visitor's own roof ("no savings worked out on your own roof, year by year"), which
   the proposal does carry.
3. "net metering papers" stays unhyphenated, as the rest of the widget and the site write it.

## What I wanted to say and could not, and what to ask the owner for

- How long the visit itself takes and whether the visitor must be home. "The visit is free" would carry more weight as "free,
  and about an hour on the roof"; there is no figure in the facts. Ask: the usual length of a visit, roof and table together.
- How soon the visit usually happens. The thank-you already says "visits are usually within the week"; the block could use it
  as honest urgency ("a visit is usually within the week"), but the brief's list did not include it and I did not add it. Ask
  whether that line still holds and whether it may stand in the block.
- Nothing about the bill growing over the years, or the price of the job moving, went in: the brief forbids a price rise, and
  the engine's escalation assumption is not printed on the page. Nothing to ask; recorded so nobody adds it later.

## For the coordinator

- `DECISIONS.md` ("Quick estimate", "Shown to the visitor", and the booking flow) needs a line for the second ruling: the widget
  no longer promises the roof check card or any reading from the visit; the proposal is the only deliverable named.
- The site pages are the coordinator's in this round; the widget's own foot ("on the free on-site assessment we measure your
  roof and the sun on it, and the proposal that follows is exact") and the booking hint already read measuring as the method,
  so I left them.
