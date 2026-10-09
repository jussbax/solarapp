# Engineering audit, round 3 (agent "engineering")

Reviewer stance: the PEE who has to sign these plans, build from these quantities and file the net-metering application with the DU. Read-only on the repository. Paths are under `backend/solarapp/` unless they start with `frontend/`. "verify" marks a code edition, DU rule or datasheet fact I do not have; no number below is invented.

## 0. What I ran

- Private app on 127.0.0.1:8040 (`solarapp.main:app`), public process on 8041, database, scripts, results, documents and screenshots in `scratchpad/agents3/engineering/` (`make_cases.py`, `results_{hybrid_1,netmeter_2,offgrid_3}.json`, `{hybrid,netmeter,offgrid}_{roof-check,proposal,program}.pdf/.txt`, `*_bom.csv/.xlsx`, `*_card.png`, `pg_*.png` page renders, `ui_*.png` browser captures, `shots.js`). Seed workbook imported on first start: 362 items, 4 suppliers. Real PVGIS 5.3 ERA5 TMY; Pila pin uses cell 14.25_121.25 at 13.4 km, Santo Tomas pin uses cell 14.0_121.25 at 16.8 km (elevation 556 m).
- Case 1, project 1 (hybrid, `combination`): Reyes residence, Brgy. Labuin, Pila. Hip-roof main house: south trapezoid 11 m eave × 4.2 m slope, 5 m ridge, 22°; east and west triangles 7 × 4.2 m at 22° (neighbour's two-storey house at 95°/22°, mango tree at 260°/30°); kitchen gable 6 × 3.6 m at 18° facing SE (1 panel left out) and NW (1.2 m wall on the left edge, 0.4 m gap). Candidates BC-PNL-001 585 W and BC-PNL-003 600 W. Two reading sets, 7 Oct 11:20 and 11:40, clear, 32 °C: south 905/915/898 W/m², 35.8/36.2/35.5 W, 56-57 °C; SE 860/870/855 W/m², 33.9/34.3/33.6 W. Sixteen appliances (fridge, 1.5 HP inverter aircon, 1 HP window aircon in the hot months, TV, 14 LED, rice cooker, 4 fans, washer, router, 2 laptops, 0.75 HP pump, iron, kettle, 3.5 kW shower heater, microwave, a future desktop). Bills Sep 2026 380 kWh / ₱4,750 and Aug 395 kWh / ₱4,900 (DU for Pila: verify). Signing 20 Oct 2026, company defaults everywhere else.
- Case 2, project 2 (`net_metering`, no battery): Villanueva residence, Brgy. San Antonio, Santo Tomas, Batangas. Gable 12 × 5 m at 18°, faces 200° (0.8 m wall on the right edge) and 20° (coconut trees 30°/28°). One reading set 940/950/930 W/m². Seventeen appliances with three inverter aircons, a chest freezer, a 4.5 kW shower heater, a dispenser; bill 700 kWh / ₱8,400 (BATELEC II, verify).
- Case 3, project 3: case 1 as the owner's "off-grid" (no export, grid as backup).
- Backend tests: 155 pass in 53 s (README.md:353 still says "96 tests"). Website estimate run through 8041 for both towns (Pila 380 kWh evening: 6 panels, 11.78 kWh battery, ₱291,000; Santo Tomas 700 kWh: 10 panels, ₱208,000).

Headline numbers the app produced:

| | Hybrid (1) | Net metering (2) | Off-grid variant (3) |
|---|---|---|---|
| k_raw → k_site, rise | 0.791 → 0.921, 26.9 °C/kW | 0.788 → 0.931, 27.7 | as 1 |
| Roof holds | 16 × 585 W = 9.36 kWp, 14,408 kWh at the panels, 13,017 at the meter (×0.903) | 27 panels, 15.79 kWp, 21,371 kWh at the meter | as 1 |
| Audit | 5,424 kWh/yr (typed 40 % above the two bills, uncertain loads ×0.37), peak 4.79 kW at 06:00 | 8,517 kWh/yr (typed 71 % above, ×0.17), peak 6.31 kW at 20:00 | as 1 |
| Sized | 7 panels 4.09 kWp (3 SE + 4 S), 5,979 kWh at the meter, coverage 93 %, battery 11.5 usable / 13.6 nominal, 6 kW, grid steps in 575 h on 114 days (391 kWh) | 11 panels 6.43 kWp on the SSW face, 9,133 kWh, self-consumption 29 %, export 6,484 kWh, sizing says 8 kW | 11 panels 6.43 kWp (3 SE + 7 S + 1 E), battery 13.5 nominal, 245 h on 56 days without the battery, 3,768 kWh curtailed |
| BOM | FS-INV-008 6 kW, BC-BAT-004 15.36 kWh, 1 string of 7, 4 mm², 8.0 mm² THHN 35 m, 63 A ×4, 250 A battery breaker | **2 × FS-INV-008 in parallel**, 2 strings of 6/5, 2 ATS, 8 breakers, 8 SPDs, 4 enclosures | FS-INV-008, BC-BAT-004, 2 strings |
| Contract | ₱312,100 (₱76/Wp) | ₱273,600 (₱43/Wp) | ₱347,500 |
| Economics | bill ₱5,650 → ₱271, payback 4.7 y, IRR 21 % | ₱8,400 → ₱2,355, payback 3.6 y, IRR 29 % | payback 5.2 y |
| Program | plans 20-22 Oct, permit 29 Oct, pickup 29 Oct, install and switch-on 30 Oct (crew of 6, roof done 07:57), CFEI 4 Nov, agreement 20 Nov, meter 5 Dec; lowest cash −₱50,804 on 29 Oct | same dates, crew of 4; −₱42,296 | late finish 14:25 |

## 1. Findings, ranked

Severity: Critical = a customer is sold the wrong hardware or a PEE/DU inspector rejects the job; Major = fails at commissioning or costs the owner money on every job; Medium = engineering is incomplete and the crew improvises; Minor = a slip on paper.

| # | Finding | Tags | Sev | Effort |
|---|---|---|---|---|
| E-01 | Net-metering (no battery) inverter sized on the house peak load, so a 6.43 kWp array gets 2 × 6 kW eco-hybrids in parallel and every AC item is doubled | engineering, bug | Critical | S-M |
| E-02 | Still no string design, and strings are now formed by count across faces: one series string mixes SE and S panels (and S with E in the off-grid variant); MPPT count and PV voltage limits unused | engineering | Critical | M-L |
| E-03 | Battery circuit: cheapest-kWh battery at 100 A for a 117-135 A inverter, then a 250 A breaker on 35 mm² cable the app itself rates 170 A; the warnings fire but every document prints | engineering, bug | Major | S |
| E-04 | AC side unchanged from round 2: 63 A breakers on 40 A wire, no grid-side (pass-through) current, 15 m of THHN for three 2-wire circuits | engineering | Major | S-M |
| E-05 | Grid-interactive flag without a certificate: FS-INV-008 is "yes" with nothing on file, so no warning and no certificate line on a net-metering proposal that promises the DU filing | engineering | Major | S |
| E-06 | BOM omissions an inspector asks for: array bonding, L-foot fasteners, placards, visible AC disconnect, export limiter for the five weeks before the two-way meter, monitoring; over-counts: 4 SPDs per board, 2 enclosures per inverter, ATS on a hybrid with its own transfer | engineering | Major | M |
| E-07 | Mounting and structure unchanged: no roof construction record, L-feet at 1.2 m regardless of purlins, no uplift or dead-load check; the proposal promises sealed fasteners into the framing on every roof | engineering | Major | M (L for uplift) |
| E-08 | The plan drawing is a customer picture, not an installation drawing: no dimensions, rails, feet, string labels, assembled roof plan, north arrow, equipment locations or scale ratio | engineering | Medium | M |
| E-09 | Cable, conduit and tray are fixed allowances; no inverter location or route length in the survey record | engineering | Medium | S-M |
| E-10 | Program: NM application starts before the sealed plans it needs, meter date ignores the CFEI, no DIS, no procurement lead time, no final site check, no export-limit task; roof factor 0.75 on a hip roof gives 7 panels on two faces in 72 minutes | engineering, pm | Medium | S-M |
| E-11 | Economics and cashflow carry-overs: monthly credit floor, no fixed charges, full output VAT 30 days after completion, 5 % agent commission on every job | engineering, finance | Medium | S |
| E-12 | Paper slips: card ratio uses the at-panels figure, "1 panels", "1 of your panel here", net-metering sentences on the off-grid proposal, 14 kWh vs 15.4 kWh on one screen, orphan page, README test count | engineering, copy, bug | Minor | S |
| E-13 | Inverter continuous requirement from the duty-weighted hour table; site k from the best set applied to every face | engineering | Minor | S |
| E-14 | BOM export has no spec/model, grouping, pack rounding, weight or header | engineering | Minor | S |
| E-15 | Hand-off: the visitor's typed kWh and pesos become the "latest bill" that sets the tariff, with no marker; old records may still carry source and contact | crm | Minor | S |

### E-01. Net-metering inverter rule and the parallel default [engineering] [bug] Critical

Where: `core/sizing.py:449-456` (`required = max(peak_load_kw, surge_req, pv_req)` for every kind, `binding = "peak load"`), `pricing/boq.py:220-222` (`units = max(units, ceil(required / inverter.rating))`), `pricing/job.py:141` (passes `required_kw`), `config.py:243` (`default_inverter_code_grid = "FS-INV-008"`, 6 kW).
What: project 2 is a net-metering job with no battery. The audit's peak (shower heater 4.5 kW plus the living-room aircon at 20:00) is 6.31 kW, so the sizing asks for 6.3 kW, picks 8 kW from the size list, and the BOM, bound to the 6 kW default, prices **two FS-INV-008 in parallel (12 kW)** for a 6.43 kWp array (DC/AC 0.54). With them come 2 ATS, 8 AC breakers, 8 AC SPDs, 4 enclosures, 2 DC SPDs and 70 m of THHN. The proposal prints "Inverter: 2 × 6 kW hybrid inverter (12 kW in all)" and "Hybrid inverter: 2 × 6 kW (Felicity Solar) PHP 58,994", "Breakers and surge protection PHP 16,832", "Electrical boxes and conduit PHP 18,947".
Why: with no battery there is no backup mode; the grid carries the house peak and the inverter only has to carry the array. The customer pays about ₱31,000 more for inverters and about ₱20,000 more in doubled balance of system than one 6 or 8 kW unit needs (FS-INV-002 8 kW ₱63,000, OP-INV-020 Deye 8 kW hybrid ₱58,000, or, if the owner ever allows a plain grid-tie on a no-battery job, OP-INV-004 Deye 8 kW grid-tie ₱28,000; `catalog.py:51-53` excludes grid-tie units from every selection). Two parallel units of a "pilot production" model (its own remark) is also a parallel-operation question for the maker (verify). A 5 % overshoot (6.31 over 6.0) doubling the inverter is the kind of thing a competitor's quote exposes.
Fix: for `kind == "net_metering"` the requirement is the PV rule (`pv_req`) plus a pass-through check of the house peak against the inverter's AC input/bypass current when the item carries `ac_input_a`; for the battery kinds keep the peak rule but let the owner mark which loads are backed up (the 3.5-4.5 kW shower heaters are what drive these peaks). In the BOM, before doubling the default, try the next rating of the same brand or the cheapest grid-interactive unit at or above the requirement, and warn when parallel units are chosen on an overshoot under a settable tolerance. Effort S-M.

### E-02. String design: still absent, and strings now cross faces [engineering] Critical

Where: `pricing/boq.py:279-283` (`strings = ceil(count / 10)`, `per_string = ceil(count / strings)`, `v_string = per_string × 42`, `i_string = Wp / 42`), `config.py:194` (`panel_vmp_v = 42`), `config.py:239` (`max_panels_per_string = 10`), `core/layout.py:298-303` (`string_rule`) and `:327-337` (`mark_used` numbers consecutive used panels across faces), `compute.py:346-350`; materials: every panel in the seed has `voc_v`, `vmp_v`, `isc_a`, `imp_a` and the coefficients blank (the workbook has no such columns, `importer.py:19-21`); FS-INV-008 carries `mppt_count 2`, `mppt_max_a 20`, `battery_max_a 135` and nothing else (no `max_pv_voltage_v`, no MPPT window); `boq.py` never reads `mppt_count`, `mppt_max_a`, `max_pv_voltage_v` or `mppt_min_v`.
What, on the cases: the hybrid's one string of 7 is panels 1-3 on the SE kitchen gable (135°, 18°) in series with panels 1-4 on the south hip (180°, 22°); the off-grid variant's string 2 is four south panels in series with the single panel on the east triangle (90°). The inverter has two MPPTs that could take the two orientations separately, for free. No Voc at the coldest cell against the inverter's maximum PV voltage, no Vmp at the hottest against the MPPT minimum, no Isc × 1.25 for the source circuit or × 1.56 for the conductor, no strings-per-MPPT check (three strings on a two-MPPT unit would pass silently; two 13.9 A strings on one 20 A MPPT would pass silently). The default of 10 per string at a typical 52 V Voc for a 585 W 144-half-cell TOPCon module (verify the datasheet) is about 520 V at STC and more on a cool morning, above the 500 V maximum two sibling inverters list in their remarks; FS-INV-008's own limit is not on file.
Why: a mixed-orientation series string runs at the current of its weakest panel every hour the sun is off one face, which is most of the day on a SE/S pair and all afternoon on an S/E pair; the "mismatch" allowance (`other 0.99`) assumes same-orientation strings. The string table with its margins is the first page a reviewing PEE and the DU evaluator read; it does not exist. An over-voltage string is a dead inverter outside warranty.
Fix: a `string_design()` in core: group used panels by face (orientation) first; series count per group from Voc(T_min) ≤ V_max and Vmp(T_max) ≥ MPPT_min with the TMY's minimum air temperature and the site thermal rise; assign strings to MPPTs (≤ `mppt_count`, Isc × 1.25 per MPPT ≤ `mppt_max_a`), split a face across MPPTs only when the count forces it; print a string table (panels, Voc cold, Vmp hot, Isc, margins, MPPT) for the PEE; number the strings on the drawing from this table, not from `string_rule`. A grid job whose panel has no electrical data on the Materials page should get a hard warning before the proposal prints. Effort M-L.

### E-03. Battery selection and the battery circuit [engineering] [bug] Major

Where: `pricing/boq.py:109-114` (`select_battery`: cheapest at or above the kWh, `continuous_a` ignored), `:142-172` (`battery_current_check`, warnings only), `:308-324` (cable from `i_bat_max × 1.25`, breaker = smallest "BATTERY BREAKER" ≥ that, upper bound only against the battery, never against the conductor), `config.py:198` (35 mm² = 170 A).
What: both battery cases pick BC-BAT-004 (15.36 kWh, 100 A continuous, "an 8-12 kW inverter needs 2 or more packs" in its own remark) for an inverter that draws 117 A at rated output and up to 135 A. The app then prices 35 mm² lug pairs (170 A by its table) and a 250 A breaker (IAN-PRT-003; the "BATTERY BREAKER" pattern jumps from 160 A to 250 A), which protects neither the 170 A conductor nor the 100 A battery. Two warnings say so, correctly, and suggest "2 units in parallel (30.72 kWh)", about ₱118,000 more; FS-BAT-003 (15 kWh, 160 A continuous, ₱4,000 more landed) sits second in the options list and would pass. The BOM, proposal, program and cashflow all print as though the design were right; the balance over the hourly year uses a 6.8 kW battery power limit (C-rate 0.5 × 13.6 kWh) that the priced 5.1 kW battery cannot deliver.
Why: at the first evening the inverter asks for more than 100 A the BMS cuts out, which is the brownout the battery was sold for; a 250 A breaker on 170 A cable is a rejected plan (the overcurrent device must protect the conductor; PEC Article 2.40, verify the clause). The owner may never see the warning on a phone.
Fix: `select_battery` takes the cheapest option satisfying kWh and, when the item carries it, `continuous_a × units ≥` the inverter's current at rated output; the breaker is bounded above by the conductor's ampacity (go up one conductor size, 50 mm² at 210 A, before going up a breaker size); use the inverter's continuous battery current for the 1.25 factor and its maximum for the conductor (verify the FS-INV-008 datasheet for which the 135 A is); the hourly balance should cap battery power at the priced unit's continuous rating. The two battery warnings should be hard (red) and block the proposal until the owner picks a unit or acknowledges. Effort S.

### E-04. AC circuits, unchanged from round 2 (E3, E17) [engineering] Major

Where: `pricing/boq.py:296-303` (one gauge for "15 m circuits + 20 m grounding per inverter", quantity `units × (15 + 20)` m), `:339-342` (four 63 A breakers labelled "DU disconnect, grid-inverter, inverter-load, grid-load", warning only if 63 A is below the load), `config.py:197` (8.0 mm² THHN 40 A in the 60 °C column; 3.5 mm² at 25 A where the 60 °C value is 20 A, verify PEC Table 3.10.2.6), `:223-225`.
What: 26.1 A × 1.25 = 32.6 A → 8.0 mm² (40 A) protected by 63 A breakers; the grid-side breaker and conductor are sized on the inverter's output, not on its AC input/bypass current (blank on the item); 35 m of THHN covers one conductor of one 15 m circuit plus the ground, where a hybrid has grid-in, load-out and bypass circuits with line and neutral each (90 m at the same allowance) and no derating for a conduit on a hot roof.
Why: a reviewing PEE rejects a 63 A breaker on 40 A wire; the crew runs out of wire on the day.
Fix: per circuit, breaker = smallest standard rating ≥ 1.25 × circuit current, conductor ampacity ≥ breaker (`_by_amps` exists); conductor count per circuit; grid side from `ac_input_a`; ambient and fill derating; correct the 3.5 mm² entry. Effort S-M.

### E-05. "Grid-interactive: yes" with no certificate on file [engineering] Major

Where: `pricing/boq.py:212-219` (hard warning when the flag is False, ordinary warning when None, nothing when True), `pricing/catalog.py:66-90` (`infer_grid_interactive`: any "hybrid" name is True), `reports/quotation_pdf.py:356-358` (the certificate line is simply omitted when blank), DECISIONS "The owner's corrections after the engineering batch".
What: FS-INV-008 is flagged grid-interactive on the owner's word that the maker confirmed "the selling option"; its `certifications` field is empty and its remark still reads "Off-grid high-frequency type ... pilot production, specs may change". Both net-metering proposals therefore print "the ERC certificate of compliance and the net metering application, all filed by us" with no inverter certificate line and no warning anywhere in the app. The DU asks for the inverter's anti-islanding listing with the application (IEC 62116 / IEC 61727 or UL 1741; verify the current list with Meralco and BATELEC II). A selling option is not a listing.
Fix: on a grid job, flag True with blank `certifications` → ordinary warning "certificate not on file: get the listing from the maker before the application, then type it on the Materials page"; the proposal prints "Inverter certificate: to be confirmed before the application" rather than nothing; until the eco-hybrid's listing is in hand, FS-INV-001 (IEC 61727 / 62116 on file, ₱18,000 more) is the safe grid default. Effort S.

### E-06. What the BOM forgets and what it over-counts [engineering] Major

Where: `pricing/boq.py:261-353`, `config.py:202-246`; catalogue items that exist and are never used: IAN-WIR-028/029/030 grounding wire, IAN-WIR-017 cable gland, IAN-ACC-008/009 and OP-ACC-002 CT/limiter/export meter, BC-ACC-001 and IAN-ACC-007 monitoring, IAN-PRT-013/014 string fuses, OP-ENC-001 battery combiner, IAN-PRT-022..026 and OP-PRT-015..019 rapid-shutdown kits.
Missing on every case: an equipment grounding conductor along the array and bonding hardware per panel and rail (the BOM has 4 earth lugs and 20 m of THHN for 7-11 panels and 12-22 rails); fasteners for 36-66 L-feet (BC-MNT-006 lists no screws, unlike IAN-MNT-008; "Sealant, fasteners and other small items" is two tubes of sealant); labels and placards (PEC Article 6.90 marking, verify what the LGU and the DU want at the service); a visible, lockable AC disconnect for the DU (verify); an export-limit CT or meter for the window the proposal itself describes ("between switch-on and the two-way meter ... power sent to the grid is not yet credited", 30 Oct to 5 Dec here: on a non-detented meter it runs backwards, verify the DU's view); a monitoring dongle; glands, UV ties and clips; string fuses or a combiner where more than two strings share an MPPT; a rapid-shutdown decision (verify whether the LGU enforces PEC 2017's rapid-shutdown rule for roof arrays). Over-counted: four AC SPDs per inverter (one Type 2 per board is the normal design), two enclosures per inverter (four on project 2), an external ATS on a hybrid that has its own transfer (verify the FS-INV-008 manual), DC SPD per inverter rather than per DC box.
Fix: a per-kind checklist in `BoqRoles` (grid: disconnect, limiter, placards; battery: combiner/fuse, ventilation note; all: EGC run and bonding per rail line, fasteners per foot, glands, labels) with the owner's tick list and quantities derived from the take-off (rails, feet, strings). Effort M.

### E-07. Mounting and structure, unchanged (E9) [engineering] Major

Where: `schemas.py:28-40` (RoofFace has no construction fields), `config.py:206-207` (`l_feet_per_rail = 3`), `reports/quotation_pdf.py:522`.
What: project 1's notes say "long-span rib-type on C-purlins at 0.8 m (verify on site)" and nothing reads them; the L-feet land every 1.2 m on a 2.4 m rail whether the purlins are at 0.6, 0.8 or 1.0 m, on a 22° hip roof as on a flat one; no uplift check (NSCP wind zone for Laguna and Batangas, verify with the PEE/CE), no dead load (7 × 26 kg plus rails), no fastener schedule, no flag for tile, concrete, old or thin roofs. The proposal tells every customer the rails "clamp to the roof framing through the sheet with sealed fasteners".
Fix: roof construction fields on the face (sheet, purlin or rafter spacing, material, age), L-foot spacing = purlin spacing capped at the rail maker's limit, a components-and-cladding uplift check returning fasteners per foot and a PEE/CE flag, a mounting detail on the plans. Effort M for fields and spacing, L for the uplift.

### E-08. The plan drawing as an installation drawing [engineering] Medium

Where: `reports/drawings.py:63-139` (`plan_drawing`), `core/layout.py:234-295` (`face_geometry` has every coordinate the drawing needs), `frontend/src/components/PlanDrawing.tsx`.
What works: each face to scale with a 1 m bar, the eave labelled, the facing and pitch, the setback dashed, wall strips hatched, obstacles lettered with a legend, panels numbered from the eave, used panels solid and spare positions dashed; the rows match the BOM's rail take-off (verified: 12 rails, 36 feet, 12 end and 8 mid clamps, 6 splices for rows of 3, 3 and 1). What a crew and a PEE still lack: dimensions (the first row is 0.25 m up the slope and panel 1 starts 2.06 m from the left corner on the south hip; nothing prints that), rail lines and feet, string numbers (only in the browser tooltip), the five faces assembled into one roof plan with a north arrow, a scale ratio, the inverter, battery, meter and conduit route, and the basis of the 0.5 m setback (walkway or fire setback, verify the LGU/BFP rule).
Fix: a dimensioned plan sheet per face (edge offsets, row pitch, rail lines at the purlin spacing, string labels, legend) and a roof plan with the faces placed, as the first page of the plans data pack. Effort M.

### E-09. Cable lengths and conduit from allowances [engineering] Medium

Where: `config.py:184-188` (PV 25 m per string, AC 15 m, ground 20 m, conduit 30 m), `config.py:230-231` (one 2 m tray), `schemas.py:138-156` (per-job overrides exist; no survey field for the inverter location or route).
What: on project 1 the kitchen-gable string and the south-hip panels are on different roofs of the house; 25 m per string is a guess either way; 30 m of 32 mm flex conduit and one tray are the same on every job; conduit fill is never computed.
Fix: survey fields for the inverter and battery wall and the route length from each face; cable per string from the route; conduit length from the route and fill from the conductor count. Effort S-M.

### E-10. Program of works [engineering] [pm] Medium

Where: `pricing/program.py:337-349` (dates), `:184-201` (task labels and man-hours), `pricing/engine.py:238-263` (roof man-hours × `roof_factor`), `config.py:98-103`, `:173-174` (`roof_factor = 0.75` for every job), `:286-306`.
What: the net-metering application starts on 21 Oct, the day after signing, while the sealed plans it needs finish on 22 Oct; the two-way meter is `max(commissioning, agreement) + 15` and only lands after the CFEI here because the CFEI (4 Nov) happens to precede the agreement (20 Nov); no DIS/DAS step with its days and fee (verify Meralco and BATELEC II); the pickup run falls on the permit-approval day with no supplier lead time; no pre-installation final check (which the proposal promises), no "export limit set to zero until the two-way meter" task, no handover and O&M briefing, no earth-resistance and insulation test as tasks. The hour plan: four people on the roof finish rails, 7 panels on two faces of a hip roof and the roof wiring between 06:45 and 07:57 (`roof_mh` 4.8 = (2 + 7 × 0.375 + 7 × 0.25) × 0.75); the roof factor is a job default, not a function of faces, pitch and shape; ground tasks still print as minute slices ("Drive and bond the ground rod 10:58-11:02" for a 3 m rod). The task floors (commissioning 120 min, battery and inverter 60 min) and the late-finish rule work as decided.
Fix: dependencies (application after the sealed plans, meter after `max(CFEI, agreement)`, DIS step), a lead-time field per supplier, the final-check and export-limit tasks, a roof factor that rises with faces, pitch and hip/triangle shapes, and rate calibration from the next jobs' timesheets. Effort S-M.

### E-11. Economics and cashflow carry-overs (E13, E16) [engineering] [finance] Medium

Where: `pricing/economics.py:91` (`after = max(import × tariff − export × credit, 0)` per month, no carry-over, warned at `:114-115`), no fixed-charge setting; `pricing/program.py:433-437` (commission on every job, full output VAT 30 days after completion), `config.py:159-161`.
What: project 1 shows the `export_credit_capped` warning; both net-metering cases credit export at ₱6.50 (verify the DU's blended generation rate, and BATELEC II's); the cashflow books ₱11,481 "Agent commission" and ₱33,429 "VAT remittance" on jobs with no agent and no input VAT netted. The finance reviewer owns these; listed so the engineering view agrees with theirs. Effort S.

### E-12. Paper slips [engineering] [copy] [bug] Minor

- Card: `reports/card.py:146` computes the ratio from `prod["avg_monthly_kwh"]` (at the panels) while `:131` prints the at-meter figure: "Your roof can make about 1,080 kWh, around 3.2 times what your house uses" (1,080 / 380 = 2.8; the roof-check PDF says 2.9). `card.py:170` prints "1 panels" for the hip ends.
- Proposal: `reports/drawings.py:161` prints "1 of your panel here"; `reports/quotation_pdf.py:520` prints "The net metering agreement transfers to the new owner" and `:434-435` "Permit and net metering dates are estimates" on the off-grid (no-export) proposal, which has no agreement.
- Screen: the at-a-glance tile says "14 kWh battery" (`frontend/src/pages/AssessmentPage.tsx:370,555`, the sizing's nominal) while System design, Quantities and the proposal say 15.4 / 15 kWh (the BOM unit).
- Roof check: page 3 holds only "About this estimate" and "Next step" on a five-face roof (`reports/customer_pdf.py:173`, the KeepTogether pushes the block).
- README.md:353 "96 tests" (155 pass).
Effort S for all.

### E-13. Peak and k methods (E11, E12) [engineering] Minor

`core/audit.py:323-331`: the inverter requirement is the duty-weighted hour table (the kettle counts 525 W of 1,500 at 06:00); the nameplate coincidence at 06:00 on project 1 is about 6.6 kW against the 4.8 kW shown, which matters in backup mode on a 6 kW unit. `core/kfactor.py:202-213`: the best set's k (0.921, south) is applied to the SE face measured at 0.909. Both as decided; noted for the record. Effort S.

### E-14. BOM export [engineering] Minor

`api/assessments.py:242-305`: columns code, item, supplier, qty, unit, role, note. For a pickup list and a PEE check it lacks the spec/model code (SMART-BCT-V-48-300(P)), the rating, a section or supplier grouping with cash per supplier (already computed in `cash_by_supplier`), wastage or pack rounding (25 m of PV cable, 35 m of THHN against the 150 m box rate, 30 m of flex against 25 m rolls), weight per line for the truck, and a header with the project, date and revision. The wastage percentages are applied as pesos in `engine.landed_cost`, never as quantities, so the crew gets no spare. Effort S.

### E-15. Hand-off from a booking [crm] Minor

`api/leads.py:174-183`: converting a lead writes a bill row (`id="lead"`) from the visitor's typed kWh and pesos; `pricing/economics.py:60-64` then derives the tariff from it and the proposal says "from your latest bill". Nothing in the audit editor marks that row as a website guess (no match for `lead` in `frontend/src/components/AuditEditor.tsx`). `schemas.py:244-253, 274` keeps a `lead` block with source and contact fields for old records inside the engineering document. Fix: a visible "from the website estimate, replace with the real bill" marker that blocks the proposal's "from your latest bill" wording until replaced; strip the old `lead.source` and `lead.contact` on migration. Effort S.

[pm] For the record, not a defect: the stage pill (`schemas.py:177`, sourcing to closed) and the cashflow's agent-commission and VAT-remittance lines are PM and finance facts living in the engineering app, as the decision in force allows until the modules exist.

## 2. Round 2 findings: what was fixed and what was not

| Round 2 | Status |
|---|---|
| E1 off-grid default on net-metering jobs | Built: flag, per-kind default, hard warning for False. Residual: the eco-hybrid is True with no certificate (E-05). |
| E2 string design | Not built. Fields exist on the items, all blank in the seed and unread by `boq.py` (E-02). |
| E3 breaker/conductor coordination | Not fixed (E-04), and now the same defect on the battery circuit (E-03). |
| E4 losses after the panels | Fixed: 0.96 × 0.98 × 0.97 × 0.99 = 0.903, applied once before sizing; documents say "at your meter". |
| E5 hourly-year battery with autonomy | Fixed: 8,760-hour balance, days of autonomy, loss-of-load hours and days, honest sentences on the proposal. |
| E6 battery continuous current | Half: the check and warnings exist; the selection rule still ignores the rating (E-03). |
| E7 grounding and bonding | Not fixed (E-06). |
| E8 BOM omissions | Not fixed (E-06). |
| E9 mounting and structure | Not fixed (E-07). |
| E10 face allocation | Fixed: best face first, whole rows, production summed over the used panels, BOM rows and drawing agree. |
| E11 duty-weighted peak | Not fixed (E-13). |
| E12 k conflation | As decided (E-13). |
| E13 credit carry-over | Not fixed, warned (E-11). |
| E14 program sequence | Partly: meter after the agreement; CFEI dependency and DIS still missing, application before plans (E-10). |
| E15 labour floors | Floors built; rates and roof factor still the workbook's (E-10). |
| E16 tax and commission lines | Not fixed (E-11). |
| E17 conductor count and ampacity table | Not fixed (E-04). |
| E18 document inconsistencies | Proposal battery from the BOM fixed; new slips (E-12). |
| E19, E20 | As decided; the website estimate agrees with the proposal in kind and ballpark. |

## 3. Deliverables, as of this round

Exists and is right enough to use: roof check (PDF, card) with the plan per face; sizing report (screen); plan drawing per face (customer grade); BOM with edits and CSV/XLSX export; BOQ and build-up; proposal; customer economics; pickup list with cash; program of works with the Gantt, hour plan and customer schedule; cashflow projection.
Partial: site survey record (no construction, service entrance, route lengths); design analysis (gauges and drops only); grounding (lines only); equipment data (flag and remark-derived figures, no datasheets); program (no dependencies, DIS or lead times).
Missing: string design table, single-line diagram, dimensioned layout, OCPD coordination sheet, mounting and structural check, plans data pack, DU application pack and checklist, commissioning test report, as-built, O&M and handover pack, labels schedule. These are items 1-3 and 5-7 of the plan's build order (`docs/plan-engineering-app.md` section 7); nothing in them was started this round beyond the data fields.

## 4. What is sound (keep it)

- Production: Perez transposition, Martin-Ruiz, Huld csi, the measured thermal rise (26.9 and 27.7 °C per kW/m², in the normal band), ERA5 hours evaluated at the interval centre, months with real day counts; −9.3 % and −8.5 % against the k = 1 reference are plausible site factors.
- The losses chain is explicit and not double-counted: temperature in the module model, soiling, wiring, inverter and "other" once each, printed with their values on the screen and summarised honestly on the documents ("about 10 % ... is lost"). Clipping is not modelled and does not matter at these DC/AC ratios.
- Layout: trapezoid and triangle faces fit correctly (checked the south hip's 3/2/2 rows by hand), wall strips cut before fitting, left-out panels respected; the drawing, the sizing's rows and the BOM's rail take-off are one geometry.
- Sizing: net-zero on the faces the panels occupy, the off-grid margin on the worst month, the hourly-year balance with loss-of-load reported, the honest "grid steps in" numbers; the two battery warnings are correct in substance.
- Pricing: reproduces the workbook; customer sections add to the contract; the proposal prints the BOM's battery and inverter, never the sizing's.
- Program and cashflow: milestones, cash at the suppliers on the pickup day, the running balance and its low point (−₱50,804 on the pickup day is the number the owner needs), the Gantt with tasks, milestones and payments, the one stale rule on every document, documents refused on test weather.
- The Design and outputs screen reads in the order an engineer wants and the protection table, strings tile and warnings are where they should be.

## 5. Decisions the owner needs to make

1. Net-metering (no battery) inverter sizing on the array, and whether a plain grid-tie inverter is allowed on a no-battery job (today: hybrids only).
2. Battery selection on continuous current as well as kWh (FS-BAT-003 over BC-BAT-004 at about ₱4,000 more), and whether the two battery warnings should block the proposal.
3. The eco-hybrid's anti-islanding listing: get the certificate from Felicity and type it on the Materials page, or make FS-INV-001 the grid default until then.
4. Strings per face and per MPPT, and the panel electrical data from the Blue Carbon datasheet (Voc, Vmp, Isc, Imp, coefficients) before the next grid job.
5. The DU checklist and lead times for Meralco and BATELEC II (application prerequisites, DIS, CFEI before the meter, export limiting before the two-way meter).
