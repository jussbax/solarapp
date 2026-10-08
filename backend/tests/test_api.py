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
        {"id": "ac2", "name": "Second split AC", "category": "aircon_inverter", "input_power_w": 2100, "status": "future", "windows": [{"start": "08:00", "end": "01:00"}]},
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
    assert sizing["battery"]["usable_kwh"] > 0 and "modules" not in sizing["battery"]
    assert len(sizing["monthly"]) == 12 and "8" in sizing["profiles"]
    # future EV load is included in sizing but not in the bill comparison
    assert audit["future_daily_kwh"] > 0
    rows = {a["id"]: a for a in audit["appliances"]}
    assert rows["ac2"]["scale_inherited"] is True and rows["ev"]["scale_inherited"] is False
    import json
    json.dumps(res)  # everything stored must be plain JSON

    # appliances were remembered in the catalogue
    found = client.get("/api/appliances", params={"q": "carrier"}).json()
    assert len(found) == 1 and found[0]["input_power_w"] == 2100 and found[0]["use_count"] == 1
    client.post(f"/api/assessments/{aid}/compute")
    assert client.get("/api/appliances", params={"q": "carrier"}).json()[0]["use_count"] == 2
    # manual add and delete
    new = client.post("/api/appliances", json={"name": "Stand fan", "brand": "Asahi", "category": "fan", "input_power_w": 55}).json()
    assert client.delete(f"/api/appliances/{new['id']}").status_code == 204

    # off-grid variant: no import, unserved reported
    d3 = dict(DOC)
    d3["audit"] = dict(TANAUAN_AUDIT, system={"kind": "off_grid"})
    r = client.post(f"/api/assessments/{aid}/compute", json=d3)
    assert r.status_code == 200, r.text
    res3 = r.json()["results"]
    og = res3["sizing"]
    assert og["kind"] == "off_grid" and og["annual_import_kwh"] == 0 and og["offgrid"]["pv_margin"] == 1.25
    assert "unserved_kwh" in og["monthly"][0]
    assert og["inverter"]["peak_load_kw"] == res3["audit"]["peak_kw"]
    pd = res3["audit"]["peak_detail"]
    assert pd["kw"] == res3["audit"]["peak_kw"] and pd["contributors"] and pd["label"] and len(res3["audit"]["hour_table"]) == 24

    # without appliances the blocks are absent and the roof results unchanged
    doc2 = dict(DOC)
    r = client.post(f"/api/assessments/{aid}/compute", json=doc2)
    assert r.json()["results"]["audit"] is None and r.json()["results"]["sizing"] is None


def test_pricing_flow(client):
    client.post("/api/auth/login", json={"username": "u", "password": "p"})
    st = client.get("/api/pricing/status").json()
    assert st["item_count"] == 362 and st["supplier_count"] == 4  # seeded at startup
    items = client.get("/api/pricing/items", params={"q": "585", "category": "Solar Panel"}).json()
    assert items and all(i["category"] == "Solar Panel" for i in items)
    r = client.put("/api/pricing/items/OP-PNL-004", json={"panel_length_m": 2.384, "panel_width_m": 1.134})
    assert r.status_code == 200 and r.json()["panel_length_m"] == 2.384
    cfg = client.get("/api/pricing/config").json()
    assert cfg["roles"]["l_feet_per_rail"] == 3 and cfg["job"]["vat"] == 0.12
    cfg["job_defaults"]["max_days"] = 3
    assert client.put("/api/pricing/config", json=cfg).json()["job_defaults"]["max_days"] == 3

    doc = dict(DOC)
    doc["panels"] = [{"id": "p1", "name": "Blue Carbon 585W", "watt_peak": 585, "length_m": 2.278, "width_m": 1.134, "code": "BC-PNL-001"}]
    doc["audit"] = dict(TANAUAN_AUDIT, system={"kind": "combination"})
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    pr = res["pricing"]
    assert pr["available"], pr
    assert pr["panel"]["code"] == "BC-PNL-001"
    roles = {l["role"] for l in pr["lines"]}
    assert {"panel", "inverter", "battery", "rail", "l_foot", "thhn", "ats"} <= roles
    panel_line = next(l for l in pr["lines"] if l["role"] == "panel")
    assert panel_line["qty"] == res["sizing"]["panels"]
    inv_line = next(l for l in pr["lines"] if l["role"] == "inverter")
    assert inv_line["code"] == "FS-INV-008" and inv_line["rating"] * inv_line["qty"] >= res["sizing"]["inverter"]["required_kw"]
    assert pr["totals"]["contract_rounded"] % 100 == 0 and pr["totals"]["contract_rounded"] > 100000
    secs = [s["key"] for s in pr["customer"]["sections"]]
    assert secs == ["materials", "labor", "equipment", "tax"]
    assert abs(sum(s["amount"] for s in pr["customer"]["sections"]) - pr["customer"]["total"]) < 0.01
    assert pr["pin_distance"]["extra_km"] > 0 and pr["job_inputs"]["extra_km"] == pr["pin_distance"]["extra_km"]
    assert pr["job_inputs"]["max_days"] == 3  # app pricing settings apply
    # quotation PDF
    r = client.get(f"/api/assessments/{aid}/quotation.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert b"landed" not in r.content.lower()
    # manual edit: remove the sealant, add a second ground rod, override extra km
    before = pr["totals"]["contract_rounded"]
    doc2 = r2 = client.get(f"/api/assessments/{aid}").json()["doc"]
    doc2["pricing"] = {"bom_edits": [{"code": "IAN-CSM-001", "qty": 0}], "bom_extra": [{"code": "OP-GND-001", "qty": 1, "note": "second rod"}], "extra_km": 0}
    res2 = client.post(f"/api/assessments/{aid}/compute", json=doc2).json()["results"]["pricing"]
    codes = {l["code"]: l["qty"] for l in res2["lines"]}
    assert "IAN-CSM-001" not in codes and codes["OP-GND-001"] == 2
    assert res2["job_inputs"]["extra_km"] == 0 and res2["totals"]["contract_rounded"] != before
    # an unlinked panel is matched by wattage with a warning; an unknown wattage is not priced
    doc3 = dict(doc2)
    doc3["panels"] = [{"id": "p1", "name": "Some 585W", "watt_peak": 585, "length_m": 2.278, "width_m": 1.134}]
    res3 = client.post(f"/api/assessments/{aid}/compute", json=doc3).json()["results"]["pricing"]
    assert res3["available"] and any(w["code"] == "panel_unlinked" for w in res3["warnings"])
    doc3["panels"] = [{"id": "p1", "name": "Odd 999W", "watt_peak": 999, "length_m": 2.278, "width_m": 1.134}]
    res4 = client.post(f"/api/assessments/{aid}/compute", json=doc3).json()["results"]["pricing"]
    assert not res4["available"]


def test_quick_estimate_and_lead(client):
    # public: no login needed, but synthetic weather data blocks the public estimate
    client.post("/api/auth/logout")
    st = client.get("/api/quick/status").json()
    assert st["data"] and not st["enabled"]
    r = client.post("/api/quick/estimate", json={"goal": "combination", "lat": 14.65, "lon": 121.03, "monthly_kwh": 338, "pattern": "evening"})
    assert r.status_code == 503
    r = client.post("/api/quick/lead", json={"goal": "combination", "lat": 14.65, "lon": 121.03, "monthly_kwh": 338, "pattern": "evening", "name": "Lead Person", "contact": "0917 000 0000", "address": "Tanauan"})
    assert r.status_code == 200 and r.json()["ok"]
    client.post("/api/auth/login", json={"username": "u", "password": "p"})
    leads = [a for a in client.get("/api/assessments").json() if a["stage"] == "lead"]
    assert leads and leads[0]["customer_name"] == "Lead Person"
    doc = client.get(f"/api/assessments/{leads[0]['id']}").json()["doc"]
    assert doc["audit"]["system"]["kind"] == "combination" and doc["audit"]["bills"][0]["kwh"] == 338 and "0917" in doc["notes"]


def test_quick_throttle_tells_browsers_apart_behind_one_address():
    """Two phones on one mobile address get their own allowance; one browser is still capped."""
    from starlette.requests import Request
    from solarapp.api import quick_routes
    from fastapi import HTTPException

    quick_routes._hits.clear()

    def req(ip: str, visitor: str | None):
        headers = [(b"x-forwarded-for", ip.encode())]
        if visitor:
            headers.append((b"x-visitor", visitor.encode()))
        return Request({"type": "http", "headers": headers, "client": (ip, 1), "method": "POST", "path": "/api/quick/estimate"})

    for _ in range(3):
        quick_routes._throttle(req("10.0.0.1", "phone-a"), 3)
    with pytest.raises(HTTPException) as e:
        quick_routes._throttle(req("10.0.0.1", "phone-a"), 3)
    assert e.value.status_code == 429
    quick_routes._throttle(req("10.0.0.1", "phone-b"), 3)  # a different browser on the same address still works
    # the address-wide cap still holds against a script that rotates tokens
    for i in range(3 * quick_routes.ADDRESS_MULTIPLIER - 4):
        quick_routes._throttle(req("10.0.0.1", f"bot-{i}"), 3)
    with pytest.raises(HTTPException):
        quick_routes._throttle(req("10.0.0.1", "bot-last"), 3)
    quick_routes._hits.clear()


def test_website_lead_carries_source_and_snapshot_and_feeds_the_funnel(client):
    client.post("/api/auth/logout")
    st = client.get("/api/quick/status").json()
    assert st["towns"] and any(t["name"] == "Pila" for t in st["towns"]) and "company_name" in st["profile"] and isinstance(st["warranty"], list)
    body = {
        "goal": "net_metering", "town": "Tanauan", "province": "Batangas", "monthly_php": 4000, "pattern": "evening",
        "name": "Web Visitor", "contact": "0917 555 1234", "address": "", "preferred_time": "Evening",
        "source": {"utm_source": "fb", "utm_campaign": "brownout1", "referrer": "https://facebook.com/", "page": "https://pldevinc.com/estimate?utm_source=fb"},
        "estimate": {"goal": "net_metering", "panels": 6, "kwp": 3.51, "battery_kwh": 0, "price": 172000, "bill_before_monthly": 4000, "bill_after_monthly": 900, "payback_years": 4.2},
    }
    r = client.post("/api/quick/lead", json=body)
    assert r.status_code == 200 and r.json()["ok"]
    # a bot filling the hidden field gets a polite yes and nothing is stored
    assert client.post("/api/quick/lead", json={**body, "name": "Bot", "website": "http://spam"}).json()["ok"]
    client.post("/api/auth/login", json={"username": "u", "password": "p"})
    rows = client.get("/api/assessments").json()
    lead = next(a for a in rows if a["customer_name"] == "Web Visitor")
    assert not any(a["customer_name"] == "Bot" for a in rows)
    assert lead["stage"] == "lead" and lead["lead_contact"] == "0917 555 1234" and lead["lead_source"] == "fb" and lead["lead_estimate"]["price"] == 172000
    assert lead["address"] == "Tanauan, Batangas" and lead["lead_town"] == "Tanauan, Batangas"
    doc = client.get(f"/api/assessments/{lead['id']}").json()["doc"]
    assert doc["lead"]["source"]["utm_campaign"] == "brownout1" and doc["lead"]["consent"] is True
    assert "From the website estimate" in doc["notes"] and "best time: Evening" in doc["notes"] and "a lower bill, no battery" in doc["notes"]
    f = client.get("/api/assessments/funnel?days=7").json()
    assert f["leads"] >= 1 and f["days"] == 7 and "estimates" in f and "signed" in f


def test_profile_settings_round_trip(client):
    r = client.put("/api/settings", json={"phone": "0917 000 1111", "owner_name": "Justin", "warranty_inverter_years": "5", "not_a_field": "x"})
    assert r.status_code == 200
    got = client.get("/api/settings").json()
    assert got["phone"] == "0917 000 1111" and got["owner_name"] == "Justin" and "not_a_field" not in got
    client.post("/api/auth/logout")
    pub = client.get("/api/quick/status").json()["profile"]
    assert pub["phone"] == "0917 000 1111" and "payment_details" not in pub


def test_estimate_only_host_refuses_the_back_office(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from solarapp.config import Settings
    from solarapp.main import create_app
    settings = Settings(data_dir=tmp_path, app_username="u", app_password="p", secret_key="s" * 32, public_host="https://www.pldevinc.com/", public_url="https://solar.pldevinc.com")
    assert settings.public_hosts == ["pldevinc.com", "www.pldevinc.com"] and settings.estimate_url == "https://pldevinc.com"
    with TestClient(create_app(settings)) as c:
        # on the public hostname only the estimate's routes answer
        assert c.get("/api/quick/status", headers={"host": "pldevinc.com"}).status_code == 200
        assert c.get("/api/health", headers={"host": "www.pldevinc.com"}).status_code == 200
        assert c.post("/api/auth/login", json={"username": "u", "password": "p"}, headers={"host": "pldevinc.com"}).status_code == 404
        assert c.get("/api/assessments", headers={"host": "pldevinc.com"}).status_code == 404
        # the back office hostname is untouched
        assert c.post("/api/auth/login", json={"username": "u", "password": "p"}, headers={"host": "solar.pldevinc.com"}).status_code == 200
        assert "estimate_url" in c.get("/api/quick/status").json()


def test_static_route_never_leaves_the_build_folder(tmp_path):
    """A path with parent segments must not read files outside the built frontend."""
    from fastapi.testclient import TestClient
    from solarapp.config import Settings
    from solarapp.main import create_app
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "estimate.html").write_text("<html>estimate</html>")
    (dist / "ok.txt").write_text("served")
    (tmp_path / "secret.txt").write_text("private")
    settings = Settings(data_dir=tmp_path / "data", app_username="u", app_password="p", secret_key="s" * 32, static_dir=dist)
    with TestClient(create_app(settings)) as c:
        assert c.get("/ok.txt").text == "served"
        for probe in ("/..%2fsecret.txt", "/%2e%2e/secret.txt", "/assets/..%2f..%2fsecret.txt", "/a/..%2f..%2fsecret.txt"):
            r = c.get(probe)
            assert "private" not in r.text, probe


def test_public_process_serves_the_site_and_forwards_only_the_estimate(tmp_path):
    """The website process has no data: pages and widget from disk, three estimate calls forwarded with the token, nothing else."""
    import httpx
    from fastapi.testclient import TestClient
    from solarapp.config import Settings
    from solarapp.main import create_app
    from solarapp.public import create_public_app
    site = tmp_path / "site"
    (site / "static").mkdir(parents=True)
    (site / "index.html").write_text("<html>home</html>")
    (site / "estimate.html").write_text("<html>estimate</html>")
    (site / "404.html").write_text("<html>lost</html>")
    (site / "static" / "site.css").write_text("body{}")
    (tmp_path / "secret.txt").write_text("private")
    token = "t" * 32
    private = create_app(Settings(data_dir=tmp_path / "data", app_username="u", app_password="p", secret_key="s" * 32, internal_token=token))
    public = create_public_app(Settings(data_dir=tmp_path / "data2", site_dir=site, static_dir=tmp_path / "nodist", upstream="http://private", internal_token=token),
                               transport=httpx.ASGITransport(app=private))
    with TestClient(private) as priv, TestClient(public) as pub:
        # pages and clean URLs
        assert pub.get("/").text == "<html>home</html>" and pub.get("/estimate").text == "<html>estimate</html>"
        assert pub.get("/estimate.html").status_code == 200 and pub.get("/static/site.css").status_code == 200
        r = pub.get("/nothing-here")
        assert r.status_code == 404 and "lost" in r.text
        assert "private" not in pub.get("/..%2fsecret.txt").text
        # security headers
        h = pub.get("/").headers
        assert "default-src 'self'" in h["content-security-policy"] and h["x-content-type-options"] == "nosniff"
        # the estimate calls cross with the token; the back office never does
        st = pub.get("/api/quick/status")
        assert st.status_code == 200 and "towns" in st.json()
        assert pub.get("/api/assessments").status_code == 404
        assert pub.post("/api/auth/login", json={"username": "u", "password": "p"}).status_code == 404
        assert pub.get("/api/quick/anything").status_code == 404
        # the private app refuses the estimate routes without the token or a session
        assert priv.get("/api/quick/status").status_code == 404
        assert priv.get("/api/quick/status", headers={"x-internal-token": token}).status_code == 200
        priv.post("/api/auth/login", json={"username": "u", "password": "p"})
        assert priv.get("/api/quick/status").status_code == 200  # a signed-in owner may still open the estimate page
        assert priv.get("/").headers.get("x-frame-options") == "DENY"
