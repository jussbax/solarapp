# UX audit, round 4: the pattern, user management, the stage pill and the panel, Settings as a menu, the three jobs

Agent "ux". The owner's words this round: eight screenshots "of things that are aesthetically wrong", "make the panel automatic in the background and remove the section from data entry", "is the tagging really necessary for the engineering team?", "the user management is really not intuitive", "Facebook-level easy", and, added mid-round, "the settings page could also do a revamp: instead of one continuous form, show only what is relevant to the menu you already created".

This report is a specification. Part 1 gives the rules that close each family of defect, then the per-field tables so nothing is missed. Part 2 specifies People, Your account and Settings-as-a-menu. Part 3 specifies the engineering status that replaces the stage pill, the automatic panel, and the other data entry the app can do for itself. Part 4 counts the taps of the three jobs the owner does most, today and in the shortest honest version. The appendix lists the measurements and the screenshots.

## Setup and method

- Private app on 127.0.0.1:8010 with a fresh database (`scratchpad/agents4/ux/app.db`, seeded from `PLD_Materials_DB.xlsx`: 362 items, 4 suppliers, 14 solar panels of which 4 carry dimensions). Projects built through the API with the real PVGIS data (`seed.py`): project 1 "Maria Santos", Pila (two faces, two candidate panels, two reading sets, eight appliances, a 380 kWh / ₱4,900 bill, net metering + battery, signing 20 Oct, stage Quoted; calculated: 5 panels, 2.92 kWp, 15 kWh battery, ₱309,900, one installation day); project 2 "Jose Reyes" calculated then edited (stale); project 3 "Ana Dizon" never calculated; two engineers with temporary passwords (`pedro.santos`, `lita.cruz`); one website booking ("Test Visitor", Pila, 380 kWh, hybrid) made through `/api/quick/estimate` and `/api/quick/lead` with the internal token, then started as a project on the desk. Stopped at the end.
- Walk: `walk.js desk` and `walk.js phone` (1280×900; 390×844 at DPR 2 with touch) over login, Projects with the booking panel, the three projects' four steps (the Pricing step's three input cards, the seven Design and outputs cards), the stale and uncalculated projects and the new draft, Materials (list, inline edit of FS-INV-008, New item, Import), Settings with every one of the 20 pricing sections opened, the find box, a dirty save bar, Your account (the "need the password first" message, the QR set-up), People (the add form and the temporary-password banner), Weather, and the first-sign-in gate as each engineer. `flows.js` measured the Settings positions and the booking hand-off. 114 screenshots in `scratchpad/agents4/ux/shots/` (`d-` desk, `p-` phone), reports in `desk-report.json`, `phone-report.json`.
- Measured on every page by `patterns.js`: number controls with more than three decimals; monospace or JSON textareas and comma-separated list inputs; `.control > .unit` spans whose `scrollWidth` exceeds their box (the CSS ellipsis); number fields in a `Field` with no unit; help texts taller than one line (height over the computed line height); a block heading repeating the field label above it; cells on one grid line whose control tops differ by more than 3 px, or whose heights differ by more than 8 px; `input[type=number]` counts (Chromium draws spin arrows on hover and focus on every one); labels, options, badges, row headers and link-buttons that start lowercase; CSS `text-overflow: ellipsis` boxes that overflow and literal "…" characters; plus round 3's `scrollWidth`, sticks, sideways-scrolling tables, tap targets and text sizes.
- Two capture artefacts to ignore in the screenshots: an element screenshot taller than the viewport shows the sticky tabs or the save bar mid-image (Playwright scrolls while stitching), and a gold ring on a button is the hover under the headless mouse.

## Verdict in one paragraph

Round 3's grid holds: every page is exactly 1280 or 390 px wide, nothing sticks out of its card, the controls on a grid line share a top edge except four places listed below. What the owner is now seeing is not alignment but *content* that was never designed for a form: 9 settings shown as raw workbook floats (0.893854748603352), one JSON box, 5 comma-separated lists, 12 units clipped by the 45 % cap on the unit span (14 on the phone, where "₱ per kWh" itself is cut), 56 number settings in Settings with no unit at all because they have no META entry (their label is the title-cased key: "Setup mh", "Typical fill", "Cargo volume m3"), 47 help texts longer than one line (the longest 13 lines in a 183 px column), 252 spin-arrow inputs on one page, ~45 lowercase labels, 13 section summaries ending in "…", one duplicated heading, and two tables sitting beside single fields on no common grid. Six rules close all of it (R1 to R6 below), and most of the work is one map (`META`) and one component (`Field`/`NumberInput`). The user-management pages are correct and safe but read as a security manual: a standing "Confirm it's you" form that must be filled before any button works, a six-column table of people with link-buttons, a 19-character password the owner has to dictate. Part 2 replaces them with cards, dialogs and switches. The stage pill carries eight commercial stages of which the engine uses one fact (quoted or not); Part 3 replaces it with a status the app derives. The Panel options card can leave the On site step: the materials list already carries the candidates.

---

# Part 1. The pattern catalogue

## 1.1 The rules (one per family; each closes every instance in the tables that follow)

**R1. Number formatting per quantity kind.** A number is shown as a person says it. `NumberInput` gets a `decimals` prop and rounds the *displayed* value (the stored value keeps its precision until the owner retypes it); `step` is `10^-decimals`; the settings editor derives `decimals` from the field's kind (the META entry carries `kind`, falling back on the unit text). Kinds and decimals:

| Kind | Decimals | Examples | Unit text |
|---|---|---|---|
| Money, whole pesos | 0, thousands separator | 3,000 · 905.62 → 906 | ₱, ₱ per day, ₱ per trip day |
| Money rate per kWh or per km | 2 | 12.00 · 6.50 · 12.00 per km | ₱ per kWh, ₱ per km |
| Percent (stored as a fraction, shown as percent) | 1, trailing zero dropped | 12 · 12.5 · 0.5 | % |
| Man-hours and hours | 2 | 0.89 · 0.43 · 0.38 · 0.25 | h, h per panel, h per unit |
| Days, counts, pieces, panels, evenings | 0 | 2 · 10 | days, pcs, panels |
| Length in metres | 2 (panel sizes 3) | 2.40 · 25 · 2.278 | m |
| Distance | 1 | 10 · 12.5 | km |
| Mass, volume | 1 / 2 | 32 · 3,000 · 14.27 | kg, m³ |
| Factor, ratio, share (dimensionless) | 2 | 0.75 · 1.25 · 1.30 · 0.14 | × |
| Electrical | V 1, A 0, W 0, kW 1, kWh 1, kWp 2 | 51.2 · 63 · 585 · 6.0 · 15.0 · 2.92 | V, A, W, kW, kWh, kWp |
| Constants the owner never edits (copper resistivity, coordinates) | shown read-only, 4 | 0.0172 · 14.2306 | Ω·mm²/m, ° |

Also round the three workbook-derived defaults in `backend/solarapp/pricing/config.py` to their kind (0.89, 0.43, 0.38 h; ₱906; 14.27 m³; 0.14) so a reset shows clean numbers (the price moves by well under 0.5 %; verify with the owner, or keep the stored precision and round only the display).

**R2. Unit placement.** A unit is never cut off. `.control > .unit` loses its `max-width` and `text-overflow` (`styles.css` "the form system" block: `max-width: 45%` on the desk, `40%` on the phone). The unit text beside a control is at most 12 characters ("₱ per kWh", "% a year", "days", "kg CO₂/kWh"); anything longer moves into the label in parentheses ("Tool charge (₱ per installation day)" becomes label "Tool charge" + unit "₱ per day"; "Final inspection certificate, days after installation" becomes label "Final inspection certificate" with unit "days" and the qualifier in the help line). Every number field has a unit; a count has "pcs", "panels", "rows", "per job"; a factor has "×". The per-field table (1.2 C) gives each.

**R3. Help-text policy.** Under a field there is at most one line at the field's width: about 30 characters in a four-column line on the desk, 22 in the phone's two-column line, 60 in a two-column (`wide`) cell. The line says *what* the number is ("Paid in cash after the job"); it never carries history, formulas or "verify" notes. Anything longer goes behind a "?" beside the label: `Field` gets an `about` prop that renders a 20 px round button (`aria-label="About {label}"`, 44 px hit area on the phone) toggling a note that spans the full grid line under the row (the `.row-help` lane that already exists), titled with the label and carrying the full text; one open at a time per grid; closed by the button, Escape or a tap elsewhere. A section-wide explanation (the roles, the categories) stays as the section note at the top. Where the label and unit already say what the number is, the help line is dropped and only the "?" remains.

**R4. The grid rule.** Everything on a grid line is a `.field` on the three-row subgrid; a table (a size table, a matrix, the payment terms, the categories) is a `.full` block on a line of its own and never sits beside a single field. Two small tables that belong together become one table with a unit column (Minimum task durations + Late finish allowance → one "Minutes" table of four rows). A block carries one heading: either the field label above it or the heading inside it, never both. A block with controls of its own (the payment terms' installments row) uses the same `.form-grid` column count as the lines above it, not an auto-fill grid. A `.row` (flex) keeps `.field` children only; a button in a row sits in a `.field-action` so its top matches the inputs.

**R5. No JSON, no comma lists.** Structured data gets an editor: a list of objects is a table with one row per object, an "Add" button and a "Remove" link; a list of scalars is a table of one column (or chips with an "Add" field); a map of size → value is the existing kv table with the size unit printed ("3.5 mm²") and a unit column header. The textarea branch of `renderField` in `PricingSettings.tsx` is removed, and a section the editor does not know becomes a read-only "Set by the developer" note rather than a JSON box.

**R6. Spinner arrows nowhere.** One CSS rule: `input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0 } input[type=number] { -moz-appearance: textfield; appearance: textfield }` in `styles.css` "controls". (The phone keyboard still gets the numeric pad from `inputmode="decimal"`.) 252 inputs on Settings, 47 on On site, 36 on Pricing, 31 on Energy audit, 30 on Design and outputs, 14 on a Materials edit row.

**R7. Capitalization.** Sentence case for every label, badge, option, row header, chip and link-button; lowercase only for units and symbols (m, kWh, mm²). The global `th { text-transform: uppercase }` is kept for column headers only; row headers in `kv` tables are sentence case (they already are, but the data gives them lowercase). The per-string table is 1.2 H.

**R8. Nothing ends in "…".** A closed section's summary shows the first names that fit and then a count chip ("12 settings") instead of "…" (no `text-overflow`); on the phone the summary wraps. Gantt labels wrap to two lines or get the full 40 % width (round 3 item 10, still open). Units never ellipsize (R2).

**R9. The form never asks what the app can know.** A value with one right answer is computed, read from the company profile or from the materials list, and shown as a default (the `default` tag device from round 3) or not shown at all. The list is in 3.4.

## 1.2 Per-field tables

Every instance measured on the desk at 1280 px; the phone adds the ones marked (phone). Sections are the Settings sections as titled today; "Site", "Audit", "Pricing step", "Materials" are the project and materials pages. Severity: B blocks a task on a roof, C confuses, K cosmetic. Effort S (an hour or two), M (half a day to a day).

### A. Raw floats (R1). Severity C, effort S (one `decimals` prop and one kind map)

| Screen | Field | Today | Show as | Unit | Kind |
|---|---|---|---|---|---|
| Settings › Ground work | Mounting mh per unit | 0.893854748603352 | 0.89 | h per unit | man-hours |
| Settings › Ground work | Wiring mh per unit | 0.43010752688172 | 0.43 | h per unit | man-hours |
| Settings › Ground work | Hybrid pace | 0.375001547634115 | 0.38 | × | factor |
| Settings › Tools | Tool charge | 905.624978858076 | 906 | ₱ per day | money |
| Settings › Truck and freight run | Cargo volume m3 | 14.274143347 | 14.27 | m³ | volume |
| Settings › Handling at base | Typical fill | 0.144482896668418 | 0.14 | × (share of the truck) | factor |
| Settings › Wiring rules | Copper resistivity | 0.0172 | 0.0172, read-only with a "?" | Ω·mm²/m | constant |
| Settings › Route | Base lat / Base lon | 14.2306 / 121.3647 | not typed: a map pin under "Company base" (R9) | ° | coordinates |
| Materials › edit FS-INV-008 | Volume (m³) | 0.05918 | 0.06 (3 decimals when under 0.01) | m³ | volume |
| Site › map | lat/lon in the pin readout | 14.2325 | fine (4 decimals) | ° | coordinates |
| Pricing step | Roof productivity factor | 0.75 | 0.75 | × | factor (already right) |

Screens: `d-10-sec-ground-work.png`, `d-10-sec-tools.png`, `d-10-sec-truck-and-freight-run.png`, `d-10-sec-handling-at-base.png`, `p-10-sec-ground-work.png` (the phone shows "0.8938547486(" cut mid-digit).

### B. JSON or free-text boxes holding structured data (R5). Severity C, effort M

| Screen | Field | Today | Replace with |
|---|---|---|---|
| Settings › Ground work | Tasks | a 12-row monospace JSON textarea of 12 objects (1,789 characters; the phone shows 9 lines of braces) | a table "Ground tasks": columns Task (label), Mounting weight (×, 2 decimals), Wiring weight (×, 2 decimals), Per (unit text: "per inverter", "per m", "per job"), Remove; "Add task" below; the `key` is generated from the label on add and shown under it in small print only for the developer's sake (as the roles do). `GroundTask` is already a typed list in `config.py`. |
| Settings › Route | Stops in driving order | one comma-separated input ("Pila base, IAN Solar, …"), clipped at the desk width; help "Comma separated." | a one-column table "Stops, in driving order" with a drag handle or ▲▼ arrows and "Add stop"; the two matrices below take their headers from it (they already do). Adding or removing a stop adds or removes the row and column in both matrices. |
| Settings › Wiring rules | Standard AC breaker sizes | a comma list of 13 numbers in a `wide` cell, with a two-line help | a chip row "16 · 20 · 25 … 250 A" with an "Add size" field (one number, Enter adds, × removes); help one line: "The breaker is the next size at or above 1.25 × the current." |
| Settings › BOM item roles | Inverter names to skip (words); Battery names to skip (words) | two comma lists in `wide` cells | chip rows with "Add word"; the help one line: "Items whose name has one of these are never picked." |
| Settings › Wiring rules | THHN ampacity, Battery cable ampacity, PV cable ampacity | kv tables (fine) but the row header is a bare "14", "3.5" and there is no unit column | keep the kv table; row header "14 mm²" (the roles section already does this), a column header "A", and sort by size (today 14, 22, 30, 3.5, 5.5, 8.0: string order). The three tables go on their own lines (R4). |
| Settings › BOM item roles | PV cable red/black, THHN wire, Battery cable lug pair, by size | kv tables of size → code (fine) | keep; add "Add size" so a new gauge needs no developer. |
| Settings › Truck and freight run | Basis | a free-text line "Isuzu NMR85HS closed van, 14 x 6 x 6 ft box (shadow truck)" clipped at the cell width | label "Truck" in a `full` cell; it is a name, not a setting, and prints nowhere: keep it as the section note or a `wide` text field "Truck (name, for your own notes)". |
| Settings › Company base | Company base (a bare string section) | one text field "Company base" = "PL Development Inc., Pila, Laguna" | folds into "Freight and the truck" as the first line of the route: name + a map pin (gives `base_lat`/`base_lon`, see R9). |
| Audit › System | Inverter sizes available (kW) | a comma list input that commits on blur | not per customer: it is the company's stock, derived from the inverters in the materials list (`rating_kw` of active items), so the field goes (3.4). |

Screens: `d-10-sec-ground-work.png`, `d-10-sec-route-stops-km-and-toll.png`, `d-10-sec-wiring-rules-and-voltage-drop.png`, `d-10-sec-bom-item-roles-codes-the-generator-uses-.png`, `d-04-audit.png`.

### C. Units cut off or missing (R2). Severity C on the desk, B on the phone for the money fields; effort S for the CSS, M for the META map

C1. Cut off by the unit span's `max-width` (12 on the desk, 14 on the phone; every one prints "…"):

| Section | Field | Unit today | Shown (px of needed) | Fix: label / unit |
|---|---|---|---|---|
| Job level | Commission | % of direct cost | 82 of 95 (62 phone) | Commission / "% of direct cost" → unit "%", help "Of the direct cost" |
| Job level | Safety gear | ₱ per person-day | 82 of 109 | unit "₱ per person-day" → "₱ a day", help "Per person on site" |
| Tools | Tool charge | ₱ per installation day | 82 of 133 | unit "₱ a day", help "Per installation day" |
| Program | Final inspection certificate | days after installation | 82 of 133 | unit "days", help "After installation" |
| Program | Inspection and net metering meter | days after switch-on | 82 of 126 | unit "days", help "After switch-on" |
| Savings | Labor per replacement | ₱ including VAT | 82 of 100 | unit "₱", help "Including VAT" |
| Savings | Upkeep | % of contract a year | 82 of 122 | unit "% a year", help "Of the contract price" |
| Savings | Grid emission factor | kg CO2 per kWh | 82 of 102 | unit "kg CO₂/kWh" |
| System losses | Inverter, Wiring, Soiling, Other | % of energy kept (×4) | 82 of 104 | unit "% kept"; the section lead says "share of energy that gets through" |
| Savings (phone only) | Tariff when the audit has no bill; Net metering credit | ₱ per kWh | 62 of 67 | fits once the cap is gone; the phone's two-column cell keeps "₱/kWh" |

C2. Number fields with no unit (56 in Settings, 4 on Site, 2 on the Pricing step, 14 on a Materials edit row, 7 on New item). These are also the fields with no META entry, so their label is the title-cased key. The table gives the label, unit and decimals to put in `META` (`PricingSettings.tsx`), which closes A, C and D for them at once:

| Section | Key (label today) | Label | Unit | Dec. | Help (one line) or "?" |
|---|---|---|---|---|---|
| Labor day rates | pay_unit_days (Pay unit days) | Pay unit | days | 0 | "?": labor is paid in whole units of this many days |
| Job defaults | max_pairs (Max roof pairs) | Max roof pairs | pairs | 0 | — |
| Roof work | setup_mh (Setup mh) | Roof set-up | h | 2 | Per roof, before the first panel |
| Roof work | mounting_mh_per_panel | Mounting | h per panel | 2 | — |
| Roof work | wiring_mh_per_panel | Wiring | h per panel | 2 | — |
| Roof work | simple_roof_factor | Simple-roof factor | × | 2 | "?": the share of the man-hours a simple roof takes |
| Ground work | mounting_mh_per_unit | Mounting | h per unit | 2 | Per weighted unit of the task table |
| Ground work | wiring_mh_per_unit | Wiring | h per unit | 2 | Per weighted unit of the task table |
| Ground work | hybrid_pace | Hybrid pace | × | 2 | "?": ground work runs at this share of the pace when there is an inverter or a battery to connect |
| Hauling | max_kg_per_person | Carried per person | kg | 0 | Heaviest pack ÷ this = carriers |
| Crew transport | vehicle_ownership_per_day | Vehicle ownership | ₱ a day | 0 | — |
| Crew transport | running_cost_per_km | Running cost | ₱ per km | 2 | — |
| Crew transport | base_to_site_km | Base to site | km | 1 | The reference site; a job adds its extra km |
| Crew transport | toll_per_round_trip | Toll | ₱ per round trip | 0 | — |
| Crew transport | one_way_travel_hours | Travel, one way | h | 2 | Taken off the productive day |
| Crew transport | packaging_disposal | Packaging disposal | ₱ per job | 0 | — |
| Truck and freight run | payload_kg | Payload | kg | 0 | — |
| Truck and freight run | cargo_volume_m3 | Cargo volume | m³ | 2 | — |
| Truck and freight run | ownership_per_trip_day | Truck ownership | ₱ per trip day | 0 | — |
| Truck and freight run | driver_per_trip_day | Driver | ₱ per trip day | 0 | — |
| Truck and freight run | helper_per_trip_day | Helper | ₱ per trip day | 0 | — |
| Truck and freight run | diesel_price | Diesel | ₱ per liter | 2 | — |
| Truck and freight run | fuel_economy_km_per_l | Fuel economy | km per liter | 1 | — |
| Truck and freight run | maintenance_per_km | Maintenance | ₱ per km | 2 | — |
| Truck and freight run | trip_days_per_run | Trip days per run | days | 0 | — |
| Handling at base | helper_day_rate | Helper | ₱ a day | 0 | — |
| Handling at base | typical_job_helper_hours | Helper hours, typical job | h | 1 | — |
| Handling at base | typical_fill | Typical fill | × | 2 | "?": share of the truck a typical 6 kW job uses |
| Route | base_lat, base_lon | (a map pin under Company base, R9) | ° | 4 | — |
| Route | reference_site_km | Base to reference site | km | 1 | One way; the pin's extra km is measured from here |
| Route | road_factor | Road factor | × | 2 | Straight line × this = road km |
| Route | km matrix, toll matrix | Km between stops / Toll between stops | km / ₱ (in the table's caption) | 0 | — |
| Wiring rules | battery_pairs_per_battery | Cable pairs per battery | pairs | 0 | — |
| Wiring rules | copper_resistivity | Copper resistivity | Ω·mm²/m | 4, read-only | "?": a physical constant |
| Wiring rules | continuous_factor | Continuous-current factor | × | 2 | 1.25 per the code |
| Wiring rules | ac_conductors_per_circuit | Conductors per AC circuit | pcs | 0 | Line and neutral; the ground is the grounding run |
| Wiring rules | the three ampacity tables | (row "3.5 mm²", column "A") | A | 0 | — |
| BOM item roles | l_feet_per_rail | L-feet per rail | pcs | 0 | — |
| BOM item roles | mc4_pairs_per_string | MC4 pairs per string | pairs | 0 | — |
| BOM item roles | ac_breakers_per_inverter | Inverter-side AC circuits | per inverter | 0 | "?" (the 89-character text) |
| BOM item roles | ac_grid_breakers_per_inverter | Grid-side AC circuits | per inverter | 0 | "?" |
| BOM item roles | ac_spds_per_inverter | AC surge protectors | per board | 0 | — |
| BOM item roles | enclosures | Enclosures | per inverter | 0 | — |
| BOM item roles | cable_trays, ground_rods, earth_lugs, sealants, ac_disconnects, placard_sets | Cable trays / Ground rods / Earth lugs / Sealant tubes / AC disconnects / Placard sets | per job | 0 | — |
| BOM item roles | max_panels_per_string | Max panels per string | panels | 0 | — |
| BOM item roles | bonding_lugs_per_panel, bonding_lugs_per_rail_line | Bonding lugs | per panel / per rail line | 0 | "?" |
| BOM item roles | fasteners_per_l_foot | Fasteners | per L-foot | 0 | "?" |
| Program | min_task_minutes (table) | Minimum task durations (table with a "Minutes" column; rows "Commissioning", "Battery", "Inverter") | minutes | 0 | — |
| Program › Payment terms | installments | Installments | payments | 0 | 0 = none |
| Website estimate | max_panels, panels_per_row, max_requests_per_hour | Most panels an estimate may use / Panels per row / Estimates per browser | panels / panels / per hour | 0 | — |
| Site | Edge setback (m), Gap between panels (m) | Edge setback / Gap between panels | m | 2 | (company defaults, see 3.4) |
| Site | Test panel rating (W), Calibration factor | Test panel / Calibration | W / × | 0 / 2 | (company settings, see 3.4) |
| Pricing step | Strings | Strings | strings | 0 | — |
| Materials › item form | List price (₱), Storage (₱), Weight (kg), Volume (m³), Panel length (m), Panel width (m), Rating, Max PV voltage (V), MPPT min/max (V), MPPT inputs, Max A per MPPT, AC input (A), Battery max (A), Continuous discharge (A) | the unit in parentheses in the label today; move it to the unit slot the `Field` of `MaterialsPage.tsx` lacks (it has its own local `Field`; give it a `unit` prop) | ₱ / kg / m³ / m / V / A / pcs | 0 / 1 / 2 / 3 / 0 / 0 / 0 | — |

Screens: `d-10-sec-job-level-fees-markups-vat-rounding.png`, `d-10-sec-savings-tariff-export-credit-escalation-.png`, `d-10-sec-system-losses-after-the-panels-figures-a.png`, `d-10-sec-crew-transport-mob-demob-.png`, `d-10-sec-roof-work.png`, `p-10-sec-savings-tariff-export-credit-escalation-.png` ("₱ per k…", "₱ includ…", "% of con…", "kg CO2 …"), `d-08b-materials-edit.png`.

### D. Help texts longer than one line (R3). Severity C (the Settings page is 15,349 px tall on the desk with every section open, 27,006 on the phone; the help texts are most of it); effort M (the `about` prop plus the META rewrite)

Measured on the desk: 47 help texts in Settings taller than one line, the longest 12 lines (Inverter overshoot tolerance, 315 characters in a 183 px column; 13 on the phone), 5 on the Pricing step, 1 on Documents, 1 on Site. A short help in the same line as a long one is stretched to the same height by the subgrid (Services markup's 28 characters sit in a 7-line gap beside VAT; Final inspection's "Assumption." in a 2-line gap): the owner's "ragged gaps" of screenshot 18. Once the long ones move behind "?", the short ones are one line and the gaps close. The table gives, per field, the one-line help (≤ 30 characters in a four-column cell, ≤ 60 in a `wide` cell) and what the "?" holds (the full text as it is today, unless noted).

| Section | Field | Chars today | One line under the field | "?" |
|---|---|---|---|---|
| Company | Owner's name | 51 | Signs the proposal | "Also named in the booking thank-you." |
| Job level | Commission | 115 | Cash after the job | full text |
| Job level | VAT | 185 | (none; the unit says it) | full text (the formula) |
| Job level | Services markup | 28 | On labor, permits and tools | — |
| BOM roles | End clamp / Mid clamp / Rail splice / DC breaker | 13–27 | keep as is | — |
| BOM roles | DC surge protector | 112 | One per MPPT input in use | full text |
| BOM roles | Battery breaker: words in the item name | 117 (wide) | Smallest match that covers 1.25 × the battery current | full text |
| BOM roles | AC breaker | 179 | One per AC circuit | full text |
| BOM roles | Inverter-side AC circuits | 89 | The output circuit to the loads | full text |
| BOM roles | AC surge protectors per board | 47 | One Type 2 per board | — |
| BOM roles | Enclosure | 52 | One box per inverter | "AC and DC protection together." |
| BOM roles | Default inverter for net metering | 261 | Must be grid-interactive | full text |
| BOM roles | Default inverter for off-grid | 101 | Blank = cheapest hybrid that fits | full text |
| BOM roles | Inverter names to skip / Battery names to skip | 71 / 70 (wide) | Never picked as the inverter / … as the battery | — |
| BOM roles | Inverter overshoot tolerance | 315 | 0 = never tolerate | full text |
| BOM roles | Grid-side AC circuits | 196 | Grid feed and bypass | full text |
| BOM roles | AC disconnect (DU) | 143 | At the service, for the DU | full text |
| BOM roles | Placards and labels | 203 | Blank = line without a price | full text |
| BOM roles | Monitoring dongle | 126 | One per inverter, same brand | full text |
| BOM roles | Export limiter | 176 | Optional, net-metering jobs | full text |
| BOM roles | Array bonding conductor | 165 | Along the array's rails | full text |
| BOM roles | Bonding jumpers per row | 100 | Added to each row's rail length | full text |
| BOM roles | Bonding lugs per panel | 106 | 0 when the clamps bond | full text |
| BOM roles | Bonding lugs per rail line | 90 | Two rail lines per row | full text |
| BOM roles | L-foot fastener | 153 | Blank = line without a price | full text |
| BOM roles | Fasteners per L-foot | 55 | Verify with the rail manual | — |
| Wiring | Standard AC breaker sizes | 112 (wide) | Next size at or above 1.25 × the current | full text |
| Wiring | Conductors per AC circuit | 89 | Line and neutral | full text |
| Wiring | Continuous current factor | 18 | 1.25 per the code | — |
| Program | Electrical permit approval | 31 | Assumption | "Until you have data." |
| Program | Minimum task durations | 183 (wide) | Floors for the hour-by-hour plan | full text |
| Program | Late finish allowance | 148 | Before the plan adds a day | full text |
| Program | Power off on installation day | 189 | 0 = not stated on the proposal | full text |
| Savings | Net metering credit | 62 | The DU's generation rate | full text |
| Savings | Battery life, if not the warranty | 289 | 0 = the battery warranty | full text (the datasheet history) |
| Savings | Inverter life | 223 | Not the warranty | full text |
| Savings | Labor per replacement | 108 | 0 = none | full text |
| System losses | Inverter | 73 | Datasheet weighted efficiency | — |
| System losses | Wiring | 50 | Cables and terminations | — |
| System losses | Soiling | 110 | Dust between rains | full text |
| System losses | Other | 172 | Mismatch, availability | full text |
| System sizing | Days of autonomy | 228 | Evenings without sun | full text |
| Pricing step | Strings | 62 | From panels per string | "Type a count to force it." |
| Pricing step | Extra km, one way | 79 | From the map pin | full text |
| Pricing step (Savings inputs) | Tariff | 95 | From bill 2026-09 | full text |
| Pricing step (Savings inputs) | Export credit | 124 | The DU's generation rate | full text |
| Pricing step (Savings inputs) | Upkeep | 46 | 0.5 % of the contract a year | — |
| Pricing step (Schedule) | Installation start | 37 (phone 2 lines) | After the permit | — |
| Design › Documents | Next step printed on the card | 138 | Blank prints the card's own line | the example moves into the placeholder (it is there already) |
| Site › Roof readings | Air temperature | 31 (2 lines at 153 px) | Estimated when blank | — |
| Your account | New password | 95 (3 lines phone) | At least 12 characters | "A short sentence you will remember works well; not your username." (or a live checklist under the field) |

Screens: `d-10-sec-bom-item-roles-codes-the-generator-uses-.png` (the tallest section: 1,960 px), `d-10-sec-savings-tariff-export-credit-escalation-.png`, `d-10-sec-system-losses-after-the-panels-figures-a.png`, `d-10-sec-job-level-fees-markups-vat-rounding.png`, `p-10-sec-savings-tariff-export-credit-escalation-.png`, `d-05b-savings-inputs.png`.

### E. Duplicated labels and headings (R4). Severity K, effort S

| Screen | What | Fix |
|---|---|---|
| Settings › Program › Payment terms | the field label "Payment terms" above a boxed block whose own heading is "Payment terms" (`PricingSettings.tsx` `BlockLabel` + `ProgramSection.tsx` `PaymentPlanEditor`'s `card-head b`) | the editor takes a `heading={false}` prop in Settings; the Pricing step keeps the inner heading and the tag |
| Site › Roof faces | two fields labelled "Facing": a compass select ("S") and a degrees input (180 °) (`FacesEditor.tsx`) | one field: the compass select with the degrees as its unit text ("S · 180°"), the exact degrees under More |
| Settings › Program | "Lunch at" (12:00) beside "Lunch" (60 minutes) | "Lunch break" for the minutes |
| Settings › any section | the closed summary repeats the first five field labels under the title, then "… (19 settings)" | a count chip only (R8); the labels inside are one tap away |
| Settings › Materials and markup tiers | the section note repeats the lead | keep one |

### F. Rows whose controls do not share a grid (R4). Severity K (C for the owner's screenshot 17), effort S

| Screen | Cells on one line | Spread | Cause and fix |
|---|---|---|---|
| Settings › Program | Minimum task durations (a kv table) beside Late finish allowance (a field) | 56 px (the owner's screenshot 17) | the table is a `field wide` on the subgrid, so its control row is 150 px tall and the neighbour's 36 px input floats in it; fix: one table "Minimum task durations" with rows Commissioning, Battery, Inverter, Late finish allowance, column "Minutes", on its own line (`full`) |
| Settings › Wiring | THHN ampacity beside Battery cable ampacity; PV cable ampacity beside Standard AC breaker sizes | 24 px; 31 px | kv tables of different lengths side by side: each table `full` on its own line, or the three ampacity tables as one table with three columns (Size mm² · THHN A · Battery cable A · PV cable A) |
| Settings › Website estimate | the "Estimate page switched on" checkbox beside three inputs | 11 px (desk and phone) | a 22 px checkbox centred in a 36 px line reads as misaligned; make it a switch row above the grid ("Estimate page: On") |
| Materials › search row | "New item" button beside the Search/Category/Supplier fields | 13 px | `MaterialsPage.tsx` has its own `Field` (a `div.narrow.field` in a flex `.row`) and wraps the button in a bare `div.narrow`; put the button in a `field-action` and convert the row to `.form-grid` (same for the Import row: file input, checkbox and Import at three heights, 13 px) |
| Audit › Electricity bill | "Add bill" beside the "Scale the audit to match the bill" checkbox | 12 px | the checkbox `label.inline` has no min-height: `label.check` (which has it) |
| Settings › Program › Payment terms | the installments line: Add milestone · Installments · Installment share · Every · First one after · Counted from on an auto-fill grid (150 px columns) | the second line's columns do not match the first (owner's screenshot 15) | "Add milestone" goes under the table at the left (as "Add category" does); the five fields on one `form-grid` line of the section's own four columns plus "Counted from" first on the next line; the milestone name column gets `min-width: 220px` so "Downpayment on signing" is not cut |
| Pricing step › Schedule | (false alarm in the scan: the override tag is a button in the label row; the inputs are aligned) | — | — |

Screens: `d-10-sec-program-of-works-site-day-durations-paym.png`, `d-10-sec-wiring-rules-and-voltage-drop.png`, `d-10-sec-website-estimate.png`, `d-08-materials.png`, `d-04-audit.png`.

### G. Spinner arrows (R6). Severity K, effort S (one CSS rule)

`input[type=number]` per page: Settings 252 (every pricing number), On site 47, Pricing step 36, Energy audit 31, Design and outputs 30 (BOM quantities), Materials edit row 14, New item 7. Chromium draws the arrows on the hovered and the focused one, which is why the owner sees them "on one field only" (screenshots 14, 18, and the Categories table in `d-10-sec-categories-wastage-and-markup-tiers.png`, where the hovered "30" shows them).

### H. Lowercase and inconsistent capitalization (R7). Severity K, effort S

| Where | Strings today | Sentence case |
|---|---|---|
| link-buttons | remove (11 category rows, every payment milestone, every shade row); unlink; restore; use default; task list | Remove · Unlink · Restore · Use default · Task list |
| badges | most kWp; used for the site; not used; low confidence; needs recalculating; password only; authenticator on; temporary password; deactivated; not in list; no size; default; override; edited | Most kWp · Used for the site · Not used · Low confidence · Needs recalculating · Password only · Two-step on · Temporary password · Access removed · Not in the list · No size · Default · Override · Edited |
| select options | clear, partly cloudy, hazy, cloudy, overcast (Sky); engineer, owner (People); unknown, yes: may export (anti-islanding listed), no: off-grid type; unknown (an ATS is priced), built in: no external ATS, none: an ATS is priced (Materials) | Clear · Partly cloudy · Hazy · Cloudy · Overcast; Engineer · Owner; Unknown · Yes, may export · No, off-grid type; Unknown (an ATS is priced) · Built in · None (an ATS is priced) |
| row headers | commissioning, battery, inverter (Minimum task durations); k (owner's formula, average of rows), k_site (heat and low-light removed) (Roof and production › Internal) | Commissioning · Battery · Inverter; Owner's k (average of rows) · Site k (heat and low-light removed) |
| column headers | k, k site (readings table) | k · Site k |
| toggles | weekdays / all days, summer only / all months, x (usage windows) | Weekdays · All days · Summer only · All months · × with `aria-label="Remove window"` |
| cells and notes | never (last sign-in); sees this (schedule); pass-through (build-up); on / off beside the website checkbox | Never · a check mark with the header "Customer sees" · Pass-through · On / Off |
| title-cased keys | Pv cable ampacity; Cargo volume m3; Payload kg; Fuel economy km per l; Setup mh; Mounting mh per panel; Base lat; Base lon; Km between stops | the labels of table C2 |

### I. Truncation with "…" (R8). Severity K, effort S

| Where | Count | Fix |
|---|---|---|
| Settings: every closed section's summary line ("Commission, VAT, Freight markup, Services markup, Safety gear, … (12 settings)") | 13 of 20 sections, plus one CSS cut (Savings: 752 of 756 px) | the count chip; the Part 2 menu removes the summaries altogether (each section is open on its own page) |
| the unit spans of table C1 | 12 (14 phone) | R2 |
| Gantt row labels on the desk ("Net metering application with your electric co…", "Electrical permit application (city or municip…", "Pickup run: IAN Solar, Felicity Solar, One Poi…", "Electric company inspection; two-way meter ins…") | 4 on the desk, 10 on the phone | `Gantt.tsx:46,65`: 40 % label width or two-line labels (round 3 item 10, still open) |
| Materials: the Name/Spec/Basis/Stops inputs clipped at the cell width (no "…", the text runs under the edge) | 4 | `wide`/`full` cells for free text |

### J. Blocks of unequal height in one row. Severity K, effort S

Closed by R3 and R4: the help row of the subgrid stretches to the tallest help in the line (screenshot 18), and a kv table beside a field (screenshot 17). After the fix a line's cells differ only by a wrapped label, which the subgrid already absorbs (label row `align-self: end`).

### K. Other members of the family

- The `default` tag on every one of the 36 fields of the Pricing step (`d-05a-pricing-inputs.png`): when everything is tagged, the tag says nothing. Show the tag only on overrides; the lead line says "All values are the company defaults unless tagged". The fields themselves fold (3.4).
- Labels that carry the unit twice: "Extra km (one way)" + "km"; "Edge setback (m)" with no unit slot; "Test panel rating (W)". The label never carries the unit once the unit slot exists.
- The Materials item form (`ItemForm`, `MaterialsPage.tsx`) is three flex rows of fixed-width cells; on the phone they wrap into ragged pairs (`p-08c-materials-new-form.png`: Unit 160 + Sold as 200, then List price + Rating, then Rating unit alone). Convert to `.form-grid` with `wide` for Name, Spec and Remarks (M).
- The field-tag buttons are 20 px tall on the phone (`BUTTON.field-tag` 64 × 20): under the 44 px rule for a control that does something (returns to the default). Give the override tag a 36 px hit area.
- The Panel options table scrolls sideways on the phone (684 px in 344) with the Model input 90 px wide ("Canad", "585W"): it leaves the step in Part 3.
- "Facing" twice; "Payment terms" twice (E).
- The pricing save bar on the phone still takes three rows while dirty (`p-10c-settings-dirty.png`: chip + Save, then Discard + Reset): Reset belongs under a "?"-style overflow, not in the bar; the Part 2 menu gives each page its own bar with Save alone.

## 1.3 Grouped by cause: what one change closes

| Cause (file) | Closes | Effort | Severity |
|---|---|---|---|
| `META` completed for every key (label, unit, kind/decimals, one-line help, about text) in `PricingSettings.tsx`; the 56 unlabelled keys get entries; keys never shown to the owner (`copper_resistivity`, `base_lat/lon`, `typical_fill`) become read-only or derived | A, C2, D, H (title-cased keys), K (double units) | M | C |
| `NumberInput` `decimals` prop and `Field` `about` prop (`NumberInput.tsx`, `Field.tsx`) | A, D | S + S | C |
| `styles.css`: unit span without `max-width`/`text-overflow`; spin buttons hidden; summary without ellipsis; `label.check` min-height | C1, G, I, F (audit row) | S | K (B on the phone for money units) |
| Table editors for the ground tasks, the stops and the three word/size lists (`PricingSettings.tsx` `renderField`) | B | M | C |
| Program section layout: one "Minutes" table; the installments line on the section grid; the heading once; the ampacity tables on their own lines or as one table (`PricingSettings.tsx`, `ProgramSection.tsx`) | E, F, J | S | K/C |
| Sentence case in the data: `SKY_CONDITIONS`, `min_task_minutes` keys (display map), badge texts, option texts, link-buttons (`types.ts`, `ReadingsEditor.tsx`, `PeopleCard.tsx`, `MaterialsPage.tsx`, `ProgramSection.tsx`, `PanelsEditor.tsx`) | H | S | K |
| Gantt label width (`Gantt.tsx`) | I | S | K |
| Materials `ItemForm` on the form grid (`MaterialsPage.tsx`) | F, K | M | K |

---

# Part 2. User management, Facebook-level easy; Settings as a menu

## 2.1 What a newcomer does not understand, in order

Walked as someone who has never seen the app (`d-11-account.png`, `d-11b-account-needconfirm.png`, `d-12-people.png`, `p-11-account.png`, `p-12-people.png`).

**Your account**

1. The first thing on the page is a form called "Confirm it's you" with a Password box and nothing to confirm. Nobody fills a form that has no button. Press "Set up the authenticator app" below it and the answer is a message: *Enter your password under "Confirm it's you" first.* The person has been sent back up the page to a form they skipped on purpose. (Measured: the message appears in a banner 480 px below the button, under the keys section.)
2. "Authenticator app" is a product category, not a thing a person wants. The banner says "Off. Your password alone opens the back office." in a warning colour: it reads as an error on a page that is fine.
3. "Security keys and passkeys": two unfamiliar nouns and a 220-character explanation ("Its PIN or fingerprint is the second factor, and it only works on this exact address, so a look-alike site gets nothing"). The only action is a text field "Name for the new key" that must be typed before "Add a security key" works, and it needs the password from section 1 too.
4. "Password" is a standing four-field form (Current, New, New again, a rule) always open on the page, under the keys, so the most common action (change my password) is the fourth section down, 701 px from the top on the desk, 1,210 px on the phone.
5. "Lost a phone or laptop?" holds the only red button, "Sign out everywhere", under three sentences that send the person to "the key list above" and "the owner under People".
6. The page is 1,135 px tall on the desk and 2,000 px on the phone for four actions a person takes once a year.

**People**

7. A six-column table (Name, Username, Role, Sign-in, Last sign-in, actions) with three gold link-buttons per row ("Rename · Reset password · Deactivate") and a `<select>` for the role that changes the role the moment it is touched (a native `confirm()` for owner only). On the phone every row is a 300 px stack of caption + value pairs (`p-12-people.png`).
8. "Add a person" asks for the Username first, before the Name, and invents a rule for it ("lower-case letters, digits, dots, dashes or underscores. It is what they type to sign in."). The newcomer does not know what to type; the app knows better than they do (juan.delacruz from "Juan dela Cruz").
9. The temporary password appears in a gold banner *under the table*, 19 characters with dashes, with no Copy button; "I have passed it on" is the only way to dismiss it. On the phone the owner must long-press to select it.
10. Rename opens a browser `prompt()`; Reset password, Deactivate and Make owner open browser `confirm()`s: four different native boxes with the browser's own chrome, which on a phone look like a crash.
11. "Deactivate" (and the badge "deactivated"), "Reset authenticator", "password only", "temporary password": status words from the server, not from the owner's world ("has not signed in yet", "two-step verification on", "access removed").
12. Nothing explains what an engineer can and cannot do except the 300-character lead paragraph.

## 2.2 People, redesigned

Route `/settings/people` (owners only; an engineer never sees the entry). The page has one heading, one line, one button and a list of cards. No table, no standing form, no native dialogs.

```
People                                              [ Add a person ]
Who can sign in to the back office.

┌ JD  Juan dela Cruz (you)              Owner                     ┐
│     juan.delacruz · signed in today 5:38 AM                     │
│     Password only                               [Your account › ]│
└─────────────────────────────────────────────────────────────────┘
┌ PS  Pedro Santos                      Engineer            [ ⋯ ] ┐
│     pedro.santos · has not signed in yet                        │
│     Temporary password                                          │
└─────────────────────────────────────────────────────────────────┘
┌ LC  Lita Cruz                         Engineer            [ ⋯ ] ┐
│     lita.cruz · last signed in 2 Oct, 4:10 PM                   │
│     Two-step verification on · 1 security key                   │
└─────────────────────────────────────────────────────────────────┘
┌ NR  Nene Reyes                        Engineer            [ ⋯ ] ┐   (muted card)
│     nene.reyes · access removed 9 Oct                           │
└─────────────────────────────────────────────────────────────────┘
```

- Card: a 40 px initials circle (gold on ink), the name in 16 px bold, "(you)" muted, a role badge "Owner" (gold) or "Engineer" (neutral), the "⋯" button (44 × 44, `aria-label="Actions for Pedro Santos"`). Second line: username · sign-in fact ("signed in today 5:38 AM" / "last signed in 2 Oct, 4:10 PM" / "has not signed in yet"). Third line: the sign-in method ("Password only" / "Two-step verification on" / "+ 2 security keys" / "Temporary password" in the bad colour). A removed person's card is muted with "access removed 9 Oct" and the menu holds "Restore access" only.
- The "⋯" menu (a popover on the desk, a bottom sheet on the phone; items 44 px): **Rename…** · **Make an owner** / **Make an engineer** · **Reset password…** · **Turn off two-step verification…** (only when the person has an authenticator or a key) · **Remove access…** (red, last). The owner's own card has no menu; its button is "Your account ›".
- Empty state (only the owner exists): under the heading, a dashed card: "Only you so far. Add an engineer so they can open projects on their own phone." with the same **Add a person** button.
- API: unchanged (`POST /api/users`, `PATCH /api/users/{id}`, `/reset-password`, `/reset-authenticator`). The username suggestion is client-side.

**Add a person** (dialog; on the phone a full-height sheet)

Step 1, title "Add a person":
- **Name** (autofocus), placeholder "Juan dela Cruz".
- **Username**, prefilled live from the name as it is typed (`juan.delacruz`: lowercase, accents stripped, spaces to dots, anything else to a dash), editable; help one line: "What they type to sign in". A taken username shows "Taken; try juan.delacruz2" inline on submit.
- **Role**, two radio tiles: **Engineer** "Projects, calculations and documents" · **Owner** "Everything, including pricing, materials and people".
- Buttons: Cancel · **Add**.

Step 2, same dialog, title "Pedro Santos is added":
- "Give them this temporary password in person or by a call, not in the same message as the address."
- The password in 20 px monospace in a box with a **Copy** button beside it (`navigator.clipboard.writeText`; the button reads "Copied" for two seconds; where the clipboard is blocked the text is `user-select: all` so one tap selects it).
- "They choose their own password at their first sign-in. It opens nothing else."
- Button: **Done**. The card appears in the list behind the dialog with "Temporary password".

**Rename…**: title "Rename Pedro Santos"; **Name** prefilled; Cancel · **Save**.

**Make an owner** / **Make an engineer**: title "Make Pedro Santos an owner?"; body "Owners change pricing, materials and people. Pedro keeps every project." Cancel · **Make an owner**. The reverse: "Make Pedro Santos an engineer?" "They keep projects and documents and lose Settings, Materials and People." (The last owner cannot be demoted; the server already refuses: show "You are the only owner" inline.)

**Reset password…**: title "Reset Pedro Santos's password?"; body "They are signed out everywhere and get a temporary password to change at their next sign-in." Cancel · **Reset password** → the step-2 box above (title "New temporary password for Pedro Santos").

**Turn off two-step verification…**: title "Turn off two-step verification for Lita Cruz?"; body "Her authenticator app and 1 security key are removed. Her password alone signs her in until she sets them up again under Your account." Cancel · **Turn off**. (Calls `/reset-authenticator`.)

**Remove access…**: title "Remove Lita Cruz's access?"; body "She is signed out everywhere and cannot sign in. Her projects stay." Cancel · **Remove access** (red). **Restore access** (from the muted card's menu): no dialog; a toast "Lita Cruz can sign in again."

Every dialog: Escape and the backdrop cancel; the primary button is the only black button; errors from the server print inside the dialog under the fields, never in a banner outside it. The owner's session is proof enough for People actions (the server does not ask for a password here; nothing changes).

## 2.3 Your account, redesigned

Route `/settings/account`. Plain sections, each one row with a switch or a button; the password (and the code when two-step is on) is asked **inside the dialog at the moment of the action**. The standing "Confirm it's you" form goes. The API already takes `{password, code}` on every step-up call (`totp/begin`, `totp/disable`, `passkeys/options`, `passkeys/{id}/remove`), so the dialog collects them and sends them: no server change.

```
Your account
Juan dela Cruz · juan.delacruz · Owner

Password
  Last changed 3 Sep 2026                          [ Change… ]

Two-step verification                                 ( ● ) On
  A code from your authenticator app is asked at sign-in.
  6 backup codes left                                [ Show new codes… ]

Security keys
  YubiKey on the keyring · added 9 Oct · last used today    [ Remove ]
  My phone · added 9 Oct · never used                       [ Remove ]
                                                     [ Add a key… ]

Devices
  Signed in on this device.                   [ Sign out everywhere… ]
```

- **Password › Change…**: dialog "Change your password" with **Current password**, **Code from your authenticator** (only when two-step is on; placeholder "6 digits or a backup code"), **New password** with a live checklist under it (✓ 12 characters or more · ✓ not your username) and a show/hide eye, **New password again**; Cancel · **Change password**. Success: toast "Password changed. Other phones and laptops were signed out." ("Last changed" needs a `password_changed_at` on `/api/auth/me`; until then the row shows no date.)
- **Two-step verification**: a switch (44 px, labelled by the row title). Off → On opens a three-step dialog: (1) "Confirm it's you": **Password** · Cancel · **Continue**; (2) "Scan this with your authenticator app" (Google Authenticator, Microsoft Authenticator, Aegis or 1Password): the 168 px QR, "Can't scan? Type this key" with the key in monospace and a Copy button, then **Code it shows now** (6 digits, autofocus) · Back · **Turn on**; (3) "Two-step verification is on": the eight backup codes in a two-column monospace grid, **Copy all** and **Download** (a `.txt`), the line "Each code signs you in once if the phone is lost. Keep them outside the phone." · **Done** (enabled after Copy or Download, or after 5 s). The switch flips only after step 3. On → Off opens "Turn off two-step verification?": "Your password alone will sign you in." **Password** · **Code** · Cancel · **Turn off** (red). The row's second line reads "Off. Your password alone signs you in." when off (muted, not a warning banner).
- "Show new codes…" needs an endpoint that regenerates the backup codes (not in the API today); until it exists the line reads "6 backup codes left" only.
- **Security keys**: rows as above; empty state "No security key yet. A key or your phone's passkey signs you in with one touch." **Add a key…** opens "Add a security key": **Name** (prefilled "Security key" on a desk, "This phone" on a phone; editable), **Password**, **Code** (when two-step is on) · Cancel · **Add** → the browser's own prompt → toast "YubiKey on the keyring added." A blocked context (http, no hostname) disables the button with the one line "Keys need https and a real hostname." **Remove** opens "Remove 'My phone'?" "It will no longer sign you in." **Password** · **Code** · Cancel · **Remove** (red).
- **Devices › Sign out everywhere…**: dialog "Sign out every phone and laptop, including this one?" "You sign in again afterwards. If a phone with the authenticator is lost and you have no backup code, the owner can turn two-step off under People." Cancel · **Sign out everywhere** (red).
- Labels: "Two-step verification" everywhere (the login page's "Code from your authenticator app" stays), never "TOTP", "authenticator" alone, or "passkey" without "security key". The login page's button reads "Sign in with a security key" (as today).

**The first-sign-in gate** (`App.tsx`): keep, with two changes. The gate does not ask for the temporary password again (the person typed it ten seconds ago; the login form passes it to the gate in memory and `changePassword(current, code, new)` sends it silently); the form is **New password** (with the live checklist) and **New password again** · **Set my password and continue**. If the page was reloaded and the memory is gone, the field "Temporary password" reappears with the line "Type the temporary password you were given once more."

## 2.4 Settings as a menu

The owner's words: "instead of 1 continuous form like, why not show what's only relevant to the menu you already created?" Settings becomes a set of pages; the index is the navigation; nothing else is on the screen but the page chosen.

**Entries, in order, with routes** (`/settings` redirects to the first entry on the desk and shows the list on the phone):

| # | Entry (menu label) | Route | What the page shows | Who |
|---|---|---|---|---|
| 1 | Company | `/settings/company` | Profile (company, owner, PEE, license, address, phone, email, where you install); Contact line on documents; Warranties printed on the proposal (five "years" fields); Where to pay | owner edits; engineer read-only |
| 2 | Website | `/settings/website` | Estimate page and booking form (Messenger, Facebook, callback promise, brands); Privacy line; **Estimate page** switch and the website estimate's assumptions (panel used, typical site factor, roof pitch and facing, most panels, panels per row, peak factor, price rounding, estimates per browser): today's pricing section `quick` moves here, so one page holds everything the public page uses; "Open the estimate page" link in the lead | owner |
| 3 | Materials and markup | `/settings/pricing/materials` | Categories: markup and wastage (table); Job level: fees, markups, VAT, rounding; Wiring rules; BOM item roles (closed by default, it is the longest) | owner |
| 4 | Labor and crew | `/settings/pricing/labor` | Labor day rates; Job defaults; Roof work; Ground work (with the tasks table); Hauling; Crew transport; Tools | owner |
| 5 | Freight and the truck | `/settings/pricing/freight` | Company base (name + map pin); Truck; Handling at base; Route: stops, km and toll | owner |
| 6 | Program of works | `/settings/pricing/program` | Site day; Permits and durations; Minimum task durations (one table); Payment terms; Cash timing | owner |
| 7 | Customer savings | `/settings/pricing/savings` | today's "Economics and warranties" (it holds no warranties; those print from Company): tariff, export credit, price rise, output loss, analysis period, discount rate, lifetimes, replacement labor, upkeep, emission factor | owner |
| 8 | System design | `/settings/pricing/system` | System losses after the panels; System sizing (days of autonomy); the audit's company-wide engine numbers that move here (3.4: surge allowance, PV-to-inverter ratio, battery usable share, battery efficiency, design margin); **Preferred panel** (3.3) | owner |
| 9 | Your account | `/settings/account` | 2.3 | everyone |
| 10 | People | `/settings/people` | 2.2 | owner |
| 11 | Weather and data | `/settings/data` | the PVGIS and NASA status table and Refresh | everyone |

A pricing section the groups do not name (a future one) lands at the end of entry 8 under "Other settings", as today's `OTHER_GROUP` does, so nothing is lost.

**Layout.** Desk: a left menu 240 px wide, sticky, with the eleven entries as 40 px rows (the six pricing entries indented under a small caption "Pricing"), the current one marked with the gold left bar as today; beside it the one page: an h1 (the entry label), a one-line lead, the sections of that page as open blocks with h3 headings (no `<details>`: on its own page a section has no reason to be closed, except BOM item roles, which is a `<details>` closed by default because it is 1,960 px). Phone: `/settings` is a list of eleven cards (label, one-line description, chevron, 56 px each); tapping one opens the page with a "‹ Settings" link in the page head (the top bar's page name reads the entry label); the browser's back button works because each entry is a route. The top bar's "admin" name link goes to `/settings/account` as today.

**Save behavior per page.**
- Company, Website: one **Save** at the foot of the page (an inline bar, not sticky; the page is short), enabled when dirty; "Saved" toast; the leave-page guard when dirty. Website's Save writes both the profile fields (`PUT /api/settings`) and the `quick` section (`PUT /api/pricing/config`) in one press.
- The six pricing pages share one in-memory draft of the config (the pricing config is one document on the server). Each pricing page has the sticky bar at its foot (as today) with the chip and **Save**; the chip counts the edited *sections across all pricing pages* ("3 sections edited · Labor and crew, Freight") and Save writes the whole document, so an owner may edit Labor then Freight and save once. The menu shows a dot beside an entry with unsaved edits. **Discard changes** stays in the bar; **Reset to defaults** leaves the bar and lives at the foot of entry 3 under a "Reset every pricing setting to the workbook defaults…" link with the same confirm-and-undo as today. Leaving Settings (not another settings page) with unsaved edits asks, as today.
- Your account, People: no Save; every action is a dialog that saves itself.
- Weather and data: Refresh only.

**Find a setting across pages.** A search box at the top of the menu on the desk (above the entries) and at the top of the list on the phone, placeholder "Find a setting (VAT, team lead, toll…)". Typing shows a result list in place of the menu entries: one row per matching setting, "VAT · Materials and markup › Job level", "Toll per round trip · Labor and crew › Crew transport", "Toll between stops · Freight and the truck › Route" (matching on label, key, help and section, as today's `matches` does, over all pricing sections plus the Company and Website fields). Tapping a row opens that page (`/settings/pricing/materials?find=vat`), opens the section if closed, scrolls the field under the sticky top and gives it a gold ring for two seconds (`:target`-style). Escape or clearing the box restores the menu. The `?find=` parameter survives a reload. "No setting matches" is the empty result.

**Section headings on the pricing pages.** With each page holding only its own sections, the long colon titles shrink: "Job level: fees, markups, VAT, rounding" → "Fees, markups and VAT"; "Program of works: site day, durations, payment terms" → the page's sections "Site day", "Permits and durations", "Payment terms", "Cash timing"; "Savings: tariff, export credit, escalation, lifetimes" → the page; "System losses after the panels (figures at the meter)" → "Losses after the panels"; "BOM item roles (codes the generator uses)" → "Items the generator uses"; "Crew transport (mob/demob)" → "Crew transport"; "Categories: wastage and markup tiers" → "Markup and wastage by category".

---

# Part 3. The stage pill and the panel card

## 3.1 What the eight stages mean to an engineer

The pill (`AssessmentPage.tsx` `stage-pill`, `types.ts` `JOB_STAGES`) offers Assessed, Quoted, Signed, Sourcing, Installing, Commissioned, Net metering, Closed. Grepping the backend for `stage`: it is read in exactly two places. (1) `api/assessments.py:153` `_needs_reprice_confirmation`: from `quoted` onward a price calculated under older pricing settings is held until the owner confirms the re-price. (2) `api/assessments.py:93`: the list summary carries it for the Projects filter and badge. The engine, the program of works, the cashflow and every document ignore it; the schedule runs from the signing date and the installation date, which are inputs of their own.

So, for an engineer, six of the eight are facts about the business, not the engineering: Signed (a contract), Sourcing (a pickup run), Installing (a crew day), Commissioned (switch-on), Net metering (the DU's meter), Closed. They are set by hand, by whoever remembers, and nothing in the app checks them against anything. DECISIONS says the engineering app "is not a CRM or PM tool" and that the leads pipeline is the CRM's: these stages belong there, with the booking status. The two that an engineer cares about (is there a design, has the proposal gone out) the app can know for itself.

## 3.2 The automatic engineering status

Replace the pill with a read-only status badge in the page head and in the project list, derived from facts the record already holds (plus one new timestamp). Nobody sets it.

| Status | Reads | Derived from | Project list filter |
|---|---|---|---|
| Draft | "Draft" (neutral) | not saved yet (`/assessments/new`), or saved without the Calculate checklist (no pin, no face with size, or no reading set) | Draft |
| Surveyed | "Surveyed" (neutral) | pin + a face + a reading set saved; results exist without `sizing`, or no results yet | Surveyed |
| Audited | "Audited" (neutral) | `results.sizing` exists (the energy audit calculated) but `pricing.available` is false (the BOM could not price: missing items) | Audited |
| Designed | "Designed" (good) | `pricing.available` and `program.available`, no `design_blocked` codes; the documents are Ready | Designed |
| Proposal issued | "Proposal issued 9 Oct · ₱309,900" (gold) | a new `proposal_issued_at` + `proposal_issued_total` + the settings version on the record, stamped by the server when `quotation.pdf` is served (once per distinct result; the first time only, later issues update the date) | Proposal issued |
| overlays, as today | "Needs recalculating" chip; "Price held" (the settings-version lock) | `results_stale`; `pricing_settings_changed` | Needs recalculating |

- The re-price lock changes its test from `stage >= quoted` to `proposal_issued_at is not None` (`_needs_reprice_confirmation`): a price goes out on paper, the app asks before moving it; before that, the price simply follows the settings. The confirm question becomes "Pricing settings changed since the proposal was issued on 9 Oct (₱309,900). Re-price now?".
- The list keeps its toggles (All · Draft · Surveyed · Audited · Designed · Proposal issued · Needs recalculating) with counts; the badge on each row is the status.
- The stored `program.stage` stays in the schema for old records and for the CRM to read; the UI no longer shows or sets it. A record with `stage >= quoted` and no `proposal_issued_at` is treated as issued on the record's `computed_at` once (a one-line migration), so today's held prices stay held.
- The page head reads: name, the status badge, the address, and, when issued, "Proposal issued 9 Oct · ₱309,900". When the current price differs from the issued one the badge reads "Proposal issued 9 Oct at ₱309,900 · now ₱312,400" in the warn colour, which is what the lock protects.

## 3.3 The panel: automatic in the background, one tap to override

Today (`d-03b-panels.png`, `p-03b-panels.png`): an eight-column table on the On site step with an "Automatic (most kWp)" radio row, candidate rows with editable name, Wp, length, width, "Fits" and "kWp", an "Add candidate panel" (a blank manual row) and "Add from materials list" (a picker), and a note. On the phone it scrolls sideways (684 px in 344) with the model input 90 px wide. The checklist makes "A panel" a condition of Calculate. A project started from a booking has no panel and no face (`flows.js`: "○ A roof face ○ A panel"), so the engineer meets the table before anything else.

**The rule (server side, at compute).** Candidates are the active Solar Panel items in the materials list that carry dimensions (today 4 of 14: BC-PNL-001 585 W, BC-PNL-002 585 W bifacial, BC-PNL-003 600 W, BC-PNL-004 630 W bifacial; the ten without a size are skipped and already flagged "No size" on the Materials page). The layout runs for every candidate (it does today for `doc.panels`; `results.panels` keeps one entry per candidate with `total_count` and `system_kwp`). The chosen panel is the **Preferred panel** from Settings › System design (a new `roles.preferred_panel_code`, seeded from `quick.panel_code` = BC-PNL-001, the panel the owner stocks and the website quotes) when at least one position fits; otherwise the candidate with the most kWp (today's rule) with a warning "The preferred panel does not fit this roof; using …". "Most kWp" alone is not the right default: with a 630 W bifacial in the list it would always win, and it is not what the crew carries.

**Where it shows.** Nowhere on the On site step: the Panel options card goes, the checklist reads "Map pin · A roof face · Roof readings". It shows where the engineer reads results: the "At a glance" tile's sub line ("5 panels · 2.92 kWp · 585 W BC-PNL-001"), the Roof and production tile "Panels the roof holds" (already prints the name and Wp), and the System design card's **Array** tile, which gains a **Change panel** link-button under its text (44 px on the phone).

**The override, one tap.** "Change panel" opens a sheet (a popover on the desk) listing the candidates with what each gives on this roof, the automatic one first and marked:

```
Panel for this roof
● 585W Monofacial solar panel  BC-PNL-001  2.278 × 1.134 m   16 fit · 9.36 kWp   Automatic (preferred)
○ 630W Bifacial solar panel    BC-PNL-004  2.382 × 1.134 m   16 fit · 10.08 kWp
○ 600W Monofacial solar panel  BC-PNL-003  2.382 × 1.134 m   16 fit · 9.60 kWp
○ 585W Bifacial solar panel    BC-PNL-002  2.278 × 1.134 m   16 fit · 9.36 kWp
○ Another panel…               (name, Wp, length, width: the old manual row, for a panel not in the list)
                                                 [ Use this panel and calculate ]   [ Back to automatic ]
```

Tapping a row and "Use this panel and calculate" sets `selected_panel_code` on the doc and runs Calculate (the results are stale the moment the panel changes, so the button does both). "Back to automatic" clears it. The Array tile reads "585 W BC-PNL-001 · chosen for this job" with the override tag when forced, as the Pricing inputs' inverter does.

**Data.** `doc.panels` and `selected_panel_id` stay for old records; new records store `selected_panel_code` (null = automatic) and, only when "Another panel…" was used, one manual `CandidatePanel`. The server builds the candidate list from the materials list at compute time, so adding a panel on the Materials page changes every future calculation and none of the saved ones. The quick estimate already does this with `quick.panel_code`.

## 3.4 Other data entry on the four steps the app could do for itself

| Step | Field today | What the app knows | Do |
|---|---|---|---|
| On site › Roof readings | Test panel rating (W) = 50, Calibration factor = 1.0, on every project | the company owns one test panel | move to Settings › System design ("Test panel: 50 W, calibration 1.00"); the step shows them as a one-line note "Test panel 50 W" with the `default` device only when a project overrides |
| On site › Roof faces | Edge setback (m) = 0.6, Gap between panels (m) = 0, on every project | company practice | Settings › System design defaults; on the step under "More" with the `default` tag |
| On site › Roof faces | "Facing" twice (compass select + degrees) | one value | one compass select with the degrees as its unit; exact degrees under More |
| On site › Roof faces | Name "Roof 1" | the order | keep the auto name; the field under More |
| On site › Roof readings | Roof face select on each set; Date and time; Sky | the only face; now; optional | the face select appears only with two or more faces; "Date and time" prefilled with now (it is); Sky defaults to "Clear" and stays |
| On site › Panel options | the whole card | the materials list | 3.3 |
| On site › checklist | "A panel" | — | gone |
| Energy audit › Electricity bill | Electric company (free text per bill) | the owner's service area has one DU | default from a Settings › Company field "Electric company" ("Meralco"); the bill row shows it filled |
| Energy audit › Electricity bill | Days in period | the month | already "auto" when blank: keep, hide under the row's "More" |
| Energy audit › System | Inverter sizes available (kW) (a comma list committed on blur), Surge allowance, Max PV-to-inverter ratio, Battery usable share, Battery efficiency, Design margin | the inverters in the materials list; the battery item's datasheet; company rules | the sizes come from the active inverters' `rating_kw`; the four factors move to Settings › System design (they are engine numbers, "every engine number is an editable setting"); the step keeps **System type** only (three radio tiles: Net metering · Net metering + battery · Battery first, no export) |
| Energy audit › Appliances | Duty factor | the category | already the category's; show it as placeholder only (it is) |
| Pricing and program › Pricing inputs | 15 fields, all tagged `default` (`d-05a-pricing-inputs.png`) | the settings and the pin | the card shows **Inverter**, **Battery** and the two facts the pin gives (extra km, strings) and folds the other 11 under "Adjust for this job" (closed `<details>`); the tag only on overrides |
| Pricing and program › Savings inputs | 9 fields, all `default` | the settings and the bill | the same fold; the tariff line stays open ("From bill 2026-09: ₱12.89 per kWh") |
| Pricing and program › Schedule | Signing date (today), Installation start (after the permit), Leave base at, Lunch at, Lunch, the three durations, Payment terms | the settings and the program | open: Signing date and Installation start; the rest folded; the Payment terms block shows "Company terms: 50 % on signing, 40 % on delivery, 10 % on switch-on · Change" and opens the editor only on Change |
| Design and outputs › Documents | Next step printed on the card | the booking's preferred time | prefill "Energy audit: Saturday morning" from `lead.preferred_time` when the project came from a booking |
| Page head | the stage pill | the record | 3.2 |
| New project | the first face 10 × 6 m, 15°, S; from a booking no face at all | — | `project_from_lead` adds the same first face as `emptyDoc` does, so a booking project opens with the face card ready to overwrite, not an empty list |

---

# Part 4. Tap-by-tap: the three jobs

Taps are presses on a control; typing a value is counted as the tap that focuses the field; a scroll is noted, not counted. "Screen" is a page or a step.

## 4.1 Start a project from a booking and reach the proposal

**Today, desk** (`flows.js`, `d-15-from-booking.png`; the booking carried the name, place, phone, best time, 380 kWh and the hybrid goal):

| # | Tap | Screen |
|---|---|---|
| 1 | Projects › **From a website booking** | Projects |
| 2 | **Start project** on the booking | Projects → On site, with name, address ("Brgy. Labuin, near the chapel, Pila, Laguna"), the town pin, the notes, the bill (380 kWh) and the system type prefilled; checklist ✓ Map pin ○ A roof face ○ A panel ○ Roof readings; Calculate disabled |
| 3 | **Add roof face** (the booking project has no face) | On site |
| 4–7 | Eave length · Slope length · Tilt · Facing (4 fields, typed) | On site |
| 8–10 | **Add from materials list** · type part of the name · pick the panel | On site |
| 11 | **Add reading set** | On site |
| 12–17 | three readings × (Sunlight, MPPT power); panel temperature optional | On site |
| 18 | **Calculate** → Design and outputs opens with the roof, no sizing ("Next: Energy audit") | On site → Outputs |
| 19 | **Energy audit** tab | Energy audit |
| 20–55 | **Add appliance** × 6 typical loads, each: name · category · W · qty · when used (open) · a window's hours ≈ 6 taps | Energy audit |
| 56 | the bill's Amount (₱4,900; the kWh came with the booking, the amount did not, and without it the tariff is the settings' ₱12) | Energy audit |
| 57 | **Calculate** → Design and outputs | Energy audit → Outputs |
| 58 | **Documents** sub-tab | Outputs |
| 59 | Proposal PDF **Download** | Outputs |

About 59 taps on 4 screens (Projects, On site, Energy audit, Design and outputs), the Pricing step untouched. On the phone the same count plus a long scroll on each step (On site is 5,432 px, the Outputs step 20,713 px).

**Shortest honest version** (the roof is measured, the audit is typed: those taps are the work):

| # | Tap | Screen |
|---|---|---|
| 1 | Projects › the booking row's **Start project** (the open bookings list under the projects, no toggle: it is empty most days and one line when not) | Projects → On site |
| 2–5 | the first face is already there (3.4): Eave · Slope · Tilt · Facing | On site |
| 6–11 | one reading set is already there with three empty rows: 3 × (Sunlight, MPPT power) | On site |
| 12 | **Calculate** (no panel to pick: 3.3) | On site → Outputs |
| 13 | **Energy audit** | Energy audit |
| 14–19 | a starter list "Typical house: fridge, aircon, lights, TV, washing machine, pump" added with one tap each, default windows from the category; then the engineer corrects watts and hours where the house differs (not counted: that is the audit) | Energy audit |
| 20 | the bill's Amount | Energy audit |
| 21 | **Calculate** | Energy audit → Outputs |
| 22 | Proposal **Download** (the Documents card sits first on the Outputs step when the design is ready, or the At a glance strip carries a "Proposal" button) | Outputs |

22 taps, 4 screens; 3 on the phone when the proposal is sent as a link. Nothing here is a trick: the face, the readings and the appliances are the survey.

## 4.2 Add an engineer and get them signed in

**Today.** Owner, desk: Settings (1) · People in the index (1) · Username (1, and invent "pedro.santos") · Name (1) · Add (1) · read the 19-character password, dictate it, **I have passed it on** (1) = 6 taps, one screen scrolled 4,720 px down (the People card's top); phone: Menu (1) · Settings (1) · People chip (1) · the same four = 7 taps, 6,574 px down. Engineer, phone: Username (1) · Password (1, 19 characters with dashes) · **Sign in** (1) · the gate: **Temporary password** (1, the same 19 characters again) · New password (1) · New password again (1) · **Set my password and continue** (1) = 7 taps, two screens, the temporary password typed twice (`d-14-gate.png`).

**Shortest honest version.** Owner: Settings (1) · People (1) · **Add a person** (1) · Name (1; the username suggests itself; role Engineer is preselected) · **Add** (1) · **Copy** (1) · Done (1) = 7 taps but no invented username, no dictation; the password goes by voice or a separate message as the rule says. Engineer: Username (1) · Password (1) · **Sign in** (1) · New password (1) · New password again (1) · **Set my password and continue** (1) = 6 taps, the temporary password typed once (2.3). Both: two screens.

## 4.3 Change a pricing rate (the team lead's day rate)

**Today.** Desk: Settings (1) · **Labor and crew** in the index (1) · open **Labor day rates** (1) · Team lead (1, type) · **Save pricing settings** (1) = 5 taps on one screen with three jumps (the section is at 2,169 px of 5,774). Phone: Menu (1) · Settings (1) · **Pricing** chip (1; the six group entries are hidden on the phone, `index_sub_visible: 0`) · scroll 1,000 px past the four closed Materials sections · **Labor day rates** (1) · Team lead (1) · **Save pricing** (1) = 6 taps and a 1,000 px scroll (the section is at 3,155 px of 8,497).

**Shortest honest version.** Desk: Settings (1) · **Labor and crew** (1, its own page, the first section open) · Team lead (1) · **Save** (1) = 4. Phone: Menu (1) · Settings (1) · **Labor and crew** (1) · Team lead (1) · **Save** (1) = 5. Or from anywhere: Settings (1) · type "team lead" in Find a setting (1) · the result (1) · Team lead (1) · Save (1) = 5 with no scrolling at all.

---

# Appendix

## A. Measurements that back the tables

- Widths: every page 1280 / 390 px (`desk-report.json`, `phone-report.json` `metrics`); no element past the viewport; the only sideways-scrolling tables on the phone are the Panel options table (684 px, goes with the card), the two route matrices (589 px, with the edge shadows), and the seven results tables of round 3 item 7.
- Settings height with every section open: 15,349 px desk, 27,006 px phone (closed: 5,592 / 8,281). Positions on the closed page: Pricing 1,444 / 2,120; Labor day rates 2,169 / 3,155; Savings 3,228 / 4,568; Your account 3,659 / 5,177; People 4,720 / 6,574; Add a person 5,340 / 7,863 (desk / phone, px from the top).
- Pattern counts, desk Settings with every section open: floats 9, JSON boxes 1, list inputs 5 (+ 4 size maps that are tables already), units cut 12 (phone 14), number fields without a unit 56, help texts over one line 47 (phone 49), duplicated headings 1, lines with controls off the grid 4, spin inputs 252, lowercase strings 8 distinct here (about 45 across the app), "…" 25 (13 summaries + 12 units). On site: floats 0 (the pin's 14.2325 is fine), no-unit 4, help 2, lowercase 11, spin 47. Pricing step: no-unit 2, help 5, lowercase 3, spin 36, tags 36 of 36. Outputs: help 1, lowercase 3, "…" 4 (Gantt), spin 30. Materials edit: floats 1, no-unit 14, lowercase 6, spin 14, rows off 2.
- Tap targets under 44 px on the phone: the People link-buttons are 36 px tall (71–124 px wide), the field-tag override button 20 px, the Menu button 29 px (56 px row), the toggles 36 px (round 3 accepted 36 for toggles); everything else 44.
- Text under 13 px on the phone: units, help and table headers at 12.5 px, field tags and the `.key` line at 11 px, the JSON textarea at 12 px, KPI labels 12 px (as round 3).
- Contrast: unchanged from round 3 (muted 5.4:1, gold text 4.9:1); the chart-gold-as-text items of round 3 are fixed (`GOLD_TEXT` in `ProgramSection.tsx` and `EconomicsSection.tsx`).
- Console: no errors on any page (`console_errors: []`).

## B. Round 3 items still open that this round's rules absorb

Gantt labels truncated (item 10 → R8); the Materials "Grid-interactive" badge now reads "Grid: yes/no/unknown" (done); the profile hints no longer repeat placeholders (done, `isExample`); bare labels in the three roof editors (item 16: the faces editor uses `Field` now; the readings table rows and the panels table still use `aria-label`s, fine); the People table fits the phone (done, as cards).

## C. Files

- Report: `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents4/ux.md` (this file).
- Scripts: `scratchpad/agents4/ux/lib.js` (round 3's stick scanner, re-pointed), `patterns.js` (this round's family scanner and the number-field dump), `walk.js` (`desk` | `phone`), `flows.js`, `seed.py`; outputs `desk-report.json`, `phone-report.json`, `phone.out`, `seed.out`, `seed-state.json`, `est.json`.
- Screenshots (`scratchpad/agents4/ux/shots/`, `d-` desk at 1280×900, `p-` phone at 390×844 DPR 2): `01-login`, `02-projects`, `02b-projects-bookings`, `03-site` (+ `03a-head`, `03b-panels`, `03c-faces`, `03d-readings`), `04-audit`, `05-pricing` (+ `05a-pricing-inputs`, `05b-savings-inputs`, `05c-program-inputs`), `06-outputs` and `06-design-{glance,roof,system,quantities,program,cashflow,savings,documents}`, `07-stale`, `07b-uncalculated`, `07c-new`, `08-materials`, `08b-materials-edit`, `08c-materials-new(-form)`, `08d-materials-import`, `09-settings-top`, `09a-company`, `09b-website`, `10-settings-all-open`, `10-sec-<section>` (one per pricing section, 20), `10b-find-toll`, `10c-settings-dirty`, `11-account`, `11b-account-needconfirm`, `11c-account-qr`, `12-people`, `12b-people-added`, `13-weather`, `14-gate`, `d-15-from-booking`.
- The repository was not modified; `frontend/dist` was not rebuilt; the server on 8010 was stopped at the end.
