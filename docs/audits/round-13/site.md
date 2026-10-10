# Round 13, item 4: the vicinity map and the site plan

Built 10 October 2026 from `engineer-brief.md`, section 4 (4.1 the vicinity map from map tiles, 4.2 the site plan, 4.3 the
tests), on the step-1 fields (`docs/audits/round-13/step1.md`: the face offsets, the lot and house outlines as typed corners,
the inverter, battery, point-of-interconnection and meter points). One new sheet after the cover, "Vicinity map and site
plan"; the set goes from five sheets to six on the Pila sample. The suite went from 272 to **289 tests**; `npm run build`
passes and `npm run lint` stays at its seven baseline warnings. The sandbox's proxy refuses the tile host (CONNECT 403),
so the one real fetch could not be tried; every build here ran on the fixture tiles.

## 1. What was built

- **`reports/vicinity.py`** (the tile fetch and the composition). The tile maths of 4.1 (`tile_xy`, `pin_pixel`,
  `metres_per_pixel`); `TileSource` (the cache under `{data_dir}/tiles/{z}/{x}/{y}.png`, reused within 30 days by the file's
  time, else one request with the policy's headers, an 8 s timeout and one retry; a 429 raises at once, a 4xx is not
  retried, the answer must decode as a 256 px image); `compose_mosaic` (Pillow: nine tiles into a 768 px PNG, the pin as
  the brand's marker, a straight north arrow top right, the scale bar bottom left, the attribution strip along the
  bottom); `fetch_mosaics` (zoom 16 then zoom 12, 3 × 3 each, written to `{data_dir}/projects/{id}/vicinity-z16.png` and
  `-z12.png` only when every tile came, with a `vicinity.json` beside them); `prepare` (the record's block after a fetch,
  reused while the mosaics on record were made for this pin rounded to five decimals, `force` to remake; a failure
  stores `error.reason` and drops the old mosaics; serialised on a process-wide lock); `store_upload` and `remove_upload`;
  `current_file` (the upload, else the main mosaic); `remove_project_files`; `user_agent`; `make_client` (the seam the
  tests replace with an httpx MockTransport).
- **The fetch policy as implemented.** User-Agent `PLDSolarApp/13 (+{website}; {email})` (the round is the app's version,
  `solarapp.APP_VERSION`; the website from `SOLARAPP_WEBSITE_URL` or the first public origin, the e-mail from Settings ›
  Company); with neither known the fetch is refused with the reason "no contact for the tile server's User-Agent" rather
  than sent anonymously. Eighteen tiles per project, one request at a time (`FETCH_LOCK`; the route answers 409 while a
  fetch is running), no prefetching, the cache, the first tile that fails after its retry abandons the whole run (a dead
  host costs two timeouts, never minutes), the attribution burned into every mosaic and printed in the sheet's caption.
  The tile address and the attribution line are settings (`map_tiles_url`, `map_tiles_attribution`;
  `SOLARAPP_MAP_TILES_URL`, `SOLARAPP_MAP_TILES_ATTRIBUTION` in `.env.example`); a blank address switches the fetch off.
  The client is a plain `httpx.Client()`, so the environment's proxy settings apply as to every outbound call.
- **The on-demand or prepare decision: "Prepare the map", never inside the PDF build.** `POST /api/assessments/{id}/
  vicinity-map/fetch` (`force` to refresh) is the office's button on the Site plan card; the plans route passes whatever
  is on record to the builder and never fetches. The page presses the button once on its own before the first plans
  download of a record that has never tried (no map, no upload, no failure on record; the pin saved), with "Preparing the
  map…" in the bar, so the brief's "the fetch runs when the plans are first generated or on the button" holds while the
  PDF request itself never waits on the tile server. A failure is kept with its reason; the office sees it in the bar,
  on the Site plan card's status line and under the plans row of the Documents card.
- **`Assessment.vicinity_map`** (a nullable JSON column, added to an older database at start-up by `db.ensure_columns`):
  `{source: "upload" | "osm" | null, upload: {file, uploaded_at, note, width, height} | null, osm: {files, fetched_at, pin,
  host, attribution, tiles_fetched, tiles_cached} | null, error: {reason, at} | null}`; `AssessmentOut.vicinity_map`
  carries it (`schemas.VicinityMap`). The upload wins when present.
- **The upload** (`POST /api/assessments/{id}/vicinity-map`, multipart `file` and `note`; `DELETE` removes it; any signed-in
  person): PNG or JPEG, 8 MB (the body cap in `main.py` for the route, 413 inside it too), decoded and re-encoded with
  Pillow (the EXIF orientation applied first, then a fresh image so no chunk survives; transparency over white), the
  longer side capped at 2,400 px, stored as `vicinity-upload.png`; 422 for a PDF or a GIF. `GET /api/assessments/{id}/
  vicinity-map.png` serves whichever prints (`which=upload|z16|z12` for one file), 404 when nothing is on record.
  `DELETE /api/assessments/{id}` removes `{data_dir}/projects/{id}/`.
- **`reports/plans_site.py`** (the sheet), called from `plans_pdf.build_plans_pdf` through `site_sheet(...) -> (name,
  flowables, scale)`; the builder inserts the name after the cover's in `sheet_names` and the flowables after the cover's
  story, and passes `vicinity` and `project_dir` (two new keyword arguments). The left half: the sheet's title, the
  address, the pin and the nearest town centre with its distance; the main mosaic at 140 mm with the inset at 64 mm and
  the caption (the attribution, the host, the date, the zooms and the widths across), or the upload fitted into 196 × 140
  mm with "vicinity map: uploaded by the office on {date}; {note}", or the failure line "vicinity map: not fetched
  ({reason}); the office may upload a screen grab (Site plan card › Vicinity map)" with the pin, the address and the
  town; then the site plan's legend (each point's typed location and coordinates) and the notes. The right half: the site
  plan drawing in a 190 × 226 mm box (`site_plan_drawing`): the largest standard scale that fits the extent with the
  dimension margins (16 mm at the sides, 10 above, 14 below), true north up, metres east and north of the pin; each face
  from `results.geometry` with the slope foreshortened by cos(tilt) and rotated by `face_axes(azimuth)` (the eave from its
  left end to its right along azimuth − 90, the ridge toward azimuth + 180), the used panels inside, the name and the
  panel count on a white pad, the eave as a black dimension and the plan depth as a grey one; faces with `plan_offset_m`
  at their eave midpoint, the others side by side in a strip below the site with 1 m gaps; the lot dash-dot with each
  edge's length, the house solid with its overall width (north side) and depth (west side); the setbacks from each house
  wall's midpoint straight out to the property line as thin dimensions; the four points as symbols with labels that
  step aside when they would overlap a symbol, the pin or another label; the pin as a cross; the north arrow; a 0–1–5 m
  scale bar and "scale 1:N"; the scale stated in the title block through `SheetMarker`.
- **The frontend.** `SitePlanCard` gains a "Vicinity map" section (`VicinityControls`): the status line (prepared on a
  date from a host, uploaded on a date, not fetched with the reason, not prepared yet), the preview of whichever prints,
  "Prepare the map" / "Refresh map", "Upload a screen grab" (PNG or JPEG) with the attribution note typed beside it,
  "Remove the upload"; the buttons are off with the reason while the record is unsaved, has unsaved edits or no pin (the
  map is composed around the saved pin). The Documents card prints the map's state under the plans row. `api.ts`:
  `prepareVicinityMap`, `uploadVicinityMap`, `removeVicinityUpload`, `vicinityMapUrl`; `types.ts`: `VicinityMap` on
  `AssessmentOut`.
- **The last sheet** no longer lists "Vicinity map and site plan" under "Not yet in this set": the sheet carries its own
  blanks with their reasons.

## 2. Tests (brief 4.3)

`test_vicinity.py` (13): the tile indices for the Pila pin at zoom 16 (54861, 30149) and zoom 12 (3428, 1884), the pin's
pixel, 2.315 m per pixel and the 86 px scale bar; the User-Agent's forms; the mosaics composed from the fixture tiles
under `tests/fixtures/tiles/` through a fake tile server (eighteen requests, the User-Agent on every one, both 768 px PNGs,
the marker's dot at the pin's pixel, the attribution strip and the arrow's box where they should be, the cache file by
z/x/y); a second build fetches nothing, "Refresh" remakes from the cache, a pin moved inside its tile remakes from the
cache, a pin moved by more than a tile fetches new tiles, a tile older than 30 days is fetched again; a 429 (one request),
a timeout and a dead host (two requests each) leave no file and record their reason; no contact or a blank address refuses
the fetch with no request; two threads leave at most one request in flight; through the API: "Prepare the map", the
preview, the sheet's attribution and source line, nothing fetched on the second press or on a build, the project's folder
removed on delete; the failure path printing the pin, the address, the town and the reason, "not prepared yet" before
any attempt, 409 without a pin; the upload (a 3,000 × 2,000 JPEG with EXIF to a 2,400 px PNG without it, the preview
serving it, the sheet's "uploaded by the office" with the note, the delete bringing the fetched map back, a transparent PNG
over white); 413 over 8 MB, 422 for a PDF and a GIF. `test_plans_site.py` (4): the projection's round trip and the face
axes; the sample's faces in true orientation (the south face's eave at the bottom, 4.76 m deep; the east hip face's eave at
the right, 3.86 m deep, the ridge to the west) and the sheet with nothing typed (the figures, the names, every "not
surveyed" and "not chosen", the cover's index naming sheet 2, the last sheet no longer listing it); the typed 15 × 12 m lot
printing its four edge lengths and 1:100 (1:75 would need 200 mm), the house's overall, the four setbacks (3.0, 3.5), the
points' legend, "verify the zoning setback"; the offsets placing a face's eave midpoint at the pin offset, and one loose
face named in the strip's note. `test_plans.py` and `test_survey_fields.py` count six sheets (four without faces).

## 3. Departures from the brief, with the reason

1. **"Prepare the map" rather than fetching inside the plans build** (4.1 says the fetch runs when the plans are first
   generated): the coordinator ruled the build must not wait on the network; the page presses the button before the first
   download instead, so the first set still carries the map when the server can reach the tiles.
2. **The upload control and the "Fetch map" button sit on the Site plan card, not the Documents card** (4.1 names the
   Documents card): the coordinator placed the control beside the site fields; the Documents card keeps the note and names
   the card. The sheet's failure line reads "(Site plan card › Vicinity map)" accordingly.
3. **No request without a contact**: 4.1 gives the User-Agent with both the website and the e-mail; with neither known the
   fetch is refused with the reason instead of sent anonymously, since the policy requires a contact.
4. **The whole run stops at the first failed tile** (4.1 gives the per-tile timeout and retry only): otherwise a dead host
   costs eighteen × two timeouts; and no partial mosaic is kept, so the sheet never prints a map with holes.
5. **The pin's pixel in the sample mosaic is (256 + 0.733 × 256, 256 + 0.801 × 256)**, not the brief's "(256 + 0.6 × 256)":
   the brief's figure was a round one; the test asserts the formula's fractional parts.
6. **The site plan's box is 190 × 226 mm**, not 230: the sheet's title row takes the 4 mm; the brief's own test figures
   (15 m at 1:100 fits, 1:75 would not) hold with the dimension margins.
7. **The eave's left end is at azimuth + 90** (the shade model's convention, `core/layout.shade_marker`), so the eave runs
   from azimuth + 90 to azimuth − 90 and the ridge lies at azimuth + 180: 4.2's "rotated so the eave's outward normal
   points to azimuth_deg" is kept; the brief leaves which end is left unsaid.
8. **Setbacks are measured from each house wall's midpoint straight out to the property line**, not "the perpendicular
   distance from each house edge to the nearest lot edge": the same figure on a rectangular lot, and well defined when a
   wall is not parallel to any lot edge. A wall whose outward ray meets no lot edge prints no setback.
9. **A record whose faces are partly placed** (some offsets, some not): the placed ones sit around the pin and the rest
   go in the strip below, named in the note; the brief covers only all-or-none.
10. **The retention run touches no project folder**: the run anonymises leads and trims the estimate log and never deletes
    a project, so 4.3's "the retention run … removes `{data_dir}/projects/{id}/`" has nothing to act on; the project
    delete removes the folder.
11. **The sheet's house dimensions sit on the north and west sides**, so the main roof's eave (usually south or east) and
    its dimension do not collide with them; the brief does not place them.
12. **The real fetch could not be tried**: the sandbox's proxy refuses tile.openstreetmap.org (CONNECT 403). The policy's
    current text was not re-read for the same reason; the build follows the brief's reading of it.

## Checks

The full suite (`289 passed`), `npm run build`, `npm run lint` (seven warnings, the baseline). The plans PDF of the Pila
sample with the fixture tiles under `scratchpad/plans13/site/`: `plans-placed.pdf` (the faces at offsets on a 20 × 14 m
lot with the house, the four points and the fetched map), `plans-strip.pdf` (no offsets: the faces side by side below the
lot), `plans-upload.pdf` (a 3,000 × 2,000 screen grab printing instead), `plans-failed.pdf` (a 429: the pin, the address,
the town and the reason), `plans-bare.pdf` (nothing typed, nothing tried), each with its `pdftotext` and `site-*-2.png`
from `pdftoppm`, looked at: the south face's eave at the bottom with "9.00 m", the east face's eave at the right with
"7.00 m", "4.76 m" and "3.86 m" as the plan depths, the lot's four "15.00 m"/"12.00 m" (or 20/14) edges, "house 9.00 m"
and "house 5.00 m", the setbacks, the labelled symbols, the scale bar, the north arrow, the map with its marker, arrow,
bar and attribution strip, and the inset beside the caption and legend.
