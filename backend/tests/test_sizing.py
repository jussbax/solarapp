import numpy as np
import pytest

from solarapp.core.sizing import BatterySpec, InverterRules, OffGridRules, balance_day, pick_inverter, size_system


def synthetic_production_per_kwp():
    # bell-shaped daytime profile, 12 identical months, about 1400 kWh/kWp a year
    hours = np.arange(24)
    bell = np.clip(np.cos((hours - 12) / 6.5 * np.pi / 2), 0, None) ** 1.5
    bell[(hours < 6) | (hours > 18)] = 0
    daily = bell.sum()
    scale = (1400 / 365) / daily
    return np.tile(bell * scale, (12, 1))


def evening_load(daily_kwh=11.0):
    hours = np.arange(24)
    shape = np.where((hours >= 18) | (hours < 6), 0.7, 0.3)
    shape = shape / shape.sum() * daily_kwh
    return np.tile(shape, (12, 1))


def test_balance_day_conserves_energy():
    load = evening_load()[0]
    prod = synthetic_production_per_kwp()[0] * 4
    b = balance_day(load, prod, usable_kwh=10, power_kw=5, kind="combination", eff_rt=0.92)
    assert np.allclose(b.direct + b.discharge + b.imported, load)
    assert np.allclose(b.direct + b.charge + b.export + b.curtailed, prod)
    assert b.curtailed.sum() == 0
    b2 = balance_day(load, prod, usable_kwh=10, power_kw=5, kind="off_grid", eff_rt=0.92)
    assert b2.export.sum() == 0 and b2.curtailed.sum() >= 0


def test_pick_inverter():
    rules = InverterRules()
    assert pick_inverter(5.5, rules) == (6.0, 1)
    assert pick_inverter(8.0, rules) == (8.0, 1)
    assert pick_inverter(9.1, rules) == (10.0, 1)
    assert pick_inverter(25.0, rules) == (12.0, 3)


def test_net_zero_sizing_and_roof_cap():
    load = evening_load(11.0)
    per_kwp = synthetic_production_per_kwp()
    r = size_system(load, per_kwp, roof_max_panels=29, panel_wp=550, kind="net_metering", peak_load_kw=4.0, largest_motor_kw=1.5, largest_motor_multiplier=3.0)
    assert abs(r["annual_consumption_kwh"] - 11.0 * 365) < 1e-6
    assert r["target_kwp"] == pytest.approx(11.0 * 365 / 1400, rel=1e-6)
    assert r["panels"] == r["target_panels"] and not r["roof_limited"]
    assert r["annual_production_kwh"] >= r["annual_consumption_kwh"]  # whole panels round up
    assert r["battery"]["modules"] == 0
    assert r["inverter"]["size_kw"] == 6.0 and r["inverter"]["units"] == 1
    # roof too small
    r2 = size_system(load, per_kwp, roof_max_panels=2, panel_wp=550, kind="net_metering", peak_load_kw=4.0, largest_motor_kw=1.5, largest_motor_multiplier=3.0)
    assert r2["roof_limited"] and r2["panels"] == 2 and r2["coverage_pct"] < 100
    assert any(w["code"] == "roof_limited" for w in r2["warnings"])


def test_battery_sizing_shifts_surplus_to_night():
    load = evening_load(11.0)
    per_kwp = synthetic_production_per_kwp()
    combo = size_system(load, per_kwp, 29, 550, "combination", 4.0, 1.5, 3.0)
    assert combo["battery"]["modules"] >= 1
    assert combo["coverage_pct"] > 60
    assert combo["annual_export_kwh"] >= 0 and combo["annual_unserved_kwh"] == 0
    # the battery raises coverage over a plain net-metering system
    nm = size_system(load, per_kwp, 29, 550, "net_metering", 4.0, 1.5, 3.0)
    assert combo["coverage_pct"] > nm["coverage_pct"]


def test_off_grid_serves_everything_from_solar_and_battery():
    load = evening_load(11.0)
    per_kwp = synthetic_production_per_kwp()
    og = size_system(load, per_kwp, 29, 550, "off_grid", 4.0, 1.5, 3.0, battery=BatterySpec(max_modules=20), offgrid=OffGridRules(pv_margin=1.25))
    assert og["kind"] == "off_grid" and not og["roof_limited"]
    assert og["annual_unserved_kwh"] == 0 and og["annual_import_kwh"] == 0 and og["annual_export_kwh"] == 0
    assert og["coverage_pct"] == pytest.approx(100.0)
    # worst month produces at least the margin times consumption
    for m in og["monthly"]:
        assert m["production_kwh"] >= 1.25 * m["consumption_kwh"] - 1e-6
    # battery carries only what solar cannot (the night deficit), never a whole extra day
    night = load[0][(np.arange(24) >= 18) | (np.arange(24) < 6)].sum()
    assert night * 0.9 <= og["battery"]["usable_kwh"] < 2 * 11.0
    combo = size_system(load, per_kwp, 29, 550, "combination", 4.0, 1.5, 3.0)
    assert og["kwp"] >= combo["kwp"]
    assert og["battery"]["modules"] == combo["battery"]["modules"]  # same rule: the surplus-to-night shift
    # roof too small: unserved energy is reported instead of a system that cannot fit
    small = size_system(load, per_kwp, 3, 550, "off_grid", 4.0, 1.5, 3.0, offgrid=OffGridRules())
    assert small["roof_limited"] and small["annual_unserved_kwh"] > 0 and small["panels"] == 3
    assert any(w["code"] == "roof_limited" for w in small["warnings"])


def test_inverter_surge_and_pv_constraints():
    load = evening_load(40.0)
    per_kwp = synthetic_production_per_kwp()
    r = size_system(load, per_kwp, 40, 550, "net_metering", peak_load_kw=5.0, largest_motor_kw=2.0, largest_motor_multiplier=3.0)
    # PV of ~10.4 kWp needs 8 kW at ratio 1.3; peak 5 kW; surge (5 + 4)/2 = 4.5
    assert r["inverter"]["binding"] == "PV array" and r["inverter"]["size_kw"] >= 8.0
    r2 = size_system(evening_load(5.0), per_kwp, 40, 550, "net_metering", peak_load_kw=9.0, largest_motor_kw=3.0, largest_motor_multiplier=3.0)
    assert r2["inverter"]["binding"] == "peak load" and r2["inverter"]["size_kw"] == 10.0
    r3 = size_system(evening_load(5.0), per_kwp, 40, 550, "net_metering", peak_load_kw=4.0, largest_motor_kw=6.0, largest_motor_multiplier=3.0, inverter=InverterRules(surge_factor=2.0))
    assert r3["inverter"]["binding"] == "motor surge" and r3["inverter"]["size_kw"] == 8.0


def test_simulation_exposes_hourly_profile(manila_tmy):
    from solarapp.core.simulation import FaceSpec, ThermalModel, simulate
    from tests.conftest import MANILA
    lat, lon, elev = MANILA
    res = simulate(manila_tmy, lat, lon, elev, [FaceSpec("f", "r", 15, 180, 10)], 550, 1.0, ThermalModel())
    prof = np.array(res.hourly_profile_kw)
    assert prof.shape == (12, 24)
    assert prof[:, 0:5].sum() == 0 and prof[:, 12].sum() > 0
    annual_from_profile = float((prof.sum(axis=1) * np.array(res.days_in_month)).sum())
    assert abs(annual_from_profile - res.annual_kwh) / res.annual_kwh < 0.02
