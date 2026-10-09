from pathlib import Path

import numpy as np
import pytest

from solarapp.core.dataset import PvgisDataset
from solarapp.core.quick import load_profile, quick_estimate
from solarapp.data_download.cli import write_synthetic
from solarapp.pricing.importer import read_workbook
from solarapp.pricing.job import PricingContext
from solarapp.schemas import QuickRequest

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"


@pytest.fixture(scope="module")
def ctx():
    imp = read_workbook(WB)
    return PricingContext(imp.catalog, imp.config)


@pytest.fixture(scope="module")
def pvgis(tmp_path_factory):
    root = tmp_path_factory.mktemp("qdata")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    return PvgisDataset(root)


def test_load_profile_shapes():
    for pat in ("morning", "balanced", "evening"):
        p = load_profile(338, pat)
        assert p.shape == (12, 24) and p[0].sum() == pytest.approx(338 / 30.4)
    assert load_profile(338, "evening")[0, 19] > load_profile(338, "morning")[0, 19]
    assert load_profile(338, "morning")[0, 7] > load_profile(338, "evening")[0, 7]


def test_quick_estimate_end_to_end(ctx, pvgis):
    req = QuickRequest(goal="combination", lat=14.09, lon=121.15, monthly_kwh=338, pattern="evening")
    q = quick_estimate(req, pvgis, ctx)
    sy, pr, ec = q["system"], q["price"], q["economics"]
    assert sy["panels"] > 0 and sy["kwp"] == pytest.approx(sy["panels"] * sy["panel_wp"] / 1000)
    assert sy["inverter_kw"] >= 6 and sy["battery_kwh"] > 0 and sy["roof_area_m2"] > 0
    assert pr["total"] % 1000 == 0 and pr["total"] > 100000
    assert abs(pr["materials"] + pr["labor"] + pr["equipment"] + pr["tax"] - pr["total"]) < 1000
    assert ec and ec["bill_before_monthly"] == pytest.approx(338 * 12.0, rel=0.01) and ec["bill_after_monthly"] < ec["bill_before_monthly"]
    assert ec["payback_years"] is None or ec["payback_years"] > 0
    assert any("net metering" in a for a in q["assumptions"])
    # pesos instead of kWh
    q2 = quick_estimate(QuickRequest(goal="net_metering", lat=14.09, lon=121.15, monthly_php=4056, pattern="balanced"), pvgis, ctx)
    assert q2["inputs"]["monthly_kwh"] == pytest.approx(338) and q2["system"]["battery_kwh"] == 0
    assert any("We read your" in a for a in q2["assumptions"])
    # the evening pattern needs more battery than the morning pattern on the same consumption
    qm = quick_estimate(QuickRequest(goal="combination", lat=14.09, lon=121.15, monthly_kwh=338, pattern="morning"), pvgis, ctx)
    assert qm["system"]["battery_kwh"] <= q["system"]["battery_kwh"]
    with pytest.raises(ValueError):
        quick_estimate(QuickRequest(goal="off_grid", lat=14.09, lon=121.15, pattern="balanced"), pvgis, ctx)


def test_quick_estimate_by_town_with_battery_alternative(ctx, pvgis, monkeypatch):
    from solarapp.core import quick as quick_module
    from solarapp.core.quick import quick_estimate
    from solarapp.schemas import QuickRequest
    q = quick_estimate(QuickRequest(goal="combination", town="Tanauan", province="Batangas", monthly_kwh=338, pattern="evening"), pvgis, ctx)
    assert q["inputs"]["town"] == "Tanauan" and q["inputs"]["in_area"] and q["inputs"]["lat"] == pytest.approx(14.086, abs=0.01)
    alt = q["alternative"]
    assert alt and alt["goal"] == "net_metering" and alt["system"]["battery_kwh"] == 0 and alt["price"]["total"] < q["price"]["total"]
    assert q["price"]["battery_part"] > 0 and q["production"]["production_vs_use_pct"] > 0
    # the whole country is on the map: a pin in Quezon City reads as such
    near = quick_estimate(QuickRequest(goal="net_metering", lat=14.65, lon=121.03, monthly_kwh=338, pattern="balanced"), pvgis, ctx)
    assert near["inputs"]["in_area"] and near["inputs"]["place"].startswith("near Quezon City")
    # a pin far from every town centre (here the middle of Laguna de Bay, with the radius shrunk) is flagged, not refused
    monkeypatch.setattr(quick_module, "OUT_OF_AREA_KM", 1.0)
    far = quick_estimate(QuickRequest(goal="net_metering", lat=14.40, lon=121.20, monthly_kwh=338, pattern="balanced"), pvgis, ctx)
    assert not far["inputs"]["in_area"] and any("off the map of the Philippines" in w for w in far["warnings"])
    with pytest.raises(ValueError):
        quick_estimate(QuickRequest(goal="net_metering", town="Atlantis", monthly_kwh=338), pvgis, ctx)


def test_quick_estimate_refuses_very_small_usage(ctx, pvgis):
    from solarapp.core.quick import MIN_MONTHLY_KWH, TOO_LITTLE
    for req in (QuickRequest(goal="net_metering", town="Pila", province="Laguna", monthly_kwh=50, pattern="balanced"),
                QuickRequest(goal="combination", town="Pila", province="Laguna", monthly_php=150, pattern="balanced")):
        with pytest.raises(ValueError) as e:
            quick_estimate(req, pvgis, ctx)
        assert str(e.value) == TOO_LITTLE and "very little usage" in TOO_LITTLE
    small = quick_estimate(QuickRequest(goal="net_metering", town="Pila", province="Laguna", monthly_kwh=MIN_MONTHLY_KWH, pattern="balanced"), pvgis, ctx)
    assert small["system"]["panels"] >= 1


def test_quick_battery_is_the_priced_unit_and_the_copy_reads_right(ctx, pvgis):
    q = quick_estimate(QuickRequest(goal="combination", town="Tanauan", province="Batangas", monthly_kwh=338, pattern="evening"), pvgis, ctx)
    kwh = q["system"]["battery_kwh"]
    ratings = [i.rating for i in ctx.catalog.by_category("Battery") if i.rating and (i.rating_unit or "").lower() == "kwh"]
    # the figure the visitor sees is units x the catalogue rating of the battery in the price, not the sizing's nominal kWh
    assert kwh >= 0.5 and any(abs(kwh - n * r) < 1e-6 for r in ratings for n in range(1, 9))
    assert q["price"]["battery_part"] > 0 and q["alternative"]["system"]["battery_kwh"] == 0
    assert any(a.startswith("Sized for a house using about 338 kWh a month, mostly in the evening: solar with a battery and net metering.") for a in q["assumptions"])
    assert any("include the " in a and "km trip from Pila, Laguna" in a for a in q["assumptions"])
    # Pila itself: no "0 km trip"
    home = quick_estimate(QuickRequest(goal="net_metering", town="Pila", province="Laguna", monthly_kwh=338, pattern="balanced"), pvgis, ctx)
    assert any(a == "Prices are from our current supplier list; no travel charge within Pila." for a in home["assumptions"])
    assert not any("0 km" in a for a in home["assumptions"])


def test_quick_battery_part_is_the_proposals_battery_figure(ctx, pvgis, monkeypatch):
    """Finance 6: one battery figure. The website's battery_part is the customer's battery line plus VAT, exactly what the
    proposal prints beside the total, no longer the selling price rounded to the hundred."""
    from solarapp.core import quick as quick_module
    from solarapp.core.quick import battery_part_for

    seen = []
    original = quick_module.price_job
    monkeypatch.setattr(quick_module, "price_job", lambda *a, **k: seen.append(original(*a, **k)) or seen[-1])
    q = quick_estimate(QuickRequest(goal="combination", pattern="evening", monthly_kwh=338, monthly_php=3987.17, lat=14.086, lon=121.149), pvgis, ctx)
    priced = seen[0]   # the first pricing is the main (combination) estimate; the no-battery alternative comes after
    battery = [i for s in priced["customer"]["sections"] for i in s["items"] if i["key"] == "Battery"]
    assert len(battery) == 1 and battery[0]["amount"] > 0
    expected = battery[0]["amount"] * (1 + ctx.config.job.vat)
    assert q["price"]["battery_part"] == pytest.approx(expected)
    assert battery_part_for(priced, ctx.config.job.vat) == pytest.approx(expected)
    # the customer line carries the battery's freight and commission shares, so it is more than the selling price alone
    selling = sum(float(l["selling"]) for l in priced["lines"] if l["category"] == "Battery")
    assert expected > selling * (1 + ctx.config.job.vat)
    # the economics behind the website figures follow the same warranty rule as the proposal
    assert q["economics"]["payback_years"] > 0
