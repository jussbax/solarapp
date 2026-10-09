# The solar engineering app: outputs, boundary and plan

Written after the second audit round (engineering, UX, marketing and copy,
security) on 8 October 2026. This is the working plan; DECISIONS.md records
what was decided and why once each batch lands.

## 1. What the app is

One record per site, called a project. It holds the site, the roof, the
readings, the energy audit, the design, the quantities, the program of works,
the cashflow projection and the documents those produce. It is not a CRM and
not a project-management tool: leads, follow-ups and sales stages belong to a
CRM module; crews, purchases, progress and actuals belong to a PM module.
Both will link to the engineering project by its id.

## 2. The engineering deliverables, corrected

The owner's list (plans, program of works, BOM, BOQ, Gantt chart, cashflow)
is right but short. Below is the full set a Philippine rooftop solar
engineering firm produces, by stage, with who consumes it and the status in
the app today. "Verify" marks a regulatory fact to confirm with the PEE or
the distribution utility (DU) before it prints on a document.

Consumers: C customer, L the LGU (building official or city electrician),
D the DU (Meralco, BATELEC II, FLECO), W the crew, P the PEE who signs,
B a bank, O the owner internally.

### Site assessment

| # | Deliverable | For | Status |
|---|---|---|---|
| 1 | Site survey record: pin, photos, roof type and material, purlin or rafter spacing, age, service entrance (meter, DU account, main breaker, phase), wall space for the inverter and battery, cable route lengths | W, P | Partial: pin, faces, walls, trees, readings. Missing roof construction, photos, service entrance, route lengths |
| 2 | Roof check: what the roof can hold and make, with shade notes | C | Exists (PDF and card) |
| 3 | Shade study by month | C, P | Exists; no horizon photo |
| 4 | Meter reading sheet: readings, k, thermal rise, quality flags | O | Exists |
| 5 | Energy audit and load schedule | C, P | Exists; the PEC-format schedule of loads for the permit is missing |

### Design

| # | Deliverable | For | Status |
|---|---|---|---|
| 6 | Sizing report: PV, battery, inverter, coverage, monthly balance, assumptions | C, P, B | Exists, with losses after the panels, the battery balanced over the hourly year with autonomy and loss-of-load, and the panels allocated to the best faces |
| 7 | Array layout drawing per face: panels, rails, feet, strings, setbacks, obstacles, dimensions | W, L, D, C | Partial: a plan drawing per face with panels, strips, obstacles, strings and the used panels, on the roof check and the proposal; rails and feet not yet drawn |
| 8 | String design table: panels per string per MPPT, Voc cold, Vmp hot, Isc, margins | P, D | Missing |
| 9 | Single-line diagram: array, strings, DC protection and disconnect, SPDs, inverter, battery, AC disconnect, breakers, point of interconnection, two-way meter, grounding | L, D, P | Missing |
| 10 | Design analysis sheet: conductor ampacity and derating, OCPD per circuit, voltage drop, EGC and GEC, conduit fill | P, L | Partial: gauges and drop computed, no OCPD coordination, no grounding conductors, no printout |
| 11 | Grounding, bonding and surge detail | P, L | Partial (BOQ lines only) |
| 12 | Mounting and structural check: roof type, fastener schedule, uplift and dead load | P, W | Missing |
| 13 | Equipment data and certificates: datasheets, the inverter's anti-islanding certificate, battery BMS, warranties | D, L, C | Partial: electrical data, a grid-interactive flag and the certificate text on each item; no datasheet files yet |
| 14 | Bill of materials (BOM): every item, code, spec, quantity, role, with manual edits | W, O | Exists, exports as CSV and XLSX |
| 15 | Bill of quantities (BOQ) and internal cost build-up: the BOM priced | O | Exists |
| 16 | Proposal: price, system, savings, payment schedule, acceptance | C, B | Exists |
| 17 | Customer economics: bill before and after, payback, NPV, IRR | C, B | Exists |

### Permits and the DU application

| # | Deliverable | For | Status |
|---|---|---|---|
| 18 | Electrical plans, signed and sealed (contents in section 4) | L, D | Missing; only a fee line and a two-day task |
| 19 | Electrical permit application data pack and checklist; later the CFEI | L | Partial: dates only |
| 20 | DU net-metering application pack: form, bill, ID, proof of ownership, sealed plans and SLD, equipment specs and certificates, site plan, DIS where required, agreement, ERC certificate of compliance (verify the current list with each DU) | D | Missing; fees and dates only |
| 21 | CFEI and DU inspection record, two-way meter installation | L, D, C | Date only |

### Procurement and construction

| # | Deliverable | For | Status |
|---|---|---|---|
| 22 | Pickup list per supplier with cash | O | Exists |
| 23 | Program of works and Gantt chart: dated tasks and milestones with dependencies; the customer's schedule | C, W, O | Partial: schedule, hourly plan with duration floors and a Gantt chart; dependencies and the DU sequence still to do |
| 24 | Crew day plan, method statement and safety plan | W | Partial (hour plan); safety content missing |
| 25 | Cashflow and payment schedule | O, B | Exists |
| 26 | Site diary, progress, change orders | O | PM module, out of scope |

### Commissioning and handover

| # | Deliverable | For | Status |
|---|---|---|---|
| 27 | Commissioning test report: visual checks, per-string Voc, Isc and polarity, insulation resistance, earth continuity and electrode resistance, AC voltages, anti-islanding and transfer test, inverter settings including export limit, battery BMS state, sign-off | P, D, C | Missing |
| 28 | As-built drawings: layout and SLD as installed, string map, serial numbers | C, D, L | Missing |
| 29 | O&M manual and handover pack: user guide, emergency shutdown, cleaning schedule, warranties, serials, monitoring login | C | Missing (warranty sentences exist) |
| 30 | Labels and placards schedule (PEC 6.90 marking) | W, L | Missing |
| 31 | DU documents: agreement copy, meter installation record, first credited bill | C, D | Missing |

### Operation

| # | Deliverable | For | Status |
|---|---|---|---|
| 32 | Performance check: actual production against the design, by month | C, O | Missing (needs actuals) |
| 33 | Maintenance schedule | C, O | Schedule is engineering; the visit log is PM |

## 3. BOM against BOQ

The bill of materials is the engineering list: every item with its code,
specification, quantity, unit and role, derived from the design and carrying
the manual edits. The crew loads it and the PEE checks it against the
drawings. The bill of quantities is the same list priced: landed cost,
markup, freight, labour, fees, VAT, summarised into the sections the customer
sees as "Details of charges". The app has both; the words will be used that
way in the back office and the documents.

## 4. What "plans" must contain

For the LGU electrical permit, as far as the reviewers are confident (verify
the LGU's own checklist and the signatory with the PEE):

- Title sheet: owner, location, project, PEE name, PRC licence, PTR and TIN,
  signature block; vicinity map.
- Roof plan with the array layout at scale: dimensions, setbacks,
  obstacles, string grouping; mounting detail (rail, foot, fastener,
  penetration seal).
- Single-line diagram and a riser or wiring diagram with the conduit runs.
- Schedule of loads in PEC format with the PV system as a source, and the
  point of interconnection stated.
- Design analysis: string table, conductor ampacity and derating, OCPD per
  circuit, voltage drop, EGC and GEC, conduit fill, short-circuit note.
- Grounding and bonding detail; SPD placement; equipment specifications;
  general notes citing PEC 2017 Article 6.90 and the storage-battery
  article; the NSCP wind zone for the mounting.

For the DU net-metering application (verify with Meralco and BATELEC II;
both publish checklists): the signed form, the latest bill and an ID, proof
of ownership, the sealed plans and SLD, module and inverter datasheets with
the anti-islanding certificate, a site plan, the DU's distribution impact
study where required, then the net-metering agreement, the CFEI, the DU
inspection and the two-way meter. The ERC certificate of compliance is a
separate filing; confirm who files it today.

## 5. The boundary

Engineering project (this app), one per site, keyed by project id: site,
customer reference (name and address; no marketing data), roof and
construction, readings and k, energy audit and bills, design (layout,
strings, sizing with assumptions, BOM, circuit design, grounding, mounting),
commercial design (BOQ, proposal, economics, payment plan, program of works,
cashflow projection), revisions, and every document generated. Its own
status is about the engineering: draft, surveyed, designed, proposal issued,
plans issued, as-built.

CRM module (later): leads and contacts, source and campaign, the estimate
log and funnel counts, callback cadence, consent and retention, messages,
proposal sent and accepted dates, sales stages (lead, contacted, quoted,
signed, lost).

PM module (later): the job after signing: sourcing, installing,
commissioned, net metering, closed; purchase orders against the pickup
list; crew and timesheets against the program; site diary and photos; change
orders; actual payments and costs against the cashflow projection; permit
and DU case tracking; commissioning actuals; warranty visits.

Links: everything carries the project id. A website lead lives in the CRM;
"Start assessment from lead" creates the project with the customer
reference, the pin or town and the bill. When the proposal is accepted the
PM job is created from the same id and reads the BOM, program and cashflow
as its baseline. The engineering app exposes read-only views of its design
and documents to the other two and never stores their state.

The website keeps three calls: status, estimate and lead. The estimate keeps
using the engineering engines so the website figure and the later proposal
agree. The lead endpoint writes to the bookings table, which is the CRM's
data: its statuses, notes and funnel counters are served by `/api/leads`
and have no screen in the engineering app (the owner's decision, round 3:
"the leads tab should not be in the solar engineering app"). The
engineering app keeps one hand-off, Projects › "From a website booking",
which lists the open bookings and starts a project from one.

What has moved out of the engineering screens: the Leads page with its
funnel, statuses and notes; the funnel card and the lead badges on the
list; the stages lead and contacted; preferred time, callback promise and
the privacy line (website settings); the estimate page link in the nav.
What stays: the card's next step as a saved field, the hour-by-hour crew
plan, the pickup list and the cashflow projection (plans, not tracking).
The job stage (assessed to closed) stays on the record for the CRM and PM
modules but has no screen since round 4: the project head and the list
show the engineering status read from the facts (draft, surveyed,
designed, proposal issued; see DECISIONS.md "Round 4: the panel in the
background, and an engineering status instead of the job stage").

## 6. Findings from the four audits, and what happens to each

Done in the security round (pushed): keyed session cookie, step-up for key
management, sign out everywhere, atomic two-factor file, passkey challenge
limits, body caps, embed CSP, tunnel-only visitor address.

Being fixed now, no decision needed (the spot-clean batch):

- Documents: one stale rule for every document, server and client; the
  proposal's battery size from the BOM; catalogue names replaced by
  quantity, rating and brand; a "Measured on your roof" block and no orphan
  page on the roof check; the reading time on the card; the program PDF's
  hourly table kept together; proposal wording (quantities line, crew
  plurals, same-day payments, tools folded into installation, one "valid
  until"); the website estimate carried onto the proposal and the card; a
  "What you get" block on the proposal.
- Website: placeholders stripped from the public build until real photos
  exist; the net-metering illustration figures from the engine; "often lower
  than the estimate" removed; the empty warranties card and the static
  warranty claims hidden until the years are filled; absolute share image
  and page URLs; the widget's duplicate header and footer when embedded;
  the sticky bar hidden while the booking form is in view; claims softened
  (tier one, transfer on sale, battery share, battery size); estimate copy
  slips; "solar engineering" positioning with a "What you get on paper"
  section; one primary button label; term consistency (ERC certificate of
  compliance, two-way meter, BOM); the lead email line by line; a website
  URL setting for the QR and the summaries.
- Estimate engine: very small usage refused with a plain message; singular
  "panel"; no "0 kWh battery"; the battery figure from the priced unit.
- Back office: per-row k values no longer shift when a reading is dropped
  (dropped rows marked); impossible inputs flagged where typed (no-fit
  faces, unusable readings, zero-panel calculations); offline and
  validation messages in the owner's words; number formats from one helper;
  appliance table fits the desk; the panel "Use" choice can go back to
  automatic; time inputs show their defaults; installer notes under the
  customer KPIs; one "next step" line instead of three empty cards after the
  first calculation; a text colour that passes contrast; back links on dead
  ends; the card's next step as a saved field; the login remembers the last
  method and offers the other as a normal button; phone details (delete
  button placement, pricing inputs grid, k under each reading, route matrix
  hint); a nudge to add a second key.

Approved on 8 October and built (see DECISIONS.md: the boundary, the
drawings, the engineering numbers): A, the separation (and in round 3 the
Leads page left the app altogether; the hand-off stays on the Projects
page), and B, the Design and outputs step with the plan drawing, the Gantt
chart, the documents card and the phone layouts. Round 3 (9 October, see
`docs/audits/round-3/00-plan.md`) then closed the hardware rules, the
money findings, the customer's story and the UI. What remains of the
engineering order is in section 7's status line.

## 7. The engineering build order and the decisions it needs

Status on 9 October 2026: item 1 has its data fields on the materials
items and the default per kind (the eco-hybrid exports, per the owner); the
string table waits on the datasheets. Item 2 is built (breakers and
conductors coordinated per circuit, the grid side on the inverter's input
rating, bonding and lugs in the BOM, conductor count), except derating.
Item 4 is built. Item 5 has the export-limiter role and the certificate
warning; the checklist, lead times and fees wait on the DU. Item 8 is built
(task floors and the late-finish allowance). Item 9: VAT is exact on the
rounded contract and every job carries the 5 % commission by the owner's
rule; the VAT invoice in the cashflow waits on the accountant. Items 3, 6,
7 and 10 are open.

1. Electrical data on the materials items and a grid-interactive flag:
   panels get Voc, Vmp, Isc, Imp and the temperature coefficients;
   inverters get the maximum PV voltage, MPPT window and count, current per
   MPPT, AC input current, battery current, the grid-interactive flag and
   the certificate; batteries get the continuous current. A string design
   table (Voc at the coldest cell, Vmp at the hottest, Isc per MPPT, margins)
   printed for the PEE. Decision needed: the default inverter. Today every
   job is designed on FS-INV-008, an off-grid type that cannot export; the
   workbook's own sample job used FS-INV-001, the grid-tie hybrid with the
   IEC 61727 and 62116 listing, at about PHP 18,000 more. The reviewer's
   recommendation: a default per system kind, grid-interactive for anything
   with net metering. Three to four days. (Decided on 8 October: the
   eco-hybrid can export and is the default on every kind; a grid-tie unit
   needs the owner's say.)
2. Circuit design sheet: breaker per circuit coordinated with the conductor
   (today a 63 A breaker sits on 8 mm² wire rated 40 A), the grid-side
   breaker from the inverter's AC input current, equipment and electrode
   grounding conductors and array bonding in the BOM, conductor count per
   circuit, derating, the 3.5 mm² ampacity entry checked against the PEC
   table. One to two days.
3. Plans data pack: array layout drawing and single-line diagram as SVG,
   schedule of loads and the design analysis in one PDF for the PEE's title
   sheet and seal. Three to four days.
4. Numbers the customer will later compare with the bill: system losses
   after the panels (inverter, wiring, soiling, about ten percent in total,
   editable), the battery balanced over the hourly year with days of
   autonomy and a loss-of-load figure, and the sized panels simulated on the
   face they occupy. Decision needed: the autonomy allowance (the reviewer
   suggests one day as the default; the owner's rule today is none) and the
   loss figures. Two days.
5. DU pack: datasheet and certificate attachments per item, a checklist
   per DU, the schedule corrected so the two-way meter follows the CFEI and
   the agreement, a distribution impact study step with its fee, the
   export-limit CT and placards in the BOM. Decision needed: the real lead
   times and fees for Meralco and BATELEC II. Two to three days.
6. Commissioning test report, as-built and handover templates generated
   from the design with blanks for the measured values. Two days.
7. Roof construction fields, L-foot spacing from the purlin spacing, an
   uplift flag for tile, concrete, old or thin roofs. Two days; the uplift
   calculation itself is a later, larger piece.
8. Program of works: minimum task durations (commissioning at least two
   hours, battery and inverter at least an hour each) and a calibration of
   the ground rates from the next jobs' timesheets. Decision needed: the
   floors, since today's ten-minute commissioning is a faithful port of the
   workbook. Half a day for the floors.
9. Cashflow tax lines: VAT net of input VAT on the quarterly deadline, the
   agent commission per job with a default of none, expanded withholding tax
   for business customers. Decision needed: confirm with the accountant.
   One day.
10. Net-metering credit carry-over and the DU's fixed charges in the bill
    after solar; a "size to best payback" option beside net-zero. One day.

## 8. Inputs only the owner can supply

- The company profile in Settings: phone, Messenger link, Facebook page,
  email, owner's name, the PEE's name and PRC number, the brands line, where
  to pay, the callback promise.
- The warranty figures: set on 9 October (panel product 12, battery 5,
  inverter 5, workmanship 2; panel performance still blank). The savings
  view replaces the battery at the warranty interval; a per-product
  override exists for a datasheet that says otherwise.
- Real photos with town and system size; the decision whether to show
  "Recent installations" before the first installs.
- The website address (pldevinc.com) and the back-office address, as two
  settings.
- The default tariff (PHP 12.00 per kWh) and the export credit (PHP 6.50)
  checked against current bills, and whether fixed or minimum charges
  remain.
- The minimum monthly usage below which the estimate declines (60 kWh is
  the suggestion).
- Verification with the DU of the net-metering transfer on sale, the
  current application checklist, the lead times and fees.
- Panel and inverter datasheets for the electrical data in item 1 of
  section 7.
- SMTP details if the lead email is wanted.
