# Round 13, item 2: the design analysis sheet

Built 10 October 2026 from `engineer-brief.md`, section 2, on step 1's circuits contract (`step1.md`), under the
coordinator's three decisions: (a) the severities of 2.4 as the brief recommends (a conductor the breaker does not protect
at temperature and a terminal-ampacity failure block the customer documents like the round-3 AC coordination; the conduit
fill, the EGC and GEC sizes and the POI 120 % rule are hard warnings that print without blocking); (b) nothing invented
(every PEC or NEC table value the brief marks "verify" is a settings table with its citation and a verify flag, printed
with the flag on the sheet, editable in Settings; a check that needs a figure not on file reads "not checked" with the
reason; the labelled assumptions print as assumptions); (c) the DU's fault level from the service block's
`fault_level_ka` the office types, "from the DU, verify" when blank. Three commits: the engine with its settings and item
fields; the sheet with the Settings page and the tests; the documents. The suite went from 272 to **283 tests**;
`npm run build` passes and `npm run lint` stays at its seven baseline warnings.

## 1. What was built

- **The engine**, `backend/solarapp/pricing/design_analysis.py`: `analyse_design(choices, lines, catalog, cfg, inverter,
  battery, units, tmy_max_air_c, service)` derates the seven `pricing.choices.circuits` records in place and writes
  `pricing.choices.design_analysis` (the ambient and its source, the assumptions, the tables used with their sources and
  flags, the short-circuit note, the GEC line, the rows not checked, the codes that block); the pure pieces
  (`temperature_factor`, `rooftop_adder`, `bundling_factor`, `conduit_fill_pct`, `fill_limit_pct`, `egc_required_mm2`,
  `next_standard_size`, `ambient_for`, `base_ampacity`, `terminal_ampacity`, `derate_circuit`, `short_circuit_note`) are
  what the hand-worked tests call. `job.price_assessment` calls it right after `generate_boq` and adds its warnings, so
  `design_blocked` carries the blocking codes as before. The website estimate has no plan set: `core/quick.py` is
  untouched and its BOQ keeps the step-1 records; the pins hold.
- **Per circuit** (2.3): the ambient (outdoors the higher of the 35 °C setting and the project cell's typical-year air
  maximum ceiled, said which; indoors the 30 °C setting), the rooftop adder for a raceway on the roof from the band table
  at the settings' 25 mm, `insulation_c` from the item (else the settings' 90 °C, an assumption), the base ampacity (THHN
  from the column of the insulation rating; PV wire and battery cable from the maker's `ampacity_a` on the item, else the
  wiring rules' cable table at 90 °C with "the cable's rating: verify"), F_temp by the formula, F_fill from the bundling
  bands, the derated figure, the breaker against it with the next-size-up rule (the DC list for the strings, the AC list
  for the AC circuits, up to 800 A, on a single-load circuit whose conductor still carries the continuous current), the
  terminal rule on the THHN 75 °C column, the conduit fill from the items' `overall_area_mm2` and `inner_diameter_mm`
  (line, neutral and the grounding run of each AC circuit in its own raceway, the rule's placement), the EGC by the
  breaker rating against the provided conductor, C7's size against the largest the AC circuits need, and the GEC line
  (the grounding run's gauge to the rod against the 14 mm² rod maximum). `ampacity_base_a`, `ampacity_base_column`,
  `insulation_c`, `conductor_code`, `conductor_area_mm2`, the factors, the fill, the EGC required, the five derated checks,
  `status`, `qualifiers` and `not_checked` fill the record; the step-1 "later step" notes go.
- **The short-circuit note**: the utility's fault current from `service.fault_level_ka` ("BLANK kA (from {DU}; verify)"
  when blank); the inverter's contribution from the new item field `fault_current_a`, else "assumption: 1.5 × rated output
  current for one cycle, {x} A — a grid-interactive inverter is current-limited; verify on the datasheet"; the battery's
  from its `fault_current_a`, else "the BMS's short-circuit trip; verify with the maker"; the breakers' `aic_ka` compared
  with the DU's figure when both are typed, "BLANK — the AIC is not on the breaker items; verify" until then.
- **The warnings** (2.4) through the existing mechanism: `conductor_derated` and `terminal_ampacity` hard and
  `blocks_documents`; `conduit_fill` and `egc_undersized` hard, not blocking; `derating_not_checked` (one per job, the rows
  and the figures to type) and `fault_level_unknown` ordinary. The Design and outputs step lists them with the design codes.
- **The sheet**, `backend/solarapp/reports/plans_analysis.py`, through one hook in `plans_pdf.py` (`analysis_sheet(doc,
  results, items)` returns the sheet's name and flowables; the builder puts them after the schedule sheets and before the
  last sheet, in the index and with the title block): one table, a row per circuit, the columns of 2.2, then the
  short-circuit note and the GEC, the tables used with their sources, values and VERIFY / "confirmed in Settings" flags,
  the assumptions, and how to read Pass. A3 landscape in the set's style; one sheet on the sample record (the table falls
  to a second page only when the Pass texts outgrow it). A figure the app does not hold prints as a blank line with its
  reason. The schedule's four "to be completed" placeholders for derating, conduit fill, the EGC size and the GEC size now
  point to the sheet, the cover's note 6 likewise, and the last sheet keeps a "Design analysis: rows not checked" entry
  naming the figures to type (it drops when every row is checked).
- **The settings** (`config.py`): `wiring.thhn_ampacity_75c`, `wiring.thhn_ampacity_90c`, `wiring.thhn_ampacity_source`,
  `wiring.thhn_ampacity_verified`; a new `derating` block (`ambient_outdoor_c` 35, `ambient_indoor_c` 30,
  `conduit_height_above_roof_mm` 25, `rooftop_adder_c` with its source and flag, the temperature-correction source and
  flag, `bundling_factor_pct` with its source and flag, `conduit_fill_limit_pct` with its source and flag,
  `next_size_up_max_a` 800 with its source and flag, `terminal_rating_c` 75 with its source and flag,
  `default_insulation_c` 90, `inverter_fault_factor` 1.5); a new `grounding` block (`egc_by_ocpd` with its source and flag,
  `gec_rod_max_mm2` 14 with its source and flag). Every value is in `settings_version`. Settings › Pricing › **Design
  analysis** (a new page, `shared.ts`) edits the two blocks with the generic editors; the band tables name their key
  column and unit (`keyLabel`, `keyUnit` in `pricingMeta.ts`, a ten-line extension of `SizeTableEditor`); the two THHN
  columns sit under Wiring rules. Every key has its label, unit, help and long text (`test_settings_meta.py`).
- **The item fields** (`catalog.Item`, `models.MaterialItem`, `MaterialItemIn`/`Patch`, `ELECTRICAL_FIELDS` so a re-import
  keeps them, `store.ensure_material_columns` for an older database, the importer's header aliases, the Materials page):
  `overall_area_mm2`, `insulation_c`, `ampacity_a` on Wires and Terminations; `inner_diameter_mm` on Enclosures and
  Raceways; `fault_current_a` on inverters and batteries; `aic_ka` on Protective Devices. The Electrical column lists them.

## 2. The tables, their citations and flags

| Setting | Default (a cited stand-in) | Citation printed | Flag |
|---|---|---|---|
| `wiring.thhn_ampacity_75c` | 3.5 → 25, 5.5 → 35, 8.0 → 50, 14 → 65, 22 → 85, 30 → 115 A | NEC 2014 Table 310.15(B)(16), copper, on the mapping 3.5 mm² = 12 AWG, 5.5 = 10, 8.0 = 8, 14 = 6, 22 = 4, 30 = 2; the PEC 2017 equivalent: Table 3.10.1.16 | `thhn_ampacity_verified`, off |
| `wiring.thhn_ampacity_90c` | 30, 40, 55, 75, 95, 130 A on the same sizes | the same | the same |
| `derating.rooftop_adder_c` | 0 mm → +33, 13 → +22, 90 → +17, 300 → +14, 900 → +8 °C | NEC 2014 Table 310.15(B)(3)(c); the NEC 2017 keeps only +33 °C under 22 mm; which the PEC 2017 adopted is the open question (6.3) | `rooftop_adder_verified`, off |
| temperature correction | F = sqrt((T_insul − T_amb) / (T_insul − 30)) | NEC 310.15(B)(2) in place of Table 310.15(B)(2)(a); the PEC 2017 equivalent clause | `temperature_correction_verified`, off |
| `derating.bundling_factor_pct` | 1 → 100, 4 → 80, 7 → 70, 10 → 50, 21 → 45, 31 → 40, 41 → 35 % | NEC 310.15(B)(3)(a); the PEC 2017 equivalent table | `bundling_factor_verified`, off |
| `derating.conduit_fill_limit_pct` | 1 → 53, 2 → 31, 3 → 40 % | NEC Chapter 9 Table 1; the PEC 2017 equivalent in Chapter 10 | `conduit_fill_verified`, off |
| `derating.next_size_up_max_a` | 800 A | NEC 240.4(B); the PEC 2017 equivalent in Article 2.40 | `next_size_up_verified`, off |
| `derating.terminal_rating_c` | 75 °C | NEC 110.14(C); the PEC 2017 equivalent in Article 1.10 | `terminal_rule_verified`, off |
| `grounding.egc_by_ocpd` | 15 → 2.0, 20 → 3.5, 30/40/60 → 5.5, 100 → 8.0, 200 → 14, 300 → 22, 400 → 30 mm² | NEC 250.122 (14/12/10/8/6/4/3 AWG) on the PEC's metric series; the PEC 2017 equivalent: Table 2.50.1.122 | `egc_verified`, off |
| `grounding.gec_rod_max_mm2` | 14 mm² | NEC 250.66(A) (6 AWG); the PEC 2017 equivalent in Article 2.50 | `gec_verified`, off |
| `wiring.pv_cable_ampacity`, `battery_cable_ampacity` | the round-3 tables, unchanged | "the wiring rules' tables; verify the cable's rating (the maker's figure on the item replaces it)" | always VERIFY until the item carries `ampacity_a` |

The assumptions, each printed as one: outdoor ambient 35 °C (the PVGIS typical-year maxima of the Laguna and Batangas cells
are 30.5–34.1 °C; the project cell may raise it), indoor ambient 30 °C, a raceway on the roof 25 mm above it (a conduit on
the rails), insulation 90 °C for a wire item without a rating, the inverter's fault contribution 1.5 × its rated output
current for one cycle, each AC circuit's line, neutral and grounding run in its own raceway (the rule's placement).

## 3. The hand-worked tests (2.6) and the rest

`tests/test_design_analysis.py`: the settings tables are the brief's and move the version, an older config takes them; the
formula against the NEC 90 °C column (within 0.01 at each band's top) and the band tables; the 6 kW inverter output (55 A
base, F 1.00 → 55 ≥ 40, terminal 50 ≥ 40 and ≥ 32.6; at 35 °C F = 0.957 → 52.7 A; "not checked" for the fill on the seed,
"pass (ambient assumed 30 °C; THHN columns: verify; EGC table: verify)" with the items typed; a terminal column below the
breaker blocks); the 630 W string (38.3 A ≥ 32 in free air at 35 °C; in a rooftop conduit under the 2014 bands +22 → 57 °C,
F = 0.742 → 29.7 A, 32 A is the next size → pass "next size up"; under a single +33 band → 68 °C, F = 0.606 → 24.2 A <
25.28 A → fail, `conductor_derated`, blocks; the cell's maximum replacing the setting; the maker's ampacity replacing the
table); the battery (270 ≥ 250 pass, EGC "verify"; a 210 A cable under a 250 A breaker fails with no standard list to
rescue it); the conduit fill (3 × 23.61 mm² in 29 mm = 10.72 % ≤ 40 %; 53.4 % in a 13 mm conduit → `conduit_fill`, hard,
not blocking; the diameter blank → "not checked" naming the item); the EGC sizes (5.5 ≤ 8.0, 5.5 ≤ 10, the 3.5 mm² bonding
→ `egc_undersized`, hard, not blocking); the short-circuit note blank and typed (the AIC "does NOT hold" below the DU's
figure); the sample job's lines and total unchanged with seven rows and no blocking code; the item fields' round trip and
the older-database migration; the sheet through the API (six sheets, named on the cover; "not checked" with the reason,
never a bare pass, the blank lines, the VERIFY flags, the assumptions; with the datasheets and the figures typed every
applicable row passes, "10.7 % / 40 %", the DU's 10 kA from the service block, the AIC comparison, a table ticked
confirmed prints so); a conductor the breaker does not protect at temperature holds the plans (409) until the setting is
put back. `test_plans.py` and `test_survey_fields.py` follow the sheet count (five to six); the circuits, string-design,
settings-meta and pricing-engine suites are unchanged.

The plans PDF of the Pila sample, with the seed alone and with the datasheets and the figures typed, under
`scratchpad/plans13/analysis/` (`plans-seed.pdf`, `plans-typed.pdf`, their `pdftotext` pages, `plans-seed-analysis-5.png`
and `plans-typed-analysis-6.png` from `pdftoppm`).

## 4. Departures from the brief, with the reason

1. **Where the engine runs**: `job.price_assessment`, not the end of `generate_boq`. The brief's section 8 wants no new
   code path reaching `core/quick.py`; the estimate has no plan set, and the project is where the survey (`service`) and
   the cell's air maximum (`results.site`) are. The BOQ's lines and totals do not move either way.
2. **A row's status with a table the app does not hold**: the PV and battery cables have no 75 °C column and the battery no
   rack-EGC role; 2.5 says a blank table value prints "not checked", but 2.6's hand-worked PV and battery rows pass. The
   rule built: a figure the office can type that is missing (an item field, the panel's Isc) makes the row "not checked"
   with the item named; a table or role the app does not hold at all is a "verify" qualifier beside the pass. A pass still
   never stands alone: the brackets name every assumption and every unverified table.
3. **The 2017-style adder**: the NEC 2017 applies +33 °C only under 22 mm, so at the assumed 25 mm it would add nothing;
   the brief's failing case (+33 → 68 °C) is built as a single band "0: 33" the owner sets, which is what the Settings help
   says. 6.3's question to the PEE decides the table.
4. **`bundling_factor_pct` in percent** (100, 80, …) rather than the brief's `fill_factors` fractions: the generic size-table
   editor shows whole numbers; the engine divides by 100. The conduit fill limits likewise in percent, as the brief gives
   them. `rooftop_adder_c` is keyed by the band's lower height in mm.
5. **`insulation_c` is a number**, not the brief's text field: it picks the ampacity column and enters the formula.
6. **The next-size-up allowance** adds the condition that the derated ampacity still covers the continuous current
   (NEC 240.4(B) does not license a conductor below its load); the brief's case needs it neither way (24.2 A fails on the
   next size being 25, not 32). The battery breaker gets no next-size-up (no standard list in the settings for it), said
   in the warning.
7. **The sources are pure citations** and the flag carries the word: the sheet prints "{source}; verify" or "{source};
   confirmed in Settings" (the brief's "verify" on every table value). The bundled Montserrat has no ≤, ≥, √, ≙ or → glyph,
   so the sheet and the notes say "at or below", "sqrt" and ":"; the values are unchanged.
8. **Each AC circuit in its own raceway** with its grounding run for the fill (3 conductors), as 2.6's 10.7 % case
   assumes; the sheet says so and that the raceway is to be verified against the survey.
9. **The schedule's placeholders** for derating, conduit fill and the two grounding conductor sizes now read "the design
   analysis sheet" (four strings in `plans_pdf.py`), and the cover's note 6 likewise: the brief lists only the new sheet,
   but a set that says "to be completed" on one sheet and computes it on the next contradicts itself. The notes that stay
   "to be completed" (the mounting, the placards, the code references) are the later items'.
10. **The two sheet-count pins** (`test_plans.py`, `test_survey_fields.py`) move from five to six, and the survey test no
    longer asserts the DU's name is absent from the set (the short-circuit note prints it). The three parallel items will
    move the same pins again.
11. **The Pass cell of a "not checked" row** prints the reasons only (the checks that did compute show in their own
    columns, the assumptions in the conductor and ambient cells): with the brief's full qualifier list on every row the
    table outgrew the sheet on the seed record.
12. **Settings › Design analysis is its own page** (`shared.ts`), not a section under Materials and markup: eleven
    tables and flags beside the wiring rules would bury both; `SettingsPage.tsx` needed no change for it.
