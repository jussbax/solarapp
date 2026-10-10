# Solar simulator: design decisions

Agreed with the owner before the build started. Keep this file current when a
decision changes; the code follows it.

This file is a log in the order the decisions were made; where a later
section conflicts with an earlier one, the later one stands. Where things
stand on 9 October 2026: the app is a solar engineering app (site
assessment, energy audit and sizing, design, BOM and BOQ, program of works,
cashflow, customer documents) for the owner and their engineers, each with
their own account; website bookings are the CRM's data and only start a
project here; the pricing follows the owner's workbook to the peso; the
customer documents open with the customer's situation and solution; the
audit team under `.claude/agents` reviews each round. The sections that
hold the current rules are "Accounts", "The Leads tab leaves the
engineering app", "Money, round three", "The customer's story on paper",
"The clean form" and "Round 3, batch 1".

## Purpose

Estimate what a roof in the Philippines can produce, combining the company's
on-site readings (UNI-T UT381PV irradiance meter and UT673PV+ MPPT meter on a
50 W test panel) with PVGIS typical-year weather data. Roof-level production
only at this stage: no inverter, wiring, financial or sizing modules yet
(the first stage; modules 2 to 5 followed, below).

## Data

- Source for all computations: PVGIS typical meteorological year (TMY),
  one file per 0.25 degree grid cell, downloaded once for the whole
  Philippines (land and coastal cells). For the Philippines PVGIS only has
  its ERA5 reanalysis database. After the one-time download the server makes
  no outside calls. Map tiles are fetched by the browser from OpenStreetMap;
  that outside call was accepted.
- NASA POWER monthly climatology is downloaded once as a reference only. It
  is shown on the internal page next to PVGIS monthly horizontal irradiation
  and is never used in the results, to avoid mixing two datasets.
- Nearest grid cell to the site is used, which is what PVGIS itself does.
- PVGIS hourly values are labelled by the start of the hour and carry an
  `irradiance_time_offset` of 0.5 h (ERA5). Verified against clear-sky
  geometry on the Manila cell: evaluating the sun position at label + 0.5 h
  gives symmetric sunrise and sunset behaviour. The offset is stored per
  cell and applied in the simulation.
- At Manila the NASA POWER annual average is about 8 percent above PVGIS
  ERA5 (5.10 versus 4.70 kWh/m2/day). This gap is the honest size of the
  weather-data uncertainty and is shown on the internal page only.
- The dataset lives outside git in `data/` on the server. The app refuses to
  produce a customer PDF from a synthetic (test) dataset.

## Readings and the k factor

- Each reading row pairs an irradiance reading, an MPPT power reading and the
  module surface temperature from the probe, taken at the same moment. Three
  rows per set. A set belongs to a roof face or to the whole site.
- S1 adopted: k is computed per row and the three are averaged.
- S7 adopted: an editable test-panel calibration factor, default 1.0,
  multiplies the 50 W rating.
- S2 adopted: k is split into a heat part and a site part using the PVGIS
  module model (Huld, crystalline silicon):
  `k_site = k_row / eta_rel(G_row, T_module_row)`.
  The remainder, `k_site`, is applied as a constant in the simulation.
- The on-site temperature also calibrates the thermal model: module
  temperature rise above ambient per kW/m2 of irradiance is taken from the
  readings. When no ambient temperature was recorded, the typical air
  temperature for that month and hour from the PVGIS cell is used and flagged.
  Implausible rises fall back to the PVGIS Faiman model with a warning.
- Several reading sets: the set with the highest `k_site` is used for the
  whole site (owner's rule), including its thermal rise.
- S6 adopted, internal only: warnings for average irradiance below 500 W/m2,
  spread above 10 percent between the three rows, cloudy or overcast sky,
  and out-of-range k. Never shown to the customer.
- S5 on hold: no losses beyond the roof. Results are "at the panels".

## Roof and panels

- Inputs per roof face in metres: length, width, tilt, compass facing.
- Usable dimensions subtract one setback value from each dimension
  (default 0.6 m, editable), then rows x columns. Both panel orientations are
  tried and the larger count wins. Gap between panels is editable, default 0
  to match the current method. A manual count override exists per face.
  The old rule of thumb is not shown; the count is fully automated.
- Panels are typed in per assessment (name, Wp, length, width); several
  candidates can be entered and the app shows the panel and count that give
  the most kWp, which is used unless another candidate is ticked. A shared
  catalogue comes later.

## Simulation

- Hourly over the typical year, per face: Perez transposition to the face's
  tilt and facing, Martin-Ruiz reflection losses, Huld module model
  (PVGIS 5 coefficients), site thermal rise, times panel count and Wp,
  times `k_site`.
- S3 adopted: month totals use the hours of that month, so actual days.
- S4 adopted: in-plane irradiation per face, not one location-wide number.
- Reference simulation: same hourly run with `k_site = 1` and the PVGIS
  default thermal model. The "measured versus PVGIS" figure is
  `(measured - reference) / reference`, shown as a signed percent.
- For continuity the owner's current formula is also shown:
  `N x Wp x k_raw x average in-plane sun hours x 30`.
- No desk estimate mode: every assessment needs on-site readings. A
  "simplified quick estimate" from location and monthly kWh consumption is
  planned once the energy audit and sizing modules exist.

## Product

- Web app, single Docker container on an Ubuntu office server behind a
  Cloudflare Tunnel. Python FastAPI backend with pvlib, SQLite storage,
  React frontend. One user for now, with saved assessments.
- Customer PDF contains only what the customer cares about. Readings, k,
  warnings and data details stay on the internal page.
- English only.

## Energy audit and sizing (module 2)

- Appliances carry nameplate input watts, quantity, brand, model and type.
  Every appliance typed is added to a shared catalogue for reuse; the
  catalogue starts empty. The same appliance may appear twice with different
  quantities when groups run at different hours (lights in different areas).
- Usage is entered as windows: start time, end time, weekdays, months.
  Duration is derived. A window whose end is at or before its start crosses
  midnight; equal start and end is 24 hours. Months default to all twelve;
  the owner accepted that a year cannot be observed before the proposal.
- Average draw in a window = nameplate x quantity x duty factor. Duty
  factors default from the type and can be overridden; the field does not
  clamp-meter appliances. Defaults and their basis:
  refrigerator 0.35 and freezer 0.40 (compressor runs 33-40% of the time in
  a typical kitchen), aircon non-inverter 0.70 (60-80% compressor duty at
  usual tropical setpoints), aircon inverter 0.55 (full input during
  pull-down, 30-50% of rated at the setpoint), water dispenser 0.08 over a
  24 h window (measured units draw 0.7-1.1 kWh per day), kettle 0.35 (full
  power only for the minutes of each boil), rice cooker 0.50 and iron 0.50
  (thermostat cycling), coffee maker 0.60, washing machine 0.60, fans 0.80,
  TV 0.80, laptop and chargers 0.50, lights and network gear 1.00, tankless
  shower heater 1.00 over the shower window. Sources are listed in
  README.md. These are engineering defaults to be refined with clamp-meter
  measurements over time.
- Nameplate values far outside the type's usual range are flagged; the
  Tanauan test audit carried a 9014 W washing machine.
- Peak load for the inverter follows the field sheet's hour table: for each
  hour, every appliance whose window touches that hour is added at quantity
  x nameplate x duty factor, and the peak is the largest hour over the week
  and the twelve months. A half-hour appliance counts in full for the hour
  it touches. The table for the peak day is shown with the result.
- Each appliance shows hours per use day and days per week, as on the
  field sheet; kWh per day is the weekly average, which is what the bill
  comparison needs.
- Bills: usually only the latest bill exists. Each bill carries its billing
  month, kWh and period length; the audit's month profile times the period
  length is compared with it.
- Reconciliation, the owner asked for the smoother and more accurate option:
  appliances in uncertain types (aircon, refrigerators, freezers, water
  dispensers, pumps, storage heaters) are scaled first, between a 15 percent
  floor and their nameplate ceiling, then any remaining gap is spread
  proportionally over every existing appliance. Future additions never
  count against the bill. A future appliance of a type the household already
  has inherits that type's scale, so a planned second aircon behaves like the
  existing one; a future appliance of a new type is used as typed.
  Appliances marked "to be removed" count against the bill but not in
  sizing. A gap above 10 percent
  before reconciliation is flagged. The Tanauan test audit as typed was
  about 1.9 times the bill even after duty factors, so the aircon hit the
  floor and the rest was spread; the reconciled profile matches the bill.
- All systems are hybrid inverters; the choice, in the owner's order, is
  off-grid (full battery, no grid import at all; surplus beyond the battery
  is lost), net metering, or net metering with a battery.
- PV, grid modes: kWp = annual consumption / annual yield per kWp of this
  roof's measured simulation (net-zero annual energy), rounded up to whole
  panels of the chosen model and capped by the panel count the roof holds.
  Roof-limited systems report the achievable coverage instead of a system
  the roof cannot hold.
- PV, off-grid: the worst month's typical day must produce the day's
  consumption times a design margin (default 1.25); panels are then added
  until the hourly balance leaves nothing unserved, up to what the roof
  holds. A roof-limited off-grid system reports the unserved kWh per year.
- Battery (off-grid and combination): hour-by-hour balance of each month's
  typical day; usable capacity = the energy the battery must deliver on the
  typical day with the largest unmet load (hours where solar is short),
  divided by the one-way efficiency, over the twelve months. It carries
  exactly what solar cannot at that hour, nothing more. No autonomy
  allowance, by the owner's rule: off-grid adds panels until the balance
  always closes instead. Reported in kWh, usable and nominal, with no
  module rounding; 85 percent depth of discharge and 92 percent round-trip
  by default, 0.5C for the power limit. Products are chosen in the pricing
  module.
- Inverter: smallest catalogue size (6, 8, 10, 12 kW by default) that covers
  the hour-table peak, the start of the largest motor load at the 200
  percent surge rating, and the PV array at 1.3 kWp per kW. Parallel units
  when the largest size is not enough.
- Outputs: recommended PV, inverter, battery, coverage of consumption,
  self-consumption, annual import and export, typical-day chart per month,
  month-by-month balance. Internal only for now; the customer PDF is
  unchanged until the pricing module exists.

## Pricing and bill of materials (module 3)

- The owner's workbook (PLD_Materials_DB) is imported once and the app is
  the master afterwards: items, suppliers and every driver, rate, route and
  job constant live in the database and are edited in the browser. A newer
  workbook can be re-imported; items are matched by code, prices and specs
  follow the workbook, panel dimensions typed in the app are kept, items
  missing from the workbook stay, and the pricing settings are kept unless
  the import is told to reload them. The packages workbook is dropped.
- Panel length and width are stored per material item (parsed from the spec
  when it carries "LLLLxWWWxDD mm", otherwise typed on the Materials page).
  A candidate panel can be picked from the database, which links it by
  code; an unlinked candidate is priced as the cheapest database panel of
  the same wattage, with a warning.
- The engine reproduces the workbook's sample job to the peso (329,300 for
  the 8-panel, 6 kW, 11.7 kWh job): landed cost = net + handling share
  + wastage + payment fee + storage; truck share = max(kg / 3000, m3 /
  14.27); markup tiers 10 / 15 / 30 percent; freight = trips x run cost
  over the loop Pila, suppliers bought from in order, site, Pila; labour
  from roof and ground man-hours with the carry crew rule, crew options of
  4, 6 or 8 and the cheapest feasible within the day limits; mob/demob,
  tools, PPE, seal, LGU permit, ERC and meter pass-throughs for net
  metering; services markup, freight markup, 5 percent commission, VAT,
  rounded up to the hundred; OCM share of the markup.
- BOQ rules: inverter = the default model on every job, the Felicity
  6 kW eco-hybrid (FS-INV-008), in as many parallel units as the sizing
  requirement needs (since round 3: one unit, and a larger single unit
  before parallel ones; see "Round 3, batch 1"), with a per-job override; when no default is set the
  cheapest hybrid at or above the sized kW is used (3-phase and
  high-voltage units excluded). Battery =
  cheapest combination at or above the nominal kWh (racks, slave modules,
  12 and 24 V units excluded); both with a per-job override. Mounting per
  row from the roof layout (a row runs along the face length; the panel
  dimension along the row follows the chosen orientation): two rail lines,
  2.4 m rails, three L-feet per rail (owner's correction), four end clamps
  per row, two mid clamps per gap, one splice per rail joint. Strings =
  ceil(panels / max per string, default 10) with an override; one DC
  breaker and two MC4 pairs per string. Wire runs use a fixed allowance
  (25 m per string each conductor, 15 m AC circuits, 20 m grounding, 30 m
  conduit) and the gauge is the smallest whose ampacity covers 1.25 times
  the current and whose drop over that run stays under 3 percent; THHN
  ampacity uses the 60 degree column (3.5 mm2 25 A ... 30 mm2 85 A) so a
  6 kW inverter gets 8.0 mm2 as on the sample job. Battery cable: two lug
  pairs per battery, gauge from 1.25 times the inverter kW at 51.2 V;
  battery breaker = smallest "BATTERY BREAKER" at or above that current.
  ATS 63 A, four AC breakers and four AC SPDs per inverter, two
  enclosures, one tray, one ground rod, four earth lugs, two sealants.
- Manual edits are stored as quantity overrides by code (zero removes) and
  added lines, so they survive a recompute; "reset to generated" clears
  them. Extra one-way km beyond the route's reference site is prefilled
  from the map pin: straight line to Pila x 1.3 road factor, less the
  10 km reference; it can be overridden per job.
- Customer quotation shows four sections in the owner's order, priced by
  general category rather than item by item: Materials (solar panels,
  inverter and battery with their counts and model names, then mounting,
  wires and terminations, protective devices, enclosures and raceways,
  grounding, consumables as lots; freight spread over the lines by truck
  share), Labor (installation crew by the day, mobilization and
  demobilization, PPE, then the permits and papers: plans and PEE seal,
  LGU permit and CFEI, ERC
  certificate and bi-directional meter for net metering), Equipment (the
  tool charge for the installation days) and Tax. Commission is spread over
  every line in proportion to direct cost and the rounding pesos sit on the
  labour line so the total is the rounded contract price. Landed costs,
  markups, item prices, freight and labour detail stay internal.

## Program of works and cashflow (module 4)

- Built from the priced job, so it needs pricing first. Everything hangs
  off the signing date (today when blank): plans and PEE seal, LGU permit
  application and approval, net metering application with the distribution
  utility (grid modes only), the pickup run the day before installation,
  installation days, commissioning on the last installation day, CFEI, DU
  inspection and bi-directional meter. The owner has no data on permit and
  utility durations, so they are editable assumptions (7, 5, 30 and 15
  days) flagged on the page and in the PDF. Installation defaults to the
  day after the expected permit; any weekday is allowed, no holiday
  calendar. Jobs may overlap; no shared crew calendar.
- Site day from the labour settings: depart base 06:00 (editable), travel
  from the mob/demob setting plus the extra km at 40 km/h, half the
  non-productive hour to set up, 6.5 productive hours, lunch 12 to 1 with
  no other stops, half an hour to pack up, travel back. Roof pairs and the
  ground crew work in parallel: rails and L-feet, panels and clamps, roof
  wiring on the roof; unloading and hand-off, battery hauling, inverter,
  battery, enclosures, protection, conduit and tray, wires, MC4, ground rod
  on the ground, then energizing and commissioning once the roof strings
  are done. The roof crew joins the ground tasks when the roof is finished.
  Hours per task are the labour calculation's man-hours divided by the
  persons on that stream, so the plan and the price agree; an early finish
  or an overrun against the paid days is flagged rather than hidden.
- Payments: default 50 percent on signing, 40 on delivery to site, 10 on
  commissioning, editable per job and as the company default, with an
  optional instalment balance (count, share, interval, start event).
  Shares that do not add up to 100 percent are scaled and flagged.
- Cash out, by the owner's practice: cash at every supplier on the pickup
  day (net price plus payment fee, not the landed cost), the run's driver,
  helper, diesel and toll the same day, PEE seal on signing, LGU fee at
  application, ERC and meter fees at the net metering application, crew
  wages, transport, packaging and PPE after the last installation day,
  commission (5 percent of direct cost) after commissioning, VAT remitted
  30 days after completion. Handling, wastage, storage, truck ownership
  and maintenance and the tool charge are allocations that stay in the
  company and are listed, not cash. The running balance shows the lowest
  point and its date.
- Customer sees milestones and payment dates in the quotation PDF; the
  hourly plan, the cashflow and the cost lines stay in the internal
  program of works PDF and page.
- Each assessment carries a job stage (assessed, quoted, signed, sourcing,
  installing, commissioned, net metering, closed) shown in the list; the
  project management dashboard and close-out actuals will build on it.

## Economics for the customer (module 5)

- Built from the sizing's month-by-month balance and the priced contract.
  The tariff is the effective rate on the latest bill (amount over kWh,
  which includes the bill's fixed and tax lines) because that is what the
  customer feels; a setting rate applies when there is no bill, and the
  rate can be typed per job.
- Bill after solar per month = import x tariff less export x export
  credit, floored at zero per month (credit beyond zero is not carried
  over, flagged when it happens). Off-grid: no grid bill; savings count the
  energy served and unserved kWh are flagged. The export credit defaults
  to 6.50 pesos per kWh as a stand-in for the distribution utility's
  blended generation rate, which is what net metering credits; it must be
  set per utility.
- Years: savings scale by (1 - degradation)^(y-1) and (1 + tariff
  rise)^(y-1); costs are upkeep (0.5 percent of the contract a year,
  escalating), a battery replacement every battery life (10 years) and an
  inverter replacement every inverter life (12 years), both at the
  quotation's customer price for that line, skipped in the final year.
  Outputs: payback and discounted payback (interpolated), NPV at the
  discount rate (8 percent), IRR by bisection, net savings over the
  period, lifetime cost per kWh produced, and CO2 avoided at 0.71 kg per
  kWh (Philippine grid factor). All defaults editable in settings and per
  job.
- The customer quotation shows the bill before and after, monthly and
  first-year savings, payback, net savings over the period, the return
  and carbon avoided, with the assumptions spelled out in one sentence.
- The proposal PDF is laid out like a utility statement so it reads as
  familiar: header strip with proposal number, statement date and valid
  until; a total-contract-price box where the bill has the amount due;
  "your electricity consumption" bar chart with the grid purchase after
  solar drawn inside it; system information; summary of charges
  (Materials, Labor, Equipment, VAT); your savings; reminders; a payment
  stub with the milestones; details of charges and the schedule on page
  two. Structure only: the company's own name and colours, no utility
  logo or colours, so it cannot be mistaken for the utility's document.

## Ported from the earlier roof-check tool (pld-roof-check)

- Faces can be a rectangle, a hip face (trapezoid, with a ridge length) or
  a triangle. Panels are fitted row by row from the eave in both
  orientations and the larger count kept; a hip face narrows as it rises,
  so each row is limited by the face width at the row's top edge. The
  rows feed the mounting takeoff directly. Orientation now follows the
  usual meaning: portrait = the panel's long side up the slope, landscape
  = along the eave (the earlier app's naming was the other way round).
  Panels left out per face (vents, tanks, areas the surveyor excluded) are
  subtracted from the fitted count.
- Walls: a firewall or long wall along one edge, with its height above the
  roof and gap to the edge. The sun's path at the site latitude is swept
  over a year to find how far the shadow reaches in the main hours (9 to
  3) and all day (8 to 4), as a multiple of the height (about 1.2 on the
  east or west, 1.0 south, 0.3 north at Pila), corrected for the roof slope
  on eave and ridge walls; the main-hours strip is cut out before fitting.
  In the hourly simulation the same geometry gives, for every hour, the
  share of the remaining panels in the wall's shadow, and that share loses
  its beam irradiance (diffuse light stays). A wall that shades the whole
  face is flagged.
- Trees and buildings: direction and angle to the top from panel height,
  with how wide they look (default 40 degrees). The field rule (under 18
  degrees ignore, 18 to 32 small loss, over 32 leave the area out, north
  side ignored under 60) is shown as guidance; the simulation blocks the
  beam whenever the sun is inside the obstacle's sector and below its top.
  Each face reports the share of the year's direct sun lost to shade.
- Meter readings: the low-sun gate moved from 500 to 600 W/m2 and the
  10 percent swing warning says a cloud was passing and to retake. The
  earlier app's k cap of 0.80 is not used, since the site factor already
  removes the heat and sun-angle effects the cap stood in for.
- Client card: a phone-sized PNG with the company band and logo, panels,
  kWp and typical monthly kWh, the bill coverage when a bill is on file,
  each face, what was measured, the shade notes and the next step, for
  sending from Messenger after the first visit. Not adopted: the lead
  qualification rules, the 135 sun-hour formula, the clear-sky
  orientation table and the artifact-runtime log; PVGIS and the server
  database replace them.

## Quick estimate (public, four questions)

- A free, login-free page at /quick asks the goal (net metering, net
  metering with a battery, off-grid), the house location on the map, the
  monthly use in kWh or the bill in pesos, and when electricity is used
  most (morning, spread, evening). Nothing else: no roof, no readings.
- Location gives the PVGIS cell; a typical roof (10 degrees facing south)
  and a typical measured site factor (0.95) give the production per kWp,
  cached per cell. The pattern picks one of three 24-hour load shapes
  scaled to the monthly kWh, the same every month. Peak load for the
  inverter is the busiest hour times 2. Sizing, bill of materials, pricing
  and economics are the same engines as the full assessment, with the
  default panel laid in rows of eight and no roof limit below 40 panels,
  and the trip distance from the pin.
- Shown to the visitor (since round 9, 10 October 2026): the bill before and after, the monthly and first-year
  saving, the payback, the installed price as one total, the panel count, the inverter and the battery with what it
  carries in words, and the day scene with its hourly kW; the kWp, the roof area, the kWh made, the coverage, the
  25-year total, the CO₂, the price split and the assumptions stay for the proposal (see "Rounds 8 and 9" below).
  Nothing internal.
- A name and contact book the free roof visit: saved as an assessment at
  stage "lead" with the four answers in the notes and the bill on file, so
  the full assessment starts from it. Public endpoints are rate limited
  per visitor address (30 an hour) and switched off while synthetic
  weather data is loaded; the quick settings sit in the pricing settings.

## Brand

- PL Development brand throughout: primary black #111111, secondary gold
  #C9A227, off white #F5F5F3, dark gray #2D2D2D, Montserrat. The web app
  self-hosts Montserrat (bundled at build time, no outside call) and uses
  the logo mark in the top bar, the login page, the favicon and the
  home-screen icons; a web manifest lets Android and iOS install it as a
  full-screen app. The PDFs register the bundled Montserrat TTFs (converted
  from the same package) with Helvetica as the fallback, carry the logo
  mark in the header, black section bars with a gold edge, and the gold
  for the headline numbers. Chart colours: gold for the headline series,
  blue for a reference or balance, orange for a cost; the trio passes the
  colour-blind separation checks, and the gold's low contrast on a light
  surface is relieved by the tables under every chart.
- Not yet: close-out actuals, project dashboard.

## Guard rails (from the UX, marketing and copy audits)

- Three audits (usability, marketing, copy) were run against the app; their
  reports live outside the repo. The first batch of fixes is defensive:
  an error boundary around every results card, so a record computed by an
  older version shows "save and compute to refresh" for that card instead
  of a blank page, and the views tolerate fields added after the first
  release (layout rows and cuts, shade, pricing sections).
- Unsaved edits are protected three ways: the browser asks before a reload
  or close, the router asks before an in-app link, and a draft of the
  document is written to the device (localStorage, per assessment) 600 ms
  after each edit and offered back on the next open. The draft is cleared
  on a successful save or compute.
- Errors from Save and compute render inside the sticky action bar, so
  they are visible wherever the user is on the page, and the page scrolls
  to the card the message is about (pin, roof faces, readings, audit).
- Every signed-in page must fit a 390 px phone with no sideways scroll:
  the top bar wraps, hints under rows take their own line, codes do not
  wrap. The check is a Playwright script in the session scratchpad.
- The public estimate's rate limit is per browser (an X-Visitor token the
  page generates) with a wider cap per address, because Philippine mobile
  networks put thousands of phones behind one address.
- The schedule keeps the order of a day as built (delivery, installation,
  switch-on) and lists payments after the day's work; a stable sort by
  date replaces the milestones-first sort.
- Wording moved toward the copy audit's glossary where it was cheap:
  "needs recalculating" for stale, "Roof check" for the customer PDF and
  card, "Proposal" for the quotation, "Tools" and "VAT" for the sections,
  degree signs instead of "deg", US spelling, no "(s)" plurals.

## The estimate on the website

- The free estimate is a marketing object and lives on the company website;
  the assessment, pricing and program pages are the company's working
  notes and stay behind the login. One engine serves both: the website
  figure and the later proposal come from the same sizing, bill of
  materials, pricing and savings code, so they never disagree.
- The public page is its own small bundle (`/estimate`, built from
  `frontend/estimate.html`) with no login shell and no map library, plus
  an embeddable script (`/widget/quick.js`, built with
  `vite.widget.config.ts`, styles inlined) that mounts the same component
  inside any page on the website and calls the server it came from. The
  old in-app `/quick` route is gone; the back office links to `/estimate`.
- Cross-origin access is limited to the origins in
  `SOLARAPP_PUBLIC_ORIGINS`, without credentials, so the login cookie never
  travels with the website's calls; only `/api/quick/*` is useful to it.
- Location is a town picker (Laguna and Batangas municipalities with
  approximate town-centre coordinates) or the phone's location, not a map
  pin: the PVGIS cell is about 27 km across and only the trip distance
  uses the point, and a careless tap on a national-zoom map was the
  biggest effort wall on a phone. A pin more than 25 km from any listed
  town is flagged as outside the usual area, not refused.
- The result leads with the bill before and after, the payback and the
  price; the system is one line. For the two net-metering goals the other
  one is computed too and shown as "without the battery" or "add a battery
  for brownouts", with the honest line that the battery adds little to the
  savings. The price breakdown and the assumptions sit under "How we worked
  this out".
- A lead carries its source (UTM tags, fbclid, referrer, page), the
  estimate the visitor saw, a preferred time, and a consent flag; a hidden
  honeypot field drops bots. The assessment's notes are written in plain
  words, the list row shows the contact (tap to call) and what they saw,
  and a "Contacted" stage sits between Lead and Assessed. Every estimate is
  logged (goal, kWh, town, price, source) and the job list shows the funnel
  for the last 30 days: estimates, leads, visits, proposals, signed.
- The company profile (phone, Messenger, Facebook, owner, PEE and licence,
  where you install, brands, warranties, where to pay, callback promise,
  privacy line) is app settings edited on the Settings page; the public
  page prints what is filled in and leaves the rest off, and the documents
  (next batch) read the same profile.
- Lead notices by email are optional (SMTP settings in `.env`); off by
  default so the server keeps making no outside calls unless asked.
- The website's analytics get a browser event and a dataLayer push on
  estimate shown and lead submitted; the page itself loads no tracker.

## Customer documents: trust and wording

- The proposal now carries what the marketing and copy audits found missing:
  a contact footer on every page (company, address, phone, Messenger,
  Facebook, email from the profile), the solar and battery parts of the
  price named under the total, brands from the profile, the bill month by
  month in pesos before and after solar instead of a kWh chart, savings
  rows in the customer's words (bill today, bill with solar, pays for
  itself in, saved over 25 years, yearly return on your money), a "Your
  questions" block that answers brownouts, net metering handling and the
  gap before the two-way meter, moving house, upkeep and what the
  installation does to the roof, the warranties and the PEE's name and
  licence, and an acceptance block with where to pay and two signature
  lines. Section and line names follow the copy audit's glossary
  (Installation and permits, Installation tools, VAT; cables and
  connectors, breakers and surge protection; the permit lines spelled
  out), and so do the schedule milestones and the default payment labels.
- The roof check PDF is titled as such, says plainly that it shows what the
  roof can hold and that the proposed system is usually smaller, carries
  the next step and the same contact footer, and no longer prints an
  internal "inputs were edited" note.
- The card is "Your Roof Check", states the roof's output as a multiple of
  the bill rather than a percentage above 100, takes the next step text
  (with a date) from a prompt when the card is opened, and ends with the
  contact line and a QR code to the estimate page tagged utm_source=card,
  so a forwarded card becomes a measured lead. The QR needs
  SOLARAPP_PUBLIC_URL; without it the card prints the contact line only.

## Back office: steps, phone ergonomics, dense editors

- The assessment page is four steps instead of one 14,000 px scroll: On
  site (site, roof faces, panel options, roof readings), Energy audit,
  Pricing and program (pricing, savings and schedule inputs), Results. The
  step lives in the URL hash so a reload or a shared link keeps it, the
  action bar sits under every step, and a calculation opens Results. A new
  record shows a checklist (map pin, a roof face, a panel, readings
  optional) and Calculate stays disabled with its reason until the first
  three are there. Delete moved from the action bar into the Site card.
- Results open with an "At a glance" strip (recommended system, contract
  price, monthly bill before and after, payback, installation date) whose
  tiles scroll to their card. Stale results are dimmed under one banner
  with a Calculate button, instead of a banner per card that scrolls away.
- "Calculate" is the verb everywhere (button, messages, API errors); the
  copy audit's glossary and style sheet drove the labels: materials list,
  needs recalculating, °, °C, W/m², mm², US spelling, no "(s)" plurals,
  and warnings that say what to do next (which setting, which page).
- Phones: every control is at least 44 px tall with 16 px text under
  640 px, toggles 36 px, the roof-face fields sit in a two-column grid with
  the rarely used fields under "More", and the appliance, bill and
  materials tables turn into stacked cards with labels (CSS only, from
  data-label attributes), so nothing scrolls sideways.
- Materials list: sortable columns, a count, an empty state, fifty rows
  at a time with "Show 50 more", a sticky header, codes that do not wrap.
- Pricing settings: labels with units and one-line help for the keys the
  owner meets, percentages edited as percent, time inputs for the site
  day, the route km and toll matrices as grids with the stops as headers,
  the payment terms through the same editor as the assessment, a chip
  that counts edited sections, Discard, and the same leave-page guard as
  the assessment.
- Before the website exists, the estimate page is the website:
  `SOLARAPP_PUBLIC_HOST` names a hostname (pldevinc.com) on which the app
  serves the estimate at the root and answers 404 to everything else, so
  the same server and tunnel carry the public page without exposing the
  login, the API or the documents there. The card's QR code and the ads
  point at that address; the back office keeps its own hostname.
  Financing and instalments are a future module and stay out of the
  marketing text until then.

## The website and the public process

- The company website is plain HTML and CSS in `site/`, built by a
  stdlib-only script into `site/dist`. No CMS, no framework, no outside
  calls: the brand font is self-hosted, the only dynamic work is the
  estimate widget and a small script that fills contact details from the
  company profile, so the owner edits those in Settings and the pages
  never go stale. Pages: home, estimate, brownouts (battery angle), net
  metering (bill angle), about, privacy notice (Data Privacy Act), 404.
  Photos are marked placeholders until real ones exist; nothing is
  fabricated.
- The website runs as a separate process from the same image
  (`solarapp.public`). It holds no database, no documents, no login and
  no secret beyond an internal token; it serves the site, the widget and
  the brand marks, and forwards only the three estimate calls to the
  private app over the Docker network with that token, passing the real
  client address on for the rate limiter. The private app answers those
  calls only to the token or to a signed-in user. A compromise of the
  public process yields a static website and two rate-limited endpoints.
- Each process gets its own Cloudflare tunnel as a container, so the host
  publishes no ports; the back office additionally sits behind Cloudflare
  Access. The single-container host-gated mode remains as a fallback.
- Both processes send security headers: the website a strict content
  security policy (same-origin scripts, inline styles for the widget,
  no frames from elsewhere), the back office no framing at all except for
  the estimate page and the widget, no sniffing, a strict referrer policy.
- A path-traversal hole in the static file route (any readable file,
  without a login) was found during the security review and closed: the
  served path must resolve inside the build folder.

## Security (from the security audit)

- Threat model and findings live in the session's audit report; the fixes
  are in the code. The public estimate's rate limiter is bounded: a
  rejected request allocates nothing, buckets expire, and a token flood
  drops to per-address buckets only; proxy headers for the client address
  are honoured only from our own networks. Login is throttled per address
  (ten failures, then fifteen minutes) and every login, lead, settings
  change, import and deletion is written to the `solarapp.audit` log.
- Secrets fail closed: the example password refuses to start the app; a
  missing or example secret key is replaced by one generated once into
  `data/secret.key`. The session cookie is Secure, HttpOnly, SameSite
  Strict, lasts seven days and carries a password generation, so changing
  the password logs every device out. Writes to the back office must come
  from the back office itself (Sec-Fetch-Site and Origin are checked), so
  neither a cross-site nor a same-site page can post with the cookie; the
  public estimate routes are exempt by design.
- The public process reads at most 16 KB of a request, lets four sizings
  run at once, caches the status call for a minute, and refuses to start
  without the internal token; the private app compares the token in
  constant time. The workbook import is capped at 10 MB, pre-checked for
  zip bombs, parsed in a thread and with defusedxml; customer-supplied
  text is escaped before it reaches reportlab markup; download names are
  ASCII-safe with a UTF-8 alternative.
- SQLite runs in WAL mode with a 30 s busy timeout; backups use the
  `.backup` API, never a file copy. Containers run as an unprivileged user
  on a read-only filesystem with all capabilities dropped, memory and pid
  limits, rotated logs, pinned base images, and the supplier workbook
  mounted into the private process only; the three Docker networks keep
  the website tunnel away from the private app.
- Data Privacy Act: a retention command anonymises leads that never became
  a visit after twelve months and trims the estimate log after ninety
  days; the estimate log keeps a town-level location only; the privacy
  notice and the privacy line say exactly what the system does, including
  the e-mail service and the encrypted backup.
- Two-factor login lives in the app, not in Cloudflare: a time-based code
  from any authenticator app after the password (offline, so it works on
  a roof), with eight one-time backup codes for a lost phone, a replay
  guard per 30 s window, wrong codes counted by the login throttle, and
  the secret kept in `data/twofactor.json` (0600), never in `.env`
  (since accounts, each person's secret lives in the database; see
  "Accounts"). Cloudflare Access stays as an optional outer layer.
- Passkeys (WebAuthn) sign in on their own: a hardware key or phone passkey
  with user verification required is possession plus PIN or fingerprint,
  and it is bound to the hostname, so it is stronger than password plus
  code, not weaker. Keys are added from Settings while signed in; the
  login lists the registered credential ids (public identifiers) so
  non-resident keys work too; challenges are single use and expire in
  five minutes; failures share the login throttle. The password and code
  stay as the fallback, so a lost key never locks the owner out.

## Security, round two

- The session cookie's generation is an HMAC of the password and a server
  nonce under the secret key, so a stolen cookie no longer carries a
  crackable fingerprint of the password. The nonce lived in
  `data/session.key` until accounts arrived; it is now each person's
  session generation in the database (see "Accounts"), and "Sign out
  everywhere" rotates that one person's generation (logout stays per
  device).
- Managing security keys is a step-up action: the password (and a fresh
  code) must be entered again. A stolen cookie alone cannot add a key or
  remove the owner's, which would otherwise have outlived a password
  change. Wrong answers count toward the login throttle.
- The two-factor file is written atomically and read under the lock; a
  backup code is consumed exactly once even under concurrent logins, and
  a file that exists but cannot be read means "on, nobody passes on the
  password alone", never "off".
- Anonymous passkey challenges have their own per-address limit, and a
  flood evicts the oldest challenge rather than everyone's.
- The private app refuses request bodies over 1 MB (11 MB for the
  workbook import) and writes without a length. The estimate page on the
  back-office host carries a content security policy that lets only the
  company website frame it. The public process believes the tunnel's
  visitor address only from a private peer, as the private app already
  did.
- Accepted as is: `/api/auth/me` tells an anonymous caller whether a
  code or a key is in use (an attacker with the password learns it on the
  first attempt anyway, and the login page needs it); styles may be
  inline (scripts may not); the app runs as one worker by design.

## Second audit round: the spot-clean batch

Four reviewers (engineering, UX, marketing and copy, security) audited the
back office and the website with the owner's framing: a solar engineering
app, not a CRM or a project-management tool. The plan that came out of it,
with the corrected deliverable set and the boundary, is
`docs/plan-engineering-app.md`. The clear-cut defects were fixed at once:

- Documents: the proposal prints the battery the customer pays for (BOM
  units times the catalogue rating), never the sizing's nominal figure;
  the three main items are built from quantity, rating and supplier, never
  the catalogue string; a What you get block names what the firm delivers;
  the website estimate is carried onto the proposal and the card; the roof
  check shows the readings it claims; every document refuses stale results
  with one message, server and client; the card prints the reading time.
- Website: placeholder photo cards and owner-facing notes are stripped
  from the public build unless `--with-placeholders` is given; the
  illustration figures on the net-metering page come from the engine and
  say so; "often lower than the estimate" is gone; warranty claims hide
  until the years are filled; the share image and page URLs are absolute
  with `--base-url`; the site says "solar engineering" and lists what the
  customer gets on paper; the embedded widget drops its duplicate header
  and footer; the sticky bar hides while the booking form is in view.
- Estimate: usage under 60 kWh a month is refused with a plain message
  (the owner may move the floor); the battery figure is the priced unit, so
  the website and the proposal agree.
- Back office: per-row k values stay aligned with the rows as typed and a
  dropped row says so; a face no panel fits is flagged on the face, and a
  layout with no panels is an input error, not a result; offline and
  validation messages are in the owner's words; one number helper
  everywhere; the login remembers the last method; the card's next step is
  a saved field that does not make results stale.
- Terms: BOM is the parts list, BOQ the priced list (Details of charges);
  ERC certificate of compliance; two-way meter; US spelling in the owner's
  screens.

Left for the owner's go-ahead (scope, not defects): the leads inbox and the
stage split, the Results regrouping with the plan drawing and the Gantt
chart, and the engineering build order in the plan. All three were approved
and built; the next sections record them.

## The boundary, built: leads out of the project list

- A website booking is a lead, not a project. Leads live in their own table
  and on a Leads page with the funnel (estimates run, leads, visits booked,
  converted); the project list shows engineering facts only (customer,
  address, faces, kWp, battery, stage, last calculated). "Start assessment"
  turns a lead into a project with the customer, the pin (the visitor's,
  or the town's centre), the bill from the estimate snapshot and a
  reference back to the lead; the proposal and the card still say what the
  website estimate was.
- The stage list is the engineering and job sequence only: assessed,
  quoted, signed, sourcing, installing, commissioned, net metering,
  closed. Lead and contacted belong to the lead's own status (new,
  contacted, visit booked, converted, closed). Old records at those stages
  read as assessed; a startup migration moves lead-stage records without
  results into the inbox and keeps those with results as projects.
- Retention anonymises inbox leads that never became a project after
  twelve months and never touches a project. The nav was Projects, Leads,
  Materials, Settings (the Leads page left the app in round 3; see "The
  Leads tab leaves the engineering app"); the estimate page link and the website-only
  profile fields sit under a Website heading in Settings; the phone top
  bar is one row with a menu.
- A future CRM module takes the bookings over through the same API; a
  future PM module takes the later stages and the actuals. Both link by
  the project id.

## Drawings: the plan and the Gantt chart

- The layout engine now reports geometry, not only counts: each panel's
  rectangle in metres from the face's bottom-left corner, placed exactly
  as the fitter measures its rows (same inset, same gap, rows from the
  eave up), with the no-panel strips, the shade markers on the edge they
  shade from, the hip or triangle outline, and which panels the sized
  system uses with their string number. Panels left out for vents are
  not drawn; the caption says how many were left out.
- The roof check and the proposal carry one plan drawing per face with
  panels (used panels solid, spare positions dashed, captions in facts:
  "4 of your panels here; room for 5 more"); the program of works opens
  its schedule with a Gantt chart (tasks as bars, milestones as diamonds,
  payments as hollow diamonds, today marked). The React components draw
  the same content for the Design and outputs step.
- The bill of materials exports as CSV and XLSX with the owner's edits,
  under the same stale rule as every document.

## Engineering numbers (the approved batch)

- Losses after the panels: inverter 0.96, wiring 0.98, soiling 0.97,
  other 0.99 (about ten percent in all), editable under the pricing
  settings, applied to the per-kWp profile before sizing so the array is
  sized on energy at the meter. Results keep both figures; customer
  documents print the one at the meter. The website estimate uses the same
  factor.
- The battery is balanced over the real hourly year, not twelve typical
  days, with a days-of-autonomy setting (default one evening without sun,
  the owner's choice) and the loss-of-load hours, days and kWh reported.
  The off-grid loop adds panels until the autonomy is met or the roof is
  full and warns when it cannot be; the proposal says plainly how many
  hours a year an off-grid house goes without power, and that the grid
  steps in on a hybrid.
- The sized panels go on the best faces first (by specific yield), whole
  rows from the eave, and the system's production is the sum over those
  panels, not the whole-roof blend; the priced mounting and the plan
  drawings follow the same allocation.
- Materials carry electrical data (panel Voc, Vmp, Isc, Imp and
  coefficients; inverter PV window, MPPTs, currents; battery continuous
  current), a grid-interactive flag inferred from the workbook names and
  remarks and editable, and the certificate text. These are the inputs
  the string design table and the circuit sheet will use next.
- The inverter rule: a job with net metering gets a grid-interactive
  inverter; the default is per system kind (the grid-tie hybrid, FS-INV-001
  in the bundled workbook, for grid jobs; the eco-hybrid for off-grid). An
  off-grid default on a grid job is skipped with a warning; an unknown
  flag gives a hard warning to confirm the anti-islanding certificate
  before the application. The proposal prints the certificate and the
  inverter the BOM carries.
- The battery bank's continuous current is checked against the inverter's
  battery current and the breaker sized at 1.25 times it, within the
  battery's rating; warnings only, never silent extra packs.
- The hour-by-hour plan has floors (commissioning two hours, battery and
  inverter one hour each) that do not change the labour price; the
  schedule-overrun warning tells the owner when a priced day is no longer
  enough.

## Design and outputs

- The fourth step is "Design and outputs": an index over seven cards in
  the order an engineer reads them: roof and production (with the plan
  drawing per face, the sized panels solid), system design (inverter and
  its certificate, battery with autonomy and loss-of-load, strings, cable
  gauges and drops, protection, panels per face), quantities (the BOM
  with its exports), program of works (the Gantt first), cashflow,
  savings, and documents (every document with its state and reason in one
  place, with the card's next step beside it). The action bar keeps the
  status chip, Save and Calculate.
- The job stage is a pill in the page head, not an input in the schedule
  card. A new project is a draft until the first Save; a mis-tap leaves no
  row behind.
- Hard warnings (an inverter that is not grid-interactive, an unknown
  certificate, autonomy not met) are red banners; ordinary warnings stay
  muted. Labels are attached to their inputs; reasons are visible text,
  not tooltips.
- Phone: the stale banner is in the flow (the bar has Calculate), the BOM
  and the payment editor are cards, month tables turn months into rows.
- Calculate needs one reading set with three readings: the k factor has
  no default, by the owner's rule that the roof is measured, not assumed.
  The proposal is refused on test weather on the server as well, like the
  roof check and the card.

## The owner's corrections after the engineering batch

- "Off-grid" in this company's vocabulary means NO EXPORT, not no grid:
  the panels and the battery carry the house first, the grid steps in
  only when both fall short, and nothing is sold back. The sizing keeps
  the design-margin rule on the worst month and stops there; it no longer
  fills the roof to chase a dark week, because the grid is there for it.
  Every kind with a battery reports "hours the grid steps in"; the
  economics bill those hours at the tariff and give no export credit; the
  documents and the website say so in those words. The internal key stays
  `off_grid` for old records.
- The Felicity eco-hybrid can export: the owner confirmed the selling
  option with the maker. Any "hybrid" is therefore grid-interactive unless
  its remark says it cannot export, the eco-hybrid is the owner's default
  on every job again (the grid-tie model stays available), and the
  certificate question is an ordinary warning: confirm the anti-islanding
  listing with the maker before the net-metering application, then record
  it on the Materials page.
- A crew stays late rather than come back for an hour: the last priced day
  may run up to a late-finish allowance (default two hours) past its usual
  end before the plan adds a day. The task floors stay; the six-panel
  hybrid is a one-day job that finishes about an hour and a half late,
  which the program says in a warning.

## Accounts: the owner and the engineers

- Everyone who opens the back office has their own account. Two roles:
  the owner (people, the company profile, pricing settings, the materials
  list and its import) and the engineer (leads, projects and every
  engineering output). The server enforces it, not just the screens:
  settings PUT, pricing config and the materials writes answer 403 to an
  engineer, and the People endpoints only exist for owners. The company
  always keeps at least one active owner.
- Passwords are argon2id hashes in the database. The `.env` username and
  password are read once, to create the first owner, and may be cleared
  afterwards; a blank password with no accounts leaves the server up and
  the login closed, with the recovery command in the log. The authenticator
  set up with the old `twofactor.json` file and the keys registered before
  accounts existed carry over to that owner, so an update changes nothing
  for the person already signed in.
- A new person gets a temporary password shown once to the owner, and the
  app opens nothing until they choose their own (twelve characters or
  more, not containing their username, five distinct characters). The
  owner is told to pass it on by voice or in person, not in the same
  message as the address.
- The authenticator app and the security keys are per person and set up
  in the browser under Your account: a QR code and the typed key, one
  code to confirm, eight backup codes shown once. The old server command
  is gone, and the secret never leaves the database. Adding a key spends
  one authenticator code: the registration challenge is bound to the
  person and stands in for the step-up on the second call, since it was
  issued only after one, is single-use and expires in five minutes.
  (The first build asked for the code twice, which a one-time code cannot
  survive: the walkthrough with the authenticator on caught it.)
- The session cookie names the person and carries an HMAC of their id,
  their session generation and the tail of their password hash under the
  secret key. A password change, a role change, a deactivation, a reset by
  the owner and "sign out everywhere" each rotate the generation, so they
  end every session of that one person and nobody else's. Signing in with
  a key as a deactivated person is refused.
- Recovery stays on the server: `python -m solarapp.users` lists, creates,
  resets a password or an authenticator, deactivates, reactivates and
  changes roles, for the day every owner is locked out. It needs shell
  access to the server, which is the point.

## The Leads tab leaves the engineering app

- The owner's rule, round 3: "the leads tab should not be in the solar
  engineering app"; the website is the starting line of the leads and CRM
  pipeline, which is a separate build. So the Leads page (funnel, statuses,
  notes, closing reasons) is gone from the back office. The bookings table
  and `/api/leads` stay as they are: the website still writes a booking
  there, the e-mail notice still goes out, and the CRM takes the router and
  the table over unchanged.
- The one hand-off stays, because a booking must be able to become a
  project without retyping: Projects › "From a website booking" lists the
  open bookings (name, place, when, what the visitor saw, the contact to
  arrange the visit) and "Start project" creates the project from one, as
  "Start assessment" did. The e-mail notice links there. Nothing else about
  a booking can be changed from the engineering app.

## Money, round three (finance findings 1, 2, 4, 5, 6, 8, 9, 14)

- A quoted price does not move under the customer. Every priced result
  stores a fingerprint of the pricing settings (`settings_version`: a hash
  of the configuration without the website estimate's own knobs, the
  company label and the import stamp). When the settings no longer match,
  the project list and the project page say "pricing settings changed since
  this price", its own reason beside "needs recalculating", and the stored
  price stays. From stage quoted onward Calculate refuses to re-price
  (409) unless it is sent with `confirm_reprice`; the page asks "Pricing
  settings changed since this price was quoted (was ₱X). Re-price now?"
  before sending it, and asks again if the server refuses because the
  settings moved after the page loaded. An assessed job re-prices freely.
  A result priced before versions existed carries none and is not flagged;
  its next Calculate stores one. The materials list (item prices) is not
  versioned yet: a price edit on the Materials page still re-prices
  silently on the next Calculate, a follow-up with the same mechanism.
- Warranty terms are the owner's (9 Oct 2026) and are the company
  profile's defaults: panel product 12 years, battery 5, inverter 5,
  workmanship 2; the panel performance warranty stays blank until the
  datasheet is in. A database that already stored blanks keeps them until
  the owner types the figures on the Settings page.
- The battery life in the customer economics is the battery warranty from
  the company profile (5 years, so a replacement every 5 years in the
  25-year view) unless the owner types a figure under Pricing settings ›
  Savings ("Battery life, if not the warranty", 0 = follow the warranty) or
  per job. The reason: the supplier notes say the battery datasheets give 5
  years, while the price list says 10 for one line; the warranty the owner
  stands behind is the honest interval. The old fixed 10-year setting is
  dropped when a stored configuration is read, so the rule applies to every
  database. A blank warranty falls back to the profile default with a
  "verify" warning in the economics, never a silent number. The inverter
  life stays the 12-year setting, with help text saying it is a service
  life and not the 5-year warranty. On the worked Tanauan job (contract
  264,900 unchanged) the payback moves from 5.7 to 7.7 years, the IRR from
  16.7 to 12.6 percent and the 25-year net from 976,229 to 742,286: four
  battery replacements instead of two, each at the VAT-inclusive customer
  price (102,417 instead of 91,443).
- Replacement costs in the economics are what the customer will pay: the
  proposal's battery and inverter lines (freight and commission shares
  inside) plus VAT, plus an optional labor per replacement ("Labor per
  replacement", pesos including VAT, default 0, verify). Earlier the
  ex-VAT amounts were used, which overstated the 25-year net by 29,110 on
  the worked job.
- Agent commission is on every job at the settings' rate; there is no
  per-job switch (the owner's decision 4). The customer block of a priced
  job exposes the three figures the proposal prints as its own rows: the
  contract price before VAT (`subtotal_ex_vat`), the VAT (`vat`, with
  `vat_rate` and `vat_label`) and the VAT-inclusive total (`total`). The
  proposal's printing of those rows is the customer-story batch's.
- One battery figure: the website estimate's `battery_part` is the
  customer's battery line plus VAT, the figure the proposal prints beside
  the total ("battery for brownouts"), no longer the selling price rounded
  to the hundred. The estimate page may round it as it rounds the total.
- VAT is worked out on the rounded, VAT-inclusive contract: VAT = total ×
  rate ÷ (1 + rate), the base is the rest, and the rounding pesos (less the
  VAT inside them) sit on the crew line as before, so "VAT, 12 % of the
  amounts above" is true to the peso and a VAT worked back from the total
  gives the printed figure. The internal build-up keeps the workbook's VAT
  on the unrounded contract (JOB!B121), so the sample job still reconciles
  cell by cell; the two differ by the VAT inside the rounding pesos (0.07
  on the worked job, 10.25 on the workbook's sample). The program's VAT
  remittance still reads the build-up figure; it moves with the cashflow's
  VAT-invoice decision (finance 3), which the owner has not made.
- The roof closes in at least a day: a saved or typed 0 for "days the roof
  is closed" (the workbook's #DIV/0!) reads as 1 in the schema and is
  floored in the engine, so the job prices instead of failing.
- The VAT labels on the customer sections ("VAT (12%)", "VAT, 12% of the
  amounts above") are formatted from the VAT setting; the commission rate
  in the owner's screens is the screens' batch.

## The customer's story on paper (round 3, marketing batch)

- The proposal opens, after the customer block and before any table, with
  an "In short" block: the bill today (and what it becomes with the
  appliances the customer plans to add), the system in plain words and the
  share of the house's usage it covers, the bill after, what the battery
  carries, the price before VAT, the VAT and the VAT-inclusive total (the
  owner's rule: "we put a before and after VAT price"), and the payback
  rounded to the half year. Every figure is the results'; a figure that is
  missing drops its sentence and nothing is invented. Under the total box
  the contract is also said as "about N months of your bill today", which
  replaces the "45 months" guess in the marketing kit.
- The battery is described by what it carries, from the hourly balance
  already in the results: usable = the battery the customer pays for (BOM
  units × rating) × the depth of discharge the sizing designs to (0.85);
  night = the reconciled load summed from 6 pm to 6 am on an average
  month's day. When usable covers the night the proposal says "enough for a
  whole night of your usual use (about N kWh from 6 pm to 6 am, aircon
  included, against M kWh usable)", "aircon included" only when an aircon's
  usage window reaches into the night; otherwise "about H hours of your
  evening use", H = usable over the night's average draw, with the aircon
  caveat only when the aircon is outside the night figure. The assumption
  (the audit's appliance hours, the depth of discharge) is printed in the
  reminders. The website estimate has no audit, so it does the same sum on
  the pattern shape scaled to the monthly kWh and says so in its
  assumptions; the words are "enough for a typical night of your use when
  the grid is down" or "about H hours of your evening use when the grid is
  down". The hybrid's old "Designed to carry 1 evening" line is gone; the
  battery-first kind keeps its grid-hours line, with "one evening".
- "What if we move house?" no longer claims a resale value or a transfer
  of the net metering agreement; it carries the website's corrected
  wording per kind (net metering is tied to the service connection and
  the new owner continues it with the electric company; the battery-first
  kind: the new owner keeps using it, we hand over the plans and papers).
  The transfer rule itself stays on the owner's verify list with the DU.
- "On installation day" tells the customer their side from the program's
  own figures (crew size, arrival, the usual finish) and one owner setting,
  `program.installation_outage_hours` (hours the power is off while the
  inverter is cut over at the panel board; 0 or blank prints no length,
  never a guess). The papers asked for are only those the app already asks
  for: the latest bill and the signature on the net metering forms; if
  the electric company asks for more "we confirm the list with you". No DU
  document list is invented.
- Two measures, two names, everywhere the customer reads them: the
  production ratio is "N% of what you use" (website "What it makes", the
  proposal's production row), the served share is "Covered by solar, by
  day and from the battery" (hybrid), "Covered by the panels and the
  battery" (battery first) or "Used straight from the panels … the rest
  goes to the grid and is credited" (net metering). "Share of your usage
  covered by solar" is gone. The third kind has one customer name, the
  estimate's: "Battery first, nothing sold back (the grid as backup)" on
  the proposal, the estimate's assumptions and the home page card; the
  "bigger battery" claim is dropped because the engine adds panels, not
  battery, for that kind.
- The website estimate prints "a small bill" instead of "about ₱0" when the
  modelled bill is under ₱100: the fixed charges never go away and the grid
  bills the hours it steps in during long rainy spells, which the proposal
  for the same house shows. The threshold is a copy rule, not an engine
  number; the owner's fixed-charge figure (plan item 10) replaces it when
  it exists.
- The net-metering page's four tiles are the engine's for its stated
  example (500 kWh a month, Tanauan, mostly evening, no battery) and are
  pinned by a test that reruns that example on the real weather and
  compares the tiles (kWp, panels, rounded price, "under 4 years", "about
  two thirds" between 60 and 72% off); on test weather the check is
  skipped. The payback and the cut are written as ranges that survive small
  price moves, by design.
- The bridge from the website estimate says what changed and why
  ("Measured on your roof and with the appliances you plan to add, it is
  7 panels and a 15 kWh battery at PHP 314,600"); the card and the roof
  check carry the estimate's panel count. The thank-you page sets up the
  path (visit, card the same evening, audit, proposal within two working
  days, valid N days from the pricing setting) and uses the first name
  when the visitor typed two words. Savings over the years are rounded as
  a person says them ("about PHP 1.41 million", "about PHP 61,000"); the
  contract and the payment schedule stay exact.
- A website booking with a landmark keeps its town in the project address
  ("Brgy. Labuin, near the chapel, Pila, Laguna") unless the visitor typed
  the town. The proposal prints no map pin (a signed document names the
  customer and the address); the roof check prints the pin in small print
  only when it is not a listed town centre, which is the hand-off's default
  pin until the roof visit. The project still starts on the town centre so
  the weather cell is right from the first calculation.
- The card's "around N times what your house uses" divides the same
  at-meter figure it prints in the sentence, as the roof check PDF does;
  the card and the roof check say "This roof check" and "About this roof
  check", since the customer's "estimate" is the website figure. The roof
  check names the panel by rating and supplier ("585 W panel (Blue
  Carbon)"), never the catalogue string. The schedule says "two-way meter
  installed".
- Still the owner's to supply, labelled as such: the outage length, the
  DU's document list and transfer rule, the inverter's transfer time (the
  brownouts page now says only that the switch-over is automatic), the
  mounting wind rating and the battery warranty for the two unanswered
  questions (typhoon, battery life), and the local fixed charges.

## The clean form: one grid, defaults that show, Settings in sections

- The owner's words, round 3: "the setting tab are all over the place and
  is not organized ... fields have default values that is not showing, the
  entry parts are not aligned ... make it clean and professional as an
  engineering solar app." The stylesheet now carries one type scale, one
  spacing scale and one control height (36 px on the desk, 44 px on a
  phone) as tokens, and every editor renders through one form cell
  (`Field`): label above, the unit beside the control, help under it. A
  line of fields is a CSS grid whose cells are subgrids of three rows, so
  every control in the line starts on the same edge whatever its label
  does, and a help text in one column never pushes the next line askew.
  The KPI tiles use the same device, so a label that wraps no longer drops
  its value below its neighbours'. Flex rows (`.row`) stay for the editors
  other batches own; a field in one carries no bottom margin, so the
  controls, not the margins, line up.
- The number in force is always visible. A project input (pricing, savings,
  schedule) shows the value the calculation will use: the job's own value,
  or the default from the pricing settings filled in and tagged "default".
  Typing makes it an override, tagged and with the way back; typing the
  default itself, or clearing the field, is the way back too. Before the
  first calculation a default the settings alone cannot give (the tariff
  from the bill, the pin's extra km, the computed string count) reads
  "shown after the first calculation". Placeholders are examples only
  ("e.g. ..."), never values, and never repeated as help.
- Settings is one page in six sections, in reading order, with a sticky
  index on the desk and a jump list on the phone: Company and documents,
  Website, Pricing, Your account, People (owners), Weather and data. The
  pricing settings keep their sections and the META map (labels, units,
  help) but are grouped the way the owner looks for them: Materials and
  markup tiers; Labor and crew; Freight and the truck; Program of works;
  Economics and warranties; System design and the website estimate. A
  section a later batch adds lands under "Other settings" rather than
  disappearing. Each section is a closed block whose summary lists what
  is inside; "Find a setting" opens every section that matches a word.
  The save bar is sticky at the foot of the Pricing card and bleeds to
  its edges; on the phone it is the chip and Save, with Discard and Reset
  on a second row only while there is something to discard or undo.
- The "At a glance" strip's battery is the battery the BOM prices, in
  nominal kWh as the proposal prints it, read from whichever field the
  server names nominal and otherwise from the chosen battery option and
  its units; the sized figure is the fallback only without pricing.
- Small rules that close the audit's "odd sticks": chart gold is a fill,
  never text (table text uses `--gold-text`); an action row inside a white
  card has no band (`.actions.inline`); a number column followed by a
  text column keeps 20 px between them; a row header is never shouted;
  every sideways-scrolling table on a phone shows the edge shadows; the
  cashflow chart draws every week from the first flow to the last; axis
  ticks read "1.5k", not "2k"; Gantt labels get 40 % of the desk width;
  the first-sign-in gate carries the brand mark; the phone menu's name
  row is as wide as the rest; no grey band sits inside a card.

## Round 3, batch 1: hardware that is wrong (E-01, E-03, E-04, E-05, E-06)

- The net-metering inverter rule (E-01): a job with no battery has no backup
  mode, so the grid carries the house peak and the inverter only has to
  carry the array. For kind `net_metering` the requirement is the PV rule
  alone (array kWp over the PV-to-inverter ratio, default 1.3); the peak
  and surge rule stays for the battery kinds. The house peak is still
  reported and the BOQ checks it against the chosen unit's AC input
  (grid pass-through) rating when the item carries one; blank or exceeded
  is an ordinary warning ("verify the inverter's grid pass-through
  rating"). The owner referred to "the first app" as sizing net metering
  correctly: neither earlier repository holds an inverter rule, so this is
  the array rule the engineer recommended, marked for the owner to confirm
  (verify).
- The parallel rule (E-01): one unit when it covers the requirement; when
  the requirement overshoots the owner's unit by no more than the tolerance
  (Pricing settings › BOM item roles, default 10 %, 0 = never) one unit is
  kept with a warning that names the overload question; above that, unless
  the owner picked the unit per job, the cheapest single unit that fits the
  kind (the default's brand on ties) replaces it with a warning that names
  the parallel alternative's price; only when no single unit fits do
  parallel units go on the BOM, warned. The Santo Tomas case therefore gets
  one eco-hybrid, not two (contract ₱273,600 → ₱236,800).
- Battery selection (E-03): the inverter's battery current (its
  `battery_max_a` when on file, else the rated output over 51.2 V) must be
  at or below the bank's continuous discharge current; the cheapest kWh is
  chosen among the units that deliver it, then among the ones whose rating
  is blank (unknown, warned), and a unit that falls short is never picked
  by the generator. A per-job pick that falls short is a hard warning.
  The Pila case moves from BC-BAT-004 (15.36 kWh, 100 A) to FS-BAT-003
  (15 kWh, 160 A).
- The battery circuit (E-03): breaker at or above 1.25 × the inverter's
  battery current, cable ampacity at or above the breaker, so the breaker
  protects the conductor (135 A → 250 A breaker → 70 mm² lug pairs at
  270 A, not 35 mm² at 170 A). The earlier "breaker within the battery's
  rating" warning is withdrawn: the BMS protects the battery, the selection
  rule above covers it, and the breaker's job is the conductor.
- Hard warnings that block the documents: a battery bank below the
  inverter's current, a battery circuit or an AC circuit that cannot be
  coordinated with the items and tables on file carry `blocks_documents`;
  `pricing.design_blocked` lists their codes and the proposal, roof check
  and card are refused on the server with "design_blocked: …" the way the
  stale rule refuses them. The program of works and the BOM export still
  print (the owner needs them to fix the list). The other hard warnings
  (an inverter that cannot export, autonomy) stay red banners only.
- The AC side (E-04): per inverter, one inverter-side circuit (the output
  to the loads) and two grid-side circuits (the grid to the inverter's AC
  input and the maintenance bypass), each with its breaker at 1.25 × the
  circuit current rounded up to the next standard size (a settable list);
  the conductor of each side is sized from its breaker (ampacity at or
  above it) with the drop checked over the run; line and neutral per
  circuit (settable), the ground on the grounding run. The grid side is
  sized on the inverter's AC input rating when the item carries it, else on
  its output with a warning. A 6 kW unit gets 40 A breakers on 8.0 mm²
  THHN (40 A), as on the sample job, and 110 m of THHN instead of 35. The
  THHN table's 3.5 mm² entry is 20 A (the 60 °C column; verify the table
  edition). When the breaker item is not listed in the size the circuit
  needs (IAN-PRT-027 comes in 32 and 63 A, the circuit needs 40 A) the BOM
  warns the owner to add that size.
- The certificate (E-05): an inverter marked grid-interactive with nothing
  under Certifications gets an ordinary warning on every grid job ("no
  certificate on file; confirm the listing with the maker before the DU
  application"); `pricing.inverter_certificate` carries the text (blank
  until it is on file) and the proposal prints "Inverter certificate: to be
  confirmed with the maker before the net metering application" rather
  than nothing.
- BOM counts (E-06): one AC SPD per board, one DC SPD per MPPT input in
  use (the strings on the inverter's MPPT count; one per inverter when the
  count is not on file), one enclosure per inverter, no ATS on an inverter
  whose item says it carries its own transfer switch (a new item flag,
  blank = unknown: the ATS is priced with a warning). A config saved
  before this round carried the sample job's 4 breakers, 4 SPDs and 2
  enclosures per inverter; it takes the new counts once.
- Roles the BOM omitted (E-06): array bonding (the grounding conductor
  along the rail lines plus jumpers, lugs per panel and per rail line on the
  earth-lug line), L-foot fasteners (per foot), placards and labels, a
  visible lockable AC disconnect for the DU (the 63 A isolator in the
  list), monitoring (one dongle per inverter, brand-specific), and on
  net-metering jobs an export limiter as an optional role with a warning
  while no item is set. A role without an item in the materials list still
  puts its line on the BOM (code `NO-ITEM-…`) with the quantity and no
  price, and one warning says to add the item: the crew and the PEE see
  what the design needs, the customer price never carries an invented
  figure. Gauges, counts and fastener numbers are the owner's to verify.
- Results name the battery figures unambiguously (E-12):
  `sizing.battery.sized_usable_kwh` and `sized_nominal_kwh` (the sizing),
  `pricing.choices.battery_nominal_kwh` (the priced bank); the glance strip
  should print the priced figure when there is one. The BOM export (E-14)
  carries a header block (customer, project, date, system), the spec or
  model per line, the lines grouped by category and the pack rounding where
  an item is sold by the roll or box.

## The service area is the whole Philippines

- The owner's rule (9 October): "for the service area, just make it the
  whole philippines". The estimate's town picker now lists every city and
  municipality in the country (1,642, in 84 provinces with Metro Manila for
  NCR), from the PSA's PSGC names with OCHA/NAMRIA area-weighted centroids
  (CC BY-IGO), bundled in `backend/solarapp/core/towns_ph.json`; the server
  still looks nothing up outside. The status call carries the provinces and
  the page fetches one province's towns when it is picked, so a phone does
  not download 1,600 rows for one estimate.
- Independent and highly urbanised cities are listed under their geographic
  province (Cebu City under Cebu, Lucena City under Quezon), by the PSGC
  code, since that is where a visitor looks for them. A city keeps "City"
  in its name when the bare name is a province's (Batangas City, Quezon
  City) or when it is independent (Davao City); a component city reads as
  people say it (Lipa, Tanauan, Santa Rosa); Metro Manila's cities are bare.
- A pin more than 60 km from every town centre is "outside the Philippines"
  (the sea, or abroad) and the estimate says so; the old "outside Laguna
  and Batangas" label is still read on bookings saved before this change.
  The company profile's "Where you install" defaults to "the whole
  Philippines" and the website says so.
- Known limit: the freight run and the crew transport are still priced from
  the base in Pila with the pin's extra kilometres, so a far site carries a
  long trip; a regional base, or a freight rule per island group, is the
  owner's call when such jobs come.

## Round 4: the panel in the background, and an engineering status instead of the job stage

The owner (9 Oct 2026): "For the panel, make it automatic done on the
background and the section remove in data entry" and, of the stage pill,
"is this really necessary for the part of the Engineering/Technical team?"

- The Panel options card is gone from the On site step; a record no longer
  carries its own candidate panels. The candidates are the usable panels of
  the materials list: every active item of category Solar Panel that
  carries a wattage, a length and a width (the bundled list has four, the
  Blue Carbon 585, 585 bifacial, 600 and 630 W; the others wait for their
  size on the Materials page). Every candidate is fitted to the roof and the
  one with the most kWp wins, the owner's "Automatic (most kWp)" rule as it
  was; two panels at the same kWp go to the lower list price per watt. The
  code is the candidate's id, so the results, the roof check, the card and
  the proposal name the panel as they did. A list with no usable panel
  refuses the calculation with a plain message; nothing fits.
- Two ways to say otherwise. Pricing settings › System design carries
  "Panel on every job" (`sizing.panel_code`, blank = automatic): one code
  puts that panel on every job. The engineer may still pick another for one
  project, but in Design and outputs, not in data entry: the System design
  card opens with one line, "Panel: Blue Carbon 585 W (most kWp of the 4
  panels in the materials list) · Use a different panel", and the link
  opens a select of the candidates with what each fits. The choice is saved
  on the document (`panel_code`, blank = automatic) and Calculate applies
  it. A code that is no longer a usable panel is said so in the results and
  the automatic rule applies. The setting moves the price, so it is part of
  the pricing settings' version.
- Old records. A forced panel that was a materials-list item becomes the
  project's `panel_code`; panels typed by hand are dropped when the record
  is read, named under `dropped_panels`, and the next calculation says "the
  panel typed by hand (X) was replaced by Y from the materials list" once
  (a results warning and a log line), then clears the note. The pricing's
  wattage fallback for an unlinked panel is unreachable now and stays as a
  safety net only.
- The website estimate keeps its own typical-panel rule: core/quick.py reads
  one code from the website settings (`quick.panel_code`, BC-PNL-001 by
  default) and never the candidate list, so the visitor's figure does not
  move when the owner adds a panel to the list; the roof visit settles it.
- The job stages were never the engineering team's: Quoted and Signed are
  the CRM's facts (when the proposal was sent and accepted), Sourcing to
  Closed are the PM module's. The engineering app knows four things and
  shows them as a read-only status on the project head and in the list:
  Draft (nothing measured yet), Surveyed (at least one reading set saved),
  Designed (results calculated and not stale), Proposal issued (the
  proposal PDF was generated for the record, with the date). Nobody types
  it; the only control is "Reopen design" beside an issued proposal, which
  asks first and clears the mark. The mark lives on the record
  (`proposal_issued_at`), outside the document, so a Save never wipes it; a
  stale design keeps "Proposal issued" because the customer holds that
  proposal until the engineer says otherwise.
- The price lock from round three keys off "Proposal issued" instead of
  stage quoted: once the proposal is out, Calculate refuses to re-price
  under changed pricing settings (409) unless confirmed, and a confirmed
  re-price keeps the proposal issued; after Reopen design the job re-prices
  freely. The job stage stays in the document for the CRM and PM modules
  (the funnel endpoint still reads it; nothing deletes it) but no screen
  shows or edits it; the project list's filter is the status. The program
  of works keeps its signing date as an input.

## Accounts, round four: a question is asked at the moment of the action

- The owner's words: "the user management is really not intuitive ... I want
  the user experience to feel like I am just browsing Facebook-level easy."
  The round-4 UX specification (part 2) was built as written, with no API
  change: People is a list of person cards and Your account is four plain
  rows, and every action is a dialog of the app's own. No native `prompt()`
  or `confirm()` remains anywhere in the back office.
- One `Dialog` component carries every question: a focus trap, Escape and the
  backdrop cancel, the primary button is the only black one, a refusal from
  the server prints inside the dialog under the fields and the dialog stays
  open. On the phone a dialog is a sheet from the bottom (Add a person is a
  full-height sheet) and every target is 44 px. The "⋯" menu is a popover on
  the desk and a sheet on the phone. The styles live in `accounts.css`,
  imported by the components that use them, so `styles.css` is untouched.
- The standing "Confirm it's you" form is gone. The password (and a fresh
  code when two-step verification is on) is asked inside the dialog of the
  action that needs it: turning two-step on or off, adding or removing a key,
  changing the password. The API already took `{password, code}` on each of
  those calls, so nothing moved on the server; the rule that a stolen cookie
  alone cannot change how a person signs in is unchanged. A wrong password or
  code is named as such ("That password is wrong. Try again." / "The password
  or the code is wrong.") instead of the server's generic step-up sentence.
- Two-step verification is a switch. Off → On is one dialog in three steps
  (password; QR or the typed key with Copy, then the code it shows now; the
  eight backup codes with Copy all and Download). The switch flips only after
  the person has kept the codes (Done wakes after Copy or Download, or after
  five seconds), and Escape at the last step still flips it, since the server
  already has it on. "Two-step verification" is the only name for it in the
  owner's UI; "authenticator app" names the phone app, never the feature.
- Adding a person asks for the Name first and suggests the username from it:
  lowercase, accents stripped, the first name, a dot, the rest of the name
  joined ("Juan dela Cruz" → `juan.delacruz`, so a surname with a particle
  reads as one word), anything else a dash; the field stays editable and a
  taken username answers "Taken; try juan.delacruz2" inline. The role is two
  tiles with what each can do; Engineer is preselected. The temporary
  password is shown in a box with a Copy button that reads "Copied" for two
  seconds (where the clipboard is blocked the text is select-all); the card
  appears in the list behind the dialog with "Temporary password" in the bad
  colour. The owner's flow is 7 taps (Settings, People, Add a person, Name,
  Add, Copy, Done), the spec's count, and no username is invented by hand.
- The first-sign-in gate no longer asks for the temporary password the person
  typed ten seconds earlier: the login form keeps it in memory (a module
  variable, never storage) and the gate sends it silently, so the form is
  New password with a live checklist (12 characters or more · not your
  username · 5 different characters) and New password again: 6 taps from the
  login page to the app. After a reload the memory is gone and the field
  "Temporary password" reappears with "Type the temporary password you were
  given once more"; if the remembered one is refused (the owner reset it in
  between) the same field reappears with that reason.
- People's words are the owner's, not the server's: "has not signed in yet",
  "signed in today 5:38 AM", "last signed in 2 Oct, 4:10 PM"; "Password
  only", "Two-step verification on · 1 security key", "Temporary password";
  "Remove access" / "Restore access" and "access removed" on a muted card,
  never "Deactivate"; "Turn off two-step verification" names what it removes
  ("Their authenticator app and 1 security key are removed.") and calls the
  unchanged `/reset-authenticator`. The owner's own card has no menu, only
  "Your account ›". The empty state (only the owner) is a dashed card with
  the same Add a person button. A removed person's card carries no date: the
  API has none, and nothing is fabricated.
- Kept for the forms agent's Settings pages: the component names and props
  (`AccountCard` with `user` and `onUser`, `PeopleCard` with `me`), plus an
  optional `heading={false}` so a page with its own h1 does not print the
  title twice. "Your account ›" links to `/settings#account` on the one-page
  Settings and to `/settings/account` from anywhere else. Left as the spec
  notes them: "Last changed" on the Password row (needs `password_changed_at`
  on `/api/auth/me`) and "Show new codes…" (needs an endpoint that regenerates
  the backup codes); until then the rows say what the API knows.
- The proof: Playwright at 1280×900 and 390×844 adds a person end to end (the
  password copied from the dialog, the new person signing in on a second
  context, choosing a password at the gate without retyping the temporary
  one, turning two-step on from the switch with a computed authenticator
  code, adding a virtual security key with a backup code as the fresh code,
  signing in with the key alone), resets a password and turns two-step off
  from the menu, removes and restores access, and counts the taps (7 owner,
  6 engineer). A security key is bound to a hostname, so the proof runs on
  `localhost`, not `127.0.0.1`: the browser refuses an IP address as a
  relying party, which the dialog reports in plain words and stays open.

## Round 4, forms: the pattern on every field, Settings as a menu, the project's inputs folded

- The owner's screenshots of round 4 (14 to 18 and 20) were not alignment
  but content never designed for a form: 13-decimal workbook floats, a
  JSON box, comma lists, units cut by a 45 % cap, 56 number settings with
  no unit because they had no META entry, help texts of twelve lines
  stretching their whole row, a block headed twice, two tables sitting
  beside single fields, lowercase row names, "…" summaries. Nine rules
  close them and the rules are now the form system's contract: a number
  reads as a person says it (`NumberInput` takes `decimals`, rounds the
  shown value and keeps the stored precision until the owner retypes;
  money 0, rates per kWh or km 2, hours 2, percent 1, counts 0, metres 2,
  km 1, factors 2, volts 1, coordinates and physical constants 4); a unit
  sits beside the control at twelve characters or fewer and is never
  clipped (a longer qualifier is the help line); the help under a field is
  one line of at most 24 characters in a four-column cell and the long
  text sits behind a "?" beside the label (`Field` takes `about`; the note
  opens in a lane that spans the whole grid line under the row, the line
  below moves down, one note at a time, Escape or a tap elsewhere closes
  it; the form grid's subgrid has a fourth row for the lane); a table is a
  block on a line of its own (`own-line`), never beside a single field;
  a block has one heading; nothing is a JSON box (the ground tasks, the
  route's stops, the breaker sizes, the word lists and every size table
  are editors with Add and Remove; a shape the editor does not know says
  "Set by the developer"); spinner arrows are nowhere (one CSS rule); labels,
  options, row headers and link-buttons are sentence case; nothing ends in
  "…" (Gantt labels wrap to two lines); the form never asks what the app
  knows (a default is shown untagged, only an override is tagged).
- Every one of the pricing settings has a META entry (label, unit,
  decimals, one-line help, long text) in `pricingMeta.ts`, and a backend
  test reads that map against `PricingConfig` so a setting added without
  its entry fails the suite. The stored workbook floats are untouched:
  rounding only the display moves no price. A ground task the owner
  removes from the table counts no hours instead of crashing the engine.
- The owner's words, mid-round: "instead of 1 continuous form, why not
  show what's only relevant to the menu you already created?" Settings is
  eleven pages, one route each (`/settings/company`, `/settings/website`,
  six `/settings/pricing/...` pages, `/settings/account`,
  `/settings/people`, `/settings/data`): on the desk a left menu with the
  one page beside it, on the phone a list of cards that opens one page
  with a way back; the browser's back button works and the top bar names
  the page. The six pricing pages share one draft of the pricing config
  (`PricingDraftProvider`), so an owner may edit Labor then Freight and
  save once; each page's sticky bar names the edited pages, the menu marks
  them with a dot, Discard stays in the bar and Reset to defaults lives at
  the foot of Materials and markup (with the ten-second undo). The website
  estimate's assumptions moved from Pricing to the Website page, whose Save
  writes the profile and the `quick` section in one press; the company base
  is a name and a map pin on the Freight page. "Find a setting" at the top
  of the menu lists every match across the pages ("VAT · Materials and
  markup › Fees, markups and VAT"); a result opens its page with `?find=`
  in the address, opens the fold it sits in, scrolls the field under the
  top and rings it for two seconds. Your account and People keep their
  components and routes; their insides are the accounts batch's. Links
  from before the menu (`/settings#account`) land on their page.
- The project's Pricing step shows what a job decides (the inverter, the
  battery, the strings and the extra distance; the tariff; the signing and
  installation dates) and folds the company defaults under "Adjust for
  this job", a line that opens itself while it holds an override and says
  how many. The payment terms are one line ("Company terms: 50% on signing,
  40% on delivery, 10% on switch-on · Change") and the editor opens only on
  Change. The roof productivity factor reads as a percent on the step as
  it does in Settings.
- Measured on the seeded private app before and after (desk and phone,
  the audit's scanner): raw floats 9 → 0 (the three left are the read-only
  copper constant and the base coordinates at the spec's four decimals),
  JSON boxes 1 → 0, comma lists 5 → 0, clipped units 12/14 → 0, number
  settings without a unit 56 → 0, help texts over one line 47/49 → 0,
  spin arrows drawn 252 → 0 (the inputs stay `type=number` for the numeric
  keypad; the arrows are hidden), lowercase strings 8 → 0 in these files,
  "…" 25 → 0, duplicated headings 1 → 0, off-grid lines 4 → 0. The scanner
  still lists a "?" or an override tag as a cell's first button; measured
  on the controls alone the lines are on one edge.

## Round 4, plans: the layout legible, and the plans for the PEE

The owner, 9 October 2026: "for the roof layout, I think it is too small to
be seen properly. And I don't see where I can get the plans that will be
handed to the PEE for signing." Then: "The plans should be in A3 not A4."

- The plan drawing on the Design and outputs step takes the card's width
  (up to 900 px on the desk, the full 344 px on the phone), one face to a
  row, with the whole drawing capped at 600 px tall: a face taller than
  wide keeps a scale that reads instead of shrinking to a thumbnail. It
  now carries dimension lines in metres (the eave and the slope as the
  outer figures, a hip's ridge above, and the strips that hold no panels
  as a near chain: the setback on each edge, or a wall strip as hatched),
  the string number under each used panel (S1, S2 … as the current rule
  numbers them) and a north arrow. "View larger" opens the same drawing in
  the one Dialog at the largest size that fits the screen, captioned with
  the face, where it looks, the tilt, the panels used of possible and the
  kWp. The dialog kit sizes itself for questions (460 px, under the page's
  sticky bars); the drawing sets its box to the viewport and lifts the
  backdrop above the step tabs and the action bar from inside, and undoes
  it on close. Worth a one-line kit change later: the backdrop's z-index
  should sit above the sticky bars for every dialog on the project page.
- North on a plan whose eave is at the bottom: the drawing's "up" is the
  direction the ridge lies in (azimuth + 180), so north sits 180 − azimuth
  degrees clockwise from up (a south face has north up, an east face has
  north to the right). The same rule in the PDF and the React drawing.
- "Plans for the PEE" is a new internal document (Documents card, needs
  pricing; GET /api/assessments/{id}/plans.pdf), refused on stale or
  design-blocked results the way the proposal is and without pricing (no
  BOM, no circuits), but not on test weather (internal, like the program
  of works). A3 landscape (420 × 297 mm) on every sheet, drawn with
  ReportLab from the geometry, the BOM and the settings the results hold:
  a title block on every page (company name and contact line; the project:
  customer, address, number; the sheet name and "Sheet n of N"; the issue
  date and the revision; the sheet size; the signature block for the
  Professional Electrical Engineer with the name and PRC number from the
  company profile, blank lines when the profile has none, and blank lines
  for the PTR, TIN, signature and date, which the app never holds). Sheet 1
  is the cover and general notes; one sheet per roof face that holds
  panels carries the array layout at the largest standard scale that fits
  (1:20, 1:25, 1:30, 1:40, 1:50 …), stated on the sheet and in the title
  block, with the dimension lines, the setback strips, the panel size and
  spacing, the panel numbers and string labels, the obstacles as surveyed,
  the north arrow and a legend; then the equipment and circuit schedule
  (inverter, battery, panels with the data on file; the DC side; the AC
  side per the round-3 circuits; the battery circuit; grounding and
  bonding; the BOQ's voltage drops against the limits); then a last sheet
  that says what is not yet in the set and why, with the energy audit's
  schedule of loads as a table, labelled as the audit's figures, when the
  audit has appliances.
- Nothing invented: every number is from the results, the BOM lines, the
  materials list or the pricing settings, and a figure the app does not
  hold prints as a blank line (`BLANK`). No clause numbers; no standard is
  named unless the materials list records it (the inverter's certificate).
  Where the signing engineer adds the clause the line reads "per the
  applicable code, to be completed by the signing engineer" (derating,
  conduit fill, the short-circuit note, the grounding conductor sizes, the
  wind zone, the placards the LGU and the DU ask for). The revision prints
  as "Rev. 0" beside the calculation's date and time, because the app keeps
  no revision history: a set regenerated after a change carries a new
  calculation stamp, and the PEE marks revisions by hand.
- The single-line diagram and the string table (Voc at the coldest cell,
  Vmp at the hottest, Isc per MPPT) stay out of the set until the panel
  and inverter datasheets are on the Materials page; the last sheet names
  which fields are still blank. The string current and voltage on the
  schedule are the wiring rules' figures (the Vmp per panel setting) and
  say so.
- The plan drawing's keyword options (`dimensions`, `scale_denominator`,
  `string_labels`, `north_arrow`, `font_pt`, `legend`) are off by default,
  so the roof check and the proposal print exactly what they printed.

## The export credit is the bill's generation charge

- The owner's rule (9 October): the assessor types the DU's generation
  charge per kWh from the customer's bill, so the net metering credit is
  the electric company's own rate. The field sits on each bill under
  Energy audit › Electricity bill; the savings take the latest bill's
  figure, a per-job entry on the Pricing step still wins, and only
  without either does the settings' figure apply, with a warning on a
  grid job. The Pricing step and the proposal say where the figure came
  from ("From bill 2026-09" / "the generation charge on your bill").

## The cashflow and the installment structure are finance, not engineering

- The owner (9 October): "move the cashflow to the finance module, along
  with the installment structure if there will be any rather than giving
  it to the engineer." The Cashflow card is gone from Design and outputs,
  the cashflow pages from the program-of-works PDF, and the per-project
  payment-terms editor from the Pricing step. The proposal prints the
  company's payment terms from Settings › Program of works (the owner's
  page); a project saved with its own terms keeps them until the finance
  module takes them over. The cashflow engine stays in the results behind
  the API for that module; no engineering screen reads it.

## Round 5: the first real photos on the website

- The owner sent thirteen drone frames of three installations (10 October) and asked that the audit team work on
  the website with them. Only web versions are committed (`site/tools/photos.py`: exact 4:3 crops at 960 and 480 px,
  WebP with a JPEG fallback, metadata dropped); the originals stay with the owner.
- What a caption may say: only what the frame shows, or a process claim the site already makes about the company.
  No town, size, system kind, date, customer name or address until the owner gives it and the customer has agreed;
  then the town only. "Our installations", not "Recent", until the months are known. The marketing audit
  (`docs/audits/round-5/marketing.md`) found the first captions claimed a fixing method and a fourth face the frames
  did not show, and a lead ("measured on the roof first … after switch-on") no one had confirmed for those jobs;
  all three were reworded to what is certain.
- Which frames are published: 25 (hero and share image, cropped so the customer's aircon unit and its brand are out of
  the frame), 27, 36 (cropped to lose the yard and most of the neighbour's house) and 35 as the three cards, 37 on
  About. Never: 29–32 (installation-day clutter, a legible sign, four people at the gate without consent) and 33–34
  (the neighbour's house and washing fill the top third). The engineer's review (`docs/audits/round-5/engineering.md`)
  had held 36 and 35 back; the owner's answers (10 October) cleared them: the black runs on the hip roof are HDPE
  conduit and the final state; the orange run on the rib roof is the PV-wire conduit on rails fixed with L-feet
  through the sheet; the three-roof property was photographed between nine and ten in the morning and "the design
  provided extra panels so that shadings will not bring the production down too much". The captions say so.
- The owner's facts, printed on the cards: the rib roof is 8 panels, 4.56 kWp, a 6 kW grid-tie inverter, no
  battery, not on net metering, installed early 2026; the hip roof is 16 panels, 9.12 kWp, a 12 kW hybrid inverter
  with no battery attached and no net metering, early 2026; the three-roof property is 13.75 kWp with a 30 kWh
  battery, a 12 kW hybrid inverter and a 6 kW grid-tie inverter carrying a 5.5 kWp part of the array, net metered
  since 2023, with ₱33,568.72 of credit accumulated (printed as "more than ₱33,000"). The owner flew the drone;
  these are family homes; the test-panel roof visit did not yet exist when they were designed, so the lead says
  "Our own installations, photographed by us from the air. No addresses, no names." and nothing about measuring.
  Towns were not given; the cards carry none. Counts by the engineer, from the frame lines (the half-cut split is
  not a panel edge): A 8, B 16 on three faces (6, 6 + 2, 2; the fourth face empty), C 37 (18 + 9 + 10).
  Every page shares the home roof until a page has a photo of its own (`<!-- og_image -->`).
- No "Our work" page until there are six or more sites each with a town, a size, a month and the customer's yes.
- The UX audit of the pages with photos (`docs/audits/round-5/ux.md`) found nothing that blocks a visitor and
  nineteen things to tidy; all the one-hour ones are done: the header's gold button and the hero's eyebrow now pass
  contrast; the full navigation waits until 860 px (the menu button serves tablets in portrait); anchors scroll
  clear of the sticky header; every profile-dependent fragment starts hidden (the build adds `is-empty`), so no
  page shows "PRC No. ." while the profile loads or when it fails; the fonts ship as WOFF2 (54 KB instead of
  146) and are preloaded; the hero photo is capped at 560 px on tablets; captions, tap targets, the phone's small
  text, the share card for X and Telegram, the About title, the estimate page's loading line, the menu's Escape
  key and the focus ring follow the report. Left for later: a 720 px photo variant and a metric-matched fallback
  font (both half a day for a small gain).
- The UX audit of the pages with photos (`docs/audits/round-5/ux.md`) found nothing that blocks a visitor and
  nineteen things to tidy; all the one-hour ones are done: the header's gold button and the hero's eyebrow now pass
  contrast; the full navigation waits until 860 px (the menu button serves tablets in portrait); anchors scroll
  clear of the sticky header; every profile-dependent fragment starts hidden (the build adds `is-empty`), so no
  page shows "PRC No. ." while the profile loads or when it fails; the fonts ship as WOFF2 (54 KB instead of
  146) and are preloaded; the hero photo is capped at 560 px on tablets; captions, tap targets, the phone's small
  text, the share card for X and Telegram, the About title, the estimate page's loading line, the menu's Escape
  key and the focus ring follow the report. Left for later: a 720 px photo variant and a metric-matched fallback
  font (both half a day for a small gain).
- Open with the owner: per site the town, the kWp, battery or net metering, the month, whether the test-panel
  visit was done and the customer's go-ahead; who flew the drone; site A's orange cable and how the rails are
  fixed; whether site B's cables were tied under the panels and run in conduit after the photo (an "after" frame
  at mid-day would make it the best site on the page); the hour site C was photographed, how the design handled
  the palms and the annex row under the eave. The engineer's list of the photos to take on the next job (fixings,
  clamps, under-array cabling, the roof exit, the combiner, the inverter wall, grounding, the two-way meter, the
  signage, a mid-day drone pass after clean-up) is in the report.

## Three BOM roles the owner struck out

- The owner, on the round-3 BOM (9 October): the L-foot fasteners are part
  of the L-foot the company buys, placards are miscellaneous, and the
  monitoring dongle comes with the inverter. The three roles (and their
  counts) are gone from the settings and the BOM; a stored configuration
  that still carries the keys loads with them ignored. The array bonding,
  the AC disconnect and the optional export limiter stay as roles.
- A BOM line whose code is not in the materials list now names its role
  ("Export limiter (no item in the materials list)") instead of "Code not
  found", so the crew and the PEE read what the design needs; it still
  carries no price.

## The estimate's location button fills the town in

- The owner (10 October): "fix the awkward use my location button on the estimate since no map is shown anymore
  on the widget." With the nationwide town picker there is no map, so a location that only set an invisible pin
  left the two pickers blank and a hint saying "location set". Now the phone's location is turned into the
  nearest town by the server (`GET /api/quick/place?lat&lon`, the same rate bucket as the towns list, "inside"
  false beyond `OUT_OF_AREA_KM`), the Province and Town pickers fill themselves in, and the hint says "Your
  location points at Pila, Laguna. Change it if that's not where the house is." The visitor can still pick
  another town. The third column with its hidden "Or" label is gone; the action is a link in the hint under the
  pickers ("At the house? Use my location and the town fills in."). If the lookup fails but the phone gave a
  location, the estimate still runs on the pin as before; outside the Philippines the hint asks for the town.

## Round 6: the website's words sell the feeling

- The owner (10 October): "I want the marketing and the copywriter to work together and instead of full solar
  terms let's make it so that it will sell emotions, for example the battery = comfort is a good start." A
  copywriter role joined the team (`.claude/agents/copywriter.md`); the round ran as brief → draft → review:
  the marketing specialist's angle brief (`docs/audits/round-6/marketing-brief.md`), the copywriter's rewrite
  (`copywriter.md`), the specialist's line-by-line review (`marketing-review.md`, five wording changes, applied
  at the merge).
- The register, now the rule for anything the customer reads: picture, fact, step, in that order. A feeling word
  describes the customer's life (the fan at 2 a.m., the fridge, the homework, the bill that stops being dreaded),
  never the product; the equipment is one plain sentence after the picture; the customer's words over the
  engineer's (brownout, the bill, the meter, the roof, the papers; never kWp, MPPT, string, grid-tie or hybrid
  except where a figure is asked for, as on an installation card); no exclamation marks, no superlatives without
  a figure, no "hassle-free". The feeling that leads each page: Home relief, Brownouts comfort, Net metering
  relief, About calm then pride, the estimate result control then relief, the thank-you calm.
- The honesty lines are kept word for word and the review checked all 73 of them: the three system kinds' names,
  every battery line ("for comfort, not savings, and we say so"; "adds little to the savings"), "It can come out
  lower or higher than the estimate, and it shows you why.", the installation lead, the six FAQ facts, the
  net-metering example and its small print, "An estimate, not a quotation". A battery sells comfort and backup;
  the panels bring the bill down. Lines that overstated left: "A bill of thousands, down to a few hundred"
  (the page's own example says about two thirds), "lowest price per kWp", "keeps producing for twenty more"
  (no performance-warranty years entered), "the moment the grid drops" (no transfer time on file; now "by
  itself").
- The owner's answers of 10 October, and what the pages do with them: the switch-over is "just milliseconds,
  seamlessly instant" as far as the owner knows, so the pages keep "by itself" until the inverter's datasheet
  gives the figure; after switch-on there is a new profile field (`after_sales`, Settings › Website) printed on About and as a
  home-page question; the owner first gave a schedule ("Kevin answers during office hours; on Messenger we reply
  within the hour at reasonable times") and then asked for it as after-sales support instead, so the default reads
  "After switch-on you are not on your own: call or message us and we answer as soon as humanly possible."; for typhoons there is no rating on file, and the
  installations "have withstood heavy wind loads", so the question answers with the fixing and the fact that
  the oldest installation, from 2023, has stood through every typhoon season since; the panel performance
  warranty is "standard 25 years" (the profile default is now 25; verify on the panel datasheet, and a
  deployment that saved Settings before this keeps its own value until the owner enters 25); the two brown roofs
  are in Pila, Laguna and the hip roof in Fairview, Quezon City, printed on the cards and the About caption with
  the lead now "The town, never the address or the name." Still open: the installation-day outage length, one
  agreed sentence from a photographed family, and the before-and-after bills of the two early-2026 homes.

## One visit: the roof and the energy audit together

- The owner (10 October): "The site assessment will be roof plus energy audit, no 2 visits." The home page's
  steps and the estimate's thank-you now describe one free visit (the test panel and meters on the roof, the bill
  and appliances at the table), the roof check card the same evening and the proposal within two working days.
  The steps say their times in the sentence; the small footnotes are gone ("What's with the small foot notes? Why
  not just say it directly?"). The customer still books a "roof visit" (the word that sells the measuring); the
  engineering app's On site step already holds both the readings and the audit.

## Brands as logos, not a sentence

- The owner (10 October), on the "Brands we install" card: "it's like an after thought that shouldn't be there, we
  can just add logos of the brand we install rather than this." The card is gone from "Why people choose us"; a
  logo strip waits as a placeholder (dropped from the public build) until the owner sends the makers' logo files
  and the names; the profile's `brands` line stays for the proposal. No brand is named or drawn until then.

## Round 7: a marketing website, not a blog

- The owner (10 October), on the live site: "anti marketing or sales", "the website looks like a blog rather than a
  marketing website", then "I want it marketing, salesy, dynamic not purely static and blog esque. Go." The round
  ran as: the marketing specialist's anti-sales audit (`docs/audits/round-7/marketing-audit.md`, 24 lines ranked by
  lost sales, the proof not yet used, the headline per page, the phone's first screen), the UX specialist as
  designer (a worktree: photo heroes, a proof strip, the homes as swipeable proof cards, a stepper, an icon grid, a
  compact FAQ, a sticky call to action on the phone), the copywriter on the merged layout (`copywriter.md`), the
  specialist's final review (`marketing-review.md`), the coordinator's walk.
- Dynamic, inside the site's rules: motion comes only from `site/static/site.css` and `site/static/site.js` (the
  public site allows `script-src 'self'`, no inline script, no outside call): the hero photo breathes, sections
  come in as they scroll into view, the ₱33,000 and the 3 count up once, cards lift under a pointer, the sticky bar
  shows after the hero and hides while the band or the footer is in view; all of it off under
  `prefers-reduced-motion`, and every page complete with JavaScript off. A block several pages share lives in
  `site/partials/` and `<!-- include: name -->` pastes it at build time.
- The phone's first screen is a roof, the promise and the gold button; the proof strip under it carries the four
  figures the facts allow (more than ₱33,000 of credit on the owner's own bill; the owner's home on solar since
  2023 and through every typhoon season since; three family homes in Laguna and Quezon City; one free visit).
  Measured: no sideways scroll at nine widths, layout shift under 0.001, the home page about 500 KB on the phone,
  every text passing contrast on every background including over the photos, nothing under 14.5 px on the phone.
- The words: headlines ask for the want ("The bill goes down. With a battery, the lights stay on.", "Which one is
  you?", "We live with what we sell.", "What you keep on when the street goes dark.", "Your meter runs both ways.",
  "Our oldest roof is our own."); the honesty lives inside the sentence (an estimate to decide with, the roof visit
  makes it exact; the panels do the saving, the battery buys the comfort); nothing beyond the owner's facts. The
  estimate widget followed the same audit: the first option says what it gives, "Saved over 25 years" sits beside
  the price, the booked visitor is thanked, the booking card lists the warranties and, once Settings carry them,
  the owner's name and number.
- Not inferred: the owner is named as "the owner" and the homes as "the owner's parents' house" and "the owner's
  wife's family house"; no pronoun is used for the owner anywhere on the site. The inverter sizes and the mounting
  words left the home cards (the chips carry the kWp); they remain on the engineering side and the proposal.

## The estimate's result: the form folds away, the system builds itself, a day plays out

- The owner (10 October): "after they entered their answers the form disappears and the estimate is shown along with
  an animation like the number of panels shown, the batteries, inverter, their house with dots travelling showing the
  flow of energy, then a 48 seconds (2 seconds duration per 'hour' of 24 hours) showing how it works with animation
  of sun up to down to moon etc." Then: "they can just Estimate another one (closes this card and opens a fresh form)
  or book my free roof visit - actually roof visit feels off, make it an on-site assessment."
- The figures behind the animation are the sizing's own: each variant carries `production.typical_day`, 24 rows
  averaged over the twelve months' typical days (what the panels make, what the house uses, what goes straight to
  the house, into and out of the battery, to the grid and from it, kW at the meter; the battery's state in kWh).
  Nothing in the scene is drawn from a number the engine did not produce.
- The scene (`frontend/src/estimate/DayScene.tsx`): a build-up once (the house, the panels one by one with the
  count and the kWp, the inverter, the battery when there is one, the meter and the pole), then the day from 6 AM
  at two seconds an hour, the sun's arc, the moon, the sky's colours, dots along the paths in proportion to each
  hour's kW, the battery's fill from its state, a readout and a caption that follow the row's figures. Play, pause,
  replay and a 24-stop scrubber; nothing moves on its own under reduced motion; the loop pauses off-screen and in a
  hidden tab; no library.
- After the estimate the question card is gone; under the figures: "Book my free on-site assessment" and
  "Estimate another one" (a fresh, empty form). A booked visit stays booked across estimates.
- The visit is the "on-site assessment" from the owner's word, on the website and in the estimate; the earlier rule
  that the customer never reads "assessment" stands for the documents (the roof check, the proposal), which keep
  their names.

## Moving house is answered on the phone, not on the page

- The owner (10 October), on the FAQ "What if we move house?": "that's not how it works, yes, the net metering stays
  on the house but we can help transfer the solar system to their new place, there so many variables at play so we
  might as well just answer this over phone no need to put it on the FAQ." The question is gone from the home
  page; nothing on the site says what happens on a move.

## The estimate's questions are cards, one at a time, with cues that answer back

- The owner (10 October): "instead of a form, find a way to make the questions into a card so they will not feel
  pressured when answering it with a slight card change animation when clicked on next or something, make it
  interactive, their answers showing cues on the screen, for example when choosing daytime nighttime energy use,
  you can show some animation that denotes day time and night time and so on."
- `frontend/src/estimate/Wizard.tsx` and `wizard.css` (the second inline stylesheet of the widget): four cards,
  "1 of 4" with dots, Back and Next, the words of the questions unchanged. A choice on the first card lands for a
  third of a second and advances; the town and the usage cards advance on Next; the last card's choice lands and
  waits for "Show my estimate" (the builder had it run the estimate on the choice; the coordinator made it wait, so
  the visitor presses the button on every card the same way). The card slides out and the next slides in (320 ms;
  instant under reduced motion; one card in the DOM apart from the slide).
- The cues, inline SVG above each question, gold on ink: the house with the meter spinning backwards for "a lower
  bill", the dark street with lit windows and a glowing battery for "lights in a brownout", the full battery and the
  faded grid line for "nothing sold back"; a pin that drops onto the town with its name; a dial that fills with the
  kWh or the pesos; and the day-and-night loop (the sun's arc, then the moon, the windows and the aircon lit in the
  morning, all day or in the evening to match the pattern). Nothing in a cue claims a figure.
- `estimateAnother` brings back card 1 with nothing pressed; the result and its day scene follow the last card.

## The public estimate keeps the recipe to itself; the family voice on the pages

- The owner (10 October), on the result's "How we worked this out": "it's like we are telling our competitors this
  how you can beat our price since this is how we computed it … this was suppose to be free for the potential
  customers but you've provided way more for potential competitors." The price split (materials, installation and
  permits, VAT, the battery's share) and the assumptions (the sun records, the panel derating, the losses, the trip,
  the tariff and its rise, the export rate, the battery's usable share) are gone from the website's result, and the
  public API no longer sends them: `public_view` in the estimate route strips `assumptions`, every price figure but
  the total, and the loss figures from `production` for a caller who is not signed in. The signed-in office sees
  the full payload. The result's foot keeps one line: what the house uses and when, the CO₂ avoided, and that it is
  an estimate, not a quotation, made exact on the on-site assessment.
- The booking card's trust lines: "Installs in the Philippines" is gone ("super awkward"); the company name and
  town are a plain head line, the ticks only on the engineer's seal, the brands, the warranties and the owner's
  name and number once Settings carry them.
- "The owner" left the pages ("owner of what is what I would ask if I am the customer"): the homes are "Our home",
  "Our parents' house" and "Our family's house" in Quezon City, the credit is "on our own bill", About says "The
  same people on every visit, an engineer on every plan."
- The estimate widget's script now answers with `Cache-Control: no-cache` on both processes, so a redeploy shows on
  the next load instead of after the browser's heuristic cache expires.

## The second round on the cards and the scene: fewer cues, a slider, 24 seconds and no controls

- The owner (10 October), on the merged cards and scene: "We can remove the animation on the first question, in
  the location too, and instead of 3 choices we make it a 3 point slider for the question 4, instead of sun moon
  cycle let's just show a morning animation showing more people are in the house in the morning, or more people in
  the house in the evening, that's it. As for the show estimate the energy flow is not that good for energy coming
  from solar it's hard to understand it unlike the grid flow. We should also make it 24 seconds for 24 hours,
  remove the replay and play controls and just make it a continuous animation."
- Cards 1 and 2 carry no cue; the question and its choices sit at the top of the card and the stage's height eases
  between cards. Card 3 keeps the dial. Card 4 is a three-stop slider (Mostly morning · All day · Mostly evening;
  "All day" to start) with the people scene above it: the same section of a house, a dawn sky with four figures at
  the kitchen, the laundry and the pump for the morning, daylight with two for all day, a dusk sky with four on the
  sofa, the TV and the aircon lit for the evening; the figures crossfade in 400 ms and stand still under reduced
  motion. No sun-and-moon cycle. The slider's stop still lands and waits for "Show my estimate".
- The day scene runs one second an hour: 24 seconds a day, the build-up once, then the loop without end. Play,
  pause, replay and the scrubber are gone. The flow from the panels follows a drawn conduit (gold, down the roof's
  edge to the inverter and on to the house), the same way the grid's flow follows the service drop, with a pulse at
  the array and "from the panels", "to the house", "to the grid" or "from the grid" at the path ends while that
  flow runs. Under reduced motion the scene is one still frame at noon with the readout for that hour.
- The hourly caption is no longer a live region: a screen reader announced it every second. The SVG's `role="img"`
  label describes the day once; the readout stays visible text.

## A redeploy shows at once: stamped assets, revalidated pages

- The owner (10 October): "check why even after updating the website, the old one still appears on a desktop or a
  phone, we need to make sure that regardless if it is www.pldevinc.com or pldevinc.com we show only the latest
  version of the website." The cause, in the code: the pages went out with `Cache-Control: no-cache`, but the
  stylesheet, the site script, the photos, the fonts and the widget script went out with no cache instruction at
  all, so a browser kept them by its own heuristic (a share of the time since the file's date, days for files that
  rarely change) and Cloudflare kept them at its edge by file extension. A new page then rendered with the old
  stylesheet and script, and the old estimate form kept appearing under a new page.
- `site/build.py` now stamps the stylesheet, the site script and the widget script with their content
  (`/static/site.css?v=77c6a36d`, the first eight hex digits of the file's SHA-1; the widget's stamp comes from
  `frontend/dist/widget/quick.js`, which the Docker build has made by then). A new build changes the stamp, so a
  kept copy is never asked for again. The fonts keep their plain address (the stylesheet names them without a
  stamp, so the preload and the CSS agree).
- `solarapp/caching.py` is the one policy for both processes: a stamped address under `/static/`, `/widget/` or
  Vite's `/assets/` is kept for a year (`immutable`); fonts, photos and brand marks for a day; any other static
  address is revalidated on every visit (`no-cache`, answered by a 304 when unchanged); the pages and the 404 are
  always revalidated. The two security-header middlewares apply it.
- The hostnames: the Cloudflare notes in `docs/security.md` already ask for the `www` → apex redirect rule; the
  note now adds why (two proxied hostnames are two caches) and the caching settings (Browser Cache TTL "Respect
  Existing Headers", no cache-everything rule, one Purge Everything after the deploy that introduces the stamps).
  The live site could not be read from the sandbox, so the Cloudflare side is the owner's to check.

## Rounds 8 and 9: the estimate in the website's voice, the installations without "ours", the result as a teaser

- The owner (10 October): "shouldn't it be emotion driven too similar to the whole website? Basically we sell
  emotions and outcome?" Then: the peso-amount field on the usage card goes ("it won't do help much in estimating");
  "Instead of 'our own homes' let's look for an angle of presenting the installations as proof that would not look
  like biased since it will feel like it is a personal claim and no one wants to listen to someone lifting their own
  chair." and, on the angle of saying it once as disclosure, "NO, we will drop ours entirely."; and "with the info we
  already provided, nothing else is witheld that will compel the potential clients to enter the funnel, shouldn't it
  be just a teaser making the customer wanting to know more?"
- Round 8 (`docs/audits/round-8/`): marketing's angle brief for the widget, the copywriter's draft, marketing's
  line-by-line review (54 accept, 4 change, 0 must go). The widget now opens on "Your new bill is a minute away.";
  the three goals are the home page's three wants ("I just want a lower bill." / "I want the lights on when the
  street goes dark." / "I want my roof to run my house.") with the kind's name opening the small text; the slider's
  stops say why the hour matters; the result is "Your estimate for {place}"; the hero says what stays in your pocket
  and what still comes; "What you get" and "What it does" replace the inventory; the battery alternative sells the
  evening when the street is dark and keeps the saving whole without it; the booking card is "The exact figure is one
  free visit away."; the day scene's captions describe the family's day and bend to the row (the grid topping up an
  evening the battery cannot finish; the panels "starting to carry the house" at dawn); the copied summary leads
  with the bill; "Try other answers" brings the cards back; the two engine warnings read as a person explaining.
- Round 9 (`docs/audits/round-9/`): the three installations stand as worked examples a buyer compares their own
  house to ("Three roofs in service. Which one is like yours?"; "Three roofs, one battery" / "Eight panels, panels
  only" / "Sixteen panels, hip roof"), with the record doing the persuading: on net metering since 2023, more than
  ₱33,000 of credit on that bill, every typhoon season stood, photographed from the air by us. No sentence on any
  page, the proof strip, the meta lines or the share snippets says whose house it is; About opens "Measured first.
  In service since 2023." The company's own lines (our crew, our workmanship warranty, our server) stay.
- The result as a teaser (marketing's version A, the coordinator's pick): the site's promise ("your new bill and the
  price in a minute") is kept, so the bill, the saving, the payback and the price stay; the kWp, the roof area, the
  kWh made, the coverage, the 25-year total and the CO₂ leave the page and land in the proposal; the scene's counter,
  chips and labels name the parts without sizes (the hourly kW readout stays as the proof); a closing block, "What
  the free visit settles", lists what the visit adds (the panels the roof really holds, what the battery carries from
  the house's own appliances, the exact price with every part and what is due when, the savings year by year and the
  25-year figure, the sealed plans and the papers, the dates), bending for the battery-first goal (no net-metering
  papers, no two-way meter) and for panels only; the sticky bar carries the new monthly bill. The engine, the lead
  payload and the e-mail are unchanged; the signed-in office still sees everything.
- Two defects fixed on the way: the first question card no longer slides in on load (the slide ran under the stage's
  clip and read as a clipped border in screenshots); the scene counts the hour before 6 AM as night, so a morning
  house never shows the evening caption at 5 AM.

## The visit yields the proposal, never the readings

- The owner (10 October), on the home page's "Your roof check: the same evening you get a card with what your roof
  can hold and what it can make": "For the on-site assessment, what we will provide is the proposal, not the
  assessment results because they might fish and give our assessment to other installers."
- Customer documents are now the proposal alone. The roof check PDF and the roof check card stay in the app as
  office documents (the documents card calls them internal; they no longer count as customer documents, so the
  test-weather lock no longer applies to them). The home page's steps go estimate → visit → proposal → installation,
  the "What you get on paper" list no longer carries the roof check, About's "one calculation" tick names the
  estimate and the proposal, the widget's thank-you goes from the visit to the proposal, and the result's closing
  block sells the proposal as what the visit leads to. The marketing kit's follow-up template for "the evening after
  the roof visit" is gone; the privacy page still lists the roof check among the records the company keeps.

## Rounds 10 and 11: the result closes on what you miss; the home page gets its hook

- The owner (10 October), on the result's closing block "What the free visit settles": "it should be what am I
  missing if I don't go contact them? We sell FOMO here." The block is now "What you miss if you stop here": close
  the page and nothing changes; next month's bill comes as it does today; about ₱N a month (the engine's own monthly
  saving, printed only when it is positive) paid to your electric company instead of kept; a roof nobody has measured,
  so the exact price and bill stay unknown; a battery sized to a typical house until your appliances are on the
  table; no sealed plans, permit or net-metering papers and nobody filing them; no dates on the calendar. The safety
  valve stays inside the block: the visit is free and nothing is decided until you say so. No scarcity, no deadline,
  no price rise: the only urgency is the engine's figure and the record. The copied summary's system line says the
  figures are a typical roof's until the free on-site assessment fits them to yours.
- The owner: "I am not seeing any hook on the website, I need a solid hook." Marketing's round-11 brief weighed five
  (the engine's example figure, the 2023 installation's credit, the dark street, the satellite-photo quote, the
  typhoon seasons) and picked the number: a figure the visitor can disbelieve and then check on the same page in the
  next minute. The home hero now reads "Home solar, sized to your bill" / "A ₱6,000 bill, down to about ₱1,900." /
  "Our estimate for a house in Tanauan using about 500 kWh a month, panels only. Pays for itself in about four years.
  Yours takes a minute." / "See my new bill". The brief had written ₱5,000 → ₱1,500 from an old peso-amount run; the
  copywriter re-ran the engine (net metering, Tanauan, 500 kWh, evening, today's price list and tariff: ₱6,003 →
  ₱1,893, 3.84 years) and the hook carries the engine's figures rounded to the hundred and the year.
  `test_home_hero_figures_match_the_engine` pins the h1, the title, the description, the lead, the net-metering lead
  and the ad line in `docs/marketing.md` to the same engine call, so a price or tariff change fails the build rather
  than leaving a stale number on the front page. The sticky bar says "Your new bill / Free, in a minute."; the home
  band "Your new bill is a minute away." with "Every month you wait is another month at the old bill"; the service
  area moved from the lead to the band so the lead stays four lines on a phone. Brownouts keeps the dark street as
  its own hook; About keeps the company's line.

## The brands strip carries the makers' marks

- The owner sent the five logos (10 October): Jinko Solar and Trina Solar, Deye and Felicity Solar, Suntree. They
  live in `site/static/brands/` as PNGs trimmed to one height (120 px, shown at 44 px on a desktop and 34 on a phone)
  on white tiles under "Brands we install" on the home page, in colour, with the maker's name as the alt text. The
  placeholder block is gone. No line says which brand goes where: the proposal names the parts.

## The datasheets in the app

Round 12, 10 October 2026: the engineer's brief (`docs/audits/round-12/engineer-brief.md`) read against the owner's
three datasheet workbooks (panels, inverters, batteries), steps 1 to 4 of its order of work built; step 5 waits on the
owner's answers to its section 6 (`docs/audits/round-12/implementation.md` has what was built and what is left).

- What was imported. `python -m solarapp.pricing.datasheets <files…> [--dry-run] [--report out.csv] [--apply-held]`
  (also the owner-only upload on the Materials page) reads each sheet's kind from its header words, never the file
  name; every row becomes a row of `datasheet_specs` (one per sheet row, never deleted; a re-run upserts by category,
  model and brand, and the same file twice changes nothing) and finds its material item in three tiers: exact (the
  model whole in the item's name or spec, the longer of two models an item names winning), contains (a one-word model
  that begins an item token; a multi-word text inside the normalised name and spec), base (the item's own model token
  as a prefix of the sheet's). The brand breaks ties; the category must agree. On the owner's files: 210 rows, 113
  matched, 90 specs-only, 7 skipped (the Solis orphan rows with no model), 6 held. Eleven fields were added to the
  items for it (the panel's maximum system voltage; the inverter's type, phase, battery-port class, charge voltage
  and current, per-input MPPT currents, battery inputs; the battery's nominal voltage, capacity and recommended
  discharge current), and `continuous_a` now means the battery's maximum continuous discharge current, the BMS limit.
- The precedence: the owner's edit on the Materials page > the datasheet > the materials workbook's electrical
  column > the remark inference. The datasheet is the maker's figure typed once per model; the workbook column is a
  transcription; the remark is prose read by regex and already disagrees with the sheet where both exist (the
  eco-hybrid's remark says 135 A, its sheet row 139 A). A field the owner types over joins the row's
  `overridden_fields` and is left alone on the next run; typing the sheet's own figure back lifts it. The grid flag is
  filled only when the item's is unknown; a disagreement is reported and the item stands (the eco-hybrid stays
  grid-interactive on the owner's word with the maker although its sheet types it off-grid). The rating fills only
  when blank; a difference is said and the item's stands (it is the price base). Because a materials re-import writes
  the remark inference back over every electrical field, the datasheet figures are re-applied at the end of every
  materials import, and the matcher runs again over the rows without an item so a renamed item is picked up; an
  existing match is never moved. Nothing on a sheet is corrected: an irregular cell is parsed by the brief's rule
  (the lower of two system voltages, the lower of a narrow charge-voltage range and the upper of a wide one, the
  per-input figure of "80A + 80A", an asterisk kept as a flag, a kW figure in an amps column left blank) and the row
  carries a notice the Materials page shows.
- Held. The Solis grid-tie 1P rows carry battery figures a grid-tie unit cannot have (brief 6.4); a battery maximum
  above 1 C would lift a hard block if it were a peak figure (6.8; the Felicity 100 Ah base row's 150 A against the
  item's 100 A). Both stay on the specs row and go on the item only on the owner's word: `--apply-held` (or the
  upload's tick) for every held row at once, or "Apply held figures" per row on the Materials page, since the answers
  to 6.4 and 6.8 may differ. The word is kept on the row (`held_applied_at`): a plain re-run, a materials re-import and
  the page all keep the figure, and "Withdraw" takes it back (the item returns to its remark's figure, or to blank).
- The checks, in the brief's order, each falling back to the rule that stood when a figure is absent and saying so:
  the battery circuit runs on the larger of the inverter's discharge and charge currents (the eco-hybrid 139 A, its
  breaker minimum 173.75 A, the same 250 A breaker and 70 mm² pair; the kW fallback over the battery's own nominal
  voltage); the recommended discharge rate is a soft check beside the hard BMS one; the inverter's charge current
  against what the bank accepts says what to set (135 A against 60 A: set 60 A, three units for the full rate); the
  voltage match holds the documents when the pack's class is not the port's (a 24 V pack on a 48 V port, an LV pack
  on an HV port) and says to lower the charge voltage when it is above the pack's ceiling; V × Ah against the kWh
  rating warns above 2 %. The strings are counted from Voc at the cold design temperature against the lower of the
  inverter's maximum PV voltage and the panel's system voltage (IEC 60891's linear term as IEC 62548 applies it;
  verify the editions; the irradiance term dropped, an assumption), the owner's `max_panels_per_string` becoming the
  cap; a strings override that forces more holds the documents; the hot Vmp against the MPPT window's low end is a
  yield warning. The string current is Imp, the string voltage per_string × Vmp, the PV conductor's ampacity and the
  DC breaker 1.25 × 1.25 × Isc (the PEC PV article's circuit current and the continuous factor; verify the clause; the
  1.56 is their product, never a setting), the DC breaker by rating when the role item is too small; the strings go
  on the MPPT inputs by their current ratings, largest first, the extra strings doubling up on the largest.
- The assumptions, all in Pricing settings › String design and each saying so in its help and in the warning a job
  carries: the design cold temperature 14 °C (the PVGIS typical-year minima of the Laguna and Batangas cells floored,
  less a 5 °C margin; the PAGASA record low of the nearest station replaces it when in hand), the design hot cell
  temperature 70 °C, the default temperature coefficients −0.30 (Voc), −0.35 (Pmax, used for Vmp) and +0.05 %/°C
  (Isc, information only). Per project the engine takes the lower of the cold setting and the project cell's
  typical-year minimum less the margin, and the higher of the hot setting and the cell's maximum plus the module's
  rise at 1 kW/m² (measured on the roof when plausible, else the Faiman model at the year's mean wind); the project
  may type its own two figures. No sheet carries a temperature coefficient, a maximum PV voltage or an MPPT window,
  so the string check runs on no residential job until the owner adds the columns (6.5, 6.6); every job says the
  strings follow the fixed rule until then.
- The outputs. The plan set's cover prints each model's datasheet figures with the file and date they came from or a
  blank line; the schedule prints the string current and voltage from the datasheet with the temperatures and the
  coefficients (and "default, an assumption" where one is), the two Isc lines, a string table (per string its count,
  Voc at T_cold, Vmp at T_hot, the limit, the margin, the input it sits on and its current), the DC breaker's rating
  check, the battery circuit on the larger of the two figures with the charge setting and the voltage match; its two
  columns are balanced by measured height and take a second sheet only when they cannot fit one; the string-table
  entry leaves the last sheet when the figures are on file; the sheet says "string design on datasheet figures from
  {file}, {date}". The Materials page shows where each electrical figure came from (datasheet, typed, remarks, none),
  the datasheet's figure beside a field the owner typed over with "reset to datasheet", the held rows, the datasheet
  rows without a priced item (with "Link to item…" and "Add as item": an inactive item at list price 0, never priced
  at zero) and the items without a datasheet. The website estimate is untouched: the same generator and the same
  catalogue; its rounded price with the seed alone is pinned (₱314,000 on the sample request) and the test states
  the figure with the datasheets loaded (₱326,000: the battery choice moves to the 15 kWh unit whose recommended rate
  covers the eco-hybrid's 139 A; the ranking is the review's, below).
- What waits on the owner (section 6 of the brief): the six panel rows whose brand column and model text disagree
  (matched on the maker in the text, both stored); the cells marked Verify or with an asterisk; the kW figures in the
  Felicity 3P rows' charge-current column; the Solis grid-tie rows' battery figures; the missing temperature
  coefficients, maximum PV voltages and MPPT windows (the importer's alias table already reads the columns the owner
  may add); the three One Solar charge-controller items that stand for nine sheet rows; the cells that do not add up
  (the Blue Carbon 25.6 V pack with a 60 V ceiling, the recommended currents above the maximum, the Felicity 1.5 C
  base row, the HV-typed 51.2 V row, the 102.4 V pack with a 230 V ceiling); and the two decisions the type column
  raises (the One Solar wall-type units now in the off-grid pool; whether a pure grid-tie unit may serve a
  net-metering job without a battery).
- After the engineer's review (`docs/audits/round-12/engineer-review.md`, 10 October 2026; verdict "merge with the
  fixes listed"; what changed is in `implementation.md` under "Review fixes"):
  - The automatic battery choice ranks the recommended rate before cost. Within the hard rank that stood (the BMS
    maximum covers the inverter's current; unknown; falls short) a pack whose recommended continuous rate covers the
    current ranks above one whose recommended figure is unknown, and that above one that passes only on its maximum;
    the maximum alone never promotes a pack. Otherwise the import rewards the sheet with the widest spread between
    its two columns (the JK rows: 200 A maximum against 80 A recommended) and the bank runs at 174 % of the
    recommended rate with a warning on every such job. The sample job's battery is FS-BAT-006 with the seed alone
    (150 A maximum from its remark, no recommended figure; nothing moves there) and FS-BAT-003 with the datasheets
    (150 A recommended ≥ 139 A), not the JK pack the review saw; the website estimate with the datasheets is
    ₱326,000 against ₱314,000 with the seed (the review saw ₱287,000 on the JK pack's maximum alone). A pack with no
    datasheet row (FS-BAT-006, the packages' 11.7 kWh unit) sits in the unknown tier until its row is linked or its
    recommended rate typed; the BOQ's battery options carry `recommended_ok` beside `current_ok`.
  - A pack of another class than the inverter's port is never offered by the automatic choice: the pack's class from
    `battery_class`, else from its nominal voltage; the port's from `battery_class`, else from its maximum charge
    voltage; judged only when both are known (a 24 V pack on a 48 V port, an LV pack on an HV port and the reverse).
    A per-job pick keeps the hard warning.
  - The sheet's generic type never fills the grid flag on an item whose remark says to check the certification: the
    remark is the owner's note about this unit and the catalogue answers "unknown" for it on purpose, so FS-INV-002
    stays unknown and is offered last on a net-metering job; the report says why.
  - "Add as item" takes the maker as the supplier only when a supplier of that name is on the SUPPLIERS sheet (Blue
    Carbon); else the owner picks one on the page or leaves it blank. The type words (`inverter_type`,
    `battery_class`) are enumerations on the API. A grid flag read from the item's name says "remarks" on the page,
    not "typed".
  - The AC note for a unit whose output exceeds the largest standard breaker size prints "above the largest
    standard size" beside the hard warning instead of failing the pricing (observed in step 4, fixed here).

## The plan set's groundwork: the title block, the circuits contract, the survey fields

Round 13, 10 October 2026: the engineer's brief for the rest of the plan set (`docs/audits/round-13/engineer-brief.md`),
step 1 of its order of work (section 7): the three pieces every later sheet builds on, so the office can start surveying
service entrances and roof construction while the single-line diagram, the design analysis, the site plan, the schedule of
loads and the mounting detail are built (`docs/audits/round-13/step1.md` has what was built and every departure).

- The title block (item 6). The signing engineer's lines come from the company profile (Settings › Company › Signing
  engineer): beside the name and PRC number, the PRC validity, the PTR number, date and place, the TIN, the PEE's address,
  the firm (or "sole practice") and its address, the phone and the email; none is public. The signature block prints
  them on every sheet: "{name}, PEE — PRC No. {no}, valid until {date}"; "PTR No. {no}, issued {date} at {place}"; "TIN
  {tin}"; "{address} · {firm}"; the firm's address, phone and email on a seventh line (the brief's six lines leave
  three of its fields unprinted, and the block's heading says every field prints); then the signature, date and seal
  line. A field the profile does not hold prints as a blank line, never a guess, and the last sheet names the blank
  ones and where to type them, dropping the entry when the profile holds them all. The project cell carries "Owner:
  {customer}" (the customer is the owner on the plans), the address, the kind in words, the system line, the date with
  the calculation stamp and the revision line.
- The revision log. `Assessment.plans_issued_at` is set when the plans PDF is first generated and is revision 0, "first
  issue"; a later download keeps the date. `Assessment.revisions` is append-only: "Issue a revision" on the Documents
  card (`POST /api/assessments/{id}/revisions`) appends the next number with a required note and the signed-in
  person's name, and is refused before the first issue. "Reopen design" leaves both: the log is a record, not a status.
  The title block prints "Rev. {n}: {note} — {date}" for the latest entry beside the calculation stamp; the cover
  carries the sheet index (every sheet's number and name) and the revision table (the first issue and the last five
  entries). An older database gets the two columns at start-up; an older record prints "Rev. 0" as before. The review's
  finding 14: `Assessment.plans_issued_by` records the signed-in person who first built the set, revision 0's "By" on the
  cover's table (a blank line with its reason when none was recorded: an older record, or a set built outside the API).
- The circuits contract (brief 2.1). `pricing.choices.circuits`, written at the end of `generate_boq` from the figures
  it already computed (`design_checks.circuits_block`): seven records on every job in a fixed order, so the balloon
  numbers on the single-line diagram, the schedule and the design analysis never move: C1 the PV string (each), C2 the
  strings joined on one MPPT input, C3 the battery, C4 the inverter output, C5 the grid feed, C6 the maintenance bypass,
  C7 the equipment grounding; `applies` says whether the job has the circuit (no battery on net metering; no combined
  circuit when no two strings share an input). Each record: `conductors` (the count, the current-carrying count, the
  size, the type: PV wire, THHN, battery cable; the insulation rating None until the item field exists), `run_m`,
  `voltage_v`, `i_continuous_a`, `i_design_a` (× 1.25; the PV row 1.25 × 1.25 × Isc when Isc is on file, else 1.25 ×
  the rule's current and the note says so), `ocpd_a` and `ocpd_code`, `placement` (the rule's: the string runs in free
  air under the array, the AC circuits in the BOM's conduit indoors, the battery cables free; a surveyed run replaces
  it later) with `conduit_code`, `ampacity_rule_a` and `ampacity_rule_column` (the wiring rules' table figure the BOQ
  sized the conductor on: the THHN 60 °C column, the PV and battery cable tables), `drop_pct` (the BOQ's), the EGC
  provided (the grounding run on the THHN line; the array bonding item's size read from its name), and `checks` with
  the BOQ's own coordination restated (`design_le_ocpd`, `ampacity_ge_ocpd`). The derated figures the design analysis
  will compute (`ambient_c`, `rooftop_adder_c`, `t_conductor_c`, `ampacity_base_a`, `ampacity_terminal_a`, `f_temp`,
  `f_fill`, `ampacity_derated_a`, `fill_pct`, `fill_limit_pct`, `egc_required_mm2`, `conduit_inner_diameter_mm` and
  the five derated checks) are None with the reason in `notes`; `status` is "not checked" until then, or "fail" where
  the BOQ's coordination already fails; no row reads "pass" on step 1. The runs the lines were priced on join
  `choices` (`pv_run_m`, `ac_run_m`, `grounding_run_m`, `conduit_m`). Nothing on a sheet reads the block yet; the BOM,
  the totals and the website estimate are unchanged.
- The survey fields (brief 1.3, 3.2, 4.2), one schema change. `AssessmentDoc.service` (the Service entrance card on
  the Site step): the DU, the account and meter numbers, the existing panelboard in words, the phase (1 or 3), the
  service voltage, the main breaker and the busbar rating, the point of interconnection (a backfeed breaker on the load
  side, a supply-side tap, the line side of the main) with its note, the DU's available fault current (2.3) and the
  panelboard's existing circuits as the office types them (5.3). `RoofFace.construction` and `AssessmentDoc.roof_default`
  (a fold under each face and under the Roof faces card): the roof type (rib-type or corrugated metal, clay or
  concrete tile, concrete deck, other), the sheet profile, the purlin material, section, thickness and spacing, the
  rafter spacing, the mean roof height, the condition note and flag; a blank field on a face reads the project's
  default. `AssessmentDoc.site` (the Site plan card): the lot and house outlines and the inverter, battery, point of
  interconnection and meter points as typed coordinates with their locations in words, and per face `plan_offset_m`,
  the eave midpoint's offset from the pin in metres east and north; the map's draw tools are a later step. Every field
  is optional and blank until surveyed; no field has a default (the wiring rules' 230 V prints as a labelled assumption
  on the sheets that read it, not as a stored value); the words are enumerations and a point is a pair in degrees (a
  422 otherwise); a survey edit is an input and makes the results stale. Nothing on a sheet reads the fields yet.
- Not in step 1, by the brief's order: the 120 % busbar rule and the `poi_busbar` warning (item 1, with the
  single-line diagram that prints it), the derating engine and its settings (item 2), the wind fields and settings
  (item 3), the vicinity map and the drawn outlines (item 4).

## The vicinity map and the site plan

Round 13, item 4 (`docs/audits/round-13/engineer-brief.md`, section 4), 10 October 2026: the sheet after the cover of the
plans for the PEE, "Vicinity map and site plan" (`docs/audits/round-13/site.md` has what was built and every departure).

- The vicinity map is composed on the server from OpenStreetMap tiles under the tile usage policy (`reports/vicinity.py`):
  two 3 × 3 mosaics per project (zoom 16, about 1.8 km across, and a zoom-12 inset of about 28 km), eighteen tiles fetched
  one at a time under a process-wide lock, each with an 8 s timeout and one retry, a 429 stopping the run at once and the
  first tile that fails after its retry abandoning the whole run (no partial map; a dead host costs two timeouts, never
  minutes); a User-Agent `PLDSolarApp/<round> (+website; e-mail)` that names the app and the company's contact (the
  website from the settings, the e-mail from Settings › Company), and no request at all when neither is known: the fetch
  is refused with that reason rather than sent anonymously. Every tile is cached under `data/tiles/{z}/{x}/{y}.png` for 30
  days; the composed mosaics live under `data/projects/{id}/` with the pin they were made for (five decimals) and go with
  the record on delete. Pillow draws the pin as the brand's marker, a north arrow (tiles are north-up), a scale bar (200 m
  on the main map, 5 km on the inset) and the attribution strip "Map data © OpenStreetMap contributors, ODbL — host,
  fetched date, zoom". The tile address and the attribution line are settings (`SOLARAPP_MAP_TILES_URL` with `{z}/{x}/{y}`,
  `SOLARAPP_MAP_TILES_ATTRIBUTION`), so another provider replaces the tile server without a code change; a blank address
  switches the fetch off.
- The fetch never runs inside the request that builds the PDF. "Prepare the map" on the Site plan card
  (`POST /api/assessments/{id}/vicinity-map/fetch`) composes it and keeps the result on the record (`Assessment.vicinity_map`);
  pressing it again fetches nothing while the mosaics on record were made for the saved pin, "Refresh map" (`force`)
  remakes them from the cache, and a moved pin remakes them. The page presses it once on its own before the first plans
  download of a record that has never tried, with "Preparing the map…" in the bar, so the brief's "runs when the plans are
  first generated" holds without the PDF request waiting on the network. A failure (no outside access, a timeout, a 429)
  is kept with its reason; the sheet prints the pin, the address, the nearest town and "vicinity map: not fetched
  (reason); the office may upload a screen grab", and the Documents card says the same under the plans row.
- The upload is the override and the fallback: a PNG or JPEG of at most 8 MB (`POST /api/assessments/{id}/vicinity-map`,
  multipart with a `note` for the attribution the office types), decoded and re-encoded by Pillow with the EXIF orientation
  applied and every chunk dropped, the longer side capped at 2,400 px, stored as `vicinity-upload.png` in the project's
  folder. When present it prints instead of the fetched map, captioned "uploaded by the office on {date}; {note}";
  `DELETE` removes it and the fetched map prints again. `GET /api/assessments/{id}/vicinity-map.png` serves whichever
  prints, for the card's preview.
- The site plan (`reports/plans_site.py`) is drawn with ReportLab primitives at a standard scale (the largest of the
  layout sheets' list that fits a 190 × 226 mm box with its dimension margins), true north up, metres east and north of
  the pin: each face's plan outline with the slope foreshortened by cos(tilt), rotated so the eave's outward normal
  points to the azimuth (a south face's eave at the bottom, an east face's at the right, the ridge to the west), the used
  panels inside, the face named with its panel count, the eave as a black dimension and the plan depth as a grey one; the
  eave midpoint at `plan_offset_m` when typed, else the face laid side by side in a strip below the site with 1 m gaps and
  the note "relative positions not surveyed; faces shown in true orientation only"; the lot (dash-dot, its edge lengths)
  and the house (solid, its overall width and depth) from the typed corners by the brief's equirectangular projection;
  when both exist, the setback from each house wall's midpoint straight out to the property line as a dimension, with
  "verify the zoning setback"; the inverter (a square), the battery (plates), the POI (a filled circle) and the meter (an
  M in a circle) at their points, each with the typed location in the legend; the pin as a small cross; a 0–1–5 m scale
  bar and the north arrow. A missing input prints its reason: "property line: not surveyed", "house outline: not
  surveyed", "setbacks: not computed (the lot and the house outline are both needed)", "… location: not chosen (Site
  step)". The sheet's scale is stated in the title block.
- Nothing invented: no map is drawn that was not fetched or uploaded, no outline or position that was not typed; the
  Leaflet draw tools for the outlines stay a later step (the corners are typed on the Site plan card).
## The design analysis sheet

Round 13, 10 October 2026, item 2 of `docs/audits/round-13/engineer-brief.md` (section 2), built on step 1's circuits
contract; `docs/audits/round-13/analysis.md` has what was built, the tables with their citations, every departure and
the test count. The coordinator's three decisions govern it: the severities of 2.4 as the brief recommends; nothing
invented (every NEC or PEC table value the brief marks "verify" is a settings table with its citation and a verify flag,
printed with the flag; a check that needs a figure not on file reads "not checked" with the reason; the labelled
assumptions print as assumptions); the DU's fault level from the service block the office types.

- Where it runs. `pricing/design_analysis.analyse_design`, called by `job.price_assessment` right after `generate_boq`,
  derates the seven `pricing.choices.circuits` records in place and writes `pricing.choices.design_analysis` (the
  ambient and its source, the assumptions, the tables used with their sources and flags, the short-circuit note, the
  GEC line, the rows not checked, the blocking codes). It runs on a project only: the website estimate has no plan set
  and its BOQ is as generated, so `core/quick.py` is untouched and its pins hold. The BOM's lines and totals do not move.
- The computation (brief 2.3). The ambient: outdoors (the string runs, a rooftop raceway) the higher of the setting
  (35 °C, an assumption) and the project cell's typical-year air maximum ceiled, said which; indoors the setting (30 °C,
  an assumption). The rooftop adder for a raceway on the roof from the band table at the settings' raceway height (25 mm,
  an assumption: a conduit on the rails); the string home runs stay in free air under the array by the rule's placement,
  so no row takes the adder today. F_temp = sqrt((T_insul − T_cond) / (T_insul − 30)), the formula the NEC permits in place
  of its table (the table's figures sit in the test, within 0.01 of the formula at each band's top). F_fill from the
  bundling bands by current-carrying conductors (the neutral counts, the EGC does not), applied on every row (1–3
  conductors give 1.00). The base ampacity: THHN from the column of the item's insulation rating (60, 75 or 90 °C
  tables; blank reads as the settings' 90 °C, said as an assumption); PV wire and battery cable from the maker's
  ampacity typed on the item, else the wiring rules' cable table as the base at 90 °C with "the cable's rating: verify".
  The breaker against the derated figure, else the next standard size above it (the DC list for the strings, the AC list
  for the AC circuits; no list for the battery breaker, which is picked from the catalogue's ratings, so the rule is not
  applied there) when the rating is at or below 800 A and the conductor still carries the continuous current: "next size
  up", still a pass. The terminal rule: the THHN 75 °C column, uncorrected, against the design current and the breaker;
  the app holds no 75 °C column for the PV and battery cables, so their rows carry "verify the terminal rating" as a
  qualifier rather than a check. The conduit fill from the new item fields `overall_area_mm2` (the wire) and
  `inner_diameter_mm` (the raceway): each AC circuit's line, neutral and the grounding run in its own raceway by the
  rule's placement, against 53 / 31 / 40 %; either field blank → "not checked" with the item named. The EGC per circuit by
  the breaker rating (the smallest table rating at or above it) against the provided conductor (the grounding run on the
  THHN line for the AC circuits, the array bonding item for the strings); the battery has no rack-EGC role, so its row
  is "not checked" naming the missing role (the review's finding 12 overruled the "verify" first built: a blank "provided"
  is a missing provision on the bill, not a table the app lacks); C7 carries the largest EGC the AC circuits need against
  the grounding run's gauge. The GEC line: the
  grounding run's gauge to the rod against the rod maximum (14 mm²).
- The short-circuit note. The utility's fault current from `service.fault_level_ka` ("BLANK kA (from {DU}; verify)" when
  blank); the inverter's contribution from the new item field `fault_current_a`, else the labelled assumption 1.5 × the
  rated output current for one cycle; the battery's from its `fault_current_a`, else "the BMS's short-circuit trip; verify
  with the maker"; the breakers' interrupting ratings from `aic_ka` on the protective devices, compared with the DU's
  figure when both are typed, "BLANK — the AIC is not on the breaker items; verify" until then.
- The status of a row. "fail" when a check fails (the breaker check passes by the next size up); "not checked" when a
  figure the office can type is missing (the conductor's area, the conduit's inside diameter, the panel's Isc for the
  string breaker), with the reason naming the item; else "pass", qualified by every assumption used and every table still
  to verify ("pass (ambient assumed 30 °C; THHN columns: verify; EGC table: verify)"), so a pass never stands on an
  assumption alone. A table the app does not hold at all (the cable's 75 °C column) is a "verify" qualifier, not a "not
  checked": the brief's hand-worked PV row passes; a BOM role the bill lacks (the battery rack's EGC) is "not checked"
  since the review (finding 12). The PV string row's continuous current is the PV article's 1.25 × Isc, the figure the
  schedule sheet prints as the circuit current, and the design current 1.25 × that (the review's finding 2: with Imp as
  the continuous current the "× 1.25" head was false for the row and the next-size-up test compared the derated ampacity
  with Imp); a breaker whose typed interrupting rating is below the DU's typed fault level raises `aic_below_fault`,
  hard and blocking (finding 1).
- The warnings and their severity (2.4, the coordinator's decision a): `conductor_derated`, `terminal_ampacity` and
  `aic_below_fault` (the review's finding 1: a breaker whose typed interrupting rating is below the DU's typed fault level
  cannot clear the fault at the service) are hard and block the customer documents like the round-3 AC coordination (the
  breaker does not protect the conductor at temperature; the terminals are rated below the load); `conduit_fill` and `egc_undersized` are hard and print without
  blocking (the fix is a larger conduit or a role change, pesos); `derating_not_checked` (one per job, naming the rows
  and the figures to type) and `fault_level_unknown` (until the DU's figure and the AIC are typed) are ordinary.
- The settings (Pricing settings › Design analysis, and the two THHN columns under Wiring rules), every value a cited
  stand-in from the NEC edition the PEC follows: `wiring.thhn_ampacity_75c` and `_90c` (NEC 2014 Table 310.15(B)(16)
  copper on the 60 °C table's size mapping; PEC 2017 Table 3.10.1.16), `derating.rooftop_adder_c` (Table 310.15(B)(3)(c)
  by height; the 2017 edition keeps only +33 °C under 22 mm, and 6.3 asks the PEE which the PEC adopted: a single band
  "0: 33" is the 2017-style adder), the temperature-correction formula's citation (310.15(B)(2)), `bundling_factor_pct`
  (310.15(B)(3)(a)), `conduit_fill_limit_pct` (Chapter 9 Table 1; PEC Chapter 10), `next_size_up_max_a` (240.4(B); PEC
  2.40), `terminal_rating_c` (110.14(C)), `grounding.egc_by_ocpd` (250.122 on the PEC's metric series; PEC Table
  2.50.1.122), `grounding.gec_rod_max_mm2` (250.66(A); PEC 2.50). Each carries a `_source` line and a `_verified` flag,
  off by default; the sheet prints the source with "VERIFY" until the owner or the PEE ticks it, then "confirmed in
  Settings". The assumptions beside them: the two ambients, the raceway height, the 90 °C default insulation, the 1.5 ×
  inverter fault factor. Every value is in `settings_version`, so a change flags the quoted jobs.
- The item fields (the Materials page, beside the electrical ones; kept on a materials re-import; added to an older
  database at start-up): `overall_area_mm2`, `insulation_c` and `ampacity_a` on the wires, `inner_diameter_mm` on the
  raceways, `fault_current_a` on inverters and batteries, `aic_ka` on the protective devices. All optional; a blank
  prints "not checked" with the reason or the labelled assumption, never a silent default.
- The sheet (`reports/plans_analysis.py`, one hook in `plans_pdf.py` after the schedule sheets and before the last
  sheet): one table, a row per circuit, the columns of 2.2 (the conductors with their insulation and item, the run, the
  currents, the base ampacity and its column, the ambient with the adder and the placement, the two factors, the derated
  and terminal figures, the breaker, the breaker check with the next-size-up answer, the drop, the conduit with its
  inside diameter, the fill against its limit, the EGC required and provided, Pass); under it the short-circuit note and
  the GEC, the tables used with their sources, values and flags, the assumptions, and how to read Pass. A figure the app
  does not hold is a blank line with its reason. The schedule's four "to be completed" placeholders for derating,
  conduit fill, the EGC and the GEC now point to the sheet; the cover's note 6 likewise; the last sheet keeps a
  "Design analysis: rows not checked" entry naming the figures to type and drops it when every row is checked.
## The mounting detail and the uplift check

Round 13, item 3 (`docs/audits/round-13/engineer-brief.md`, section 3; what was built and every departure in
`docs/audits/round-13/mounting.md`): the mounting detail sheet of the plan set, the roof construction it reads and the
NSCP 2015 uplift check behind the BOM's L-foot count.

- The app ships no wind-code figure and no fastener figure: no zone, no basic wind speed, no exposure constant, no
  directionality factor, no pressure coefficient, no pull-out figure. The signing engineer types the basic wind speed by
  province (Settings › Mounting and wind, a table of every province of the town list from `core/wind_zones.json`, which
  ships with every figure blank and NSCP 2015 Figure 207A.5-1A named as the source), the exposure constants alpha and zg
  per category, Kd, and per project (Roof faces › Wind for the uplift check) the zone and speed when they differ from
  the province's row, the exposure category, Kzt and the GCp per roof zone; the office types the screw's allowable
  withdrawal from the maker's sheet (in Settings, or per roof on the roof construction) and the rail maker's maximum
  foot span. Each figure is stored with its source line and printed beside it. Until typed, the check reads "not
  checked" naming what is missing, the sheet prints the chain with a blank line and the reason at every stopped step,
  and the BOM keeps the rule's L-feet with a note. The only defaults are labelled assumptions: exposure B when blank (a
  town site), Kzt 1.0 (no hill or ridge), two screws per L-foot (the set's screw, pad and bolt), the rails at the
  quarter points, the worst typed zone's GCp for every panel, the BOQ rule's spacing as the span cap until the maker's
  maximum is typed, a missing panel weight or rail weight left out of the dead load (the conservative side); a pass
  reached on one prints "PASS (on assumptions)".
- The chain (`pricing/uplift.py`, pricing.choices.uplift) follows the brief's: Kz = 2.01 × (max(h, 4.6 m) / zg)^(2/alpha),
  qh = 0.613 Kz Kzt Kd V², p_up = qh |GCp| (the array above the roof surface: no internal pressure on it), 0.6D + 0.6W,
  each rail line carrying half the panel's dimension across the rails, the feet on purlins at a multiple of the purlin
  spacing at or under the span cap, a screw's share against the typed withdrawal, and s_allow giving the closest
  spacing that holds. The verdict is on the design the BOM carries: PASS when a foot spacing on the purlins holds, the
  L-foot count then following the feet per rail line (closer feet when the maker's maximum span does not hold, as the
  brief's 0.5 kN case closes to every purlin); FAIL when even a foot on every purlin does not hold (`uplift_fail`, hard,
  printed in red on the sheet, never blocking: the fix is more screws per foot or a stronger fastener, the engineer's;
  the BOM keeps the rule's count); NOT CHECKED otherwise (`uplift_not_checked`, ordinary). A roof condition other than
  sound raises `roof_condition` (hard, not blocking); a tile roof, a concrete deck or "other" raises
  `roof_type_out_of_scope` (ordinary). The chain runs in two steps since the review (finding 9): the pressure chain to
  T_panel for every roof type once V, h, the exposure constants, Kd and GCp are on file (the loads the signing engineer
  needs for any mounting), the fastener step only on a roof with a drawn detail and the purlin spacing and pull-out typed;
  a tile roof stops at the fastener step ("the tile hook's allowable withdrawal: not on file (Detail C waits on the
  owner's word)"), and `stop` carries the reason, printed in the first blank cell of the sheet's chain. In the FAIL state
  the details print "S = ______ (FAIL: the signing engineer's; the BOM carries the rule's 1.2 m)" and the plan key says
  the feet are drawn at the rule's spacing, the count the BOM carries (finding 6). Each face is evaluated on its own construction
  (a blank field reading the project's default) for the rows it holds; the website estimate never reaches the check.
- The sheet (`reports/plans_mounting.py`, one hook in `plans_pdf.py` after the array layouts): Detail A, rib-type metal
  sheet on steel C-purlins, and Detail B, corrugated sheet on purlins, both at 1:5 as sections along the rail at an L-foot
  with the purlin under the foot shown cut and hatched, the screw through the crest with its EPDM washer and the sealant
  bead, the rail on the foot's leg with its bolt, the mid and end clamps on the panel frames, the bonding lug and its
  conductor, callouts numbered to the BOM roles and the typed purlin and sheet, the foot spacing S from the check and the
  clearance C as a blank line (the L-foot height is not on the item); a plan key of a 2 × 3 patch with the rail lines,
  the purlin lines dashed, the feet at the check's spacing, the splices and the clamps; the chain per face as a table
  with every figure beside its source or assumption, the verdict, the L-feet on the BOM against the rule's, and the
  assumptions. The drawings carry typical proportions; the roof's own sizes are the typed figures in the callouts and
  the sheet says so. The tile detail prints as a line that waits on the owner's word on the bracket and the screw; a
  roof type out of scope prints "not drawn". The last sheet lists the uplift inputs still blank, the tile detail and
  any out-of-scope face, and drops them when none applies.
## The single-line diagram

Round 13, item 1 (`docs/audits/round-13/engineer-brief.md`, section 1; what was built and every departure in
`docs/audits/round-13/sld-and-loads.md`): one sheet after the array layouts, its own module (`reports/plans_sld.py`)
called from the plan set through one hook that returns the sheet's name and its flowables.

- One horizontal bus from the array to the meter, drawn with ReportLab primitives in the set's frame at the brief's
  line weights, every device carrying the balloon of its circuit row (C1 to C7, drawn only where the circuit applies):
  the strings (one chain per distinct length, the rest "alike, one drawn") with the panel count and the datasheet's
  Voc, Voc at T_cold, Vmp, Isc and Imp; the home-run pair with its gauge and run, the connector pairs, the array
  bonding dashed; the DC box with a 2P breaker per string, an SPD per MPPT input in use, the fan to the inputs by the
  BOQ's round-robin ("combiner" and the fuse note when strings join, a spare input marked); the inverter with its
  ratings, inputs, grid flag, certificate and battery port; the battery bank below it with its breaker and lug pairs;
  the inverter-output breaker, the transfer switch (or "built in"), the AC SPD on the board, the existing panelboard
  (bus, backfeed breaker, main), the lockable AC disconnect, the point of interconnection, the kWh meter (two arrows
  on net metering, one and "nothing exported" off grid), the service drop and the DU with its fault level; the grid
  feed and the maintenance bypass on a line above the bus; the EGC bus, the electrode and the bonds below. A legend
  names every symbol (IEC 60617-style simple shapes) and says to verify the set against the DU's sample; a placards
  table fills the DU's labels from the figures with "verify the DU's wording" on each.
- Nothing invented: a figure not on file prints as a blank line with its reason (not on the item, not surveyed, from
  the DU), a role without an item says so, a string without the datasheets carries "(rule)", the DC-grounding line is a
  labelled assumption, the title block reads "Not to scale". The point of interconnection sits on the panelboard's bus
  bar for a load-side breaker (and when not chosen), at the service for a supply-side tap or the line side.
- The 120 % rule (`pricing/service_checks.py`): for a load-side breaker with both ratings surveyed, the grid-side
  breaker × units plus the main breaker at or below 1.2 × the busbar (NEC 705.12(B)(2)(3)(b); the PEC 2017 equivalent
  printed with "verify"). The job pricing writes `choices.poi_busbar` with the whole inequality and raises
  `poi_busbar` on a failure, hard and never blocking: the fix (a supply-side tap or a larger panel) is the PEE's call,
  and the sheets print PASS or FAIL with the arithmetic, or the reason the rule is not checked. The sheets recompute
  it from the service block when the stored results predate it, so the warning and the sheet always agree.
- Tags inside symbols are 6 pt (below the brief's 7 pt floor) so they fit the symbol; "≤" is not used (no glyph in
  Montserrat), the limit is printed as a line of its own. The last sheet lists the diagram's blank lines under its sheet
  number with the rest of the set's (the review's finding 5, below). The review's smaller findings on the diagram: the
  electrode caption sits to the right of the C7 balloon, clear of the EGC bus line and the electrode, and the service
  block is wide enough for "fault level at the service 10.0 kA" on one line (finding 3); a grid-interactive inverter's
  balloon leads with the role and the datasheet's type word follows ("6 kW grid-interactive (hybrid), 1Ø; the datasheet's
  type: off-grid", finding 7); the panelboard's tag reads "C5 backfeed brk; C6 bypass feed" since C6 is a load-side feed
  (finding 11); on a no-export job the 120 % block adds "(applied although nothing is exported: conservative; the DU's
  view: verify)" (finding 10).

## The schedule of loads in the permit's format

Round 13, item 5 (brief section 5; `docs/audits/round-13/sld-and-loads.md`): its own sheet before the last one
(`reports/plans_loads.py`, one hook like the diagram's), replacing the audit's table on the last sheet.

- The format a sealed plan carries per panelboard, flagged to verify against the LGU's sample: the header line
  (panelboard, voltage, phase and wires, main breaker AT / AF, bus, fed from) and the columns Circuit No. |
  Description of load (count × type) | Load (W) | Load (VA) | Volts | Amperes | Wire (mm² THHN) | Conduit (mm) | OCPD
  (AT/AF, poles) | Remarks. The existing circuits typed on the Site step print first and verbatim; the audit's
  appliances follow under three headings, Lighting, Convenience outlets and Equipment, each with its power factor
  labelled "assumption", every line W, VA = W / PF and A = VA / V with the circuit number, wire, conduit and OCPD as
  blank lines (the engineer's, from the existing panelboard); subtotals, the connected existing load, the planned
  loads apart and outside the total, the demand load blank (the PEC 2.20 factors are the engineer's) beside the
  hourly profile's coincident peak as the audit's own figure, the main breaker's adequacy the engineer's. Under the
  table the PV system as a source (the array, the inverter's current, the backfeed and output breakers, the wire,
  the conduit item, the storage) and the point of interconnection (the choice in words, the main and busbar, the
  120 % line, the meter, the DU and account). A footnote names what the engineer fills by hand.
- `PricingConfig.loads`: the power factors by group (1.00, 1.00, 0.85, assumptions) and the audit categories tabled
  as equipment, under Settings › Pricing › System design; outside the pricing fingerprint, since the sheet reads
  them live and they move no price. The volts are the surveyed service voltage, else the wiring rules' 230 V
  labelled an assumption; a missing power factor leaves VA and A blank.
- The last sheet is "Not yet in this set" and lists the schedule's blank lines under its sheet number, the signing
  engineer's own (the frame rating, fed from, the demand load, the branch-circuit figures) under their own heading (the
  review's finding 5, below); the cover's general notes split six and two so the bottom block, one table that cannot
  split, stays on the cover with the longer sheet index (about 20 mm of slack for the sheets still to come).

## Round 13 review: the fixes

The solar engineer's review of the ten-sheet set (`docs/audits/round-13/engineer-review.md`: merge with the fixes listed)
and what was done about each finding (`docs/audits/round-13/fixes.md`). The two that would have passed an inspection
failure through: a breaker whose typed interrupting rating is below the typed fault level now raises `aic_below_fault`,
hard and blocking, through the existing mechanism; the PV string row's continuous current is the PV article's 1.25 × Isc
when the datasheet is on file, so the schedule sheet, the "× 1.25" head and the next-size-up test agree. The rest: the
diagram's two collisions and three labels, the site plan's label placement and depth dimension, the FAIL state's callout,
the tile roof's pressure chain, the battery rack's EGC as a missing role, the dead load's label, cover note 6 naming its
column, and revision 0's "By".

- One collector for the set's blank lines (finding 5). `reports/plans_blanks.py`: `Blanks`, which every sheet module
  appends to whenever it prints a blank line with its reason (`blanks.add(sheet, item, reason)` returns BLANK and stands
  where BLANK stood; `n` for a figure printed in several cells; `engineer=True` for a line the set leaves to the signing
  engineer by design). The last sheet prints "Blank lines in this set, by sheet" (one row per sheet and reason, with the
  figures and the count of lines) beside "what the set still lacks" and "the signing engineer's lines", and shrinks the
  block to the frame as the cover's index does, so the seed state's 283 blank lines still make one last sheet. The
  design analysis prints the engine's "BLANK" words as the set's blank line and records them (the DU's fault level, each
  breaker's AIC, the battery's short-circuit trip). The test: in the reviewer's typed state the blank lines pdftotext
  counts per sheet, less the title block's signature line, equal the lines the last sheet lists for that sheet.
- The site plan (finding 4): a face's depth dimension sits one gap further out than the eave's; every dimension figure's
  box is collected and the face labels go through the same placement loop as the point labels (the centroid, the four
  offsets, the strip along the bottom with a leader), keeping clear of the symbols, the figures and the labels before.
- The mounting sheet keeps its two columns side by side when they overrun the frame by a little (the longer dead-load
  label, a second face's column), shrinking them as the cover's index does, and stacks them only when they overrun by
  more; the set keeps its sheet count in every state the review built.
- The reviewer's typed state typed the 40 A breaker's AIC at 6 kA against the DU's 10 kA; with finding 1 that state
  holds the set (409), which is the point. The rebuilt states type 10 kA, and a ninth state keeps the 6 kA to show the
  refusal.
