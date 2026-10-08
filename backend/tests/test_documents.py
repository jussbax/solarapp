"""Documents: one stale rule for every document, per-row k values that follow the rows as typed, the no-fit guard,
the card's saved next step, and the proposal's wording (the battery from the BOM, customer item names, the tools
charge folded into installation, same-day payments, the website estimate carried forward)."""
import re
import shutil
import subprocess
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.schemas import AssessmentDoc

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


LAGUNA_DOC = {
    "customer_name": "Maria Santos", "address": "Brgy. Labuin, Pila, Laguna", "lat": 14.2335, "lon": 121.3645,
    "faces": [
        {"id": "f1", "name": "Main roof (south)", "length_m": 9.0, "width_m": 5.0, "tilt_deg": 18, "azimuth_deg": 180},
        {"id": "f2", "name": "Kitchen roof (east)", "length_m": 6.0, "width_m": 4.0, "tilt_deg": 15, "azimuth_deg": 90},
    ],
    "panels": [{"id": "p1", "name": "Blue Carbon 585W", "watt_peak": 585, "length_m": 2.278, "width_m": 1.134, "code": "BC-PNL-001"}],
    "reading_sets": [
        {"id": "s1", "face_id": "f1", "measured_at": "2026-10-03T11:30:00", "ambient_temp_c": 33, "sky_condition": "clear",
         "readings": [{"irradiance_wm2": 903, "power_w": 36.1, "module_temp_c": 57}, {"irradiance_wm2": 910, "power_w": 36.4, "module_temp_c": 58}, {"irradiance_wm2": 896, "power_w": 35.8, "module_temp_c": 57}]},
        {"id": "s2", "face_id": "f2", "measured_at": "2026-10-03T11:50:00", "sky_condition": "clear",
         "readings": [{"irradiance_wm2": 0, "power_w": 0}, {"irradiance_wm2": 850, "power_w": 32.9, "module_temp_c": 56}, {"irradiance_wm2": 860, "power_w": 33.3, "module_temp_c": 56}]},
    ],
    "audit": {
        "appliances": [
            {"id": "ref", "name": "Refrigerator", "category": "refrigerator", "input_power_w": 150, "quantity": 1, "windows": [{"start": "06:00", "end": "06:00"}]},
            {"id": "ac", "name": "Split inverter AC", "category": "aircon_inverter", "input_power_w": 1200, "quantity": 1, "windows": [{"start": "20:00", "end": "06:00"}]},
            {"id": "led", "name": "LED bulb", "category": "lighting", "input_power_w": 9, "quantity": 8, "windows": [{"start": "18:00", "end": "06:00"}]},
            {"id": "tv", "name": "TV", "category": "other", "input_power_w": 90, "quantity": 1, "windows": [{"start": "18:00", "end": "23:00"}]},
            {"id": "ac2", "name": "Second aircon (planned)", "category": "aircon_inverter", "input_power_w": 1200, "status": "future", "windows": [{"start": "13:00", "end": "17:00"}]},
        ],
        "bills": [{"id": "b1", "billing_month": "2026-09", "kwh": 310, "days": 30, "amount_php": 3980.5, "utility": "FLECO"}],
        "reconcile": True,
        "system": {"kind": "combination"},
    },
}
LEAD = {
    "contact": "0917 555 1234", "town": "Pila", "created_at": "2026-09-28T10:15:00",
    "source": {"utm_source": "fb"},
    "estimate": {"goal": "hybrid", "panels": 5, "kwp": 2.93, "battery_kwh": 10, "price": 282000, "bill_before_monthly": 3980, "bill_after_monthly": 400},
}


def _computed(client: TestClient, doc: dict) -> dict:
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    return r.json()


def _pdf_text(pdf: bytes) -> str:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    return subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode()


def test_every_document_refuses_stale_results_with_one_message(client):
    out = _computed(client, LAGUNA_DOC)
    aid, doc = out["id"], out["doc"]
    assert out["results"]["pricing"]["available"], out["results"]["pricing"]
    doc["notes"] = "edited after the calculation"
    assert client.put(f"/api/assessments/{aid}", json=doc).json()["results_stale"] is True
    answers = {name: client.get(f"/api/assessments/{aid}/{name}") for name in ("report.pdf", "quotation.pdf", "program.pdf", "card.png")}
    assert {r.status_code for r in answers.values()} == {409}
    assert {r.json()["detail"] for r in answers.values()} == {STALE}
    # calculated again: the priced documents build; the customer documents stay off under test weather data
    assert client.post(f"/api/assessments/{aid}/compute").status_code == 200
    assert client.get(f"/api/assessments/{aid}/quotation.pdf").status_code == 200
    assert client.get(f"/api/assessments/{aid}/program.pdf").status_code == 200
    assert "test weather" in client.get(f"/api/assessments/{aid}/report.pdf").json()["detail"]
    assert "test weather" in client.get(f"/api/assessments/{aid}/card.png").json()["detail"]
    # a record that was never calculated
    fresh = client.post("/api/assessments", json=LAGUNA_DOC).json()["id"]
    assert client.get(f"/api/assessments/{fresh}/program.pdf").json()["detail"] == "Calculate first."


def test_per_row_k_values_follow_the_rows_as_typed(client):
    res = _computed(client, LAGUNA_DOC)["results"]
    s1, s2 = res["k"]["sets"]
    assert s1["row_usable"] == [True, True, True] and len(s1["k_raw_values"]) == 3
    assert s1["measured_at"] == "2026-10-03T11:30:00" and s1["sky_condition"] == "clear"
    # row 1 of the second set has no sunlight: it is dropped and its slot stays empty, the other rows keep their place
    assert s2["row_usable"] == [False, True, True]
    assert s2["k_raw_values"][0] is None and s2["k_site_values"][0] is None
    assert len(s2["k_raw_values"]) == 3 and all(v > 0 for v in s2["k_raw_values"][1:])
    assert abs(s2["k_raw"] - sum(s2["k_raw_values"][1:]) / 2) < 1e-9
    assert any(w["code"] == "few_readings" for w in s2["warnings"])


def test_a_face_that_fits_no_panel_is_named_and_no_fit_at_all_is_refused(client):
    doc = deepcopy(LAGUNA_DOC)
    doc["faces"][1] = {**doc["faces"][1], "name": "Garage roof (west)", "width_m": 0.5}
    res = _computed(client, doc)["results"]
    w = next(w for w in res["warnings"] if w["code"] == "face_no_fit")
    assert w["message"].startswith("Garage roof (west): no panel fits this face") and w["face_id"] == "f2"
    assert res["production"]["faces"][1]["panel_count"] == 0 and res["production"]["total_panels"] > 0
    doc["faces"][0] = {**doc["faces"][0], "width_m": 0.5}
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 422 and r.json()["detail"] == "No panel fits any roof face. Check the face sizes and the setback."


def test_card_next_step_is_saved_on_the_record(client, monkeypatch):
    from solarapp.db import get_engine
    from solarapp.models import Assessment

    out = _computed(client, LAGUNA_DOC)
    aid, doc = out["id"], out["doc"]
    assert doc["card_next_step"] == ""
    doc["card_next_step"] = "Next step: your free energy audit on 20 Oct"
    assert client.post(f"/api/assessments/{aid}/compute", json=doc).json()["doc"]["card_next_step"] == doc["card_next_step"]
    # test weather data keeps the card off; mark the stored results as real to reach the builder
    with Session(get_engine()) as s:
        a = s.get(Assessment, aid)
        a.results = {**a.results, "dataset": {**a.results["dataset"], "synthetic": False}}
        s.add(a)
        s.commit()
    seen = {}

    def fake_card(doc, results, company, next_step="", public_url=""):
        seen["next_step"] = next_step
        return b"\x89PNG"

    monkeypatch.setattr("solarapp.api.assessments.build_client_card", fake_card)
    assert client.get(f"/api/assessments/{aid}/card.png").status_code == 200
    assert seen["next_step"] == "Next step: your free energy audit on 20 Oct"
    client.get(f"/api/assessments/{aid}/card.png", params={"next_step": "Site visit on Friday"})
    assert seen["next_step"] == "Site visit on Friday"


def test_payment_rows_merge_same_day_milestones():
    from solarapp.reports.quotation_pdf import payment_rows

    rows = payment_rows([
        {"key": "downpayment", "label": "Downpayment on signing", "date": "2026-10-20", "amount": 150000, "share": 0.5},
        {"key": "delivery", "label": "On delivery of materials to your house", "date": "2026-11-05", "amount": 120000, "share": 0.4},
        {"key": "completion", "label": "On switch-on and testing", "date": "2026-11-05", "amount": 30000, "share": 0.1},
    ])
    assert [r["label"] for r in rows] == ["Downpayment on signing", "On installation day, after switch-on and testing"]
    assert rows[1]["amount"] == 150000 and abs(rows[1]["share"] - 0.5) < 1e-9
    rows = payment_rows([
        {"key": "delivery", "label": "On delivery of materials to your house", "date": "2026-11-05", "amount": 120000, "share": 0.4},
        {"key": "completion", "label": "On switch-on and testing", "date": "2026-11-07", "amount": 30000, "share": 0.1},
        {"key": "installment_1", "label": "Installment 1 of 2", "date": "2026-11-07", "amount": 10000, "share": 0.05},
    ])
    assert [r["label"] for r in rows] == ["On delivery of materials to your house", "On switch-on and testing", "Same day, installment 1 of 2"]


def test_proposal_prints_the_bom_battery_plain_item_names_and_the_website_estimate(client):
    from solarapp.reports.card import estimate_line
    from solarapp.reports.quotation_pdf import bom_battery_kwh, customer_sections, lead_estimate_sentence, what_you_get

    doc = deepcopy(LAGUNA_DOC)
    doc["lead"] = LEAD
    out = _computed(client, doc)
    res, aid = out["results"], out["id"]
    pr = res["pricing"]
    bat = next(l for l in pr["lines"] if l["role"] == "battery")
    kwh = bat["qty"] * bat["rating"]
    assert bom_battery_kwh(pr) == kwh > 0
    # the three main items: quantity, rating and supplier, never the catalogue string
    names = [i["name"] for i in pr["customer"]["sections"][0]["items"] if i["main"]]
    assert names[0].startswith("Solar panels: ") and " × 585 W (" in names[0]
    assert any(n.startswith("Hybrid inverter: ") and " kW (" in n for n in names)
    # one unit prints "12 kWh (supplier)", several print "2 × 6 kWh (12 kWh in all) (supplier)"; sized at the meter this job takes two
    assert any(n.startswith(("Lithium battery (LiFePO4): ", "Battery: ")) and (f"{kwh:.0f} kWh (" in n or f"({kwh:.0f} kWh in all)" in n) for n in names)
    assert not any("Monofacial" in n or "BMS" in n or "eco-hybrid" in n for n in names)
    crew = next(i for i in pr["customer"]["sections"][1]["items"] if i["key"] == "labor")["name"]
    assert "skilled technicians" in crew or "1 skilled technician," in crew
    assert any(i["key"] == "erc" and i["name"].startswith("ERC certificate of compliance") for i in pr["customer"]["sections"][1]["items"])
    assert any(i["key"] == "meter" and i["name"].startswith("Two-way meter from your electric company") for i in pr["customer"]["sections"][1]["items"])
    # the engine keeps four sections; the proposal folds the tools into Installation and permits
    assert [s["key"] for s in pr["customer"]["sections"]] == ["materials", "labor", "equipment", "tax"]
    secs = customer_sections(pr["customer"])
    assert [s["key"] for s in secs] == ["materials", "labor", "tax"]
    assert secs[1]["items"][1]["key"] == "tools" and abs(sum(s["amount"] for s in secs) - pr["customer"]["total"]) < 0.01
    # the website estimate, on the proposal and the card
    parsed = AssessmentDoc.model_validate(out["doc"])
    assert lead_estimate_sentence(parsed, res["economics"]) == (
        "Your website estimate on 28 Sep 2026 was PHP 282,000 for 5 panels and a 10 kWh battery. "
        "This proposal is measured on your roof and includes the appliances you plan to add.")
    assert lead_estimate_sentence(AssessmentDoc.model_validate(LAGUNA_DOC), None) == ""
    assert estimate_line(parsed) == "Your estimate said about PHP 282,000; the visit settles the exact figure."
    assert what_you_get(res["sizing"], res["program"], False)[-1].endswith("on installation day.")
    assert "warranties" in what_you_get(res["sizing"], res["program"], True)[-1]
    assert res["program"]["assumptions"][-2].startswith("Assumed: permit approval") and res["program"]["assumptions"][-1].startswith("Assumed for net metering:")
    assert not any("no data yet" in a for a in res["program"]["assumptions"])
    # the PDF itself
    text = _pdf_text(client.get(f"/api/assessments/{aid}/quotation.pdf").content)
    assert text.count("Valid until") == 1
    assert "WHAT YOU GET" in text and "Your website estimate on 28 Sep 2026" in text
    assert text.count(f"{kwh:.0f} kWh lithium battery") == 1 and f"A {kwh:.0f} kWh battery carries" in text
    assert "Installation tools subtotal" not in text and "Installation tools" in text
    assert "Quantities are based on your roof check" in text and "roof assessment" not in text
    assert "ERC certificate of compliance" in text and "ERC Certificate" not in text and "Two-way meter from your electric company" in text
    assert "Savings against your bill today" in text
    # crew plurals: "1 skilled technician, 2 helpers" or "2 skilled technicians, 3 helpers" (this job takes one pair: two 6 kWh packs carry lighter than one 10 kWh pack)
    assert re.search(r"\b1 skilled technician, |\b[2-9] skilled technicians, ", text) and "1 skilled technicians" not in text


def test_roof_check_prints_the_readings_and_keeps_the_closing_notes_together(client):
    from solarapp.reports.customer_pdf import build_customer_pdf
    from solarapp.reports.program_pdf import build_program_pdf

    out = _computed(client, LAGUNA_DOC)
    doc, res = AssessmentDoc.model_validate(out["doc"]), out["results"]
    text = _pdf_text(build_customer_pdf(doc, res, {"company_name": "Test Solar", "company_contact": "x"}))
    assert "Measured on your roof" in text and "Sunlight on the roof: " in text and "clear sky, 11:30 AM" in text and "Test panel: " in text
    last = next(p for p in text.split("\f") if "Next step: your free energy audit" in p)
    assert "About this estimate" in last  # never a lone paragraph on its own page
    text = _pdf_text(build_program_pdf(doc, res, {"company_name": "Test Solar"}))
    assert "Assumed: permit approval" in text and "Assumption:" not in text


def test_card_next_step_does_not_make_results_stale(client):
    """The next-step line is printed on the card, never computed, so editing it keeps the documents available."""
    client.post("/api/auth/login", json={"username": "u", "password": "p"})
    rows = client.get("/api/assessments").json()
    calculated = [r for r in rows if r["has_results"] and not r["results_stale"]]
    assert calculated, "a calculated record from the earlier tests is expected"
    aid = calculated[0]["id"]
    doc = client.get(f"/api/assessments/{aid}").json()["doc"]
    r = client.put(f"/api/assessments/{aid}", json={**doc, "card_next_step": "Your free energy audit on Monday"})
    assert r.status_code == 200 and r.json()["results_stale"] is False
    assert client.get(f"/api/assessments/{aid}").json()["doc"]["card_next_step"] == "Your free energy audit on Monday"
    r = client.put(f"/api/assessments/{aid}", json={**doc, "card_next_step": "Your free energy audit on Monday", "notes": "changed"})
    assert r.json()["results_stale"] is True
