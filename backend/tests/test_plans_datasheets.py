"""Round 12 (brief 4.2): with the datasheets on file and a maximum PV voltage on the inverter, the plan set prints
the string table and the equipment schedule rows from the datasheet figures, each saying which file they came
from; the "waits on the datasheets" entry for the string table drops off the last sheet, and the rest of the set
is unchanged. test_plans.py keeps pinning the set without them."""
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
from solarapp.reports.plans_pdf import BLANK
from tests.test_drawings import PILA_DOC

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
        for f in FILES:
            with open(f, "rb") as fh:
                assert c.post("/api/pricing/datasheets", files={"file": (f.name, fh, "application/octet-stream")}).status_code == 200
        # no sheet carries a maximum PV voltage (brief 6.6): the owner types the eco-hybrid's on the Materials page for this test
        assert c.put("/api/pricing/items/FS-INV-008", json={"max_pv_voltage_v": 500}).status_code == 200
        yield c


def _pdf_text(pdf: bytes) -> str:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    return subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode()


def _pages(text: str) -> list[str]:
    return [p for p in text.split("\f") if p.strip()]


def test_the_plans_print_the_string_table_and_the_datasheet_figures(client):
    aid = client.post("/api/assessments", json=deepcopy(PILA_DOC)).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    sdn = res["pricing"]["choices"]["string_design"]
    assert sdn["available"] and sdn["v_limit_v"] == 500 and sdn["n_max"] >= 8 and sdn["coefficients"]["voc"]["default"]
    assert res["pricing"]["choices"]["battery_current_source"] == "datasheet" and res["pricing"]["choices"]["battery_current_a"] == 139
    codes = {w["code"] for w in res["pricing"]["warnings"]}
    assert "temp_coeff_default" in codes and "string_rule_fallback" not in codes and res["pricing"]["design_blocked"] == []
    pages = _pages(_pdf_text(client.get(f"/api/assessments/{aid}/plans.pdf").content))
    cover, last = pages[0], pages[-1]
    # the schedule's two columns no longer fit one A3 with the string table and the battery rows: it takes two sheets, named on the cover
    sched_pages = [p for p in pages if "Equipment and circuit schedule" in p.split("\n", 3)[0:3].__str__()]
    assert len(sched_pages) == 2 and "Equipment and circuit schedule (continued)" in cover and f"Sheet {len(pages)} of {len(pages)}" in last
    schedule = "\n".join(sched_pages)
    flat = lambda s: " ".join(s.split())  # noqa: E731
    # the cover's models table: the figures with their file and date, the string design on the datasheet figures
    assert "ALL_SOLAR_PANEL_DATA_SHEET.xlsx" in flat(cover) and "max system voltage 1,500 V" in flat(cover)
    assert "string design on datasheet figures from ALL_SOLAR_PANEL_DATA_SHEET.xlsx" in flat(cover)
    assert "battery port LV" in flat(cover) and "139 A discharge" in flat(cover) and "135 A charge" in flat(cover)
    # the schedule: the string table, the two Isc lines, the battery circuit on the larger of the two figures, the charge setting, the voltage match
    assert "String table" in schedule and re.search(r"S1\s+\d+\s+[\d.,]+ V", schedule) and "Margin" in schedule
    assert "PV circuit current" in schedule and "1.25 × Isc" in flat(schedule) and "conductor and OCPD" in flat(schedule) and "× Isc" in flat(schedule)
    # pdftotext interleaves the two columns line by line, so the checks are on words that sit on one line of a cell
    assert "larger of discharge 139 A" in flat(schedule) and "charge 135 A" in flat(schedule)
    assert "Charge current" in flat(schedule) and "Voltage match" in flat(schedule) and "holds" in flat(schedule)
    assert "default, an" in flat(schedule) and "assumption" in flat(schedule) and "T_cold" in flat(schedule)
    assert "Rev. 0" in cover
    # the last sheet: the string table entry is gone, the single-line diagram names only what is still missing
    assert "Not yet in this set, and why" in last and "String table (Voc at the coldest cell" not in last
    # pdftotext breaks the cell at "temperature / coefficient", so the phrases are the ones that sit on one line
    assert "Single-line diagram" in last and "the panel's temperature" in flat(last) and "coefficient of Voc; the inverter's MPPT window (low), MPPT window (high)" in flat(last)
    assert "panel's the" not in flat(last) and "inverter's the" not in flat(last)   # the wording slip of the review's finding 8
    assert pages[-2].strip().startswith("Schedule of loads") and "Refrigerator" in pages[-2]   # the permit's format, its own sheet (round 13)
    # a figure the app does not hold is a blank line, never a guess: the series fuse rating is not on file
    assert "series fuse rating" in flat(schedule) and BLANK in schedule
