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
- BOQ rules: inverter = cheapest hybrid at or above the sized kW (3-phase
  and high-voltage units excluded), times the parallel units; battery =
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
  demobilization, PPE, plans and PEE seal, LGU permit and CFEI, ERC
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
- Not yet: close-out actuals, project dashboard, the simplified quick
  estimate.
