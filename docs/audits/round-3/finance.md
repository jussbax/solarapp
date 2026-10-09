# Finance audit, round 3: the pricing engine against PLD_Materials_DB.xlsx

Auditor: finance. Date: 9 Oct 2026. Repository read-only (branch claude/wonderful-maxwell-wawb8t). Server: 127.0.0.1:8050, own database.
Scripts, the priced job (result.json), the proposal and program PDFs and their text are in
`scratchpad/agents3/finance/`.

## Verdict

The Excel BOQ logic was carried over exactly. I dumped the JOB, DRIVERS, LABOR RATES, MOB-DEMOB, TOOLS, LABOR CALC,
REF BASKET, ROUTE and TOLL sheets (formulas and values) and re-applied the workbook's own formulas, cell by cell, to
the BOM the app generated for a real job (Tanauan, 5 x 585 W, 6 kW eco-hybrid, 10 kWh battery, 26.8 extra km). Every
intermediate agrees to floating-point noise: 25 of 25 item lines, the takeoff (JOB!B19:B29), the freight run
(JOB!B84:B89), LABOR CALC column I (man-hours, pace, carry crew, crew choice, days, labor, mob/demob, tools), the
ten build-up lines (JOB!B107:E116), commission, VAT, the contract (264,899.42 -> 264,900), OCM and OP (16,069.62
each), kWp and price per Wp. The repository's own test reproduces the workbook's sample job at 329,300 (7 tests pass).

On the owner's specific worry: the workbook has ONE OCM share (JOB!B104 = 50%) applied to the total markup (D117);
OP is the balance (B125 = D117 - B124). The "different percentages" are the markup tiers (panels and inverters 10%,
batteries and all-in-one 15%, all other items 30%, freight 15%, labor/mob-demob/tools/PPE/seal 30%, permit, ERC and
meter 0%). The app carries all of these: `cfg.job.ocm_share`, `cfg.categories[*].markup_tier`, `job.freight_markup`,
`job.services_markup`, and the three pass-throughs at tier 0 (engine.py:355-368, 380). There is no per-line or
per-category OCM split in the workbook, so there is none to carry. What is NOT in the app is the workbook's close-out
block (JOB!B129:B133 and the per-line Actual column N/O): that is a gap for the PM module, not a bug.

The money findings are therefore not in the build-up but around it: a settings change re-prices old projects
silently on the next Calculate, the customer economics rest on a 10-year battery life the workbook itself doubts,
replacement costs are taken ex-VAT, the cashflow pays suppliers without the VAT invoice the NOTES sheet says to take,
and the 5% agent commission cannot be switched off per job.

## Ranked findings

| # | Sev | Tag | Where | What | Peso effect on the worked job | Fix | Effort |
|---|-----|-----|-------|------|-------------------------------|-----|--------|
| 1 | High | [finance] | api/assessments.py:135-157 (compute), pricing_routes.py:36-42 (PUT config); no stale/version rule for config | A pricing-settings change does not touch stored results (price stays, `results_stale` false, nothing in the list) and the next Calculate, by anyone incl. an engineer, re-prices with the new settings with no warning. Tested: services markup 30->35%, OCM share 50->60%: stored 264,900 (OCM 16,070) -> recomputed 265,600 (OCM 19,606, OP 13,071). Stage (quoted, signed) locks nothing. | +700 on this job for a 5-point change; a battery tier 15->20% would move it by 71,152 x 0.05 x 1.12 = 3,985; a quoted price can change under a signed customer | Store the config `imported_at`/a hash in `results.pricing`; on compute, when it differs, warn "Pricing settings changed since this price: was X, now Y"; from stage quoted onward keep the quoted contract unless the owner confirms the re-price | M |
| 2 | Medium (verify) | [finance][sales] | config.py:303 `battery_life_years=10`; SUPPLIERS!I3 "lithium batteries 10 yrs on the price list (battery datasheets say 5 yrs)" | The proposal prints "Pays for itself in 5.7 years", "Saved over 25 years PHP 976,229", "Yearly return 17%" on a 10-year battery. At the datasheet's 5 years (per-job override, same job): payback 7.5 years, discounted payback 7.8 -> 12.6, NPV 233,229 -> 142,167, IRR 16.7% -> 13.3%, 25-year net 793,342. | -182,887 on the printed 25-year figure; +1.8 years on payback | Default the life to the battery warranty the owner types in Settings (`warranty_battery_years`, profile.py:32) and print "verify" until it is filled; for the Felicity FLB line the list says 10 years, for Blue Carbon 5 vs 10 is unsettled | S |
| 3 | Medium | [finance][pm] | program.py:400-413 (supplier cash), :434 (VAT remittance); NOTES!A5 "Take the VAT invoice (12% more)" | Cash at the suppliers is the VAT-exclusive net (154,635) and the full output VAT (28,382) is remitted. With the VAT invoice the pickup-day cash is 173,191 and the remittance is net of input VAT. Cash margin is unchanged but the lowest balance, which is what the cashflow is for, is 18,556 too kind. Plan item 9 lists it as open. | Lowest balance -41,528 -> -60,084 on 18 Oct; remittance 28,382 -> 9,826 | Add 12% to supplier cash when the supplier gives a VAT invoice (a flag per supplier); remit output less input VAT; date per the quarterly return (verify with the accountant) | S |
| 4 | Medium | [finance] | engine.py:371 `commission = direct * j.agent_commission`; schemas.py PricingJob has no commission field; DRIVERS!B26 = 5% | Every job pays a 5% agent commission on direct cost; the workbook has the same single driver, so this is faithful, but the plan (item 9) wants "a default of none" per job and the owner has no per-job switch. | 9,732 commission + 1,168 VAT on it = 10,900 of the 264,900 contract when there is no agent | Add `commission_pct` to PricingJob (blank = setting), show it in Pricing inputs, print nothing to the customer | S |
| 5 | Medium-low | [finance] | economics.py:91-92 `battery_cost = cust_items["Battery"]["amount"]` (an ex-VAT section amount) | Battery and inverter replacements are charged ex-VAT (91,443 and 29,848) while the proposal's own total box adds VAT to the battery part (102,417). No labor for the replacement either. | 25-year net overstated by 29,110 undiscounted (battery y10, y20: 2 x 10,973; inverter y12, y24: 2 x 3,582) | Multiply by (1 + vat); optionally add a replacement-labor setting | S |
| 6 | Low | [website][sales] | core/quick.py:151-152, 171; Estimate.tsx:407, 509 | The same battery is three numbers: the website hero "battery_part" 91,600 (selling line x 1.12, no freight or commission share), the website line "Add a battery for brownouts: about 102,000 more" (difference of two whole systems), the proposal "battery for brownouts PHP 102,417" (customer amount x 1.12). | 10,800 between the two website figures on one page | Make `battery_part` the customer item amount x (1 + vat), as the proposal does | S |
| 7 | Low | [copy][sales] | docs/marketing.md "Bill swap" ad and "45 months" frame | Ad copy says "A 5,000 bill becomes about 1,100; pays for itself in under 4 years". The engine for a 5,000 bill in Tanauan (net metering, evening use) gives 5,003 -> 216 a month and 5.1 years (500 kWh: 6,003 -> 357, 4.6 years). "Pay about 45 months of your bill": the worked job is 66 months (264,900 / 3,987). | Claims the engine does not support | Generate the ad figures from `/api/quick/estimate` for the stated bill and keep "about"; drop "under 4 years" | S |
| 8 | Low | [finance][bug] | engine.py:272 `roof_mh / (2 * prod * job.roof_closed_days)`; schemas.py PricingJob.roof_closed_days `ge=0` | Roof closed within 0 days raises ZeroDivisionError and the job prices as "Pricing failed" (the workbook gives #DIV/0!). | Job unpriced | `ge=1` on the field, or treat 0 as 1 | S |
| 9 | Low | [finance] | engine.py:438-444; sample job | The rounding pesos sit on the labour line but VAT is computed before rounding, so "VAT, 12% of the amounts above" is not 12% of them, and a BIR-style VAT on the VAT-inclusive total differs. | 0.07 here (rounding 0.58); on the workbook's sample job 10.25 (rounding 85.41); BIR VAT 35,282.14 vs printed 35,272.99 | VAT = rounded x 12/112, base = rounded - VAT; spread the base difference on the labour line | S |
| 10 | Low (verify) | [finance] | JOB!B117-B119, engine.py:355-371 | Government fees "passed through at cost" (permit 5,000, ERC 1,500, meter 3,000) carry the 5% commission and 12% VAT in the workbook and the app alike. | Customer pays 11,172 for 9,500 of fees | Owner to confirm the intent; the accountant to confirm whether reimbursed government fees are VATable | S |
| 11 | Low | [finance][ux] | PricingSection.tsx:236, 374; api returns totals.ocm/op and landed costs to any user | The engineer role (tested as "juan") reads OCM, OP, landed costs and markups through the API and the "Show internal build-up" toggle; only the Settings page is owner-gated. The owner may want margins owner-only. | None (disclosure) | Owner's call; if yes, strip `build_up`, `totals.ocm/op/markup` and `lines[*].landed*` for engineers server-side | S |
| 12 | Low | [finance] | importer.py:148 `typical_fill`, :188-190 `mounting/wiring_mh_per_unit`, `hybrid_pace` stored as numbers; `roof.simple_roof_factor` imported but unused | In the workbook these are formulas of other inputs (REF BASKET fill; the 9.12 kWp and 13.97 kWp reference jobs). In the app they are frozen numbers, so editing a parent setting has a different effect than in Excel. Example: payload 3000 -> 2000 kg moves handling per panel 44.99 -> 67.48 in the app; the workbook keeps about 44.99 because the REF BASKET fill rescales. | 22.49 per panel in that example | Either recompute them from the reference quantities (store REF BASKET and the two reference jobs) or label them "calibrated figures: re-enter after changing weights"; drop or wire `simple_roof_factor` (JOB!B11 links to it) | M |
| 13 | Low (verify) | [sales] | economics.py:60-63 tariff = bill amount / kWh; plan item 10 | The tariff is all-in (fixed charges included) and the bill after solar is import x tariff, so fixed or minimum charges vanish in "Your bill with solar PHP 167.31". | Overstates savings by the DU's fixed charge each month (verify on a BATELEC II bill) | Add a fixed-charge setting per utility, subtract it from the before/after savings | S |
| 14 | Trivial | [ux] | engine.py:448 "VAT (12%)", PricingSection.tsx:169, ProgramSection.tsx:395 "Commission is 5%" | Rates are settings, labels are hard-coded. | None today | Format from `cfg.job.vat` and `agent_commission` | S |
| 15 | Trivial | [finance][pm] | program.py:425-426 | Mob/demob is cash in full, though it holds the pickup's ownership (560/day) and 2/km maintenance, which by the truck's own rule are allocations. | 707 on this job | Split like the truck run | S |
| 16 | Gap | [pm] | JOB!N33:O72, B129:B133 absent | No close-out: actual cost per line, actual direct cost, actual gross profit, OCM at plan, actual OP. Planned for the PM module (plan §5). | None until actuals exist | PM module; keep the planned OCM/OP in results so the close-out can read them | M |

Not findings, but noted: an empty BOM still carries ERC and meter (4,500) while the seal and permit are zeroed
(workbook keeps all four; immaterial). The LGU 5,000 and the 3,000 meter difference are "Est." in the workbook;
BATELEC II's figures for the worked job are unverified.

## 1. The price build-up as the workbook does it

Values are the sample job (JOB sheet, 8 x 630 W, FS-INV-001, FS-BAT-006) and, in brackets, the worked Tanauan job
priced by the same formulas.

1. MATERIALS DB per item: net J = list H x (1 - supplier discount I); truck share Q = max(kg N / 3000, m3 O /
   14.274); handling S = 750 x Q / typical fill 0.144483 (DRIVERS!B23/B24); wastage T = J x category wastage;
   payment fee U = J x supplier fee; landed W = J + S + T + U + storage V; tier Y by category; selling Z = W (1 + Y).
2. JOB BOM rows 33-72: I = qty x W; J = I x Y; K = I + J; L = qty x Q x (supplier does not deliver); M = kg.
   Totals I73 = 207,458.82 [156,188.32]; J73 = 31,753.67 [26,183.30]; L73 = 0.144716 [0.105756].
3. Takeoff B19:B29 from the BOM: panels, hybrid inverters (name has "hybrid" or "off-grid", or All-in-one),
   grid-tie inverters, packs, heaviest pack kg, enclosures (box/enclosure), protective devices, conduit m (+2 m per
   tray piece), wire m, MC4 pairs, ground rods.
4. Freight rows 77-89: stops in driving order (IAN, Felicity, One Point, Blue Carbon) when the BOM buys from them
   and they do not deliver; legs from ROUTE!B13:G18 and the toll matrix ROUTE!B22:G27 (built from the TOLL sheet
   Class 2 tables); loop = 235 km + 2 x extra km [288.6]; toll 2,220 + extra; run cost = (8,500 + 1,500 + 1,000) x
   trip-days + loop x 17.2857 + toll = 17,282.14 [18,208.66]; trips = ROUNDUP(L73) = 1; freight = 17,282.14 [18,208.66].
5. LABOR CALC col I: roof MH = (2 + panels x 0.375) x rf + panels x 0.25 x rf = 5.25 [3.84]; ground pace 0.375 on
   any job with a hybrid or a battery; carry crew = max(2, ROUNDUP(kg / 32)) = 4 [3]; ground MH from the twelve
   per-unit rates D39:D50 (calibrated 0.8939 and 0.4301 MH per weighted unit) x pace, plus hauling carry x 0.5 h x
   packs = 8.61 [7.98]; hand-off 2; total 15.86 [13.83]. Min pairs = max(roof within closed days, carry crew);
   options 1/2/3 pairs: days = ROUNDUP(MH / (persons x 6.5)); cost with transport; cheapest feasible within max
   pairs and max days, else the largest allowed. Chosen 1 pair, 4 persons, 1 day: labor 6,500; person-days 4;
   mob/demob = 1 x 800 + 500 + days x (2 x extra km x 12 + extra toll) = 1,300 [1,943.20]; tools 905.62.
6. Build-up rows 107-116: materials by item tier; freight x 15%; labor, mob/demob, tools, PPE (person-days x 100)
   and the PEE seal (1,000) x 30%; LGU permit and CFEI 5,000, ERC CoC 1,500 and meter 3,000 at 0% (the last two
   only with net metering). Direct B117 = 244,346.59 [194,645.80]; markup D117 = 37,377.68 [32,139.25]; selling
   E117 = 281,724.27 [226,785.05].
7. Commission B119 = B117 x 5% = 12,217.33 [9,732.29]; ex-VAT B120 = 293,941.60 [236,517.34]; VAT 12% = 35,272.99
   [28,382.08]; contract B122 = 329,214.59 [264,899.42]; rounded up to the next 100: 329,300 [264,900].
8. Planned OCM B124 = D117 x 50% = 18,688.84 [16,069.62]; planned OP B125 = D117 - B124 = 18,688.84 [16,069.62].
   kWp 5.04 [2.925]; price per Wp 65.34 [90.56].
9. Close-out B130:B133: actual direct cost (lines without an actual count at estimate), actual gross profit =
   B120 - actual direct - commission, OCM stays at plan, actual OP = actual GP - planned OCM.

## 2. Cell-by-cell reconciliation (workbook -> app)

| Workbook | App | Result on the worked job |
|---|---|---|
| MATERIALS DB J, Q, S, T, U, W, Y | engine.landed_cost (engine.py:30-39), config.category | identical, 25 of 25 lines (landed unit, tier, truck share) |
| JOB I/J/K/L per row, I73, J73, L73 | engine.price_lines; freight_for truck_share | identical: 156,188.3193 / 26,183.3037 / 0.1057556 |
| JOB B19:B29 takeoff | engine.takeoff_from_lines | identical: 5 / 1 / 0 / 1 / 88 kg / 2 / 12 / 32 m / 85 m / 2 / 1 |
| JOB C78:C81 stops, E/F legs, B84:B89 | engine.freight_for, RouteConfig km/toll | identical: 4 stops, 288.6 km, 2,220, 18,208.657, 1 trip |
| DRIVERS B13 running cost, B19 run cost | TruckConfig.running_cost_per_km | identical 17.2857 |
| LABOR CALC I23:I41 | engine.labor_for (roof, pace, carry, ground parts, hand-off) | identical: 3.84375 / 0.375002 / 3 / 7.98282 / 2 / 13.82657 |
| LABOR CALC I45:I59 crew choice | labor_for options and the feasible/else rule | identical: min pairs 1, pairs 1, days 1, persons 4 |
| LABOR CALC I62:I67, I70:I73, I80; JOB B98 | labor_for labor, person_days, mobdemob (+ extra km per day), tools | identical: 6,500 / 4 / 1,943.20 / 905.625 |
| JOB B102, B103, B104, B113, B114, B115, B116 | JobLevel services_markup, ppe_per_person_day, ocm_share, pee_seal, lgu_permit_cfei, erc_coc_fee, bidirectional_meter_fee (importer.py:271-281) | identical 0.30 / 100 / 0.50 / 1,000 / 5,000 / 1,500 / 3,000 |
| JOB B107:E116 ten lines | engine.price_job build-up (engine.py:355-368) | identical, all ten directs and markups |
| JOB B117, C117, D117, E117 | totals.direct, markup_over_direct, markup, selling | identical 194,645.80 / 0.165117 / 32,139.25 / 226,785.05 |
| JOB B119:B123 | totals.commission, contract_ex_vat, vat, contract, contract_rounded | identical 9,732.29 / 236,517.34 / 28,382.08 / 264,899.42 / 264,900 |
| JOB B124, B125 OCM, OP | totals.ocm = markup x ocm_share, totals.op = markup - ocm | identical 16,069.62 each |
| JOB B126, B127 | totals.kwp, price_per_wp | identical 2.925 / 90.564 |
| JOB B9 net metering switch | JobInputs.net_metering = kind != off_grid | identical (combination -> Yes) |
| JOB B7, B8 extra km/toll | PricingJob.extra_km (prefilled from the pin: straight x 1.3 - 10 = 26.8) / extra_toll | identical mechanics; the prefill is app-only (workbook: typed) |
| JOB N33:O72, B129:B133 close-out | none | missing (gap, PM module) |
| Customer split (not in the workbook) | engine.py:383-452 | sections sum to 264,900; freight spread by truck share, commission by direct, rounding 0.58 on the crew line; identity holds |

Importer check (importer.py) against the sheets: DRIVERS (truck, handling, commission, VAT, freight markup, the
eleven category tiers and wastages), ROUTE (6 stops, both matrices, reference site km 10), LABOR RATES (three
rates, allowance, owner day, paid and non-productive hours, pay unit, roof setup and per-panel rates, the two
calibrated ground rates, hybrid pace, max kg per person, twelve task weights), MOB-DEMOB (ownership per day,
running cost, base-to-site km, toll, one-way time, packaging), TOOLS (charge per day), JOB (roof factor, closed
days, max days, max pairs, haul hours, services markup, PPE, OCM share, seal, permit, ERC, meter): all read by
their row labels, all matching the workbook's values (test_import_counts_and_config confirms the key ones).
Left at app defaults, not in the workbook: `round_up_to` 100 (hard-coded in JOB!B123 anyway),
`quotation_validity_days` 15, the wiring rules, BOM roles, program durations, payment plan and the economics
block. Stored as numbers where the workbook has formulas: finding 12.

## 3. The worked job

Input: Tanauan, Batangas pin (14.086, 121.149); two 10.1 x 6.4 m faces at 15 deg, three readings each; BATELEC II
bill Aug 2026, 338 kWh, 3,987.17; combination (battery and net metering); panel BC-PNL-001 585 W.
Sizing: 5 panels, 2.925 kWp, FS-INV-008 6 kW x 1, FS-BAT-002 10 kWh x 1 (7.41 kWh required), 4,273 kWh/yr at the
meter. BOM: 25 lines as listed in result.json. Price: direct 194,645.80, markup 32,139.25 (16.5% over direct),
commission 9,732.29, ex-VAT 236,517.34, VAT 28,382.08, contract 264,899.42 -> 264,900; OCM 16,069.62, OP 16,069.62;
90.56 per Wp. Customer sections: Materials 212,031.43, Installation and permits 23,263.90 (+ tools 1,222.59 folded
in on the PDF = 24,486.49), VAT 28,382.08, total 264,900.00. The proposal prints these and no internal word
(grep for landed/markup/OCM/profit/commission/freight: 0 hits). The website estimate for the same house on a
typical roof gives 265,000: the two agree.

## 4. OCM and OP, answered directly

- Split: one share of the total markup (JOB!B104, `job.ocm_share`, 50%); OP is the balance. Identical.
- By line or category: neither the workbook nor the app splits OCM/OP per line; the per-line differences are the
  markup tiers, which the app carries exactly (10 / 15 / 30 / 15 / 30 / 0).
- Where shown: Quantities card, under "Show internal build-up", one muted line "OCM 16,070, profit 16,070, markup
  16.5% over direct" (PricingSection.tsx:374); the program PDF shows cash margin, not OCM/OP; the proposal,
  the roof check and the card show none of it. The engineer role sees the line (finding 11).
- Close-out: absent (finding 16). The cash margin the program shows (43,965) is not OP: it is OP + OCM + the
  non-cash allocations + rounding (16,070 + 16,070 + 11,825 + 0.58 = 43,965), which the page says in words.
- Label: Settings calls it "Overhead share of markup" with no help text; the workbook says "OCM share of markup
  (input): the rest is OP". Add that sentence [ux].

## 5. Cashflow and economics

Program (worked job): signing 9 Oct, permit 11-18 Oct, pickup 18 Oct, install and switch-on 19 Oct, CFEI 24 Oct,
meter 24 Nov; payments 50 / 40 / 10 (the last two merge on the install day on the PDF); cash out as DECISIONS
describes; lowest balance -41,528 on the pickup day; the crew finishes 22 minutes late within the allowance.
Findings 3 and 15 above. The VAT remittance date (completion + 30 days) is a placeholder: verify the quarterly
return with the accountant (plan item 9).

Economics (worked job): tariff 11.80 from the bill, export 6.50, escalation 3%, degradation 0.5%, 25 years,
8% discount, battery 10 / inverter 12 years, upkeep 0.5% (1,324.50). Bill 3,987 -> 167 a month, savings 44,938
in year 1, payback 5.7 years (7.8 discounted), NPV 233,229, IRR 16.7%, 25-year net 976,229, LCOE 5.52, CO2 3.0 t.
Arithmetic checked: monthly bill after = max(import x tariff - export x credit, 0) (credit beyond zero not carried,
flagged); year rows scale by (1 - d)^(y-1) and (1 + e)^(y-1); replacements at y % life == 0 and y < years;
payback interpolated; IRR by bisection; lifetime net = savings - (contract + costs). All consistent. Findings 2, 5
and 13 are about the inputs, not the arithmetic. No financing or "from X a month" wording anywhere (grep of
site/pages, the estimate widget, the three PDFs and docs/marketing.md).

## 6. Controls

- Only the owner changes prices: PUT /api/pricing/config, item writes and the import answer 403 to the engineer
  (tested); the engineer reads the config (200), computes, edits BOM quantities (2 batteries -> 360,600) and sees
  OCM/OP (findings 1 and 11).
- Settings change vs old projects: finding 1.
- Rounding: next 100 (editable `round_up_to`), identical to JOB!B123; website rounds the contract up to 1,000.
- VAT: 12% setting; label hard-coded (finding 14); VAT line arithmetic (finding 9).
- Printed vs computed: the proposal prints the engine's customer sections and total exactly; refuses stale
  results; the BOM CSV/XLSX carry the owner's edits.

## 7. What is sound

- The landed cost, truck share, handling, wastage, payment fee, freight run and trips, the crew rule, the
  tiers, the pass-throughs, commission, VAT, rounding, OCM/OP and price per Wp: a faithful port, proven on the
  workbook's sample (329,300) and on a fresh job (264,900) by an independent recompute.
- The importer reads every driver by its label, so a re-imported workbook moves the app's settings with it;
  `--keep-config` protects in-app edits.
- The customer split sums exactly to the contract; freight, commission and rounding are spread as the owner
  intended; no internal number reaches the proposal.
- The cashflow's cash/allocation split follows the owner's practice and says so on the page.
- The economics are arithmetically right, state their assumptions in one sentence on the proposal, and the
  export-credit cap is flagged rather than hidden.

## Files

scratchpad/agents3/finance/: wb_dump.txt (all sheets, formulas and values), job.json (the input), result.json
(the computed record), proposal.pdf/.txt, program.pdf/.txt, bom.csv, cfg_orig.json, private.log.
