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
    # no export: the grid bills what it still supplies at the tariff, and the surplus earns nothing
    off = build_economics(AssessmentDoc(), _results(kind="off_grid"), cfg)
    assert off["assumptions"]["export_rate_php_per_kwh"] == 0 and off["year1"]["export_credit"] == 0
    assert off["bill_after_monthly"] == pytest.approx(off["year1"]["import_kwh"] / 12 * 12.0)
    assert off["year1"]["savings"] == pytest.approx(12 * 338 * 12.0 - off["year1"]["import_kwh"] * 12.0)
    # unavailable without pricing
    r = _results(); r["pricing"] = {"available": False}
    assert not build_economics(AssessmentDoc(), r, cfg)["available"]


def test_battery_life_follows_the_warranty_and_replacements_carry_vat():
    """Finance 2 and 5, the owner's decision 3: the battery warranty in the company profile (5 years) is the battery life
    unless a setting or the job overrides it; the inverter life stays the 12-year setting (a service life, not its 5-year
    warranty); replacements cost the proposal's line plus VAT plus the replacement-labor setting (0 by default)."""
    doc = AssessmentDoc()
    cfg = PricingConfig()
    assert cfg.economics.battery_life_years_override == 0 and cfg.economics.inverter_life_years == 12 and cfg.economics.replacement_labor_php == 0
    profile = {"warranty_battery_years": "5", "warranty_inverter_years": "5"}
    eco = build_economics(doc, _results(), cfg, profile)
    a = eco["assumptions"]
    assert a["battery_life_years"] == 5 and a["battery_life_source"] == "battery warranty" and a["inverter_life_years"] == 12
    assert a["battery_replacement_cost"] == pytest.approx(91205.0 * 1.12)
    assert a["inverter_replacement_cost"] == pytest.approx(29806.0 * 1.12)
    assert a["replacement_labor_php"] == 0 and a["replacement_vat"] == 0.12
    notes = {r["year"]: r["note"] for r in eco["years"]}
    assert [y for y, n in notes.items() if "battery replacement" in n] == [5, 10, 15, 20]   # four in 25 years, never in the last
    assert [y for y, n in notes.items() if "inverter replacement" in n] == [12, 24]
    assert eco["years"][4]["costs"] == pytest.approx(266900 * 0.005 * 1.03 ** 4 + 91205.0 * 1.12)
    assert not any(w["code"] == "battery_life_verify" for w in eco["warnings"])
    # a stored config from before this rule still carries battery_life_years = 10: it is dropped, the warranty rule applies
    old = PricingConfig.model_validate({"economics": {"battery_life_years": 10}})
    assert old.economics.battery_life_years_override == 0 and not hasattr(old.economics, "battery_life_years")
    assert build_economics(doc, _results(), old, profile)["assumptions"]["battery_life_years"] == 5
    # two more replacements than the old 10-year life: the 25-year net is lower, never silently higher
    ten = PricingConfig()
    ten.economics.battery_life_years_override = 10
    assert eco["lifetime_net"] < build_economics(doc, _results(), ten, profile)["lifetime_net"]
    # the settings override wins over the warranty, the job's own figure over both; labor rides on every replacement
    cfg.economics.battery_life_years_override = 8
    cfg.economics.replacement_labor_php = 2500
    eco8 = build_economics(doc, _results(), cfg, profile)
    assert eco8["assumptions"]["battery_life_years"] == 8 and eco8["assumptions"]["battery_life_source"] == "setting"
    assert eco8["assumptions"]["battery_replacement_cost"] == pytest.approx(91205.0 * 1.12 + 2500)
    assert eco8["assumptions"]["inverter_replacement_cost"] == pytest.approx(29806.0 * 1.12 + 2500)
    doc.economics.battery_life_years = 7
    assert build_economics(doc, _results(), cfg, profile)["assumptions"]["battery_life_source"] == "entered"
    # a blank warranty: the profile's default with a verify warning, never a silent number; no profile at all reads the same
    blank = build_economics(AssessmentDoc(), _results(), PricingConfig(), {"warranty_battery_years": ""})
    assert blank["assumptions"]["battery_life_years"] == 5 and blank["assumptions"]["battery_life_source"] == "assumed"
    assert any(w["code"] == "battery_life_verify" for w in blank["warnings"])
    assert build_economics(AssessmentDoc(), _results(), PricingConfig())["assumptions"]["battery_life_source"] == "assumed"


def test_export_credit_from_the_bills_generation_charge():
    """The assessor types the generation charge off the bill; the DU credits exports at that rate, not the settings' figure."""
    doc = AssessmentDoc()
    doc.audit.bills = [
        {"id": "b1", "billing_month": "2026-07", "kwh": 330, "amount_php": 3900.0, "utility": "BATELEC II", "generation_rate_php_per_kwh": 6.12},
        {"id": "b2", "billing_month": "2026-08", "kwh": 338, "amount_php": 3987.17, "utility": "BATELEC II", "generation_rate_php_per_kwh": 5.98},
    ]
    doc = AssessmentDoc.model_validate(doc.model_dump())
    cfg = PricingConfig()
    eco = build_economics(doc, _results(), cfg)
    a = eco["assumptions"]
    assert a["export_rate_php_per_kwh"] == pytest.approx(5.98) and a["export_rate_source"] == "bill 2026-08"   # the latest bill's rate
    assert eco["monthly"][0]["bill_after"] == pytest.approx(max(80 * a["tariff_php_per_kwh"] - 120 * 5.98, 0))
    assert not [w for w in eco["warnings"] if w["code"] == "export_rate_default"]
    # the job's own figure wins over the bill
    doc.economics.export_rate_php_per_kwh = 7.0
    a2 = build_economics(doc, _results(), cfg)["assumptions"]
    assert a2["export_rate_php_per_kwh"] == 7.0 and a2["export_rate_source"] == "entered"
    # no generation charge typed: the settings' figure, and a warning on a grid job but not on a no-export one
    plain = AssessmentDoc()
    plain.audit.bills = [{"id": "b1", "billing_month": "2026-08", "kwh": 338, "amount_php": 3987.17, "utility": ""}]
    plain = AssessmentDoc.model_validate(plain.model_dump())
    eco3 = build_economics(plain, _results(), cfg)
    assert eco3["assumptions"]["export_rate_php_per_kwh"] == 6.5 and eco3["assumptions"]["export_rate_source"] == "setting"
    assert any(w["code"] == "export_rate_default" for w in eco3["warnings"])
    assert not any(w["code"] == "export_rate_default" for w in build_economics(plain, _results(kind="off_grid"), cfg)["warnings"])
