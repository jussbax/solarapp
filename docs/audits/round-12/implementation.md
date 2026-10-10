# Round 12, implementation: the datasheets in the app

Built 10 October 2026 from `engineer-brief.md`, steps 1 to 4 of its order of work (section 7); step 5 waits on the
owner's answers to section 6. Four commits on the branch, one per step. The suite went from 212 to 246 tests;
`npm run build` passes and `npm run lint` stays at its seven baseline warnings. Nothing on a sheet was corrected;
every default is labelled an assumption in the code, in the warning a job carries and in the settings' help.

## Step 1: the fields, the specs table, the importer, the fixture, the tests

- The eleven item fields of section 1 on `Item` (`pricing/catalog.py`), `ELECTRICAL_FIELDS` (so `KEEP_WHEN_BLANK`
  protects them on a materials re-import), `ELECTRICAL_HEADERS` (the materials workbook may carry the same
  columns), `MaterialItem` (`models.py`; `ensure_material_columns` adds them to an older database at start-up),
  `MaterialItemIn` / `MaterialItemPatch`, `types.ts` and the Materials page editor: `max_system_voltage_v`,
  `inverter_type`, `phase`, `battery_class`, `charge_v_max`, `charge_a_max`, `mppt_currents_a`, `battery_inputs`,
  `nominal_v`, `capacity_ah`, `discharge_a_recommended`. `is_hybrid_inverter` reads the type first (1.4) and falls
  back to the name; `select_inverter` also keeps a unit with phase 3 or an HV battery port off residential jobs.
- The `datasheet_specs` table (`models.DatasheetSpec`): one row per sheet row, never deleted, with the brief's
  columns plus `held_fields` (the figures held back, beside the `held` flag).
- `pricing/datasheets.py`: `python -m solarapp.pricing.datasheets <files…> [--dry-run] [--report out.csv]
  [--apply-held]`, and the owner-only `POST /api/pricing/datasheets` (one workbook per call; the page loops),
  `GET /api/pricing/datasheets?category=`, `POST /api/pricing/datasheets/{id}/link`, `POST
  /api/pricing/datasheets/{id}/add-item`. The sheet kind is read from the header words of each sheet; the header
  row is found by its words; the column map comes from the sheet's own names plus the materials importer's alias
  table (so the columns the owner may add later, 6.5 and 6.6, are read already); battery sheet 3's maker
  sub-headers reset the map and inherit the columns they leave blank. Every irregular cell of 1.5 is parsed by its
  rule and flagged (`test_datasheets_parse.py`, one case per rule). The three tiers of 2.2 (exact, contains,
  base) with the brand as the tie-breaker and the category agreement (`test_datasheets_match.py`). The precedence
  of 2.4: the datasheet overwrites the numeric and text fields unless the owner typed over them
  (`overridden_fields`, kept by `PUT /api/pricing/items/{code}`; typing the sheet's own figure back lifts it), the
  grid flag fills only when the item's is None and a disagreement is reported, the rating fills only when blank
  with a notice on a difference. The re-apply at the end of every materials import (2.6) with a re-match over the
  rows without an item. Re-runnable: the same file twice changes nothing; a row missing from a later file keeps
  its specs row with a notice. The report prints one line per row in the brief's form and the summary counts
  (rows read, matched, specs-only, skipped, held, items changed, items untouched, priced projects that use a
  changed item); `--report` writes the CSV; `--dry-run` rolls back. The stamps `datasheets_imported_from` and
  `datasheets_imported_at` sit on the pricing config outside the settings version.
- The fixture: `backend/tests/fixtures/datasheets/` with its README (the three workbooks cut from the owner's
  files: the panel and battery sheets verbatim, the plain 3P grid-tie rows dropped from the Deye and Solis
  sheets; every irregular cell and every layout kept).

## Step 2: the settings block and the two TMY figures

`PricingConfig.string_design` (`config.StringDesign`): `design_cold_c` 14, `cold_margin_c` 5,
`design_hot_cell_c` 70, `temp_coeff_voc_default_pct` −0.30, `temp_coeff_pmax_default_pct` −0.35,
`temp_coeff_isc_default_pct` +0.05, `isc_irradiance_factor` 1.25, `dc_breaker_sizes_a` 16…63, each with the
brief's reason as a comment and "assumption" / "verify" in the META help, every one in `settings_version`; plus
`roles.dc_breaker_pattern` ("DC BREAKER") for 3.2. Per project (`PricingJob.design_cold_c`,
`design_hot_cell_c`, under the pricing inputs' adjust fold): `compute.py` puts in `results["site"]` the cell's
typical-year air extremes, the module's rise at 1 kW/m² (the site's measured rise when plausible, else the Faiman
model at the year's mean wind) and T_cold = min(setting, floor(TMY min) − margin), T_hot = max(setting, TMY max +
rise); `job.py` hands them to the BOQ; the System design step prints the line "TMY extremes at this project's
cell". The website estimate has no project and uses the settings alone.

## Step 3: the checks in the generator

`pricing/design_checks.py` (plain functions) called from `generate_boq`, in the brief's order, each falling back
to today's behaviour when a figure is absent and saying so; hand-worked tests in `test_battery_match.py` and
`test_string_design.py` on the brief's figures:

- 3.5 the battery circuit: I_inv = max(battery_max_a, charge_a_max); the eco-hybrid 139 A → breaker minimum
  173.75 A, the same 250 A breaker and 70 mm² pair; FS-INV-002 max(174, 190) = 190; the kW fallback over the
  chosen battery's `nominal_v` when on file; the soft `battery_discharge_recommended` (the 230 Ah IP65 row's 115 A
  against 139 A); `battery_inputs_verify` on a two-input port. The hard bank check is unchanged and reads
  `continuous_a`, now the sheet's maximum.
- 3.7 the voltage match: `battery_voltage_class` (hard, blocks; the 25.6 V pack on a 48 V port, an LV pack on an
  HV port) and `battery_charge_voltage` (60 V against a 57.6 V ceiling warns; 58.4 V against 60 V does not).
- 3.6 the charge check: `battery_charge_current` (135 A against 60 A: set 60 A, three units for the full rate).
- 3.8 Ah against kWh: `battery_ah_kwh` above 2 % (25.6 × 120 passes at 0.07 %; 51.2 × 100 against 6 kWh warns at
  14.7 %); the import raises the same notice.
- 3.1 the strings: the 630 W panel's 48.90 V → 50.51 V at 14 °C and nine per string on a 500 V input (505.1 V for
  the fixed ten), eight on the 630 W bifacial, nine on the 585 W monofacial, 50.22 V at 16 °C; Vmp_hot 34.29 V at
  70 °C; n_min from a window given in the test; `string_voltage_cold` (hard, blocks, only on a strings override),
  `string_voltage_hot`, `string_rule_fallback`, `temp_coeff_default`.
- 3.2 and 3.3: I_string = Imp (15.48 A), V_string = per_string × Vmp (366.3 V for nine), I_design = 1.25 × Isc =
  20.23 A, I_cond = 25.28 A (1.5625 × Isc) → 4 mm² holds, the OCPD 32 A; the 720 W panel 32 A, the 630 W bifacial
  25 A; the DC breaker by rating with `dc_breaker_rating` when the role item is too small (the 16/25 A role item
  gives way to the 32 A one for the 630 W panel; the 585 W panel keeps it).
- 3.4 the MPPT inputs: 2 × 15.48 A = 30.96 A on an 18 A input warns, on a 36 A input not; the DC SPD count reads
  the Deye MPPT counts the remarks never gave.
- `choices` gains `string_design` (the plan with the coefficients' `default` flags, `per_mppt`, the current block),
  `dc_breaker`, `battery_current_source` and `battery_current_basis`, `battery_charge`, `battery_voltage_match`,
  `battery_ah_kwh`; the BOM notes say "datasheet" or "the rule's". The 10 × 630 W job on a 500 V inverter goes
  from one string to two (+1 DC breaker, +2 MC4 pairs, +25 m red and black).
- 4.5: the quick estimate is untouched; `test_the_quick_estimate_price_with_and_without_the_datasheets` pins
  ₱314,000 with the seed alone and states ₱326,000 with the fixture loaded (after the review's battery ranking the
  choice moves to the 15 kWh unit whose recommended rate covers the 139 A; as first built it was ₱287,000 on the JK
  pack's maximum alone; the string count does not move, the default inverter having no maximum PV voltage).

## Step 4: the plan set, the Materials page, the Settings section

- `reports/plans_pdf.py` (4.2): the cover's models table prints the panel's maximum system voltage, the
  inverter's type and phase, battery-port class, charge voltage, discharge and charge currents and per-input MPPT
  currents, the battery's voltage, Ah, kWh, maximum, recommended and charge currents, ceiling and class, each
  block saying "datasheet (file, date)" or staying BLANK; the Strings row and general note 4 say "string design on
  datasheet figures from {file}, {date}" with n_max and T_cold; the schedule's DC rows print Imp and Vmp from the
  datasheet with T_cold, T_hot and the coefficients ("default, an assumption" where one is), the two Isc lines
  (1.25 × Isc, and 1.25 × that = 1.5625 × Isc for the conductor and the OCPD), the DC breaker's rating check, a
  string table (per string its count, Voc at T_cold, Vmp at T_hot, the limit, the margin in volts and percent,
  the MPPT low end, the input it sits on and its current), and the battery circuit on "the larger of discharge and
  charge" with the charge setting (3.6) and the voltage match (3.7); the last sheet drops the string-table entry
  when the figures are on file and the single-line entry names only what is still missing (the panel's maximum
  system voltage and the inverter's window added). `test_plans_datasheets.py` pins it; `test_plans.py` is
  unchanged for the set without the figures.
- The Materials page (2.5): a provenance badge in the Electrical column (datasheet with the file and date on hover,
  typed, remarks, none), the held note on held rows, the datasheet's figure under a field the owner typed over
  with "reset to datasheet", the datasheet's notices in the editor, the eleven fields in the editor, a Datasheets
  card with, per category, "datasheet rows without a priced item (N)" (brand, model, the key figures, the
  notices, "Link to item…", "Add as item": an inactive item at list price 0) and "items without a datasheet (N)",
  and an "Import datasheet workbooks" block (several files, the apply-held tick, a dry run, the report's lines).
- Settings (5.2): Pricing settings › Materials and markup › String design with the nine settings and their help;
  the "TMY extremes at this project's cell" line on the System design step.
- `DECISIONS.md` "The datasheets in the app"; `README.md`'s materials paragraph, the import command and the layout
  lines.

## The importer's report on the owner's three workbooks

`scratchpad/datasheets/import-report.txt` (and `.csv`), run on a scratch database seeded from the bundled
workbook: **rows read 210, matched 113 (6 of them held), specs-only 90, skipped 7, items changed 113**.

- Matched: all 14 panel rows (the seven maker-prefixed rows on the maker in the text; rows 10–12 by the contains
  tier, the rest exact); the 25 Deye rows (4 grid-tie 1P, 9 grid-tie 3P, 6 hybrid 1P with their MPPT figures, 6
  hybrid 3P); the 35 Solis rows (the ESS set to IAN-AIO-001, the 5 grid-tie 1P held, 16 grid-tie 3P, 6 hybrid 1P,
  7 hybrid 3P); the 6 One Solar off-grid rows; BC-INV-001 and BC-INV-004; FS-INV-005 and FS-INV-006 (contains,
  with the suffix notice), FS-INV-008 (`battery_max_a 135 -> 139`, `charge_v_max - -> 58.4`, `charge_a_max - ->
  135`, `inverter_type - -> off_grid`, `phase - -> 1`, `battery_class - -> LV`; `grid_interactive kept (item yes,
  sheet off-grid)`), FS-INV-002 (`battery_max_a 190 -> 174`, the charge figure 190 beside it: the circuit runs on
  190); the batteries BC-BAT-001, BC-BAT-002 (base), FS-BAT-001 (held: the 150 A maximum above 1 C), FS-BAT-002
  (`continuous_a 120 -> 150`, the 10 vs 10.24 kWh notice), FS-BAT-003 and FS-BAT-004 (the TG2 rows, the longer of
  two), FS-BAT-005 and FS-BAT-007 (base), the 7 One Point and 8 IAN battery rows that are verbatim; the 21 battery
  items without a continuous current take the sheet's maximum.
- Specs-only (90): 76 rows no item names (the Blue Carbon series the price list does not carry, the Felicity
  variants, the 3P hybrids and charge controllers); the 9 One Solar charge-controller rows naming OP-INV-001..003
  (6.7); the Blue Carbon base 6.5 kW row (`ambiguous: BC-INV-004, BC-INV-005`); the two 230 Ah rows FS-BAT-006 is
  the base of; the FLA48300 and FLA48500 rows (their items take the longer TG2 models). The items the brief lists
  as unmatched stay unmatched (FS-INV-001, -003, -004, -007, IAN-INV-035, BC-INV-002, -003, -005, -006, -007,
  -008, BC-BAT-003, -004, FS-BAT-006, -008, -009, IAN-BAT-002, -004, -006, OP-BAT-003, OP-INV-001..003).
- Skipped (7): the Solis orphan rows 47–53, "no model in the model column".
- Held (6): the Solis grid-tie 1P rows 5–9 (type and phase applied; the three battery figures on the specs row)
  and the Felicity 100 Ah base row (FS-BAT-001 keeps 100 A).
- A second run changes nothing (items changed 0). The notices the brief lists in 1.5 and 6.8 all appear on their
  rows (the 60 V ceiling on the 25.6 V pack, the recommended above the maximum on twelve Blue Carbon rows, the
  HV-typed 51.2 V row, the 2.2× ceiling, the "(21A)", the 230/380/720 V dash figures, the kW figures in the
  Felicity amps column, the asterisks, the "Verify").

## Departures from the brief, with the reason

- `battery_inputs` is stored blank for "one" (the brief: int, default 1): a materials re-import writes every
  electrical field its row produces, and a stored 1 would overwrite the sheet's 2 until the re-apply ran.
- The exact tier requires a boundary before the model as well as after (the brief names the character after
  only): without it "BCT-V-48-100" occurs whole at the tail of "SMART-BCT-V-48-100" and the plain row would take
  the smart item, which the brief says must not happen.
- The exact tier reads an item name's slash alternatives once each ("40A ONE MPPT - 12/24/48V" as three names), and
  exact rows of equal length claiming one item leave it unmatched with the notice: the only way the three One Solar
  rows can name OP-INV-001 (6.7) under the brief's "longer model wins" rule.
- The battery sheet kind is also recognised by MAX DISCHARGE CURRENT: battery sheet 3's header (MODEL and Max
  Charge Voltage, no Capacity or BATTERY TYPE) would read as an inverter sheet under the brief's words alone.
- The specs row's upsert key carries the model as typed beside the normalised one: "BCT-FXC-1.2KW" and
  "BCT-FXC-12KW" normalise alike and are two units.
- The held figures live in a `held_fields` column beside the `held` flag (not in the brief's column list), so the
  page and `--apply-held` can show and apply exactly them; the battery class derived from a held charge voltage is
  held with the three figures.
- `--apply-held` applies both held kinds (the Solis grid-tie figures and a battery maximum above 1 C): the brief
  ties the second to "the owner's confirmation" without naming a switch, and one switch on the owner's word is
  simpler than two. The review added the per-row apply beside it (finding 5; Review fixes below).
- The DC breaker: when the panel's Isc is on file and the role item's rating is below 1.5625 × Isc, the smallest
  "DC BREAKER" item that covers it is used and the warning says so (the brief's "pick `_by_amps` … and warn" read
  as substitute and warn); the pattern is a new setting, `roles.dc_breaker_pattern`, as the battery breaker's is.
  When the role item covers it, it stays (so the 585 W panel's job does not move to a cheaper brand).
- The Pmax coefficient is always the settings' default: no item field holds one (the brief's 6.5 counts it outside
  the eleven); the string design's `coefficients.pmax.default` is True and the plans say "default, an assumption".
- 3.5's I_cable is not computed as a separate figure: as the brief notes, in a passing design it equals I_inv and
  the cable is still sized from the breaker.
- The schedule sheet's two columns are balanced by measured height and, when the string table and the battery rows
  cannot fit one A3 beside the rest, the schedule takes a second sheet ("Equipment and circuit schedule
  (continued)", named on the cover); the set without the figures keeps its five sheets. The two Isc lines share one
  row (two lines in one cell) and the equipment rows print the figures without the file and date, which the cover
  carries.
- Observed in step 4 (outside the brief) and fixed in the review round: the AC side's BOM note formatted the breaker
  size without a guard, so a unit whose output current exceeds the largest standard AC size (an 80 kW 3P unit picked
  per job) raised a TypeError after its hard warning; it now prints "above the largest standard size".

## What is left for step 5

The owner's answers to section 6, then: apply the held rows (`--apply-held`, or per row); correct the brand column
on the panel sheet (the importer stores both and matches on the maker in the text meanwhile); the four inverter
columns (maximum PV voltage, MPPT min and max, Isc per MPPT) and the panel columns (the Voc coefficient, a Pmax
coefficient as a new field `temp_coeff_pmax_pct`, the maximum series fuse rating as a new field) — the alias
table reads the first three already; the One Solar charge-controller decision (one unit or three codes); the
Felicity 3P rows' kW figures; the cells that do not add up (6.8); and the two decisions of 6.9 (the wall-type
units in the off-grid pool; a grid-tie unit on a net-metering job). Once the default inverter carries a maximum PV
voltage the string check runs on every residential job and the plans print the string table on the owner's own
figures.

## Review fixes

The engineer's review (`engineer-review.md`, 10 October 2026): verdict "merge with the fixes listed", every
hand-worked figure confirmed, every departure accepted but the AC-note TypeError. Fixed on the branch in two commits
(the code and its tests; the documents), the full suite (248 tests), `npm run build` and `npm run lint` (the seven
baseline warnings) run before them.

- Finding 1 (must fix): `apply_spec` leaves the grid flag unknown when the item's remark carries the
  check-certification pattern `catalog.infer_grid_interactive` answers None for, with the note "grid flag left
  unknown: the item's remark says to check the certification" on the report line and the row. FS-INV-002 stays
  unknown; IAN-INV-022 (no such remark) takes the sheet's yes. Test in
  `test_the_figures_on_the_items_and_the_precedence`.
- Finding 2 (must fix): `DatasheetSpec.held_applied_at` (added to an older database at start-up by
  `ensure_columns`). Set by `--apply-held` and the upload's tick on every held row, by the per-row apply on one; kept
  through the upsert (a re-run never clears it; a row that stops holding figures does); honoured by `apply_spec`
  (`apply_held = apply_held or bool(spec.held_applied_at)`), so the re-apply after a materials import and a plain
  re-run keep the figure. The report line reads `matched CODE <- … (exact; held figures applied on <date>)` and the
  summary's held count leaves out the applied rows; the page says "held figures applied on <date> on the owner's
  word" and the editor's "held: X (not applied)" hint goes; a held figure the owner applied reads "datasheet" in the
  provenance. "Withdraw" (`POST /api/pricing/datasheets/{id}/withdraw-held`) clears it and returns each held figure
  still on the item to the remark's figure or blank. Test: `--apply-held`, then `import_workbook`, then a plain
  re-run: FS-BAT-001 keeps 150 A and reports `matched`; withdrawn, it is 100 A and `held` again; one Solis row
  applied alone keeps its 208 A through a materials import.
- Finding 3 (the coordinator's call): `select_battery` ranks `(hard rank, recommended rank, cost, units)`, the
  recommended rank 0 when units × `discharge_a_recommended` cover the current, 1 when the figure is unknown, 2 when
  it falls short; the maximum alone never promotes a pack. The figures: the sample job (BC-PNL-004 × 8, 6 kW,
  11.7 kWh) is FS-BAT-006 × 1 with the seed alone (unchanged) and FS-BAT-003 × 1 with the datasheets (150 A
  recommended ≥ 139 A, `recommended_ok` true, no `battery_discharge_recommended` warning), not the JK OP-BAT-007 the
  review saw; the website estimate is ₱314,000 with the seed (unchanged) and ₱326,000 with the datasheets (the review
  saw ₱287,000 on the JK pack's maximum alone; the battery goes from 10.24 to 15 kWh). `QUICK_PRICE_WITH_DATASHEETS`
  is 326000; the options list carries `recommended_ok`. Test
  `test_the_automatic_battery_choice_ranks_the_recommended_rate_before_cost`.
- Finding 4: `battery_class_mismatch(battery, inverter)` in `boq.py`; `select_battery` takes the inverter and skips a
  candidate whose class is known and differs from the port's (the fine 12/24/48/HV class from the voltages when both
  are on file, else the coarse LV/HV from the typed class). On the 80 kW HV unit the LV packs are gone and the Deye
  HV packs offered; on the eco-hybrid no HV pack. A per-job pick keeps the hard warning. Test
  `test_a_pack_of_another_class_than_the_port_is_never_offered`.
- Finding 5: `POST /api/pricing/datasheets/{id}/apply-held` and `…/withdraw-held` (owner only); the Materials page
  lists the held rows per category with the held figures, the state (held, or applied on a date) and the two buttons.
- Finding 6 (must fix): `_size_txt` in `boq.py` prints "above the largest standard size" where no standard breaker
  covers the current; the 80 kW unit picked per job gives the hard `ac_circuit` warning and a priced BOM.
- Finding 7: `battery_inputs_verify` prints "(X A each)" only when the figure is on file.
- Finding 8: the last sheet's labels lose their article ("the panel's temperature coefficient of Voc; the
  inverter's MPPT window (low), MPPT window (high)").
- Finding 9: `inverter_type` and `battery_class` are `Literal` enumerations on `MaterialItemIn` and
  `MaterialItemPatch` (the values of the page's selects); another word is a 422.
- Finding 10: the page's provenance compares the grid flag and the certificate against `infer_grid_interactive` and
  `certifications_in_remarks`, so a flag read from the name says "remarks".
- Finding 11: `add_item_from_spec` takes the maker as the supplier only when a `MaterialSupplier` of that name
  exists (case-insensitive: "BLUE CARBON" is Blue Carbon), else blank; the page's "Add as item" gained a supplier
  select and its message says when the supplier is still to be typed.
- Finding 12: the dead `taken` comprehension is a `taken.pop(...)` before the code is cleared; the README's layout
  line reads "the owner's three datasheet workbooks as received, for the importer and the fixture".
- The importer on the owner's three workbooks on a fresh scratch database after the fixes: the same counts (210 rows,
  113 matched including 6 held, 90 specs-only, 7 skipped), FS-INV-002's line carrying the new note; after
  `--apply-held` a plain re-run reports the six as matched with "held figures applied on 2026-10-10" and no change.
