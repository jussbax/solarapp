# Round 13 engineer brief: the sheets still missing from the plan set

Written 10 October 2026 by the solar engineer on the audit team, read-only, from the owner's words: "Let's build
the missing so we can create the complete engineering plan, and for the vicinity map, maybe the engineer will
just upload a screen grab of the vicinity map from the map that we have or can you just automate this since we
already use the openmap." Round 12 is merged at 1dde65e. This is the specification an implementer builds from,
one section per item the last sheet of the plan set lists under "Not yet in this set"
(`backend/solarapp/reports/plans_pdf.py:787-815`).

Read for it: `DECISIONS.md` ("Round 4, plans" and "The datasheets in the app"), `reports/plans_pdf.py` (the
sheet frame, `BLANK`, `TO_COMPLETE`, the title block at lines 139–200, the general notes at 677–705, the
schedule's two-column balancing at 572–612), `reports/drawings.py` (the ReportLab primitives, dimension lines,
`north_angle_deg`, `_north_arrow`, `fit_scale`, `STANDARD_SCALES`), `pricing/boq.py` (the roles, `choices`),
`pricing/design_checks.py` (the string design and the battery checks, the warning shape), `core/layout.py`
(`row_spans`, the geometry the layout sheets draw), `schemas.py` (`RoofFace`, `AssessmentDoc`, `EnergyAudit`,
`PricingJob`), `models.py` (`Assessment`: `doc` and `results` as JSON, `proposal_issued_at`), `profile.py`
(`PROFILE_FIELDS`), `frontend/src/components/MapPicker.tsx` (Leaflet on `https://tile.openstreetmap.org`,
allowed by `OFFICE_CSP` in `main.py:28`), `frontend/src/components/FacesEditor.tsx` (where the roof
construction fields go), `core/towns.py` and `core/towns_ph.json` (the province behind a pin).

Rules that apply to every item, as the set already keeps them (DECISIONS, "Round 4, plans"):

- **Nothing invented.** A figure the app does not hold prints as `BLANK` with the reason beside it ("not on the
  item", "not surveyed", "from the DU"); a default is printed only as a labelled assumption ("assumption: …")
  and raises the warning that says so. The PEE replaces every assumption before sealing.
- **Standards.** The Philippine Electrical Code (PEC 2017) is named by article where the rule is its; every
  article number, table and figure below is marked **verify** unless the app computes it from a formula the
  text gives. NSCP 2015 for wind. Where I give a figure from the NEC edition the PEC follows, it is a cited
  stand-in, never a value the app ships as fact: it lives in a settings table the owner or the PEE confirms,
  with its source line printed on the sheet.
- **Sheets.** A3 landscape (420 × 297 mm), the frame, the title block and the signature block as today;
  Montserrat (`brand.fonts()`); line weights: frame 0.9 pt, outlines and buses 0.7, symbols 0.5, dimension and
  leader lines 0.35/0.25, text 7–8.5 pt, headings 11 and 16; black and the brand gold for fills, nothing else.
  Drawn with ReportLab `Drawing` primitives as `drawings.py` does (Line, Rect, Polygon, Circle, Path, String),
  never raster, except the vicinity map (a raster image by nature).
- **Warnings** go through the existing mechanism (`pricing.warnings` with `code`, `message`, `hard`,
  `blocks_documents`; `job.py` collects the blocking codes into `design_blocked`, which refuses the proposal,
  roof check, card and plans). Each item says which of its checks block.
- **Contract first.** Items 1 and 2 both read one new block, `pricing.choices.circuits` (section 2.1): the
  circuit rows with their conductors, currents, breakers and derating. Build it before either sheet.
- **No model names** in code, settings, fixtures or this brief: roles and item codes only.

Effort marks: S under half a day, M one to two days, L three days or more.

---

## 1. Single-line diagram (one sheet)

### 1.1 What the sheet shows, in the order a PEE reads it

Left to right along one horizontal bus, generation to interconnection, each device numbered with a balloon that
matches a row of the circuit schedule and of the design analysis (C1 …):

1. **The array.** One drawn string per distinct string length (the rest "typ." with the count): a chain of
   module symbols, the string label "S1: {per_string} × {panel W} W", and under it the datasheet line "Voc
   {voc} V STC, {voc_cold} V at {t_cold} °C; Vmp {vmp} V; Isc {isc} A; Imp {imp} A" from `choices.string_design`
   and the panel item, each figure `BLANK` when not on file. The module symbol: the IEC 60617 photovoltaic
   generator symbol (a rectangle carrying the cell symbol with the two incoming arrows), simplified to a
   rectangle with the arrows; the PEC prescribes no symbol set, and the usual sealed plans here use ANSI/IEEE
   315 or IEC 60617 shapes: **verify** which the LGU's reviewer expects (6.1 asks the owner for a sealed sample).
2. **DC home runs.** Per string two conductors (+/−) labelled "{pv_gauge} mm² PV wire, {pv_run} m per conductor",
   the connector pair at the array end (the `mc4_pair` role), the array bonding conductor drawn as a dashed
   line along the strings to the EGC bus (the `array_bonding` role, its gauge).
3. **The DC box** (the `enclosure` role, one per inverter): one two-pole DC breaker per string (`choices.dc_breaker`:
   rating and code; the breaker is the string's DC disconnect, as the schedule says), the DC SPD per MPPT input
   in use (`dc_spds`, the item's voltage from its name), the enclosure outline dashed with its code. Strings
   that share an MPPT input (`string_design.per_mppt` with `strings` > 1) join after their breakers inside the
   box; the box is then labelled "combiner" and the PEE's note "verify a fuse per string where more than two
   join" prints under it (the BOM has no combiner role; `string_design.per_mppt` says when one is needed).
4. **The inverter.** The IEC DC/AC converter symbol (a square split by a diagonal, "=" above, "~" below) with
   the item code, the rating kW, the type and phase, "{mppt_count} MPPT inputs, {mppt_currents_a} A, max PV
   {max_pv_voltage_v} V, window {mppt_min_v}–{mppt_max_v} V", the AC output "{ac_voltage} V 1Ø" (from the wiring
   rules; 3Ø units are excluded from residential jobs), "grid-interactive: yes/no/not marked; certificate:
   {certifications or BLANK}" (the proposal's line), and the battery port "{battery_class}, {charge_v_max} V,
   {battery_max_a} A discharge, {charge_a_max} A charge".
5. **The battery bank** (not on `net_metering`): the IEC battery symbol (long and short plates) ×
   `battery_units`, "{units} × {rating} kWh = {bank} kWh, {nominal_v} V, max discharge {continuous_a} A per
   unit"; the battery breaker (`battery_circuit.breaker_a`, the item code) and the cable "{cable_gauge} mm² lug
   pairs, {pairs} per unit"; units > 2 print "parallel bus: verify a battery combiner (not a BOM role)".
6. **The AC side**, in this order from the inverter: the inverter-output breaker (`ac_breaker_a`, 2P), the
   transfer switch (the `ats` role, or "built in" when `choices.ats == "built-in"`), the AC SPD (type 2, the
   `ac_spd` role) on the board, the grid-side feed breaker and the maintenance bypass (`ac_grid_breaker_a`, the
   round-3 circuits), the loads panel as a rectangle "existing panelboard: main {main_breaker_a} A, bus
   {busbar_a} A" (new survey fields, 1.3), the visible lockable AC disconnect at the service (the `ac_disconnect`
   role, its rating), the **point of interconnection** marked with a filled circle and the label from the new
   field (1.3), the **meter**: a circle "kWh" with two arrows for a two-way meter on `net_metering` and
   `combination` ("two-way meter: installed by the DU after the CFEI; meter number: BLANK"), one arrow and
   "existing meter; nothing exported" on `off_grid`, then the service drop and "{du_name}: fault level at the
   service BLANK (from the DU, verify)".
7. **Grounding.** The electrode (the `ground_rod` role) with the IEC earth symbol, the GEC to the AC board's
   ground bar, the EGC bus with the array bonding, the inverter and enclosure bonds, the battery rack bond
   (printed "verify" since the BOM carries no battery-rack lug); the DC system grounding line "transformerless
   inverter: no DC conductor grounded, EGC only (assumption; verify on the inverter datasheet)".
8. **Labels and placards** as a table at the foot of the sheet, the text the app can fill from the figures
   and "verify the DU's wording" on each: at the service "WARNING: dual power source — PV system connected";
   the AC disconnect "PV system AC disconnect"; the DC box "PV DC disconnect: maximum Voc {per_string ×
   voc_cold} V at {t_cold} °C, Isc {per_string strings…} A" (the NEC 690.53 placard; **verify** the PEC 6.90
   clause); the inverter "{kW} kW grid-interactive inverter"; the battery "energy storage {kWh} kWh, {V} V";
   the rapid-shutdown label only when the BOM carries an RSD item (it does not today; a role for later).

The title block's scale field reads "Not to scale". One sheet; above eight distinct string lengths the array
prints as a table beside one drawn string.

### 1.2 Inputs and their sources

| Element | Source |
|---|---|
| strings, per string, the MPPT assignment, Voc/Vmp/Isc/Imp and T_cold | `pricing.choices.strings`, `panels_per_string`, `string_design` (and `string_design.current`), the panel item |
| PV gauge, run, breaker, SPD count, enclosure | `choices.pv_gauge`, `pv_run_m` (the job's or the wiring rules'), `choices.dc_breaker`, `choices.dc_spds`, the BOM lines by role (`_lines_by_role`) |
| inverter ratings | the inverter item (round-12 fields), `choices.inverter_grid_interactive`, `pricing.inverter_certificate` |
| battery | the battery item, `choices.battery_units`, `battery_nominal_kwh`, `battery_circuit` |
| AC breakers, gauges, ATS, disconnect | `choices.ac_breaker_a`, `ac_grid_breaker_a`, `ac_gauge`, `ac_grid_gauge`, `ats`, the BOM roles |
| the existing panelboard, the POI, the DU, the meter | **new** `doc.service` (1.3) |
| grounding | the BOM roles `ground_rod`, `earth_lug`, `array_bonding`; the EGC sizes from section 2 |
| derated figures and pass/fail per circuit | `choices.circuits` (2.1) |

### 1.3 New fields: the service entrance (the survey record the plan called for, item 1 of `docs/plan-engineering-app.md`)

`AssessmentDoc.service: ServiceEntrance` (`schemas.py`), edited on the Site step beside the map:
`du_name` (text; "Meralco", "BATELEC II", "FLECO"…), `account_no` (text, optional; customer data, shown only on the
plans and the DU pack), `meter_no` (text, optional), `phase` (1 or 3; default blank), `voltage_v` (default blank;
the wiring rules' 230 V prints as the assumption when blank), `main_breaker_a`, `busbar_a` (numbers, blank
until surveyed), `interconnection`: `load_side_breaker` (a backfeed breaker in the existing panelboard, the
usual residential arrangement) | `supply_side_tap` | `line_side_of_main` | blank, with `interconnection_note`
(text: where the breaker sits, the distance to the meter). **The 120 % rule** when `load_side_breaker` and both
ratings are typed: `ac_grid_breaker_a × units + main_breaker_a ≤ 1.2 × busbar_a` (NEC 705.12(B)(2)(3)(b); the
PEC 2017 equivalent: **verify**); fail → warning `poi_busbar` (**hard, not blocking**: the fix is a supply-side
tap or a larger panel, the PEE's call; the sheet prints FAIL beside the POI). Blank ratings print "busbar and
main breaker not surveyed; the 120 % rule is not checked".

### 1.4 What prints when an input is missing

Every figure `BLANK` with its reason in the label; a device whose role has no item (`NO-ITEM-…` lines) prints
with its role name and "no item in the materials list"; no POI typed → the POI circle is drawn at the
panelboard with "point of interconnection: not chosen (Site step)"; no datasheet → the string label keeps the
panel count and watts and the rule's string voltage with "(rule)", as the schedule does.

### 1.5 Tests

Hand-worked on the Pila sample project (`tests/test_drawings.py::PILA_DOC`, synthetic weather, the datasheet
fixture and a 500 V maximum PV voltage typed on the default inverter, as `test_plans_datasheets.py` does): the
sheet exists and is named on the cover; `pdftotext` finds "S1: 6 × 585 W", "Voc 53.1 V STC, 54.8 V at 14 °C"
(6 × 54.83 = 329.0 V on the placard line), the DC breaker rating from `choices.dc_breaker`, "139 A" on the
battery port, the inverter-output breaker "40 A", "two-way meter" on a combination job and "nothing exported" on
an off-grid job, the balloon numbers C1–C7 identical to the schedule's rows, "Not to scale" in the title block;
without the datasheets every datasheet figure is `BLANK` and the string label carries "(rule)"; with
`service.main_breaker_a = 100`, `busbar_a = 100` and a 40 A grid breaker the 120 % check prints FAIL and
`poi_busbar` is in the warnings (not in `design_blocked`); with `busbar_a = 125` it passes (140 ≤ 150). The
existing `test_plans.py` set keeps its sheet count plus one.

**Effort M** (the symbol library S, the layout M, the service fields and the 120 % check S, tests S).

---

## 2. Design analysis sheet

### 2.1 The contract: `pricing.choices.circuits`

A list the generator writes after the BOQ (a new function in `design_checks.py`, called at the end of
`generate_boq`), one row per circuit, read by the schedule, the SLD and this sheet:

```
{id: "C1", name: "PV string (each)", kind: "dc_pv" | "dc_combined" | "dc_battery" | "ac_inverter_output" | "ac_grid_feed" | "ac_bypass" | "egc",
 conductors: {n_total, n_current_carrying, size_mm2, insulation_c (90 for THHN and PV wire: verify the items), type: "THHN" | "PV wire" | "battery cable"},
 run_m, voltage_v, i_continuous_a, i_design_a (× 1.25; the PV row × 1.25 × 1.25), ocpd_a, ocpd_code,
 placement: "rooftop_conduit" | "rooftop_free_air" | "indoor_conduit" | "indoor_free_air", conduit_code, conduit_inner_diameter_mm,
 ambient_c, rooftop_adder_c, t_conductor_c,
 ampacity_base_a (at insulation_c), ampacity_terminal_a (at 75 °C), f_temp, f_fill, ampacity_derated_a,
 fill_pct, fill_limit_pct, egc_required_mm2, egc_provided_mm2,
 drop_pct (the BOQ's), checks: {ocpd_le_derated, terminal_ge_design, next_size_up_used, fill_ok, egc_ok}, status: "pass" | "fail" | "not checked", notes: [...]}
```

### 2.2 What the sheet shows

One table, a row per circuit (C1 PV string; C2 combined DC when strings join; C3 battery; C4 inverter output;
C5 grid feed; C6 bypass; C7 equipment grounding), columns: Circuit | Conductors (n × mm², type, insulation) |
Run | Continuous A | Design A (× 1.25) | Base ampacity (column) | Ambient °C (+ rooftop adder) | F_temp |
F_fill (n current-carrying) | Derated A | Terminal A (75 °C) | OCPD A | OCPD ≤ derated (next size up?) |
Drop % | Conduit (code, inside Ø) | Fill % / limit | EGC required / provided | Pass. Under it four notes:
**short-circuit**, **grounding electrode conductor**, **the tables used with their sources**, and **assumptions**.

### 2.3 Computation

**Ambient.** `derating.ambient_outdoor_c` (default 35 °C, **assumption**: the PVGIS typical-year air maxima of
the Laguna and Batangas cells are 30.5–34.1 °C, round 12) and `derating.ambient_indoor_c` (default 30 °C,
assumption), per project the higher of the setting and `ceil(results.site.tmy_max_air_c)` for outdoor runs.
**Rooftop adder** for a raceway on the roof: the NEC 2014 Table 310.15(B)(3)(c) bands by height above the roof
(0–13 mm: +33 °C; 13–90 mm: +22; 90–300: +17; 300–900: +14; above 900: +8) — **verify which the PEC 2017
adopted** (the NEC 2017 kept only +33 °C for raceways under 22 mm above the roof); a settings table
`derating.rooftop_adder_c` the owner confirms, and a wiring field `conduit_height_above_roof_mm` (default
25 mm, assumption: a conduit on the rails). The PV home runs in free air under the array take the outdoor
ambient without the adder (placement `rooftop_free_air`, the default for the string runs until the BOM carries
a rooftop conduit).

**Temperature correction** by the formula the NEC permits in place of the table (NEC 310.15(B)(2); the PEC
equivalent: **verify**): `F_temp = sqrt((T_insul − T_amb) / (T_insul − 30))`, T_insul 90 °C for THHN and PV
wire (verify the items' ratings; a text field `insulation_c` on the wire items, blank = 90 with the note).
The printed check values against the NEC 2014 Table 310.15(B)(2)(a) 90 °C column (31–35 °C 0.96, 36–40 0.91,
41–45 0.87, 46–50 0.82, 51–55 0.76, 56–60 0.71, 61–65 0.65, 66–70 0.58, 71–75 0.50) sit in the test, not in
the code.

**Bundling** (NEC 310.15(B)(3)(a); PEC **verify**): 1–3 current-carrying conductors 1.00, 4–6 0.80, 7–9 0.70,
10–20 0.50, 21–30 0.45, 31–40 0.40, 41+ 0.35; the neutral of a 2-wire 230 V circuit counts (both conductors
carry current); the EGC does not. A settings table `derating.fill_factors`.

**Base ampacity.** The wiring rules carry the 60 °C column today (`wiring.thhn_ampacity`, PEC 60 °C, round 3);
add `wiring.thhn_ampacity_75c` and `wiring.thhn_ampacity_90c` keyed by the same sizes, defaults from the NEC
2014 Table 310.15(B)(16) copper columns on the size mapping the 60 °C table already follows (3.5 mm² ≙ 12 AWG:
25/30 A; 5.5 ≙ 10: 35/40; 8.0 ≙ 8: 50/55; 14 ≙ 6: 65/75; 22 ≙ 4: 85/95; 30 ≙ 2: 115/130), **verify against PEC
Table 3.10.1.16**; the PV cable and the battery cable keep their single tables (`pv_cable_ampacity`,
`battery_cable_ampacity`) as the base at 90 °C with "verify the cable's rating" printed until the owner types
the maker's figure on the item (new numeric field `ampacity_a` on wire items, with `insulation_c`).

```
ampacity_derated = ampacity_base(T_insul column) × F_temp(T_amb + adder) × F_fill(n_cc)
checks:  ocpd_a ≤ ampacity_derated            (else: the next standard size above ampacity_derated may be used when
                                              ocpd_a ≤ 800 A and the circuit is not a multi-outlet branch: NEC 240.4(B);
                                              PEC 2.40 verify → "next size up" noted, still a pass)
         ampacity_terminal(75 °C column, uncorrected) ≥ i_design_a and ≥ ocpd_a   (NEC 110.14(C) terminal rule; verify)
         i_design_a ≤ ocpd_a                                                        (the BOQ's rule, restated)
```

**Conduit fill.** `fill_pct = Σ A_conductor / (π/4 × d_inner²)`; limits 53 % for one conductor, 31 % for two,
40 % for three or more (NEC Chapter 9 Table 1; PEC Chapter 10 **verify**). `A_conductor` from a new numeric
field on the wire items, `overall_area_mm2` (the insulated conductor's cross-section, from the PEC table or the
maker's sheet; the NEC Chapter 9 Table 5 THHN areas on the AWG mapping, 12 AWG 8.58 mm², 10 AWG 13.61, 8 AWG
23.61, 6 AWG 32.71, 4 AWG 53.16, 2 AWG 74.71, are the cited stand-ins the test uses, **verify**); `d_inner` from
a new numeric field on the raceway items, `inner_diameter_mm` (the BOM's conduit role is a 32 mm flexible
conduit whose inside diameter no table in the app holds). Either blank → the row prints "fill: not checked
(the conductor's area / the conduit's inside diameter is not on the item)".

**Short-circuit note.** Three lines: the utility's available fault current at the service "BLANK kA (from
{du_name}; verify)" from `service.fault_level_ka` (new, optional); the inverter's contribution from a new item
field `fault_current_a` ("maximum output fault current" on the maker's sheet; blank → "assumption: 1.5 × rated
output current for one cycle, {x} A — a grid-interactive inverter is current-limited; verify on the datasheet");
the battery's from the item (`fault_current_a` too, blank → "the BMS's short-circuit trip; verify with the
maker"); then "breaker interrupting ratings (AIC) ≥ the fault level at each point: BLANK — the AIC is not on
the breaker items; verify" (a new item field `aic_ka` on protective devices; when typed the sheet prints the
comparison with the DU figure).

**Equipment grounding conductor** per circuit from the OCPD rating (NEC 250.122; **PEC Table 2.50.1.122
verify**): a settings table `grounding.egc_by_ocpd` with the cited stand-ins 15 A → 2.0 mm², 20 → 3.5, 30 and
40 and 60 → 5.5, 100 → 8.0, 200 → 14, 300 → 22, 400 → 30 (the NEC's 14/12/10/8/6/4/3 AWG on the PEC's metric
series). Provided: the AC circuits' ground on the THHN line (the BOM's grounding run, its gauge), the array
bonding role's gauge for the PV rows, blank for the battery (the BOM has no battery-rack EGC: "verify"). The
**grounding electrode conductor**: for a rod electrode the GEC need not exceed 14 mm² copper (NEC 250.66(A);
PEC 2.50 **verify**); the sheet prints "GEC: {gauge of the ground-rod run} to the rod; required ≤ 14 mm² for a
rod (verify)".

### 2.4 Warnings and severity

- `conductor_derated` — **hard, blocks**: the OCPD is above the derated ampacity and no next-size-up applies;
  the breaker does not protect the conductor at temperature (the same class as the round-3 `ac_circuit`).
- `terminal_ampacity` — **hard, blocks**: the 75 °C column is below the design current.
- `conduit_fill` — **hard, not blocking**: over the limit; the fix is a larger conduit (a BOM line, pesos).
- `egc_undersized` — **hard, not blocking**: the provided EGC is below the table; the fix is a role change.
- `derating_not_checked` — **ordinary**: a figure missing (the item's area, the conduit's diameter, the cable's
  rating); the row prints "not checked" and the reason.
- `fault_level_unknown` — **ordinary**, once per job, until `service.fault_level_ka` and the AIC are typed.

### 2.5 What prints when an input is missing

A row with a blank table value prints `BLANK` in that cell and "not checked" in Pass; the assumptions note lists
every default used (ambient 35 °C, the adder band, 90 °C insulation, the 1.5 × fault assumption) with the word
"assumption". Nothing in Pass reads "pass" on an assumption alone: a pass computed on an assumed ambient prints
"pass (ambient assumed 35 °C)".

### 2.6 Tests (hand-worked)

- Inverter output, 6 kW: 26.1 A, design 32.6 A, breaker 40 A, 8.0 mm² THHN, indoor 30 °C, 2 current-carrying:
  base 90 °C 55 A, F_temp 1.00, F_fill 1.00 → 55 A ≥ 40 ✓; terminal 75 °C 50 A ≥ 40 ✓ → pass. At 35 °C outdoor:
  F_temp = sqrt(55/60) = 0.957 → 52.7 A, still pass.
- PV string, the 630 W panel: I_cond 25.28 A, breaker 32 A, 4 mm² PV wire at the app's 40 A (verify), free air
  under the array at 35 °C: F = 0.957 → 38.3 A ≥ 32 ✓ pass. The same run in a conduit 25 mm above the roof
  (adder +22 °C → 57 °C): F = sqrt(33/60) = 0.742 → 29.7 A < 32 A, next standard size above 29.7 is 32 → pass
  "next size up". With the 2017-style single adder (+33 → 68 °C): F = sqrt(22/60) = 0.606 → 24.2 A < 25.28 A
  design → **fail**, `conductor_derated`, the 6 mm² cable is needed: the test states both outcomes and the
  settings decide (6.3 asks the owner which band table the PEE uses).
- Battery, 139 A inverter current, 250 A breaker, 70 mm² lug pairs at 270 A, indoor: 270 ≥ 250 ✓; EGC blank →
  "verify".
- Conduit fill, 3 × 8.0 mm² THHN (L, N, G) in the 32 mm flexible conduit with `inner_diameter_mm` 29 typed in
  the test: Σ = 3 × 23.61 = 70.8 mm², area 660.5 mm², 10.7 % ≤ 40 % ✓; with the diameter blank → "not checked".
- EGC: the 40 A AC circuit needs 5.5 mm², the grounding run is on the 8.0 mm² line → pass; the PV row (32 A)
  needs 5.5 mm², the bonding role carries 10 mm² → pass; a bonding role set to the 3.5 mm² wire → fail,
  `egc_undersized`.
- The round-3 sample job (8 panels, 6 kW, 11.7 kWh, no datasheets) keeps its BOM and totals; the circuits
  block carries seven rows and no blocking code.

**Effort L** (the tables and item fields S, the engine M, the sheet M, tests S).

---

## 3. Mounting detail and the roof construction

### 3.1 Roof types

The company meets, on its Laguna and Batangas jobs (6.1 asks the owner to confirm the list):

| Roof | Mounting | In scope now |
|---|---|---|
| rib-type (trapezoidal) long-span metal sheet on steel C-purlins | L-foot on the rib crest, self-drilling screw with bonded EPDM washer into the purlin; or a rib clamp with no penetration | **yes** (the first detail) |
| corrugated galvanised sheet on steel or wood purlins | L-foot on the crest, screw into the purlin or rafter | **yes** (the same detail, the profile differs) |
| clay or concrete tile on battens and rafters | tile hook or tegula bracket under the tile, screwed to the rafter (the BOM has tile brackets as items, no role) | **a second detail**, once the owner confirms the bracket and the screw (6.1) |
| concrete deck (flat) | ballast or chemical anchor, tilted frames | **not now**: needs the deck's structural check and a different mounting set |

The assessment records the roof type per face; a face of a type that is not in scope prints "mounting detail:
not drawn for {type}; the structural check is the engineer's" on the sheet and raises `roof_type_out_of_scope`
(**ordinary**).

### 3.2 The roof construction fields

`RoofFace.construction: RoofConstruction` (`schemas.py`), with a project-level default `AssessmentDoc.roof_default`
the faces inherit ("same as the project" unless typed per face), edited on the Roof faces step as a fold "Roof
construction" under each face (`FacesEditor.tsx`): `roof_type` (rib_metal | corrugated_metal | tile_clay |
tile_concrete | concrete_deck | other; blank = not surveyed), `sheet_profile` (text, e.g. the rib height and
pitch), `purlin_material` (steel_c | steel_tubular | wood | none), `purlin_section` (text as the surveyor reads
it), `purlin_thickness_mm` (number; drives the pull-out figure), `purlin_spacing_m` (number), `rafter_spacing_m`
(number; tile roofs), `mean_roof_height_m` (number; the wind check's h), `condition` (text) and
`condition_flag` (sound | rusted | thin | old; a flag other than sound prints "condition: {flag}; verify the
roof carries the array" and raises `roof_condition`, **hard, not blocking**). No field has a default; a blank
prints `BLANK` with "not surveyed".

### 3.3 The standard detail (drawn)

One sheet "Mounting detail", two drawings at **1:5** (a 400 mm section is 80 mm on paper), the second only when a
face is a tile roof:

**Detail A, metal sheet on purlins** — a section across the rail at an L-foot: the purlin (a C-section, hatched,
its typed section and spacing as callouts), the roof sheet profile (a polyline crest–valley–crest; rib-type
trapezoid or corrugated sine, from `roof_type`), the L-foot on the crest, the self-drilling screw through the
crest into the purlin with the EPDM bonded washer, a sealant bead at the penetration (the `sealant` role),
the rail on the L-foot with its bolt, the panel frame on the rail held by a mid clamp (left) and an end clamp
(right), the bonding lug and the bonding conductor on the rail (the `earth_lug` and `array_bonding` roles),
the panel glass line. Callouts numbered to the BOM roles (rail, l_foot, mid_clamp, end_clamp, splice,
earth_lug, sealant, and "fastener: {screw size and length} into the purlin" from the new fastener fields, 3.4).
Dimensions: foot spacing along the rail (3.5), the rail-to-rail spacing (the panel's dimension up the slope ×
0.5, assumption: the rails at the quarter points, the maker's clamping zone verify), the panel edge overhang,
the clearance under the panel (the L-foot height, typed on the item or blank). Line weights: section cuts 0.7,
hatching 0.3, callout leaders 0.25.

**Detail B, tile roof** — the rafter and batten, the tile courses, the hook under the tile screwed to the
rafter, the rail on the hook, the clamps and the bonding as in A.

**Plan key** beside the section: a 2 × 3 panel patch in plan showing the two rail lines, the feet on the purlin
lines (the purlin spacing drawn when typed, dashed), the splice, the clamps; "feet on every {k}-th purlin" from
3.5.

### 3.4 The fastener and the feet: new settings and item fields

`PricingConfig.mounting` (Pricing settings › Mounting and wind): `screws_per_foot` (default 2, assumption; the
L-foot item's set says "screw, rubber pad and bolt"), `fastener_pullout_kn` (blank: the maker's allowable
withdrawal per screw in the purlin material and thickness the office types, with `fastener_pullout_source`
text; a labelled assumption only when the owner types one), `fastener_description` (text: size, length, washer),
`foot_spacing_max_m` (blank; the rail maker's maximum span, verify), `rail_position_fraction` (0.25,
assumption). Per project the uplift check may override `fastener_pullout_kn` with a figure for that roof
(`doc.roof_default.fastener_pullout_kn`, with its source).

### 3.5 The uplift check (NSCP 2015 Section 207, allowable stress design; every figure verify)

```
V        basic wind speed, 3-s gust at 10 m, Occupancy Category II, by wind zone     (NSCP 2015 Figure 207A.5-1A: verify)
Kz       velocity pressure exposure coefficient at h: 2.01 × (max(h, 4.6) / zg)^(2/α)  (NSCP Table 207A.9-1 ≡ ASCE 7-10 Table 26.9-1: verify)
         α, zg by exposure: B 7.0, 365.76 m; C 9.5, 274.32 m; D 11.5, 213.36 m        (cited stand-ins; verify)
Kzt      topographic factor, 1.0 unless typed (a ridge or hill: the PEE's)             (NSCP 207A.8: verify)
Kd       directionality, 0.85 for components and cladding                            (NSCP Table 207A.6-1: verify)
qh       = 0.613 × Kz × Kzt × Kd × V²   [N/m², V in m/s]                             (NSCP 207B.3-1 / 207E.3-1: verify)
GCp      external pressure coefficient, components and cladding, for the roof zone the panel sits in
         (gable or hip, the face's tilt, zone 1 interior / 2 edge / 3 corner, effective area = one panel):
         read by the PEE from the NSCP figure (207E.4-2A/B/C or its hip and gable successors: verify) and
         TYPED per project (doc.wind.gcp_zone1/2/3); the app ships none. Assumption until typed: the worst
         zone's figure for every panel, if the PEE types only one.
p_up     = qh × |GCp|   net uplift on the panel (assumption: the array sits above the roof surface, so the
         internal pressure GCpi does not act on it; the PEE may replace this with the rooftop-solar method of
         ASCE 7-16 29.4.3 / 29.4.4 (GCrn with γp, γc, γE) when the office adopts it: verify)
A_panel  = panel_length_m × panel_width_m
D        panel weight (the item's weight_kg × 9.81) + the rail share (mounting.rail_kg_per_m × rail per panel), /A_panel as a pressure
T_panel  = 0.6 × p_up × A_panel − 0.6 × D × A_panel       (ASD combination 0.6D + 0.6W, NSCP 203.4: verify; zero when negative)
strip    = the panel dimension across the rails × 0.5    (each rail line carries half the panel; portrait: length/2)
s_foot   = the foot spacing along the rail: a multiple of purlin_spacing_m (feet sit on purlins), ≤ foot_spacing_max_m
T_foot   = (0.6 × p_up − 0.6 × D) × s_foot × strip
T_screw  = T_foot / screws_per_foot   ≤ fastener_pullout_kn   → pass
s_allow  = screws_per_foot × fastener_pullout_kn / ((0.6 × p_up − 0.6 × D) × strip)
feet per rail line = floor(line_length / s_foot) + 1,  s_foot = the largest multiple of purlin_spacing_m ≤ min(s_allow, foot_spacing_max_m)
```

The BOM: when `purlin_spacing_m` is typed, the `l_foot` count follows `feet per rail line` instead of
`l_feet_per_rail` per rail piece, and the note says "feet on every purlin ({s} m)"; the sheet prints both
counts when they differ. The screws: `screws_per_foot × feet` as a line on the mounting detail (not a BOM line:
the owner's round-4 rule keeps fasteners inside the L-foot set; the count prints for the crew).

**Wind zone lookup.** `core/wind_zones.json`: `{province: {zone, v_kmh, source}}` keyed by the province names
of `towns_ph.json`; shipped **empty of figures** (zone and V blank, the file's header naming NSCP 2015 Figure
207A.5-1A as the source the owner reads them from). The pin → the nearest town (`core/towns.py`) → the
province → the row; a project override `doc.wind.zone`, `v_kmh`, `exposure` (B default, assumption: a town
site; C for open ground, the lakeshore and the coast), `kzt`. For the owner's reading of the figure: the 2010
edition zoned the country in three (Zone I 250, Zone II 200, Zone III 150 km/h) and placed Laguna and Batangas
in Zone II — the reviewer's recollection, **verify on the 2015 figure before typing**. Settings › Mounting and
wind shows the table with "not set" per province until typed; a project in a province without a figure prints
"wind zone: not set in Settings" and the uplift check is "not checked".

### 3.6 What prints when an input is missing

Each line of the computation prints its inputs; a blank V, GCp, purlin spacing, mean roof height or pull-out
figure stops the chain at that line with `BLANK` and "not typed / not surveyed / not set"; the Pass column reads
"not checked" and `uplift_not_checked` (**ordinary**) says what is missing. A fail: `uplift_fail`, **hard, not
blocking** (the fix is more feet or a stronger fastener, the PEE's; the plans print FAIL in red). A pass
computed on an assumption (exposure B untyped, one GCp for all zones, the screws per foot default) prints
"pass (assumption: …)".

### 3.7 Tests (hand-worked; every figure below is a test input, not a value the app ships)

V = 200 km/h = 55.56 m/s, exposure B, h = 5 m: Kz = 2.01 × (4.6/365.76)^(2/7) = 0.576 (the ASCE table's 0.57 at
0–4.6 m); qh = 0.613 × 0.576 × 1.0 × 0.85 × 55.56² = 926 N/m²; GCp −1.8 typed → p_up = 1.667 kPa; the 585 W
panel 2.278 × 1.134 = 2.583 m², 32 kg (0.314 kN; 0.122 kPa): T_panel = 0.6 × (1.667 − 0.122) × 2.583 = 2.39 kN;
portrait rails, strip 1.139 m, purlins at 0.6 m, feet at 1.2 m: T_foot = 0.6 × 1.545 × 1.2 × 1.139 = 1.267 kN,
two screws → 0.634 kN each; pull-out typed 1.5 kN → pass (ratio 0.42); typed 0.5 kN → fail, s_allow = 1.0 /
(0.927 × 1.139) = 0.947 m → feet on every purlin (0.6 m) → 5 feet per 2.4 m rail instead of 3; on the 8-panel sample roof (two rows of four, 4.536 m rail
lines, four lines) the BOM's L-foot line moves from 24 (8 rails × 3) to 32 (floor(4.536 / 0.6) + 1 = 8 feet on
each of the four lines). Exposure C (α 9.5, zg 274.32): Kz = 2.01 × (4.6/274.32)^(2/9.5) =
0.849 (the table's 0.85), qh 1,365 N/m². No V → "not checked"; the purlin spacing blank → the BOM keeps 3 per
rail and the sheet says so.

**Effort L** (the fields and the settings S, the two details M, the wind engine and the zone file M, the BOM
tie-in S, tests M; 4–5 days).

---

## 4. Vicinity map and site plan (one sheet)

### 4.1 The vicinity map, automated from OpenStreetMap tiles

The owner's "can you just automate this since we already use the openmap": yes, within the tile usage policy.

**The policy** (tile.openstreetmap.org, `https://operations.osmfoundation.org/policies/tiles/`; **verify the
current text before the build**): the tile servers are run on donated resources for light use; heavy use (an
app distributed to many users relying on them) needs permission; bulk downloading is forbidden (in particular
areas of more than about 250 tiles at zoom 17 and above for offline use); a valid HTTP User-Agent that
identifies the application and a contact is required; attribution "© OpenStreetMap contributors" with the
licence (ODbL) must be displayed; tiles should be cached per the HTTP expiry headers or at least seven days;
no more than two download threads. **At the company's scale** — one project at a time, 18 tiles per project
fetched once and kept — this is light use by any reading; the build respects it by: a User-Agent
`PLDSolarApp/<version> (+{settings.website_base}; {profile.email})` (6.1: the contact address), one fetch per
project pin, sequential requests (one thread), the tile cache below, the attribution and licence line on the
sheet, no prefetching, and the upload as the fallback. If the volume ever grows past a few dozen projects a
month, move to a commercial tile provider with a key (a setting `map_tiles_url` with `{z}/{x}/{y}` and an
attribution string makes the source swappable from day one).

**Tiles.** Web Mercator: `n = 2^z`, `x = floor((lon + 180) / 360 × n)`, `y = floor((1 − ln(tan φ + sec φ) / π) / 2
× n)` with φ the latitude in radians; the pin's pixel inside its tile from the fractional parts × 256; metres
per pixel `156543.03 × cos φ / n`. Two mosaics per project: the **main map at zoom 16, 3 × 3 tiles** (768 px,
about 1.78 km across at 14 °N) centred on the pin's tile, and an **inset at zoom 12, 3 × 3 tiles** (about
28 km: the town and its neighbours, the way a permit's vicinity map places the site); 18 tiles. Composed with
Pillow into one PNG per mosaic, the pin drawn as the brand's marker (a filled circle with a white ring and a
stem) at its pixel, a north arrow top right (tiles are north-up, so a straight arrow), a scale bar bottom left
(200 m at zoom 16 = 86 px at 14 °N; 5 km on the inset), the attribution strip along the bottom "Map data ©
OpenStreetMap contributors, ODbL — tile.openstreetmap.org, fetched {date}, zoom {z}". Fetch with `httpx`
(already a dependency), timeout 8 s per tile, one retry, `User-Agent` as above, through the environment's
proxy settings as any outbound call.

**Cache.** Tiles under `{data_dir}/tiles/{z}/{x}/{y}.png` with the fetch date in the file's mtime, reused within
30 days (the policy's seven-day floor, generously); the composed mosaics under `{data_dir}/projects/{id}/
vicinity-z16.png` and `-z12.png`, keyed by the pin rounded to five decimals, remade only when the pin moves
or the office presses "Refresh map". The composed maps are the project's record: kept with it, deleted with it
(the retention run and `DELETE /api/assessments/{id}` remove the folder).

**When the fetch fails** (no outside access, a timeout, an HTTP error, the policy's 429): the sheet prints the
pin "{lat:.5f}, {lon:.5f}", the address, the town and province, and "vicinity map: not fetched ({reason}); the
office may upload a screen grab (Documents card › Vicinity map)". The Documents card shows the same note with
the "Fetch map" and "Upload" buttons; the fetch runs when the plans are first generated or on the button, never
on every Calculate.

**The upload (the override).** `POST /api/assessments/{id}/vicinity-map` (multipart, owner or engineer): PNG or
JPEG, 8 MB cap on the body (`MAX_UPLOAD_BODY` route list in `main.py`), decoded and re-encoded with Pillow
(EXIF stripped, the longer side capped at 2,400 px, PNG), stored as `{data_dir}/projects/{id}/vicinity-upload.png`;
`DELETE` removes it. `Assessment.vicinity_map` (a new JSON column: `{source: "upload" | "osm", file, uploaded_at,
note}`) says which the sheet prints: the upload wins when present, and the sheet's caption reads "vicinity map:
uploaded by the office on {date}" with the attribution the office types (`note`, e.g. "screen grab of the
office map, © OpenStreetMap contributors"). `GET /api/assessments/{id}/vicinity-map.png` serves whichever is
current for the Documents card's preview (behind the session like every route).

### 4.2 The site plan

The right half of the sheet: the roof faces of the assessment in plan, true north up, drawn to scale.

- **Each face** as its plan-view outline: the rectangle, hip trapezoid or triangle from `results.geometry`
  (eave, slope, ridge, the outline points) with the slope dimension foreshortened by `cos(tilt)`, rotated so the
  eave's outward normal points to `azimuth_deg` (the drawing's up is true north: the rotation is `azimuth +
  180` of today's eave-at-the-bottom plan, `north_angle_deg` in reverse), the used panels drawn inside (the
  same rectangles as the layout sheet, rotated), the face name and "{n} panels".
- **Placement.** Today the assessment holds no relative positions. Add per face `plan_offset_m: [east, north]`
  of the face's eave midpoint from the pin (numbers the surveyor types, or picked by dragging the face on the
  office map: a later step) and `plan_rotation_lock` (none). Faces without an offset are laid side by side
  along the sheet with 1 m gaps and the note "relative positions not surveyed; faces shown in true orientation
  only" (`site_plan_positions`, **ordinary**).
- **The lot and the house.** Add `AssessmentDoc.site: SitePlan` with `lot_polygon` and `house_polygon` as
  lists of `[lat, lon]`, drawn on the office map with Leaflet's draw tools (`MapPicker.tsx` gains a "Draw the lot"
  and "Draw the house outline" mode, the polygons stored on the document), converted to metres east/north of
  the pin by the equirectangular projection (`east = (lon − lon0) × 111,320 × cos φ0`, `north = (lat − lat0) ×
  110,574`; adequate below 500 m), drawn as the property line (dash-dot, 0.5) and the house outline (0.7).
  Until drawn: "property line: not surveyed" and no setback dimension. Setbacks print when both the lot and
  the house exist: the perpendicular distance from each house edge to the nearest lot edge, as dimension
  lines (the LGU's setback requirement is not checked: "verify the zoning setback").
- **The equipment and the POI.** `site.inverter_location` (text: "ground floor utility room, south wall") and
  `site.inverter_point` (`[lat, lon]`, picked on the map or dragged on the site plan), the same for the
  battery and for the point of interconnection and the meter (`site.poi_point`, `site.meter_point`), each drawn
  as a labelled symbol (inverter square, battery plates, a filled circle for the POI, "M" in a circle for the
  meter) with the typed text; blank → the legend line "inverter and battery location: not chosen (Site step)".
- **Scale** from `fit_scale` over `STANDARD_SCALES` on the extent of the lot polygon (else the faces' bounding
  box) in a 190 × 230 mm box, stated in the title block; a 1 m / 5 m scale bar; the north arrow.
- **Dimensions**: the lot edges' lengths (from the polygon), the house's overall, the faces' eaves (as the
  layout sheets).

### 4.3 Tests (hand-worked)

- Tile indices for the Pila sample pin 14.2335, 121.3645 at zoom 16: x = floor(301.3645 / 360 × 65536) = 54861,
  y = floor((1 − ln(tan 0.24842 + sec 0.24842) / π) / 2 × 65536) = 30149; the pin's pixel in the 3 × 3 mosaic
  (256 + 0.6 × 256, 256 + 0.6 × 256) to the pixel; metres per pixel 2.315; the scale bar 200 m = 86 px.
- The fetch is mocked (`httpx` transport): nine 256 × 256 tiles returned → one 768 × 768 PNG with the pin, the
  arrow, the bar and the attribution text; a 429 or a timeout → no file, the sheet prints the coordinates, the
  address and the reason; a second build fetches nothing (the cache); moving the pin by more than a tile
  refetches; the User-Agent header on every request; at most one request in flight.
- The upload: a 3,000 × 2,000 JPEG with EXIF → a 2,400 px PNG without EXIF; a 9 MB file → 413; a PDF → 422;
  with an upload present the sheet's caption says "uploaded by the office".
- The site plan: the two faces of the sample (9 × 5 m at 180°, 7 × 4 m hip at 90°) print rotated so the south
  face's eave is at the bottom and the east face's eave is at the right, slope lengths 5 × cos 18° = 4.76 m and
  4 × cos 15° = 3.86 m; a lot polygon of four corners 15 × 12 m typed in the test prints its four edge lengths
  and the scale 1:100 (15 m is 150 mm at 1:100 and fits the 190 mm box; 1:75 would need 200 mm); no polygon →
  "not surveyed".
- The retention run and the project delete remove `{data_dir}/projects/{id}/`.

**Effort M** (the fetcher, cache and composition S–M, the upload S, the sheet M, the site plan with the
offsets M; the Leaflet draw tools for the lot and house are the one L piece and can follow: 2.5 days without
them, 4 with).

---

## 5. Schedule of loads in the permit's format

### 5.1 The format (verify against the LGU's sample: 6.1)

The schedule of loads on a sealed Philippine electrical plan is a table per panelboard: a header line
"Panelboard {name}: {voltage} V, {phase}Ø {wires}W, main breaker {AT} AT / {AF} AF, bus {A} A, fed from {source}",
then the columns **Circuit No. | Description of load (count × type) | Load (W) | Load (VA) | Volts | Amperes |
Wire (mm² THHN) | Conduit (mm) | OCPD (AT/AF, poles) | Remarks**, the connected-load total, the demand factor
line, the demand load and the main breaker. **Verify** the LGU's column order (the building official's
reviewer and the DU each have a sample; the owner's past sealed plans carry it).

### 5.2 What the sheet shows

Three blocks:

1. **The existing loads, from the energy audit**, grouped as the format groups them: Lighting (`category ==
   "lighting"`), Convenience outlets (small appliances: refrigerator, TV, fans, kitchen, `other`), Equipment
   (`aircon_*`, pumps, water heaters, motors: the audit's categories with a motor or a compressor, listed in a
   settings map `loads.equipment_categories`), each line "{quantity} × {name}, {W each} W" with W, VA (VA = W /
   PF, PF 1.00 assumption for lighting and outlets, 0.85 assumption for equipment, both labelled and settable
   under `loads.power_factor`), Volts 230 (`service.voltage_v` or the wiring rules' with the assumption label),
   Amperes = VA / V, **Wire, Conduit, OCPD and Circuit No. blank** (the audit holds loads, not circuits: "the
   engineer's, from the existing panelboard"), Remarks "existing" / "planned" (`status == "future"` lines are
   listed under a sub-heading "Planned loads" and excluded from the existing total). Totals: connected load W
   and VA; "demand load: BLANK — the demand factors of PEC 2.20 (**verify**) are the engineer's; the hourly
   profile's coincident peak is {sizing.inverter.peak_load_kw} kW" printed as the audit's own figure.
2. **The PV system as a source**: "PV array: {n} × {W} W = {kWp} kWp DC, {strings} strings; inverter: {kW} kW AC,
   {I} A at {V} V, 1Ø; PV backfeed breaker: {ac_grid_breaker_a} A 2P; wire {ac_grid_gauge} mm² THHN; conduit
   {conduit role, size}; energy storage: {units} × {kWh} = {kWh} kWh, {V} V, max discharge {A} A (none on net
   metering)"; the DC side's figures stay on the SLD and the circuit schedule.
3. **The point of interconnection**: the typed choice (1.3) in words, the existing main breaker and busbar, the
   120 % check line with its result, the meter line (two-way on net metering), "{du_name}, account {account_no
   or BLANK}".

### 5.3 What the engineer still fills by hand

The circuit numbers and the branch-circuit split of the existing panelboard (unless the office types the
existing circuits: an optional `service.circuits` list `{no, description, breaker_a, poles, wire_mm2, conduit_mm}`
the sheet prints verbatim above the audit's loads when present), the demand factors and the demand load, the
main breaker's adequacy with the PV source, the panel schedule's "fed from". The sheet says so in a footnote.

### 5.4 Tests

The sample audit (8 LED bulbs 9 W, a 150 W refrigerator, a 1,200 W inverter aircon, a 90 W TV, a planned second
aircon): Lighting 72 W / 72 VA / 0.31 A; Convenience outlets 240 W / 240 VA / 1.04 A; Equipment 1,200 W /
1,412 VA (PF 0.85, assumption) / 6.14 A; planned 1,200 W listed apart; connected (existing) 1,512 W; the PV
block "6 kW, 26.1 A, 40 A 2P, 8.0 mm²"; the POI block with the 120 % line; every blank cell is `BLANK`, no
circuit number is printed unless `service.circuits` is typed, in which case the typed rows print first.

**Effort M** (the sheet and the grouping S–M, the service circuits input S, tests S; 1.5 days).

---

## 6. Title block

### 6.1 Profile fields (Settings › Company, `profile.py PROFILE_FIELDS`, printed on every sheet)

`pee_name`, `pee_license` (exist); add `pee_prc_valid_until` (date text), `pee_ptr_no`, `pee_ptr_date`,
`pee_ptr_place` (the PTR line reads "PTR No. {no}, issued {date} at {place}"), `pee_tin`, `pee_address`,
`pee_firm` (the firm or "sole practice") and `pee_firm_address`, `pee_phone`, `pee_email`. None is public
(`PUBLIC_KEYS` unchanged); the Settings page groups them under "Signing engineer". The signature block becomes
six lines: "Signed and sealed by the Professional Electrical Engineer"; "{pee_name}, PEE — PRC No. {license},
valid until {date}"; "PTR No. {no}, issued {date} at {place}"; "TIN {tin}"; "{address} · {firm}"; "Signature
________ Date ________ Seal". A blank field prints `BLANK` as today; nothing moves on the other three cells.

### 6.2 The owner and project cell

The project cell gains "Owner: {customer_name}" above the address (the customer is the owner on the plans) and
the kind in words (`KIND_LABEL`); the system line stays.

### 6.3 The revision line and the revision log

`Assessment.revisions` (a new JSON column, append-only): entries `{no, date, note, by}`; `plans_issued_at`
(like `proposal_issued_at`) is set when the plans PDF is first generated and is revision 0 ("first issue").
"Issue a revision" on the Documents card (a note required, the signed-in user's name recorded) appends the next
number; "Reopen design" does not clear the log. The title block prints "Rev. {n}: {note} — {date}" for the
latest, with "calculated {stamp}" beside it as today; the cover carries a revision table (the last five) and a
**sheet index** (every sheet's name and number, from `sheet_names`). An older record without the column prints
"Rev. 0" as today.

### 6.4 Tests

The profile fields round-trip through Settings; the title block prints the six lines with `BLANK` where empty
and the full lines when filled (`pdftotext` on page 1); a revision appended prints "Rev. 1" on every sheet and
in the cover's table; `plans_issued_at` is set on the first plans build and unchanged on the second; the
existing `test_plans.py` assertions on the title block hold.

**Effort S** (the fields S, the block and index S, the revision log and the card button S; one day in all).

---

## 7. Order of work, and what runs in parallel

1. **First, together (two days):** item 6 (every sheet changes under it) and the `circuits` contract of 2.1
   (both sheets of items 1 and 2 read it), plus the survey fields of 1.3 and 3.2 and the site fields of 4.2 in
   one schema change, so the office can start surveying service entrances and roof construction while the
   sheets are built.
2. **In parallel:** item 2 (the design analysis: engine then sheet) and item 1 (the SLD) — one implementer each;
   item 5 (the schedule of loads) with item 1's implementer after the SLD, since both read the service block.
3. **In parallel with 2:** item 4 (the vicinity map, the upload, the site plan with typed offsets); the Leaflet
   draw tools last.
4. **Last:** item 3 (the mounting details and the uplift check), once the owner has answered 6.1's roof-type and
   fastener questions and the wind-zone source is in hand; its fields went in at step 1.

Effort total: 6 (S, 1 day) + contract (S, 0.5) + 1 (M, 2) + 2 (L, 3) + 3 (L, 4.5) + 4 (M, 2.5; +1.5 for the draw
tools) + 5 (M, 1.5) = **15 days of work, 16.5 with the lot-drawing tools**; about nine calendar days with two
implementers.

## 8. Tests, in one list

The hand-worked cases of 1.5, 2.6, 3.7, 4.3, 5.4 and 6.4; the set's sheet count and names on the cover (cover,
layouts, schedule(s), SLD, design analysis, mounting detail, vicinity map and site plan, schedule of loads, the
last sheet now listing only what the owner has not supplied); "nothing invented": a fixture document with every
new field blank builds the whole set with `BLANK` and a reason on every missing figure and no `pass` on an
assumption alone; `design_blocked` carries exactly the blocking codes of 2.4; the round-3 sample job's BOM,
totals and the ₱329,300 unchanged; the quick estimate untouched (no new code path reaches `core/quick.py`);
the tile fetch mocked, never live in the suite; `pdftotext` skipped when absent, as today.

## 9. What to ask the owner

1. **Roof types and feet** (3.1, 3.3): which roofs the crews actually mount on (rib-type on steel C-purlins,
   corrugated, tile; concrete decks?), the foot per roof (L-foot with screws, rib clamp, hanger bolt, tile
   hook), the screw used (size, length, washer) and the rail maker's maximum foot span; a photo of a finished
   penetration for the detail.
2. **Fastener figures** (3.4): the screw maker's allowable withdrawal in 1.2, 1.5 and 2.0 mm steel purlins and in
   wood, with the sheet it comes from; the typical purlin sections and spacings the surveyor should expect (for
   the field's choices, not defaults).
3. **The wind-zone source** (3.5): which NSCP edition the PEE works from, the zone and basic wind speed the PEE
   reads for Laguna and Batangas from its figure, the exposure the PEE uses in the towns and on the lakeshore,
   and the GCp figures per roof zone the PEE will type (or whether the PEE prefers the ASCE 7-16 rooftop-solar
   coefficients); the derating band table the PEE applies for rooftop raceways (2.3).
4. **The DU** (1.1, 2.3): the available fault current at a residential service from Meralco and BATELEC II
   (the DU states it on request, verify), the DU's SLD and placard samples and its net-metering checklist; the
   breakers' interrupting ratings from the supplier.
5. **The LGU format** (5.1): a past sealed plan's schedule of loads and title block from Pila or the Batangas
   towns the company works in, to match column for column.
6. **The signing engineer** (6.1): the PEE's PTR, TIN, address and firm; whether the PEE is the same on every
   job.
7. **The map** (4.1): the contact e-mail for the User-Agent; the upload as the day-one fallback; whether the
   office will draw the lot and house outlines on the map or keep typing offsets.

## 10. The three decisions needed from the coordinator before the build

1. **The wind coefficients' home**: the app ships no NSCP table or figure value; the PEE types V (by zone), the
   exposure and the GCp per roof zone, and the sheet prints each with its source — against the alternative of
   a settings table pre-filled from the 2010 zoning with "verify". I recommend the first (nothing invented, the
   PEE owns the figure); it means the uplift check reads "not checked" until the office types the figures.
2. **The vicinity map's source**: server-side OpenStreetMap tiles under the usage policy with the upload as the
   fallback (my recommendation, with the swappable tile URL), or the upload alone on day one with the fetch as
   a later step; and the User-Agent contact.
3. **Severity**: the design analysis blocks the customer documents on a conductor the breaker does not protect
   at temperature and on a terminal-ampacity failure (as the round-3 AC coordination does), while conduit fill,
   EGC size, the uplift and the POI 120 % rule are hard but print — or every new check prints without blocking
   until the owner has seen a season of results.
