# Round 13, item 3: the mounting detail, the roof construction and the uplift check

Built 10 October 2026 from `engineer-brief.md` section 3 (3.1 the roof types, 3.3 the details, 3.4 the settings and item fields,
3.5 the NSCP 2015 chain, 3.6 the blanks, 3.7 the hand-worked tests) under the coordinator's decisions: the app ships no
wind-code figure and no fastener figure; every one is typed with its source and printed with it; the check is a hard warning
that prints and never blocks; the two metal details are drawn and the tile detail waits on the owner's word. Four commits on
the branch: the settings block, the wind-zone file, the engine and the BOM tie-in; the sheet; the Settings card and the
project's wind inputs; the documents. The suite went from 272 to **280 tests**; `npm run build` passes and `npm run lint` stays
at its seven baseline warnings. The sample plans in the three states (nothing typed, the figures typed at a 0.5 kN pull-out,
a 0.1 kN pull-out) with their `pdftotext` pages and a PNG of the mounting sheet are under `scratchpad/plans13/mounting/`
(`plans-blank-mounting-4.png`, `plans-pass-mounting-4.png`, `plans-fail-mounting-4.png`).

## 1. The settings (`PricingConfig.mounting`, Settings › Mounting and wind)

Its own block in `pricing/config.py` (`MountingConfig`), its own card in the front end (`components/MountingSettings.tsx`, one
route hook in `SettingsPage.tsx`, the entry in `shared.ts`, the labels in `pricingMeta.ts`), every figure blank until typed:

| Setting | Default | Source field | Read by |
|---|---|---|---|
| `screws_per_foot` | 2, an ASSUMPTION the sheet labels | (the owner confirms the set) | T_screw = T_foot / screws |
| `fastener_description` | blank | (its own words: size, length, washer) | callout 8 on the details |
| `fastener_pullout_kn` | blank | `fastener_pullout_source` | the allowable withdrawal per screw |
| `foot_spacing_max_m` | blank | `foot_spacing_max_source` | the cap on the foot spacing (the BOQ rule's spacing stands in, labelled) |
| `rail_position_fraction` | 0.25, an ASSUMPTION | (the maker's clamping zone: verify) | the rail-to-rail spacing printed |
| `rail_kg_per_m` | blank (the rail's weight left out of D: the conservative side, said so) | | the dead load D |
| `kd` | blank | `kd_source` | qh |
| `exposures` (B, C, D: `alpha`, `zg_m`) | blank | `exposure_source` | Kz |
| `wind_zones` (province: `zone`, `v_kmh`, `source`) | empty; the page lists every province of `core/wind_zones.json` as "not set" | per row | V |

`core/wind_zones.json` ships every province of `towns_ph.json` with the zone, the speed and the source blank and a header
naming NSCP 2015 Figure 207A.5-1A as the figure the signing engineer reads them from; `GET /api/pricing/wind-zones` serves
it to the page. The typed rows live in the pricing config (they move the L-foot count, so the settings version moves and a
priced job is flagged).

Per project (`schemas.py`): `AssessmentDoc.wind` (`WindInputs`: `zone`, `v_kmh`, `v_source`, `exposure` B/C/D or blank,
`kzt`, `kzt_source`, `gcp_zone1/2/3`, `gcp_source`), a fold "Wind for the uplift check" under the Roof faces card
(`components/WindInputs.tsx`, three lines in `AssessmentPage.tsx`); `RoofConstruction.fastener_pullout_kn` and
`fastener_pullout_source` (the face's over the project's over the settings'), two fields more in the roof construction fold.

## 2. The engine (`pricing/uplift.py`, `pricing.choices.uplift`)

`apply_uplift` runs in `job.price_assessment` right after `generate_boq` (three lines; `RoofRow` gained `face_id` so the
rows know their face). Per face that holds rows, on that face's construction over the project's default:

```
V (km/h → m/s)   the project's figure, else the province's row (the pin → the nearest town → the province)
Kz               2.01 × (max(h, 4.6) / zg)^(2/alpha), alpha and zg of the typed exposure category (B when blank: assumption)
Kzt              typed, else 1.0 (assumption: no hill or ridge)
qh               0.613 × Kz × Kzt × Kd × V²   [N/m²]
GCp              the worst typed zone's figure for every panel (assumption, named)
p_up             qh × |GCp|   [kPa]
D                (weight_kg + rail_kg_per_m × 2 × the panel's dimension along the row) × 9.81 / A_panel   [kPa]
net              0.6 p_up − 0.6 D;   T_panel = net × A (zero when negative)
strip            the panel's dimension across the rails / 2
cap              foot_spacing_max_m, else rail_length_m / (l_feet_per_rail − 1) (assumption)
S_std            the largest multiple of the purlin spacing ≤ cap;   T_screw = net × S_std × strip / screws, against the pull-out
s_allow          screws × pull-out / (net × strip);   S = the largest multiple of the purlin spacing ≤ min(s_allow, cap)
feet per line    floor(line / S) + 1, two lines per row;  screws = feet × screws_per_foot;  feet per 2.4 m rail = floor(2.4 / S) + 1
```

Statuses: **pass** (a spacing on the purlins holds: the BOM's L-foot line takes the feet per rail line, its note "feet on every
k-th purlin (S m; purlins at p m)", and says the rule's count when it differs); **fail** (even a foot on every purlin does not
hold: `uplift_fail`, hard, not blocking, the BOM keeps the rule's count with a note); **not checked** (a blank V, exposure
constants, Kd, GCp, h, purlin spacing or pull-out, or a tile or out-of-scope roof: `uplift_not_checked`, ordinary, naming
each). `roof_condition` (hard, not blocking) on a flag other than sound; `roof_type_out_of_scope` (ordinary) on tile, deck
or other. `design_blocked` never carries any of them. The block carries every figure as `{value, source, assumed, note,
missing}` so the sheet prints each beside its provenance, and the project's `l_foot` summary (`rule`, `checked`, `bom`,
`note`, `screws`).

## 3. The sheet (`reports/plans_mounting.py`, "Mounting detail and uplift check")

One sheet after the array layouts and before the schedules (`plans_pdf.py`: the module call, the name in `sheet_names`,
three lines in the story, the last sheet's entries from the module, note 3 of the cover now saying the status and the
L-feet). Left: **Detail A** (rib-type metal sheet on steel C-purlins) and **Detail B** (corrugated sheet on purlins) at 1:5,
each a section along the rail at an L-foot: the purlin cut and hatched (callout P: the typed section, material, thickness
and spacing), the sheet profile crest-valley-crest (S: the typed type and profile), the L-foot's plate on the crest and its
leg (2), the screw with its EPDM washer through the crest into the purlin's top flange (8: the typed fastener), the sealant
beads at the plate (7), the rail in profile on the leg with its bolt (1), the mid clamp between two panel frames (3) and
the end clamp at the far frame (4), the bonding lug and its conductor on the rail (6), the panel frames and glass line (9),
the dimension S (the foot spacing from the check, broken) and C (the clearance under the panel, a blank line: the L-foot
height is not on the item), a 100 mm scale bar. Under them the plan key of a 2 × 3 patch at the largest standard scale that
fits (the rail lines at the quarter points, the purlin lines dashed when surveyed, the feet at the check's spacing or the
rule's, the splices, the clamps) and the callout legend with the BOM's items and counts (5, the splice, in the plan key
only). Right: the chain as a table, the steps with their formula or clause in the first column and one column per face
(three at most per table), every typed figure with "source: …" in small type, every assumption labelled, every blank
`__________` with its reason, the Result row PASS / FAIL (red) / NOT CHECKED; then the L-feet on the BOM against the rule's,
the assumptions and the notes (a condition flag, a blank roof type). The two columns sit side by side when they fit the
sheet, one under the other otherwise (the table then splits over the sheets it needs). The tile detail prints as a line
and the last sheet lists it, as it lists the uplift inputs still blank and any out-of-scope face.

## 4. Tests (`tests/test_uplift.py`, eight; the plans tests follow the sheet count)

The app's defaults ship no figure, the wind-zone file holds every province with blanks, a typed row moves the settings
version; the hand-worked chain of 3.7 at V = 200 km/h (Kz 0.576 at the 4.6 m floor, qh 926 N/m², p_up 1.667 kPa, T_panel
2.39 kN, strip 1.139 m, 1.267 kN per foot at 1.2 m, 0.634 kN per screw, pass at 1.5 kN with ratio 0.42; exposure C 0.849
and 1,365 N/m²); the 0.5 kN case (s_allow 0.947 m, every purlin, 0.317 kN per screw, five feet per 2.4 m rail, 32 feet on
the two 4.536 m rows) and the 0.3 kN fail (hard, not blocking); "not checked" naming each blank input, the province's row
standing in for V and the project's figure winning, exposure C's own constants; the roof type and condition warnings and
the merged construction; the sample job's BOM keeping its 24 L-feet and its lines with nothing typed, 32 at 0.5 kN, 16
at 1.5 kN; the Pila record through the API (not checked and the rule's count, then the figures typed under Settings and
on the project with the face's own purlin spacing over the project's, nothing blocked); the sheet in the three states
with every source printed, the cover's note and the last sheet's entries, the wind-zone route. `test_plans.py`,
`test_survey_fields.py` count six sheets.

## Departures from the brief, with the reason

1. **The hand-worked Kz.** 3.7 names h = 5 m but works Kz at the formula's 4.6 m floor (0.576, "the table's 0.57 at 0 to
   4.6 m"); the engine follows the formula the brief itself gives, 2.01 × (max(h, 4.6) / zg)^(2/alpha), which is 0.590 at
   5 m (the table climbs from 0.57 at 15 ft to 0.62 at 20 ft). The test reproduces the brief's figures at h = 4.5 m and
   asserts the 5 m value beside them; the brief's qh of 1,365 N/m² for exposure C is its rounded Kz (the formula gives
   1,367) and the test allows it.
2. **The verdict and the BOM's count.** 3.5 feeds the BOM the feet per rail line whenever the purlin spacing is typed; the
   coordinator feeds it only when the check passed. 3.7 calls the 0.5 kN case a "fail" at 1.2 m and then closes the feet
   to every purlin, moving the BOM to 32. Built: the verdict is on the design the BOM carries, so the 0.5 kN case is PASS
   with the feet on every purlin (the sheet prints the 1.2 m figure that does not hold and the closing-up), the BOM follows
   the closer feet, and FAIL is reserved for a fastener that does not hold even with a foot on every purlin (the BOM then
   keeps the rule's count). The brief's "the sheet prints both counts when they differ" holds in every state.
3. **Kd and the exposure constants are typed, not shipped.** 3.5 gives Kd 0.85 and the alpha, zg per exposure as cited
   stand-ins; the coordinator's decision ships none, so both are settings with source fields, blank until typed, and a
   blank stops the chain at its line (the brief's 3.6 list of chain-stoppers gains them). Kzt keeps the brief's 1.0 as a
   labelled assumption (the neutral value, no amplification).
4. **The foot span cap when the maker's maximum is blank.** 3.5 needs a cap and 3.4 leaves it blank; built: the BOQ rule's
   own spacing (2.4 m rails with 3 feet: 1.2 m) caps the span, labelled an assumption, until the maker's figure is typed;
   a purlin spacing wider than the cap keeps a foot on every purlin and notes it.
5. **Two metal details, the tile a line.** 3.3 draws Detail A (metal, the profile by type) and Detail B (tile); the
   coordinator draws rib-type and corrugated and keeps the tile as a placeholder. Built: Detail A rib-type, Detail B
   corrugated, both always drawn (the standard details the crews mount with, the face's own type in the table and the
   callouts), a Detail C line for tile faces, "not drawn" for a deck or other. A blank roof type runs the chain (the feet
   and purlins do not depend on the sheet profile) and the sheet says the detail that applies is blank.
6. **The section drawn.** 3.3 asks in one view for the purlin cut as a C-section, the sheet profile crest to crest and
   the clamps left and right along the rail; no single true section holds all three. Built as a section along the rail
   with the purlin under the foot shown cut, said so under the details, and the chain's assumption that the rails cross
   the purlins (a foot at each purlin crossing) printed as an assumption with the note that where the rails run with the
   purlins the feet are screwed into that purlin at the spacing shown and the engineer verifies.
7. **The long dimensions.** The foot spacing (1.2 m), the rail-to-rail spacing (1.139 m) and the panel edge overhang do
   not fit a 1:5 section: S is a broken dimension line with the figure, the rail-to-rail spacing and the overhang are
   printed under the details, C (the clearance) is a dimension line with a blank figure as 3.3 asks.
8. **Blank panel weight and rail weight.** 3.6 does not list them; a missing panel weight or rail weight is not a
   chain-stopper here but a labelled assumption (zero, the conservative side), since leaving the dead load out only
   raises the uplift.
9. **Fonts.** Montserrat has no Greek alpha, no ≤ and no arrow, so the sheet spells them out ("alpha", "at or under",
   "gives").
10. **The sheet count.** The plans tests of step 1 pinned five sheets; they count six now (the mounting detail sits
    between the layouts and the schedules), and `test_survey_fields.py`'s expected roof construction carries the two
    fastener fields.
11. **`choices.rows` carry `face_id`**, so the sheet and the check know which face a row sits on; the BOQ's own counts are
    unchanged and `test_boq.py` holds.
12. **Not built:** the GCp per roof zone as settings defaults (the brief types them per project; the coordinator says
    the PEE types them), the rooftop-solar method of ASCE 7-16 (named on the sheet as the office's later choice), a
    tile chain on the rafter spacing (waits with the detail), a per-panel zone assignment (the worst zone for every
    panel, as 3.5's assumption).
