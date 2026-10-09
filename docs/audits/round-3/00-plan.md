# Audit round 3: the five reports in one plan

Five reviewers (cyber security, solar engineer, financial analyst, UI/UX, marketing and
sales) audited the engineering app, its documents and the website on 9 October 2026, each
on its own server with the real weather data, read-only on the repository. Their full
reports are beside this file; the brief they worked from is `brief.md`. This page is the
owner's summary: the verdict per discipline, what is a plain fix, what needs the owner's
decision, what only the owner can supply, and the order I propose.

## Verdicts

| Role | Verdict |
|---|---|
| Finance | The Excel BOQ logic was carried over exactly: every cell of a real Tanauan job reconciles to the peso (contract ₱264,900, OCM and OP ₱16,070 each). There is one OCM share (50 % of the total markup, OP the balance) in the workbook and in the app; the "different percentages" are the markup tiers (10/15/30, freight 15, services 30, pass-throughs 0), all carried. The close-out block (actuals) does not exist in the app: a PM-module gap, not a bug. The money findings are around the build-up, not in it. |
| Security | No critical, no high. Every round-2 finding is fixed and was confirmed live. The accounts system holds under probing (role split, step-up, challenge binding, replay guards, revocation). Two lows: a shared rate-limit dictionary under two locks, and the booking inbox being readable and deletable by engineers (closed in this round's Leads change). |
| Solar engineer | Production, losses, the hourly-year battery, face allocation, drawings, Gantt and cashflow are sound and agree with each other. The electrical design is still not reviewable by a PEE (no string design), and two selection rules sell the wrong hardware: a no-battery net-metering job is sized on the house peak and gets two 6 kW hybrids, and the cheapest-kWh battery is picked at 100 A for a 135 A inverter. |
| UI/UX | Far cleaner than round 2: every page is exactly 1280 or 390 px wide except one, nothing overflows its card, the new sign-in screens and the seven Design and outputs cards work end to end. The "odd sticks" come from six stylesheet causes, one fix each. The one regression (the People table on a phone) is fixed in this round's commit. |
| Marketing and sales | Honest and consistent end to end (one engine, estimate carried onto the proposal and card, no financing, no utility branding, placeholders hidden). But the documents are engineering summaries, not the customer's problem and its solution; five small fixes close that gap, and one stale "adds to its value" line survives in the signed document. |

## Already done in this round

- The Leads tab is out of the engineering app; the booking inbox (list, statuses, notes,
  delete, funnel) is owner-only on the server; everyone signed in sees the open bookings
  under Projects › "From a website booking" and can start a project from one. (Security #2,
  the owner's directive.)
- The People table lays out as cards on a phone; the Settings page fits 390 px again.
  (UX #1.)

## A. Plain fixes, no decision needed

Bugs and slips the reviewers proved. Each is small; together about two days.

| Ref | What | Where |
|---|---|---|
| Eng E-03 | Battery picked on price per kWh at 100 A for a 117–135 A inverter, then a 250 A breaker on 35 mm² cable the app rates 170 A; warnings fire but every document prints. Select on continuous current first; refuse the proposal on a failed battery circuit. | `pricing/boq.py` |
| Eng E-04 | AC side: 63 A breakers on 40 A wire, no grid-side pass-through current, 15 m of THHN for three circuits. | `pricing/boq.py` |
| Eng E-05 | FS-INV-008 is grid-interactive "yes" with no certificate on file, so no warning and no certificate line on a net-metering proposal. Warn until the listing is recorded. | `pricing/boq.py`, `quotation_pdf.py` |
| Eng E-06 | BOM over-counts: 4 SPDs per board, 2 enclosures per inverter, an ATS on a hybrid with its own transfer; omits array bonding, L-foot fasteners, placards, a visible AC disconnect, monitoring. | `pricing/boq.py` |
| Eng E-12, Mkt M3, UX 12 | Card ratio uses the at-panels figure ("6.9 times" vs 6.2); "1 panels", "1 rows, 2 lines each", "23.8 C per kW/m2", net-metering sentences on the no-export proposal, 14 vs 15.4 kWh on one screen, README test count. | `reports/card.py`, `boq.py`, `simulation.py`, `quotation_pdf.py` |
| Fin 1 | A pricing-settings change does not mark results stale and the next Calculate re-prices silently, by anyone, at any stage. Store the settings version with the results; warn on compute; from stage quoted keep the quoted contract unless the owner confirms. | `api/assessments.py`, `pricing_routes.py` |
| Fin 5 | Battery and inverter replacement costs taken ex-VAT in the 25-year economics (overstates by ₱29,110 on the worked job). | `pricing/economics.py` |
| Fin 8, 9 | Roof closed in 0 days crashes pricing; VAT computed before the rounding pesos. | `pricing/engine.py`, `schemas.py` |
| Fin 6 | The same battery is three figures (website hero 91,600, website line 102,000, proposal 102,417). | `core/quick.py` |
| Sec 1 | The rate-limit dictionary is written under two different locks (sporadic 500). One lock. | `api/auth_routes.py`, `api/quick_routes.py` |
| Sec 3 | Doc drift: the session nonce is a per-person column now, not `data/session.key`; the password-change message overstates. | `docs/security.md`, `DECISIONS.md` |
| Mkt C2 | The proposal still says the system "adds to its value" and the net metering agreement "transfers to the new owner". Replace with the corrected website wording per system kind. | `quotation_pdf.py:520` |
| Mkt M1, M2 | Net-metering page figures drifted ("about 3 years", "three quarters" vs 3.6 years, 69 %); "→ about ₱0" on the battery-first estimate. Pin the page figures with a test. | `site/pages/net-metering.html`, `Estimate.tsx` |
| Mkt M5, M7 | "Share of your usage covered by solar 29 %" after the website said 102 % (two measures, one name); the glance strip says 13 kWh while the proposal says 15. | `quotation_pdf.py`, `AssessmentPage.tsx` |
| UX 2–7 | Chart gold as table text (2.42:1); grey `.actions` bars inside white cards (the literal "odd bars"); rows aligned on the bottom edge; KPI tiles off the row line; number columns glued to text; six phone tables without the scroll affordance. One stylesheet fix each. | `styles.css` and the sections named in the UX report |
| UX 8–16 | Cashflow chart skips empty weeks; ragged input grids; Gantt labels truncated; "0k 2k 3k" ticks; the "Grid-interactive: unknown" badge wrapping; profile hints repeating placeholders; phone details. | as named in the UX report |

## B. Decisions the owner must make

| Ref | Question | My recommendation |
|---|---|---|
| Eng E-01 (critical) | A no-battery net-metering job is sized on the house peak (the shower heater plus an aircon), so a 6.43 kWp array gets 2 × 6 kW eco-hybrids in parallel, about ₱50,000 the customer should not pay. Size the inverter on the array for net metering, with a pass-through check of the house peak against the inverter's AC input rating? And may a plain grid-tie unit (OP-INV-004, ₱28,000) be sold on a no-battery job, or is the eco-hybrid always the unit? | Size on the array for net metering; keep the peak rule for the battery kinds but let the owner mark which loads are backed up. Allow grid-tie units only if you say so; the default stays the eco-hybrid. |
| Eng E-02 (critical) | String design does not exist and strings are formed by count across roof faces (3 SE + 4 S panels in one series string). Building it needs the panel electrical data (Voc, Vmp, Isc, temperature coefficients) and the inverter's PV voltage window and MPPT count on the Materials page: who enters them, and from which datasheets? | Build the string design per face and per MPPT (Voc cold, Vmp hot, Isc × 1.25, strings per MPPT) and print the string table; a grid job whose panel has no electrical data gets a hard warning. You supply the datasheet values for the panels and inverters you actually sell. |
| Fin 2 | The economics assume a 10-year battery life; your supplier notes say the datasheets give 5. Payback moves from 5.7 to 7.5 years on the worked job. | Default the life to the battery warranty you type in Settings, and print "verify" until it is filled. |
| Fin 3 | The cashflow pays suppliers VAT-exclusive and remits the full output VAT; your NOTES sheet says to take the VAT invoice. Lowest balance would be ₱18,556 lower. | A per-supplier "gives a VAT invoice" flag; remit output less input VAT on the quarterly date. Confirm the date with your accountant. |
| Fin 4 | 5 % agent commission on every job, no per-job switch (₱10,900 of the worked contract). | A per-job commission field, blank meaning the setting, nothing printed to the customer. |
| Fin 10 | Government fees "passed through at cost" (permit, ERC, meter) carry commission and VAT in the workbook and the app alike (₱9,500 becomes ₱11,172). Intended? | Your call, with your accountant. |
| Fin 11 | Engineers can see OCM, OP, landed costs and markups through "Show internal build-up". | Owner-only if you prefer; one server-side strip. |
| Eng E-07 | Mounting and structure: no roof construction record, L-feet at 1.2 m regardless of purlins, no uplift check, while the proposal promises sealed fasteners into the framing on every roof. | Add the roof construction fields to the survey (purlin spacing, material, sheet type) and an uplift check against a wind rating you supply. |
| Eng E-10 | The program starts the net-metering application before the sealed plans, the meter date ignores the CFEI, no lead times. | Reorder the tasks and add the DU checklist and lead times once you confirm them with Meralco and BATELEC II. |
| Mkt C1, C3, M4 | Open the proposal with the customer's situation and the solution in one block ("your bill is ₱4,058, you plan a second aircon, seven panels and a 15 kWh battery bring it to about ₱291 and carry your evening in a brownout"); say what the battery runs and for how long from the engine's own hourly balance; tell the customer their side of installation day (power off for N hours, who is home, papers to hand over). All wording is in the marketing report. | Yes to all three; the installation-day outage length becomes a setting you fill. |
| Mkt M9 | The proposal does not answer typhoon rating, battery life and "what if it makes less". | Answer them once you supply the mounting wind rating and the battery warranty. |
| Eng E-08 | The plan drawing is a customer picture, not an installation drawing (no dimensions, rails, feet, string labels, equipment locations, north arrow). | Build the installation drawing after the string design, since the string labels come from it. |

## C. Inputs only the owner can supply

Panel and inverter electrical data from the datasheets; the eco-hybrid's anti-islanding
listing (or the decision to make FS-INV-001 the grid default); the mounting system's wind
rating; the battery warranty years; the installation-day outage length; the DU's document
list, lead times and transfer rule for Meralco and BATELEC II; the local fixed charges on a
bill; whether reimbursed government fees carry VAT; the three real photos and the profile
fields the website still waits for.

## D. Proposed order

1. **Batch 1, hardware that is wrong (Eng E-01, E-03, E-04, E-05, E-06):** the net-metering
   inverter rule, battery selection on continuous current, the AC side, the certificate
   warning, the BOM counts. These change what a customer is sold. Needs decision E-01.
2. **Batch 2, money (Fin 1, 2, 3, 4, 5, 6, 8, 9):** the settings-version lock on priced
   projects, the battery life, the VAT invoice in the cashflow, the per-job commission, the
   replacement VAT, the one battery figure. Needs decisions Fin 2, 3, 4.
3. **Batch 3, the customer's story (Mkt C1, C2, C3, M1–M7):** the proposal's opening block,
   the battery sentence, installation day, the stale value claim, the drifted page figures.
   Needs the outage-length setting.
4. **Batch 4, the sticks (UX 2–16) and the slips (Eng E-12, Sec 1, Sec 3):** one pass through
   the stylesheet and the copy.
5. **Batch 5, string design and the installation drawing (Eng E-02, E-08, E-09):** the
   largest piece and the one a reviewing PEE reads first. Needs the datasheet values.
6. Later, with the PM module: close-out actuals, roof construction and uplift, the DU
   checklist and lead times, fixed charges.
