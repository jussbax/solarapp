"""Round 13, step 1 (brief 6.4): the signing engineer's profile fields round-trip through Settings and stay off the public
profile; the title block prints the signature block's lines with BLANK where the profile is empty and the full lines
when filled, the owner and the kind in the project cell; the plans' first build sets `plans_issued_at` (revision 0)
and the second leaves it; "Issue a revision" appends to the append-only log and prints "Rev. 1" on every sheet and in
the cover's table; "Reopen design" leaves the log; an older database gets the two columns at start-up."""
import shutil
import subprocess
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.db import ensure_columns
from solarapp.main import create_app
from solarapp.models import Assessment
from solarapp.profile import PEE_KEYS, PROFILE_KEYS, PUBLIC_KEYS
from solarapp.reports.plans_pdf import BLANK
from tests.test_drawings import PILA_DOC

PEE = {
    "pee_name": "Juan dela Cruz", "pee_license": "0012345", "pee_prc_valid_until": "31 Dec 2028", "pee_ptr_no": "7654321", "pee_ptr_date": "5 Jan 2026",
    "pee_ptr_place": "Pila, Laguna", "pee_tin": "123-456-789-000", "pee_address": "Brgy. Santa Clara Sur, Pila, Laguna", "pee_firm": "sole practice",
    "pee_firm_address": "", "pee_phone": "0917 000 0000", "pee_email": "pee@example.com",
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


def _pdf_text(pdf: bytes) -> str:
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    return subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode()


def _pages(text: str) -> list[str]:
    return [p for p in text.split("\f") if p.strip()]


def _computed(client: TestClient) -> int:
    aid = client.post("/api/assessments", json=deepcopy(PILA_DOC)).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    return aid


def test_the_signing_engineers_fields_round_trip_and_stay_off_the_public_profile(client):
    assert set(PEE_KEYS) <= set(PROFILE_KEYS) and not (set(PEE_KEYS) - {"pee_name", "pee_license"}) & set(PUBLIC_KEYS)
    assert client.put("/api/settings", json=PEE).status_code == 200
    got = client.get("/api/settings").json()
    assert {k: got[k] for k in PEE} == PEE
    pub = client.get("/api/quick/status").json()["profile"]
    assert pub["pee_name"] == "Juan dela Cruz" and "pee_tin" not in pub and "pee_ptr_no" not in pub and "pee_address" not in pub
    # back to blank for the next test: a blank is stored as a blank, not as a default
    assert client.put("/api/settings", json={k: "" for k in PEE}).status_code == 200
    assert all(client.get("/api/settings").json()[k] == "" for k in PEE)


def test_the_title_block_prints_blank_lines_then_the_full_lines(client):
    aid = _computed(client)
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 200
    pages = _pages(_pdf_text(r.content))
    flat = lambda s: " ".join(s.split())  # noqa: E731
    for page in pages:
        # the signature block: every line present, every field a blank line
        assert "Signed and sealed by the Professional Electrical Engineer" in page
        assert f"{BLANK}, PEE — PRC No. {BLANK}, valid until {BLANK}" in flat(page)
        assert f"PTR No. {BLANK}, issued {BLANK} at {BLANK}" in flat(page) and f"TIN {BLANK}" in page
        assert "Signature " + BLANK in page and "Seal" in page
        # the owner and the kind in the project cell, the revision line beside the calculation stamp
        assert "Owner: Maria Santos" in page and "Hybrid: grid-interactive with a battery (net metering)" in page
        assert "Rev. 0: first issue" in page and "calculated" in page
    # the last sheet names the blank fields and where to type them
    assert "Signing engineer's details in the title block" in pages[-1] and "Settings › Company › Signing engineer" in flat(pages[-1])
    assert "PTR number" in flat(pages[-1]) and "TIN" in flat(pages[-1])
    # the cover: the sheet index and the revision log with the first issue
    cover = flat(pages[0])
    assert "Sheets in this set" in cover and "Sheet 1 Cover and general notes" in cover and f"Sheet {len(pages)} Not yet in this set" in cover
    assert "Revisions" in cover and "0 " in cover and "first issue" in cover

    client.put("/api/settings", json=PEE)
    try:
        pages = _pages(_pdf_text(client.get(f"/api/assessments/{aid}/plans.pdf").content))
        for page in pages:
            assert "Juan dela Cruz, PEE — PRC No. 0012345, valid until 31 Dec 2028" in flat(page)
            assert "PTR No. 7654321, issued 5 Jan 2026 at Pila, Laguna" in flat(page) and "TIN 123-456-789-000" in page
            assert "Brgy. Santa Clara Sur, Pila, Laguna · sole practice" in flat(page)
            assert f"{BLANK} · 0917 000 0000 · pee@example.com" in flat(page)   # the firm's address alone is blank
        # the last sheet names only the one field still blank
        assert "Signing engineer: Firm's address." in flat(pages[-1]) and "PTR number" not in flat(pages[-1])
    finally:
        client.put("/api/settings", json={k: "" for k in PEE})


def test_the_first_build_issues_revision_0_and_a_revision_prints_on_every_sheet(client):
    aid = _computed(client)
    out = client.get(f"/api/assessments/{aid}").json()
    assert out["plans_issued_at"] is None and out["revisions"] == []
    # a revision cannot be issued before the first issue
    r = client.post(f"/api/assessments/{aid}/revisions", json={"note": "x"})
    assert r.status_code == 409 and "revision 0" in r.json()["detail"]
    assert client.get(f"/api/assessments/{aid}/plans.pdf").status_code == 200
    out = client.get(f"/api/assessments/{aid}").json()
    first = out["plans_issued_at"]
    assert first is not None and out["plans_issued_by"] == "u"   # review finding 14: the signed-in person who first built the set
    assert client.get(f"/api/assessments/{aid}/plans.pdf").status_code == 200
    assert client.get(f"/api/assessments/{aid}").json()["plans_issued_at"] == first   # the second build keeps the first date
    # a note is required
    assert client.post(f"/api/assessments/{aid}/revisions", json={"note": "   "}).status_code == 422
    assert client.post(f"/api/assessments/{aid}/revisions", json={}).status_code == 422
    r = client.post(f"/api/assessments/{aid}/revisions", json={"note": "busbar and main breaker surveyed"})
    assert r.status_code == 200, r.text
    revs = r.json()["revisions"]
    assert len(revs) == 1 and revs[0]["no"] == 1 and revs[0]["note"] == "busbar and main breaker surveyed" and revs[0]["by"] == "u" and revs[0]["date"]
    assert r.json()["plans_issued_at"] == first and r.json()["results_stale"] is False   # a revision is a record, not an input
    pages = _pages(_pdf_text(client.get(f"/api/assessments/{aid}/plans.pdf").content))
    flat = lambda s: " ".join(s.split())  # noqa: E731
    for page in pages:
        assert "Rev. 1: busbar and main breaker surveyed —" in flat(page) and "Rev. 0" not in page
    cover = flat(pages[0])
    assert "Revisions" in cover and "first issue u" in cover and "1 " in cover and "busbar and main breaker surveyed" in cover and " u" in cover   # Rev. 0's "By" and Rev. 1's
    # the log is append-only and "Reopen design" leaves it
    r = client.post(f"/api/assessments/{aid}/revisions", json={"note": "inverter moved to the utility room"})
    assert [x["no"] for x in r.json()["revisions"]] == [1, 2]
    r = client.post(f"/api/assessments/{aid}/reopen")
    assert r.status_code == 200 and [x["no"] for x in r.json()["revisions"]] == [1, 2] and r.json()["plans_issued_at"] == first
    pages = _pages(_pdf_text(client.get(f"/api/assessments/{aid}/plans.pdf").content))
    assert all("Rev. 2: inverter moved to the utility room" in flat(p) for p in pages)
    assert "Rev. 0" not in flat(pages[1])


def test_an_older_database_gets_the_revision_columns_at_start_up(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE assessments (id INTEGER PRIMARY KEY, created_at DATETIME, updated_at DATETIME, customer_name VARCHAR, address VARCHAR, "
                          "doc JSON NOT NULL, results JSON, results_stale BOOLEAN, proposal_issued_at DATETIME)"))
        conn.execute(text("INSERT INTO assessments (id, created_at, updated_at, customer_name, address, doc, results_stale) VALUES (1, '2026-01-01', '2026-01-01', 'Old', '', '{}', 0)"))
    added = ensure_columns(engine, "assessments", Assessment)
    assert {"plans_issued_at", "plans_issued_by", "revisions"} <= set(added) and ensure_columns(engine, "assessments", Assessment) == []
    from sqlmodel import Session

    with Session(engine) as s:
        a = s.get(Assessment, 1)
        assert a.plans_issued_at is None and a.plans_issued_by is None and a.revisions is None   # reads as "Rev. 0", an empty log, the By a blank line
