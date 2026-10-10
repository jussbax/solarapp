"""The plans for the PEE (round 4): the A3 drawing set builds for the reference record, one sheet per roof face with
panels between the cover and the schedules, the title block on every sheet with the company, the project, the
sheet number and the PEE's signature block (blank lines when the profile has none), and the same refusals as the
proposal on stale, design-blocked or unpriced results, while test weather does not stop it (an internal document)."""
import re
import shutil
import subprocess
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.reports.plans_pdf import BLANK, build_plans_pdf
from solarapp.schemas import AssessmentDoc
from tests.test_drawings import PILA_DOC

STALE = "Inputs changed since the last calculation. Calculate again first."


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)  # Laguna
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def _computed(client: TestClient, doc: dict) -> dict:
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    return r.json()


def _pdf_text(pdf: bytes) -> str:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    return subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode()


def _pages(text: str) -> list[str]:
    return [p for p in text.split("\f") if p.strip()]


def test_plans_build_for_the_reference_record_on_a3(client):
    out = _computed(client, PILA_DOC)
    aid, res = out["id"], out["results"]
    assert res["pricing"]["available"] and res["pricing"]["design_blocked"] == []
    client.put("/api/settings", json={"company_name": "Test Solar", "address": "Pila, Laguna", "pee_name": "Juan dela Cruz", "pee_license": "0012345"})
    r = client.get(f"/api/assessments/{aid}/plans.pdf")   # test weather does not stop an internal document
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith('attachment; filename="plans-Maria_Santos.pdf"')
    pages = _pages(_pdf_text(r.content))
    faces_with_panels = [g for g in res["geometry"] if g["panels"]]
    assert len(faces_with_panels) == 2
    # cover, the vicinity map and site plan (round 13, item 4), one layout per face with panels, the mounting detail (item 3), the schedule, the design analysis (item 2), the last sheet
    assert len(pages) == 2 + len(faces_with_panels) + 4 == 8
    # the title block on every sheet: company, project, sheet n of N, the sheet size and the signature block from the profile
    for i, page in enumerate(pages, start=1):
        assert "Test Solar" in page and "PV system plans: Maria Santos" in page and f"Project P-" in page
        assert f"Sheet {i} of 8" in page and "A3 landscape, 420 × 297 mm" in page
        # round 13: the signature block's six lines from the profile; a field the profile does not hold is a blank line, never invented
        assert "Signed and sealed by the Professional Electrical Engineer" in page and "Juan dela Cruz, PEE" in page and "PRC No. 0012345" in page
        assert "PTR No. " + BLANK in page and "TIN " + BLANK in page
        assert "Owner: Maria Santos" in page and "Rev. 0: first issue" in page   # the owner and the revision line on every sheet
    cover, site, main, kitchen, mounting, schedule, analysis, last = pages
    assert "Mounting detail and uplift check" in mounting and "Detail A: rib-type metal sheet" in mounting and "Detail B: corrugated sheet" in mounting
    assert "NOT CHECKED" in mounting and "Scale 1:5 on A3" in mounting   # nothing typed: the chain prints its blanks, never a figure
    assert "Cover and general notes" in cover and "General notes" in cover and "Sheets in this set" in cover
    assert "Vicinity map and site plan" in site and "Site plan" in site   # the sheet after the cover; its own tests are in test_plans_site.py
    assert "Hybrid: grid-interactive with a battery" in cover and "Main roof (south)" in cover and "Kitchen roof (east)" in cover
    assert "to be completed by the signing engineer" in cover and "PEC" not in cover   # no clause numbers, no standards named by the app
    assert "Array layout: Main roof (south)" in main and re.search(r"Scale 1:\d+ on A3", main) and "Eave (lower edge)" in main
    assert "9.00 m" in main and "5.00 m" in main          # the eave and the slope as dimension lines
    assert "Strings on this face" in main and re.search(r"S1\s+panels 1–\d+", main)
    assert "Array layout: Kitchen roof (east)" in kitchen and "ridge 3.00 m" in kitchen and "hip (trapezoid)" in kitchen
    assert "Hatched" in kitchen and "Wall on the left side" in kitchen
    assert "Equipment and circuit schedule" in schedule and "DC side" in schedule and "AC side" in schedule
    assert "Grounding and bonding" in schedule and "Voltage drop" in schedule and "Battery circuit" in schedule
    assert "Grid-side" in schedule and "Inverter output" in schedule   # pdftotext wraps the narrow cells
    assert "Design analysis: conductor derating" in analysis and "Sheet 7 of 8" in analysis   # test_design_analysis.py reads the sheet itself
    assert "Not yet in this set, and why" in last and "Single-line diagram" in last and "String table" in last
    assert "Schedule of loads: the energy audit's figures" in last and "Refrigerator" in last and "Total" in last
    # the drop figures are the BOQ's
    ch = res["pricing"]["choices"]
    assert f"{ch['pv_drop'] * 100:.1f} %" in schedule and f"{ch['ac_drop'] * 100:.1f} %" in schedule


def test_plans_print_blank_lines_where_the_profile_is_empty():
    """The builder needs no server: the document, the results, the profile. An empty profile and an empty BOM print
    blank lines, never a guess; no face with panels means no layout sheet."""
    doc = AssessmentDoc.model_validate(PILA_DOC)
    results = {"computed_at": "2026-10-09T06:05:00+00:00", "geometry": [], "pricing": {"available": True, "lines": [], "choices": {}, "totals": {"kwp": 0}},
               "sizing": {"kind": "net_metering", "panels": 0, "kwp": 0}, "audit": {"appliances": []}}
    pdf = build_plans_pdf(doc, results, {"company_name": "", "pee_name": "", "pee_license": ""}, items={}, config={}, project_no="P-2026-0001")
    pages = _pages(_pdf_text(pdf))
    assert len(pages) == 6   # cover, the site sheet, the mounting detail (the standard details draw without a check), the schedule, the design analysis (every row a blank line: no circuit records), the last sheet
    assert BLANK + ", PEE" in pages[0] and "PRC No. " + BLANK in pages[0] and "Sheet 1 of 6" in pages[0]
    assert "The uplift check is not in these results" in pages[2]
    assert "no circuits" in pages[4] and "calculate again" in pages[4]
    assert "Rev. 0" in pages[0] and "Rev. 0: first issue" not in pages[0]   # no issue date outside the API: the title block reads "Rev. 0" as before the log existed
    assert "The energy audit has no appliances yet" in pages[-1]


def test_plans_are_refused_like_the_proposal(client):
    out = _computed(client, PILA_DOC)
    aid, doc = out["id"], out["doc"]
    # the one stale rule
    doc["notes"] = "edited after the calculation"
    assert client.put(f"/api/assessments/{aid}", json=doc).json()["results_stale"] is True
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 409 and r.json()["detail"] == STALE
    assert client.post(f"/api/assessments/{aid}/compute").status_code == 200
    assert client.get(f"/api/assessments/{aid}/plans.pdf").status_code == 200
    # a design the hard warnings block (the battery bank below the inverter's current) is refused with the reason
    need = float(out["results"]["sizing"]["battery"]["installed_kwh"])
    code = "BC-BAT-003" if need <= 10.24 else "BC-BAT-004" if need <= 15.36 else None
    if code is not None:
        doc = client.get(f"/api/assessments/{aid}").json()["doc"]
        doc["pricing"] = {"battery_code": code}
        res = client.post(f"/api/assessments/{aid}/compute", json=doc).json()["results"]
        assert res["pricing"]["design_blocked"] == ["battery_current"]
        r = client.get(f"/api/assessments/{aid}/plans.pdf")
        assert r.status_code == 409 and r.json()["detail"].startswith("design_blocked: ")
    # a record that was never calculated, and one without pricing
    fresh = client.post("/api/assessments", json=PILA_DOC).json()["id"]
    assert client.get(f"/api/assessments/{fresh}/plans.pdf").json()["detail"] == "Calculate first."
    unpriced = deepcopy(PILA_DOC)
    unpriced["audit"] = {"appliances": [], "bills": [], "reconcile": True, "system": {"kind": "combination"}}
    u = _computed(client, unpriced)["id"]
    assert client.get(f"/api/assessments/{u}/plans.pdf").status_code == 409
