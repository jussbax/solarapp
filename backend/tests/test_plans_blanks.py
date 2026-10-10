"""Round 13 review, finding 5: the last sheet lists every blank line of the set. One collector (reports/plans_blanks.Blanks)
every sheet module appends to whenever it prints a blank line with its reason; the last sheet prints it grouped by sheet,
the signing engineer's own lines (the frame rating, "fed from", the demand load, the branch-circuit figures) under their
own heading. In the reviewer's typed state (the datasheets, the item figures, the service entrance, the roof construction,
the wind inputs, the site outlines and points, the signing engineer's profile) every blank line on sheets 1 to N−1 has its
row on the last sheet: the count of blank lines per page in pdftotext, less the title block's signature line, equals the
"Lines" the last sheet lists for that sheet, and the figures the reviewer named are all there."""
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
from solarapp.reports.plans_blanks import BLANK, Blanks
from solarapp.reports.plans_pdf import build_plans_pdf
from solarapp.schemas import AssessmentDoc
from tests.test_drawings import PILA_DOC
from tests.test_plans_title_block import PEE
from tests.test_survey_fields import CONSTRUCTION, SERVICE, SITE
from tests.test_uplift import WIND

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "datasheets"
FILES = [FIXTURES / f"ALL_{n}_DATA_SHEET.xlsx" for n in ("SOLAR_PANEL", "INVERTER", "BATTERY")]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def _pages(pdf: bytes, layout: bool = True) -> list[str]:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    args = ["pdftotext"] + (["-layout"] if layout else []) + ["-", "-"]
    text = subprocess.run(args, input=pdf, capture_output=True, check=True).stdout.decode()
    return [p for p in text.split("\f") if p.strip()]


def _typed(client: TestClient) -> int:
    """The reviewer's typed state: everything the brief's test inputs supply, none of it shipped by the app."""
    for f in FILES:
        with open(f, "rb") as fh:
            assert client.post("/api/pricing/datasheets", files={"file": (f.name, fh, "application/octet-stream")}).status_code == 200
    assert client.put("/api/pricing/items/FS-INV-008", json={"max_pv_voltage_v": 500, "fault_current_a": 45}).status_code == 200
    assert client.put("/api/pricing/items/IAN-WIR-004", json={"overall_area_mm2": 23.61, "insulation_c": 90}).status_code == 200
    assert client.put("/api/pricing/items/IAN-ENC-011", json={"inner_diameter_mm": 29}).status_code == 200
    assert client.put("/api/pricing/items/IAN-PRT-027", json={"aic_ka": 10}).status_code == 200
    assert client.put("/api/settings", json={"company_name": "Test Solar", **PEE, "pee_firm_address": "Pila, Laguna"}).status_code == 200   # every profile field, so the title block prints no blank
    cfg = client.get("/api/pricing/config").json()
    cfg["mounting"].update({"fastener_pullout_kn": 0.5, "fastener_pullout_source": "test input", "foot_spacing_max_m": 1.2, "foot_spacing_max_source": "test input",
                            "fastener_description": "self-drilling screw (test input)", "kd": 0.85, "kd_source": "test input", "exposure_source": "test input",
                            "wind_zones": {"Laguna": {"zone": "II", "v_kmh": 200, "source": "test input"}}})
    cfg["mounting"]["exposures"]["B"] = {"alpha": 7.0, "zg_m": 365.76}
    assert client.put("/api/pricing/config", json=cfg).status_code == 200
    doc = deepcopy(PILA_DOC)
    doc["service"] = {**deepcopy(SERVICE), "fault_level_ka": 10}
    doc["roof_default"] = deepcopy(CONSTRUCTION)
    doc["wind"] = deepcopy(WIND)
    doc["site"] = deepcopy(SITE)
    doc["faces"][0]["plan_offset_m"] = [0.0, -2.5]
    doc["faces"][1]["plan_offset_m"] = [4.5, 0.0]
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    assert r.json()["results"]["pricing"]["design_blocked"] == []
    return aid


def _listed(last_page_reading: str) -> dict[str, int]:
    """The last sheet's two tables, read in reading order: {"7–8": lines, ...} summed per sheet label."""
    out: dict[str, int] = {}
    for label, n in re.findall(r"^Sheet (\d+(?:–\d+)?)\s*\n\s*(\d+)\s*\n", last_page_reading, flags=re.M):
        out[label] = out.get(label, 0) + int(n)
    return out


def test_every_blank_line_of_the_typed_set_has_its_row_on_the_last_sheet(client):
    aid = _typed(client)
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 200, r.text
    pages, reading = _pages(r.content), _pages(r.content, layout=False)
    assert len(pages) == len(reading) == 11 and pages[-1].strip().startswith("Not yet in this set")
    # the title block's signature line prints two blank lines on every page and is not a figure; the profile is full, so no other title-block blank
    counted = {i + 1: p.count(BLANK) - 2 for i, p in enumerate(pages[:-1])}
    assert all(n >= 0 for n in counted.values()) and sum(counted.values()) > 25
    listed = _listed(reading[-1])
    assert "7–8" in listed   # the schedule's two sheets, listed as one
    expected = {str(i): n for i, n in counted.items() if i not in (7, 8)}
    expected["7–8"] = counted[7] + counted[8]
    assert {k: v for k, v in expected.items() if v} == listed, (expected, listed)
    assert pages[-1].count(BLANK) == 2   # the last sheet itself prints no blank figure
    # the figures the reviewer named as missing from the old list, each with where to type it
    flat = " ".join(reading[-1].split())
    for text in ("Inverter FS-INV-008: certificate", "Inverter FS-INV-008: AC input rating", "Inverter FS-INV-008: MPPT window (low)",
                 "interrupting rating (AIC) of IAN-PRT-009", "interrupting rating (AIC) of IAN-PRT-003", "the battery's short-circuit trip",
                 "C3: EGC provided", "C, the clearance under the panel (the L-foot height)", "not on the L-foot item (Materials page)",
                 "The signing engineer's lines", "main breaker AF (the frame rating)", "fed from", "demand load (W, VA, A)", "Revisions: the first issue's By"):
        assert text in flat, text
    assert "Single-line diagram (figures blank)" not in flat and "Schedule of loads (service entrance blank)" not in flat


def test_the_collector_groups_by_sheet_and_reason_in_the_sets_order():
    b = Blanks()
    assert b.add("Schedule of loads", "fed from", "the engineer's", engineer=True) == BLANK
    b.add("Cover and general notes", "certificate", "none on file")
    b.add("Cover and general notes", "AC input rating", "not on the Materials page")
    b.add("Cover and general notes", "MPPT window (low)", "not on the Materials page", n=2)
    b.add("Schedule of loads", "wire, conduit and OCPD", "the engineer's", engineer=True, n=3)
    assert b.count("Cover and general notes") == 4 and b.count("Schedule of loads") == 4 and b.count("Design analysis") == 0
    groups = b.grouped(["Cover and general notes", "Single-line diagram", "Schedule of loads"])
    assert [(g["no"], g["engineer"], g["n"]) for g in groups] == [(1, False, 1), (1, False, 3), (3, True, 4)]
    assert groups[1]["items"] == {"AC input rating": 1, "MPPT window (low)": 2} and groups[2]["items"] == {"fed from": 1, "wire, conduit and OCPD": 3}


def test_the_builder_takes_a_collector_and_the_seed_alone_stays_one_last_sheet():
    """Outside the API: the builder records into the collector it is given; with nothing typed the set is mostly blank and the
    last sheet still fits one sheet (the block shrinks to the frame, as the cover's index does)."""
    doc = AssessmentDoc.model_validate(PILA_DOC)
    results = {"computed_at": "2026-10-09T06:05:00+00:00", "geometry": [], "pricing": {"available": True, "lines": [], "choices": {}, "totals": {"kwp": 0}},
               "sizing": {"kind": "net_metering", "panels": 0, "kwp": 0}, "audit": {"appliances": []}}
    blanks = Blanks()
    pdf = build_plans_pdf(doc, results, {"company_name": "", "pee_name": "", "pee_license": ""}, items={}, config={}, project_no="P-2026-0001", blanks=blanks)
    pages = _pages(pdf)
    assert len(pages) == 8 and pages[-1].strip().startswith("Not yet in this set") and "Blank lines in this set, by sheet" in pages[-1]
    assert blanks.count("Single-line diagram") >= 10 and blanks.count("Schedule of loads") >= 1 and blanks.count("Cover and general notes") >= 5
    assert "Sheet 3" in pages[-1] and "Blank lines in this set, by sheet" in pages[-1]   # the diagram is sheet 3 of this set, its blanks listed under that number
