"""The website side: the site build, the website address setting and the lead email."""
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.notify import lead_notice
from solarapp.schemas import LeadEstimate

ROOT = Path(__file__).resolve().parent.parent.parent
SITE = ROOT / "site"


@pytest.fixture(scope="module")
def build():
    spec = importlib.util.spec_from_file_location("site_build", SITE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- site/build.py: placeholders out of the public build, absolute share addresses on request

def test_public_build_drops_placeholders_and_keeps_them_on_request(build):
    layout = (SITE / "layout.html").read_text(encoding="utf-8")
    for page, marker in (("index.html", "Recent installations"), ("about.html", "Photo: the owner")):
        src = (SITE / "pages" / page).read_text(encoding="utf-8")
        assert "<!-- placeholder:start -->" in src and marker in src
        public = build.render_page(layout, SITE / "pages" / page)
        assert marker not in public and "Replace this" not in public and "placeholder" not in public
        preview = build.render_page(layout, SITE / "pages" / page, with_placeholders=True)
        assert marker in preview
    # the public home page still has its real sections and the layout's frame
    home = build.render_page(layout, SITE / "pages" / "index.html")
    assert "What you get on paper" in home and "How it works" in home and "Solar engineering for homes" in home
    assert "Contact details appear here" not in home


def test_build_base_url_writes_absolute_og_tags(build):
    layout = (SITE / "layout.html").read_text(encoding="utf-8")
    relative = build.render_page(layout, SITE / "pages" / "about.html")
    assert '<meta property="og:image" content="/brand/icon-512.png" />' in relative and "og:url" not in relative
    absolute = build.render_page(layout, SITE / "pages" / "about.html", base_url="https://pldevinc.com/")
    assert '<meta property="og:image" content="https://pldevinc.com/brand/icon-512.png" />' in absolute
    assert '<meta property="og:url" content="https://pldevinc.com/about" />' in absolute
    home = build.render_page(layout, SITE / "pages" / "index.html", base_url="https://pldevinc.com")
    assert '<meta property="og:url" content="https://pldevinc.com/" />' in home


def test_build_writes_every_page(build, tmp_path):
    out = tmp_path / "dist"
    pages = build.build(out, base_url="https://pldevinc.com")
    assert set(pages) >= {"index.html", "about.html", "estimate.html", "net-metering.html", "brownouts.html", "privacy.html", "404.html"}
    assert (out / "static" / "site.css").is_file() and (out / "static" / "site.js").is_file()
    estimate = (out / "estimate.html").read_text(encoding="utf-8")
    assert 'data-embedded="true"' in estimate
    css = (out / "static" / "site.css").read_text(encoding="utf-8")
    assert "[data-warranty-wrap].is-empty { display: none; }" in css


# ---- the website address: the card's QR and the widget's summary point at the website's estimate page

def test_website_url_setting_and_estimate_url():
    base = dict(data_dir=Path("x"), secret_key="s" * 32)
    assert Settings(**base).estimate_url == ""
    assert Settings(**base, public_url="https://solar.pldevinc.com").estimate_url == "https://solar.pldevinc.com/estimate"
    # the first public origin is the website unless told otherwise
    s = Settings(**base, public_origins="https://pldevinc.com, https://www.pldevinc.com", public_url="https://solar.pldevinc.com")
    assert s.website_base == "https://pldevinc.com" and s.estimate_url == "https://pldevinc.com/estimate"
    s = Settings(**base, website_url="https://www.pldevinc.com/", public_origins="https://pldevinc.com", public_url="https://solar.pldevinc.com")
    assert s.estimate_url == "https://www.pldevinc.com/estimate"
    # the estimate-only host (single-container fallback) serves the estimate at its root
    s = Settings(**base, public_host="pldevinc.com", public_url="https://solar.pldevinc.com")
    assert s.estimate_url == "https://pldevinc.com"
    assert Settings(**base, website_url="https://pldevinc.com", public_host="pldevinc.com").estimate_url == "https://pldevinc.com/estimate"


# ---- the lead email, one fact per line

def test_lead_notice_reads_line_by_line():
    est = LeadEstimate(goal="net_metering", panels=5, kwp=2.92, battery_kwh=0, price=161000, bill_before_monthly=4002, bill_after_monthly=516, payback_years=3.8)
    subject, body = lead_notice(
        name="Maria Santos", contact="0917 555 1234", preferred_time="Evening", wants="a lower bill, no battery", uses="spread through the day",
        kwh=333, monthly_php=4000, estimate=est, place="Pila, Laguna", pin_placed=False, address="", source="fb/audit",
        link="https://solar.pldevinc.com/?booking=1", promise="within one working day",
    )
    assert subject == "New lead: Maria Santos, 0917 555 1234, Pila (evening)"
    assert body.splitlines() == [
        "Name: Maria Santos",
        "Contact: 0917 555 1234, best time evening",
        "Wants: a lower bill, no battery",
        "Uses power: spread through the day",
        "Bill: about 333 kWh (₱4,000)",
        "Saw on the website: 5 panels, 2.92 kWp, ₱161,000, bill ₱4,002 → about ₱516, pays for itself in 3.8 years",
        "Location: Pila, Laguna",
        "Source: fb/audit",
        "Open: https://solar.pldevinc.com/?booking=1",
        "The thank-you page promised a message or call within one working day.",
    ]
    # a battery, a pin, an address, no preferred time, no estimate seen
    est2 = LeadEstimate(goal="combination", panels=1, kwp=0.59, battery_kwh=10.24, price=250000)
    subject, body = lead_notice(
        name="Jose", contact="jose.fb", preferred_time="", wants="a lower bill and backup in brownouts", uses="mostly in the evening",
        kwh=120, monthly_php=None, estimate=est2, place="near Pila, Laguna", pin_placed=True, address="Brgy. Labuin, beside the chapel",
        source="direct", link="booking #2", promise="the same day",
    )
    assert subject == "New lead: Jose, jose.fb, near Pila"
    lines = body.splitlines()
    assert lines[1] == "Contact: jose.fb" and lines[4] == "Bill: about 120 kWh"
    assert lines[5] == "Saw on the website: 1 panel, 0.59 kWp, 10 kWh battery, ₱250,000"
    assert lines[6] == "Address: Brgy. Labuin, beside the chapel"
    assert lines[7] == "Location: near Pila, Laguna; pin placed by the customer, confirm on the visit"
    assert lines[-1] == "The thank-you page promised a message or call the same day."
    _, body = lead_notice(name="A", contact="b", preferred_time="", wants="w", uses="u", kwh=100, monthly_php=None, estimate=LeadEstimate(),
                          place="Pila, Laguna", pin_placed=False, address="", source="direct", link="l", promise="p")
    assert "Saw on the website" not in body


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("sitedata")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic",
                        public_url="https://solar.pldevinc.com", smtp_host="smtp.example.test", notify_email="owner@example.test")
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def test_lead_route_sends_the_line_by_line_notice(client, monkeypatch):
    sent = []
    monkeypatch.setattr("solarapp.api.quick_routes.send_lead_notice", lambda settings, subject, body: sent.append((subject, body)) or True)
    r = client.post("/api/quick/lead", json={
        "goal": "net_metering", "town": "Pila", "province": "Laguna", "monthly_kwh": 333, "monthly_php": 4000, "pattern": "balanced",
        "name": "Maria Santos", "contact": "0917 555 1234", "preferred_time": "Evening", "consent": True,
        "source": {"utm_source": "fb", "utm_campaign": "audit"},
        "estimate": {"goal": "net_metering", "panels": 5, "kwp": 2.92, "battery_kwh": 0, "price": 161000, "bill_before_monthly": 4002, "bill_after_monthly": 516, "payback_years": 3.8},
    }, headers={"X-Visitor": "t1"})
    assert r.status_code == 200, r.text
    assert len(sent) == 1
    subject, body = sent[0]
    assert subject == "New lead: Maria Santos, 0917 555 1234, Pila (evening)"
    assert "Wants: a lower bill, no battery\nUses power: spread through the day\nBill: about 333 kWh (₱4,000)\n" in body
    assert "Saw on the website: 5 panels, 2.92 kWp, ₱161,000, bill ₱4,002 → about ₱516, pays for itself in 3.8 years\n" in body
    # the link opens the booking under Projects (the hand-off), not a project of its own
    assert f"Source: fb/audit\nOpen: https://solar.pldevinc.com/?booking={r.json()['id']}\n" in body
    assert body.endswith("The thank-you page promised a message or call within one working day.\n")
    client.post("/api/auth/login", json={"username": "u", "password": "p"})
    assert client.get(f"/api/leads/{r.json()['id']}").json()["name"] == "Maria Santos"
    assert client.get("/api/assessments").json() == []


def test_unavailable_message_leaves_the_contact_channel_to_the_page():
    from solarapp.api import quick_routes
    assert "Facebook" not in quick_routes.UNAVAILABLE


# ---- the net-metering page's illustration figures are the engine's (the report's example: 500 kWh, Tanauan, mostly evening)

NET_METERING_EXAMPLE = dict(goal="net_metering", town="Tanauan", province="Batangas", monthly_kwh=500, pattern="evening")


def _tiles() -> list[str]:
    import re
    page = (SITE / "pages" / "net-metering.html").read_text(encoding="utf-8")
    return re.findall(r'<div class="big">(.*?)</div><div class="lab">(.*?)</div>', page)


def test_net_metering_page_names_its_example_and_four_tiles():
    tiles = _tiles()
    assert [lab for _, lab in tiles][:4] == ["7 panels", "installed, VAT included", "pays for itself", "off the bill"]
    page = (SITE / "pages" / "net-metering.html").read_text(encoding="utf-8")
    assert "500 kWh a month, mostly in the evening, net metering without a battery" in page
    assert "three quarters" not in page and "about 3 years" not in page


def test_net_metering_page_figures_match_the_engine():
    """Runs the page's own example through the engine on the real weather (SOLARAPP_DATA_DIR, or <repo>/data); skipped on test weather."""
    import os

    from solarapp.core import quick
    from solarapp.core.dataset import PvgisDataset
    from solarapp.core.quick import quick_estimate
    from solarapp.pricing.importer import read_workbook
    from solarapp.pricing.job import PricingContext
    from solarapp.schemas import QuickRequest

    root = Path(os.environ.get("SOLARAPP_DATA_DIR") or ROOT / "data")
    pvgis = PvgisDataset(root) if root.is_dir() else None
    if pvgis is None or not pvgis.available or pvgis.synthetic:
        pytest.skip("the page's figures are checked against the real PVGIS weather only")
    quick._per_kwp_cache.clear()   # keyed by cell id: the synthetic datasets of the other tests share ids with the real one
    imp = read_workbook(ROOT / "backend" / "data_seed" / "PLD_Materials_DB.xlsx")
    q = quick_estimate(QuickRequest(**NET_METERING_EXAMPLE), pvgis, PricingContext(imp.catalog, imp.config))
    big = {lab: val for val, lab in _tiles()}
    assert big["7 panels"] == f"{q['system']['kwp']:.1f} kWp" and q["system"]["panels"] == 7
    assert big["installed, VAT included"] == f"about ₱{q['price']['total']:,.0f}"
    e = q["economics"]
    assert big["pays for itself"] == "under 4 years" and e["payback_years"] < 4
    cut = (1 - e["bill_after_monthly"] / e["bill_before_monthly"]) * 100
    assert big["off the bill"] == "about two thirds" and 60 <= cut <= 72
