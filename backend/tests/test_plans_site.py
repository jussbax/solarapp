"""Round 13, item 4 (docs/audits/round-13/engineer-brief.md 4.2 and 4.3): the site plan sheet. The faces of the Pila sample
print in true orientation (the south face's eave at the bottom, the east face's eave at the right) with the slope
foreshortened by cos(tilt); a typed lot prints its edge lengths and the scale 1:100; the house and the setbacks; the
typed offsets place the faces around the pin; every missing input prints its reason; the sheet sits after the cover."""
import math
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.reports.plans_site import BOX_H_MM, BOX_W_MM, face_axes, face_plan, fit_site_scale, from_metres, setbacks, site_plan_drawing, to_metres
from solarapp.schemas import AssessmentDoc
from tests.test_drawings import PILA_DOC
from tests.test_plans import _pages, _pdf_text

LAT0, LON0 = PILA_DOC["lat"], PILA_DOC["lon"]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def _corners(pts: list[tuple[float, float]]) -> list[list[float]]:
    return [list(from_metres(e, n, LAT0, LON0)) for e, n in pts]


LOT = _corners([(-7.5, -6), (7.5, -6), (7.5, 6), (-7.5, 6)])            # 15 × 12 m around the pin
HOUSE = _corners([(-4.5, -2.5), (4.5, -2.5), (4.5, 2.5), (-4.5, 2.5)])   # 9 × 5 m, centred


def _computed(client: TestClient, doc: dict) -> dict:
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    return r.json()


def _sheet_pages(client: TestClient, aid: int) -> list[str]:
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 200, r.text
    return _pages(_pdf_text(r.content))


def test_the_projection_round_trips_and_the_axes_follow_the_azimuth():
    e, n = to_metres(*from_metres(15.0, -12.0, LAT0, LON0), LAT0, LON0)
    assert abs(e - 15.0) < 1e-6 and abs(n + 12.0) < 1e-6
    # a south face: the eave runs west to east, the ridge lies north; an east face: the eave runs north, the ridge lies west
    (ex, ey) = face_axes(180)
    assert abs(ex[0] - 1) < 1e-9 and abs(ex[1]) < 1e-9 and abs(ey[0]) < 1e-9 and abs(ey[1] - 1) < 1e-9
    (ex, ey) = face_axes(90)
    assert abs(ex[0]) < 1e-9 and abs(ex[1] - 1) < 1e-9 and abs(ey[0] + 1) < 1e-9 and abs(ey[1]) < 1e-9


def test_the_sample_faces_print_in_true_orientation(client):
    out = _computed(client, deepcopy(PILA_DOC))
    aid, geometry = out["id"], out["results"]["geometry"]
    south, east = geometry
    s = face_plan(south, (0.0, 0.0))
    # the south face: 9 × 5 m at 18°: the eave at the bottom (its two ends share the outline's lowest north), 4.76 m deep in plan
    assert abs(s["depth_m"] - 5 * math.cos(math.radians(18))) < 1e-9 and round(s["depth_m"], 2) == 4.76
    assert abs(s["eave"][0][1] - s["eave"][1][1]) < 1e-9 and abs(s["eave"][0][1] - s["bbox"][1]) < 1e-9
    assert abs((s["eave"][0][0] + s["eave"][1][0]) / 2) < 1e-9 and abs(s["eave"][0][1]) < 1e-9      # the eave's midpoint is the origin
    assert abs(s["bbox"][2] - s["bbox"][0] - 9.0) < 1e-9 and abs(s["bbox"][3] - s["bbox"][1] - 4.76) < 0.01
    # the east hip face: 7 × 4 m at 15°: the eave at the right (its ends share the outline's greatest east), 3.86 m deep, the ridge to the west
    e = face_plan(east, (0.0, 0.0))
    assert round(e["depth_m"], 2) == 3.86
    assert abs(e["eave"][0][0] - e["eave"][1][0]) < 1e-9 and abs(e["eave"][0][0] - e["bbox"][2]) < 1e-9
    assert abs(e["bbox"][3] - e["bbox"][1] - 7.0) < 1e-9 and abs(e["bbox"][2] - e["bbox"][0] - 3.86) < 0.01
    assert s["n_panels"] == south["used"] and all(len(q) == 4 for q in s["panels"])
    # the sheet, with nothing typed: the faces side by side, every missing input with its reason
    doc = AssessmentDoc.model_validate(out["doc"])
    drawing, scale_n, notes = site_plan_drawing(doc, geometry)
    assert abs(drawing.width - BOX_W_MM * 72 / 25.4) < 1e-6 and abs(drawing.height - BOX_H_MM * 72 / 25.4) < 1e-6
    assert any(n.startswith("relative positions not surveyed") for n in notes) and "property line: not surveyed" in notes and "house outline: not surveyed" in notes
    assert any("not chosen (Site step)" in n for n in notes)
    pages = _sheet_pages(client, aid)
    cover, sheet = " ".join(pages[0].split()), " ".join(pages[1].split())
    assert "Sheet 2 Vicinity map and site plan" in cover and "Vicinity map and site plan" not in " ".join(pages[-1].split()).split("Not yet in this set, and why")[1].split("Schedule of loads")[0]
    assert "Vicinity map and site plan" in sheet and "Sheet 2 of" in sheet and "true north up" in sheet
    assert "4.76 m" in sheet and "3.86 m" in sheet and "9.00 m" in sheet and "7.00 m" in sheet
    assert "Main roof (south)" in sheet and "Kitchen roof (east)" in sheet and "6 panels" in sheet
    assert "relative positions not surveyed" in sheet and "property line: not surveyed" in sheet and "not chosen (Site step)" in sheet
    assert "vicinity map: not fetched" in sheet and "pin 14.23350, 121.36450" in sheet


def test_a_typed_lot_prints_its_edges_the_house_the_setbacks_and_the_scale(client):
    doc = deepcopy(PILA_DOC)
    doc["site"] = {"lot_polygon": LOT, "house_polygon": HOUSE, "inverter_location": "utility room", "inverter_point": list(from_metres(3.0, -2.0, LAT0, LON0)),
                   "battery_location": "beside the inverter", "battery_point": list(from_metres(3.8, -2.0, LAT0, LON0)),
                   "meter_location": "gate post", "meter_point": list(from_metres(-6.5, -5.5, LAT0, LON0))}
    out = _computed(client, doc)
    aid = out["id"]
    # the scale: 15 m is 150 mm at 1:100 and fits the box with the dimension margins; 1:75 would need 200 mm
    assert fit_site_scale(15.0, 12.0) == 100 and fit_site_scale(11.0, 10.0) == 75 and fit_site_scale(2.0, 2.0) == 20 and fit_site_scale(400.0, 10.0) == 500
    parsed = AssessmentDoc.model_validate(out["doc"])
    _drawing, scale_n, notes = site_plan_drawing(parsed, out["results"]["geometry"])
    assert scale_n == 100 and "property line: not surveyed" not in notes and any("verify the zoning setback" in n for n in notes)
    assert any("point of interconnection location: not chosen" in n for n in notes)
    # the setbacks from each house wall straight out to the property line
    lot_m = [to_metres(la, lo, LAT0, LON0) for la, lo in LOT]
    house_m = [to_metres(la, lo, LAT0, LON0) for la, lo in HOUSE]
    assert sorted(round(d, 2) for _, _, d in setbacks(house_m, lot_m)) == [3.0, 3.0, 3.5, 3.5]
    pages = _sheet_pages(client, aid)
    sheet = " ".join(pages[1].split())
    assert sheet.count("15.00 m") == 2 and sheet.count("12.00 m") == 2       # the four edge lengths
    assert "house 9.00 m" in sheet and "house 5.00 m" in sheet
    assert "Scale 1:100 on A3 landscape" in sheet and "scale 1:100" in sheet
    assert "Inverter: utility room" in sheet and "Battery: beside the inverter" in sheet and "Meter: gate post" in sheet
    assert "POI" not in sheet.split("Site plan")[1].split("setback")[0] or "point of interconnection location: not chosen" in sheet
    assert "verify the zoning setback" in sheet


def test_typed_offsets_place_the_faces_around_the_pin(client):
    doc = deepcopy(PILA_DOC)
    doc["faces"][0]["plan_offset_m"] = [3.5, -2.0]
    doc["faces"][1]["plan_offset_m"] = [8.5, 0.0]
    out = _computed(client, doc)
    parsed = AssessmentDoc.model_validate(out["doc"])
    south = face_plan(out["results"]["geometry"][0], (3.5, -2.0))
    mid = ((south["eave"][0][0] + south["eave"][1][0]) / 2, (south["eave"][0][1] + south["eave"][1][1]) / 2)
    assert abs(mid[0] - 3.5) < 1e-9 and abs(mid[1] + 2.0) < 1e-9
    _drawing, _scale, notes = site_plan_drawing(parsed, out["results"]["geometry"])
    assert not any("relative positions" in n for n in notes)
    sheet = " ".join(_sheet_pages(client, out["id"])[1].split())
    assert "relative positions not surveyed" not in sheet and "pin" in sheet
    # one face placed, one not: the loose one goes below the site with the note naming it
    doc["faces"][1]["plan_offset_m"] = None
    out = _computed(client, doc)
    _drawing, _scale, notes = site_plan_drawing(AssessmentDoc.model_validate(out["doc"]), out["results"]["geometry"])
    assert any("side by side below the site: Kitchen roof (east)" in n for n in notes)
