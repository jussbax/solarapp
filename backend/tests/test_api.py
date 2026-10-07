import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.5, 14.75, 120.75, 121.0), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


DOC = {
    "customer_name": "Juan Dela Cruz", "address": "Quezon City", "lat": 14.65, "lon": 121.03,
    "faces": [
        {"id": "f1", "name": "Front", "length_m": 10.1, "width_m": 6.4, "tilt_deg": 15, "azimuth_deg": 180},
        {"id": "f2", "name": "Back", "length_m": 10.1, "width_m": 6.4, "tilt_deg": 15, "azimuth_deg": 0},
    ],
    "panels": [
        {"id": "p1", "name": "550W", "watt_peak": 550, "length_m": 2.278, "width_m": 1.134},
        {"id": "p2", "name": "450W", "watt_peak": 450, "length_m": 2.094, "width_m": 1.038},
    ],
    "reading_sets": [
        {"id": "s1", "face_id": "f1", "label": "Front", "measured_at": "2026-03-10T11:30:00", "ambient_temp_c": 32, "sky_condition": "clear",
         "readings": [{"irradiance_wm2": 905, "power_w": 36.2, "module_temp_c": 58}, {"irradiance_wm2": 890, "power_w": 35.6, "module_temp_c": 58}, {"irradiance_wm2": 915, "power_w": 36.8, "module_temp_c": 59}]},
        {"id": "s2", "face_id": "f2", "label": "Back", "measured_at": "2026-03-10T11:45:00", "sky_condition": "clear",
         "readings": [{"irradiance_wm2": 870, "power_w": 33.0, "module_temp_c": 57}, {"irradiance_wm2": 860, "power_w": 32.6, "module_temp_c": 57}, {"irradiance_wm2": 880, "power_w": 33.4, "module_temp_c": 58}]},
    ],
}


def test_requires_login(client):
    assert client.get("/api/assessments").status_code == 401


def test_login_and_flow(client):
    assert client.post("/api/auth/login", json={"username": "u", "password": "x"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": "u", "password": "p"})
    assert r.status_code == 200
    assert client.get("/api/auth/me").json()["signed_in"]

    status = client.get("/api/data/status").json()
    assert status["pvgis"]["available"] and status["pvgis"]["synthetic"]
    cell = client.get("/api/data/cell", params={"lat": 14.65, "lon": 121.03}).json()
    assert cell["distance_km"] < 40

    r = client.post("/api/assessments", json=DOC)
    assert r.status_code == 201, r.text
    aid = r.json()["id"]

    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    assert res["k"]["selected_set_index"] == 0  # front set has the higher k_site
    assert res["k"]["thermal_kind"] == "site_rise"
    assert res["production"]["total_panels"] > 0
    assert res["production"]["annual_kwh"] > 0
    assert res["panels"][0]["best"] is True  # 550 W gives more kWp
    assert res["best_panel"]["id"] == "p1" and res["best_panel"]["count"] == res["production"]["total_panels"]
    assert abs(res["comparison"]["deviation_pct"]) < 60
    assert res["nasa_reference"] is not None
    # set 2 has no ambient -> estimated from the dataset
    assert res["k"]["sets"][1]["ambient_source"] == "estimated"
    assert any(w["code"] == "synthetic_data" for w in res["warnings"])

    # customer PDF refused on synthetic data
    assert client.get(f"/api/assessments/{aid}/report.pdf").status_code == 409

    # editing marks results stale
    doc = dict(DOC)
    doc["customer_name"] = "Edited"
    r = client.put(f"/api/assessments/{aid}", json=doc)
    assert r.json()["results_stale"] is True
    assert client.get("/api/assessments").json()[0]["customer_name"] == "Edited"

    s = client.get("/api/settings").json()
    assert "company_name" in s

    # no readings is rejected clearly
    bad = dict(DOC)
    bad["reading_sets"] = []
    r = client.post("/api/assessments", json=bad)
    r = client.post(f"/api/assessments/{r.json()['id']}/compute")
    assert r.status_code == 422

    assert client.delete(f"/api/assessments/{aid}").status_code == 204
    assert client.get(f"/api/assessments/{aid}").status_code == 404


def test_pdf_builds_from_results(client):
    from solarapp.reports.customer_pdf import build_customer_pdf
    from solarapp.schemas import AssessmentDoc

    client.post("/api/auth/login", json={"username": "u", "password": "p"})
    r = client.post("/api/assessments", json=DOC)
    aid = r.json()["id"]
    res = client.post(f"/api/assessments/{aid}/compute").json()
    pdf = build_customer_pdf(AssessmentDoc.model_validate(res["doc"]), res["results"], {"company_name": "Test Solar", "company_contact": "x"})
    assert pdf[:4] == b"%PDF" and len(pdf) > 10000


TANAUAN_AUDIT = {
    "appliances": [
        {"id": "ref", "name": "Refrigerator", "brand": "Samsung", "model": "RT20", "category": "refrigerator", "input_power_w": 150, "quantity": 1, "windows": [{"start": "06:00", "end": "06:00"}]},
        {"id": "ac", "name": "Split inverter AC 2.5HP", "brand": "Carrier", "model": "XP", "category": "aircon_inverter", "input_power_w": 2100, "quantity": 2, "windows": [{"start": "08:00", "end": "01:00"}]},
        {"id": "led", "name": "LED bulb", "category": "lighting", "input_power_w": 9, "quantity": 9, "windows": [{"start": "18:00", "end": "06:00"}]},
        {"id": "wash", "name": "Top load washer", "category": "washing_machine", "input_power_w": 9014, "quantity": 1, "windows": [{"start": "06:00", "end": "07:30", "days": [5, 6]}]},
        {"id": "ev", "name": "EV charger", "category": "ev_charger", "input_power_w": 3500, "status": "future", "windows": [{"start": "22:00", "end": "02:00"}]},
    ],
    "bills": [{"id": "b1", "billing_month": "2026-08", "kwh": 338, "days": 31, "amount_php": 3987.17, "utility": "BATELEC II"}],
    "reconcile": True,
    "system": {"kind": "combination"},
}


def test_audit_and_sizing_flow(client):
    client.post("/api/auth/login", json={"username": "u", "password": "p"})
    cats = client.get("/api/appliances/categories").json()
    assert any(c["id"] == "aircon_inverter" and c["uncertain"] for c in cats)

    doc = dict(DOC)
    doc["audit"] = TANAUAN_AUDIT
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    audit, sizing = res["audit"], res["sizing"]
    assert audit["audit_vs_bill"]["reconciled"]
    assert abs(audit["audit_vs_bill"]["bills"][0]["reconciled_kwh"] - 338) < 0.01
    assert any(w["code"] == "nameplate_out_of_range" for a in audit["appliances"] for w in a["warnings"])
    assert sizing["kind"] == "combination"
    assert sizing["panels"] >= 1 and sizing["inverter"]["size_kw"] in (6.0, 8.0, 10.0, 12.0)
    assert sizing["battery"]["modules"] >= 1
    assert len(sizing["monthly"]) == 12 and "8" in sizing["profiles"]
    # future EV load is included in sizing but not in the bill comparison
    assert audit["future_daily_kwh"] > 0

    # appliances were remembered in the catalogue
    found = client.get("/api/appliances", params={"q": "carrier"}).json()
    assert len(found) == 1 and found[0]["input_power_w"] == 2100 and found[0]["use_count"] == 1
    client.post(f"/api/assessments/{aid}/compute")
    assert client.get("/api/appliances", params={"q": "carrier"}).json()[0]["use_count"] == 2
    # manual add and delete
    new = client.post("/api/appliances", json={"name": "Stand fan", "brand": "Asahi", "category": "fan", "input_power_w": 55}).json()
    assert client.delete(f"/api/appliances/{new['id']}").status_code == 204

    # without appliances the blocks are absent and the roof results unchanged
    doc2 = dict(DOC)
    r = client.post(f"/api/assessments/{aid}/compute", json=doc2)
    assert r.json()["results"]["audit"] is None and r.json()["results"]["sizing"] is None
