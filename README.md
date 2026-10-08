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
   that shade them, and candidate panels (Wp, length, width, or picked from
   the materials database). The app cuts the wall strips, fits panels row by
   row in both orientations, shades the simulation hour by hour, and shows
   the panel and count that give the most kWp.
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
   load against this roof's production for an off-grid system (full
   battery, no grid import), net metering, or net metering with a battery:
   PV capped by the roof, battery modules, and the inverter size from your
   catalogue sizes with the 200% surge rule. Every appliance typed is kept
   in a catalogue for reuse.
7. Pricing: the materials workbook (suppliers, 362 items, drivers, route,
   labour rates, mob/demob, tools, job fees) is imported once into the app,
   which is then the master: edit prices, weights, panel sizes and settings
   in the browser, re-import a newer workbook to update items by code. A
   bill of materials is generated from the sizing and the roof layout
   (panels from the database, default inverter model (Felicity 6 kW eco-hybrid) in parallel units
   as needed, cheapest battery combination at or above the required kWh,
   rails, L-feet, clamps and splices per row, strings, PV and AC cable with
   a voltage-drop gauge check, protection, enclosures, grounding,
   consumables), can be edited line by line, and is priced exactly as the
   workbook does it: landed cost, freight run through the suppliers, labour
   crew and days, build-up with markups, commission and VAT, rounded up to
   the hundred. A customer quotation PDF shows Materials, Labor, Equipment
   (the tool charge) and Tax only.
8. Program of works: from the signing date, the schedule of permits, net
   metering steps, the pickup run, installation days with activities by
   the hour for the roof pairs and the ground crew, commissioning and the
   meter change; customer payments on milestones or in instalments; a
   cashflow with the running balance and the lowest point the company has
   to carry. The quotation PDF carries the milestone schedule and payment
   terms; an internal PDF carries the full program and cashflow. Each
   assessment has a job stage for the project list.
9. Economics for the customer: monthly bill before and after solar from
   the sizing's hourly balance and the effective tariff on the latest bill,
   export credit under net metering, savings by year with tariff rise and
   panel degradation, battery and inverter replacements, upkeep, payback,
   net savings over the analysis period, NPV, IRR, cost of solar energy
   and carbon avoided. The proposal PDF, laid out like a utility statement
   with the company's own branding, carries the charges, savings, payment
   stub, details and schedule.
10. Free estimate for the company website at `/estimate`, no login: goal,
    town (Laguna and Batangas) or the phone's location, monthly use, usage
    pattern. Returns the bill before and after, payback, price and the
    system from the same engines with typical-roof assumptions, shows the
    battery as a priced add-on, and books the free roof visit as a lead on
    the job list with its source (UTM tags, referrer) and what the visitor
    saw. The same page ships as an embeddable widget for the website (see
    below). The job list shows the funnel for the last 30 days: estimates
    run, leads, visits, proposals, signed.

## The website and the estimate

The company website lives in `site/` as plain HTML and CSS (pages under
`site/pages/`, the shared frame in `site/layout.html`, styles and the small
script under `site/static/`). `python site/build.py` writes it to
`site/dist/`; the Docker build does this. Contact details, the owner, the
PEE, warranties, brands and the service area are filled in at page load
from the company profile under Settings, so the pages never need editing
for those. The estimate page (`/estimate`) embeds the widget. Photos are
placeholders until real ones replace them (`site/pages/index.html` and
`about.html`, the `.photo.placeholder` blocks).

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
5. Switch on two-factor login for the back office:
   `docker compose exec solarapp python -m solarapp.twofactor setup`, scan
   the QR code with an authenticator app and keep the backup codes. The
   login page then asks for the code after the password. Then add your
   hardware key or phone passkey in Settings › Sign-in security: it signs
   you in with one touch. Cloudflare Access in front of
   `solar.pldevinc.com` is optional on top (see `docs/security.md`).

Then follow `docs/security.md` for the Cloudflare rules (rate limits, WAF,
Access, the www redirect), the server checklist, backups and the monthly
retention run. Note that the compose file now requires
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
with the lead and counted on the job list. The widget raises a
`pld-estimate` browser event (`estimate_shown`, `lead_submitted`) and pushes
`pld_estimate_shown` / `pld_lead_submitted` to `window.dataLayer` when one
exists, so a Meta Pixel or Google Tag on the website can fire Lead events.

**Lead notices:** set `SOLARAPP_SMTP_*` and `SOLARAPP_NOTIFY_EMAIL` in `.env`
to get an email for each booking (Gmail works with an app password). Without
it, leads simply appear at the top of the job list with their contact and
what they saw.

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

### Update

```bash
git pull && docker compose build && docker compose up -d
```

Backups: copy `./data/solarapp.db` (assessments) and, optionally, `./data/`
as a whole (weather dataset, re-downloadable).

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
python -m pytest                                          # 64 tests, no network
python -m solarapp.pricing ../path/to/PLD_Materials_DB.xlsx   # import a materials workbook (the Materials page does this too)
python -m solarapp.data_download --out ../data --synthetic --bbox 14.25 14.75 120.75 121.25
SOLARAPP_DATA_DIR=../data uvicorn solarapp.main:app --reload --port 8000
# in another terminal
cd frontend && npm run dev                                # http://localhost:5173, proxies /api
```

`--synthetic` writes clearly labelled fake weather so the UI can be tried
without the download. The app shows a red banner and refuses to produce a
customer PDF while synthetic data is in use.

## Layout

```
backend/solarapp/core/kfactor.py      k per reading, site factor, thermal rise, quality checks
backend/solarapp/core/layout.py       panel fitting row by row on rectangle, hip and triangle faces
backend/solarapp/core/shade.py        wall strips and hourly shade from walls, trees and buildings
backend/solarapp/core/quick.py        quick estimate from four answers
backend/solarapp/core/simulation.py   hourly pvlib simulation and monthly aggregation
backend/solarapp/core/dataset.py      nearest-cell lookup and TMY loading
backend/solarapp/core/audit.py        appliance types and duty factors, load profiles, bill reconciliation
backend/solarapp/core/sizing.py       hourly balance, PV target, battery modules, inverter choice
backend/solarapp/pricing/importer.py  reads the materials workbook (items, suppliers, drivers, route, rates)
backend/solarapp/pricing/engine.py    landed cost, freight run, labour calc, build-up, customer sections
backend/solarapp/pricing/boq.py       bill of materials from the sized system and roof layout
backend/solarapp/pricing/job.py       prices an assessment: BOQ, manual edits, extra km from the map pin
backend/solarapp/pricing/store.py     materials tables and pricing settings in SQLite, workbook import
backend/solarapp/pricing/program.py   program of works: schedule, hourly installation plan, cashflow
backend/solarapp/pricing/economics.py customer economics: bill before and after, payback, NPV, IRR
backend/data_seed/                    bundled materials workbook, loaded on first start
backend/solarapp/compute.py           turns an assessment into results
backend/solarapp/data_download/       one-time PVGIS and NASA download
backend/solarapp/reports/             customer PDF, client card PNG, proposal PDF, internal program of works PDF
backend/solarapp/api/                 FastAPI routes
frontend/src/                         React app (map pin, editors, results)
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
