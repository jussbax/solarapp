"""Round 13, item 1 (brief 1.5): the single-line diagram sheet of the plans for the PEE, and the 120 % busbar rule at the
point of interconnection. Hand-worked on the Pila sample with the datasheet fixtures and a 500 V input on the default
inverter (one string of 6 × 585 W; Voc 53.08 V → 54.83 V at 14 °C, 6 × 54.83 = 329.0 V on the placard; the 25 A DC
breaker; 139 A on the battery port; the 40 A inverter-output breaker): the sheet exists and is named on the cover, the
balloons match the circuit rows, "two-way meter" on a combination job and "nothing exported" on an off-grid job (two
strings there), "Not to scale" in the title block; with the service block blank every figure is a blank line with its
reason; without the datasheets the string label carries "(rule)" and the datasheet figures are blank; busbar 100 A with
the 100 A main and the 40 A grid breaker prints FAIL and raises poi_busbar (hard, not blocking), busbar 125 A passes."""
import re
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from reportlab.graphics.shapes import Circle, Line, String
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from solarapp.pricing.service_checks import poi_busbar_check
from solarapp.reports.plans_pdf import BLANK
from solarapp.reports.plans_sld import _figures, poi_lines, sld_drawing
from solarapp.schemas import AssessmentDoc
from tests.test_drawings import PILA_DOC
from tests.test_survey_fields import SERVICE

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "datasheets"
FILES = [FIXTURES / f"ALL_{n}_DATA_SHEET.xlsx" for n in ("SOLAR_PANEL", "INVERTER", "BATTERY")]


def _client(tmp_path_factory, datasheets: bool):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    c = TestClient(app)
    c.__enter__()
    c.post("/api/auth/login", json={"username": "u", "password": "p"})
    if datasheets:
        for f in FILES:
            with open(f, "rb") as fh:
                assert c.post("/api/pricing/datasheets", files={"file": (f.name, fh, "application/octet-stream")}).status_code == 200
        assert c.put("/api/pricing/items/FS-INV-008", json={"max_pv_voltage_v": 500}).status_code == 200
    return c


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    c = _client(tmp_path_factory, True)
    yield c
    c.__exit__(None, None, None)


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    c = _client(tmp_path_factory, False)
    yield c
    c.__exit__(None, None, None)


def _pdf_text(pdf: bytes) -> str:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    return subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode()


def _pages(text: str) -> list[str]:
    return [p for p in text.split("\f") if p.strip()]


def _sld_page(pages: list[str]) -> str:
    return next(p for p in pages if p.strip().splitlines()[0].strip() == "Single-line diagram")


def _doc(kind: str = "combination", service: bool = True, **svc) -> dict:
    doc = deepcopy(PILA_DOC)
    doc["audit"]["system"]["kind"] = kind
    if service:
        doc["service"] = {**deepcopy(SERVICE), **svc}
    return doc


def _build(client: TestClient, doc: dict) -> tuple[dict, list[str]]:
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    pdf = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert pdf.status_code == 200, pdf.text
    res["_aid"] = aid
    return res, _pages(_pdf_text(pdf.content))


def _drawing(client: TestClient, res: dict):
    """The diagram itself (a reportlab Drawing) for the record `res` was computed on, with the materials list and the settings."""
    doc = AssessmentDoc.model_validate(client.get(f"/api/assessments/{res['_aid']}").json()["doc"])
    items = {it["code"]: it for it in client.get("/api/pricing/items", params={"limit": 1000, "include_inactive": True}).json()}
    return sld_drawing(_figures(doc, res, items, client.get("/api/pricing/config").json()))


def test_the_sheet_prints_the_sample_figures_and_its_balloons_match_the_circuit_rows(client):
    res, pages = _build(client, _doc())
    ch = res["pricing"]["choices"]
    assert ch["strings"] == 1 and ch["panels_per_string"] == 6 and ch["dc_breaker"]["ocpd_a"] == 25 and ch["ac_breaker_a"] == 40
    assert res["pricing"]["design_blocked"] == [] and "poi_busbar" not in {w["code"] for w in res["pricing"]["warnings"]}
    cover, sld = pages[0], _sld_page(pages)
    # named on the cover's sheet index, after the two array layouts; not to scale in the title block
    assert "Sheet 5 Single-line diagram" in " ".join(cover.split()) and "Not to scale" in sld
    # the string and the datasheet line, the placard's 6 × 54.83 V, the DC breaker, the battery port, the inverter-output breaker
    assert "S1: 6 × 585 W" in sld and "Voc 53.1 V STC, 54.8 V at 14 °C; Vmp 44.0 V; Isc 13.53 A; Imp 13.31 A" in sld
    assert "329.0 V at 14 °C" in sld and "25 A 2P DC breaker per string" in sld and "139 A" in sld and "40 A 2P" in sld
    # the AC side as the circuits carry it, the two-way meter on a combination job, the DU and the 120 % rule from the service block
    assert "two-way meter: installed" in sld and "nothing exported" not in sld
    assert "FLECO: fault level at the service" in sld and "existing panelboard:" in sld and "main 100 A, bus 125 A" in sld
    assert "120 %: 40 A + 100 A = 140 A" in sld and "limit 1.2 × 125 A = 150 A" in sld and "PASS" in sld and "FAIL" not in sld
    # the balloons: every circuit that applies, and no C2 (one string joins nothing)
    applies = [c["id"] for c in ch["circuits"] if c["applies"]]
    assert applies == ["C1", "C3", "C4", "C5", "C6", "C7"]
    for cid in applies:
        assert re.search(rf"\b{cid}\b", sld), cid
    assert not re.search(r"\bC2\b", sld)
    # the legend and the placards say what to verify; nothing invented on the sheet
    assert "verify the symbol set against the DU's sample" in " ".join(sld.split()) and "verify the DU's wording" in sld
    assert "PV DC DISCONNECT" in sld and "DUAL POWER SOURCE" in sld and "ENERGY STORAGE 15.00 kWh" in sld
    assert "transformerless inverter" in " ".join(sld.split())


def test_an_off_grid_job_draws_its_two_strings_and_exports_nothing(client):
    res, pages = _build(client, _doc("off_grid"))
    ch = res["pricing"]["choices"]
    assert ch["strings"] == 2 and ch["panels_per_string"] == 5 and ch["dc_spds"] == 2
    sld = _sld_page(pages)
    assert "S1, S2: 5 × 585 W (2 alike, one drawn)" in sld and "DC SPD 600 V × 2" in sld
    assert "existing meter; nothing exported" in sld and "two-way meter" not in sld
    assert "Battery with the grid as backup" in sld   # the kind in the title block
    assert "ENERGY STORAGE" in sld and "FS-BAT-003" in sld
    # the review's finding 10: the 120 % rule is applied all the same on a no-export job, and says so (the block carries the kind)
    poi = ch["poi_busbar"]
    assert poi["kind"] == "off_grid" and poi["checked"] and poi["ok"]
    assert poi_lines(poi) == ["120 %: 40 A + 100 A = 140 A", "limit 1.2 × 125 A = 150 A", "PASS; verify the PEC clause",
                              "(applied although nothing is exported: conservative; the DU's view: verify)"]
    assert "applied although nothing is exported" in " ".join(sld.split())
    reading = next(p for p in _pages(subprocess.run(["pdftotext", "-", "-"], input=client.get(f"/api/assessments/{res['_aid']}/plans.pdf").content, capture_output=True, check=True).stdout.decode())
                   if p.strip().startswith("Schedule of loads"))
    assert "PASS; verify the PEC clause; (applied although nothing is exported: conservative; the DU's view: verify)" in " ".join(reading.split())
    # the grid-interactive inverter on a no-export job leads with the role (finding 7)
    assert "grid-interactive (no export), 1Ø; the datasheet's type: off-grid" in " ".join(s.text for s in _drawing(client, res).contents if isinstance(s, String))


def test_a_net_metering_job_has_no_battery_and_the_last_sheet_lists_only_what_is_missing(client):
    res, pages = _build(client, _doc("net_metering"))
    sld, last = _sld_page(pages), pages[-1]
    assert "no battery (net metering)" in sld and "ENERGY STORAGE" not in sld and "two-way meter" in sld
    assert not re.search(r"\bC3\b", sld)   # the battery circuit does not apply
    # the diagram is in the set: the last sheet lists the figures still blank on it under its sheet number (review finding 5)
    flat_last = " ".join(last.split())
    assert "Sheet 5 2 Inverter: MPPT window (low); Inverter: MPPT window (high) not on the item (Materials page)" in flat_last
    assert "Sheet 5 1 Inverter: certificate none on file: type it on the Materials page" in flat_last and "Single-line diagram (figures blank)" not in last


def test_a_blank_service_block_prints_a_blank_line_with_its_reason_everywhere(client):
    res, pages = _build(client, _doc(service=False))
    sld = _sld_page(pages)
    poi = res["pricing"]["choices"]["poi_busbar"]
    assert poi["checked"] is False and "not chosen" in poi["reason"] and "poi_busbar" not in {w["code"] for w in res["pricing"]["warnings"]}
    assert "not chosen (Site step)" in sld and "120 % rule: not checked" in sld and f"DU {BLANK}" in sld
    assert "230 V (assumption)" in sld and f"phase {BLANK}" in sld and f"account {BLANK}" in sld and f"meter number: {BLANK}" in sld
    assert "existing panelboard:" in sld and f"bus {BLANK}" in sld and "(not surveyed)" in sld and "PASS" not in sld and "FAIL" not in sld


def test_without_the_datasheets_the_figures_are_blank_and_the_string_label_says_rule(plain):
    res, pages = _build(plain, _doc())
    sld = _sld_page(pages)
    assert res["pricing"]["choices"]["string_design"]["available"] is False
    assert re.search(r"S1: \d+ × 585 W \(rule\)", sld) and f"Voc {BLANK} STC, {BLANK} at 14 °C" in sld
    assert "not checked: no Isc on file" in sld and f"maximum Voc {BLANK}" in " ".join(sld.split())
    assert "two-way meter" in sld and "120 %: 40 A + 100 A = 140 A" in sld
    # the set: cover, two layouts, the diagram, the schedule, the schedule of loads, the last sheet
    assert len(pages) == 10 and "Sheet 5 Single-line diagram" in " ".join(pages[0].split())


def test_the_120_rule_fails_on_a_100_a_busbar_and_passes_on_125(client):
    res, pages = _build(client, _doc(busbar_a=100))
    codes = {w["code"] for w in res["pricing"]["warnings"]}
    poi = res["pricing"]["choices"]["poi_busbar"]
    assert poi["checked"] and poi["sum_a"] == 140 and poi["limit_a"] == 120 and poi["ok"] is False
    assert "poi_busbar" in codes and res["pricing"]["design_blocked"] == []   # hard, not blocking: the plans still build
    w = next(w for w in res["pricing"]["warnings"] if w["code"] == "poi_busbar")
    assert w["hard"] is True and not w.get("blocks_documents") and "140 A" in w["message"] and "120 A" in w["message"]
    sld = _sld_page(pages)
    assert "FAIL" in sld and "poi_busbar" in sld and "PASS" not in sld
    res, pages = _build(client, _doc(busbar_a=125))
    poi = res["pricing"]["choices"]["poi_busbar"]
    assert poi["ok"] is True and poi["limit_a"] == 150 and "poi_busbar" not in {w["code"] for w in res["pricing"]["warnings"]}
    assert "PASS" in _sld_page(pages)


def test_the_electrode_caption_clears_the_egc_bus_and_the_labels_read_as_the_review_asked(client):
    """The review's finding 3: the electrode caption's box (the figure's, not the text's) sits clear of the EGC bus line and the
    electrode, to the right of the C7 balloon, and the service block keeps "fault level at the service 10.0 kA" on one line.
    Finding 7: the inverter balloon leads with the role and the datasheet's type word follows. Finding 11: C6 is the bypass feed."""
    res, _pages_ = _build(client, _doc(fault_level_ka=10))
    d = _drawing(client, res)
    strings = [s for s in d.contents if isinstance(s, String)]
    lines = [l for l in d.contents if isinstance(l, Line)]
    earth_y = 11.0 * mm
    bus = max((l for l in lines if abs(l.y1 - earth_y) < 0.01 and abs(l.y2 - earth_y) < 0.01), key=lambda l: abs(l.x2 - l.x1))   # the EGC bus
    balloon = max((c for c in d.contents if isinstance(c, Circle) and abs(c.cy - earth_y) < 0.01), key=lambda c: c.cx)            # the C7 balloon
    caption = [s for s in strings if any(w in s.text for w in ("EGC bus", "bonds dashed", "electrode:", "GEC", "or less for a rod"))]
    assert len(caption) >= 4
    box = (min(s.x for s in caption), min(s.y for s in caption), max(s.x + pdfmetrics.stringWidth(s.text, s.fontName, s.fontSize) for s in caption), max(s.y + s.fontSize for s in caption))
    assert box[0] > max(bus.x1, bus.x2) + 1.0 * mm and box[0] >= balloon.cx + balloon.r      # right of the bus's end (and of the electrode under the panelboard) and of the balloon
    assert box[2] <= d.width and box[1] >= 0                                                 # inside the sheet
    assert any(s.text.endswith("fault level at the service 10.0 kA") for s in strings)       # not wrapped into "10.0" / "kA"
    joined = " ".join(s.text for s in strings)
    assert "FS-INV-008: 6 kW grid-interactive (hybrid), 1Ø; the datasheet's type: off-grid" in joined and "off-grid type" not in joined
    assert "C5 backfeed brk; C6 bypass feed" in joined and "backfeed brk: C5, C6" not in joined


def test_the_rule_itself():
    """The check is a plain function the sheets call too: the arithmetic, the units, and every reason it is not checked."""
    block, warns = poi_busbar_check({"interconnection": "load_side_breaker", "main_breaker_a": 100, "busbar_a": 125}, {"ac_grid_breaker_a": 40, "inverter_units": 1})
    assert block["checked"] and block["sum_a"] == 140 and block["limit_a"] == 150 and block["ok"] and warns == [] and block["kind"] == ""
    assert poi_lines(block)[-1] == "PASS; verify the PEC clause" and poi_lines(block, "off_grid")[-1] == "(applied although nothing is exported: conservative; the DU's view: verify)"
    block, warns = poi_busbar_check({"interconnection": "load_side_breaker", "main_breaker_a": 100, "busbar_a": 125}, {"ac_grid_breaker_a": 40, "inverter_units": 2})
    assert block["backfeed_a"] == 80 and block["sum_a"] == 180 and block["ok"] is False and [w["code"] for w in warns] == ["poi_busbar"] and "× 2" in warns[0]["message"]
    for svc, word in (
        ({"interconnection": "", "main_breaker_a": 100, "busbar_a": 100}, "not chosen"),
        ({"interconnection": "supply_side_tap", "main_breaker_a": 100, "busbar_a": 100}, "supply-side tap"),
        ({"interconnection": "load_side_breaker", "main_breaker_a": None, "busbar_a": 100}, "not surveyed"),
        ({"interconnection": "load_side_breaker", "main_breaker_a": 100, "busbar_a": 100}, "no grid-side breaker"),
    ):
        choices = {"ac_grid_breaker_a": None if word.startswith("no grid") else 40, "inverter_units": 1}
        block, warns = poi_busbar_check(svc, choices)
        assert block["checked"] is False and block["ok"] is None and word in block["reason"] and warns == []
