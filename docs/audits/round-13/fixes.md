# Round 13: the review's findings applied

Built 10 October 2026 from `engineer-review.md` (the verdict "merge with the fixes listed", fourteen findings in rank order,
the departures' verdicts, section 5), on the merged ten-sheet set at `0e5beca`. Every finding is applied in the review's
order, each with the test the review gives or a figure of its own; nothing is invented, no model name appears, the customer
documents and the website estimate are untouched (their pins pass unchanged). Six commits on the branch, in the review's
rank order: `d8e83b6` (findings 1 and 2), `44e469f` (3, 4, 7, 10, 11), `6f9b4d6` (5), `f309f68` (6, 9, 13), `9db6be7`
(8, 12, 14), and the documents. The suite went from **320 to 325 tests**; `npm run build` passes and `npm run lint` stays at
its seven baseline warnings. The reviewer's states were rebuilt with its own script (`review_build.py`, reused as
`fixes/build_states.py` with the AIC typed at 10 kA, since the reviewer's 6 kA now holds the set) under
`scratchpad/plans13/fixes/states/` and every sheet a finding touches was rendered and looked at (section 3).

## 1. The findings, in rank order

**1 (H) — a breaker's AIC below the fault level now holds the documents.** `pricing/design_analysis.py`, `analyse_design`,
right after `short_circuit_note`: for every breaker whose typed interrupting rating is below the typed fault level
(`a["ok"] is False`) a warning `aic_below_fault`, `hard` and `blocks_documents`, with the review's message (the code, the two
figures, "change the breaker role under Pricing settings › BOM item roles (verify the DU's figure)"), through the existing
mechanism (`job.price_assessment` collects it into `design_blocked`; the proposal, roof check, card and plans answer 409
with the code). The short-circuit note's item 4 names the code beside "does NOT hold"; the module's header, the brief's 2.4,
DECISIONS and the Design and outputs step's design codes (`SystemDesign.tsx`) carry it; the design analysis sheet's "How
to read the Pass column" says it holds the documents. Test: `test_design_analysis.py`, the typed-full test, types
IAN-PRT-027 at 6 kA against FLECO's 10 kA: `design_blocked == ["aic_below_fault"]`, the warning hard and blocking, the
plans and the proposal 409; at 10 kA the set builds with "holds".

**2 (H) — the PV string's continuous current is 1.25 × Isc.** `pricing/design_checks.py`, `circuits_block`, C1: with the
datasheet on file `i_continuous_a = isc_factor × Isc` (16.91 A on the sample) with the note "1.25 × Isc … the PV article's
circuit current", `i_design_a` stays `sc["i_cond_a"]` (21.14 A); without a datasheet the rule's current and its "not
applied" note stay. The combined DC row (C2) follows the same rule (strings × 1.25 × Isc) so the two PV rows agree. The
design analysis sheet's column reads "Design A (× 1.25; C1: 1.25 × 1.25 × Isc)". Tests: `test_circuits_contract.py` (16.91 A
and 21.14 A on the Pila record), `test_design_analysis.py` (16.91 A on the typed state, the note, the column head; the
brief's 630 W string at 20.22 A = 1.25 × 16.18 in place of Imp 15.48 A).

**3 (M) — the electrode caption and the service block.** `reports/plans_sld.py`: the caption now sits to the right of the C7
balloon, start-anchored (`cap_x = x_disc + 5 + BAL_R + 1.6`) and as wide as the sheet leaves, where no line or symbol runs
(the review's alternative; below `EARTH_Y` there is room for three lines, the caption needs six); the DU block's stack is
62 mm wide so "fault level at the service 10.0 kA" stays on one line (the seed's "DU ____: fault level at the service
____" needs 60 mm). Test: `test_plans_sld.py::test_the_electrode_caption_clears_the_egc_bus_…` reads the Drawing itself:
the caption's box (every String of it, with its width) clears the EGC bus line's end, the electrode under the panelboard
and the balloon, stays inside the sheet, and the fault-level String ends in "10.0 kA".

**4 (M) — the site plan's labels and dimensions.** `reports/plans_site.py`: a face's depth dimension sits at `2 × gap`
(one gap further out than the eave's, the review's second option: the far side would collide with the house's west
dimension); `_dim_seg` returns the figure's box and every figure's box joins `taken`; the face labels go through
`_place_label` (the centroid, then below, above, right, left, then the strip along the bottom of the box with a leader to
the centroid), each keeping clear of the symbols, the figures and the labels placed before it; the point labels follow as
before. Test: `test_plans_site.py::test_two_faces_whose_labels_would_collide_…` rebuilds the reviewer's offsets ([0, −2.5]
and [4.5, 0] on the 15 × 12 m lot): the two pads do not overlap, no pad hides a figure, no two figures overprint, "7.00 m"
and "4.76 m" both print and "4.7.00" does not.

**5 (M) — one collector for the set's blank lines.** `reports/plans_blanks.py` holds BLANK and `Blanks`: every sheet module
records each blank line it prints with the figure and the reason it already composes (`blanks.add(sheet, item, reason)`
returns BLANK and stands where BLANK stood; `n` for a figure printed in several cells; `engineer=True` for a line the set
leaves to the signing engineer by design). The cover, the layout sheets, the schedule, the diagram, the mounting detail,
the design analysis, the schedule of loads and the site sheet all record through it; the design analysis prints the
engine's "BLANK" words as the set's blank line and records them (the DU's fault level, each breaker's AIC, the battery's
short-circuit trip, which the engine now words as a blank line with its reason). The last sheet keeps "what the set still
lacks" (the string table, the rows not checked, the tile detail, the uplift inputs, the signing engineer's profile) beside
"the signing engineer's lines" (the frame rating, fed from, the demand load, the branch-circuit figures) and prints "Blank
lines in this set, by sheet" under them: one row per sheet and reason, with the figures and the count of lines; the two
entries the collector made redundant (the diagram's figures, the schedule's service entrance) are gone. The block shrinks
to the frame as the cover's index does, so the seed state's 283 blank lines still make one last sheet and the set keeps its
sheet count. Test: `test_plans_blanks.py` builds the reviewer's typed state and compares, sheet by sheet, the blank lines
pdftotext counts (less the title block's signature line) with the lines the last sheet lists: equal on every sheet, the
schedule's two pages as one, every figure the reviewer named present (the certificate, the AC input rating, the AIC of
IAN-PRT-009 and IAN-PRT-003, the battery's trip, C3's EGC, the L-foot height, the frame rating, fed from, the demand load).

**6 (M) — the FAIL state's callout.** `reports/plans_mounting.py`: when the face's check is FAIL the details print
"S = ______ (FAIL: the signing engineer's; the BOM carries the rule's 1.2 m)" and the plan key says the feet are drawn at
the rule's spacing, the count the BOM carries, because the check FAILED on that face and S is the signing engineer's;
"not checked" keeps its blank as before. Test: `test_uplift.py`'s FAIL case asserts the callout and the key note and that
"S = 0.6 m" is gone.

**7 (S) — the inverter balloon leads with the role.** `plans_sld.py`: with the grid-interactive flag set, "FS-INV-008:
6 kW grid-interactive (hybrid), 1Ø; the datasheet's type: off-grid" ("(no export)" on a no-export job, nothing on net
metering); otherwise the datasheet's word first as before. Tests: the caption test (the combination job) and the off-grid
test read the Drawing's strings.

**8 (S) — cover note 6 names its column.** `plans_pdf.py`: "from the wiring rules' sizing table (the THHN 60 °C column, the
conservative sizing basis: …; the 90 °C and 75 °C columns are on the design analysis sheet; verify the edition)". Test:
`test_plans.py` on the cover.

**9 (S) — the pressure chain on every roof.** `pricing/uplift.py`, `evaluate_face`: the chain runs in two steps, the pressure
chain to T_panel for every roof type once V, h, the exposure constants, Kd and GCp are on file, the fastener step only on a
roof with a drawn detail and the purlin spacing and pull-out typed; a tile roof stops at the fastener step with "the tile
hook's allowable withdrawal: not on file (Detail C waits on the owner's word)", a deck or "other" with its out-of-scope
reason; `stop` carries the reason the chain stopped and the sheet prints it in the face's first blank chain cell (the Kz
cell in the seed state, the fastener cell on a tile roof), "(not computed)" after it. Tests: `test_uplift.py` splits the
blank inputs into the pressure ones (Kz blank, the stop named) and the fastener ones (Kz 0.576, qh 926, T_panel 2.39 still
computed) and works the reviewer's tile state at exposure C and h 4 m: Kz 0.8495, qh 1,366 N/m², the stop's wording.

**10 (S) — the 120 % rule on a no-export job.** `pricing/service_checks.py` writes the job's `kind` into the block;
`plans_sld.poi_lines` (the diagram and the schedule of loads) adds "(applied although nothing is exported: conservative;
the DU's view: verify)" on `off_grid`. Test: the off-grid test on both sheets and the rule's own test.

**11 (S) — "C5 backfeed brk; C6 bypass feed"**, right-anchored inside the panelboard box. Test: the caption test.

**12 (S) — the battery rack's EGC is a missing role.** `design_analysis.py`: the blank "provided" on the battery row is
`not_checked` ("EGC: no battery-rack EGC role on the BOM (Pricing settings › BOM item roles)"), `egc_ok` None, the row
"not checked" and `derating_not_checked` naming it; the analysis report's departure 2 is overruled for this row (DECISIONS
says so). Tests: the battery unit test, the sample job (C3 among the rows not checked), the typed state (the one row left
"not checked", listed on the last sheet).

**13 (S) — the dead load's label.** `uplift.py`: "the item's weight on file (Datasheet (volume +10% packing)); the module's
net weight from the datasheet: verify". With the longer label the two-face typed state no longer fitted the mounting sheet
side by side and the chain split over two sheets; the sheet now shrinks its two columns to the frame when they overrun it by
a little and stacks them only when they overrun by more (the set keeps 11 sheets in the off-grid state).

**14 (S) — revision 0's "By".** `Assessment.plans_issued_by` (nullable, `ensure_columns`) is set with the signed-in
person's display name when `plans_issued_at` is first set (`api/assessments.py`, `current_account`); `AssessmentOut` and
`types.ts` carry it; the cover's revision table prints it on the Rev. 0 row, or a blank line "no signed-in name was recorded
at the first build" (an older record, or a set built outside the API); the Documents card's revision line says "by …".
Tests: `test_plans_title_block.py` (the first build records "u", the cover's row reads "first issue u", the older database
gets the column), `test_plans_blanks.py` (the blank disappears through the API, appears outside it).

## 2. Beyond the findings, and what could not be done

- The combined DC row (C2) takes the same 1.25 × Isc rule as C1 (it does not apply on the sample; the two PV rows would
  otherwise contradict each other). The cover's "point of interconnection" prints the surveyed choice; it was a fixed blank.
- The design analysis prints the engine's "BLANK" word as the set's blank line (`__________`) so the count on the sheet
  and the collector agree; the engine's own texts keep the word, and the API tests pin them as before.
- The battery-rack EGC: the row now reads "not checked" with the review's words, but the BOM roles hold no battery-rack
  EGC role yet, so the owner cannot add the conductor on that page until a role exists (a later step; the brief's 2.3
  left the battery's EGC blank by design). The message points where the role will live.
- Finding 3's test is on the caption's box clearing the bus line, the electrode and the balloon, not "below the bus":
  the caption sits to the right (the review's own alternative) because the 11 mm under the bus hold three lines, not six.
- The last sheet shrinks its block to the frame when the set is mostly blank (the seed state), so the type there is
  small; the alternative, a second last sheet, would add a page the cover's index does not name.
- The review's H-real state (the customer documents on the real PVGIS cells) was not rebuilt here: the pins that guard
  the customer documents and the quick estimate (`test_documents.py`, `test_customer_story.py`, `test_quick.py`) pass
  unchanged, and no new code path reaches `core/quick.py` or the customer PDFs.
- The review's C-full state types IAN-PRT-027 at 6 kA against 10 kA; with finding 1 that state holds the set (409),
  which is what the finding asks. The rebuilt typed states type 10 kA; a ninth state (`I-aic6`) keeps the 6 kA to show
  the refusal (`plans refused 409: design_blocked: … aic_below_fault`).

## 3. The states rebuilt and looked at

Under `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/plans13/fixes/states/`: `plans-{state}.pdf`,
`.txt` (pdftotext, layout) and `{state}-{nn}.png` (100 dpi) for A-seed, B-datasheets, C-full, D-offgrid, E-fail, F-fail,
G-tile and I-aic6 (refused); the 150 and 220 dpi crops `zoom-*.png` of the places the review's crops showed: the electrode
caption and the service block (`zoom-sld-gec-05`, `zoom-sld-service-05`), the site plan (`zoom-site-02`), the FAIL details
(`zoom-fail-details-06`), the tile chain (`zoom-tile-uplift-06`), the seed's chain with the stop's reason
(`zoom-seed-uplift-06`), the typed analysis table (`zoom-full-analysis-09`). Looked at: the caption clear of the bus and the
electrode with "10.0 kA" whole; "7.00 m" and "4.76 m" side by side and both labels placed (the main roof's below its
centroid); the inverter lead and the C5/C6 tag; "S = ______ (FAIL …)" on both details and the key's note; Kz 0.850 and
qh 1,367 N/m² on the tile roof with the stop in the fastener cell; "16.91 A" and "21.14 A" under the new column head; the
last sheet's three tables in the typed and the seed states, one sheet each; the sheet counts 10 (seed) and 11 (typed)
in every state.

## Checks

The full suite before each commit (`cd backend && SOLARAPP_DATA_DIR=/home/user/solarapp/data .venv/bin/python -m pytest
-q`: 320 → 322 → 325 passed), `npm run build` and `npm run lint` (seven warnings, the baseline) for the commits that
touch the frontend (the design codes list, the Documents card). The scripts that applied the edits and built the states
are beside the states (`fixes/edit_*.py`, `fixes/build_states.py`).
