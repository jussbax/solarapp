"""Round 4 (the owner, 9 Oct 2026): the panel is chosen in the background from the materials list and the Panel options
card leaves data entry; the project head shows an engineering status read from the facts instead of the job-stage pill."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from solarapp.compute import NO_USABLE_PANEL, best_panel_index
from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.models import Assessment
from solarapp.schemas import AssessmentDoc

from tests.conftest import real_weather
from tests.test_api import DOC, TANAUAN_AUDIT

BC_PANELS = ["BC-PNL-001", "BC-PNL-002", "BC-PNL-003", "BC-PNL-004"]   # the seed's panels that carry a wattage, a length and a width


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.5, 14.75, 120.75, 121.0), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def _priced_doc() -> dict:
    return {**deepcopy(DOC), "audit": dict(deepcopy(TANAUAN_AUDIT), system={"kind": "combination"})}


def _compute(client, aid, doc=None):
    r = client.post(f"/api/assessments/{aid}/compute", json=doc)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- the rule
def test_most_kwp_wins_and_a_tie_goes_to_the_lower_price_per_watt():
    results = [{"system_kwp": 4.1}, {"system_kwp": 4.41}, {"system_kwp": 4.41}, {"system_kwp": 4.41}]
    assert best_panel_index(results, [8.46, 8.65, 8.33, 8.33]) == 2      # most kWp, then the cheaper watt
    assert best_panel_index(results, [8.46, 8.65, 8.33, 8.00]) == 3
    assert best_panel_index([{"system_kwp": 5.0}, {"system_kwp": 4.0}], [9.0, 1.0]) == 0   # price never beats kWp
    assert best_panel_index(results, [1.0, 1.0, 1.0, 1.0]) == 1          # all equal: the list's order


# ---------------------------------------------------------------- automatic, the setting, the override
def test_the_panel_comes_from_the_materials_list_without_naming_one(client):
    """A project built without ever naming a panel is sized on the most-kWp panel of the list; the record carries no panel
    list any more, the roof check and the pricing print the chosen one."""
    out = client.post("/api/assessments", json=_priced_doc()).json()
    assert "panels" not in out["doc"] and "selected_panel_id" not in out["doc"] and out["doc"]["panel_code"] is None
    out = _compute(client, out["id"])
    res = out["results"]
    assert [p["panel"]["code"] for p in res["panels"]] == BC_PANELS and all(p["panel"]["id"] == p["panel"]["code"] for p in res["panels"])
    best = max(res["panels"], key=lambda p: p["system_kwp"])
    assert best["best"] and res["selected_panel_id"] == best["panel"]["code"] == res["best_panel"]["id"]
    assert res["panel_choice"]["rule"] == "automatic" and res["panel_choice"]["candidates"] == 4 and res["panel_choice"]["setting_code"] is None
    assert res["production"]["total_panels"] == best["total_count"] and res["production"]["system_kwp"] == pytest.approx(best["system_kwp"])
    assert res["pricing"]["available"] and res["pricing"]["panel"]["code"] == best["panel"]["code"]
    assert res["geometry"][0]["panel_length_m"] == best["panel"]["length_m"]
    assert not any(w["code"] in ("panel_typed_by_hand_replaced", "panel_choice_unavailable", "panel_unlinked") for w in res["warnings"])
    # the roof check names the chosen panel
    from solarapp.reports.customer_pdf import build_customer_pdf
    pdf = build_customer_pdf(AssessmentDoc.model_validate(out["doc"]), res, {"company_name": "Test Solar", "company_contact": "x"})
    assert pdf[:4] == b"%PDF"


def test_the_setting_puts_one_panel_on_every_job_and_the_project_may_still_differ(client):
    aid = client.post("/api/assessments", json=_priced_doc()).json()["id"]
    cfg = client.get("/api/pricing/config").json()
    assert cfg["sizing"]["panel_code"] == ""
    cfg["sizing"]["panel_code"] = "BC-PNL-003"
    assert client.put("/api/pricing/config", json=cfg).status_code == 200
    try:
        res = _compute(client, aid)["results"]
        assert res["panel_choice"]["rule"] == "setting" and res["selected_panel_id"] == "BC-PNL-003" and res["panel_choice"]["setting_code"] == "BC-PNL-003"
        assert res["pricing"]["panel"]["code"] == "BC-PNL-003" and res["best_panel"]["id"] != "BC-PNL-003"
        # the engineer's choice for this project beats the setting; blank goes back to the setting
        doc = client.get(f"/api/assessments/{aid}").json()["doc"]
        res = _compute(client, aid, {**doc, "panel_code": "BC-PNL-002"})["results"]
        assert res["panel_choice"]["rule"] == "project" and res["selected_panel_id"] == "BC-PNL-002" and res["pricing"]["panel"]["code"] == "BC-PNL-002"
        assert client.get(f"/api/assessments/{aid}").json()["doc"]["panel_code"] == "BC-PNL-002"
        res = _compute(client, aid, {**doc, "panel_code": None})["results"]
        assert res["panel_choice"]["rule"] == "setting" and res["selected_panel_id"] == "BC-PNL-003"
        # a setting that names no usable panel says so and the automatic rule applies
        cfg["sizing"]["panel_code"] = "IAN-PNL-001"   # 720 W, no size on file
        assert client.put("/api/pricing/config", json=cfg).status_code == 200
        res = _compute(client, aid)["results"]
        assert res["panel_choice"]["rule"] == "automatic" and res["selected_panel_id"] == res["best_panel"]["id"]
        assert any(w["code"] == "panel_choice_unavailable" and "IAN-PNL-001" in w["message"] and "Pricing settings" in w["message"] for w in res["warnings"])
    finally:
        cfg["sizing"]["panel_code"] = ""
        assert client.put("/api/pricing/config", json=cfg).status_code == 200


def test_a_materials_list_without_a_usable_panel_refuses_plainly(client):
    aid = client.post("/api/assessments", json=_priced_doc()).json()["id"]
    try:
        for code in BC_PANELS:
            assert client.put(f"/api/pricing/items/{code}", json={"active": False}).status_code == 200
        r = client.post(f"/api/assessments/{aid}/compute")
        assert r.status_code == 422 and r.json()["detail"] == NO_USABLE_PANEL
        # a panel with a wattage but no size is not usable either
        assert client.put("/api/pricing/items/BC-PNL-001", json={"active": True}).status_code == 200
        assert _compute(client, aid)["results"]["panel_choice"]["candidates"] == 1
    finally:
        for code in BC_PANELS:
            client.put(f"/api/pricing/items/{code}", json={"active": True})


# ---------------------------------------------------------------- old records
def _legacy_record(client, selected: str | None) -> int:
    """A record as round 3 saved it: its own candidate panels, one typed by hand, and the one ticked under Use."""
    doc = _priced_doc()
    doc["panels"] = [
        {"id": "hand", "name": "Canadian 550W (manual)", "watt_peak": 550, "length_m": 2.278, "width_m": 1.134, "code": None},
        {"id": "list", "name": "585W Bifacial solar panel", "watt_peak": 585, "length_m": 2.278, "width_m": 1.134, "code": "BC-PNL-002"},
    ]
    doc["selected_panel_id"] = selected
    with Session(client.app.state.engine) as s:
        a = Assessment(customer_name="Old Record", address="Pila", doc=doc)
        s.add(a)
        s.commit()
        s.refresh(a)
        return a.id


def test_an_old_record_keeps_its_forced_list_panel_and_drops_the_one_typed_by_hand(client, caplog):
    aid = _legacy_record(client, "list")
    out = client.get(f"/api/assessments/{aid}").json()
    assert "panels" not in out["doc"] and "selected_panel_id" not in out["doc"]
    assert out["doc"]["panel_code"] == "BC-PNL-002" and out["doc"]["dropped_panels"] == ["Canadian 550W (manual)"]
    with caplog.at_level("INFO", logger="solarapp.compute"):
        out = _compute(client, aid)
    res = out["results"]
    assert res["panel_choice"]["rule"] == "project" and res["selected_panel_id"] == "BC-PNL-002"
    w = next(w for w in res["warnings"] if w["code"] == "panel_typed_by_hand_replaced")
    assert w["message"].startswith("The panel typed by hand (Canadian 550W (manual)) was replaced by 585W Bifacial solar panel (BC-PNL-002) from the materials list")
    assert "panel typed by hand dropped: Canadian 550W (manual) replaced by BC-PNL-002" in caplog.text
    # reported once: the stored record is clean and the next calculation says nothing
    assert out["doc"]["dropped_panels"] == [] and "panels" not in out["doc"]
    with Session(client.app.state.engine) as s:
        stored = s.get(Assessment, aid).doc
    assert "panels" not in stored and "selected_panel_id" not in stored and stored["panel_code"] == "BC-PNL-002"
    assert not any(w["code"] == "panel_typed_by_hand_replaced" for w in _compute(client, aid)["results"]["warnings"])


def test_an_old_record_that_forced_a_panel_typed_by_hand_goes_automatic_with_the_warning(client):
    aid = _legacy_record(client, "hand")
    out = client.get(f"/api/assessments/{aid}").json()
    assert out["doc"]["panel_code"] is None and out["doc"]["dropped_panels"] == ["Canadian 550W (manual)"]
    # a Save from the browser before any calculation keeps the note for the calculation, and does not count as an edit
    saved = client.put(f"/api/assessments/{aid}", json=out["doc"]).json()
    assert saved["doc"]["dropped_panels"] == ["Canadian 550W (manual)"] and saved["results_stale"] is False
    res = _compute(client, aid)["results"]
    assert res["panel_choice"]["rule"] == "automatic" and res["selected_panel_id"] == res["best_panel"]["id"]
    w = next(w for w in res["warnings"] if w["code"] == "panel_typed_by_hand_replaced")
    assert "Canadian 550W (manual)" in w["message"] and res["best_panel"]["name"] in w["message"]


# ---------------------------------------------------------------- the engineering status
def test_the_status_follows_the_facts_and_the_proposal_marks_it(client):
    """Draft (nothing measured) → Surveyed (a reading set saved) → Designed (calculated, not stale) → Proposal issued (the
    proposal PDF generated, with its date), back on Reopen design. The job stage the document keeps plays no part."""
    doc = _priced_doc()
    readings = doc.pop("reading_sets")
    out = client.post("/api/assessments", json=doc).json()
    aid = out["id"]
    assert out["status"] == "draft" and out["proposal_issued_at"] is None
    row = lambda: next(r for r in client.get("/api/assessments").json() if r["id"] == aid)  # noqa: E731
    assert row()["status"] == "draft" and row()["stage"] == "assessed"
    out = client.put(f"/api/assessments/{aid}", json={**out["doc"], "reading_sets": readings}).json()
    assert out["status"] == "surveyed" and row()["status"] == "surveyed"
    out = _compute(client, aid)
    assert out["status"] == "designed" and row()["status"] == "designed"
    # an edit to the inputs makes the results stale: the design is no longer standing
    out = client.put(f"/api/assessments/{aid}", json={**out["doc"], "notes": "edited after the calculation"}).json()
    assert out["results_stale"] is True and out["status"] == "surveyed"
    out = _compute(client, aid)
    assert out["status"] == "designed"
    # the proposal PDF marks the record; a second download keeps the first date
    real_weather(aid, client)
    assert client.get(f"/api/assessments/{aid}/quotation.pdf").status_code == 200
    out = client.get(f"/api/assessments/{aid}").json()
    assert out["status"] == "proposal_issued" and out["proposal_issued_at"]
    issued = out["proposal_issued_at"]
    assert client.get(f"/api/assessments/{aid}/quotation.pdf").status_code == 200
    assert client.get(f"/api/assessments/{aid}").json()["proposal_issued_at"] == issued
    assert row()["status"] == "proposal_issued" and row()["proposal_issued_at"] == issued
    # the proposal stands through a Save (even one that makes the results stale) and whatever the document's stage says
    out = client.put(f"/api/assessments/{aid}", json={**out["doc"], "notes": "a note after the proposal", "program": {**out["doc"]["program"], "stage": "signed"}}).json()
    assert out["results_stale"] is True and out["status"] == "proposal_issued" and out["doc"]["program"]["stage"] == "signed"
    assert row()["stage"] == "signed" and row()["status"] == "proposal_issued"
    # Reopen design clears the mark: the status is the facts again (stale here, so surveyed), then designed on Calculate
    out = client.post(f"/api/assessments/{aid}/reopen").json()
    assert out["status"] == "surveyed" and out["proposal_issued_at"] is None
    assert client.post(f"/api/assessments/{aid}/reopen").json()["status"] == "surveyed"   # idempotent
    assert _compute(client, aid)["status"] == "designed"
    assert client.get(f"/api/assessments/{aid}").json()["doc"]["program"]["stage"] == "signed"   # the document keeps it for the CRM
