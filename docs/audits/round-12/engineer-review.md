# Round 12 engineer review: steps 1 to 4 of the datasheet brief, as built

Reviewed 10 October 2026 by the solar engineer on the audit team, against `docs/audits/round-12/engineer-brief.md`.
Branch `worktree-agent-a21c306df6541283b` (d75ad2f, 0e82354, 8706317, f055df3 on a2bf621), read-only; the
implementer's report `docs/audits/round-12/implementation.md`; the importer's report on the owner's three
workbooks (`scratchpad/datasheets/import-report.txt`, 210 rows) and the six screenshots. Nothing in either
checkout was changed; this file is the only thing written. Line numbers are the worktree's.

What I ran myself: the backend suite (`246 passed, 7 warnings in 109 s`); a scratch database round trip on the
owner's real files (seed → datasheets → materials re-import → `--apply-held` → plain re-run → materials
re-import again); every hand-worked figure of the brief's section 3 through the code's own functions
(`string_plan`, `string_current`, `mppt_assignment`, `inverter_battery_current`, `charge_check`,
`voltage_match`, `ah_kwh_check`, `design_temperatures`); the sample job's BOQ on the main checkout and on the
branch with and without the datasheets; the plans PDF for the Pila sample project with and without them
(`pdftotext`); the quick-estimate pin test; a probe of the automatic battery choice at 15, 25, 40 and 60 kWh.

## Verdict

**Merge with the fixes listed.** Two fixes before the merge, both small (findings 1 and 2); the rest are
follow-ups or the owner's call. What was asked for is there, the irregular cells are parsed by the brief's rules
and flagged, the precedence holds through a materials re-import, every hand-worked figure reproduces to the
hundredth, the sample job's lines are identical to the main checkout's without the datasheets, and the website
estimate's code is untouched.

## What was verified, point by point

1. **Field mapping and the rules of 1.5.** All 14 panel rows match their items; the six brand-shifted rows
   (sheet rows 8–13) carry both brands and matched on the maker in the model text, with the 6.1 notice. The 100 W
   row stores 600 of "600V DC / 1000V DC" with its notice; the "~" cells parse with four "approximate" notices
   (row 13). The five Solis grid-tie 1P rows are **held** (type and phase applied, the three battery figures and
   the class on the specs row, nothing on the item: `IAN-INV-001.battery_max_a is None` after the import); the
   Felicity 100 Ah base row's 150 A is held (FS-BAT-001 keeps 100 A). The twelve Felicity 3P kW cells are blank
   with the 6.3 notice, never a number. "Verify" (One Solar row 16) and the three asterisk cells (Deye row 26,
   Solis row 35, battery sheet 3 row 10) are flagged. "N/A (No Battery Input)" sets `battery_class = none` with
   no notice; "NO DISCHARGE OUTPUT" is blank with none; "80A + 80A" stores 80 and two inputs; "1,000V" → 1000;
   "58.4V–60V" → 58.4 (narrow), "40 – 60 V" and "40-60V" → 60 with the low end noted (wide); "Varies by BMS /
   Up to 800V" → 800; "29.6A standard" → 29.6; the Deye "MPPT 18/36/36A" → count 3, 18 A, "18/36/36" (the
   remarks never gave these; `OP-INV-017.mppt_count == 3` after the import). The 25.6 V / 60 V row, the twelve
   recommended-above-maximum rows, the HV-typed 51.2 V row (sheet 2 row 14) and the 102.4 V / 230 V row carry
   their 6.8 notices. The Solis orphan rows 47–53 are skipped as "no model in the model column".
2. **Match tiers and precedence.** Exact on the verbatim names (25 Deye, 35 Solis, 6 One Solar off-grid, the
   Solar Homes and Blue Carbon panels); contains on FS-INV-005/-006 and panel rows 10–12; base on FS-BAT-005,
   -007 and BC-BAT-002; the longer-of-two rule gives FS-BAT-003 and -004 their TG2 rows (160 A, 250 A, as their
   remarks say); the Blue Carbon base 6.5 kW row and FS-BAT-006's two variants are ambiguous and specs-only; the
   three One Solar controller items stand for nine rows, specs-only with the 6.7 note; the 23 items the brief
   lists as unmatched stay unmatched. The eco-hybrid: `battery_max_a 135 → 139`, `charge_a_max 135`,
   `charge_v_max 58.4`, type off-grid, phase 1, class LV, and `grid_interactive` kept True with the conflict
   reported. **The re-apply after a materials import works**: after `import_workbook(replace_config=False)`
   the eco-hybrid still reads 139 A, OP-INV-017 keeps its three MPPT inputs, BC-BAT-001 keeps 100 A
   (`store.py:111-113`, `datasheets.py reapply_datasheets`); the stamps survive a `replace_config=True` import.
   A second run of the same files changes nothing (items changed 0). The owner's override survives a re-run and
   typing the sheet's figure back lifts it (`note_overrides`).
3. **The checks against my figures** (all through the code; the brief's expected values in brackets): Voc_cold
   50.51 V, n_max 9, two strings of five for ten 630 W panels on a 500 V input [50.51 / 9 / 2 / 5]; 50.22 V and
   still 9 at 16 °C; the 630 W bifacial 57.37 V and 8, the 585 W 54.83 V and 9, the 600 W 55.68 V and 8, the
   620 W 49.97 V and 10, the 720 W 50.62 V and 9 [as the brief's 3.1 says, exception included]; Vmp_hot 34.29 V
   [34.29]; a forced single string raises `string_voltage_cold` with `blocks_documents`. I_string 15.48 A,
   V_string 366.3 V, I_design 20.225 A, I_cond 25.281 A, OCPD 32 A [15.48 / 366.3 / 20.23 / 25.28 / 32]; the
   720 W 29.05 A → 32 A, the 630 W bifacial 23.67 A → 25 A; the role breaker (25 A) gives way to the 32 A item
   on the 630 W panel and stays on the 585 W. Two strings on an 18 A input: 30.96 A, `mppt_current`; on the
   36 A input of the 12 kW unit, none. Battery circuit: the eco-hybrid 139 A ("the larger of discharge 139 A
   and charge 135 A"), FS-INV-002 190 A [139 / 190]; breaker minimum 173.75 A, the same 250 A breaker and
   70 mm² pair. Charge: 135 A against 60 A, set 60, three units [as 3.6]; the 12 kW Deye 250 A against 62.8 A,
   four units. Voltage match: a 60 V port on a 57.6 V ceiling warns `battery_charge_voltage`; 58.4 V on 60 V
   passes; the 25.6 V pack and an LV pack on an HV port raise `battery_voltage_class` with `blocks_documents`.
   Ah–kWh: 25.6 × 200 = 5.12 (0.0 %), 51.2 × 314 = 16.077 against 16 (0.48 %), the hand-built 51.2 × 100
   against 6 kWh 14.7 %. Design temperatures at Pila's figures (21.9 / 34.1 °C, Faiman rise 25.9 °C at 2 m/s):
   T_cold 14 (the setting; the cell gives 16), T_hot 70 (the setting; the cell gives 59.95).
   **The fallback holds**: the sample job (8 × BC-PNL-004, 6 kW, 11.7 kWh) on the branch without the
   datasheets produces the same 27 BOM lines, the same quantities and the same choices as the main checkout
   (1 string of 8, 15.0 A, 336 V, 4 mm², 135 A, 168.75 A, FS-BAT-006 × 1); the only difference is the ordinary
   `string_rule_fallback` warning the brief asked for. `test_pricing_engine` still gives ₱329,300.
4. **The plan set.** Without the datasheets: five sheets, every datasheet figure a blank line, the "String
   table … waits on the datasheets" entry on the last sheet, as before. With them (and a 500 V maximum PV
   voltage typed on the eco-hybrid, since no sheet carries one): six sheets, the schedule on two (named on the
   cover); the string table reads "S1 6 329.0 V 222.2 V 500 V 171.0 V (34 %) ______ MPPT 1: 13.31 A at Imp
   of 20 A" (6 × 54.83 = 329.0 and 6 × 37.04 = 222.2: right); "PV circuit current 16.91 A" (1.25 × 13.53) with
   the conductor line at 1.5625 × Isc; "Inverter battery 139 A the larger of discharge 139 A and charge 135 A;
   datasheet"; "Battery breaker at least 174 A … chosen 250 A"; "Charge current 100 A the bank accepts 100 A
   (2 × 50 A)"; "Voltage match holds battery 51.2 V nominal (48 V class, LV)"; the coefficients say "default,
   an assumption"; the string-table entry is gone from the last sheet and the single-line entry names only
   what is still blank. One wording slip on that sheet (finding 8).
5. **The quick estimate.** `core/quick.py`, `api/quick_routes.py`, `public.py` untouched. The pin test holds:
   ₱314,000 with the seed, ₱287,000 with the datasheets; the ₱27,000 moves because the automatic battery choice
   changes, not the strings (finding 3 says what I think of that).
6. The departures: section "Departures" below.
7. Missing against the brief and built beyond it: the two sections at the end.

## Findings, in rank order

Effort S under half a day, M one to two days. Severity: what hurts a customer or fails an inspection first.

### 1. The sheet's generic type overrides the owner's explicit "check the certification" remark — must fix, S

`datasheets.py apply_spec` (the `grid_interactive` block, lines 851–857): the type fills the flag whenever the
item's is None. FS-INV-002's flag is None on purpose: its remark says the grid certifications are "in progress"
and the IEC 61727 / 62116 listing is not on it, and `catalog.infer_grid_interactive` (`catalog.py:81-82`)
returns None for exactly that pattern. The import report shows `matched FS-INV-002 … grid_interactive - -> yes`
from the sheet's "Hybrid 1P". Effect: on a net-metering job that steps up from the 6 kW default,
`select_inverter` (`boq.py:115-133`) prefers marked units over unknown ones, so this 8 kW unit now sits in the
marked pool (my probe: `FS-INV-002 True` among the 8–10 kW grid candidates) and can be the automatic choice
with only the ordinary `inverter_certificate_missing` warning, where before it was offered last with the
`inverter_certificate_unknown` warning that names the anti-islanding certificate. A DU application built on it
is the customer's problem. The sheet's "Hybrid" is one word about a family; the remark is the owner's note
about this unit. **Fix**: in `apply_spec`, fill `grid_interactive` only when the item's flag is None **and**
`re.search(r"check[^.]*certif", item.remarks or "", re.I)` is false; otherwise leave None and add the note
"grid flag left unknown: the item's remark says to check the certification". Add the case to
`test_datasheets_match.py::test_the_figures_on_the_items_and_the_precedence` (FS-INV-002 stays None) and to
the report line.

### 2. A figure applied with `--apply-held` is lost on the next materials import, and the page keeps saying "held … not applied" — must fix, S

Verified in the round trip: after `import_datasheets(apply_held=True)` FS-BAT-001 reads 150 A; a plain re-run
leaves 150 on the item but reports the row as `held` again; the next `import_workbook` writes the remark's
100 A back and `reapply_datasheets` (`datasheets.py`, called at `store.py:113`) applies `spec.fields` only, so
the item ends at **100 A** with no line saying so. The Solis grid-tie figures survive only because their
workbook rows carry no remark. The owner's confirmation (brief 6.4, 6.8) is the one thing the hold exists to
record, and it evaporates on the next price-list import; the Materials page then shows "held: maximum above
1 C not applied" (`MaterialsPage.tsx:201`) under a figure that is applied. The direction of the loss is the
conservative one here (back to 100 A), which is why it is not a safety finding, but it is a silent reversal of
a decision. **Fix**: add `held_applied_at: Optional[datetime]` to `DatasheetSpec` (`models.py`); set it when
`apply_held` is used (the command and the page) and keep it on the row through a re-run (the upsert must not
clear it: `datasheets.py import_datasheets`, the block that copies `r.held` onto `s`); in `apply_spec`,
`apply_held = apply_held or bool(spec.held_applied_at)`; the report line reads `matched (held figures applied
on <date>)` and the page's note reads "held figures applied on <date> on the owner's word", with "withdraw" to
clear it. Test: apply-held, then `import_workbook`, then assert 150 A; a plain re-run reports `matched`.

### 3. The automatic battery choice now follows the "maximum" column alone, and the sample estimate moved by ₱27,000 on it — the owner's call, S

With the datasheets the sample job's battery goes from FS-BAT-006 (150 A maximum from its remark) to
OP-BAT-007 (the JK 230 Ah pack: 200 A maximum, 80 A recommended, 50 A charge), and the Pila sample project's
from FS-BAT-003 to two OP-BAT-008 (the JK 120 Ah packs: 120 A maximum, 60 A recommended each). Both are right
by the rule as built and as the brief wrote it (`select_battery`, `boq.py:146-161`: the hard figure first,
then cost) — the JK packs had no continuous current before and ranked below; now they carry the sheet's
maximum and are cheaper. But the bank then runs at 139 A against 80 A (174 %) or 120 A (116 %) recommended,
and the two new ordinary warnings (`battery_discharge_recommended`, `battery_charge_current`) fire on every
such job. The engineer's view: a pack that passes the recommended rate should rank above one that passes only
the maximum, before cost; otherwise the import rewards the sheet with the widest spread between its two
columns (the JK rows: 2.5×). **Fix, if the owner agrees**: in `select_battery`, rank by
`(hard rank as today, 0 if units × discharge_a_recommended ≥ current else 1 if unknown else 2, cost, units)`;
on the sample job that returns FS-BAT-003 (150 A recommended ≥ 139) ahead of FS-BAT-006 (unknown) and the JK
packs (fail), and the pinned ₱287,000 changes again — the test states the new figure. If the owner prefers the
cheaper pack with the warning, leave it and say so in DECISIONS.

### 4. The generator may pick a pack its own class check then blocks — S

`select_battery` (`boq.py:146-161`) does not read `battery_class` or `nominal_v`; `voltage_match` runs after
the choice (`boq.py:409-411`). My probe at 15, 25, 40 and 60 kWh on the eco-hybrid picked LV or unknown-class
packs each time (the HV packs cost more), so nothing blocks today, but the rule is incomplete: the exclude
words (`config.py:251`) keep "12V"/"24V" names out and nothing keeps an HV pack out of an LV job. **Fix**:
skip a candidate whose class (from `battery_class`, else `voltage_class(nominal_v)`) is known and differs from
the inverter's port class (from `battery_class`, else `voltage_class(charge_v_max)`), when both are known; a
per-job pick keeps the hard warning as built.

### 5. One switch applies two different answers — S

`--apply-held` and the page's tick apply the Solis grid-tie figures (question 6.4) and the above-1 C maxima
(question 6.8) together (departure 7). The owner may confirm one and not the other. **Fix**: a per-row
"Apply held figure" on the Materials page (`POST /api/pricing/datasheets/{id}/apply-held`, setting finding 2's
`held_applied_at`); keep the switch for the command.

### 6. A per-job pick of a unit above the largest standard AC size crashes the pricing — S (observed by the implementer, outside the brief)

`boq.py:609-610` formats `b_inv:g` and `b_grid:g` after the hard `ac_circuit` warning set them to None, so
the whole Calculate fails with a 500 instead of the warning. `select_inverter` now keeps 3P and HV units out,
but `inverter_code` (a per-job pick) bypasses it. **Fix**: print "above the largest standard size" where the
figure is None (`_g(b_inv, 'A')` already does this), lines 609–610, 622 and 627.

### 7. `battery_inputs_verify` raises when the inverter has two inputs and no discharge figure — S

`design_checks.py:85-87` (the `battery_inputs_verify` message) formats `inverter.battery_max_a:g`; the parser always sets both, but the Materials
page lets the owner set "Two" inputs on an item with a blank discharge figure. **Fix**: `_f`-style guard,
"({x} A each)" only when the figure is on file.

### 8. The last sheet reads "the panel's the temperature coefficient of Voc; the inverter's the MPPT window" — S

`plans_pdf.py` (the `panel_lbl` / `inv_lbl` dicts and the `datasheet_state` sentence): the labels start with
"the" and the sentence prefixes "the panel's ". Seen in the PDF I built. It is the PEE's sheet. **Fix**: drop
the article from the labels, or build "the panel's " only for labels without one.

### 9. `inverter_type` and `battery_class` are free text on the API — S

`schemas.py MaterialItemIn / MaterialItemPatch`: any string is stored; `is_hybrid_inverter` (`catalog.py`)
treats an unknown string as blank and falls back to the name rule without a word. The page uses a select, the
API does not. **Fix**: `Literal["", "grid_tie", "hybrid", "off_grid", "charge_controller", "ess_set"]` and
`Literal["", "LV", "HV", "none"]`.

### 10. The page labels a name-inferred grid flag "typed" — S

`datasheets.py datasheet_page`: provenance is "remarks" only when `electrical_from_remarks` produced the
value; `grid_interactive` comes from `infer_grid_interactive(name, remarks)`, which that dict never carries, so
the eco-hybrid's "yes" (from the word hybrid in its name) shows as "typed". **Fix**: compare against
`infer_grid_interactive(it.name, it.remarks)` for that field.

### 11. "Add as item" sets the maker as the supplier — S

`add_item_from_spec` defaults `supplier` to the sheet's brand (FELICITY, BLUE CARBON…), which is not a row on
the SUPPLIERS sheet; the next materials import warns "supplier not on the SUPPLIERS sheet" and the landed cost
takes a blank supplier's terms. The route accepts `supplier`; the page (`api.ts addDatasheetItem`) never sends
one. **Fix**: a supplier select beside the code on the page, required.

### 12. Small things — S each

- `datasheets.py import_datasheets`: `taken = {c: w for c, w in taken.items() if c != s.matched_code}` runs
  after `s.matched_code` was set to None, so it removes nothing; harmless (the item is gone) but dead.
- README.md:458 calls `backend/datasheets/` "the importer's default inputs"; the command has no default
  (`nargs="+"`). Say "the owner's three workbooks as received, for the importer and the fixture".
- The screenshot's "202 rows" against the report's 203 upserted: through the page route I count 203; the
  screenshot predates the model-as-typed key (departure 5). No fix.

## Departures: verdicts

| Departure | Verdict |
|---|---|
| `battery_inputs` blank for one | **Accepted**: a stored 1 would be written over the sheet's 2 by a materials re-import until the re-apply ran. |
| Exact tier bounded before as well as after the model | **Accepted**: it is what 2.2's token-start rule needs; the plain 48 V 100 Ah row does not take the smart item (verified, `test_datasheets_match.py:79`). |
| Slash alternatives read once each; equal-length exact rows leave the item unmatched | **Accepted**: the only way the three One Solar rows can name OP-INV-001 under "the longer model wins". |
| Battery sheet kind also from MAX DISCHARGE CURRENT | **Accepted**: battery sheet 3's header has no Capacity or BATTERY TYPE word. |
| Upsert key carries the model as typed | **Accepted**: 1.2 kW and 12 kW normalise alike and are two units. |
| `held_fields` beside `held` | **Accepted**, with finding 2: the applied state must be persisted too. |
| `--apply-held` applies both held kinds | **Accepted for the command**, with finding 5: the page needs the per-row action, since 6.4 and 6.8 have different answers. |
| DC breaker: substitute and warn; `roles.dc_breaker_pattern` | **Accepted**: it is what 3.2 meant; the role item stays when it covers the string. |
| Pmax coefficient always the default | **Accepted**: the brief's own gap (6.5); the plans say "default, an assumption". |
| I_cable not a separate figure | **Accepted**: in a passing design it equals I_inv. |
| The schedule on a second sheet when needed; the two Isc lines in one cell; file and date on the cover only | **Accepted**: the set without the figures keeps its five sheets (verified); the cover line names the file. |
| Observed, not changed: the AC-note TypeError | **Not accepted as "observed"**: finding 6, a one-line guard; a per-job pick reaches it. |

## Asked for and missing

- Nothing of the brief's steps 1–4 is missing. Two things the brief implied but did not spell out are
  findings 2 and 5 (the applied-held state and the per-row apply). The module's maximum series fuse rating
  bound on the DC breaker, the temperature-coefficient and MPPT-window columns, and the string check on the
  default inverter wait on step 5 as the brief said; until then every residential job carries
  `string_rule_fallback` (verified on the sample job) and the plans keep the "waits on the datasheets" entry.

## Built beyond the brief

The slash-alternative reading, the `held_fields` column, `roles.dc_breaker_pattern`,
`choices.battery_current_source` / `battery_current_basis`, the "two inputs differ" notice, the schedule's
second sheet, `DatasheetLink.supplier`, and the owner's three workbooks committed under `backend/datasheets/`
(tracked; the fixture README cites them). All accepted; the last one the owner should know about, as the seed
materials workbook already is in the repository.

## Before the merge, in one list

1. Finding 1: `apply_spec` keeps `grid_interactive` None when the remark says to check the certification;
   FS-INV-002 back to unknown; test.
2. Finding 2: `held_applied_at` on the specs row, honoured by `apply_spec`, the re-apply and the page; test
   across a materials import.
3. Finding 6: the None guard on the AC breaker note.
Then the owner's two calls (findings 3 and 5) and the S follow-ups (4, 7–12).
