"""The leads inbox: website bookings land there (not on the project list), the owner works them, Start assessment makes the project.

Also the startup migration of lead-stage assessments, the retention run over leads, and the stage contract (C1).
"""
import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app

BOOKING = {
    "goal": "net_metering", "town": "Tanauan", "province": "Batangas", "monthly_kwh": 333, "monthly_php": 4000, "pattern": "evening",
    "name": "Web Visitor", "contact": "0917 555 1234", "address": "", "preferred_time": "Evening", "consent": True, "notice_version": "2026-03",
    "source": {"utm_source": "fb", "utm_campaign": "brownout1", "referrer": "https://facebook.com/", "page": "https://pldevinc.com/estimate?utm_source=fb"},
    "estimate": {"goal": "net_metering", "panels": 6, "kwp": 3.51, "battery_kwh": 0, "price": 172000, "bill_before_monthly": 4000, "bill_after_monthly": 900, "payback_years": 4.2},
}


def _settings(root):
    return Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("leads")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    with TestClient(create_app(_settings(root))) as c:
        yield c


def login(client):
    client.post("/api/auth/login", json={"username": "u", "password": "p"})


def book(client, **over):
    client.post("/api/auth/logout")
    r = client.post("/api/quick/lead", json={**BOOKING, **over})
    assert r.status_code == 200 and r.json()["ok"], r.text
    login(client)
    return r.json()["id"]


# ---- the website lead lands in the inbox

def test_website_lead_lands_in_the_inbox_not_the_project_list(client, caplog):
    with caplog.at_level(logging.INFO, logger="solarapp.audit"):
        lid = book(client)
    assert any("lead created id=%s" % lid in m for m in caplog.messages)
    assert client.get("/api/leads").status_code == 200
    lead = client.get(f"/api/leads/{lid}").json()
    assert lead["status"] == "new" and lead["name"] == "Web Visitor" and lead["contact"] == "0917 555 1234" and lead["preferred_time"] == "Evening"
    assert lead["town"] == "Tanauan" and lead["province"] == "Batangas" and lead["place"] == "Tanauan, Batangas" and lead["lat"] is None
    assert lead["source"]["utm_campaign"] == "brownout1" and lead["source_label"] == "fb/brownout1" and lead["consent"] is True and lead["notice_version"] == "2026-03"
    est = lead["estimate"]
    assert est["price"] == 172000 and est["panels"] == 6 and est["monthly_kwh"] == 333 and est["monthly_php"] == 4000 and est["pattern"] == "evening"
    assert "From the website estimate" in lead["notes"] and "best time: Evening" in lead["notes"] and "a lower bill, no battery" in lead["notes"]
    assert lead["project_id"] is None and lead["closed_reason"] == "" and not lead["anonymised"]
    # nothing on the project list, and the summaries carry no lead fields except lead_id
    rows = client.get("/api/assessments").json()
    assert not any(a["customer_name"] == "Web Visitor" for a in rows)
    assert all(set(k for k in a if k.startswith("lead")) == {"lead_id"} for a in rows)
    # a bot filling the hidden field gets a polite yes and nothing is stored
    client.post("/api/auth/logout")
    assert client.post("/api/quick/lead", json={**BOOKING, "name": "Bot", "website": "http://spam"}).json() == {"ok": True}
    login(client)
    assert not any(l["name"] == "Bot" for l in client.get("/api/leads").json())
    # the inbox needs the login
    client.post("/api/auth/logout")
    assert client.get("/api/leads").status_code == 401
    login(client)


def test_pin_leads_keep_the_pin_and_say_near(client):
    lid = book(client, town="", province="", lat=14.09, lon=121.15, name="Pin Person", address="Brgy. Sambat, beside the chapel")
    lead = client.get(f"/api/leads/{lid}").json()
    assert lead["lat"] == 14.09 and lead["lon"] == 121.15 and lead["town"] == "Tanauan" and lead["place"] == "near Tanauan, Batangas"
    assert "pin placed by the customer" in lead["notes"] and lead["address"] == "Brgy. Sambat, beside the chapel"


# ---- the owner works the inbox

def test_inbox_lists_newest_first_filters_searches_edits_and_deletes(client, caplog):
    a = book(client, name="Ana Reyes", contact="0918 111 2222")
    b = book(client, name="Ben Cruz", contact="ben.cruz.fb", town="Pila", province="Laguna")
    ids = [l["id"] for l in client.get("/api/leads").json()]
    assert ids.index(b) < ids.index(a)  # newest first
    assert [l["name"] for l in client.get("/api/leads?q=ben").json()] == ["Ben Cruz"]
    assert any(l["id"] == b for l in client.get("/api/leads?q=pila").json())
    assert client.get("/api/leads?status=nope").status_code == 422
    with caplog.at_level(logging.INFO, logger="solarapp.audit"):
        r = client.patch(f"/api/leads/{a}", json={"status": "contacted", "notes": "Called, visit Saturday."})
    assert r.status_code == 200 and r.json()["status"] == "contacted" and r.json()["notes"] == "Called, visit Saturday."
    assert any(f"lead status id={a} new -> contacted" in m for m in caplog.messages)
    assert [l["id"] for l in client.get("/api/leads?status=contacted").json()] == [a]
    assert a not in [l["id"] for l in client.get("/api/leads?status=new").json()]
    # closing takes a reason; reopening clears it; "converted" is only reached through Start assessment
    r = client.patch(f"/api/leads/{a}", json={"status": "closed", "closed_reason": "Renting, landlord said no."})
    assert r.json()["status"] == "closed" and r.json()["closed_reason"] == "Renting, landlord said no."
    assert client.patch(f"/api/leads/{a}", json={"status": "new"}).json()["closed_reason"] == ""
    assert client.patch(f"/api/leads/{a}", json={"status": "converted"}).status_code == 409
    with caplog.at_level(logging.INFO, logger="solarapp.audit"):
        assert client.delete(f"/api/leads/{b}").status_code == 204
    assert any(f"lead deleted id={b}" in m for m in caplog.messages)
    assert client.get(f"/api/leads/{b}").status_code == 404 and client.delete(f"/api/leads/{b}").status_code == 404


# ---- Start assessment

def test_start_assessment_creates_the_project_from_the_lead(client, caplog):
    lid = book(client, name="Maria Santos")
    client.patch(f"/api/leads/{lid}", json={"status": "visit_booked", "notes": "From the website estimate. Visit Saturday 9am."})
    with caplog.at_level(logging.INFO, logger="solarapp.audit"):
        r = client.post(f"/api/leads/{lid}/convert")
    assert r.status_code == 200, r.text
    pid = r.json()["project_id"]
    assert r.json()["lead"]["status"] == "converted" and r.json()["lead"]["project_id"] == pid
    assert any(f"lead converted id={lid} project_id={pid}" in m for m in caplog.messages)
    a = client.get(f"/api/assessments/{pid}").json()
    doc = a["doc"]
    assert doc["customer_name"] == "Maria Santos" and doc["address"] == "Tanauan, Batangas"
    assert doc["lat"] == pytest.approx(14.086) and doc["lon"] == pytest.approx(121.150)  # the town's coordinates, since the visitor gave no pin
    assert doc["audit"]["bills"] == [{"id": "lead", "billing_month": datetime.now(timezone.utc).strftime("%Y-%m"), "kwh": 333.0, "days": None, "amount_php": 4000.0, "utility": ""}]
    assert doc["audit"]["system"]["kind"] == "net_metering" and doc["program"]["stage"] == "assessed" and doc["lead_id"] == lid
    assert doc["notes"] == "From the website estimate. Visit Saturday 9am."
    # the project keeps only the estimate the visitor saw (for the proposal's sentence), not the contact or the source
    assert doc["lead"]["estimate"]["price"] == 172000 and doc["lead"]["contact"] == "" and doc["lead"]["source"]["utm_source"] == ""
    row = next(s for s in client.get("/api/assessments").json() if s["id"] == pid)
    assert row["lead_id"] == lid and row["stage"] == "assessed" and row["face_count"] == 0 and row["battery_kwh"] is None and row["computed_at"] is None
    assert "lead_contact" not in row and "lead_estimate" not in row
    # converting again returns the same project; deleting the project lets the lead start another
    assert client.post(f"/api/leads/{lid}/convert").json()["project_id"] == pid
    assert client.delete(f"/api/assessments/{pid}").status_code == 204
    pid2 = client.post(f"/api/leads/{lid}/convert").json()["project_id"]
    assert client.get(f"/api/leads/{lid}").json()["project_id"] == pid2 and client.get(f"/api/assessments/{pid2}").json()["doc"]["lead_id"] == lid


def test_start_assessment_keeps_the_pin_and_the_address(client):
    lid = book(client, town="", province="", lat=14.10, lon=121.16, name="Pin Person", address="Brgy. Sambat", monthly_kwh=None, monthly_php=5000, goal="combination",
               estimate={"goal": "combination", "panels": 8, "kwp": 4.68, "battery_kwh": 10.24, "price": 300000})
    pid = client.post(f"/api/leads/{lid}/convert").json()["project_id"]
    doc = client.get(f"/api/assessments/{pid}").json()["doc"]
    assert doc["lat"] == 14.10 and doc["lon"] == 121.16 and doc["address"] == "Brgy. Sambat" and doc["audit"]["system"]["kind"] == "combination"
    assert doc["audit"]["bills"][0]["amount_php"] == 5000 and doc["audit"]["bills"][0]["kwh"] > 0  # pesos read as kWh at the default tariff


# ---- the funnel moved to the inbox

def test_funnel_counts_from_the_inbox_and_the_projects(client):
    from solarapp.db import get_engine
    from solarapp.models import QuickEstimateLog
    with Session(get_engine()) as s:
        s.add(QuickEstimateLog(goal="net_metering", source="fb"))
        s.add(QuickEstimateLog(goal="net_metering", source=""))
        s.commit()
    before = client.get("/api/leads/funnel?days=7").json()
    lid = book(client, name="Funnel Person")
    client.patch(f"/api/leads/{lid}", json={"status": "visit_booked"})
    assert client.post("/api/assessments", json={"customer_name": "Quoted Job", "program": {"stage": "quoted"}}).status_code == 201
    assert client.post("/api/assessments", json={"customer_name": "Signed Job", "program": {"stage": "signed"}}).status_code == 201
    f = client.get("/api/leads/funnel?days=7").json()
    assert f["days"] == 7 and f["estimates"] >= 2 and f["estimates_by_source"]["fb"] >= 1 and f["estimates_by_source"]["direct"] >= 1
    assert f["leads"] == before["leads"] + 1 and f["visits_booked"] == before["visits_booked"] + 1 and f["converted"] == before["converted"]
    assert f["quoted"] >= before["quoted"] + 2 and f["signed"] >= before["signed"] + 1
    client.post(f"/api/leads/{lid}/convert")
    f2 = client.get("/api/leads/funnel?days=7").json()
    assert f2["converted"] == f["converted"] + 1 and f2["visits_booked"] == f["visits_booked"]
    assert client.get("/api/assessments/funnel").status_code in (404, 422)  # gone from the project list


# ---- the stage contract (C1)

def test_job_stage_contract_and_old_records_stay_readable(client):
    from solarapp.schemas import JOB_STAGES, AssessmentDoc, ProgramJob
    assert JOB_STAGES == ["assessed", "quoted", "signed", "sourcing", "installing", "commissioned", "net_metering", "closed"]
    assert ProgramJob(stage="lead").stage == "assessed" and ProgramJob(stage="contacted").stage == "assessed" and ProgramJob(stage="quoted").stage == "quoted"
    with pytest.raises(ValueError):
        ProgramJob(stage="prospect")
    # an old record carrying doc.lead is still readable, and the API reads an old client's "lead" stage as assessed
    old = AssessmentDoc.model_validate({"customer_name": "Old", "program": {"stage": "contacted"}, "lead": {"contact": "0917", "town": "Pila, Laguna", "estimate": {"panels": 5, "price": 150000}}})
    assert old.program.stage == "assessed" and old.lead.contact == "0917" and old.lead.estimate.price == 150000 and old.lead_id is None
    r = client.post("/api/assessments", json={"customer_name": "Old Client", "program": {"stage": "lead"}})
    assert r.status_code == 201 and r.json()["doc"]["program"]["stage"] == "assessed"
    assert client.get("/api/assessments").json()[0]["stage"] in JOB_STAGES


# ---- the startup migration

def _legacy_row(name, stage, *, results=None, lead=None, bills=None, lat=14.233, lon=121.365, notes="", anonymised=False, days_ago=0, address=None):
    from solarapp.models import Assessment
    from solarapp.schemas import AssessmentDoc
    doc = AssessmentDoc(customer_name=name, address=f"{name} St" if address is None else address, notes=notes, lat=lat, lon=lon).model_dump(mode="json")
    doc["program"]["stage"] = stage  # saved by the app before the inbox existed
    if lead is not None:
        doc["lead"] = lead
    if bills:
        doc["audit"]["bills"] = bills
    if anonymised:
        doc["anonymised"] = True
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return Assessment(customer_name=name, address=doc["address"], doc=doc, results=results, created_at=when, updated_at=when)


def test_migration_moves_lead_stage_assessments_to_the_inbox(tmp_path_factory, caplog):
    from solarapp.api.leads import migrate_lead_assessments
    from solarapp.db import get_engine
    from solarapp.models import Assessment, Lead
    root = tmp_path_factory.mktemp("migrate")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = _settings(root)
    with TestClient(create_app(settings)):
        with Session(get_engine()) as s:
            s.add(_legacy_row("Town Lead", "lead", lead={"contact": "0917 1 2 3", "town": "Pila, Laguna", "preferred_time": "Morning", "consent": True, "notice_version": "v1",
                                                         "source": {"utm_source": "fb", "utm_campaign": "c1"}, "estimate": {"goal": "net_metering", "panels": 5, "kwp": 2.9, "price": 160000}},
                              bills=[{"id": "lead", "billing_month": "2026-02", "kwh": 338, "amount_php": 4056}], notes="From the website estimate.", days_ago=40))
            s.add(_legacy_row("Pin Contacted", "contacted", lead={"contact": "ana.fb", "town": "near Tanauan, Batangas", "source": {}, "estimate": {}}, lat=14.1, lon=121.16, days_ago=20,
                              address="Tanauan, Batangas"))  # the old route wrote the town as the address when the visitor gave none
            s.add(_legacy_row("Far Away", "lead", lead={"contact": "x", "town": "outside Laguna and Batangas"}, lat=14.65, lon=121.03))
            s.add(_legacy_row("Gone Already", "lead", lead={"contact": "", "town": "Pila, Laguna"}, anonymised=True, days_ago=400))
            s.add(_legacy_row("Measured Lead", "lead", results={"computed_at": "2026-03-01T00:00:00+00:00", "sizing": {"kwp": 3.0, "panels": 5, "kind": "net_metering"}},
                              lead={"contact": "0918", "town": "Pila, Laguna"}))
            s.add(_legacy_row("Quoted Job", "quoted"))
            s.commit()
    # the app starts again on the same database: the lifespan runs the migration
    with caplog.at_level(logging.INFO, logger="solarapp.audit"):
        with TestClient(create_app(settings)) as c:
            assert any("lead migration: 4 lead-stage assessments moved to the leads inbox, 1 with results kept as projects at stage assessed" in m for m in caplog.messages)
            login(c)
            projects = {a["customer_name"]: a for a in c.get("/api/assessments").json()}
            assert set(projects) == {"Measured Lead", "Quoted Job"}
            assert projects["Measured Lead"]["stage"] == "assessed" and projects["Measured Lead"]["has_results"] and projects["Quoted Job"]["stage"] == "quoted"
            assert c.get(f"/api/assessments/{projects['Measured Lead']['id']}").json()["doc"]["lead"]["contact"] == "0918"  # the old record keeps its lead info
            leads = {l["name"]: l for l in c.get("/api/leads").json()}
            assert set(leads) == {"Town Lead", "Pin Contacted", "Far Away", "Gone Already"}
            t = leads["Town Lead"]
            assert t["status"] == "new" and t["contact"] == "0917 1 2 3" and t["town"] == "Pila" and t["province"] == "Laguna" and t["place"] == "Pila, Laguna" and t["lat"] is None
            assert t["preferred_time"] == "Morning" and t["consent"] and t["notice_version"] == "v1" and t["source_label"] == "fb/c1" and t["notes"] == "From the website estimate."
            assert t["estimate"]["price"] == 160000 and t["estimate"]["monthly_kwh"] == 338 and t["estimate"]["monthly_php"] == 4056
            assert t["created_at"] < leads["Pin Contacted"]["created_at"]  # the original dates survive
            assert t["address"] == "Town Lead St"
            p = leads["Pin Contacted"]
            assert p["status"] == "contacted" and p["town"] == "Tanauan" and p["lat"] == 14.1 and p["place"] == "near Tanauan, Batangas" and p["address"] == ""
            assert leads["Far Away"]["town"] == "" and leads["Far Away"]["lat"] == 14.65 and leads["Far Away"]["place"] == "outside Laguna and Batangas"
            assert leads["Gone Already"]["anonymised"] and not leads["Town Lead"]["anonymised"]
            # idempotent: a second run moves nothing
            with Session(get_engine()) as s:
                assert migrate_lead_assessments(s) == {"moved": 0, "kept": 0}
                assert len(s.exec(select(Lead)).all()) == 4 and len(s.exec(select(Assessment)).all()) == 2
            # the migrated lead converts like any other, with the bill from the old record
            pid = c.post(f"/api/leads/{t['id']}/convert").json()["project_id"]
            doc = c.get(f"/api/assessments/{pid}").json()["doc"]
            assert doc["audit"]["bills"][0]["kwh"] == 338 and doc["audit"]["bills"][0]["amount_php"] == 4056 and doc["lat"] == pytest.approx(14.233)


# ---- retention

def test_retention_anonymises_stale_leads_and_never_projects(client):
    from solarapp.models import Assessment, Lead, QuickEstimateLog
    from solarapp.retention import ANONYMISED_NOTE, run
    old = datetime.now(timezone.utc) - timedelta(days=400)
    with Session(client.app.state.engine) as s:
        stale = Lead(name="Old Lead", contact="0917 1 2 3", town="Pila", province="Laguna", address="Somewhere 12", lat=14.12345, lon=121.12345, preferred_time="Evening",
                     source={"utm_source": "fb"}, estimate={"panels": 5, "price": 150000, "monthly_kwh": 300}, notes="From the website estimate.", status="closed", closed_reason="No reply",
                     created_at=old, updated_at=old)
        kept = Lead(name="Old Customer", contact="0917 9 9 9", town="Pila", province="Laguna", status="converted", project_id=1, created_at=old, updated_at=old)
        fresh = Lead(name="Fresh Lead", contact="0917 4 5 6", town="Pila", province="Laguna", status="new")
        project = Assessment(customer_name="Old Project", address="Kept St", doc={"customer_name": "Old Project", "address": "Kept St", "program": {"stage": "assessed"}}, created_at=old, updated_at=old)
        for row in (stale, kept, fresh, project, QuickEstimateLog(goal="net_metering", created_at=old), QuickEstimateLog(goal="net_metering")):
            s.add(row)
        s.commit()
        sid, kid, fid, pid = stale.id, kept.id, fresh.id, project.id
        preview = run(s, dry_run=True)
        assert preview["anonymised_leads"] == 1 and preview["deleted_estimates"] == 1 and preview["dry_run"]
        s.expire_all()
        assert s.get(Lead, sid).name == "Old Lead"  # the dry run changed nothing
        result = run(s)
        assert result["anonymised_leads"] == 1 and result["deleted_estimates"] == 1
        s.expire_all()
        gone = s.get(Lead, sid)
        assert gone.name == "" and gone.contact == "" and gone.address == "" and gone.preferred_time == "" and gone.notes == ANONYMISED_NOTE
        assert gone.town == "Pila" and gone.province == "Laguna" and gone.estimate["price"] == 150000 and gone.source == {"utm_source": "fb"} and gone.status == "closed"
        assert gone.lat == 14.12 and gone.lon == 121.12 and gone.anonymised_at is not None
        assert s.get(Lead, kid).name == "Old Customer" and s.get(Lead, fid).name == "Fresh Lead"
        assert s.get(Assessment, pid).customer_name == "Old Project" and s.get(Assessment, pid).doc["customer_name"] == "Old Project"
        assert run(s)["anonymised_leads"] == 0  # not counted twice
    r = client.get(f"/api/leads/{sid}").json()
    assert r["anonymised"] and r["name"] == "" and r["place"] == "near Pila, Laguna"
    assert client.post(f"/api/leads/{sid}/convert").status_code == 409
