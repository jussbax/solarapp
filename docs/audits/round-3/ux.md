# UX audit, round 3: the "odd sticks" hunt

Agent "ux". Brief: the owner "still sees some odd sticks popping out here and there". Every signed-in screen, the new sign-in screens (first-sign-in gate, Your account with the authenticator and the backup codes, People), the Design and outputs step's seven cards, the six documents, and the website were walked at 1280×900 and at 390×844 (DPR 2, touch) and screenshotted. Each page was also measured: `scrollWidth` against the viewport, elements sticking out past their container, bordered elements that are empty or line-thin, sticky bars, tables that scroll sideways, tap targets under 44 px, text under 13 px, and contrast. Repository untouched; `frontend/dist` not rebuilt.

## Setup notes

- Private app on 127.0.0.1:8010, fresh database `scratchpad/agents3/ux/app.db` (seeded itself from `PLD_Materials_DB.xlsx`: 362 items, 4 suppliers). Public website on 127.0.0.1:8011 forwarding to 8010. Both stopped at the end.
- Projects built through the API with the real PVGIS data (`seed.py`, `fix.py`): project 1 "Maria Santos", Brgy. Labuin, Pila (main roof 9 × 5.5 m S 15° with a 1.2 m firewall and a mango tree, garage 6 × 4 m W 12°, a Blue Carbon 585 W panel and a manual 550 W, two reading sets, eight appliances, a 380 kWh / ₱4,900 Meralco bill, net metering + battery, signing 20 Oct, stage Quoted; calculated through pricing and the program: 5 panels, 2.92 kWp, 15.4 kWh battery, ₱291,500, one installation day). Project 2 "Jose Reyes": the same, calculated, then edited so it is stale. Project 3 "Ana Dizon": saved, never calculated. One website booking ("Test Visitor") made through the public estimate on both widths, then turned into project 4 with Start assessment.
- People: the owner `admin`; engineers `pedro.santos` and `lita.cruz` (created through the API for the first-sign-in gate at each width), `juan.delacruz` and `maria.lim` (created through the People card). The owner's authenticator was switched on and off again on both widths to photograph the set-up and the backup codes; it is off now.
- Scripts and measurements in `scratchpad/agents3/ux/`: `lib.js` (the stick scanner), `desk-a.js`, `desk-b.js`, `phone.js`, `phone2.js`, `gate.js`, `site.js`, `measure.js`, with `*-report.json` and `*.out`. 329 screenshots in `scratchpad/agents3/ux/shots/` (index at the end). Prefixes: `d` desk back office, `p` phone back office, `g-desk`/`g-phone` the engineer's first sign-in, `w-d`/`w-p` website, `pdf-` rasterised pages, `doc-` the downloaded documents, `crop-` phone crops.
- Two capture artefacts to ignore when reading the screenshots: an element screenshot taller than the viewport shows the sticky tabs or the action bar mid-image (Playwright scrolls while stitching), and a gold ring on a tab or button is the hover state under the headless mouse, not a focus or an error state.
- OpenStreetMap tiles are blocked in the sandbox: every map is grey.

## Verdict

The build is far cleaner than round 2. Every measured page is exactly 1280 or 390 px wide except one, nothing overflows its card, no bare borders or dangling lines exist on the desk, the seven Design and outputs cards read in the right order with a working index, the documents card and the one stale rule behave as promised, the plan drawings and the Gantt are legible on both widths, the authenticator set-up, the backup codes, the temporary-password gate and the People card work end to end, and the website's booking flow lands in Leads and converts to a project with the pin, the notes and the bill prefilled. Round 2's top ten are all built (table below).

The "odd sticks" are real, and almost all of them come from six stylesheet causes rather than sixty places, so one fix each closes them. In order of what hurts on a roof:

1. **Settings does not fit a phone any more.** The new People table is 742 px wide inside a 368 px card: the page scrolls sideways (765 px), the Sign-in badges are cut at the screen edge, Rename / Reset password / Deactivate are off-screen, and because the cells carry `data-label` but the table has no card layout, every cell prints its label twice (column header plus an in-cell caption), so one person is a 147 px tall row. This is the one guard-rail regression (DECISIONS "every signed-in page must fit a 390 px phone").
2. **Grey bars inside white cards.** The page-level `.actions` style (page-grey background, meant for the sticky bar on the grey page) is reused for three inline button rows: the BOM "Export CSV / Export XLSX / Show internal build-up" row in Quantities, the "Save profile" row in Company profile, and the sticky bar of Pricing settings. Each is a grey stripe with white card around it; on the phone the pricing one is 111 px tall. This is the most literal "odd bar".
3. **Controls at different heights in the same row.** `.row` aligns to the bottom edge, and `.field` carries a 10 px bottom margin and sometimes a hint, so "Add a person" is a 40 px staircase on the desk and 64 px on the phone, "Add a security key" sits 8 px below its input, and the readings-set labels sit at two heights.
4. **Gold as table text.** The chart gold `#C9A227` is used as text in three tables (payments in the schedule, "In" in the cashflow, "Savings" in the year table): 2.42:1 on white, under half the AA minimum and unreadable in sunlight. Round 2 fixed this for links with `--gold-text`; the inline chart colours were missed.
5. **KPI tiles out of line.** The glance strip's tiles are buttons, and buttons centre their content, so the first tile (three lines) sits 12 px higher than its neighbours; in Quantities and Savings a label that wraps ("Contract price (VAT included)", "Monthly bill, without → with solar") pushes its value 15 px below the row.
6. **Table typography.** A right-aligned number column followed by a left-aligned text column with only 12 px between them reads as one phrase ("12 5", "1 pc 1 per string") in four tables; the Site factor table's row headers are shouted in uppercase because the global `th` rule applies; on the phone the card captions on numeric cells inherit right alignment, and empty cells still print their caption ("ELECTRICAL", "PANEL SIZE").

Nothing in the documents (roof check, proposal, program of works, card, BOM exports) shows a stray line or a broken table; one copy slip ("1 rows, 2 lines each") and one unit slip ("23.8 C per kW/m2") are the only marks.

## Round 2 items: what is actually fixed

| Round 2 | Status in this build | Evidence |
|---|---|---|
| 1 CRM out of the front door | Done: Projects list carries engineering facts only, stages assessed…closed, nav Projects · Leads · Materials · Settings, stage pill in the page head, website fields under Settings › Website. The Leads tab itself is leaving per this round's decision [crm]. | `d02-projects.png`, `d03a-page-head.png` |
| 2 One stale rule for every document | Done and verified: stale project answers 409 on `report.pdf`; all six rows in Documents show "Needs a calculation"; the exports' buttons disable with the reason; the card opens a prepared tab. | `desk-a-report.json` `doc_stale_report`, `d09b-stale-documents.png`, `phone2-report.json` `card_popup` |
| 3 Per-row k shift on a dropped reading | Not re-tested this round (no zero reading in the seed). | |
| 4 Design and outputs with an index and a Documents card | Done: seven cards, sticky sub-tabs on the desk, a jump list on the phone, the index follows the scroll, a tap lands the card 62 px under the tabs. | `d06-outputs-viewport.png`, `p06c-outputs-jumped-program.png` |
| 5 Plan drawing and Gantt | Done in the app and in both PDFs. | `d07-design-roof.png`, `d07-design-program.png`, `pdf-roof-check-2.png`, `pdf-program-1.png` |
| 6 Phone results | Done: stale banner in flow (106 px), documents in their card, BOM as cards, months as rows, payment editor as cards. | `p08-outputs-stale-unsaved.png`, `crop-p-bom-rows.png`, `p07-design-roof.png`, `p05e-payment-terms.png` |
| 7 Offline and validation wording | In code (`AssessmentPage.tsx:49` OFFLINE_EDITS_KEPT, `api.ts:22-80` label map); not re-tested. | |
| 8 Phone top bar | Done: one 63 px row, page name, Menu with 44 px items. | `p02b-topbar.png`, `p02c-menu-open.png` |
| 9 Website sticky bar | Done: hidden while the form is in view and after booking; body padding 84 px while it is up; footer clear. | `site-report.json` `w-p_sticky_at_form`, `w-p-estimate-9-bottom.png` |
| 10 Impossible inputs, create on first Save | Done: `/assessments/new` is a draft ("Not saved yet"), leaving it leaves no row; a face where nothing fits warns by name. | `d11-new-viewport.png`, `desk-a-report.json` `list_after_abandon` |
| 11 PDF page and table breaks | Done: roof check page 2 holds the plans and the next step; the program PDF's hourly table is whole. | `pdf-roof-check-2.png`, `pdf-program-2.png` |
| 12 Number formats | Done ("-₱46,272" everywhere). | `d07-design-cashflow.png` |
| 13 Appliance table on the desk | Done (fits 1,034 px). | `d04-audit-viewport.png` |
| 14 Settings leftovers | Mostly done: categories editor, BOQ roles labelled with the code under the label, Undo reset. **Not done:** five profile hints still repeat the placeholder (finding 14). | `d24-05-…png`, `d24-20-…png`, `d21b-profile.png` |
| 15 "Use" radio, blank times | Done ("Automatic (most kWp)" row; "(default)" and "from the program settings"). | `d03d-card-panels.png`, `d05d-program-inputs.png` |
| 16 Installer notes, empty cards | Done. | `d07-design-savings.png` |
| 17 Gold contrast | Done for links and eyebrows (`--gold-text` 4.9:1); **not** for the chart gold used as table text (finding 4). | `measure-report.json` |
| 18 Labels attached to inputs | Partly: `Field` exists and the Site card, Documents and the pricing inputs use it; the faces, panels and readings editors still have bare labels (`site_labels` in `desk-a-report.json`: 2 of 18 attached). | |
| 19–22 Website details, dead ends, sign-in, phone details | Done (widget header hidden, 404 and missing-project pages with a way back, remembered sign-in method, Delete in the card foot, k under each reading on the phone, route-matrix scroll hint). | `w-p-estimate-1-top.png`, `d12-missing-project.png`, `p03f-card-readings.png`, `p18-04-…png` |

## Findings, ranked

Tags: [ux] [bug] [copy] [engineering] [crm] [website]. Effort S (an hour or two), M (half a day to a day). Severity: blocks a task / confuses / cosmetic. Screens are in `shots/`.

| # | Severity | Tag | Finding | Where | Effort |
|---|---|---|---|---|---|
| 1 | blocks (phone) | [ux][bug] | Settings scrolls sideways on the phone: the People table is 742 px wide, actions off-screen, every cell labelled twice | `PeopleCard.tsx:81-150`, `styles.css:214-222` | S |
| 2 | confuses | [ux] | Chart gold used as table text at 2.42:1 (schedule payments, cashflow In, savings by year) | `ProgramSection.tsx:247,385`, `EconomicsSection.tsx:164` | S |
| 3 | cosmetic, the owner's "odd bars" | [ux] | Page-grey `.actions` reused inside white cards: BOM export row, Save profile row, Pricing settings bar (111 px on the phone) | `styles.css:54`, `PricingSection.tsx:229`, `SettingsPage.tsx:88`, `PricingSettings.tsx:563` | S |
| 4 | cosmetic | [ux] | Rows aligned to the bottom edge: Add a person staircase (40/64 px), Add a security key 8 px low, readings-set labels at two heights | `styles.css:51,35,128`, `PeopleCard.tsx:164-186`, `AccountCard.tsx:261-268` | S |
| 5 | cosmetic | [ux] | KPI tiles off the row line: glance tiles are buttons (content centred, 12 px); wrapped labels push values 15 px in Quantities and Savings | `styles.css:178`, `AssessmentPage.tsx:550-575`, `PricingSection.tsx:145`, `EconomicsSection.tsx:57` | S |
| 6 | cosmetic | [ux] | Table typography: number glued to text in four tables; uppercase row headers in Site factor; phone captions right-aligned on numeric cells; captions printed for empty cells | `styles.css:60-62,222`, `ResultsView.tsx:162,188`, `SystemDesign.tsx:187,220` | S |
| 7 | confuses (phone) | [ux] | Six tables scroll sideways on the phone with no affordance (the `.scroll-x` shadow exists but only on the route matrices) | `styles.css:63,265`, `SystemDesign.tsx`, `ProgramSection.tsx`, `AuditResults.tsx` | S |
| 8 | confuses | [ux][engineering] | Cashflow weekly chart skips the empty weeks, so 1 week and 9 weeks are drawn the same width | `ProgramSection.tsx:338`, `backend/solarapp/pricing/program.py:458-479` | S |
| 9 | cosmetic | [ux] | Ragged input grids: 5-column auto-fill with 4 fields leaves an empty right column in six of eight blocks | `styles.css:254-256`, `PricingSection.tsx:27-77`, `EconomicsSection.tsx:24-38`, `ProgramSection.tsx:151-164` | S |
| 10 | cosmetic | [ux] | Gantt row labels truncated with "…" on 5 of 14 rows at 1,034 px (label column capped at 250 px) | `Gantt.tsx:46,65-66` | S |
| 11 | cosmetic | [ux] | Y-axis ticks rounded to whole thousands: "0k 2k 3k 5k 6k" on the monthly bill chart | `EconomicsSection.tsx:109` | S |
| 12 | cosmetic | [copy] | "1 rows, 2 lines each" in the BOM note and exports; "23.8 C per kW/m2" in Internal details | `backend/solarapp/pricing/boq.py:270`, `backend/solarapp/core/simulation.py:47` | S |
| 13 | cosmetic | [ux] | Materials: the "Grid-interactive: unknown" badge wraps to three lines (99 × 49 px) in every all-in-one and inverter row | `MaterialsPage.tsx` electrical cell | S |
| 14 | cosmetic | [ux][copy] | Five profile hints repeat the placeholder under the field, one under a filled field (round 2 item 14) | `SettingsPage.tsx:56` | S |
| 15 | cosmetic | [ux] | Phone details: draft banner's buttons split the sentence; the menu's "admin" row is 160 px wide; the gate page has no brand bar; lead row textarea clips its third line | `AssessmentPage.tsx:384-392`, `styles.css:409`, `App.tsx:60-73`, `styles.css` `.lead-row textarea` | S |
| 16 | cosmetic | [ux] | Bare labels remain in the faces, panels and readings editors (round 2 item 18) | `FacesEditor.tsx`, `PanelsEditor.tsx`, `ReadingsEditor.tsx` | M |

### 1. Settings does not fit the phone: the People table [ux][bug] — blocks a task on the phone

Where: `frontend/src/components/PeopleCard.tsx:81-150` (a plain `<table>` with six columns and `td.cell-actions` set to `white-space: nowrap` at line 124), `frontend/src/styles.css:214-222` (the phone card layout covers `table.appliances, table.materials, table.bills`, later `table.bom`, `table.payments`, `table.categories`; the `td[data-label]::before` caption rule at :222 is global).

What: at 390 px the table is 742 px wide in a 368 px card and the whole page becomes 765 px wide (`phone-report.json` `settings`, `people_table`): the Sign-in badges are cut at the screen edge, the Last sign-in column and the Rename / Reset password / Deactivate links are off-screen, and because every cell carries `data-label` the global caption rule prints "NAME", "USERNAME", "ROLE", "SIGN-IN" inside each cell while the column headers stay visible: the admin row is 147 px tall (`people_doubled_labels`: 25 of 25 cells captioned). Every other card on Settings sits on a page that now pans sideways. Screens: `p17-people-viewport.png`, `p17d-people-table-cut.png`, `p17b-people.png`; desk for comparison `d23-people.png`.

Why it matters: the owner adds an engineer, resets a password or deactivates someone from the phone as often as from the laptop, and this is the only page in the app that breaks the 390 px rule.

Fix (S): give the table `className="people"` and add it to the phone card rule (`table.people, table.people tbody { display: block }`, `thead` hidden, rows as a two-column grid with `.cell-main` for the name and `.cell-actions` full width), exactly as `table.materials` does; drop the `nowrap` on the actions cell under 640 px. Also scope `td[data-label]::before` to the card-layout tables (`table.appliances td[data-label]::before, …`) so a future table with captions cannot double its headers again.

### 2. Chart gold as table text [ux] — confuses

Where: `ProgramSection.tsx:247` (schedule rows of kind `payment_in` get `color: C_IN`), `:385` (cashflow "In" cells), `EconomicsSection.tsx:164` (year table "Savings"); `C_IN`/`C_SAVE` = `#C9A227`, the fill colour of the bars.

What: 14 px regular text in `#C9A227` on white measures 2.42:1 (`measure-report.json` `gold_text_contrast`), below AA for any size. Round 2 introduced `--gold-text #856a14` (4.9:1) for links and eyebrows; these three inline styles reuse the bar colour instead. Screens: `d07-design-program.png` (three gold rows), `d07-design-cashflow.png` (In column), `d07f-savings-years.png`.

Fix (S): keep the bars gold and set the text to `var(--gold-text)` (or make the payment rows bold black with a small gold "payment" badge); same for the red `C_OUT` cells, which pass at 4.6:1 but only just.

### 3. Grey bars inside white cards: `.actions` reused inline [ux] — cosmetic, the owner's "odd bars"

Where: `styles.css:54` (`.actions { position: sticky; background: var(--bg); border-top: 1px solid var(--line) … }`), reused with `position: static; border: 0` but the background left in place at `PricingSection.tsx:229` (`actions bom-actions`), `SettingsPage.tsx:88` (Save profile), and as a sticky bar inside the card at `PricingSettings.tsx:563`.

What (`measure-report.json` `inline_actions_bands`, `settings_actions_bands`, `phone2-report.json` `profile_band`): a `#F5F5F3` stripe inside a `#FFFFFF` card, 70 px tall across the whole Quantities card above the BOM (desk) and 144 px on the phone; 40 px (desk) / 50 px (phone) behind "Save profile"; and a 55 px (desk) / 111 px (phone, three wrapped rows) sticky stripe at the foot of the Pricing settings card, with white card padding showing on both sides of it. Screens: `d06c-outputs-scrolled-quantities.png` (y 585–655), `crop-p-bom-rows.png` (top), `p15c-profile-save-band.png`, `d24z-pricing-actions.png`, `p18y-pricing-actions.png`.

Fix (S): one modifier `.actions.inline { position: static; background: transparent; border: 0; padding: 4px 0 8px }` used by the three places; for the pricing bar keep it sticky but give it `margin: 0 -16px -16px; padding: 10px 16px; border-radius: 0 0 10px 10px` so it bleeds to the card edge, and on the phone put the chip and "Save pricing settings" on one row with Discard and Reset in a second row only while dirty (the bar is then about 60 px, like the project bar).

### 4. Rows aligned to the bottom edge [ux] — cosmetic

Where: `styles.css:51` (`.row { align-items: flex-end }`), `:35` (`.field { margin-bottom: 10px }`), `:128` (`.hint` inside a `.field` instead of as a full-width `.row > .hint`); `PeopleCard.tsx:164-186` (the hint sits inside the username field; the role `.narrow` has no margin; the button wrapper has `paddingBottom: 4`), `AccountCard.tsx:261-268`.

What (`measure-report.json` `settings_rows`, `phone-report.json` `add_form_boxes`): Add a person on the desk: username input top 2294, name 2326, role select 2334, Add 2330, a 40 px staircase; on the phone the name input sits 64 px below the username input and the role/Add pair wraps under them. Add a security key: button 8 px lower than its input. Readings set head: "Air temperature (°C, optional)" wraps, so its label sits 14 px above the others while the inputs align. The faces editor's "remove" links sit 4 px above the inputs' bottom. Screens: `d23b-people-add-form.png`, `p17c-people-add-form.png`, `d22-account.png` (key row), `d03e-card-readings.png`.

Fix (S): move the username hint out of the field to a full-width `.hint` after the row (the rule at `:128` already lays it out), set `.row > .field { margin-bottom: 0 }` so flex-end aligns the inputs rather than the margins, and drop the ad-hoc `paddingBottom: 4` wrappers. One line in `styles.css` plus two markup moves closes all of them.

### 5. KPI tiles off the row line [ux] — cosmetic

Where: `styles.css:178` (`.kpi-link` is a `<button>`; buttons centre their content vertically), `AssessmentPage.tsx:550-575` (the glance tiles), `PricingSection.tsx:145` ("Contract price (VAT included)"), `EconomicsSection.tsx:57` ("Monthly bill, without → with solar"), `SystemDesign.tsx:71-120` (the Inverter tile's nine-line sub-text stretches the whole row to 200 px).

What (`measure-report.json` `kpi_value_offsets`): At a glance values start at 25 / 37 / 37 / 37 / 37 px from the row top (the first tile has three lines, the others are centred), so the labels sit on two different lines across the strip; Quantities and Savings: the wrapped label pushes its value to 40 px while the other four sit at 25. On the phone the glance grid shows the same 12 px step between "Recommended system" and "Contract price". Screens: `d06a-glance.png`, `p06a-glance.png`, `d06c-outputs-scrolled-quantities.png`, `d07-design-savings.png`, `d07-design-system.png`.

Fix (S): `.kpi-link { display: block; align-content: start }` (or `display: grid; align-content: start`), and shorten the two labels ("Contract price" with "VAT included" in the sub, as the glance strip already does; "Monthly bill" with "without → with solar" in the sub). For the System design row, cap the sub-text at two lines with the rest under a "more" or move the inverter's four facts into the Protection table.

### 6. Table typography: numbers glued to words, shouted row headers, phone captions [ux] — cosmetic

Where: `styles.css:60-62` (6 px cell padding; `td.num` right-aligned), `:222` (phone caption inherits the cell's alignment and prints for empty cells), `:242` (`table.kv` is the only reset for row headers); `ResultsView.tsx:162-185` (Site factor table without `kv`), `:188-230` (Panel layout: "Landscape | Rows from the eave"), `SystemDesign.tsx:187` ("Qty | Basis"), `:220` ("Positions | Rows from the eave"), `PricingSection.tsx` BOM ("Qty | Unit").

What (`measure-report.json` `num_then_text_columns`, `uppercase_row_headers`): "12 5", "12 6, 6 (portrait)", "1 pc 1 per string" and "5 pc" read as one token because the number is flush right and the next cell's text flush left with 12 px between them; the Site factor table prints "K (OWNER'S FORMULA, AVERAGE OF ROWS)" and "K_SITE (HEAT AND LOW-LIGHT REMOVED)" because the global uppercase `th` applies to row headers; on the phone the payment-terms captions "SHARE %" and "PLUS DAYS" are right-aligned while "DUE AT" is left-aligned, and the materials cards print "PANEL SIZE" and "ELECTRICAL" over nothing. Screens: `d07-design-system.png` (Panels per face row), `d07g-roof-internal.png`, `p05e-payment-terms.png`, `p14-materials-top.png`.

Fix (S): `td.num + td:not(.num) { padding-left: 18px }`; `className="kv"` on the Site factor table; `td[data-label]::before { text-align: left }` and `td[data-label]:empty { display: none }` under 640 px.

### 7. Phone tables that scroll sideways with no affordance [ux] — confuses on the phone

Where: `styles.css:63` (`.table-wrap { overflow-x: auto }`), `:265-271` (`.scroll-x` shadow and `.scroll-note`, applied only by `PricingSettings.tsx` to the route matrices).

What (`phone-report.json` `xscroll_tables`): six tables wider than 344 px scroll inside their wrapper with no edge shadow and no note: Panels per face (526 px), Protection (359), Panel layout (380), Appliances and the peak hour (646), Schedule (496), the hourly plan and the cashflow (473). The right-hand column is simply cut at the card edge. Screens: `crop-p-system-top.png` bottom, `p07-design-program.png`, `p07-design-cashflow.png`.

Fix (S): under 640 px give every `.table-wrap` the `.scroll-x` background and show `.scroll-note` when `scrollWidth > clientWidth` (a three-line `useElementWidth` check, which already exists in `responsive.ts`), or just add `scroll-x` to the six wrappers.

### 8. Cashflow weekly chart is not to scale [ux][engineering] — confuses

Where: `ProgramSection.tsx:338` (one bar group per entry of `cashflow.weekly`, categorical X axis), `backend/solarapp/pricing/program.py:458-479` (the weekly buckets hold only weeks with a flow: `a1-results.json` has three entries, 2026-10-20, 2026-10-27 and 2026-12-29, for flows that run to 2027-01-04).

What: the eight empty weeks of November and December are missing, so the step from Oct 27 to Dec 29 is drawn as wide as the step from Oct 20 to Oct 27; the balance line looks like it drops two weeks after installation when it drops nine. Screen: `d07-design-cashflow.png`.

Fix (S): emit every week from the first flow to the last (zero in and out, balance carried), or give the chart a time axis.

### 9. Ragged input grids [ux] — cosmetic

Where: `styles.css:254-256` (`.input-grid` auto-fill at 170 px gives five columns at 1,034 px), `PricingSection.tsx:27-77` (four blocks: 2+2 wide, 4, 5, 4 fields), `EconomicsSection.tsx:24-38` (4, 5), `ProgramSection.tsx:151-164` (5, 3).

What (`measure-report.json` `input_grids`): six of the eight blocks leave one or two empty cells at the right, so the field edges step in and out down the card. Screens: `d05b-pricing-inputs.png`, `d05c-savings-inputs.png`, `d05d-program-inputs.png`.

Fix (S): one `.input-grid` per card instead of one per thematic row (the labels carry the theme), or `repeat(4, 1fr)` above 640 px so the first and last rows line up.

### 10. Gantt labels truncated [ux] — cosmetic

Where: `Gantt.tsx:46` (`labelW = min(250, 34 %)`), `:65-66` (37 characters then "…").

What: "Electrical plans, signed and sealed…", "Net metering application with your…", "On delivery of materials to your ho…", "Final electrical inspection certifi…", "Electric company inspection; net me…" on the desk; the full text is only in a `<title>`, invisible on touch. Screen: `d07-design-program.png`, `p06c-outputs-jumped-program.png`.

Fix (S): cap at 320 px / 40 % on the desk, or wrap long labels to two lines with a 34 px row.

### 11. Chart axis ticks [ux] — cosmetic

Where: `EconomicsSection.tsx:109` (`Math.round(v / 1000)k` on ticks at 1,500 steps). What: the monthly-bill chart's axis reads "0k 2k 3k 5k 6k". Screen: `d07-design-savings.png`. Fix (S): one decimal when the step is under 1,000 (`1.5k`), or ticks at `[0, 2000, 4000, 6000]`.

### 12. Copy and unit slips in generated text [copy] — cosmetic

`backend/solarapp/pricing/boq.py:270`: "1 rows, 2 lines each, 2.4 m rails" in the BOM note, the CSV and the XLSX (`doc-bom.csv` line 5) — use the `plural` helper. `backend/solarapp/core/simulation.py:47`: "site-measured rise of 23.8 C per kW/m2 above ambient" — "°C per kW/m²" like the rest of the card. Screens: `d07b-quantities-internal.png`, `d07g-roof-internal.png`.

### 13. Materials: the Electrical badge [ux] — cosmetic

Where: `MaterialsPage.tsx` (the electrical cell renders "Grid-interactive: unknown" as one `.badge.bad`). What: a 99 × 49 px pill wrapping to three lines in every inverter and all-in-one row, the loudest thing on the page. Screen: `d20-materials-viewport.png`. Fix (S): "Grid: unknown" / "Grid: yes" / "Grid: no" with the long form in a title, or an em-dash for "unknown" and the badge only for "no".

### 14. Profile hints repeat the placeholder [ux][copy] — cosmetic (round 2 item 14, not done)

Where: `SettingsPage.tsx:56` (`hint && !long` shows the hint always). What (`measure-report.json` `profile_grid_hints`): Owner's name, Where you install (filled), Messenger link, Brands you install, After a booking: the same sentence as placeholder and as hint, which also makes the grid rows uneven (83–99 px against 67). Screen: `d21b-profile.png`. Fix (S): show the hint only when the field is empty, or use it as the placeholder alone.

### 15. Phone details [ux] — cosmetic

- Draft banner: "Unsaved edits from … are saved on this device. [Restore them] [Discard]" wraps with the buttons inside the sentence (`AssessmentPage.tsx:384-392`); put the buttons on their own line under 640 px. Screen: `p08e-draft-banner.png`.
- The open menu's "admin" row is 160 px wide while the others fill the width (`styles.css:409` `.who { max-width: 160px }` still applies inside `.topbar.open nav.right`); its highlight and tap area are narrower than the rest. Screen: `p02c-menu-open.png`.
- The first-sign-in gate renders without the brand bar that the login page has (`App.tsx:60-73`), so the engineer's first screen has no logo and no company name. Screens: `g-desk-01-gate.png`, `g-phone-01-gate.png`.
- Leads: the note textarea shows two lines and clips the third mid-letter (`.lead-row textarea { min-height: 44px }`), and the facts line prints the address twice ("Brgy. Labuin, Pila, Laguna · Pila, Laguna"). [crm] Screen: `d30-leads-with-lead.png`.

### 16. Bare labels in the three roof editors [ux] — cosmetic (round 2 item 18)

`FacesEditor.tsx`, `PanelsEditor.tsx`, `ReadingsEditor.tsx` still render `<label>` without `htmlFor` (`desk-a-report.json` `site_labels`: 2 of 18 attached); tapping "Eave length (m)" on the phone does not focus the field. The `Field` component exists; converting the three editors is mechanical. Effort M.

## What is sound (checked, no defect)

- Widths: every signed-in page measures 390 / 1280 px except Settings on the phone (finding 1); no element sticks out of its container on any page; no `<hr>`, no empty bordered boxes, no line-thin bordered elements anywhere (`*-report.json` `over`, `bordered`, `bars`).
- Sticky chrome: the tabs (54 px) and the sub-tabs (44 px) stack to 94 px on the desk and never overlap content on a jump; the phone keeps the index as a jump list (102 px, static) and the bar at 61 px (chip, Save, Calculate on one row); the stale banner is in flow (44 px desk, 106 px phone) with its own Calculate.
- Tap targets: on the phone every input, select and button is 44 px; toggles 36–40 px; the only sub-36 targets are the Leaflet attribution links and the brand mark. Text under 13 px on the phone is limited to table headers (12.5 px), KPI labels (12 px) and badges (12 px).
- Contrast: muted text 4.9–5.4:1, gold links 4.9:1, badges 4.7:1 and up, warn and info banners pass; only the chart gold as text fails (finding 2).
- Sign-in screens: wrong password, the temporary-password gate (no top bar, Sign out offered, short password refused with "Use at least 12 characters; a short sentence works well.", mismatch keeps the button disabled, success lands on Projects with the person's name in the bar), the engineer's views (no People card, read-only profile and pricing, no New item or Import on Materials), the authenticator set-up (password required first, 168 px QR, typed key, wrong code refused, eight backup codes in a monospace grid, "I have saved them", status line with the codes left, turning it off), the People card (add, temporary password shown once with the "in person or by a call" line, rename, role select, deactivate badge and reactivate, the username rule message).
- Design and outputs: the glance strip's tiles scroll to their cards; the index follows the scroll; the seven cards carry the right content in the right order; hard warnings are red, ordinary ones muted; the plan drawings number panels from the eave, mark the sized ones solid, hatch the wall strip, letter the tree and label the eave, scale and direction at 440 and 344 px; the Gantt has weeks, milestones, hollow payment diamonds and a legend, and scrolls with a note on the phone; the BOM edits, removes, restores and adds items; the Documents card lists all six documents with a state badge, the reason when not ready, and the card's next-step field.
- Documents: roof check (2 pages: figures, chart, table, roof table; plans, measured block, next step), proposal (3 pages, utility-statement layout, plans with the sized panels, reminders, payment schedule, charges, schedule, questions, acceptance), program of works (4 landscape pages: Gantt, schedule, hourly day, task list, cashflow, headers repeated across page breaks), the card (1080 × 2496, readable at phone size), BOM CSV with a BOM marker for Excel and XLSX. No stray rule, no orphan page.
- Website: home, brownouts, net metering, about, privacy, 404 ("That page is not here.") and the estimate on both widths; the widget shows no duplicate header or footer; the four questions, the result hero, the no-battery alternative, the details block, the booking form (sticky bar hidden while it is in view), the thank-you with "Copy my estimate", the off-grid wording ("no export"). The booking lands in Leads with the number, the time, what the visitor saw; Start assessment makes a project with the name, address, pin, notes and the bill (380 kWh, ₱4,900) prefilled.

## Top five

1. Give the People table the phone card layout and scope the caption rule (finding 1): the only page that breaks the 390 px rule.
2. `--gold-text` for the three tables that print the chart gold as text (2).
3. An `.actions.inline` modifier without the page background, and a one-row pricing bar on the phone (3).
4. Align `.row` on the inputs, not the margins: fixes the People staircase, the key row and the readings labels (4).
5. `.kpi-link` top-aligned and the two wrapped labels shortened (5); then the table typography batch (6) and the scroll affordance on the six phone tables (7).

## Screenshots (`scratchpad/agents3/ux/shots/`)

Desk back office (1280×900): `d01-login`, `d01b-login-error`; `d02-projects`, `d02b-projects-filter`, `d02c-projects-nomatch`; `d03-site-viewport/-full`, `d03a-page-head`, `d03b..e-card-{site,faces,panels,readings}`, `d03f-card-faces-more`, `d03g-actions`; `d04-audit-viewport/-full`, `d04b-audit-window-editor`; `d05-pricing-viewport/-full`, `d05b-pricing-inputs`, `d05c-savings-inputs`, `d05d-program-inputs`; `d06-outputs-viewport/-full`, `d06a-glance`, `d06b-subtabs`, `d06c-outputs-scrolled-quantities`, `d06d-outputs-all-open-full`, `d06e-page-head-outputs`; `d07-design-{roof,system,quantities,program,cashflow,savings,documents}`, `d07b-quantities-internal`, `d07c-quantities-proposal-lines`, `d07d/d2-quantities-add-item`, `d07e-program-tasks`, `d07f-savings-years`, `d07g-roof-internal`; `d08-actions-unsaved`, `d08b-outputs-stale-unsaved`, `d08c-draft-banner`; `d09-stale-viewport/-full`, `d09b-stale-documents`, `d09c-stale-banner`; `d10-uncalculated-viewport/-full`, `d10b-checklist`, `d10c-uncalculated-pricing`, `d10d-uncalculated-audit-empty`, `d10e-readings-empty`, `d10f-panels-one`; `d11-new-viewport/-full`, `d11b..f-new-*`; `d12-missing-project`, `d12b-no-page`; `d13-leads` (empty); `d20-materials-viewport/-full`, `d20b-materials-nomatch`, `d20c-materials-search`, `d20d/d2-materials-edit`, `d20e/e2-materials-new-item`, `d20f-materials-import`; `d21-settings-viewport/-full`, `d21b-profile`, `d21c-profile-unsaved`; `d22-account`, `d22b-account-needs-confirm`, `d22c/c2-account-totp-setup`, `d22d-account-wrong-code`, `d22e/e2-account-backup-codes`, `d22f-account-totp-on`, `d22g-account-totp-off`; `d23-people`, `d23b-people-add-form`, `d23c-people-add-error`, `d23d-people-temp-password`, `d23e-people-deactivated`; `d24-01..20-*` (every pricing settings card), `d24-pricing-closed`, `d24x-settings-full-open`, `d24y-pricing-edited`, `d24z-pricing-actions`; `d25-weather`; `d30-leads-with-lead(-full)`, `d30b-lead-row`, `d31-project-from-lead`, `d31b-project-from-lead-audit`.

Phone back office (390×844 @2x): `p01-login`, `p01b-login-error`; `p02-projects(-full)`, `p02b-topbar`, `p02c-menu-open`, `p02d-projects-card`; `p03-site-top/-full`, `p03a-page-head`, `p03b-tabs`, `p03c..f-card-*`, `p03g-card-faces-more`, `p03h-site-bottom`, `p03i-actions`; `p04-audit-top/-full`, `p04b-audit-window-editor`, `p04b2-window-editor-row`, `p04c-audit-bills`, `p04d-audit-system`; `p05-pricing-top/-full`, `p05b..d-*-inputs`, `p05e-payment-terms`; `p06-outputs-top/-full`, `p06a-glance`, `p06b-subtabs`, `p06c-outputs-jumped-program`, `p06d-outputs-bottom`; `p07-design-{roof,system,quantities,program,cashflow,savings,documents}`, `p07b-quantities-internal`, `p07e-program-tasks`, `p07f-savings-years`, `p07g-roof-internal`, `p07h-documents-viewport`; `p08-outputs-stale-unsaved`, `p08b-stale-banner`, `p08c-actions-unsaved`, `p08d-bom-actions-dirty`, `p08e-draft-banner`; `p09-stale-top`, `p09b-stale-documents`; `p10-uncalculated-top/-full`, `p10b-checklist`, `p10c-actions-disabled`; `p11-new-top/-full`, `p11b-new-face`, `p11c-new-readings`; `p12-missing`; `p13-leads(-full)`; `p14-materials-top/-full`, `p14b/b2-materials-edit`, `p14c-materials-new`, `p14d-materials-import`; `p15-settings-top/-full`, `p15b-profile`, `p15c-profile-save-band`; `p16-account`, `p16b/b2-totp-setup`, `p16c/c2-backup-codes`, `p16d-account-on`; `p17-people-viewport`, `p17b-people`, `p17c-people-add-form`, `p17d-people-table-cut`, `p17e-people-table-scrolled-right`; `p18-01..20-*` (pricing cards), `p18y-pricing-actions`, `p18z-settings-bottom`; `p19-weather`; `p30-leads-with-lead(-full)`, `p30b-lead-row`; crops `crop-p-{quantities-kpis-actions,bom-rows,system-top,program-top,savings-top}`.

Engineer's first sign-in: `g-desk-01-gate(-full)`, `g-desk-02-gate-error`, `g-desk-03-after-gate`, `g-desk-04-settings-engineer`, `g-desk-04b-profile-readonly`, `g-desk-04c-pricing-readonly`, `g-desk-05-materials-engineer`; the same with `g-phone-` plus `g-phone-06-menu-engineer`.

Documents: `doc-roof-check.pdf` → `pdf-roof-check-1..2`; `doc-proposal.pdf` → `pdf-proposal-1..3`; `doc-program.pdf` → `pdf-program-1..4`; `doc-card.png`; `doc-bom.csv`, `doc-bom.xlsx`.

Website desk (1280): `w-d-{home,brownouts,net-metering,about,privacy,this-page-does-not-exist}-top/-full`, `w-d-estimate-1-top/-full`, `-2-filled`, `-3-result-top/-full`, `-3b-hero`, `-4-alternative`, `-5-details`, `-6-book-form`, `-6b-book-card`, `-7-book-filled`, `-8-thanks`, `-8b-thanks-box`, `-9-bottom`, `-10-offgrid`. Website phone (390): the same with `w-p-`, plus `w-p-home-menu`.
