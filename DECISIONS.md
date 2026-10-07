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
- Panels are typed in per assessment (name, Wp, length, width); several
  candidates can be entered and the one with the most kWp is marked and
  selected by default. A shared catalogue comes later.

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
- Desk estimate mode (no readings yet) uses the average `k_site` of saved
  measured assessments, or 1.0 when none exist, and is labelled unmeasured.

## Product

- Web app, single Docker container on an Ubuntu office server behind a
  Cloudflare Tunnel. Python FastAPI backend with pvlib, SQLite storage,
  React frontend. One user for now, with saved assessments.
- Customer PDF contains only what the customer cares about. Readings, k,
  warnings and data details stay on the internal page.
- English only.
