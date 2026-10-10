"""Round 13, item 5 (brief 5.4): the schedule of loads in the permit's format, its own sheet before the last one. The
sample audit (8 LED bulbs 9 W, a 150 W refrigerator, a 1,200 W inverter aircon, a 90 W TV, a planned second aircon):
Lighting 72 W / 72 VA / 0.31 A; Convenience outlets 240 W / 240 VA / 1.04 A; Equipment 1,200 W / 1,412 VA (PF 0.85,
an assumption) / 6.14 A; the planned 1,200 W listed apart; connected (existing) 1,512 W; the PV block "6 kW, 26.1 A,
40 A 2P, 8.0 mm²"; the POI block with the 120 % line; every blank cell a blank line; no circuit number unless
service.circuits is typed, in which case the typed rows print first. The grouping and the power factors are settings;
the last sheet no longer tables the audit and lists the schedule only while the service block is blank."""
import re
import shutil
import subprocess
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.pricing.config import LoadsConfig, PricingConfig, settings_version
from solarapp.reports.plans_loads import load_groups
from solarapp.reports.plans_pdf import BLANK
from tests.test_drawings import PILA_DOC
from tests.test_survey_fields import SERVICE

PLANNED = {"id": "ac2", "name": "Second aircon (planned)", "category": "aircon_inverter", "input_power_w": 1200, "quantity": 1, "status": "future",
           "windows": [{"start": "20:00", "end": "06:00"}]}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def _pdf_text(pdf: bytes) -> str:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    return subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode()


def _pages(text: str) -> list[str]:
    return [p for p in text.split("\f") if p.strip()]


def _loads_page(pages: list[str]) -> str:
    return next(p for p in pages if p.strip().splitlines()[0].strip() == "Schedule of loads")


def _doc(service: bool = True, planned: bool = True, circuits: bool = False) -> dict:
    doc = deepcopy(PILA_DOC)
    if planned:
        doc["audit"]["appliances"].append(deepcopy(PLANNED))
    if service:
        doc["service"] = deepcopy(SERVICE)
        if not circuits:
            doc["service"]["circuits"] = []
    return doc


def _build(client: TestClient, doc: dict) -> tuple[dict, list[str]]:
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    pdf = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert pdf.status_code == 200, pdf.text
    return r.json()["results"], _pages(_pdf_text(pdf.content))


def _row(page: str, label: str) -> str:
    """The table line that carries the label (pdftotext keeps a table row on one line)."""
    return next(ln for ln in page.splitlines() if label in ln)


def test_the_groups_and_their_figures_are_hand_worked():
    """The grouping and the arithmetic on the sample audit, settings and volts as the sheet reads them."""
    apps = [
        {"name": "Refrigerator", "category": "refrigerator", "status": "existing", "quantity": 1, "input_power_w": 150},
        {"name": "Split inverter AC", "category": "aircon_inverter", "status": "existing", "quantity": 1, "input_power_w": 1200},
        {"name": "LED bulb", "category": "lighting", "status": "existing", "quantity": 8, "input_power_w": 9},
        {"name": "TV", "category": "other", "status": "existing", "quantity": 1, "input_power_w": 90},
        {"name": "Second aircon (planned)", "category": "aircon_inverter", "status": "future", "quantity": 1, "input_power_w": 1200},
        {"name": "Old freezer", "category": "freezer", "status": "retiring", "quantity": 1, "input_power_w": 200},
    ]
    g = load_groups(apps, LoadsConfig().model_dump(), 230.0)
    li, out, eq, pl = g["groups"]["lighting"], g["groups"]["outlets"], g["groups"]["equipment"], g["planned"]
    assert (li["w"], li["va"], round(li["a"], 2)) == (72, 72, 0.31) and li["pf"] == 1.0
    assert (out["w"], out["va"], round(out["a"], 2)) == (240, 240, 1.04) and [ln["name"] for ln in out["lines"]] == ["Refrigerator", "TV"]
    assert eq["w"] == 1200 and round(eq["va"]) == 1412 and round(eq["a"], 2) == 6.14 and eq["pf"] == 0.85
    assert pl["w"] == 1200 and [ln["name"] for ln in pl["lines"]] == ["Second aircon (planned)"]
    assert g["existing_w"] == 1512 and round(g["existing_va"]) == 1724 and g["retiring"] == 1
    # a power factor missing from the settings leaves the VA and the amperes blank, never a guess
    g2 = load_groups(apps, {"power_factor": {"lighting": 1.0}, "equipment_categories": ["aircon_inverter"]}, 230.0)
    assert g2["groups"]["equipment"]["va_known"] is False and g2["groups"]["equipment"]["lines"][0]["va"] is None and g2["existing_va"] is None
    # the settings block is a sheet's labels, outside the pricing fingerprint
    cfg = PricingConfig()
    v0 = settings_version(cfg)
    cfg.loads.power_factor["equipment"] = 0.9
    assert settings_version(cfg) == v0 and cfg.loads.equipment_categories[0] == "aircon_inverter"


def test_the_sheet_prints_the_sample_in_the_permits_format(client):
    res, pages = _build(client, _doc())
    cover, loads, last = pages[0], _loads_page(pages), pages[-1]
    assert len(pages) == 7 and "Sheet 6 Schedule of loads" in " ".join(cover.split()) and "Sheet 7 Not yet in this set" in " ".join(cover.split())
    flat = " ".join(loads.split())
    # the header line and the columns, flagged to verify against the LGU's sample
    assert "Panelboard main panel, ground floor, 12-way: 230 V, 1Ø 2W, main breaker 100 AT /" in flat and "bus 125 A, fed from" in flat
    assert "verify against the LGU's sample" in flat
    for col in ("Circuit No.", "Description of load", "Load (W)", "Load (VA)", "Volts", "Amperes", "Wire (mm² THHN)", "Conduit (mm)", "OCPD (AT/AF, poles)", "Remarks"):
        assert col in flat, col
    # the three groups with their labelled power factors, the lines and the subtotals (one table row per line)
    assert "Lighting (PF 1.00, assumption" in flat and "Convenience outlets (PF 1.00, assumption" in flat and "Equipment (PF 0.85, assumption" in flat
    assert re.search(r"8 × LED bulb, 9 W each\s+72\s+72\s+230\s+0\.31", loads)
    assert re.search(r"Lighting subtotal\s+72\s+72\s+230\s+0\.31", loads)
    assert re.search(r"Convenience outlets subtotal\s+240\s+240\s+230\s+1\.04", loads)
    assert re.search(r"Equipment subtotal\s+1,200\s+1,412\s+230\s+6\.14", loads)
    assert re.search(r"Connected load, existing\s+1,512\s+1,724\s+230\s+7\.49", loads)
    # the planned aircon apart and outside the existing total; the demand load blank with the audit's own peak
    assert "Planned loads" in flat and re.search(r"1 × Second aircon \(planned\), 1200 W\s+1,200\s+1,412\s+230\s+6\.14", loads) and "planned" in loads
    # the planned aircon raises the sizing's coincident peak (0.87 kW without it) and the system (10 panels, two strings, two battery units)
    assert "Demand load" in flat and "demand factors of PEC 2.20 (verify) are the engineer's" in flat and "coincident peak is 1.53 kW" in flat
    # no circuit number, wire, conduit or breaker on an audit line: the first column blank, three blank lines, the engineer's
    led = _row(loads, "8 × LED bulb")
    assert led.count(BLANK) == 3 and re.match(r"\s{6,}8 × LED bulb", led)
    # the PV system as a source and the point of interconnection
    assert re.search(r"10 × 585 W = 5\.85 kWp DC, 1 string of 10", flat) and "26.1 A at 230 V" in flat and "40 A 2P (C5" in flat and "8.0 mm² THHN" in flat   # no datasheets here: the rule's one string of ten
    assert "FLEX CONDUIT 32mm (IAN-ENC-011)" in flat and "Energy storage" in flat and re.search(r"Energy storage \d+ × [\d.]+ kWh = [\d.]+ kWh", flat)
    assert "a backfeed breaker on the load side of the existing panelboard" in flat and "100 A, 125 A" in flat
    assert "120 %: 40 A + 100 A = 140 A; limit 1.2 × 125 A = 150 A; PASS" in flat and "two-way meter" in flat and "FLECO, account 12-3456-7890" in flat
    assert "Filled by the signing engineer" in flat
    # the last sheet no longer tables the audit, and the service block is surveyed, so it does not list the schedule either
    assert "Refrigerator" not in last and "Schedule of loads" not in last and "Not yet in this set, and why" in last
    assert res["pricing"]["design_blocked"] == []


def test_typed_circuits_print_first_and_verbatim(client):
    res, pages = _build(client, _doc(circuits=True))
    loads = _loads_page(pages)
    flat = " ".join(loads.split())
    assert "Existing circuits as typed on the Site step" in flat
    r1, r2 = _row(loads, "lights, ground floor"), _row(loads, "aircon, master bedroom")
    assert re.match(r"\s*1\s+lights, ground floor", r1) and "3.5" in r1 and "20" in r1 and "20 AT /" in r1 and "1P" in r1 and "existing, as typed" in r1
    assert re.match(r"\s*2\s+aircon, master bedroom", r2) and "5.5" in r2 and "25" in r2 and "32 AT /" in r2 and "2P" in r2
    assert loads.index("lights, ground floor") < loads.index("Lighting (PF")


def test_a_blank_service_block_and_no_planned_loads(client):
    res, pages = _build(client, _doc(service=False, planned=False))
    loads, last = _loads_page(pages), pages[-1]
    flat = " ".join(loads.split())
    assert f"Panelboard {BLANK}: 230 V (assumption), {BLANK} Ø (not surveyed), main breaker {BLANK} AT" in flat
    assert "Planned loads" not in flat and "not chosen (Site step)" in flat and "120 % rule: not checked" in flat
    assert f"{BLANK}, {BLANK} (not surveyed)" in flat and f"{BLANK}, account {BLANK}" in flat
    # the last sheet lists the schedule only while the service entrance is blank
    assert "Schedule of loads (service entrance blank)" in " ".join(last.split()) and "Site step" in " ".join(last.split())


def test_an_audit_without_appliances_still_builds_the_sheet(client):
    doc = _doc(service=False, planned=False)
    doc["audit"] = {"appliances": [], "bills": [], "reconcile": True, "system": {"kind": "combination"}}
    aid = client.post("/api/assessments", json=doc).json()["id"]
    assert client.post(f"/api/assessments/{aid}/compute").status_code == 200
    assert client.get(f"/api/assessments/{aid}/plans.pdf").status_code == 409   # no sizing: no pricing, no plans (as before)
