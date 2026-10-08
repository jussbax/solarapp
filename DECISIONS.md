# Solar simulator: design decisions

Agreed with the owner before the build started. Keep this file current when a
decision changes; the code follows it.

## Purpose

Estimate what a roof in the Philippines can produce, combining the company's
on-site readings (UNI-T UT381PV irradiance meter and UT673PV+ MPPT meter on a
50 W test panel) with PVGIS typical-year weather data. Roof-level production
only at this stage: no inverter, wiring, financial or sizing modules yet.

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
  requirement needs, with a per-job override; when no default is set the
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
- Shown to the visitor: panels, kWp and roof area, inverter, battery, the
  installed price rounded up to the thousand with the four customer
  sections, production and coverage, bill before and after, payback, net
  over the period, CO2, and the assumptions in plain words. Nothing
  internal.
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
  the secret kept in `data/twofactor.json` (0600), never in `.env`.
  Cloudflare Access stays as an optional outer layer.
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
  crackable fingerprint of the password. The nonce lives in
  `data/session.key`; "Sign out everywhere" rotates it and ends every
  session at once (logout stays per device).
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
chart, and the engineering build order in the plan.

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
  twelve months and never touches a project. The nav is Projects, Leads,
  Materials, Settings; the estimate page link and the website-only
  profile fields sit under a Website heading in Settings; the phone top
  bar is one row with a menu.
- A future CRM module takes the Leads page over through the same API; a
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
