# Marketing and sales audit, round 3: PL Development Inc. (website, estimate, roof check, proposal, card, hand-off)

Audit only; nothing under /home/user/solarapp was changed. Lens for this round, in the owner's words: are the
plans and quantity take-offs translated into what the customer really cares about and a solution to their
problem? I walked the whole customer path on my own servers and judged every document against "what do I get,
what does it cost, what do I save, what happens when, who is responsible, what can go wrong".

Owner constraints respected: no financing or "from ₱X a month" lines; no utility branding; nothing fabricated;
warranties blank until Settings is filled; customer documents carry no internal costs; the server makes no
outside calls. Where a proposed line needs the owner's data, the report says what to ask for instead of inventing it.

## Method

- Private app on 127.0.0.1:8020 (database `agents3/marketing/app.db`, materials workbook seeded on first start),
  public website process on 127.0.0.1:8021 serving `site/dist`. The private app was started with
  `SOLARAPP_PUBLIC_URL=https://solar.pldevinc.com` and `SOLARAPP_WEBSITE_URL=https://pldevinc.com`, as production
  will be, so the card's QR code and the copied summary carry their real links (`start-private.sh`).
- Every page in `site/pages` rendered with Playwright at 390 px and 1366 px; text, titles, OG tags, hidden blocks and
  buttons captured: `agents3/marketing/shots/{phone,laptop}-*.png`, `shots/site.json` (`site.js`). No sideways scroll
  on any page at either width; no console errors beyond my own 404 test page.
- Estimate flow end to end on the public port (`flow.js`, `shots/flow.json`, `shots/flow-*.png`): six cases
  (Pila ₱4,000 all-day hybrid, with the battery toggle; Tanauan 500 kWh evening net metering; Los Baños 338 kWh
  morning battery-first; a ₱150 bill; 3,000 kWh; Lipa ₱12,000 morning), the booking with a landmark address, the
  thank-you page, the clipboard summary, the site footer.
- The booked lead (Maria Santos, Brgy. Labuin, Pila, fb/audit3) taken through the real hand-off: `Start assessment`
  through the API, then the roof (two 9.7 × 6.5 m faces at 15°, a 1.2 m wall and a mango tree), one reading set
  (903 W/m², clear sky, 11:30), eight appliances including a planned second aircon and a Wi-Fi router, the 338 kWh /
  ₱4,058 September bill, signing 20 Oct 2026; calculated with the real PVGIS data (`docs.py`, `results.json`).
- Every customer document generated twice, with the blank profile as it ships and with an obviously-test profile
  (`docs-blank/`, `docs-filled/`, PDFs plus `pdftotext -layout`), and once more for the same house as net metering
  only and as battery-first no-export (`docs-net_metering/`, `docs-off_grid/`). The card viewed as an image.
- The owner's lead e-mail rendered from the real lead's data (`notify.lead_notice`). The back office opened in a
  phone-sized browser as the owner: Leads page, the project's Design and outputs step, Settings (`office.js`,
  `shots/office-*.png`, `shots/office.json`).
- Both servers stopped at the end.

## Verdict

The pipeline now hangs together: one engine gives the website ₱181,000 for the Tanauan house and the page says
₱181,000; the lead lands in its own inbox with what the visitor saw; the proposal bridges the website figure, names
what the firm delivers, answers the usual questions, prints the battery the customer pays for, and can be signed; the
card carries readings with their time and a QR code back to the estimate. Honesty is in good shape: no financing, no
utility branding, "estimate, not a quotation" everywhere, placeholders stripped from the public build, warranties
hidden until filled, "before any fixed charges" on the website figure.

What is still missing is the owner's actual ask. The documents are honest engineering summaries, not a customer's
problem and its solution:

1. The proposal opens with the price box, not with "your bill is ₱4,058 and you plan a second aircon; seven panels
   and a 15 kWh battery bring it to about ₱291 and carry your evening in a brownout". Every number for that sentence
   is already computed; nothing says it.
2. The battery is still a quantity ("10 kWh lithium battery", "designed to carry 1 evening without sun"). For Maria's
   house the engine shows the battery holds the whole night, aircon included (9.3 kWh used from 6 pm to 6 am against
   13 kWh usable). That is the sentence a buyer pays for.
3. The schedule tells the customer what happens when, but not what happens to them: that their power goes off on
   installation day, who must be home, what papers they must hand over.
4. Three honesty slips remain: the proposal still says the system "adds to its value" and that the net metering
   agreement "transfers to the new owner" (the website was corrected last round, the proposal was not); the
   net-metering page's illustration figures have drifted from the engine after the losses batch ("about 3 years"
   and "three quarters off" against 3.6 years and 69% today); the battery-first estimate promises "→ about ₱0".
5. One visible bug on the first document the customer ever gets: the card says the roof makes "around 6.9 times
   what your house uses" beside "about 2,110 kWh"; 2,110 / 338 is 6.2, which is what the PDF says.

## What happened to round 2's items

| Round 2 | Status now |
|---|---|
| C1 placeholders published | Fixed: public build drops them; "Talk to us" hidden while blank |
| C2 net-metering figures not from the engine | Fixed then drifted again (M3 below) |
| C3 "often lower than the estimate" | Fixed everywhere, including docs/marketing.md |
| C4 battery 13 kWh vs 15.36 kWh on the proposal | Fixed: 15 kWh on every proposal line; but the engineer's glance strip still says 13 (M7) |
| C5 catalogue names on page 2 | Fixed: "Solar panels: 7 × 585 W (Blue Carbon)"; the roof check PDF still prints the catalogue panel name (m1) |
| C6 relative og:image | Fixed: absolute og:image and og:url per page |
| M1 installer positioning | Fixed: "Solar engineering for homes", "What you get on paper", four hero points |
| M2 proposal never says what the firm delivers | Fixed: "What you get" block |
| M3 empty warranties card | Fixed: `[data-warranty-wrap].is-empty` hides every warranty claim |
| M4 ₱150 bill → ₱189,000 | Fixed: refused under 60 kWh with a plain message |
| M5 double header on /estimate | Fixed: embedded widget without its own header and footer |
| M6 estimate not carried forward | Fixed on the proposal and the card; not on the roof check PDF (M8) |
| M7 claims needing a source | Fixed on the site; the proposal's "move house" answer was missed (C2) |
| M8 estimate copy slips | All fixed, including "before any fixed charges" and "message or call" |
| M9 proposal leftovers | Fixed (plural technicians, "your roof check", one installation-day payment line, tools folded, one "Valid until"); the map pin still prints in the customer block (M6) |
| M10 roof check shows no readings; orphan page | Fixed: "Measured on your roof" with the time, next step kept together |
| M11 reading time never prints | Fixed: "(clear sky, 11:30 AM)" |
| M12 QR and summary point at the back office | Fixed: `SOLARAPP_WEBSITE_URL`, QR to pldevinc.com/estimate?utm_source=card, "Run your own: pldevinc.com/estimate" |
| M13 lead e-mail one dense paragraph | Fixed: one fact per line, subject with the number and the town |
| m1 Settings wording | Partly: "Blank fields are left off" added; "PEE licence", "After a booking, you reach out", "Warranties printed on the proposal" unchanged (m3) |
| m2 term consistency | Mostly: ERC and BOM consistent; "net metering meter" survives in the schedule row (m1) |
| m3 three button labels | Fixed: "Get my free estimate" everywhere |
| m4 footer headings, privacy phone sentence | Fixed |
| m5 summary links | Fixed |
| m6 program assumption lines | Fixed |
| m7 small page wording | Fixed |
| m8 savings order | Improved: "Savings against your bill today" row added |

## Findings, ranked by lost sales first

Severity: Critical (costs the sale or breaks trust), Major (a gap a buyer or a competitor will find), Minor
(polish). Effort: S under an hour, M a day, L more.

| # | Sev. | Eff. | Tags | Where | Finding |
|---|---|---|---|---|---|
| C1 | Critical | S | [sales][copy] | proposal page 1 (`quotation_pdf.py` ~L300, after the customer block) | The proposal never states the customer's problem and the solution in one place; it opens with the price box |
| C2 | Critical | S | [copy][sales] | `quotation_pdf.py:520` | "adds to its value" and "the net metering agreement transfers to the new owner": unverifiable, and contradicts the corrected website answer |
| C3 | Critical | S | [sales][copy] | estimate `Estimate.tsx:23-27`; proposal `quotation_pdf.py` `battery_backup_line` and System information | The battery is a number, never what it runs; the engine already knows it holds Maria's whole night |
| M1 | Major | S | [website][copy] | `site/pages/net-metering.html:33-36` | Illustration figures drifted from the engine: "about 3 years" / "three quarters" against 3.6 years / 69% today |
| M2 | Major | S | [website][copy] | `Estimate.tsx:318-321` (hero) for the battery-first goal | "₱4,058 → about ₱0" overpromises; the proposal for the same kind prints ₱158 and 286 grid hours |
| M3 | Major | S | [bug][copy] | `reports/card.py:146` | Card: "around 6.9 times what your house uses" beside "about 2,110 kWh"; the PDF says 6.2 (at-panels ratio against an at-meter figure) |
| M4 | Major | S | [sales][copy] | proposal Schedule (`quotation_pdf.py` ~L480) | Nothing about the customer's side of installation day: power off, who is home, what to hand over |
| M5 | Major | S | [copy][sales] | proposal System information row "Share of your usage covered by solar" | On the no-battery proposal it reads 29% after the website said 102%: two measures with one name |
| M6 | Major | S | [crm][bug][copy] | `api/leads.py` `project_from_lead`; `quotation_pdf.py` customer block; `customer_pdf.py:~80` | The hand-off drops the town from a landmark address and prints the town-centre pin on customer documents as "Map pin" |
| M7 | Major | S | [copy][ux] | `AssessmentPage.tsx:370,555` | The engineer's glance strip says "13 kWh battery" while the proposal says 15 kWh: the engineer will quote one and hand over the other |
| M8 | Major | S | [website][copy] | home page card and tag `index.html:34-36`; `quick.py` GOAL_LABEL; `quotation_pdf.py` KIND_LABEL | Three names for the third system kind, and "a bigger battery" is not what the engine does |
| M9 | Major | S | [sales][copy] | proposal Your questions | Objections a comparing buyer will raise and the proposal does not answer: typhoon, battery life, "what if it makes less" |
| M10 | Major | S | [copy][sales] | proposal Reminders (`lead_estimate_sentence`); card `estimate_line`; roof check PDF | The bridge says what the estimate was but not what changed and why; the roof check PDF has no bridge at all |
| M11 | Major | S | [website][copy][crm] | `Estimate.tsx:380` thank-you | The thank-you promises a message but does not set up the path (visit → card → audit → proposal) |
| m1 | Minor | S | [copy] | several, listed below | Term slips: "net metering meter", "This estimate comes from…" on the card, catalogue panel name on the roof check, "2 × 12 kW hybrid inverter", "1 evening", tools line on the website breakdown, home step 5 sequence |
| m2 | Minor | S | [copy] | proposal Your savings; website "How we worked this out" | Savings printed to the centavo over 25 years |
| m3 | Minor | S | [copy][crm] | `LeadsPage.tsx:275`, `types.ts:802,811`, `SettingsPage.tsx:74` | Owner-facing names: "Start assessment" next to "Projects"; Settings labels left from round 2 |
| m4 | Minor | S | [copy] | `docs/marketing.md` | Stale: job list → Leads page; "Where the estimate lives" predates the website process; ad 2 figures and the "45 months" frame need the engine |
| m5 | Minor | S | [copy][website] | `brownouts.html:22`, `about.html:12` | "a fraction of a second" switch-over and "a skilled technician" need the datasheet and the crew line |
| m6 | Minor | – | [copy] | `quotation_pdf.py:207` | "A test and switch-on report on installation day" is promised; the app does not produce one yet (plan item 27) |
| m7 | Minor | – | [pm] | project head stage pill | The stage pill carries the PM stages (sourcing to closed); by decision until the PM module, noted only |

### Critical

**C1 [sales][copy] The proposal never states the problem and the solution. S**
Where: `docs-filled/proposal.pdf.txt` page 1. After the header the eye lands on "TOTAL CONTRACT PRICE PHP
314,600.00", then "Summary of charges", then a savings table of nine rows. The customer's situation (the ₱4,058 bill,
the planned aircon, the brownouts) and the answer to it are scattered across "Your savings", "System information"
and "Your questions" on three pages. A buyer with two quotes on the table reads the first paragraph of each; ours has
none. Why: the owner's own brief ("translate the quantity take-offs and plans to something the customer would
really care about and provide a solution to their problem") is exactly this paragraph. Fix: an "IN SHORT" block
between the customer block and the two columns (`quotation_pdf.py`, after `story.append(cb)`), built only from
fields the results already hold. For Maria's hybrid proposal it reads:
> **In short.** Your bill today is PHP 4,058 a month for 338 kWh; with the second aircon you plan to add it would be
> about PHP 5,379. Seven panels (4.09 kWp) and a 15 kWh battery cover 92% of what the house uses: the bill comes down
> to about PHP 291 a month, and the battery carries your evening when the grid drops. PHP 314,600 installed, permits
> and VAT included; it pays for itself in about 5 years.
Template: `Your bill today is PHP {bill_today} a month for {bill_kwh} kWh{; with the appliances you plan to add it
would be about PHP {bill_before}}. {n} panels ({kwp} kWp){ and a {battery} kWh battery} cover {coverage}% of what
the house uses: the bill comes down to about PHP {bill_after} a month{kind sentence}. PHP {total} installed, permits
and VAT included; it pays for itself in about {payback} years.` Kind sentences: net metering `; there is no battery,
so the house runs on the grid at night and in a brownout`; hybrid `, and the battery carries your evening when the
grid drops`; battery-first `, the battery carries the house at night, nothing is sold back, and the grid steps in only
in long rainy spells (about {loss_of_load_hours} hours a year)`. Round payback to the half year ("about 5 years",
"about 3½ years"). The same five sentences, shortened, are the "Sending the proposal" Messenger template in
docs/marketing.md, so the owner's message and the paper agree.

**C2 [copy][sales] The proposal's "What if we move house?" makes two claims the website no longer makes. S**
Where: `backend/solarapp/reports/quotation_pdf.py:520` prints `The system stays with the house and adds to its
value. The net metering agreement transfers to the new owner.` The home page (`index.html:149`) was corrected last
round to `Net metering is tied to the service connection, so the new owner continues it with the electric company;
we help with the paperwork.` Why: "adds to its value" is a claim nobody can back, and the transfer rule is a
verify-with-the-DU item (plan section 8); a customer who reads both will notice the paper says more than the site,
and the paper is the one they sign. Fix, by kind:
- net metering and hybrid: `The system stays with the house. Net metering is tied to the service connection, so the
  new owner continues it with the electric company; we help with the paperwork.`
- battery-first (no net metering): `The system stays with the house, and the new owner keeps using it. We hand over
  the plans and the papers.`
Keep the owner's verification of the transfer rule on the list in section "Ask the owner" below.

**C3 [sales][copy] The battery is a quantity, never what it does for the customer. S**
Where: estimate `Estimate.tsx:23-27` prints `10 kWh lithium battery` in the system line and nothing else about it;
proposal System information prints `Battery backup: Designed to carry 1 evening without sun; in the rainy season
the grid covers the rest.` (`battery_backup_line`), and the brownout answer says `A 15 kWh battery carries lights,
fans, the refrigerator, TV and wifi through a typical evening; running aircon shortens that.` Why: "10 kWh" and "1
evening without sun" are the engineer's units. The buyer's question is "will the aircon run tonight if the power
goes?" and the engine can answer it: for Maria's house the reconciled load profile (`results.json`,
`audit.load_profile_kw`, average month) uses 9.3 kWh between 6 pm and 6 am, aircon included, against 13.1 kWh
usable in the 15.36 kWh battery at 85% depth of discharge. So the honest sentence is stronger than the one printed.
Fix (engineering agent to confirm the formula): usable = BOM kWh × depth of discharge; night kWh = the reconciled
profile summed 18:00 to 06:00; if usable ≥ night kWh print
> Battery: 15 kWh, enough for a whole night of your usual use (about 9 kWh from 6 pm to 6 am, aircon included),
> recharged by the panels the next day.
else print `Battery: {kwh} kWh, about {usable / evening average kW:.0f} hours of your evening use (lights, fans,
refrigerator, TV, Wi-Fi; aircon shortens that).` Keep "running aircon shortens that" only when the aircon is not
inside the night figure. On the website estimate there is no audit, so use the pattern shape (`quick.py` SHAPES)
scaled to the monthly kWh: for Pila, 333 kWh, "all day", the night share is 46% of 10.95 kWh a day = 5.0 kWh against
8.5 kWh usable, so the system line becomes `10 kWh lithium battery (enough for a typical night of your use when the
grid is down)`; when it is not enough, `(about N hours of your evening use)`. The brownouts page's "usually 8 to 15
kWh" line can then point at the estimate: "the estimate tells you how many hours yours holds".

### Major

**M1 [website][copy] The net-metering page's illustration figures have drifted from the engine. S**
Where: `site/pages/net-metering.html:33-36`: `4.1 kWp / 7 panels · about ₱181,000 · about 3 years / pays for
itself · about three quarters / off the bill`. Engine on 9 Oct 2026 for 500 kWh, Tanauan, mostly evening, net
metering (`shots/flow.json` result_net_metering): 7 × 585 W (4.09 kWp), ₱181,000, `₱6,003 → about ₱1,851` (69%
off), `pays for itself in 3.6 years`. The losses-at-the-meter batch moved the payback from 3.3 to 3.6 years and the
cut from 75% to 69%; the page kept the old words. Why: the visitor reads "about 3 years" and one click later sees
"3.6 years" from the same company; the first thing the site teaches them is that the site rounds in its own favour.
Fix: `under 4 years` and `about two thirds` (both true at 3.6 years and 69%, and both survive small price moves).
Then pin them: a test in `backend/tests/test_site.py` that runs `quick_estimate` for the page's inputs and asserts
the kWp, the rounded price, that payback is under 4 years and the cut is between 60 and 72%; or generate the four
tiles at build time from the engine with a "from our own estimate on {date}" note. No test covers this today.

**M2 [website][copy] The battery-first estimate says "→ about ₱0". S**
Where: `Estimate.tsx:318-321`, case Los Baños 338 kWh morning battery-first: `₱4,058 → about ₱0`, `about ₱4,058
less each month, before any fixed charges on your bill`. The owner's correction says this kind keeps the grid as
backup and bills the hours it steps in; the proposal for the same kind (`docs-off_grid/proposal.pdf.txt`) prints a
bill of PHP 158 and "about 286 hours on 71 days" of grid power, and the estimate's own text under it says "the grid
would still supply…" only when imports exceed 50 kWh a year. Why: "₱0" is the one figure a customer repeats to the
neighbours and the one the first bill contradicts (the fixed and minimum charges never go away). Fix: when the goal
is battery-first or the bill after is under ₱100, print the hero as `₱4,058 → about ₱0 for energy` and the sub-line
as `only your electric company's fixed charges remain; the grid still covers long rainy spells`. The same rule for
the proposal's "Your bill with solar" row: never below the owner's fixed-charge figure once that setting exists
(plan item 10 asks the owner for it).

**M3 [bug][copy] The card's "times what your house uses" uses the at-panels figure. S**
Where: `reports/card.py:146` `ratio = prod["avg_monthly_kwh"] / bill_kwh` (at the panels, 2,331 kWh) while line 131
prints the at-meter figure (2,110 kWh) in the same sentence: `Your roof can make about 2,110 kWh, around 6.9 times
what your house uses` (`docs-filled/card.png`). The roof check PDF (`customer_pdf.py`) divides the at-meter figure
and says 6.2. Why: the card is forwarded to relatives; the PDF is read at the table; the two disagree on the one
number the customer can check with a calculator. Fix: `ratio = monthly / bill_kwh` (the rounded at-meter figure
already computed on L131); the sentence then reads "about 2,110 kWh, around 6.2 times what your house uses".

**M4 [sales][copy] The schedule says what happens when, not what happens to the customer. S**
Where: proposal Schedule rows `30 Oct 2026 Materials delivered to your house / Installation (1 day, crew of 6) /
System switched on and tested` and Your questions. Nothing tells the customer that their power will be off, that
someone must be home, that the gate must be open for a crew of six at 06:15, or what papers they must hand over.
The internal hour plan knows the arrival (`fr['arrive']` 06:15), the crew size and the energize window; the outage
length is not computed anywhere. Why: these are the questions the customer asks on the phone the night before, and
the ones a competitor's proposal answers to look organised. Fix: an "ON INSTALLATION DAY" paragraph under the
schedule, from the program's figures plus one owner setting:
> Our crew of {persons} arrives about {arrive} and is usually done by mid-afternoon. We need someone at home, the
> gate open for the materials, and access to the roof, the panel board and the wall where the inverter{ and the
> battery} go. Your power is off for {outage, owner to confirm} while we connect the inverter to your panel board;
> we tell you before we switch it off.
and a "WHAT WE NEED FROM YOU" line for the net-metering kinds: `A copy of your latest bill and a valid ID for the net
metering application (your electric company may also ask for proof that you own the house; we confirm the list with
you), and your signature on the forms.` The outage length is an input only the owner has (typical cut-over time at
the panel board): make it a setting under Program of works with the help text "printed on the proposal; blank prints
'for a short while'". Mark the document list "verify with Meralco and BATELEC II" until the DU pack exists (plan
item 20).

**M5 [copy][sales] "Share of your usage covered by solar" means two different things on the website and the proposal. S**
Where: website net-metering result `What it makes: about 512 kWh a month, 102% of the 500 kWh you use` (production
over use); net-metering proposal (`docs-net_metering/proposal.pdf.txt`) `Share of your usage covered by solar 29%`
(`sizing.coverage_pct`, the share met directly, since there is no battery) beside `Solar power made about 5,966 kWh a
year at your meter` (111% of the 5,377 kWh used). Why: the customer who saw 102% on the website and reads 29% on the
proposal concludes the roof visit cut the system by two thirds, and nothing on the page explains the drop. Fix the
row label by kind: net metering `Used straight from the panels: 29% of your usage; the rest of the day's solar goes
to the grid and is credited on your bill`; hybrid `Covered by solar, by day and from the battery: 92%`; battery-first
`Covered by the panels and the battery: 97%`. And append the ratio to the production row everywhere: `about 5,966
kWh a year at your meter, 111% of what you use`, so the website's figure reappears on the proposal by name.

**M6 [crm][bug][copy] The hand-off loses the town and prints the town-centre pin as if it were the house. S**
Where: `api/leads.py` `project_from_lead`: `address=lead.address.strip() or place_label(...)`, so a visitor who
typed a landmark ("Brgy. Labuin, near the chapel") becomes a project whose address is the landmark alone; the
project list row and the proposal would print it without "Pila, Laguna" (`shots/office.json` list row; I overwrote
the address by hand before generating the documents). The pin is the town centre (`find_town`), and both customer
documents print it: proposal customer block `Map pin 14.23300, 121.36500` (`quotation_pdf.py` cust_block), roof
check `Map pin: 14.23300, 121.36500` (`customer_pdf.py`). Why: a customer sees a coordinate on a signed document that
is not their house; an engineer sees an address with no town. Fix: `address = ", ".join(x for x in (lead.address,
place_label(town, province, None)) if x)` when the landmark does not already contain the town; drop the map-pin line
from the proposal (round 2 M9 asked for it) and keep it on the roof check only in small print, as it is.

**M7 [copy][ux] The engineer's glance strip and the proposal disagree on the battery. S**
Where: `frontend/src/pages/AssessmentPage.tsx:370` `batteryKwh = sizing?.battery?.installed_kwh` → the At a glance
tile `7 panels · 4.09 kWp / 13 kWh battery` (`shots/office.json`), while the proposal, the card-to-be and the project
list row use the BOM figure (`api/assessments.py:74` `customer_battery_kwh`) → 15 kWh. Why: the engineer on the
phone with the customer reads the strip and says "13"; the proposal that follows says "15"; the customer asks which
one they are paying for. Fix: compute the tile from the BOM lines the way the list row does (`customer_battery_kwh`
is importable; the frontend can read `pricing.lines` the same way), fallback to the sizing only without pricing.

**M8 [website][copy] Three names for the third system kind, and one claim the engine does not make. S**
Where: home page `index.html:34-36` tag `Off the grid`, title `Independent from the grid`, text `The panels and a
bigger battery carry the house…`; estimate goal `Battery first, nothing sold back` (`Estimate.tsx:13`); proposal
`Solar with battery, no export (the grid as backup)` (`quotation_pdf.py` KIND_LABEL); estimate assumptions `solar
with a battery and no export (the grid as backup)` (`quick.py` GOAL_LABEL). "Bigger battery": for the same 338 kWh
house the engine gave 10 kWh both as hybrid (Pila) and as battery-first (Los Baños); it adds panels (5 → 8), not
battery. Why: a buyer who picks "Off the grid" on the home page, "Battery first" on the estimate and receives
"Solar with battery, no export" on the proposal is not sure it is the same product; "independent from the grid"
contradicts the owner's definition in the same card. Fix, one customer name everywhere, the estimate's:
- `index.html:34` tag `Backup first`; L35 `Battery first, nothing sold back`; L36 `More panels and a battery carry
  the house day and night; the grid steps in only when both fall short, and nothing is sold back. For homes that
  cannot or do not want to apply for net metering.`
- `quotation_pdf.py` KIND_LABEL off_grid `Battery first, nothing sold back (the grid as backup)`; `quick.py`
  GOAL_LABEL off_grid `battery first, nothing sold back (the grid as backup)`.
- The back office keeps its own label (`AuditResults.tsx:11`), which already says "Battery first".

**M9 [sales][copy] Objections a comparing buyer raises and the proposal does not pre-empt. S (after the owner's data)**
Checked against the five on the role's list: brand and warranty (brands line and warranties print when filled:
good), after-sales ("Who looks after it": good), net-metering paperwork (good, with the gap before the two-way meter
explained: very good), roof penetration (good). Missing:
- Typhoon. The proposal says the rails "clamp to the roof framing through the sheet with sealed fasteners" and
  nothing about wind. In Laguna and Batangas this is the first question after the price. The app has no mounting
  check yet (plan item 12), so nothing can be claimed; ask the owner for the mounting system's rated wind speed
  from the maker's datasheet and whether the PEE designs to the NSCP wind zone; until then add only what is true:
  `Rails are bolted to the purlins (the roof framing), not just to the sheet, with the fasteners and sealant on the
  parts list.`
- Battery life. "a new battery after 10 years" sits in a 60-word reminder. Add to Your questions: `How long does the
  battery last? We plan on a new battery after about 10 years and a new inverter after about 12; the savings on
  page 1 already include both.` (figures from `economics.assumptions`, which the owner edits).
- "What if it makes less than you say?" The roof check says "some years will be higher and some lower"; the
  proposal only says "Savings are estimates". Add: `What if it makes less? The figures are a typical year from
  long-term sun records and the readings on your roof; a rainy year makes less, a dry one more. The inverter's
  screen or app shows the real output, and we compare it with the design at switch-on.` (No performance guarantee
  is implied; none exists.)

**M10 [copy][sales] The bridge from the estimate says what it was, not what changed. S**
Where: proposal Reminders `Your website estimate on 9 Oct 2026 was PHP 263,000 for 5 panels and a 10 kWh battery.
This proposal is measured on your roof and includes the appliances you plan to add.` The price rose ₱51,600 and
the reader must find "7 panels" and "15 kWh" elsewhere to see why. The card prints `Your estimate said about PHP
263,000; the visit settles the exact figure` and no panel count, although the Messenger template in
docs/marketing.md promises "Your roof holds [N] panels; you need about [n] to cover your bill". The roof check PDF
has no bridge at all (`customer_pdf.py`). Why: docs/marketing.md says it best, "a price that moves after
measurement is a trust event when the reason is on paper". Fix:
- proposal: `Your website estimate on 9 Oct 2026 was PHP 263,000 for 5 panels and a 10 kWh battery. Measured on your
  roof and with the second aircon you plan to add, it is 7 panels and a 15 kWh battery at PHP 314,600.` (deltas from
  `doc.lead.estimate` against the BOM; the "with the appliances" clause only when `includes_future_loads`).
- card and roof check PDF: `Your estimate said about 5 panels and ₱263,000; the visit settles the exact figure.`
  (`est.panels` is on the record; add `reading_lines`-style `estimate_line` to `customer_pdf.py` under "Your bill
  shows").
- under the total box: `That is about 78 months of your bill today.` (contract ÷ `bill_today_monthly`; 44 months on
  the net-metering proposal). docs/marketing.md's "about 45 months" frame then becomes a computed line instead of a
  guess.

**M11 [website][copy][crm] The thank-you page promises a message but does not set up the path. S**
Where: `Estimate.tsx:380` `Thank you, Maria Santos. We will message or call you within one working day to pick a
visit day; visits are usually within the week. Have a recent bill handy.` Why: this is the most attentive moment of
the whole funnel and it says nothing about the card, the audit or the proposal, which the home page promised three
screens earlier; the visitor who did not read the home page does not know a document is coming the same evening.
Fix:
> Thank you, Maria. {Owner} will message or call you within one working day to pick a day. Then: the roof visit,
> about an hour and free; your roof check card the same evening; the energy audit over your bill and appliances;
> your proposal within two working days, valid 15 days. Have a recent bill handy.
("two working days" and "15 days" are the home page's promise and the pricing setting `quotation_validity_days`;
use the first name only when the visitor typed two words.) Keep the Messenger button and "Copy my estimate".

### Minor

**m1 [copy] Term and wording slips. S**
- `pricing/program.py:376` schedule row `Electric company inspection; net metering meter installed` → `Electric
  company inspection; two-way meter installed` (the glossary; the proposal's own answer says two-way meter).
- `reports/card.py` footer `This estimate comes from the measurements we took on your roof…` → `This roof check
  comes from…`; `customer_pdf.py` heading `About this estimate` → `About this roof check` (the customer's
  "estimate" is the website figure).
- `customer_pdf.py:~83` `Panel: 585W Monofacial solar panel` (catalogue string, the round 2 C5 fix stopped at the
  proposal) → `585 W panel (Blue Carbon)` from quantity, rating and supplier.
- `Estimate.tsx:23` `2 × 12 kW hybrid inverter` → `2 × 12 kW hybrid inverters` (3,000 kWh case).
- `quotation_pdf.py` `battery_backup_line` `Designed to carry 1 evening` → `one evening` (superseded by C3).
- `Estimate.tsx` "How we worked this out" prints `Installation tools ₱1,223` as its own line while the proposal folds
  it into Installation and permits (`customer_sections`); fold it on the website too so the two breakdowns match.
- `index.html:56` step 5 `One or two days on site, then we file the papers with your electric company` while the
  schedule starts the net metering application the day after signing; say `We file the papers with your electric
  company as soon as you sign, install in one or two days, and the two-way meter follows the inspection.` (the
  sequence itself is the engineering agent's item; align the words to whatever it becomes).

**m2 [copy] Savings printed to the centavo. S**
Proposal `Saved over 25 years PHP 1,414,229.20`, `Savings in the first year PHP 61,062.36`; website `Saved over 25
years: about ₱1,025,889`. Keep the contract and the payment schedule exact; round the savings rows as a person says
them: `about PHP 1.4 million`, `about PHP 61,000`, `about ₱1.03 million`.

**m3 [copy][crm] Owner-facing names. S**
- `LeadsPage.tsx:275` `Start assessment` beside a nav that says Projects and an empty state that says "New project"
  → `Start project` (the brief's own words: start a project from a booking).
- Round 2 m1 leftovers: `types.ts:802` and `profile.py` `PEE licence number (PRC)` → `PEE license number (PRC)`;
  `types.ts:811` `After a booking, you reach out` → `Callback promise (printed on the thank-you page)`;
  `SettingsPage.tsx:74` `Warranties printed on the proposal` → `Warranties (website, estimate page and proposal)`.

**m4 [copy] docs/marketing.md is one round behind. S**
- "the lead appears on the job list" and "Measure five numbers every week, from the job list header" → the Leads
  page: estimates run, leads, visits booked, converted; quoted and signed from the projects.
- "Where the estimate lives: Now, before the website exists" → the website is its own process (README "Set it up:
  two tunnels"); the embed snippet points at `solar.pldevinc.com/widget/quick.js` while README says
  `pldevinc.com/widget/quick.js`.
- Ad 2 `A ₱5,000 bill becomes about ₱1,100. The system pays for itself in under 4 years` → engine today for ₱5,000 in
  Tanauan, evening, net metering: `₱5,003 → about ₱1,460`, 4.0 years → `A ₱5,000 bill becomes about ₱1,500, and the
  system pays for itself in about 4 years`; and keep the rule "verify against the estimate on the day it is posted".
- The landing headline `Your ₱4,000 bill, down to a few hundred` holds (₱767 without a battery, ₱144 with, in Pila).
- "The safe frame is 'about 45 months of your bill'" → use the computed line from M10 (44 months net metering, 78
  hybrid for the sample house).
- The roof-visit template "you need about [n] to cover your bill" → the card line from M10 supplies [n].

**m5 [copy][website] Two lines that need a source. S**
`brownouts.html:22` `The switch-over is automatic and takes a fraction of a second.` → verify the transfer time on
the Felicity inverter's datasheet (and keep "a fraction of a second" only if it is under one second, which
UPS-mode hybrids usually are; otherwise "within a few seconds"). `about.html:12` `Our crew of a team lead, a skilled
technician and helpers` while the proposal prints `1 team lead, 2 skilled technicians, 3 helpers` → `a team lead,
skilled technicians and helpers`.

**m6 [copy] A promised document the app does not produce. –**
`quotation_pdf.py:207` "A test and switch-on report on installation day" (added on round 2's advice). The
commissioning report is plan item 27, missing. Not a fabrication, but a promise the owner must keep on paper until
the app prints it; keep a one-page form in the truck.

**m7 [pm] The stage pill carries the PM stages. –**
`AssessmentPage.tsx:401` offers Sourcing, Installing, Commissioned, Net metering, Closed on an engineering record.
DECISIONS.md keeps them there until the PM module; nothing else in the customer path depends on them. Noted only.

## What a lead carries into the engineering app, and what the CRM will need [crm]

Carried today (`models.Lead`, `project_from_lead`): name, contact (one free-text field: a number or a Messenger
name), town and province, landmark address, the phone's pin when used, preferred time, consent and the privacy
notice version, source (UTM tags, fbclid, referrer, page), the estimate snapshot (goal, panels, kWp, battery, price,
bill before and after, payback, monthly kWh and pesos, pattern), notes, status with a closed reason, the project id.
The project gets the customer reference, the pin or town, the bill as the first bill entry, the system kind from the
goal, the estimate snapshot for the bridge sentences, and `lead_id`. That is the right boundary: the engineering
record carries no marketing data.

What the CRM will want that is not captured, in order of how often the owner will miss it:
1. Contact type: split "mobile number or Messenger name" into two fields, or store a type; the CRM cannot dial a
   Messenger name or message a number. (Website form, S.)
2. Timestamps per status (contacted at, visit booked for, converted at): today only `updated_at` and the audit log
   line; the funnel's "visits within the week" promise cannot be measured. (Model, S.)
3. The visit date and time as a field, not a note, so the card's next step and the CRM's calendar come from one place.
4. A qualifying question for net metering: does the visitor own the house (the DU asks for proof of ownership;
   verify the list). One optional chip on the booking form: "I own the house / I rent".
5. The bill photo: the templates ask for it on Messenger; the form cannot take it. Leave it to Messenger until the
   CRM exists, but record "bill photo received" as a status note.
6. The electric company (Meralco, BATELEC II, FLECO) derived from the town, so the proposal's net-metering timeline
   and the DU pack can differ per DU later.
7. Lost reasons as a fixed list (price, no budget, chose another installer, roof not suitable, moved) instead of free
   text, so the owner can count them.

## What is sound (keep it)

- One engine, one figure: the net-metering page's ₱181,000 is the engine's ₱181,000; the website estimate is carried
  onto the proposal and the card; the battery on the proposal is the unit the customer pays for on every line.
- The estimate leads with the bill, the payback and the price; "before any fixed charges on your bill"; the battery
  as a priced add-on with "it adds little to the savings"; tiny usage refused in plain words; the 40-panel cap
  explained; the out-of-area message; the battery-first goal described in the owner's corrected words ("nothing is
  sold back", "the grid steps in only when both fall short") on the website, the estimate and the proposal, with the
  hours the grid steps in printed on the proposal.
- The booking: name and a number are enough; a landmark instead of an address; best time chips; the privacy line;
  the thank-you with a dated promise; "Copy my estimate" with "Run your own: pldevinc.com/estimate".
- The owner's lead e-mail: one fact per line, the number and the town in the subject, the promise the thank-you made.
- The Leads row: contact to tap, what they want, what they saw, the source, notes, a status with a closed reason.
- The proposal: "What you get" in the customer's words; the solar and battery parts named under the total; "Your
  questions" with the gap before the two-way meter explained with dates; the bill month by month in pesos; the
  warranties and the PEE line only when filled; the acceptance block with where to pay; the roof plan with "7 of your
  panels here; room for 8 more"; the contact footer on every page.
- The roof check and the card: "Measured on your roof" with the sky and the time, "That is a good roof", the shade
  notes in plain words, the full-roof figure stated as a multiple of the bill, the next step with a date, the QR
  code tagged `utm_source=card`.
- Honesty gates: placeholders stripped from the public build; warranty claims hidden until the years are filled;
  customer documents and the public estimate refused on test weather, server side; no financing line anywhere; no
  utility name or colours ("your electric company" throughout); every assumption printed in one sentence.

## Ask the owner (inputs no reviewer should invent)

- The typical length of the power cut on installation day, for M4 (a setting, printed on the proposal).
- The mounting system's rated wind speed from the maker, and what the PEE designs to, for the typhoon answer (M9).
- The inverter's grid-to-battery transfer time from the datasheet (m5).
- The DU's current document list for the net-metering application, and the transfer-on-sale rule (C2, M4).
- The fixed or minimum charges on a local bill, so "→ about ₱0" can become "→ the fixed charge" (M2).
- The profile: phone, Messenger, Facebook, e-mail, owner's name, PEE and PRC number, brands, the five warranty
  figures, where to pay; three real photos with the town and the system size.
