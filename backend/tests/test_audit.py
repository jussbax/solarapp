import numpy as np
import pytest

from solarapp.core.audit import Appliance, Bill, Window, build_profile, run_audit, window_mask


def test_window_mask_wraps_midnight():
    m = window_mask("18:00", "06:00")
    assert m.sum() == 12 * 60 and m[0] and m[18 * 60] and not m[12 * 60]
    assert window_mask("06:00", "06:00").sum() == 1440
    assert window_mask("07:00", "07:30").sum() == 30


def test_profile_energy_and_hours():
    a = Appliance("a", "LED bulb", "lighting", 9, quantity=9, windows=[Window("18:00", "06:00")])
    p = build_profile(a)
    assert abs(p.hours_per_day - 12) < 1e-9
    daily_wh = p.energy_wh[0].sum(axis=1).mean()
    assert abs(daily_wh - 9 * 9 * 12) < 1e-6
    assert p.nameplate_w.max() == 81


def test_days_and_months_filters():
    a = Appliance("a", "Washer", "washing_machine", 500, windows=[Window("06:00", "07:30", days=[5, 6], months=[1])])
    p = build_profile(a)
    assert p.energy_wh[0, 0].sum() == 0 and p.energy_wh[0, 5].sum() > 0
    assert p.energy_wh[1].sum() == 0
    assert abs(p.hours_per_day - 1.5 * 2 / 7) < 1e-9


def test_nameplate_warning():
    p = build_profile(Appliance("a", "Top load washer", "washing_machine", 9014, windows=[Window("06:00", "07:30")]))
    assert any(w["code"] == "nameplate_out_of_range" for w in p.warnings)


def tanauan_appliances():
    allday = Window("06:00", "06:00")
    return [
        Appliance("ref", "Refrigerator", "refrigerator", 150, windows=[allday]),
        Appliance("ac", "Split inverter AC 2.5HP", "aircon_inverter", 2100, quantity=2, windows=[Window("08:00", "01:00")]),
        Appliance("tv", "Television", "tv", 74, quantity=2, windows=[Window("07:00", "15:00"), Window("19:00", "22:00")]),
        Appliance("led", "LED bulb", "lighting", 9, quantity=9, windows=[Window("18:00", "06:00")]),
        Appliance("rice", "Rice cooker", "rice_cooker", 1000, windows=[Window("07:00", "07:30"), Window("12:00", "12:30"), Window("19:00", "19:30")]),
        Appliance("iron", "Steam iron", "steam_iron", 1200, windows=[Window("07:00", "07:30")]),
        Appliance("wifi", "Router", "router_network", 12, windows=[allday]),
        Appliance("wac", "Window inverter 0.5HP", "aircon_inverter", 1119, windows=[Window("18:00", "06:00")]),
        Appliance("disp", "Water dispenser", "water_dispenser", 500, windows=[allday]),
        Appliance("wash", "Top load washer", "washing_machine", 500, windows=[Window("06:00", "07:30", days=[5, 6])]),
        Appliance("kettle", "Kettle", "electric_kettle", 2000, windows=[Window("06:00", "06:30")]),
        Appliance("fan", "Stand fan", "fan", 55, windows=[allday]),
        Appliance("pw", "Pressure washer", "pressure_washer", 2200, windows=[Window("15:00", "16:00", days=[5, 6])]),
    ]


def test_tanauan_reconciles_to_bill():
    bills = [Bill("b1", "2026-08", 338.0, days=31)]
    res = run_audit(tanauan_appliances(), bills)
    avb = res.audit_vs_bill
    assert avb is not None and avb["reconciled"]
    assert avb["audit_kwh"] > 600  # typed audit overstates badly even with duty factors
    assert abs(avb["bills"][0]["reconciled_kwh"] - 338.0) < 0.01
    assert avb["scale_uncertain"] == pytest.approx(0.15)  # aircon floor hit
    assert any(w["code"] == "reconcile_floor" for w in res.warnings)
    assert any(w["code"] == "audit_gap" for w in res.warnings)
    # sizing profile integrates to the bill month daily consumption
    assert abs(res.daily_kwh_by_month[7] * 31 - 338.0) < 0.01
    assert res.load_kw.shape == (12, 24)
    assert res.peak_kw > res.peak_avg_kw > 0
    # fixed appliances keep their relative share: lights scale == scale_all
    led = next(r for r in res.appliances if r["id"] == "led")
    assert led["scale"] == pytest.approx(avb["scale_all"])
    ac = next(r for r in res.appliances if r["id"] == "ac")
    assert ac["scale"] == pytest.approx(avb["scale_all"] * 0.15)


def test_understated_audit_scales_up_within_ceiling():
    apps = [
        Appliance("ref", "Refrigerator", "refrigerator", 150, windows=[Window("06:00", "06:00")]),
        Appliance("led", "LED bulb", "lighting", 9, quantity=5, windows=[Window("18:00", "22:00")]),
    ]
    res = run_audit(apps, [Bill("b", "2026-03", 200.0, days=31)])
    avb = res.audit_vs_bill
    assert avb["scale_uncertain"] == pytest.approx(1 / 0.35)  # refrigerator capped at nameplate
    assert any(w["code"] == "reconcile_ceiling" for w in res.warnings)
    assert abs(avb["bills"][0]["reconciled_kwh"] - 200.0) < 0.01


def test_future_and_retiring_status():
    apps = [
        Appliance("old", "Old AC", "aircon_non_inverter", 1500, status="retiring", windows=[Window("20:00", "06:00")]),
        Appliance("new", "New inverter AC", "aircon_inverter", 1000, status="future", windows=[Window("20:00", "06:00")]),
        Appliance("led", "LED bulb", "lighting", 9, quantity=5, windows=[Window("18:00", "22:00")]),
    ]
    res = run_audit(apps, [Bill("b", "2026-05", 150.0, days=30)])
    rows = {r["id"]: r for r in res.appliances}
    assert rows["new"]["scale"] == 1.0  # future of a type the house does not have yet: used as typed
    assert rows["old"]["scale"] != 1.0  # retiring counts against the bill
    # sizing set excludes the retiring unit and includes the future one
    expected_daily = rows["new"]["kwh_per_day_reconciled"] + rows["led"]["kwh_per_day_reconciled"]
    assert abs(res.daily_kwh_by_month[4] - expected_daily) < 1e-6
    assert res.future_daily_kwh > 0


def test_no_bills_keeps_audit_as_typed():
    res = run_audit(tanauan_appliances(), [])
    assert res.audit_vs_bill is None
    assert any(w["code"] == "no_bills" for w in res.warnings)
    assert np.allclose(res.load_kw, res.load_kw_unreconciled)


def test_future_copy_of_existing_type_inherits_scale():
    apps = [
        Appliance("ac", "Split AC", "aircon_inverter", 2100, windows=[Window("08:00", "01:00")]),
        Appliance("ac2", "Second split AC (planned)", "aircon_inverter", 2100, status="future", windows=[Window("08:00", "01:00")]),
        Appliance("led", "LED bulb", "lighting", 9, quantity=9, windows=[Window("18:00", "06:00")]),
        Appliance("ev", "EV charger (planned)", "ev_charger", 3500, status="future", windows=[Window("22:00", "02:00")]),
    ]
    res = run_audit(apps, [Bill("b", "2026-08", 338.0, days=31)])
    rows = {r["id"]: r for r in res.appliances}
    assert rows["ac2"]["scale"] == rows["ac"]["scale"] != 1.0 and rows["ac2"]["scale_inherited"]
    assert rows["ev"]["scale"] == 1.0 and not rows["ev"]["scale_inherited"]
    assert abs(rows["ac2"]["kwh_per_day_reconciled"] - rows["ac"]["kwh_per_day_reconciled"]) < 1e-9
