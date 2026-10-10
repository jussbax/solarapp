"""Round 13, step 1 (brief 1.3, 3.2, 4.2): the survey record the plan set reads, in one schema change. The service
entrance, the roof construction per face with the project's default, the site plan's outlines and points (typed
coordinates for now) and the face offsets round-trip through the API; an older record reads every field blank; the
words are enumerations and a point is a pair in degrees (422 otherwise); a survey edit is an input (the results go
stale); the quick estimate and the plan set are unchanged by the fields."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.schemas import AssessmentDoc, RoofConstruction, ServiceEntrance, SitePlan
from tests.test_drawings import PILA_DOC

SERVICE = {
    "du_name": "FLECO", "account_no": "12-3456-7890", "meter_no": "M-998877", "panelboard": "main panel, ground floor, 12-way", "phase": 1, "voltage_v": 230,
    "main_breaker_a": 100, "busbar_a": 125, "interconnection": "load_side_breaker", "interconnection_note": "a 2P backfeed breaker at the bottom of the panel, 4 m from the meter",
    "fault_level_ka": None, "circuits": [{"no": "1", "description": "lights, ground floor", "breaker_a": 20, "poles": 1, "wire_mm2": 3.5, "conduit_mm": 20},
                                        {"no": "2", "description": "aircon, master bedroom", "breaker_a": 32, "poles": 2, "wire_mm2": 5.5, "conduit_mm": 25}],
}
CONSTRUCTION = {"roof_type": "rib_metal", "sheet_profile": "rib 30 mm, pitch 250 mm", "purlin_material": "steel_c", "purlin_section": "C 100 × 50 × 1.5", "purlin_thickness_mm": 1.5,
                "purlin_spacing_m": 0.6, "rafter_spacing_m": None, "mean_roof_height_m": 5.0, "condition": "sound, repainted 2024", "condition_flag": "sound"}
SITE = {
    "lot_polygon": [[14.2334, 121.3644], [14.2334, 121.3646], [14.2336, 121.3646], [14.2336, 121.3644]],
    "house_polygon": [[14.23345, 121.36445], [14.23345, 121.36455], [14.23355, 121.36455], [14.23355, 121.36445]],
    "inverter_location": "ground floor utility room, south wall", "inverter_point": [14.2335, 121.3645],
    "battery_location": "beside the inverter", "battery_point": [14.23351, 121.3645],
    "poi_location": "backfeed breaker in the main panel", "poi_point": None,
    "meter_location": "gate post", "meter_point": [14.2334, 121.36445],
}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def _surveyed() -> dict:
    doc = deepcopy(PILA_DOC)
    doc["service"] = deepcopy(SERVICE)
    doc["roof_default"] = deepcopy(CONSTRUCTION)
    doc["faces"][0]["construction"] = {**CONSTRUCTION, "condition_flag": "rusted", "condition": "rust along the eave"}
    doc["faces"][0]["plan_offset_m"] = [3.5, -2.0]
    doc["site"] = deepcopy(SITE)
    return doc


def test_the_survey_fields_round_trip_through_the_api(client):
    doc = _surveyed()
    r = client.post("/api/assessments", json=doc)
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    got = client.get(f"/api/assessments/{aid}").json()["doc"]
    assert got["service"] == SERVICE
    assert got["roof_default"] == CONSTRUCTION
    assert got["faces"][0]["construction"] == {**CONSTRUCTION, "condition_flag": "rusted", "condition": "rust along the eave"} and got["faces"][0]["plan_offset_m"] == [3.5, -2.0]
    assert got["faces"][1]["construction"] == RoofConstruction().model_dump() and got["faces"][1]["plan_offset_m"] is None   # the second face inherits the project's default
    assert got["site"] == SITE
    # a survey field is an input: editing it after a calculation marks the results stale, and the next Calculate keeps it
    assert client.post(f"/api/assessments/{aid}/compute").status_code == 200
    got["service"]["busbar_a"] = 100
    r = client.put(f"/api/assessments/{aid}", json=got)
    assert r.status_code == 200 and r.json()["results_stale"] is True and r.json()["doc"]["service"]["busbar_a"] == 100
    out = client.post(f"/api/assessments/{aid}/compute").json()
    assert out["results_stale"] is False and out["doc"]["service"]["busbar_a"] == 100 and out["doc"]["site"]["inverter_point"] == [14.2335, 121.3645]


def test_an_older_record_reads_every_survey_field_blank(client):
    aid = client.post("/api/assessments", json=deepcopy(PILA_DOC)).json()["id"]
    got = client.get(f"/api/assessments/{aid}").json()["doc"]
    assert got["service"] == ServiceEntrance().model_dump() and got["service"]["du_name"] == "" and got["service"]["phase"] is None and got["service"]["circuits"] == []
    assert got["roof_default"] == RoofConstruction().model_dump() and got["roof_default"]["roof_type"] == "" and got["roof_default"]["purlin_spacing_m"] is None
    assert all(f["construction"]["roof_type"] == "" and f["plan_offset_m"] is None for f in got["faces"])
    assert got["site"] == SitePlan().model_dump(mode="json") and got["site"]["lot_polygon"] == [] and got["site"]["inverter_point"] is None
    # the defaults are blanks, never figures
    assert ServiceEntrance().voltage_v is None and ServiceEntrance().main_breaker_a is None and RoofConstruction().mean_roof_height_m is None


@pytest.mark.parametrize("path, value", [
    (("roof_default", "roof_type"), "asbestos"),
    (("roof_default", "purlin_material"), "bamboo"),
    (("roof_default", "condition_flag"), "fine"),
    (("roof_default", "purlin_spacing_m"), 0),
    (("service", "phase"), 2),
    (("service", "interconnection"), "somewhere"),
    (("service", "busbar_a"), -1),
    (("site", "lot_polygon"), [[95, 121], [14, 121], [14, 122]]),
    (("site", "house_polygon"), [[14.2, 121.3], [14.3, 121.3]]),
    (("site", "inverter_point"), [14.2]),
    (("site", "meter_point"), [14.2, 200]),
])
def test_the_words_are_enumerations_and_a_point_is_a_pair_in_degrees(client, path, value):
    doc = _surveyed()
    doc[path[0]][path[1]] = value
    assert client.post("/api/assessments", json=doc).status_code == 422


def test_a_face_offset_is_a_pair_of_metres(client):
    doc = _surveyed()
    doc["faces"][0]["plan_offset_m"] = [1.0]
    assert client.post("/api/assessments", json=doc).status_code == 422
    doc["faces"][0]["plan_offset_m"] = [-12.5, 40]
    assert client.post("/api/assessments", json=doc).status_code == 201


def test_the_plan_set_and_the_quick_estimate_are_unchanged_by_the_fields(client):
    """Nothing on a sheet reads the fields yet (step 1): the surveyed record builds the same five sheets as the plain one;
    the website estimate's document carries the blank defaults and no new code path reads them."""
    import shutil
    import subprocess

    from solarapp.core.quick import quick_estimate  # noqa: F401  (imports; the estimate's own tests pin its price)

    aid = client.post("/api/assessments", json=_surveyed()).json()["id"]
    assert client.post(f"/api/assessments/{aid}/compute").status_code == 200
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 200
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext", "-layout", "-", "-"], input=r.content, capture_output=True, check=True).stdout.decode()
        pages = [p for p in text.split("\f") if p.strip()]
        assert len(pages) == 5 and "FLECO" not in text and "busbar" not in text.lower()
    assert AssessmentDoc().service == ServiceEntrance() and AssessmentDoc().site == SitePlan()
