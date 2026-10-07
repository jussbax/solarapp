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
- The instantaneous coincident peak for the inverter uses nameplate watts at
  minute resolution, without duty factors.
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
  typical day; usable capacity = the largest daily surplus-to-night shift
  over the twelve months, and for off-grid at least the autonomy days
  (default 1) times the largest daily consumption. Rounded up to whole
  modules (default 5.12 kWh, 90 percent depth of discharge, 92 percent
  round-trip, 0.5C), capped at a configurable number of modules.
- Inverter: smallest catalogue size (6, 8, 10, 12 kW by default) that covers
  the nameplate coincident peak, the start of the largest motor load at the
  200 percent surge rating, and the PV array at 1.3 kWp per kW. Parallel
  units when the largest size is not enough.
- Outputs: recommended PV, inverter, battery, coverage of consumption,
  self-consumption, annual import and export, typical-day chart per month,
  month-by-month balance. Internal only for now; the customer PDF is
  unchanged until the pricing module exists.
