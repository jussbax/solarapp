# Solar Roof Simulator

Estimates what a roof in the Philippines can produce, combining the company's
on-site readings (UNI-T UT381PV irradiance meter and UT673PV+ MPPT meter on a
50 W test panel) with PVGIS typical-year weather data. The weather data is
downloaded once; after that the server makes no outside calls.

The design decisions behind every formula are in [DECISIONS.md](DECISIONS.md).

## What it does

1. Drop a map pin on the roof. The nearest PVGIS grid cell is used.
2. Enter roof faces (length, width, tilt, facing) and candidate panels
   (Wp, length, width). The app fits panels in rows and columns, tries both
   orientations, and shows the panel and count that give the most kWp.
3. Enter the on-site readings: three simultaneous rows of irradiance, MPPT
   power and panel surface temperature per roof face. The app computes the
   owner's k per row, removes the heat and low-light effect present at the
   moment of measurement (PVGIS Huld module model) to get a site factor,
   and calibrates the thermal model from the probe temperature.
4. Simulates every hour of a typical year per face (Perez transposition,
   Martin-Ruiz reflection, Huld module model, site thermal rise) and reports
   monthly and annual kWh at the panels, the "measured versus PVGIS" percent,
   and the owner's original formula for continuity.
5. Produces a trimmed customer PDF. Readings, k, warnings and dataset details
   stay on the internal page.
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
   (panels from the database, cheapest hybrid inverter at or above the
   required kW, cheapest battery combination at or above the required kWh,
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

The app listens on `127.0.0.1:8000` only. Expose it with a Cloudflare Tunnel:

```bash
# quick tunnel for testing
cloudflared tunnel --url http://localhost:8000

# named tunnel (recommended): create once, then in the tunnel's ingress
# point your hostname at http://localhost:8000
cloudflared tunnel login
cloudflared tunnel create solarapp
cloudflared tunnel route dns solarapp solar.yourdomain.com
# ~/.cloudflared/config.yml:
#   tunnel: <tunnel id>
#   credentials-file: /home/<user>/.cloudflared/<tunnel id>.json
#   ingress:
#     - hostname: solar.yourdomain.com
#       service: http://localhost:8000
#     - service: http_status:404
sudo cloudflared service install
```

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
backend/solarapp/core/layout.py       panel fitting (rows x columns, both orientations)
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
backend/data_seed/                    bundled materials workbook, loaded on first start
backend/solarapp/compute.py           turns an assessment into results
backend/solarapp/data_download/       one-time PVGIS and NASA download
backend/solarapp/reports/             customer PDF, quotation PDF, internal program of works PDF
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
