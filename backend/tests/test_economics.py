import pytest

from solarapp.pricing.config import PricingConfig
from solarapp.pricing.economics import _irr, _npv, _payback, build_economics
from solarapp.schemas import AssessmentDoc


def _results(kind="combination", contract=266900.0, export=120.0, imp=80.0):
    monthly = [{"month": m, "days": 30, "consumption_kwh": 338.0, "production_kwh": 480.0, "direct_kwh": 150.0, "battery_kwh": 100.0,
                "export_kwh": export, "curtailed_kwh": 0.0, "import_kwh": imp, "unserved_kwh": 0.0} for m in range(1, 13)]
    sections = [{"key": "materials", "items": [{"key": "Solar Panel", "amount": 44787.0}, {"key": "Inverter", "amount": 29806.0}, {"key": "Battery", "amount": 91205.0}]}]
    return {"sizing": {"kind": kind, "monthly": monthly, "annual_production_kwh": 5760.0},
            "pricing": {"available": True, "totals": {"contract_rounded": contract}, "customer": {"sections": sections}}}


def test_helpers():
    assert _npv(0.0, [-100, 60, 60]) == pytest.approx(20)
    assert _irr([-100, 60, 60]) == pytest.approx(0.1307, abs=1e-3)
    assert _payback([-100, -40, 20, 80]) == pytest.approx(1 + 40 / 60)
    assert _payback([-100, -50, -10]) is None


def test_economics_from_bill_tariff():
    doc = AssessmentDoc()
    doc.audit.bills = [{"id": "b1", "billing_month": "2026-08", "kwh": 338, "days": 31, "amount_php": 3987.17, "utility": "BATELEC II"}]
    doc = AssessmentDoc.model_validate(doc.model_dump())
    cfg = PricingConfig()
    eco = build_economics(doc, _results(), cfg)
    assert eco["available"]
    a = eco["assumptions"]
    assert a["tariff_php_per_kwh"] == pytest.approx(3987.17 / 338) and a["tariff_source"] == "bill 2026-08"
    tariff = a["tariff_php_per_kwh"]
    m = eco["monthly"][0]
    assert m["bill_before"] == pytest.approx(338 * tariff)
    assert m["bill_after"] == pytest.approx(max(80 * tariff - 120 * 6.5, 0))
    assert eco["year1"]["savings"] == pytest.approx(12 * (m["bill_before"] - m["bill_after"]))
    assert eco["bill_after_monthly"] < eco["bill_before_monthly"]
    assert eco["bill_today_monthly"] == pytest.approx(3987.17) and eco["bill_today_kwh"] == 338 and not eco["includes_future_loads"]
    yrs = eco["years"]
    assert len(yrs) == 25 and yrs[0]["savings"] == pytest.approx(eco["year1"]["savings"])
    assert yrs[1]["savings"] == pytest.approx(eco["year1"]["savings"] * 0.995 * 1.03)
    assert "battery replacement" in yrs[9]["note"] and yrs[9]["costs"] > 91000
    assert "inverter replacement" in yrs[11]["note"]
    assert yrs[0]["costs"] == pytest.approx(266900 * 0.005)
    assert eco["payback_years"] is not None and 3 < eco["payback_years"] < 15
    assert eco["lifetime_net"] == pytest.approx(yrs[-1]["cumulative"])
    assert eco["irr"] is not None and eco["irr"] > 0.05
    assert eco["lcoe_php_per_kwh"] is not None and 0 < eco["lcoe_php_per_kwh"] < tariff
    assert eco["co2_t_per_year"] == pytest.approx(5760 * 0.71 / 1000)


def test_economics_overrides_and_off_grid():
    doc = AssessmentDoc()
    cfg = PricingConfig()
    eco = build_economics(doc, _results(), cfg)
    assert eco["assumptions"]["tariff_source"] == "setting" and eco["assumptions"]["tariff_php_per_kwh"] == 12.0
    doc.economics.tariff_php_per_kwh = 15.0
    doc.economics.export_rate_php_per_kwh = 0.0
    doc.economics.analysis_years = 10
    doc.economics.om_per_year = 0.0
    doc.economics.battery_life_years = 20
    eco2 = build_economics(doc, _results(), cfg)
    assert eco2["assumptions"]["tariff_source"] == "entered" and len(eco2["years"]) == 10
    assert eco2["monthly"][0]["bill_after"] == pytest.approx(80 * 15.0)
    assert all(r["costs"] == 0 for r in eco2["years"])  # no O&M, no replacement within 10 years
    # off-grid: no grid bill at all, export credit ignored
    off = build_economics(AssessmentDoc(), _results(kind="off_grid"), cfg)
    assert off["bill_after_monthly"] == 0 and off["assumptions"]["export_rate_php_per_kwh"] == 0
    assert off["year1"]["savings"] == pytest.approx(12 * 338 * 12.0)
    # unavailable without pricing
    r = _results(); r["pricing"] = {"available": False}
    assert not build_economics(AssessmentDoc(), r, cfg)["available"]
