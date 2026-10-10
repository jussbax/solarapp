# Round 13, step 1: the plan set's groundwork

Built 10 October 2026 from `engineer-brief.md`, section 7, item 1: the title block (item 6), the `pricing.choices.circuits`
contract (2.1) and the survey and site fields (1.3, 3.2, 4.2) in one schema change, so the office can start surveying
service entrances and roof construction while the sheets of items 1 to 5 are built. Nothing of the later steps: no sheet
changes beyond the title block, no derating engine, no 120 % rule, no wind fields, no map tools. Three commits on the
branch (the title block and the revision log; the circuits contract; the survey fields) and one for the documents. The
suite went from 248 to **272 tests**; `npm run build` passes and `npm run lint` stays at its seven baseline warnings.

## 1. The title block (brief 6.1 to 6.4)

- `profile.PROFILE_FIELDS` gains ten fields (`profile.PEE_KEYS` names the twelve of the signing engineer): `pee_prc_valid_until`,
  `pee_ptr_no`, `pee_ptr_date`, `pee_ptr_place`, `pee_tin`, `pee_address`, `pee_firm`, `pee_firm_address`, `pee_phone`,
  `pee_email`. Dates are text (as the PRC and PTR documents print them). `PUBLIC_KEYS` is unchanged, so none reaches the
  website. Settings › Company groups them under "Signing engineer" with the note that a blank prints as a blank line;
  the find box lists them under that block.
- The signature block (`plans_pdf._canvas_class`) on every sheet: "Signed and sealed by the Professional Electrical
  Engineer"; "{name}, PEE — PRC No. {no}, valid until {date}"; "PTR No. {no}, issued {date} at {place}"; "TIN {tin}";
  "{address} · {firm}"; "{firm's address} · {phone} · {email}"; "Signature ____ Date ____ Seal". Every blank field is
  `BLANK`. The last sheet's entry "Title sheet items beyond the signature block (PTR, TIN)" became "Signing engineer's
  details in the title block", naming the fields still blank and where to type them, and drops out when the profile
  holds them all.
- The project cell (6.2): "PV system plans: {customer}"; "Owner: {customer}"; the address; "Project {no} · {kind in
  words}"; the system line; "Date {today} · calculated {stamp}"; the revision line; the internal-set line.
- The revision log (6.3): `Assessment.plans_issued_at` and `Assessment.revisions` (a nullable JSON column; `db.ensure_columns`
  adds both to an older database at start-up, an older record reads "Rev. 0"). `GET /plans.pdf` sets `plans_issued_at` on
  the first build and never again; `POST /api/assessments/{id}/revisions` (`RevisionIn.note`, required) appends
  `{no, date, note, by}` with the signed-in person's display name, 409 before the first issue, 422 on a blank note;
  `AssessmentOut` carries both. The title block prints "Rev. {n}: {note} — {date}" for the latest entry, "Rev. 0: first
  issue — {date}" before any, "Rev. 0" when the builder is called without the stamp. The cover carries "Sheets in this
  set" (No. | Sheet, from `sheet_names`) and "Revisions" (Rev. | Date | Note | By: the first issue, then the last five
  entries). The Documents card shows the revision line under the plans row with "Issue a revision" (a prompt for the
  note); the page refreshes the record after the first plans download so the line appears.
- Tests (`test_plans_title_block.py`): the round trip and the public profile; the title block with `BLANK` then the full
  lines on every sheet, the owner and the kind, the last sheet's list; revision 0 on the first build and kept on the
  second, the 409 and the 422, "Rev. 1" on every sheet and in the cover's table, the append-only log through a second
  revision and "Reopen design"; the older-database migration. `test_plans.py`'s title-block assertions follow the new
  lines (departure 2 below). The set keeps its five sheets on the Pila record.

## 2. The circuits contract (brief 2.1)

`design_checks.circuits_block`, called at the end of `generate_boq` after `choices` is complete, reads `choices` and the
BOM lines and writes `choices["circuits"]`: seven records on every job, C1 to C7 in a fixed order. The runs the lines were
priced on join `choices` (`pv_run_m`, `ac_run_m`, `grounding_run_m`, `conduit_m`). The shape, with the sample job's C4
(8 × 585 W, 6 kW, 11.7 kWh, the seed alone):

```
{"id": "C4", "name": "Inverter output", "kind": "ac_inverter_output", "applies": true, "count": 1,
 "conductors": {"n_total": 2, "n_current_carrying": 2, "size_mm2": 8.0, "insulation_c": null, "type": "THHN"},
 "run_m": 15, "voltage_v": 230.0, "i_continuous_a": 26.087, "i_design_a": 32.609, "ocpd_a": 40.0, "ocpd_code": "IAN-PRT-027",
 "placement": "indoor_conduit", "conduit_code": "IAN-ENC-011", "conduit_inner_diameter_mm": null,
 "ambient_c": null, "rooftop_adder_c": null, "t_conductor_c": null,
 "ampacity_rule_a": 40.0, "ampacity_rule_column": "THHN 60 °C column (the wiring rules; verify the table edition)",
 "ampacity_base_a": null, "ampacity_terminal_a": null, "f_temp": null, "f_fill": null, "ampacity_derated_a": null,
 "fill_pct": null, "fill_limit_pct": null, "egc_required_mm2": null, "egc_provided_mm2": 8.0, "egc_provided_code": "IAN-WIR-004",
 "drop_pct": 0.00732,
 "checks": {"design_le_ocpd": true, "ampacity_ge_ocpd": true, "ocpd_le_derated": null, "terminal_ge_design": null, "next_size_up_used": null, "fill_ok": null, "egc_ok": null},
 "status": "not checked",
 "notes": ["line and neutral per circuit, both current-carrying; the ground is the grounding run (C7)",
           "current: the inverter's rated output over the AC voltage; design current 1.25 × it, the breaker the next standard size",
           "placement: in the BOM's conduit indoors (the rule's placement until the survey records the run); the conduit's inside diameter is not on the item",
           "EGC provided: the grounding run on the THHN line of the AC circuits (the BOM's conductor)",
           "derating (ambient, temperature and bundling factors), conduit fill and the EGC size are not computed yet: the design analysis is a later step"]}
```

Per row: C1 the PV string (two PV-wire conductors, the gauge and run, the string current and voltage, the drop; with Isc
on file `i_design_a` = 1.25 × 1.25 × Isc and `ocpd_a` the DC breaker the generator chose, else 1.25 × the rule's current
and the note that the breaker's rating is not checked; placement `rooftop_free_air`; the EGC provided is the array
bonding item's size read from its name, 10 mm² on the seed); C2 the strings joined on one MPPT input (`applies` only when
an input takes two or more strings; the worst input's current; no conductor or combiner role in the BOM, so the note
says to verify a fuse per string); C3 the battery (the lug pairs' gauge and table ampacity, I_inv, 1.25 × it, the breaker;
the battery's nominal voltage when on file, else the wiring rules' 51.2 V said so; no run, no drop, no rack EGC: the notes
say why); C4, C5, C6 the AC circuits (THHN, line and neutral, the breaker, the 60 °C figure, the drop, the EGC on the
same line; C5 notes whether the grid side is sized on the AC input rating or the output); C7 the equipment grounding
(the grounding run and gauge, the bonding item and the rod named). `status` is "not checked" until the design analysis
derates the row, "fail" where the BOQ's own coordination already fails (`design_le_ocpd`, `ampacity_ge_ocpd`); no row
reads "pass" on step 1. `types.ts` carries `CircuitRecord`; DECISIONS.md documents the shape.

Tests (`test_circuits_contract.py`): the sample job's seven rows with the BOQ's figures and its unchanged BOM; a
net-metering job's battery row does not apply and the numbers hold; a failed coordination reads "fail"; the Pila record
through the API, then with the datasheets and a 500 V input the PV row's 1.25 × 1.25 × Isc and the DC breaker; the size
reader. The BOQ, design-rule, string-design and quick-estimate suites are unchanged (the website estimate's pins hold).

## 3. The survey and site fields (brief 1.3, 3.2, 4.2)

One schema change (`schemas.py`), the API round trip, the screens, the tests:

- `AssessmentDoc.service: ServiceEntrance`: `du_name`, `account_no`, `meter_no`, `panelboard` (the existing panelboard in
  words), `phase` (1 | 3 | null), `voltage_v`, `main_breaker_a`, `busbar_a`, `interconnection` (`load_side_breaker` |
  `supply_side_tap` | `line_side_of_main` | blank), `interconnection_note`, `fault_level_ka` (2.3), `circuits` (5.3:
  `{no, description, breaker_a, poles, wire_mm2, conduit_mm}`). The Service entrance card on the Site step, after the
  map; the circuits as a fold with a small table.
- `RoofFace.construction: RoofConstruction` and `AssessmentDoc.roof_default`: `roof_type` (`rib_metal` | `corrugated_metal`
  | `tile_clay` | `tile_concrete` | `concrete_deck` | `other` | blank), `sheet_profile`, `purlin_material` (`steel_c` |
  `steel_tubular` | `wood` | `none` | blank), `purlin_section`, `purlin_thickness_mm`, `purlin_spacing_m`, `rafter_spacing_m`,
  `mean_roof_height_m`, `condition`, `condition_flag` (`sound` | `rusted` | `thin` | `old` | blank). A fold "Roof
  construction and position (for the plans)" under each face (a blank reads "same as the project") and "Roof construction
  for the whole project" under the Roof faces card. Per face `plan_offset_m: [east, north]` metres of the eave midpoint
  from the pin, in the same fold.
- `AssessmentDoc.site: SitePlan`: `lot_polygon`, `house_polygon` (lists of `[lat, lon]`; three corners or more, or none),
  `inverter_location` / `inverter_point`, `battery_location` / `battery_point`, `poi_location` / `poi_point`,
  `meter_location` / `meter_point`. The Site plan card: a location text and a latitude and longitude per point (saved
  when both are typed), the outlines as one "lat, lon" per line (saved when every line reads), labelled as typed
  coordinates for now.
- Every field is optional and blank until surveyed; no field has a default; the words are enumerations and a point is a
  pair in degrees (422 otherwise); a survey edit is an input (the results go stale). Nothing on a sheet reads the fields
  yet, so the PDF is unchanged beyond the title block; the quick estimate's document carries the blank defaults and no
  new code path reaches `core/quick.py`.
- Tests (`test_survey_fields.py`): the round trip of every block through POST, GET, PUT and Calculate; an older record
  reads every field blank; eleven invalid values are 422; the face offset; the plan set's five sheets and the quick
  estimate unchanged.

## Checks

The full suite (`272 passed`), `npm run build`, `npm run lint` (seven warnings, the baseline). The plans PDF of the Pila
sample with the profile filled, one revision issued, under `scratchpad/plans13/step1/` (`plans-rev0.pdf`,
`plans-rev1.pdf`, their `pdftotext` pages, `cover-1.png` from `pdftoppm`): the title block on all five sheets, the
cover's sheet index and revision table. The private server on port 8222 with the built frontend: `settings-company-*.png`,
`service-entrance-*.png`, `site-plan-*.png`, `roof-construction-*.png`, `documents-card-*.png` at 1280 (desk) and 390
(phone); no horizontal scroll at 390; the saved document read back through the API carries what was typed.

## Departures from the brief, with the reason

1. The signature block prints seven lines, not six: the firm's address, the phone and the email on a line of their own.
   6.1's heading says every profile field prints on every sheet, and its six lines leave those three unprinted.
2. `test_plans.py`'s three title-block assertions were reworded ("Name: Juan dela Cruz" → "Juan dela Cruz, PEE",
   "PRC No.: 0012345" → "PRC No. 0012345", "PTR No.: BLANK" → "PTR No. BLANK"): 6.4 says the existing assertions hold,
   but they pinned the old labels the six lines replace; their substance (the name, the PRC number, the blank PTR) holds.
3. Every job carries all seven circuit rows, with `applies` and `count` on each (not in the brief's shape): 2.6's test
   says the sample job carries seven rows although it has one string (no combined circuit) and 2.2 lists C2 "when
   strings join"; a fixed row set keeps the balloon numbers identical on every sheet, and `applies` says which the job has.
4. `ampacity_rule_a` and `ampacity_rule_column` carry the wiring rules' table figure the BOQ sized on (the THHN 60 °C
   column, the PV and battery cable tables); `ampacity_base_a` stays None. The brief's base is "at insulation_c", the
   90 °C columns of step 2; the 60 °C figure must not be called that. `egc_provided_code` is beside the size.
5. `insulation_c` is None, not 90: the brief ties 90 to a new item field with a note (step 2); nothing is defaulted
   silently here. `placement` follows the brief's rules (the string runs in free air, the AC circuits in the BOM's conduit
   indoors) and the battery cables indoors free; each row's note says it is the rule's placement until the survey records
   the run.
6. `checks` gained `design_le_ocpd` and `ampacity_ge_ocpd`, the BOQ's rules 2.3 lists among the checks, computed now;
   a row whose coordination fails reads "fail" (the generator's hard warning already blocks).
7. The service block carries `panelboard` (text), `fault_level_ka` (2.3) and `circuits` (5.3) beyond 1.3's list: they are
   the same survey record, and the task asked for one schema change.
8. The 120 % rule and `poi_busbar` are not built: 7.1 puts the fields in step 1 and the check with the single-line
   diagram that prints it (item 1).
9. `plan_rotation_lock` is not added (4.2 says "(none)"); `doc.wind` and `roof_default.fastener_pullout_kn` are item 3's.
10. A revision cannot be issued before the first plans build (409): revision 0 is the first issue, and a log that starts
    at 1 with no 0 would misnumber the set. "Reopen design" leaves `plans_issued_at` as well as the log (6.3 names only
    the log): clearing the stamp would make the next download "Rev. 0" again under an append-only log.
11. The cover's "By" is blank on the Rev. 0 row: the API does not record who first generated the set.
12. The per-face fold is a second fold under each face ("Roof construction and position") rather than the fields in the
    face grid, so the Roof faces step stays one line per face until the fold opens; the project default sits under the
    Roof faces card. The Site plan's outlines are textareas of corners (the brief's "typed coordinates for now").
