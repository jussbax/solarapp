# Solar Roof Simulator

Estimates what a roof in the Philippines can produce, combining the company's
on-site readings (UNI-T UT381PV irradiance meter and UT673PV+ MPPT meter on a
50 W test panel) with PVGIS typical-year weather data. The weather data is
downloaded once; after that the server makes no outside calls.

The design decisions behind every formula are in [DECISIONS.md](DECISIONS.md).

## What it does

1. Drop a map pin on the roof. The nearest PVGIS grid cell is used.
2. Enter roof faces (rectangle, hip face or triangle: eave, ridge, slope,
   tilt, facing, panels left out) with any firewalls, trees or buildings
   that shade them. The panel is chosen in the background: every active
   panel in the materials list that carries a wattage, a length and a width
   is fitted, and the one with the most kWp on this roof is used (ties to
   the lower price per watt), unless the pricing settings name one panel
   for every job or the engineer picks another under System design. The
   app cuts the wall strips, fits panels row by row in both orientations,
   shades the simulation hour by hour, and shows the panel and count.
3. Enter the on-site readings: three simultaneous rows of irradiance, MPPT
   power and panel surface temperature per roof face. The app computes the
   owner's k per row, removes the heat and low-light effect present at the
   moment of measurement (PVGIS Huld module model) to get a site factor,
   and calibrates the thermal model from the probe temperature.
4. Simulates every hour of a typical year per face (Perez transposition,
   Martin-Ruiz reflection, Huld module model, site thermal rise) and reports
   monthly and annual kWh at the panels, the "measured versus PVGIS" percent,
   and the owner's original formula for continuity.
5. Produces a trimmed customer PDF and a phone-sized client card image for
   the first visit. Readings, k, warnings and dataset details stay on the
   internal page.
6. Energy audit: appliances with usage windows (start, end, weekdays,
   months), duty factors per type, reconciliation with the latest bill, and
   future additions. Sizing from the hour-by-hour balance of the reconciled
   load against this roof's production for net metering, net metering with
   a battery, or the company's "off-grid" (no export: the panels and the
   battery carry the house and the grid steps in only when both fall
   short): PV capped by the roof, the battery balanced over the hourly year
   with days of autonomy, and the inverter sized on the array for net
   metering or on the house peak with the 200% surge rule when there is a
   battery. Every appliance typed is kept in a catalogue for reuse.
7. Pricing: the materials workbook (suppliers, 362 items, drivers, route,
   labour rates, mob/demob, tools, job fees) is imported once into the app,
   which is then the master: edit prices, weights, panel sizes and settings
   in the browser, re-import a newer workbook to update items by code. A
   bill of materials is generated from the sizing and the roof layout
   (panels from the database, the default inverter per system kind as one
   unit, a larger single unit before parallel ones, the battery chosen on
   continuous current first and price second, rails, L-feet, clamps and
   splices per row, strings, PV and AC cable with breakers and conductors
   coordinated and a voltage-drop gauge check, protection, enclosures,
   grounding and bonding, a disconnect, consumables), can be edited line by
   line, and is priced exactly as the
   workbook does it: landed cost, freight run through the suppliers, labour
   crew and days, build-up with markups, commission and VAT, rounded up to
   the hundred. The maker's datasheet workbooks (panels, inverters,
   batteries) are imported on top (`python -m solarapp.pricing.datasheets`,
   or the upload on the Materials page): every sheet row is kept as a specs
   row and matched to its item by model, the figures sit above the workbook
   remarks and below what the owner types, and the page shows where each
   electrical figure came from, the rows without a priced item and the held
   rows that wait on the owner. With the figures on file the generator counts
   the strings from Voc at the cold design temperature against the inverter's
   maximum PV voltage, sizes the PV conductor and the DC breaker for
   1.25 × 1.25 × Isc, lays the strings on the MPPT inputs, runs the battery
   circuit on the larger of the inverter's discharge and charge currents and
   checks the battery's voltage class, charge current and Ah against kWh;
   the temperatures and the default coefficients are under Pricing settings ›
   String design, every one an assumption the owner replaces. The proposal PDF opens with the customer's situation and
   the solution in plain words, then Materials, Installation and permits,
   Installation tools and VAT, with the price before and after VAT.
8. Program of works: from the signing date, the schedule of permits, net
   metering steps, the pickup run, installation days with activities by
   the hour for the roof pairs and the ground crew, commissioning and the
   meter change; the customer's payments on the company's milestones. The
   proposal PDF carries the milestone schedule and payment terms; an
   internal PDF carries the full program and the pickup list. The cashflow
   projection and any installment structure belong to the finance module
   (the engine still computes them behind the API for it). "Plans
   for the PEE" is an internal A3 landscape drawing set for the signing
   engineer: a title block and signature block on every sheet (the PEE's
   name and PRC number from the company profile, blank lines otherwise),
   the cover and general notes, one array layout per roof face at a stated
   standard scale with dimension lines, strings and a north arrow, the
   equipment and circuit schedule from the BOM, and a last sheet that says
   what still waits on the datasheets (the single-line diagram, the string
   table) with the audit's schedule of loads. Each
   project shows an engineering status read from its facts (draft,
   surveyed, designed, proposal issued) on its head and in the project
   list; generating the proposal PDF marks it issued and locks the price
   until "Reopen design". The job stage (quoted, signed, sourcing...) stays
   on the record for the CRM and PM modules to come but has no screen here.
9. Economics for the customer: monthly bill before and after solar from
   the sizing's hourly balance and the effective tariff on the latest bill,
   export credit under net metering, savings by year with tariff rise and
   panel degradation, battery replacements at the warranty interval and
   inverter replacements, upkeep, payback,
   net savings over the analysis period, NPV, IRR, cost of solar energy
   and carbon avoided. The proposal PDF, laid out like a utility statement
   with the company's own branding, carries the charges, savings, payment
   stub, details and schedule.
10. Free estimate for the company website at `/estimate`, no login: goal,
    town (any city or municipality in the Philippines) or the phone's
    location, monthly use, usage
    pattern. Returns the bill before and after, payback, price and the
    system from the same engines with typical-roof assumptions, shows the
    battery as a priced add-on, and books the free roof visit as a website
    booking (a lead) with its source (UTM tags, referrer) and what the
    visitor saw. The bookings are the CRM's data, not the engineering
    app's: the back office only lists the open ones under Projects ›
    "From a website booking" and starts a project from one with the
    customer, the town or pin and the bill prefilled. The same page ships
    as an embeddable widget for the website (see below). The booking
    statuses, notes and the funnel (estimates run, leads, visits booked,
    converted) stay behind `/api/leads` for the CRM to come.
11. People: the owner and the engineers each sign in with their own
    account; an engineer works on projects and outputs, only an owner
    changes the company profile, pricing, the materials list and the
    people. Each person sets up their own authenticator app and security
    keys under Settings › Your account.

## The website and the estimate

The company website lives in `site/` as plain HTML and CSS (pages under
`site/pages/`, the shared frame in `site/layout.html`, a block shared by
several pages under `site/partials/` pasted by `<!-- include: name -->`,
styles and the small script under `site/static/`; the script fills the
profile, and gives the pages their motion: sections that come in as they
scroll into view, the proof figures that count up, the phone's sticky
call to action, all off under reduced motion and absent with JavaScript
off). `python site/build.py` writes it to `site/dist/`; the Docker build
does this. The build stamps the stylesheet, the site script and the
widget script with their content (`/static/site.css?v=…`), and the public
process sends the pages with `Cache-Control: no-cache` and stamped
assets with a year's `immutable`, so a redeploy shows on the next visit
on every phone and desktop, through Cloudflare included. After the first
deploy that carries this, purge Cloudflare's cache once (Caching ›
Configuration › Purge Everything); from then on nothing stale can stick. Build with `--base-url https://pldevinc.com` for absolute share-image and page addresses (Facebook needs them), and with `--with-placeholders` to keep the photo placeholder blocks, which the public build drops.
Contact details, the owner, the
PEE, warranties, brands and the service area are filled in at page load
from the company profile under Settings, so the pages never need editing
for those. The estimate page (`/estimate`) embeds the widget. Photos: the
web versions live in `site/static/photos/` (made from the owner's originals
by `python site/tools/photos.py IMG.jpg --name slug [--crop l,t,r,b]`: an
exact 4:3 crop at 960 and 480 px, WebP and JPEG, camera metadata dropped;
`--og` writes the 1200 × 630 share image). The home page carries a photo
beside the hero and three installation cards; About carries one; a page may
name its own share image with `<!-- og_image: ... -->`. The remaining
`.photo.placeholder` blocks (the roof visit, the owner, the crew) wait for
those photos and never reach the public build. Captions say only what the
frame shows until the owner supplies the town, the size and the customer's
go-ahead; no address or customer name is ever printed.

The website runs as its own process from the same image
(`solarapp.public:app`, the `solarapp-public` service): it serves the
built site, the brand marks and the widget, and forwards only the three
estimate calls (`/api/quick/status`, `estimate`, `lead`) to the private app
over the Docker network, with a shared token. It holds no database, no
documents and no login. The private app answers those three calls only to
the token or to a signed-in user.

### Set it up: two tunnels as containers

1. In `.env` set `SOLARAPP_INTERNAL_TOKEN` to a long random string
   (`openssl rand -hex 24`) and `SOLARAPP_PUBLIC_URL=https://solar.pldevinc.com`.
   `SOLARAPP_WEBSITE_URL=https://pldevinc.com` is where the card's QR code and the copied estimate summary send people (its `/estimate` page); it defaults to the first entry of `SOLARAPP_PUBLIC_ORIGINS`.
2. In the Cloudflare Zero Trust dashboard (Networks › Tunnels) create two
   tunnels of the Docker type and copy each token into `.env`:
   - **office**: public hostname `solar.pldevinc.com` → service
     `http://solarapp:8000`. Token into `CF_TUNNEL_TOKEN_OFFICE`.
   - **website**: public hostnames `pldevinc.com` and `www.pldevinc.com` →
     service `http://solarapp-public:8000`. Token into `CF_TUNNEL_TOKEN_PUBLIC`.
   The dashboard creates the DNS records for you.
3. Start everything, tunnels included:

   ```
   docker compose --profile tunnels up -d --build
   ```

4. Stop and remove the old host-level `cloudflared` service
   (`sudo systemctl disable --now cloudflared`) once the containers are up,
   and delete the old tunnel in the dashboard. You may then also delete the
   `ports:` block on the `solarapp` service in `docker-compose.yml`: the
   host no longer needs to publish anything.
5. Sign in as the owner (the username and password from `.env`; they are
   used once, to create the owner's account) and open Settings › Your
   account: set up the authenticator app (scan the QR code, keep the eight
   backup codes) and add your hardware key or phone passkey, which signs
   you in with one touch. Give an engineer their own account under
   Settings › People: the temporary password is shown once and they
   choose their own at the first sign-in. Cloudflare Access in front of
   `solar.pldevinc.com` is optional on top (see `docs/security.md`).

Then follow `docs/security.md` for the Cloudflare rules (rate limits, WAF,
Access, the www redirect), the server checklist, backups and the monthly
retention run (`python -m solarapp.retention`: website bookings that never
became a project lose their name, contact, address and precise pin after
twelve months, the estimate log is trimmed after ninety days, and projects
are never anonymised). Note that the compose file now requires
`SOLARAPP_INTERNAL_TOKEN` in `.env`, refuses the example password, runs
both processes as an unprivileged user (`sudo chown -R 10001:10001 data`
once) and publishes no host ports; use `docker-compose.lan.yml` for a
host-level cloudflared or LAN testing.

Single-container fallback: without the public process, set
`SOLARAPP_PUBLIC_HOST=pldevinc.com` and route that hostname to the private
app; it then serves the estimate page alone at the root of that hostname
and refuses everything else there.

### Embedding the estimate elsewhere

Any page can carry the estimate with

```html
<div id="pld-solar-estimate"></div>
<script src="https://pldevinc.com/widget/quick.js" defer></script>
```

The script calls the server it was loaded from. From a different origin,
list that origin in `SOLARAPP_PUBLIC_ORIGINS` on the private app and point
the script at it with `data-api`. Links to the estimate can carry UTM tags
(`?utm_source=fb&utm_medium=ad&utm_campaign=brownout1`); they are stored
with the booking for the CRM. The widget raises a
`pld-estimate` browser event (`estimate_shown`, `lead_submitted`) and pushes
`pld_estimate_shown` / `pld_lead_submitted` to `window.dataLayer` when one
exists, so a Meta Pixel or Google Tag on the website can fire Lead events.

**Lead notices:** set `SOLARAPP_SMTP_*` and `SOLARAPP_NOTIFY_EMAIL` in `.env`
to get an email for each booking (Gmail works with an app password); the
email carries the contact, what the visitor saw and a link that opens the
booking under Projects. Without it, bookings simply wait under Projects ›
"From a website booking" with their contact and what they saw.

Messenger templates, ad angles and offer notes for the funnel are in
`docs/marketing.md`.

## Brand

Colours and font live in `frontend/src/styles.css` (CSS variables at the top)
and `backend/solarapp/reports/brand.py` (PDF colours, fonts, logo). The logo
files are in `frontend/public/brand/` and `backend/solarapp/reports/assets/`;
Montserrat is bundled, so the app makes no font requests to the internet.
The company name and contact line on the documents come from `.env` or the
Settings page.

## Deploy on an Ubuntu server with Docker

```bash
sudo apt install -y docker.io docker-compose-v2   # if not installed
git clone <this repo> solarapp && cd solarapp
cp .env.example .env && nano .env                 # set username, password, secret, company name
docker compose build
```

### One-time weather data download (needs internet once)

```bash
docker compose run --rm solarapp python -m solarapp.data_download --out /app/data
```

This fetches the PVGIS typical meteorological year for every 0.25 degree
cell over the Philippines that contains land (913 cells, about 15 minutes
with the default 3 parallel requests, about 170 MB on disk) and the NASA
POWER monthly climatology for reference (198 points, under a minute). It is
resumable: run it again if it stops and it continues where it left off.
Data lands in `./data/` on the host, outside the image. Options:

```bash
python -m solarapp.data_download --help
python -m solarapp.data_download --out /app/data --bbox 12.0 19.0 119.0 124.5   # a smaller area first
python -m solarapp.data_download --out /app/data --limit 20                     # quick connectivity test
```

### Run

```bash
docker compose up -d
curl http://127.0.0.1:8000/api/health
```

The app listens on `127.0.0.1:8000` only. To reach it from other machines on
the office network, set `SOLARAPP_BIND=0.0.0.0` in `.env`, run
`docker compose up -d` again and open `http://<server ip>:8000`. For access
from anywhere, expose it with a Cloudflare Tunnel:

```bash
# quick tunnel for testing
cloudflared tunnel --url http://localhost:8000

# named tunnel (recommended): a fixed address such as solar.yourdomain.com on a
# domain whose DNS is on Cloudflare. Run once on the server:
cloudflared tunnel login                      # prints a link: open it on any browser, pick the domain
cloudflared tunnel create solarapp            # prints the tunnel id and writes ~/.cloudflared/<id>.json
cloudflared tunnel route dns solarapp solar.yourdomain.com
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/<id>.json /etc/cloudflared/
sudo tee /etc/cloudflared/config.yml > /dev/null <<EOF2
tunnel: <id>
credentials-file: /etc/cloudflared/<id>.json
protocol: http2
ingress:
  - hostname: solar.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF2
sudo cloudflared service install
sudo systemctl status cloudflared --no-pager
```

`protocol: http2` matters on networks that block UDP port 7844 (the
quick-tunnel pre-checks say "QUIC connection failed"). The service starts on
boot; `sudo journalctl -u cloudflared -f` shows its log.

Consider putting Cloudflare Access in front of the hostname as a second
login layer; the app itself has one password-protected user.

### Update a running server

Every update is the same five steps; the first update after the website,
the tunnels and the sign-in changes needs the extra ones marked "first time".

1. Back up first, from the repository folder on the server:

   ```bash
   mkdir -p data/backup
   docker compose exec -T solarapp python -c "import sqlite3,datetime; s=sqlite3.connect('/app/data/solarapp.db'); d=sqlite3.connect(f'/app/data/backup/solarapp-{datetime.date.today()}.db'); s.backup(d); d.close()"
   cp .env .env.bak
   ```

2. Pull the code. The work lives on the branch named below until it is
   merged; check it out explicitly:

   ```bash
   git fetch origin
   git checkout claude/wonderful-maxwell-wawb8t
   git pull
   ```

3. Bring `.env` up to date against `.env.example` (first time: the
   variables under "Website estimate" and "Website and tunnels" are new).
   Required now: `SOLARAPP_INTERNAL_TOKEN` (`openssl rand -hex 24`), a real
   `SOLARAPP_APP_PASSWORD` (the app refuses `change-me`; it only creates
   the first owner's account and may be cleared afterwards),
   `SOLARAPP_PUBLIC_ORIGINS`, `SOLARAPP_PUBLIC_URL`, `SOLARAPP_WEBSITE_URL`,
   `SOLARAPP_OFFICE_HOST`, `SOLARAPP_COOKIE_SECURE=true`, the two tunnel
   tokens and `COMPOSE_PROFILES=tunnels`. `SOLARAPP_SECRET_KEY` may stay
   blank: the app keeps one in `data/secret.key`.

4. First time only: the containers run as an unprivileged user, so the data
   folder must be theirs, and the two tunnels must exist in Cloudflare (see
   "Set it up: two tunnels as containers" above):

   ```bash
   sudo chown -R 10001:10001 data
   ```

5. Rebuild and restart (the build compiles the frontend and the site; a few
   minutes the first time):

   ```bash
   docker compose --profile tunnels up -d --build
   docker compose ps
   docker compose logs --since 5m solarapp | grep -E "migration|audit|Error"
   ```

   The app updates its own database on start: new tables and columns are
   added, and website leads that were saved as records move to the
   bookings table (the log says how many).

After the first update, in the browser:

- Materials: import the workbook again with "keep settings" ticked, so each
  inverter gets its grid-interactive flag and the electrical data the new
  checks use (until then the checks note that the flag is unknown).
- Settings: fill the company profile (contact details, the PEE, warranties,
  where to pay, the callback promise); they print on every document and on
  the website.
- Sign in with the `.env` username and password: that creates the owner's
  account, and an authenticator set up the old way (the `twofactor.json`
  file) and any security keys already registered carry over to it. From
  then on the password lives in the database, not in `.env`: change it
  under Settings › Your account, where the authenticator app and the keys
  are set up too. Add your engineer under Settings › People. The old
  `data/session.key` file is no longer read and can be deleted.
- Check `https://solar.pldevinc.com` (login), `https://pldevinc.com` (site),
  run the estimate and a test booking, and see it under Projects › "From a
  website booking".

Backups: `data/solarapp.db` holds everything the app knows; `data/` as a
whole adds the weather dataset (re-downloadable) and the secret key
(`secret.key`), which is worth keeping. Locked out (every owner lost their
phone and backup codes, or forgot the password)? On the server:
`docker compose exec solarapp python -m solarapp.users reset-authenticator <username>`
or `... reset-password <username>` (`list` shows everyone, `create` makes a
new owner); the command needs shell access to the server, which is the
point.

## Without Docker (plain Ubuntu)

```bash
sudo apt install -y python3-venv nodejs npm
cd frontend && npm ci && npm run build && cd ..
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env && nano .env
python -m solarapp.data_download --out ../data           # once
SOLARAPP_DATA_DIR=../data uvicorn solarapp.main:app --host 127.0.0.1 --port 8000
```

Run it under systemd or `nohup` to keep it alive.

## Development

```bash
cd backend && . .venv/bin/activate && pip install -r requirements-dev.txt
python -m pytest                                          # the whole suite, no network
python -m solarapp.pricing ../path/to/PLD_Materials_DB.xlsx   # import a materials workbook (the Materials page does this too)
python -m solarapp.pricing.datasheets ../path/to/ALL_SOLAR_PANEL_DATA_SHEET.xlsx ../path/to/ALL_INVERTER_DATA_SHEET.xlsx ../path/to/ALL_BATTERY_DATA_SHEET.xlsx   # the maker's datasheets onto the items (--dry-run, --report out.csv, --apply-held)
python -m solarapp.data_download --out ../data --synthetic --bbox 14.25 14.75 120.75 121.25
SOLARAPP_DATA_DIR=../data uvicorn solarapp.main:app --reload --port 8000
# in another terminal
cd frontend && npm run dev                                # http://localhost:5173, proxies /api
```

`--synthetic` writes clearly labelled fake weather so the UI can be tried
without the download. The app shows a red banner and refuses to produce a
customer PDF while synthetic data is in use.

## BOM and BOQ, in the app's words

The bill of materials (BOM) is the parts list the design generates, with the
owner's edits: every item, code, quantity and role. The bill of quantities
(BOQ) is that list priced through the build-up; the customer sees it as
"Details of charges" on the proposal, without the internal costs.

## Layout

```
backend/solarapp/core/kfactor.py      k per reading, site factor, thermal rise, quality checks
backend/solarapp/core/layout.py       panel fitting row by row on rectangle, hip and triangle faces
backend/solarapp/core/shade.py        wall strips and hourly shade from walls, trees and buildings
backend/solarapp/core/quick.py        quick estimate from four answers
backend/solarapp/core/simulation.py   hourly pvlib simulation and monthly aggregation
backend/solarapp/core/dataset.py      nearest-cell lookup and TMY loading
backend/solarapp/core/audit.py        appliance types and duty factors, load profiles, bill reconciliation
backend/solarapp/core/sizing.py       hourly balance, PV target, the battery over the hourly year, inverter requirement per kind
backend/solarapp/pricing/importer.py  reads the materials workbook (items, suppliers, drivers, route, rates)
backend/solarapp/pricing/engine.py    landed cost, freight run, labour calc, build-up, customer sections
backend/solarapp/pricing/boq.py       bill of materials from the sized system and roof layout: unit choice, circuits, roles
backend/solarapp/pricing/catalog.py   the materials list as the engine reads it (flags, ratings, grid-interactive inference)
backend/solarapp/pricing/config.py    every pricing, program and economics setting with its default and its version
backend/solarapp/pricing/job.py       prices an assessment: BOM, manual edits, extra km from the map pin
backend/solarapp/pricing/store.py     materials tables and pricing settings in SQLite, workbook import
backend/solarapp/pricing/datasheets.py  the maker's datasheet workbooks: the specs table, the three-tier match, the precedence, the report
backend/solarapp/pricing/design_checks.py  the string design and the battery checks the datasheet figures unlock (round 12)
backend/datasheets/                   the owner's three datasheet workbooks (the importer's default inputs)
backend/solarapp/pricing/program.py   program of works: schedule, hourly installation plan; the cashflow engine the finance module will read
backend/solarapp/pricing/economics.py customer economics: bill before and after, payback, NPV, IRR
backend/data_seed/                    bundled materials workbook, loaded on first start
backend/solarapp/compute.py           turns an assessment into results
backend/solarapp/data_download/       one-time PVGIS and NASA download
backend/solarapp/reports/             roof check PDF, client card PNG, proposal PDF, program of works PDF, plans for the PEE (A3), plan and Gantt drawings
backend/solarapp/api/                 FastAPI routes (assessments, pricing, settings, bookings, auth, people)
backend/solarapp/auth.py, users.py    accounts: passwords, sessions, roles; the server-side people command
backend/solarapp/passkeys.py, twofactor.py  security keys and the authenticator app, per person
backend/solarapp/public.py            the website process: static pages and the estimate proxy
frontend/src/                         React app (pages, components, the estimate page, the pricing settings)
site/                                 the website pages and their build
docs/                                 security, marketing, the engineering plan, the audit team and its rounds
.claude/agents/                       the five standing audit roles
data/                                 weather dataset and SQLite database (not in git)
```

## Data format

`data/pvgis/index.json` lists cells; `data/pvgis/cells/<lat>_<lon>.parquet`
holds 8760 hourly rows with `time_utc, temp_air, rh, ghi, dni, dhi, ir,
wind_speed, wind_dir, pressure` (float32). PVGIS labels each hour by its
start; the index stores `time_offset_h` (0.5 for ERA5) and the simulation
evaluates the sun position at the centre of each hour. For the Philippines
PVGIS serves its ERA5 database (2005 to 2023) with terrain horizon applied.
`data/nasa/climatology.json` holds monthly horizontal irradiation per NASA
POWER grid point (1 degree).

## Duty factor sources

Defaults in `backend/solarapp/core/audit.py` are engineering estimates
drawn from: refrigerator compressor duty of 33-40% in a typical kitchen
([Engineer Fix](https://engineerfix.com/what-is-a-normal-duty-cycle-for-a-refrigerator/)),
inverter aircon running 30-50% of rated input once at the setpoint and
saving 30-44% over fixed-speed units
([Cooling Insights](https://coolinginsights.com/guides/inverter-vs-normal-ac-consumption),
[comparison study](https://www.researchgate.net/publication/336234751_Comparison_of_Energy_Consumption_between_a_Standard_Air_Conditioner_and_an_Inverter-type_Air_Conditioner_Operating_in_an_Office_Building)),
hot and cold water dispensers measured at 0.66-1.1 kWh per day
([ENERGY STAR water coolers](https://www.energystar.gov/productfinder/product/certified-water-coolers/),
[EMSD Hong Kong](https://www.emsd.gov.hk/filemanager/WaterDispenser/en/data.pdf)),
and typical Philippine appliance wattages from the Meralco appliance
calculator. Override any factor per appliance when a clamp-meter reading
exists.
