# Round 12 engineer brief: the three datasheet workbooks into the app

Written 10 October 2026 by the solar engineer on the audit team, read-only: nothing in the repository was
changed, no test was run against a database. Every figure quoted below is copied from the three plain-text
dumps of the owner's workbooks (panels: 14 rows; inverters: five sheets, 107 model rows and 7 orphan lines;
batteries: three sheets, 82 model rows and 6 maker sub-headers) or computed from them with the arithmetic
shown. No model string is printed in this brief; rows are named by sheet, workbook row, brand, kW/W/Ah and
the item code that would take them. "Verify" marks a figure that depends on a code edition, a DU rule or a
datasheet the app does not hold.

Files read: `backend/solarapp/pricing/catalog.py`, `importer.py`, `boq.py`, `config.py`, `store.py`,
`job.py`, `core/sizing.py`, `core/quick.py`, `reports/plans_pdf.py`, `models.py`, `schemas.py`,
`api/pricing_routes.py`, `frontend/src/pages/MaterialsPage.tsx`, `DECISIONS.md` (contract C4 under
"Engineering numbers", the BOQ rules under module 3 and "Round 3, batch 1", the plan set under "Round 4,
plans"), `docs/plan-engineering-app.md`, the bundled `backend/data_seed/PLD_Materials_DB.xlsx` (the only
copy of the materials workbook in the tree; `backend/tests/fixtures` does not exist, the tests read the seed).

Effort marks: S under half a day, M one to two days, L three days or more. Severity marks on warnings:
**hard, blocks** (refuses the customer documents like `battery_current` does today, `job.py:187`),
**hard** (red banner only), **ordinary**.

---

## 0. What the sheets hold, in one look

| Workbook | Sheet (header row) | Rows | Columns as typed |
|---|---|---|---|
| Panels | Sheet1 (row 3, columns O–V) | 14 | BRAND, Model / Capacity, PMAX, VMP, IMP, VOC, ISC, Max DC System Voltage |
| Inverters | Sheet1 Deye (row 2; header typo "MIODEL"), Sheet2 Solis (row 3), Sheet3 One Solar (row 3), Sheet4 Blue Carbon (row 3), Sheet5 Felicity (row 4) | 25, 35 (+7 orphan lines, rows 47–53, model text in the Details column only), 15, 6, 26 | TYPES OF INVERTER, MODEL, BRAND, Details / specs, Max Charge Voltage, Recommended Discharge Current, Max Recommended Charge Current |
| Batteries | Sheet1 Blue Carbon (title row 4, header row 5), Sheet2 Felicity (row 3), Sheet3 One Solar / Pylontech / Deye / Dyness / Solis / Hithium / JK (row 3, then a sub-header per maker with blank rows between the blocks) | 23, 40, 19 | Sheets 1–2: [LV/HV, unlabelled], BATTERY TYPE (the chemistry), MODEL, BRAND, Nominal Voltage / Voltage, Capacity, Energy Capacity / Energy Rating, MAX CHARGE VOLTAGE, MAX DISCHARGE CURRENT, RECOMMENDED DISCHARGE CURRENT, MAX RECOMMENDED CHARGE CURRENT. Sheet 3: class text, MODEL, BRAND, Details / specs (V; Ah; kWh), Max Charge Voltage, Max Discharge Current, Recommended Discharge Current, Max Recommended Charge Current |

Two layout facts the importer must live with: (a) no sheet has its header on a fixed row or column (the
panel sheet starts at column O, the battery sheets at B, C or D), so the header row is found by its words,
never by position; (b) on battery sheets 1 and 2 the header "BATTERY TYPE" sits over the chemistry column
and the LV/HV column to its left has no header at all, so "the column left of BATTERY TYPE" is a rule, not
a header lookup.

What no sheet carries: the panels' temperature coefficients and maximum series fuse rating; the inverters'
maximum PV voltage, MPPT window, MPPT count (except inside the Deye "MPPT 18/36/36A" text), AC input
current, transfer switch; the batteries' depth of discharge and cycle life. Section 6 asks for the ones the
checks need.

---

## 1. Field mapping, column by column

### 1.1 Panels (category Solar Panel)

| Sheet column | Item field today (`catalog.py:21-49`, `models.py:122-158`) | Rule |
|---|---|---|
| BRAND | none (`supplier` is the dealer: IAN Solar, One Point, Blue Carbon, not the maker) | Stored on the specs row (section 2) as `brand`; the tie-breaker in matching. Not an Item field. |
| Model / Capacity | none; the match key | Stored as `model` and `model_norm` on the specs row. |
| PMAX | `rating` with `rating_unit` "W" | "585W", "585 W" → 585. Fills only when the item's rating is blank; when both exist and differ by more than 0.5 % an import notice says so and the item's rating stands (it is the price-per-watt base and the kWp base; `catalog.panel_candidates` at `catalog.py:159-167` needs it). All 14 rows agree with their items today. |
| VMP | `vmp_v` (V) | "40.50 V" → 40.5. A leading "~" (the 670 W row, sheet row 13: "~42.10 V", "~15.92 A", "~49.50 V", "~16.90 A") parses to the number and flags the row `approximate` with a notice "figure marked approximate on the datasheet; verify before the plans are sealed". |
| IMP | `imp_a` (A) | as VMP. |
| VOC | `voc_v` (V) | as VMP. |
| ISC | `isc_a` (A) | as VMP. |
| Max DC System Voltage | **none today → new `max_system_voltage_v` (V)** | "1500V DC", "1500 V DC" → 1500. Two figures with a slash (row 4, the 100 W panel: "600V DC / 1000V DC") → the lower (600) is stored and the row is flagged "two system-voltage ratings on the sheet; the lower is used; verify which applies to the unit sold". The lower bound is the conservative one for the string check (3.1). |
| (absent) | `temp_coeff_voc_pct`, `temp_coeff_isc_pct` | stay blank; section 6.5 proposes the defaults and the warning. |

### 1.2 Inverters (category Inverter; the Solis "Commercial ESS" row goes to All-in-one System)

| Sheet column | Item field | Rule |
|---|---|---|
| TYPES OF INVERTER | **new `inverter_type`** (text: `grid_tie`, `hybrid`, `off_grid`, `charge_controller`, `ess_set`; blank = unknown) and **new `phase`** (1 or 3; blank = unknown) | Mapping in 1.4. The type also feeds `grid_interactive` and `is_hybrid_inverter` (1.4). |
| MODEL | the match key | as panels. |
| BRAND | specs row `brand` | as panels. |
| Details / specs: the kW | `rating` with `rating_unit` "kW" | first number followed by kW/Kw/KW → "8 kW" 8, "0.48 Kw-12V" 0.48, "1.2KW-12V" 1.2, "13KW-720V" 13, "12 kW; List says '12W' - typo for 12kW" 12 (the kW match comes first; "12W" is never read as a rating). "Commercial" (the ESS set) → no kW, no notice (the item's rating is kWh). Fill-when-blank, notice on a difference, as for Pmax. The 3 One Solar charge-controller items (OP-INV-001..003) have no rating today; the sheet's 0.48–4.80 kW would fill them — see 6.7 before that happens, since one item stands for three sheet rows. |
| Details: "MPPT 18/36/36A" (Deye hybrids, sheet 1 rows 16–21) | `mppt_count` (existing) = the number of figures (3 or 2); `mppt_max_a` (existing, one figure) = the **smallest** of them; **new `mppt_currents_a`** (text, "18/36/36") for the per-input check (3.4) | Today `electrical_from_remarks` (`catalog.py:118-122`) reads none of these: its pattern wants "N MPPT" or "MPPT NA" and the slash defeats both, so the six Deye 1P hybrids (OP-INV-017..022) carry no MPPT data. The smallest figure is the conservative single value because every input must hold its own strings. |
| Details: "LV battery", "HV battery" | **new `battery_class`** (text `LV`, `HV`, `none`; blank = unknown). On an inverter: the class of its battery port | "LV battery" → LV, "HV battery" → HV; "N/A (No Battery Input)" in the Max Charge Voltage column → `none`; a charge-controller or off-grid row with a max charge voltage → the class from that voltage (≤ 16 V → 12 V class, ≤ 32 V → 24 V, ≤ 64 V → 48 V, all three LV; above → HV). |
| Details: the figure after the dash on the One Solar, Blue Carbon and Felicity rows ("-12V", "-48V", "-230V", "-380V", "-720V") | not stored as a field | On the One Solar and Blue Carbon rows it reads as the battery class (12/24/48 V) and is cross-checked against the max charge voltage (6.8 lists the two Blue Carbon rows where they disagree). On the Felicity rows it cannot be the battery class (230 V, 380 V, 720 V): left in the raw text, asked in 6.8. |
| Max Charge Voltage | **new `charge_v_max`** (V). On an inverter: the highest voltage its battery port charges to or accepts | "60V" 60, "58.4 V" 58.4, "1,000V" 1000 (comma stripped), "936V" 936, "14.6V" 14.6. "N/A (No Battery Input)" → blank, `battery_class = none`, no notice (a fact, not a gap). A range: narrower than 5 V ("58.4V–60V", Felicity 3P rows 16–22) → the **lower** figure (the conservative maximum; the pair kept in the notes), 5 V or wider ("40 – 60 V" with an en dash, Solis sheet rows 5–9; "40-60V", rows 35 and 38) → the **upper** figure as the maximum and the lower kept in the notes as the window's low end (not a field: no check uses it yet). Every range raises a notice. "Varies by BMS / Up to 800V" (Felicity rows 23–27) → 800 with the notice "varies by BMS; verify per battery". |
| Recommended Discharge Current | `battery_max_a` (existing: "inverters: maximum battery charge/discharge current", `models.py:150`). After this import it means **the inverter's recommended continuous discharge current from the battery** | "250A" 250, "135 A" 135. "240A*" (Deye sheet row 26) and "Up to 290A*" (Solis row 35) → 240 / 290 with the flag `asterisk` and the notice "marked with an asterisk on the sheet; the condition is not on the sheet; verify". "80A + 80A" (Deye rows 22, 24), "50A + 50A" (rows 23, 27), "100A + 100A", "70A + 70A" (Solis rows 32–34, 36), "50A + 50A (Dual Input)" (Felicity rows 23–27) → the per-input figure (80, 50, 100, 70) in `battery_max_a` and **new `battery_inputs`** = 2 (int, default 1). "NO DISCHARGE OUTPUT" (charge controllers) → blank, no notice. "N/A" → blank, no notice on a no-battery-input row, a notice otherwise. |
| Max Recommended Charge Current | **new `charge_a_max`** (A). On an inverter: the most it will push into the battery | as above for amps. "Verify" (One Solar sheet row 16, the 1 kW 12 V wall unit) → blank + notice "marked Verify on the sheet". **A kW figure in this column** (Felicity rows 16–27: "13kW", "32kW", "28.8kW", "24kW", "22.4kW", "18kW", "15kW", "80kW", "64kW", "48kW", "47.84kW", "40kW") → **blank**, raw text kept, notice "a kW figure in the charge-current column; asked of the owner (6.3)". Never converted to amps: the sheet does not say at which voltage. |

### 1.3 Batteries (category Battery)

| Sheet column | Item field | Rule |
|---|---|---|
| LV/HV (sheets 1–2, the unlabelled column; sheet 3: the class text "12V / 24V batteries", "48V low-voltage batteries", "High-voltage batteries") | `battery_class` (the same new column as the inverter's; on a battery: its own class) | "LOW VOLTAGE" / "12V / 24V" / "48V low-voltage" → LV; "HIGH VOLTAGE" / "High-voltage" → HV. Cross-checked against the nominal voltage (6.8: one Felicity row typed HIGH VOLTAGE carries 51.2 V). |
| BATTERY TYPE (chemistry: "LIFEPO4BATTERY PACK", "LIFEPO4BATTERY") | specs row only (`chemistry`) | Only LiFePO4 appears; no Item field until a second chemistry does. |
| MODEL, BRAND | match key, tie-breaker | as above. Brand "JK (One Solar)" keeps the parenthesis in the raw text; the maker is JK. |
| Nominal Voltage / Voltage; sheet 3: the "V" figure in Details | **new `nominal_v`** (V) | "51.2V" 51.2, "12 V" 12, "48 V" 48 (the Pylontech 100 Ah unit says 48, not 51.2: stored as typed). Deye HV rows (sheet 3 rows 17–20), the Pylontech per-kWh row (row 12) and the Solis 16 kWh row (row 31) carry no voltage → blank, notice "no nominal voltage on the sheet". |
| Capacity; sheet 3: the "Ah" figure | **new `capacity_ah`** (Ah) | "200Ah" 200, "314 Ah" 314. Deye HV rows: the module's Ah (100, 314) is stored as typed with the notice that the pack is a series stack (the model text says 8×, 12× or 16×). |
| Energy Capacity / Energy Rating; sheet 3: the first "kWh" figure | `rating` with `rating_unit` "kWh" | "10.24 kWh" 10.24, "3.83kWh" 3.83, "16.076 kWh" 16.076. Sheet 3 takes the first kWh figure in Details and ignores a second one marked "~" ("16 kWh; ... ~16.1 kWh" → 16). Fill-when-blank, notice on a difference above 2 %: FS-BAT-002 (item 10 kWh, sheet 10.24), FS-BAT-003 (15 vs 15.36), FS-BAT-004 (25 vs 25.60) get the notice; the item's rating stands (it sets `battery_units = ceil(kWh / rating)`, `boq.py:376`, and the proposal's kWh line). |
| MAX CHARGE VOLTAGE | `charge_v_max` (the same new column; on a battery: its ceiling) | "60V" 60, "57.6V" 57.6, "921.6V" 921.6. A range ("44.8-57.6V", "48-57.6", "185.6-230V", "359-460V", "22.4-28.8V", "11.2-14.4V") → the **upper** figure; the lower is kept in the notes as the discharge floor (assumption: on a LiFePO4 pack the lower figure of a voltage range is the cut-off; no check uses it). Notice on every range. |
| MAX DISCHARGE CURRENT | `continuous_a` (existing). After this import `continuous_a` means **the battery's maximum continuous discharge current (the BMS limit)**, the figure the hard bank check reads | "120A" 120. A figure above 1 C (the amps over the Ah) is **held**: stored on the specs row with the notice "above 1 C; verify it is a continuous rating, not a peak" and applied to the item only on the owner's confirmation, because applying it could lift a hard block. Five rows: the Felicity base-model 100 Ah row (sheet 2 row 5: 150 A, 1.5 C, while its three variant rows say 100 A), the HIGH VOLTAGE-typed 100 Ah row (row 14: 150 A) and three 100 Ah rows of another Felicity series at 120 A (1.2 C); only the first is a priced item (FS-BAT-001; 3.5, 6.8). |
| RECOMMENDED DISCHARGE CURRENT | **new `discharge_a_recommended`** (A) | "100A" 100; "100A*" (Pylontech 12 V, sheet 3 row 10) → 100 + `asterisk` notice. Note for the owner: on every Felicity row this column is exactly Ah ÷ 2 and the charge column Ah ÷ 5, so they read as a 0.5 C / 0.2 C rule, not a datasheet figure (6.8). |
| MAX RECOMMENDED CHARGE CURRENT | `charge_a_max` (the same new column; on a battery: the most it accepts) | "40A" 40, "62.8A" 62.8, "29.6A standard" (sheet 3 row 12) → 29.6 with the word kept in the notes. |

### 1.4 The type column → `grid_interactive`, `is_hybrid_inverter`, the owner's off-grid kind

Today `is_hybrid_inverter` is a name test (`catalog.py:51-54`: "hybrid" or "off-grid" in the NAME) and
`grid_interactive` a name-and-remark inference (`catalog.py:71-95`). With `inverter_type` on file the property
reads the field first and falls back to the name when the field is blank:

| Type as typed | `inverter_type` | `phase` | `is_hybrid_inverter` | `grid_interactive` (fills only when the item's flag is None; see 2.4) | Offered on the owner's kinds |
|---|---|---|---|---|---|
| "Grid-tie 1P", "Grid-tie 3P" | grid_tie | 1 / 3 | False (no battery port) | True (export is the unit's purpose; the certificate warning `inverter_certificate_missing` still fires until Certifications is typed) | none today: `sizing.py:3-7` says every system is a hybrid; 6.9 asks whether net-metering-without-battery jobs may take a grid-tie unit |
| "Hybrid 1P", "Hybrid 3P", "Hybrid" | hybrid | 1 / 3 / blank | True | True (the current name rule: a hybrid may export; certificate still to be confirmed) | net_metering, combination, off_grid |
| "Off-grid", "OFF GRID" | off_grid | from Details ("230V" → 1), else blank | True (the app's off-grid kind is a no-export hybrid with the grid as backup) | False | off_grid only |
| "Off-grid/Grid-tie" (Blue Carbon rows 5–6) | hybrid | blank | True | None (two modes named, like "(on/off-grid)" today → unknown → the certificate warning) | all kinds, warned |
| "Charge controllers (MPPT)" | charge_controller | — | False | False | never (today they are out only because `rating` is blank, `boq.py:111`; the type makes it explicit) |
| "Commercial ESS (inverter + battery set)" | ess_set | 3 (Details "Commercial"; the model text says 125 kW) | n/a (category All-in-one System) | None | excluded by the 3P/HV words (`config.py:250`) as today |

Three One Solar wall-type units (OP-INV-029, -030, -032; names without "hybrid" or "off-grid", the word is in
the spec) are not hybrids today and never selectable; the sheet types them "Off-grid", so they enter the
off-grid pool after the import. The owner should know (6.9).

Phase also from Details when the type lacks it: "380V", "380-400V", "400V", "440-480V", "480V" → 3;
"220-230V" on a "Hybrid 3P" row stays 3 (the type wins). The `inverter_exclude_words` list (`config.py:250`:
"3P", "3-phase", "high-voltage", "HV") keeps working on names; `phase == 3` and `battery_class == "HV"`
become the second test so a unit whose name hides the phase is still excluded. S.

### 1.5 Every irregular cell and its fate

| Cell text (sheet, row) | Parsed as | Notice the owner sees |
|---|---|---|
| "600V DC / 1000V DC" (panels, row 4) | 600 | two ratings; lower used; verify |
| "~42.10 V" and the three other "~" cells (panels, row 13) | 42.1 … | approximate on the sheet; verify |
| "N/A (No Battery Input)" (inverters, every grid-tie row) | blank; `battery_class = none` | none |
| "N/A" in the two current columns of those rows | blank | none |
| "40 – 60 V" with 135/208/190/112/70 A (Solis rows 5–9, grid-tie 1P) | parsed by the range rule (max 60) **but held**: on a row typed grid-tie the three battery figures are stored on the specs row and **not** copied to the item until the owner answers 6.4 | "battery figures on a grid-tie unit; held" |
| "40-60V" (Solis rows 35, 38) | 60, low end 40 in notes | range |
| "58.4V–60V" (Felicity rows 16–22) | 58.4 | narrow range; lower maximum used |
| "Varies by BMS / Up to 800V" (Felicity rows 23–27) | 800 | varies by BMS; verify per battery |
| "1,000V" (Deye rows 22, 24) | 1000 | none |
| "240A*" (Deye row 26), "Up to 290A*" (Solis row 35), "100A*" (batteries sheet 3 row 10) | 240, 290, 100 | asterisk; condition not on the sheet; verify |
| "80A + 80A", "50A + 50A", "100A + 100A", "70A + 70A", "50A + 50A (Dual Input)" | per-input figure, `battery_inputs = 2` | two battery inputs; the circuit rule prices one circuit and says to verify (3.5) |
| "NO DISCHARGE OUTPUT" (12 charge-controller rows) | blank | none |
| "Verify" (One Solar row 16) | blank | marked Verify |
| "13kW" … "40kW" in the amps column (Felicity rows 16–27) | blank, raw kept | kW in a current column; 6.3 |
| "12 kW; List says '12W' - typo for 12kW" (Solis row 27) | 12 kW | none (the text is the owner's own note) |
| "30 kW; … list shows '259,00' - confirm" (Solis row 37) | 30 kW | none |
| "Hybrid 1P LV battery (21A)" (Solis row 26) | nothing from "(21A)" | "21A unexplained"; 6.8 |
| Solis rows 47–53 (model text in the Details column, no type, no model) | skipped | "no model in the model column" |
| "29.6A standard" (batteries sheet 3 row 12) | 29.6 | word kept |
| "3.83kWh" (no space), "16.076 kWh", "~16.1 kWh" | 3.83, 16.076, ignored | none |
| "48 V; 100 Ah; 4.8 kWh" (Pylontech row 11) | 48, 100, 4.8 | passes the Ah–kWh check (48 × 100 / 1000 = 4.8) |
| "1 kWh; 4.74 kWh/module, min 37.92 kWh" (Pylontech row 12) | kWh 1; no V, no Ah | priced per kWh; the stack figures are in the text; check skipped |
| "100 Ah; 40 kWh" and the other three Deye HV rows | Ah, kWh; no V | no nominal voltage; check skipped (the implied 400 V is shown in the notice, never stored) |
| "44.8-57.6V", "48-57.6", "185.6-230V", "359-460V", "22.4-28.8V", "11.2-14.4V" | the upper figure | range; lower kept as the floor |
| Brand "JK (One Solar)" | brand JK | none |
| A model text with a trailing " P" before the suffix (Blue Carbon batteries sheet row 27) | normalised away | none |
| Blue Carbon battery row with 25.6 V, 120 Ah, 3.07 kWh and a 60 V max charge voltage (sheet 1 row 20) | stored as typed | class check fails (24 V pack, 48 V ceiling); 6.8 |
| Felicity battery row typed HIGH VOLTAGE with 51.2 V / 100 Ah / 44.8–57.6 V (sheet 2 row 14) | stored as typed | class disagrees with the voltage; 6.8 |
| Felicity 102.4 V, 50 Ah, 5.12 kWh, 185.6–230 V (sheet 2 row 43) | stored | the Ah–kWh check passes; the ceiling is 2.2× the nominal; 6.8 |

New Item fields proposed in this section: `max_system_voltage_v`, `inverter_type`, `phase`,
`battery_class`, `charge_v_max`, `charge_a_max`, `mppt_currents_a`, `battery_inputs`, `nominal_v`,
`capacity_ah`, `discharge_a_recommended` — **eleven**. Each goes on `Item` (`catalog.py`), `ELECTRICAL_FIELDS`
(`catalog.py:65-68`, so `KEEP_WHEN_BLANK` at `store.py:20` protects it on a workbook re-import),
`ELECTRICAL_HEADERS` (`importer.py:21-39`, so the materials workbook may carry the same columns),
`MaterialItem` (`models.py`; `ensure_material_columns` at `store.py:23-40` adds them to an old database),
`MaterialItemIn` / `MaterialItemPatch` (`schemas.py:434-509`), `types.ts` and the Materials page editor
(`MaterialsPage.tsx:29-97`). M.

---

## 2. How a datasheet row finds its material item

### 2.1 The specs table

A new table `datasheet_specs` (one row per sheet row, never deleted): `category`, `brand` (the column),
`brand_in_model` (the maker named in the model text when it differs: 6.1), `model` as typed, `model_norm`,
`fields` (the parsed figures, JSON), `raw` (every cell as typed), `notices` (JSON), `source_file`,
`source_sheet`, `source_row`, `file_sha256`, `imported_at`, `last_seen_at`, `matched_code` (nullable),
`match_tier` (`exact`, `contains`, `base`, `manual`), `match_note`, `overridden_fields` (JSON list of fields
the owner later typed over on the Materials page), `held` (bool: 1.5's grid-tie battery figures). Keyed by
(`category`, `model_norm`, `brand`): a re-run upserts. M.

### 2.2 Normalisation and the three tiers

`norm(s)` = upper case, every character outside A–Z and 0–9 removed (so hyphens, spaces, dots,
parentheses and slashes vanish: a model typed with a space before its last letter equals the same model typed
without). Before matching, the maker's words are stripped from the front of the panel model texts (the set of
brands on the three sheets plus "Solar": seven panel rows start with the maker's name, and the item names do
not, so "maker + code + watts" must match an item named "code + watts").

The item text searched is the item's `name` **and** its `spec`: the task says the name, but the Blue Carbon
and Felicity items carry the model in the spec column (name "6 kW low-voltage eco-hybrid inverter", spec
begins with the model) while the IAN Solar and One Point items carry it in the name. Both are searched;
the name first.

Tiers, in order, each row taking at most one item and each item at most one row:

1. **exact**: the raw model text occurs in the raw item text (case-insensitive, spaces collapsed) and the
   character after it is the end, a space, a comma, a semicolon, a slash or a parenthesis, not a hyphen,
   letter or digit. Two exact rows for one item (FS-BAT-003's spec names the base model and, in
   parentheses, the brochure variant; both are on the sheet) → the longer model wins and a notice names the
   other. The 25 Deye rows, the 35 Solis rows, the 6 One Solar off-grid rows, the 3 Solar Homes panels and
   most IAN and One Point battery rows are verbatim the item names: exact.
2. **contains**: a one-word model (every inverter and battery row) must **begin** an item token (the
   item's name and spec split on spaces, commas, semicolons, slashes and parentheses; hyphens stay inside a
   token): `norm(token).startswith(norm(model))`, and exactly one item has such a token. A multi-word model
   text (the panel rows after the maker strip) matches as a substring of `norm(name + " " + spec)`, since
   the dealers hyphenate those names differently. The token-start rule exists for one pair on the Blue
   Carbon battery sheet: the plain 48 V 100 Ah row (row 18) is the tail of the smart 100 Ah item's model
   (BC-BAT-002) and must not take it; the smart row with the trailing letter (row 27) does, by tier 3. This
   tier is the "sheet names the base, the item names a suffixed variant" case: the Felicity 6 kW and 8 kW
   off-grid rows against FS-INV-005 and FS-INV-006 (the items' specs add a generation suffix). Matched with
   the notice "the item's spec carries a suffix the sheet row lacks; verify it is the unit sold". More than
   one item contains it (the Blue Carbon base 6.5 kW row against BC-INV-004 and BC-INV-005) → **no match**,
   specs-only, the notice names both codes for a manual link.
3. **base**: the reverse: the item's own model token (the first comma-separated segment of the spec, or the
   name) normalised is a prefix of `norm(model)` and exactly one row extends it: the Felicity IP65 100 Ah and
   314 Ah items (FS-BAT-005, -007) against the sheet rows that add one suffix letter; the Blue Carbon smart
   100 Ah item (BC-BAT-002) against the row with the trailing letter. Two rows extend the same item
   (FS-BAT-006: the sheet has two market variants of its model with different recommended currents, 115 A
   and 100 A) → no match, notice.

Tie-breakers inside a tier: the brand (the sheet's brand, or the maker in the model text, against the item's
name, spec and supplier), then the category must agree with the sheet (panel sheet → Solar Panel; inverter
sheets → Inverter, the ESS row → All-in-one System; battery sheets → Battery). A model that would match an
item of another category is specs-only with a notice.

What does **not** match, so the owner can see it in the report: FS-INV-001 (the sheet's 6 kW 1P hybrid row
is the earlier generation; the item is the later one), FS-INV-003, FS-INV-004 (generation differs),
FS-INV-007, IAN-INV-035, BC-INV-002, -003, -006, -007, -008 (not on the sheets), BC-INV-005 (the sheet row's
two suffix letters are in the other order), BC-BAT-003 and -004 (the sheet's smart rows carry a series letter
the items lack: one letter), FS-BAT-008, -009 (the sheet's HV 100 Ah row names neither the controller nor the
slave module), IAN-BAT-002, -004, -006, OP-BAT-003 (not on the sheets), OP-INV-001..003 (one item for three
sheet rows each: 6.7). Those items keep today's remark inference and the existing "unknown" warnings
(`battery_current_unknown`, `inverter_pass_through_unknown`, `ats_unknown`, `inverter_certificate_unknown`).

### 2.3 A row with no priced item

Stays in `datasheet_specs` with `matched_code` null. The Materials page lists it under its category as
**"datasheet only"** (2.5) with "Link to item…" (a manual match: `match_tier = manual`, applied at once) and
"Add as item" (creates a `MaterialItem` with the owner's code, the datasheet figures, `list_price` 0 and
`active = False`, so the BOQ never prices it at zero; the owner types the price and activates it). A later
materials import that adds an item whose text matches picks the row up automatically (2.6).

### 2.4 Precedence, and why

**Owner's edit on the Materials page > datasheet > materials workbook electrical column > remarks.**

- The datasheet is the maker's figure, typed once per model; the workbook's electrical column is the owner's
  transcription per item, one step removed (and absent from the bundled workbook, `importer.py:19-20`); the
  remark is prose read by regex, two steps removed, and already disagrees with the sheet where both exist
  (the eco-hybrid's remark says battery 135 A, the sheet's discharge figure is 139 A and its charge figure
  135 A; the Felicity 100 Ah remark says continuous 100 A, the sheet's base-model row 150 A).
- The owner's edit sits on top because the app is the master after import (DECISIONS, module 3) and because
  one decision was made in the app, not on a sheet: the eco-hybrid FS-INV-008 is marked grid-interactive on
  the owner's word with the maker (DECISIONS, "The owner's corrections after the engineering batch"); the sheet types it "OFF GRID". So:
  - numeric fields: the datasheet overwrites (except a held figure: 1.5, 1.3), and the import report prints every change as `old → new`
    (the owner reads what moved); a field the owner later types over is listed in `overridden_fields` and
    left alone on the next run;
  - `grid_interactive`: the type fills it **only when the item's flag is None**; a disagreement with a set
    flag is reported ("datasheet type off-grid, item marked grid-interactive: the item stands");
  - `certifications`, `has_transfer_switch`: untouched (no sheet carries them);
  - `rating`: fill-when-blank, notice on a difference (1.1–1.3).
- A later **materials workbook re-import** today writes the remark inference back over every electrical field
  the workbook row produces (`store.py:91-96`: only a None from the workbook is skipped, and
  `electrical_values` at `importer.py:69-92` never returns None for a remark it can read). To keep the
  precedence the datasheet figures are re-applied from `datasheet_specs` at the end of every materials
  import (`persist_import`, `store.py:79-115`, one call after the loop). Without this the eco-hybrid's
  139 A would go back to 135 A on the next price-list import. S, and the test in 5.4 pins it.

### 2.5 The office's view (the Materials page, `MaterialsPage.tsx`)

- The "Electrical" column (`MaterialsPage.tsx:401, 450`) gains a provenance badge: **datasheet** (file and
  date on hover), **remarks**, **typed**, or **none**.
- The editor (`ElectricalFields`, lines 29–97) shows the datasheet's figure greyed beside a field the owner
  overrides, with "reset to datasheet".
- A collapsible block per category, "Datasheet rows without a priced item (N)", with brand, model, the
  key figures and the two actions of 2.3; and a block "Items without a datasheet (N)" that lists 2.2's
  unmatched items so the owner can send the maker's sheet.
- The held Solis figures of 1.5 show with "held: grid-tie unit, battery figures not applied (6.4)".

M for the page.

### 2.6 When the materials workbook changes

Items are matched by code on import (`store.py:84-99`); a code's name or spec may change. After each
materials import the matcher runs again over unmatched specs only (a matched row keeps its item unless
the item is gone), so a renamed item is picked up and an existing match is never silently moved.

---

## 3. The rules the figures unlock

Settings they need (one new block `PricingConfig.string_design`, beside `wiring`, under Pricing settings ›
"String design"; every value in `settings_version`, `config.py:437-441`, so a change flags quoted jobs):

| Setting | Default | Why this default |
|---|---|---|
| `design_cold_c` | 14 °C | **Assumption.** The PVGIS TMY (ERA5, typical months 2005–2023) in `data/pvgis/cells` gives these hourly air-temperature minima and maxima: the cell that holds Pila and Calamba (14.25 N, 121.25 E, 2 m): 21.9 / 34.1 °C; the cell that holds Tanauan, Lipa, Santo Tomas and San Pablo (14.00, 121.25, 556 m): 19.4 / 33.2; the cell that holds Batangas City (13.75, 121.00, sea level): 21.2 / 32.2; the neighbouring cells 14.25/121.50: 19.4 / 30.5, 14.00/121.00: 19.5 / 33.5, 13.75/121.25: 19.3 / 32.0, 14.00/121.50: 20.2 / 33.3. A TMY is a typical year, not a record, so the lowest of these (19.3) is floored and a 5 °C margin taken: 14 °C. The owner replaces it with the PAGASA record low of the station nearest the job when in hand (verify). |
| `cold_margin_c` | 5 °C | assumption; the gap between a typical-year minimum and a record low |
| `design_hot_cell_c` | 70 °C | **Assumption.** The TMY maxima above (30.5–34.1 °C) plus the module's rise at 1 kW/m² (the site's measured rise when the k readings have a plausible one, `compute.py:171-174`, else the Faiman model) give roughly 60–65 °C; 70 is the conservative envelope. |
| `temp_coeff_voc_default_pct` | −0.30 %/°C | **Assumption**, 6.5: a conservative envelope for the crystalline-silicon families on the sheet; the maker's figure replaces it and the warning says a default was used |
| `temp_coeff_pmax_default_pct` | −0.35 %/°C | assumption, used for Vmp (6.5) |
| `temp_coeff_isc_default_pct` | +0.05 %/°C | assumption; informational only (3.3) |
| `isc_irradiance_factor` | 1.25 | the PV-circuit sizing rule of the PEC's solar PV article (the NEC 690.8 equivalent: verify the clause in the current edition) |
| `dc_breaker_sizes_a` | 16, 20, 25, 32, 40, 50, 63 | the standard DC MCB ratings the suppliers list (verify against the price lists; like `ac_breaker_sizes_a`, `config.py:203`) |

Per project (`doc.pricing`, `schemas.py:143-146`): `design_cold_c`, `design_hot_cell_c` overrides, beside
the existing `strings_override` and `max_panels_per_string`. Per project the engine takes
T_cold = min(setting, floor(TMY minimum of the project's cell) − margin) and
T_hot = max(setting, TMY maximum + rise × 1 kW/m²); `compute.py` already holds the TMY (`tmy["temp_air"]`)
and puts the two figures in `results["site"]` for the string table. The website estimate has no project and
uses the settings alone (4.5). S for the settings; S for the two figures in compute.

### 3.1 String count from Voc at the cold temperature (replaces the fixed `max_panels_per_string` when the figures exist)

Inputs: `voc_v`, `vmp_v`, `temp_coeff_voc_pct` (or the default), `max_system_voltage_v` from the panel;
`max_pv_voltage_v`, `mppt_min_v`, `mppt_max_v`, `mppt_count` from the inverter; T_cold, T_hot.

Form (IEC 60891's linear temperature term, which IEC 62548 applies to array design; verify the editions):

    Voc_cold = Voc × (1 + β_Voc / 100 × (T_cold − 25))
    Vmp_cold = Vmp × (1 + β_Pmax / 100 × (T_cold − 25))
    Vmp_hot  = Vmp × (1 + β_Pmax / 100 × (T_hot − 25))
    V_limit  = min(inverter max_pv_voltage_v, panel max_system_voltage_v)
    n_max    = floor(V_limit / Voc_cold), also floor(mppt_max_v / Vmp_cold) when the window is on file
    n_min    = ceil(mppt_min_v / Vmp_hot) when the window is on file, else 1
    per_string_cap = min(n_max, roles.max_panels_per_string)      # the setting becomes the owner's cap
    strings  = strings_override or ceil(panels / per_string_cap)
    per_string = ceil(panels / strings)                          # as boq.py:416; must be ≥ n_min

STC Voc is the base (at lower irradiance Voc is lower, so STC is the conservative side); the irradiance
term of IEC 60891 is dropped (assumption). The PEC's PV article has the maximum-voltage rule and, for a
module without a coefficient, a table of correction factors by lowest ambient temperature (the NEC Table
690.7(A) equivalent): once the owner has the edition, the app can print the table's factor beside the
computed one; until then the default coefficient stands in (verify).

Hand-worked (the 630 W row whose model text names JA Solar, panel sheet row 8: Voc 48.90 V, Vmp 40.70 V; an
inverter whose remark gives "500 Voc", as FS-INV-005 and BC-INV-003 do, `catalog.py:122`; T_cold 14 °C,
β_Voc −0.30): Voc_cold = 48.90 × (1 + 0.0030 × 11) = 48.90 × 1.033 = 50.51 V; n_max = floor(500 / 50.51) =
floor(9.90) = **9**. The current rule puts 10 in a string (`config.py:244`): 10 × 50.51 = 505.1 V, over the
unit's 500 V. On the owner's own 630 W bifacial (row 17, Voc 55.54 V): Voc_cold = 57.37 V, n_max = **8**;
ten in a string is 573.7 V cold and 555.4 V at STC. On the 585 W monofacial the quick estimate uses
(BC-PNL-001, row 14, Voc 53.08 V): 54.83 V cold, n_max = **9**. So on every 580–720 W panel on the sheet
but one the fixed ten exceeds a 500 V input (the exception is the 620 W row, Voc 48.37 V: 49.97 V cold, ten
give 499.7 V, 0.3 V to spare); the rule-of-thumb 10 × 42 V = 420 V on the schedule (`plans_pdf.py:543`)
hides it. At T_cold 16 °C (Pila's own cell without the dataset-wide floor) the 630 W
JA-made panel gives 50.22 V and still n_max = 9.

Vmp_hot for the same panel at 70 °C, β_Pmax −0.35: 40.70 × (1 − 0.0035 × 45) = 40.70 × 0.8425 = 34.29 V;
n_min = ceil(mppt_min_v / 34.29) once the window is on file (no sheet has it: 6.6).

Warnings:
- `string_voltage_cold` — **hard, blocks**: "A string of {n} × {panel} reaches {V} V at {T_cold} °C
  (Voc {voc} V, coefficient {β} %/°C{, a default}), above the inverter's {limit} V maximum PV voltage
  {or the panel's {max_system} V system voltage}. The generator uses {n_max} per string; this job forces
  {n} (strings override or panels per string). The proposal, roof check, card and plans are held." Blocks
  because an over-voltage input is equipment damage and a failed inspection. Fires only when an override
  forces it; the generator itself never produces it.
- `string_voltage_hot` — **ordinary**: "{n} panels per string give {V} V at {T_hot} °C, below the MPPT
  window's low end {mppt_min} V: the inverter stops tracking on hot afternoons. Use at least {n_min} per
  string or another inverter." Yield, not safety.
- `string_rule_fallback` — **ordinary**: "{panel} has no Voc on file / {inverter} has no maximum PV voltage
  on file: the strings follow the fixed rule of {max_panels_per_string} per string. Type the datasheet
  figures (Materials page) before the plans are sealed." Replaces the silent rule today.
- `temp_coeff_default` — **ordinary**: "The string design used the default temperature coefficient
  {β} %/°C for Voc (the panel has none on file). Type the datasheet's figure on the Materials page."
Effort M (`boq.py:414-421`, the choices block at `boq.py:584-592`, the plans' DC rows at
`plans_pdf.py:539-550`).

### 3.2 String current, PV cable and DC breaker

    I_string   = Imp                                       # replaces panel W / 42 V, boq.py:418
    V_string   = per_string × Vmp                          # replaces per_string × 42, boq.py:419; the drop base
    I_design   = Isc × isc_irradiance_factor (1.25)        # the PEC PV-article circuit current (verify)
    I_cond     = I_design × continuous_factor (1.25)       # = 1.5625 × Isc: conductor ampacity before derating
    OCPD       = next size in dc_breaker_sizes_a ≥ I_design × 1.25 = I_cond; and ≤ the module's maximum
                 series fuse rating when on file (not on the sheet: 6.6)

The PV cable gauge is the smallest in `pv_cable_ampacity` (`config.py:200`) at or above I_cond with the
drop at I_string over the run within `dc_drop_limit`: `pick_gauge` (`boq.py:149-166`) already does the
drop; it is called with I_string for the drop and `min_ampacity = I_cond`. The temperature term on Isc
(+0.05 %/°C: 16.18 × (1 + 0.0005 × 45) = 16.54 A) is not stacked on the 1.25: the code method is
irradiance × continuous, and stacking would double-count. Derating for conduit fill and roof temperature
stays "to be completed by the signing engineer" as the plans say today (`plans_pdf.py`, TO_COMPLETE).

Hand-worked (630 W, row 8: Imp 15.48 A, Isc 16.18 A): I_string 15.48 A (the rule gives 630 / 42 =
15.0 A today); I_design = 20.23 A; I_cond = 25.28 A → 4 mm² PV cable (40 A in the table) holds; OCPD ≥
25.28 A → **32 A**. The 720 W panel (row 9, Isc 18.59 A): 29.05 A → 32 A. The 630 W bifacial (row 17,
Isc 15.15 A): 23.67 A → 25 A. V_string for 9 × 630 W = 366.3 V (the rule prints 420 V).

The DC breaker today is the role item IAN-PRT-009 at any rating (`boq.py:514`; `config.py:222`), never
checked. With the figures: pick `_by_amps` (`boq.py:174-182`) on a "DC BREAKER" pattern like the battery
breaker, and warn `dc_breaker_rating` — **ordinary** — when the role item's rating is below I_cond ("the
{x} A DC breaker is below the {I_cond} A the string needs (1.25 × 1.25 × Isc {isc} A)") or above the module's
fuse rating once that is on file ("above the panel's maximum series fuse rating {f} A: the panel is not
protected on a back-feed"; hard then, verify). M.

### 3.3 Isc with 1.25 and 1.56

Stated on the schedule as two lines so the PEE sees both: "PV circuit current 1.25 × Isc = {I_design} A"
and "conductor and OCPD at 1.25 × that = {I_cond} A (1.56 × Isc)". The 1.56 is never a separate setting; it is
the product of the two factors above. S (`plans_pdf.py:539-550`).

### 3.4 Parallel strings per MPPT against `mppt_max_a` (and the per-input figures)

Assignment: inputs sorted by their current rating, largest first (`mppt_currents_a` when on file, else
`mppt_max_a` repeated `mppt_count` times); strings go one per input, then the extra strings double up on the
largest inputs. For each input with p strings: p × Imp ≤ I_input, else `mppt_current` — **ordinary**:
"{p} strings in parallel on MPPT {k} draw {p × Imp} A at Imp, above the input's {I_input} A: the inverter
clips or the input overheats. Use {more inputs / fewer panels / another unit}; verify the input's
short-circuit rating (not on the sheet)." Strings in parallel on one input must be the same length (the
generator's uniform `per_string` already is; a `strings_override` that leaves unequal strings on one input
adds the sentence "unequal strings on one input mismatch at Vmp"). DC SPD count (`boq.py:515-516`) now
reads the Deye MPPT counts the remarks never gave.

Hand-worked: a 6 kW 1P hybrid with "MPPT 18/18A" (Deye sheet row 17) and 630 W panels (Imp 15.48 A): one
string per input (15.48 ≤ 18); a 20-panel job at 9 per string is 3 strings on 2 inputs → one input takes
2 × 15.48 = 30.96 A > 18 A → warning. The 12 kW unit with "18/36/36A" (row 16): 2 strings on a 36 A input
(30.96 ≤ 36), fine. M.

### 3.5 The battery circuit

    I_inv      = max(inverter battery_max_a, inverter charge_a_max)   # the same conductor carries both directions
    I_cable    = min(I_inv, units_bat × battery continuous_a)       # "the lower governs the cable"
    breaker    ≥ 1.25 × I_inv   (next "BATTERY BREAKER" at or above, as today: boq.py:485-486)
    cable      : ampacity ≥ breaker (as today: boq.py:489-491)
    bank check : units_bat × continuous_a ≥ I_inv × units_inv       # hard, blocks, as today: boq.py:184-207
    soft check : units_bat × discharge_a_recommended ≥ I_inv × units_inv, else ordinary warning

Why the charge figure enters I_inv: on the Felicity 1P hybrids the charge column is the larger (sheet 5
rows 12–15: 109/120, 130/135, 165/190, 174/190 A), and the cable between inverter and battery carries the
charge current as surely as the discharge. On the Deye rows the two are equal. The "lower governs the cable"
clause can only lower the cable below the inverter's figure when the bank's rating is below it, and that
design is already blocked by the bank check; in a passing design I_cable = I_inv. The breaker stays at 1.25
× the inverter's figure, the cable at or above the breaker, as DECISIONS "Round 3, batch 1" settled. A unit
with `battery_inputs = 2` prices one circuit and warns "two battery inputs on the datasheet: the second
circuit is not priced; verify" (ordinary) — every such unit is 3P/HV and excluded from residential jobs.
The battery voltage for the kW fallback (`boq.py:358`, 51.2 V from `config.py:194`) becomes the chosen
battery's `nominal_v` when on file.

Hand-worked: the eco-hybrid FS-INV-008 matches the Felicity 6 kW off-grid row (sheet 5 row 9): discharge
139 A, charge 135 A → I_inv = 139 A (was 135 from the remark) → breaker ≥ 173.75 A (was 168.75, the figure
`test_design_rules.py:176` pins) → the "BATTERY BREAKER" at or above it is the same 250 A unit the test
expects, so the 70 mm² lug pairs stand; only the BOM note moves (139 A). FS-INV-002 (the 8 kW 1P hybrid,
row 15): I_inv = max(174, 190) = 190 A, as the remark already said. Bank: FS-BAT-003 (the TG2 variant row:
160 A max, 150 A recommended) against 139 A → passes both; the 230 Ah IP65 row with 115 A recommended
against 139 A → passes the hard check (150 A max), gets the soft one (that row is one of the two market
variants of FS-BAT-006's model, which is why the item itself stays unmatched until the owner links it). **Changed outcome to watch**: the
Felicity 100 Ah wall/floor item (FS-BAT-001) carries "continuous 100 A" from its remark and fails the hard
check against the eco-hybrid today; the sheet's base-model row says 150 A, which would pass it. Its three
variant rows say 100 A. Held by the above-1 C rule of 1.3 until 6.8 is answered: the importer applies 150
only after the owner confirms.

Warning `battery_discharge_recommended` — **ordinary**: "{units} × {battery} deliver {x} A at the recommended
continuous rate and the inverter draws up to {I_inv} A: within the BMS maximum ({max} A) but above the
recommended rate; the battery runs warm at full power. Verify the warranty condition with the maker."

### 3.6 The charge check

    accept = units_bat × battery charge_a_max
    if inverter charge_a_max > accept: warning battery_charge_current (ordinary)

"The inverter can charge at {inv} A and the bank accepts {accept} A ({units} × {per unit} A): set the
inverter's maximum charge current to {accept} A, or the BMS limits or trips. {Units needed for the full
rate: n}." Ordinary because the charge current is an inverter setting; the commissioning report (plan
item 27) should print the value to set. Hand-worked: eco-hybrid 135 A against FS-BAT-003 (60 A per unit)
→ set 60 A, or 3 units for the full 135 A (180 A); a 12 kW Deye 1P hybrid (250 A) against a 314 Ah pack at
62.8 A → set 62.8 A, or 4 units. S.

### 3.7 The voltage match

    class(V) = 12 if V ≤ 16, 24 if V ≤ 32, 48 if V ≤ 64, else HV      # applied to nominal_v and to charge_v_max
    V1: class(battery nominal_v) == class(inverter charge_v_max), and battery_class == inverter battery_class
        when both are on file  → else battery_voltage_class, hard, blocks
    V2: inverter charge_v_max ≤ battery charge_v_max → else battery_charge_voltage, ordinary

V1 blocks: an LV pack on an HV port (or the reverse, or a 24 V pack on a 48 V port) is a wrong purchase and
a unit that will not start. V2 is ordinary: "the inverter charges to {inv} V and the battery's ceiling is
{bat} V: set the charge voltage to {bat} V or lower (a closed-loop BMS connection normally does this;
verify)". The window's low end is on no sheet, so nothing is checked against it. Hand-worked: a Deye 1P
hybrid (60 V) with a Felicity 51.2 V pack (ceiling 57.6 V) → V1 passes (both 48 V class), V2 warns; a Blue
Carbon 48 V inverter (58.4 V) with a Blue Carbon pack (60 V) → both pass; BC-BAT-001 (25.6 V) on any 48 V
port → V1 blocks (today it is only kept out by the "24V"/"25.6V" exclude words, `config.py:251`). S.

### 3.8 Ah-to-kWh consistency

    kWh_calc = nominal_v × capacity_ah / 1000
    if |kWh_calc − rating| / rating > 0.02: notice at import and, on a job that prices the unit,
    warning battery_ah_kwh (ordinary): "{V} V × {Ah} Ah = {calc} kWh against the {rating} kWh on file ({d} %): one of the three figures is wrong; verify"

Every row on the three sheets with all three figures passes: 25.6 × 120 / 1000 = 3.072 against 3.07
(0.07 %); 12.8 × 300 = 3.84 against 3.83 (0.26 %); 51.2 × 314 = 16.077 against 16 (0.48 %), 16.08 and
16.076; 48 × 100 = 4.8; 102.4 × 50 = 5.12; 51.2 × 587 = 30.05 against 30. The check earns its keep on the
next sheet. Rows without a voltage (Deye HV, the Pylontech per-kWh row, the Solis 16 kWh row) are skipped
with "no nominal voltage on the sheet". S.

### 3.9 `continuous_a` after this

The battery's **maximum continuous discharge current, the BMS limit**: the sheet's MAX DISCHARGE CURRENT.
It is the figure the hard bank check and `battery_current_ok` (`boq.py:124-129`) read, and the figure the
owner's remarks called "continuous" (five of seven remark figures equal the sheet's maximum on the matched
rows). The recommended rate is the new soft field. A maximum above 1 C is flagged at import as "verify it is
a continuous rating, not a peak" and held (1.3), because a 1.5 C "maximum" (the Felicity base 100 Ah row)
would pass a 6 kW inverter on a 5 kWh pack.

---

## 4. What changes in each output

### 4.1 The BOQ (`boq.py`, `job.py:136-146`)

- Strings: `choices.strings` and `panels_per_string` from 3.1 when the panel has Voc and the inverter a
  maximum PV voltage; else the fixed rule with `string_rule_fallback`. New block `choices.string_design`:
  `t_cold_c`, `t_hot_c`, `voc_cold_v`, `vmp_hot_v`, `v_limit_v` and which of the two limits binds, `n_max`,
  `n_min`, `coefficients` with a `default` flag each, `per_mppt` (input, strings, amps at Imp, limit). On
  the 10-panel sample roof (`test_boq.py:23-30`: 8 panels, one string today) nothing moves while the figures
  are absent; with the fixture of 5.1 loaded and a 500 V inverter, a 10 × 630 W job goes from 1 string to
  2 (5 + 5): +1 DC breaker, +2 MC4 pairs, +25 m red and +25 m black PV cable, DC SPDs min(strings, inputs).
- String current `Imp`, string voltage `per_string × Vmp`, the PV cable from 1.56 × Isc with the drop at
  Imp, the DC breaker by rating (3.2); the BOM notes say "datasheet" where the figure is one and "rule"
  where it is not.
- Battery: `battery_current_a` = I_inv of 3.5 (the eco-hybrid: 139 A); `battery_breaker_min_a` 1.25 × it;
  the bank check on the sheet's maxima; new `choices.battery_charge` (inverter A, bank accepts A, units for
  the full rate), `choices.battery_voltage_match` (classes, ceilings, ok), `choices.battery_ah_kwh`
  (calc, rating, %), and `discharge_a_recommended` beside `continuous_a` in `battery_options`
  (`boq.py:383-388`).
- The BOM export (`api/assessments.py:439-503`) carries the same notes; nothing else in the export moves.

### 4.2 The plan set (`plans_pdf.py`)

- Cover models table (lines 403–417): the panel row adds "max system voltage {V}"; the inverter row prints
  the type and phase, the battery port class, "battery {V} V max, {A} A discharge, {A} A charge" from the
  datasheet, the per-input MPPT currents; the battery row prints "{V} V, {Ah} Ah, {kWh} kWh; max
  {A} A, recommended {A} A, charge {A} A; ceiling {V} V". Each figure says "datasheet ({file}, {date})" or
  stays BLANK; nothing is derived on the sheet.
- Equipment and circuit schedule (lines 517–598): the DC rows "String current, Imp" and "String voltage at
  Vmp" (lines 542–543) print the datasheet figures with T_cold and T_hot and the coefficients (and "default"
  when they are), and a new **string table** row block: per string count n, Voc_cold, Vmp_hot, the limits,
  the margin in volts and percent, the input it sits on and its amps; the DC breaker row prints the rating
  check; the battery circuit rows (577–585) print I_inv with "the larger of discharge and charge", the
  charge setting to apply (3.6) and the voltage match (3.7).
- Last sheet "Not yet in this set" (lines 612–630): the string-table entry drops out when the figures are on
  file and the single-line diagram entry names only what is still missing; `panel_missing` (line 614) adds
  `max_system_voltage_v` and the inverter's window.
- Rev. 0 stays; the sheet says "string design on datasheet figures from {file}, {date}".
M.

### 4.3 The warnings the office sees

New codes in `pricing.warnings` (`job.py:184-187` puts the blocking ones in `design_blocked`):
`string_voltage_cold` (hard, blocks), `battery_voltage_class` (hard, blocks), `string_voltage_hot`,
`mppt_current`, `dc_breaker_rating`, `battery_charge_current`, `battery_charge_voltage`,
`battery_discharge_recommended`, `battery_ah_kwh`, `string_rule_fallback`, `temp_coeff_default`,
`battery_inputs_verify`. Existing ones keep their meaning; `battery_current_unknown` fires less often
because the 21 battery items with no continuous current today (BC-BAT-001, -002, eight IAN-BAT and eleven
OP-BAT codes) take the sheet's maximum. Import-time notices (1.5) live in the import report and on the
Materials page, not in a job's warnings.

### 4.4 The proposal, roof check, card, program

Untouched in content: they print quantities, kW, kWh and the certificate line (DECISIONS, "The customer's
story on paper"). They are **refused** by two more blocking codes (4.3), the way `battery_current` refuses
them today (`api` stale-and-blocked rule). The battery kWh the proposal prints is still the item's rating
(1.3).

### 4.5 The quick website estimate

**Not touched**: no change to `core/quick.py`, `api/quick_routes.py`, `public.py` or the site. It calls the
same `generate_boq` (`quick.py:174-176`) with the same catalogue, as a materials price edit reaches it
today, so its price follows the string count only through the DC breaker, connector and cable lines, and it
shows no warnings and no string table; it has no project, so T_cold and T_hot are the settings alone. The
test in 5.4 pins the sample estimate's rounded price (rounded to ₱1,000, `config.py:394`) with and without
the fixture loaded; if it moves, the owner is told the amount in the import report.

---

## 5. The importer, the office's view and the tests

### 5.1 The command

`python -m solarapp.pricing.datasheets <files…> [--dry-run] [--report out.csv] [--apply-held]`
(`backend/solarapp/pricing/datasheets.py`, beside `__main__.py`):

- Opens each file with openpyxl `data_only=True`; detects the workbook kind by the header words of each
  sheet (PMAX and VOC → panels; TYPES OF INVERTER or MODEL + Max Charge Voltage → inverters; Capacity +
  Energy or BATTERY TYPE → batteries; sheet 3's maker sub-headers are header rows and reset the column map),
  never by the file name. The header row is the first row with at least three of the sheet kind's words;
  columns are mapped by `_norm_header` (`importer.py:43-44`, reused) with the alias table extended by the
  sheet's own words ("MIODEL", "Model / Capacity", "Energy Rating", "RECOMMENDED DISCHARGE CURRENT"…) and
  by the two positional rules of section 0.
- Per row: parse (1.1–1.5), upsert the specs row, match (2.2), apply (2.4), and print one line:
  `matched FS-INV-008 <- inverters sheet5 row 9 (exact): battery_max_a 135 -> 139, charge_v_max - -> 58.4,
  charge_a_max - -> 135, inverter_type - -> off_grid, phase - -> 1, battery_class - -> LV; grid_interactive
  kept (item yes, sheet off-grid)`; `specs-only inverters sheet4 row 6 (ambiguous: BC-INV-004, BC-INV-005)`;
  `skipped inverters sheet2 row 47: no model in the model column`; `held inverters sheet2 row 5: battery
  figures on a grid-tie unit (6.4)`. A summary: rows read, matched, specs-only, skipped, held, items
  changed, items untouched, priced projects that use a changed item (they re-price on their next Calculate;
  the materials list is not versioned, DECISIONS "Money, round three", so this is the same follow-up as a
  price edit).
- Re-runnable and never deleting: the same file twice changes nothing (idempotent on `file_sha256` per row);
  a row missing from a later file keeps its specs row with an older `last_seen_at` and a notice.
- Stores `source_file` (the base name), `file_sha256`, `imported_at` per row, and `datasheets_imported_at`
  on the pricing config beside `imported_from` (`config.py:419-420`; excluded from `settings_version` like
  the import stamp, `config.py:434`).
- An owner-only route `POST /api/pricing/datasheets` (multipart, like `/import` at
  `pricing_routes.py:59-88`) and `GET /api/pricing/datasheets?category=` for the page (2.5). M.

### 5.2 Settings view

Pricing settings › "String design": the nine settings of section 3 with their help text ("assumption" where
it is one, "verify" where it depends on the code edition), and a read-only line "TMY extremes at this
project's cell" on the project's System design step. S.

### 5.3 The fixture

`backend/tests/fixtures/datasheets/` with three workbooks cut from the owner's files, every irregular cell
of 1.5 kept, every sheet's layout kept (the panel sheet starting at column O, the unlabelled LV/HV column,
the Felicity sheet's header at row 4, the Solis orphan rows, the sub-headers of battery sheet 3), the six
brand-shifted panel rows, both Felicity variants of the 230 Ah model, the base-and-variant Blue Carbon
6.5 kW rows, the two Felicity off-grid rows whose items carry a suffix, the Felicity 100 Ah base and
variant rows, the three One Solar charge-controller rows that share one item. Each file carries a
`README` line naming the source file and the date it was cut.

### 5.4 The tests

- **Parsing** (`test_datasheets_parse.py`): one case per rule of 1.5, asserting the value, the flag and the
  notice text: 600/1000 → 600; "~" → value + approximate; "1,000V" → 1000; both en-dash and hyphen ranges;
  the 5 V width rule on "58.4V–60V" (→ 58.4) and "40-60V" (→ 60, low end noted); "Varies by BMS / Up to
  800V" → 800; "240A*" and "Up to 290A*" → value + asterisk; "80A + 80A" → 80 and 2 inputs; "NO DISCHARGE
  OUTPUT", "N/A", "N/A (No Battery Input)" → blank with and without a notice; "Verify" → blank + notice; the
  twelve kW-in-amps cells → blank + notice, never a number; "12 kW; List says '12W'…" → 12; "0.48 Kw-12V" →
  0.48; "3.83kWh" → 3.83; "~16.1 kWh" ignored; "29.6A standard" → 29.6; the LV/HV column left of BATTERY
  TYPE; the Deye "MPPT 18/36/36A" → count 3, min 18, text kept; the type table of 1.4 for all nine type
  strings; phase from "380-400V".
- **Matching** (`test_datasheets_match.py`), against the seed workbook's catalogue (`read_workbook(WB)` as
  `test_boq.py:9-14`): the exact tier on a verbatim name; the maker-word strip on the seven panel rows; the
  longer-of-two-exact rule on FS-BAT-003 and -004 (the TG2 variant rows win: 160 A and 250 A, which the
  items' remarks already say); the contains tier on FS-INV-005/-006 with the notice; the ambiguity on the
  Blue Carbon base 6.5 kW row and on FS-BAT-006 → specs-only naming both codes; the token-start rule: the
  plain Blue Carbon 48 V 100 Ah row does not take BC-BAT-002 and the smart row does; the base tier on FS-BAT-005,
  -007, BC-BAT-002; no match on FS-INV-001 (generation), BC-INV-005 (letter order), BC-BAT-003/-004 (series
  letter), FS-BAT-008/-009; the one-item-three-rows case → three specs-only rows naming OP-INV-001; a
  category clash → specs-only; the manual link; the re-run is a no-op; the re-match after a renamed item;
  the materials re-import keeps the datasheet figures (2.4: eco-hybrid stays 139 A after
  `persist_import` of the seed).
- **Precedence**: `grid_interactive` on FS-INV-008 stays True with the conflict reported; a field the owner
  typed over (`overridden_fields`) survives a re-run; `rating` fills only when blank and the 10 vs 10.24 kWh
  notice appears for FS-BAT-002.
- **Checks, hand-worked** (`test_string_design.py`, `test_battery_match.py`), each with the figures of
  section 3 asserted to two decimals: Voc_cold 50.51 V and n_max 9 at 14 °C on a 500 V input, 8 on the
  630 W bifacial, 9 on the 585 W; the forced 10 → `string_voltage_cold` hard and in `design_blocked`;
  Vmp_hot 34.29 V and n_min against a window given in the test; I_design 20.23 A, I_cond 25.28 A, OCPD 32 A,
  4 mm²; 2 × 15.48 = 30.96 A on an 18 A input → `mppt_current`, on a 36 A input none; I_inv 139 A → breaker
  min 173.75 A, the same 250 A breaker and 70 mm² pair as `test_design_rules.py:172-184`; I_inv
  max(174, 190) = 190 on FS-INV-002; the soft recommended check on the 230 Ah IP65 row (115 A) against
  139 A; the charge check 135 A against 60 A (set 60, 3 units for 180); V1 blocks a 25.6 V pack on a 48 V
  port and an LV pack on an HV port; V2 warns at 60 V against 57.6 V and not at 58.4 V against 60 V;
  Ah–kWh: 25.6 × 120 → 0.07 % pass, a hand-built 51.2 × 100 against 6 kWh → 14.7 % warn; the `default`
  flag and `temp_coeff_default` when the coefficient is blank; `string_rule_fallback` when Voc or the
  maximum PV voltage is blank.
- **Unchanged where the figures are absent** (`test_boq.py`, `test_design_rules.py`, `test_pricing_engine.py`
  run as they are): the seed workbook without any datasheet gives the same strings, currents, breaker
  minimum (168.75 A) and the sample job's ₱329,300 (`test_pricing_engine.py:52-77`); the plans PDF's
  "waits on the datasheets" sentences (`plans_pdf.py:623-627`) still print; the quick estimate's rounded
  price with the seed alone is the figure it is today, and with the fixture loaded the test states the
  figure it becomes (4.5).
- **Import report**: a dry run writes the CSV with one line per row and the summary counts; the held Solis
  rows appear as held and are applied only with `--apply-held`.
L in all, across three or four days with the fields and the page.

---

## 6. What to ask the owner

### 6.1 Panel rows whose brand column and model text disagree

Six rows; the brand I would take is the maker named in the model text, because the electrical figures
belong to the maker's module and the dealer's price list (the items) already files them under that maker:

| Panel sheet row | Brand column | Maker in the model text | Watts | Item it matches | Brand taken |
|---|---|---|---|---|---|
| 8 | Trina Solar | JA Solar | 630 | IAN-PNL-004 | JA Solar |
| 9 | Trina Solar | JA Solar | 720 | IAN-PNL-001 | JA Solar |
| 10 | IAN Solar | Trina Solar | 620 | OP-PNL-004 | Trina Solar |
| 11 | JA Solar | Trina Solar | 630 | OP-PNL-005 | Trina Solar |
| 12 | JA Solar | AIKO Solar | 665 | OP-PNL-006 | Aiko |
| 13 | Aiko | IAN Solar | 670 | IAN-PNL-002 | IAN Solar |

Row 7 (JA Solar, 625 W) and the three Solar Homes and four Blue Carbon rows agree. Ask: is the brand column
simply scrambled, or does any of these rows describe a re-badged module? The importer stores both and
matches on the maker in the text.

### 6.2 Cells marked "Verify" or with an asterisk

One Solar sheet row 16 (the 1 kW 12 V wall unit): the charge current is "Verify" — what is it? Deye sheet
row 26 (the 3P 12 kW LV-battery unit): "240A*" on both current columns — what does the asterisk condition?
Solis sheet row 35 (the 3P 15 kW LV-battery unit): "Up to 290A*" — the same question, and is 290 A the
figure to size on? Battery sheet 3 row 10 (the Pylontech 12 V 200 Ah unit): "100A*" recommended discharge.
Until answered the figures are stored with the flag and every circuit that uses them prints "verify".

### 6.3 The Felicity 3P rows' last column

Felicity sheet rows 16–27 carry a kW figure in "Max Recommended Charge Current" ("13kW", "32kW", "28.8kW",
"24kW", "22.4kW", "18kW", "15kW", "80kW", "64kW", "48kW", "47.84kW", "40kW"), each equal to the kW in the
Details column. Is it the maximum charging power (then the current follows from the battery voltage the
owner states), or a copy of the rating by mistake? Left blank until answered; these units are 3P and not
offered on residential jobs, so no job waits on it.

### 6.4 The Solis grid-tie 1P rows' battery figures

Solis sheet rows 5–9 (3, 5, 6, 8, 10 kW grid-tie 1P) carry "40 – 60 V" and 70 / 112 / 135 / 190 / 208 A in
the three battery columns, while every other grid-tie row says "N/A (No Battery Input)". A grid-tie unit has
no battery port; the 190 A and 135 A figures also appear on the Solis and Deye hybrid rows. Were these
pasted from the hybrid rows? Held, not applied, until answered (1.5). If they are real the units are hybrids
and the type column is wrong, which changes their `is_hybrid_inverter`.

### 6.5 The missing temperature coefficients

No panel row carries a coefficient, and 3.1 needs β_Voc on every string. Proposal: one default per
coefficient, not per cell type, because the sheet does not say the cell type for most rows (TOPCon, PERC,
back-contact and bifacial are mixed and only the Blue Carbon items name TOPCon in their specs):
β_Voc −0.30 %/°C, β_Pmax −0.35 %/°C (used for Vmp), α_Isc +0.05 %/°C. **Source: an assumption**, a
conservative envelope for crystalline-silicon modules; more negative is conservative at both ends (a higher
cold Voc, a lower hot Vmp). The warning on every string design made with a default: "The string design used
the default temperature coefficient −0.30 %/°C for Voc (the panel has none on file); type the datasheet's
figure on the Materials page before the plans are sealed." Ask the owner for the maker's datasheet figures
(Voc and Pmax coefficients) for the 14 rows, as two columns added to the panel sheet: the importer's alias
table already knows `tempcoeffvoc` / `betavoc` (`importer.py:37`); a "Temp coeff Pmax (%/°C)" column needs a
new field `temp_coeff_pmax_pct` (not counted in section 1's eleven; S). Also ask for the maximum series fuse
rating per panel (3.2) as a third column.

### 6.6 The inverters' MPPT windows and maximum PV voltages

No inverter sheet carries them; the string check needs `max_pv_voltage_v` (and `mppt_min_v`, `mppt_max_v`
for n_min and the cold Vmp check). Today two items have "500 Voc" from their remarks (FS-INV-005,
BC-INV-003; `catalog.py:122`) and the default inverter FS-INV-008 has none, so the string check would run
on no residential job after this import. Proposal: the owner adds four columns to the inverter sheet,
"Max PV Voltage (V)", "MPPT Min (V)", "MPPT Max (V)", "Max PV Isc per MPPT (A)", one row per model, the
maker's figures — the datasheet importer reads them through the same alias table the materials importer
uses (`importer.py:24-28`), so the same words work in either workbook. The materials workbook's electrical
columns remain the fallback for an item with no sheet row. Until the columns exist the plans keep the "waits
on the datasheets" sentence for the string table and the BOQ keeps the fixed rule with
`string_rule_fallback` on every job.

### 6.7 One item, three sheet rows

OP-INV-001, -002, -003 (One Solar MPPT charge controllers, "12/24/48V" in one name) stand for nine sheet
rows (One Solar sheet rows 4–12: 40, 60, 100 A at 12, 24, 48 V with 0.48 to 4.80 kW). Does the company sell
one unit that switches voltage (then the three rows are one model and the item takes the 48 V figures with a
note) or three units per rating (then three codes)? Specs-only until answered.

### 6.8 Other cells that do not add up (found while reading; the importer flags them)

- Blue Carbon battery sheet row 20: a 25.6 V, 120 Ah pack with a 60 V maximum charge voltage (its 24 V
  siblings say 30 V) and 120 A maximum discharge (they say 100 and 80 A).
- Blue Carbon battery sheet: on twelve rows (the 250 and 300 Ah packs of every series, 24 V and 48 V) the
  "recommended" discharge current is above the "maximum" (48 V 250 Ah rows: 125 A recommended against
  120 A maximum; 48 V 300 Ah: 150 against 120; 24 V 250 and 300 Ah: 125 and 150 against 100; the smart 250
  and 300 Ah rows: 125 and 150 against 100). Which column is the BMS limit? Section 3.9 takes the maximum.
- Felicity battery sheet: the recommended column is Ah ÷ 2 and the charge column Ah ÷ 5 on every row (100 →
  50 and 20; 314 → 157 and 62.8; 279 → 140 and 55.8). Are these the maker's figures or a rule the sheet's
  author applied? The soft check (3.5) reads them either way; the hard check does not.
- Felicity battery sheet row 5 (the base 100 Ah model): 150 A maximum against 100 A on its three variant
  rows and "continuous 100 A" in the item's remark (FS-BAT-001); 1.5 C. Held (3.5).
- Felicity battery sheet row 14: typed HIGH VOLTAGE with 51.2 V, 100 Ah, 44.8–57.6 V. A module of an HV
  stack, as FS-BAT-008/-009 are? Then it is not a battery the BOQ may pick alone (the "controller module" and
  "slave" exclude words, `config.py:251`, do not match this row's text).
- Felicity battery sheet row 43: 102.4 V nominal, 185.6–230 V maximum charge: the ceiling is 2.2 × the
  nominal, which no LiFePO4 pack does (a 32-cell pack charges to about 1.14 × nominal). One of the two
  figures is for another pack.
- Blue Carbon inverter sheet rows 8–9 (the two "Hybrid" rows): Details say 12 V and 24 V, the maximum
  charge voltage says 58.4 V (a 48 V class) on both.
- Felicity inverter sheet rows 28–30 (charge controllers): Details say 12 V, 24 V, 48 V, the maximum charge
  voltage says 14.6 V on all three.
- Felicity inverter sheet rows 12–15 (hybrid 1P): "-380V" after the kW on a single-phase unit, and row 16
  "13KW-720V" where the model text says 10 K: what are the voltages, and is the first 3P unit 10 or 13 kW?
- Felicity inverter sheet rows 12–15: the charge current exceeds the discharge current (109/120, 130/135,
  165/190, 174/190). Confirm; 3.5 sizes the cable on the larger.
- Deye sheet: discharge and charge figures are identical on all twelve hybrid rows. Are both really the
  port's maximum, or was one column copied?
- Solis sheet row 26: "(21A)" in Details on the 10 kW 1P hybrid — what is it?
- Solis sheet row 4 (the commercial ESS set): matched to IAN-AIO-001; its 936 V, 157 A figures go on an
  All-in-one item that nothing prices on a residential job. Fine to keep.
- Battery sheet 3: Pylontech "48 V" nominal on the 100 Ah unit (the others say 51.2 V): as typed; the Ah–kWh
  check passes at 48 × 100 = 4.8 kWh.
- The panel sheet's 100 W row: 600/1000 V (1.1).

### 6.9 Two decisions the type column raises

- Three One Solar wall-type units (OP-INV-029, -030, -032) become selectable for the owner's off-grid kind
  (1.4). Keep them in, or exclude by name?
- A pure grid-tie unit (Deye 1P 3.6–10 kW, Solis 1P 3–10 kW) is cheaper than a hybrid and is what a
  net-metering job without a battery actually needs; `sizing.py:3-7` sizes every job as a hybrid and
  `select_inverter` (`boq.py:103-121`) never offers one. Offer them on `net_metering` jobs (with the
  pass-through check unchanged, since the grid carries the house), or keep the hybrid-only rule? The brief
  builds the field either way; the rule change is S once decided.

---

## 7. Order of work

1. Fields and migrations (section 1, M), the specs table and the importer with its report (5.1, M), the
   fixture and the parse/match tests (5.3–5.4, M). Nothing visible changes on a job yet.
2. The settings block and the two TMY figures (section 3 head, S).
3. The checks in the generator in this order: 3.5 battery circuit on the sheet's figures (S; the eco-hybrid's
   139 A), 3.7 voltage match (S), 3.6 charge check (S), 3.8 Ah–kWh (S), 3.1–3.4 strings, current, breaker,
   MPPT (M). Each with its hand-worked test before the plans print it.
4. The plan set's string table and schedule rows (4.2, M), the Materials page view (2.5, M), the Settings
   section (5.2, S).
5. The owner's answers of section 6 folded in: held rows applied, the brand column corrected on the sheet,
   the four inverter columns and the three panel columns added, then the string check runs on the default
   inverter for the first time.
