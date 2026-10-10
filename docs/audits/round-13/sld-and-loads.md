# Round 13, items 1 and 5: the single-line diagram and the schedule of loads

Built 10 October 2026 from `engineer-brief.md`, sections 1 and 5, on top of step 1 (3c95145: the title block, the
`pricing.choices.circuits` contract, the survey fields). Three commits on the branch: the diagram with the 120 % busbar
rule, the schedule of loads with its settings block, the documents. The suite went from 272 to **284 tests**; `npm run
build` passes and `npm run lint` stays at its seven baseline warnings. The sample set, its `pdftotext` pages and the PNGs
of the two sheets are under `scratchpad/plans13/sld/` (`plans-combination-future.pdf`, `combination-future-p4-4.png` the
diagram, `combination-future-p7-7.png` the schedule of loads, `cover-future-1.png` the cover; the off-grid, blank-service
and busbar-100 variants beside them).

## 1. The single-line diagram (brief 1.1 to 1.5)

`reports/plans_sld.py`, one sheet after the array layouts, called from `plans_pdf.build_plans_pdf` through one hook
(`sld_sheet(doc, results, items, cfg, styles) → (name, flowables)`). A3 landscape in the set's frame, drawn with
ReportLab `Drawing` primitives (Line, Rect, Circle, Polygon, String) on a 392 × 150 mm canvas in millimetres; the
brief's line weights (bus and outlines 0.7, symbols 0.5, leaders 0.35 and 0.25), 7 pt labels in Montserrat, black with
the brand gold only on a FAIL line; the title block reads "Not to scale".

Left to right along one horizontal bus, every device carrying the balloon of its circuit row (C1 to C7, drawn only where
`circuits[i].applies`):

1. **The array.** One drawn string per distinct string length (a chain of module symbols), the rest "alike, one drawn";
   the label "S1: 6 × 585 W" (with "(rule)" when the datasheets are not on file) and under the first chain "Voc 53.1 V
   STC, 54.8 V at 14 °C; Vmp 44.0 V; Isc 13.53 A; Imp 13.31 A" from `string_design` and the panel item, each figure
   `BLANK` when absent. Above three distinct lengths one is drawn and a table under the diagram lists every string.
2. **The home runs.** The + lead from the chain's right end, the − lead from its left end over the top, both to the DC
   box, labelled with the gauge and run per conductor; the connector pairs at the array end (`mc4_pair`); the array
   bonding conductor dashed along the strings to the EGC bus with its size and item.
3. **The DC box.** A dashed enclosure outline with the `enclosure` item; a 2P DC breaker per string (`choices.dc_breaker`
   rating and code; "rated … not checked: no Isc on file" without the datasheet); the fan to the MPPT inputs by the
   BOQ's round-robin, a junction dot where strings share an input, a spare input marked "spare"; an SPD per MPPT input
   in use (`dc_spds`, the voltage from the item's name) to the box's earth bar, the stubs jumping the other inputs'
   lines; "DC box (combiner)" and the fuse-per-string note when strings join (C2 balloon).
4. **The inverter.** The square split by its diagonal ("=" above, "~" below), the code, rating, type and phase, the MPPT
   count and currents, the maximum PV voltage and window, the AC output with the grid flag and certificate, the battery
   port's class, voltage and currents.
5. **The battery bank** (not on net metering), below the inverter: the breaker (C3), the plates per unit (three drawn
   at most, "… × n"), the label with units × kWh, the nominal voltage, the maximum discharge per unit, the breaker and
   lug pairs, "parallel bus: verify a battery combiner" above two units; the rack bond dashed and marked "verify".
6. **The AC side.** The inverter-output breaker (C4) with its gauge and run, the transfer switch (a box with two
   inputs and the blade, or a junction and "built into the inverter"), the AC SPD on the board to the EGC bus, the
   existing panelboard (bus bar, backfeed breaker tag, main breaker, the surveyed ratings or "(not surveyed)", the
   panelboard text), the lockable AC disconnect in a dashed box with its rating, the point of interconnection (a
   filled circle on the panelboard's bus bar for a load-side breaker or when not chosen, at the service for a
   supply-side tap or the line side), the kWh meter (two arrows and "two-way meter: installed by the DU after the
   CFEI" on net metering and combination; one arrow and "existing meter; nothing exported" off grid), the service drop
   dashed, and the DU with its fault level ("from the DU, verify"), the voltage (the survey's, else the wiring rules'
   as an assumption), phase and account. The grid feed to the inverter's AC input (C5) and the maintenance bypass to
   the transfer switch (C6) run on a line above the bus from the point of interconnection.
7. **Grounding.** The EGC bus along the bottom from the DC box to the disconnect (C7), the electrode under the
   panelboard, the bonds dashed (array, DC box, inverter, battery rack "verify"), the grounding run's gauge and
   length, "GEC … to the rod, required 14 mm² or less for a rod (verify)".
8. **Legend and placards.** Fifteen symbols named, three to a row, with "verify the symbol set against the DU's
   sample (the PEC prescribes none)"; a table of the DU's labels filled from the figures, "verify the DU's wording"
   on each: the dual-source warning at the service, the AC disconnect, the DC disconnect placard (maximum Voc =
   per string × Voc at T_cold, the array's Isc = strings × Isc; the NEC 690.53 placard, verify the PEC 6.90 clause),
   the inverter, the battery; the rapid-shutdown row only when the BOM carries an `rsd` role line (none today).
   Under them the DC-grounding assumption (transformerless, EGC only; verify on the datasheet).

### The symbol legend

| Symbol | Drawn as |
|---|---|
| PV module | a rectangle with the cell (long and short plate) and two incoming arrows of light; a chain is a string |
| circuit-breaker, 2P | the line opens at an inclined contact, a cross at the hinge, two poles with a dashed link |
| surge-protective device | a rectangle with the arrowed diagonal, between the line and the earth bar |
| DC/AC converter | a square split by its diagonal, "=" above, "~" below |
| battery | alternating long and short plates, one group per unit |
| transfer switch | a box with two inputs and one output, the blade to the line's input |
| disconnect (isolator) | the open contact with a bar at its free end; a dashed box means lockable |
| existing panelboard | a rectangle with the bus bar and the main breaker |
| point of interconnection | a filled circle |
| kWh meter | a circle "kWh"; two arrows = two-way |
| earth electrode | three bars of decreasing length |
| bonding conductor | dashed |
| connector pair | two small bodies on the lead |
| circuit balloon | a white circle with the number of the schedule row |
| enclosure outline | dashed rectangle |

### The 120 % rule (brief 1.3)

`pricing/service_checks.py`, `poi_busbar_check(service, choices) → (block, warnings)`: for `interconnection ==
"load_side_breaker"` with both ratings typed, `ac_grid_breaker_a × inverter_units + main_breaker_a ≤ 1.2 × busbar_a`
(NEC 705.12(B)(2)(3)(b); the PEC 2017 equivalent printed with "verify"). `price_assessment` calls it after the BOQ and
writes `choices.poi_busbar` (`checked`, `reason`, `grid_breaker_a`, `units`, `backfeed_a`, `main_breaker_a`, `busbar_a`,
`factor`, `limit_a`, `sum_a`, `ok`, `source`); a failure raises `poi_busbar`, hard and never `blocks_documents`. The
sheets print the arithmetic ("120 %: 40 A + 100 A = 140 A; limit 1.2 × 125 A = 150 A; PASS; verify the PEC clause") or
"120 % rule: not checked — {reason}" (not chosen; another arrangement, verify the DU's rule; busbar and main breaker not
surveyed; no grid-side breaker sized); a FAIL prints in gold with "poi_busbar (hard warning, prints)". The sheets call
the function again when the stored results predate it, so the warning and the sheet always agree.

### Tests (1.5, `test_plans_sld.py`, seven)

The Pila sample with the datasheet fixtures and the 500 V input (one string of 6 × 585 W): the sheet named on the
cover as sheet 4, "S1: 6 × 585 W", the datasheet line, "329.0 V at 14 °C" on the placard, "25 A 2P DC breaker per
string", "139 A", "40 A 2P", "two-way meter", the DU, the panelboard, the 120 % PASS, the balloons of the applying
rows and no C2, the legend's and placards' verify lines, "Not to scale"; the off-grid job (two strings of 5, two SPDs,
"nothing exported", the battery placard); a net-metering job (no battery, no C3, the last sheet naming the figures
still blank and the sheet); a blank service block (every line blank with its reason, no PASS or FAIL); the set
without the datasheets ("(rule)", blank figures, "not checked: no Isc on file", seven sheets); busbar 100 A → FAIL,
`poi_busbar` raised and not in `design_blocked`, 125 A → PASS; the rule's own cases (the units, every reason).

## 2. The schedule of loads in the permit's format (brief 5.1 to 5.4)

`reports/plans_loads.py`, its own sheet before the last one, called through `loads_sheet(...) → (name, flowables)`.

**The format (verify)**: the header line "Panelboard {name}: {V}, {phase}Ø {wires}, main breaker {AT} AT / BLANK AF
(the frame rating is not surveyed), bus {A} A, fed from BLANK (the engineer's)"; the columns **Circuit No. |
Description of load (count × type) | Load (W) | Load (VA) | Volts | Amperes | Wire (mm² THHN) | Conduit (mm) | OCPD
(AT/AF, poles) | Remarks**, introduced as "the usual column order of a sealed plan's schedule of loads: verify against
the LGU's sample (a past sealed plan)" (the brief's verify flag, 5.1; the owner's question 9.5).

**What prints**: the existing circuits as typed on the Site step first and verbatim (number, description, wire,
conduit, "{AT} AT / BLANK AF, {poles}P"; the load figures the engineer's); the audit's appliances under three shaded
group headings — Lighting (`category == "lighting"`), Convenience outlets (everything else: refrigerator, TV, fans,
kitchen, other), Equipment (`loads.equipment_categories`) — each heading carrying "(PF {x}, assumption (Settings ›
System design))", each line "{qty} × {name}, {W} W each" with W, VA = W / PF, Volts (the surveyed service voltage,
else 230 V "(assumption)"), Amperes = VA / V, and blank lines for the circuit number, wire, conduit and OCPD; a
subtotal per group; "Connected load, existing" (W, VA, A); "Planned loads" (status "future") apart with their own
subtotal and outside the existing total; "Demand load" blank with "the demand factors of PEC 2.20 (verify) are the
engineer's; the hourly profile's coincident peak is {sizing.inverter.peak_load_kw} kW (the audit's own figure)"; "Main
breaker" with the surveyed AT and "its adequacy with the PV source: the engineer's"; retiring appliances counted, not
listed. Under the table, side by side: **The PV system as a source** (the array, the inverter with its current at the
AC voltage and phase, the PV backfeed breaker (C5) and the inverter-output breaker (C4), the wire, the conduit item
and allowance, the energy storage or "none (net metering)", the DC side's reference to the diagram) and **The point of
interconnection** (the choice in words with its note, the main breaker and busbar, the 120 % line with its source,
the meter, the DU and account with the fault level). A footnote lists what the engineer still fills by hand (5.3).

**Settings**: `PricingConfig.loads` (`LoadsConfig`): `power_factor` {lighting 1.00, outlets 1.00, equipment 0.85; every
figure an assumption the sheet labels} and `equipment_categories` (aircon_inverter, aircon_non_inverter, water_pump,
pressure_washer, water_heater_tankless, water_heater_storage, washing_machine, dryer, ev_charger). Shown under
Settings › Pricing › System design (`pricingMeta.ts`, `shared.ts`); outside the pricing fingerprint
(`VERSION_EXCLUDES`), since the sheet reads them live and they move no price. A power factor missing from the map
leaves the VA and amperes blank with "PF not set in Settings".

**The last sheet** no longer tables the audit; it is named "Not yet in this set" and lists the diagram only as
"Single-line diagram (figures blank)" naming the Materials figures still blank, and the schedule only as "Schedule of
loads (service entrance blank)" until the main breaker, busbar and interconnection are typed. The cover's general
notes are split six and two so the bottom block (one table that cannot split) stays on the cover with the longer
sheet index; it has about 20 mm of slack for the sheets still to come.

### Tests (5.4, `test_plans_loads.py`, five)

The grouping and arithmetic hand-worked on the sample audit with the planned second aircon: Lighting 72 W / 72 VA /
0.31 A; Convenience outlets 240 / 240 / 1.04; Equipment 1,200 / 1,412 / 6.14 (PF 0.85); planned 1,200 W apart;
connected (existing) 1,512 W, 1,724 VA; a retiring appliance counted; a missing power factor leaves VA blank; the
settings block outside the fingerprint. The sheet through the API: sheet 6 of 7 on the cover, the header line and
every column, the three groups with their labelled PF, the rows as table lines, the planned aircon apart, the demand
line with the audit's 1.53 kW peak, blank lines and no circuit number on an audit line, the PV block ("26.1 A at 230
V", "40 A 2P (C5", "8.0 mm² THHN", the conduit item, the storage), the POI block with the 120 % PASS line, the DU and
account, the footnote; the last sheet without the audit; typed circuits first and verbatim; a blank service block
(every blank with its reason, the last sheet listing the schedule); an audit without appliances (no sizing, the
plans refused as before).

## Departures from the brief, with the reason

1. The schedule of loads is its own sheet before the last one (brief 8 lists it as a sheet; the coordinator allowed
   either), and the last sheet's audit table is gone: the permit's format carries the same lines with more.
2. The diagram sits after the array layouts (the coordinator's order); brief 8 lists it after the schedules.
3. The grid feed and the maintenance bypass run on a line above the bus from the point of interconnection, not on the
   bus itself (1.1.6 lists them "in this order from the inverter"): one straight bus with the AC SPD's stub below stays
   readable, and the feed and the bypass are what they are, two circuits from the grid side.
4. The point of interconnection sits on the panelboard's bus bar for a load-side breaker (and when not chosen, as 1.4
   says) and between the disconnect and the meter for a supply-side tap or the line side; the disconnect is drawn
   between the panelboard and the meter as 1.1.6 orders it, with "verify its place" since the DU decides.
5. The tags inside symbols (balloon numbers, "ATS", "kWh", "AC in", "MPPT n", "spare", the bus and main tags) are
   6 pt, below the brief's 7 pt floor, so they fit the symbol; every label is 7 pt.
6. The 120 % line prints "limit 1.2 × 125 A = 150 A" rather than "≤": Montserrat has no glyph for it, and the three
   short lines keep each figure whole when the label wraps. The not-checked reasons are the cause alone after "120 %
   rule: not checked —" ("busbar and main breaker not surveyed"), not the brief's full sentence twice.
7. `choices.poi_busbar` carries the whole inequality (the brief names only the warning): the sheets print the
   arithmetic, and a set built on older results recomputes it from the service block.
8. The sample's figures: with the datasheets the Pila sample is one string of 6 (the brief's "S1: 6 × 585 W" holds);
   the off-grid variant is two strings of 5; the loads sample's planned second aircon raises the sizing to 10 panels
   (two strings of 5 with the datasheets, one string of 10 by the rule) and the coincident peak to 1.53 kW, so the
   loads test expects those, and a client without the datasheets picks another battery pack, so the storage line is
   checked by shape.
9. The `loads` settings live under Settings › Pricing › System design (the brief says "settable under
   `loads.power_factor`" and no page); the refrigerator and freezer are convenience outlets as 5.2 lists them, the
   motor and compressor categories are the equipment list.
10. The placard's array current is strings × Isc (1.1.8 writes "Isc {per_string strings…} A"); the rapid-shutdown row
    prints only with an `rsd` role line, so it is absent today.
11. Retiring appliances are left off the schedule with a count line (the format lists what stays); the header's AF and
    "fed from" are blank lines with "not surveyed" / "the engineer's" since no field holds them.
12. `test_plans.py` counts seven sheets (the brief's "plus one" became plus two with the schedule of loads); its
    last-sheet assertions on the audit table moved to the loads sheet, `test_plans_datasheets.py`'s likewise, and
    `test_survey_fields.py`'s "nothing reads the fields" assertion became its opposite (the diagram prints the DU and
    the 120 % line).
13. The cover's notes split six and two (not in the brief): with two more index rows the four-and-four bottom block
    overflowed to a second page.
