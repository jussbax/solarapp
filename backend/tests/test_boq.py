from pathlib import Path

import pytest

from solarapp.pricing.boq import BoqRequest, RoofRow, generate_boq, pick_gauge, rows_for, select_battery, select_inverter
from solarapp.pricing.engine import JobInputs, price_job
from solarapp.pricing.importer import read_workbook

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"


@pytest.fixture(scope="module")
def imported():
    return read_workbook(WB)


def test_rows_for():
    rows = rows_for(8, 4, 1.134)
    assert [r.panels for r in rows] == [4, 4] and rows[0].length_m == pytest.approx(4.536)
    assert [r.panels for r in rows_for(9, 4, 1.134)] == [4, 4, 1]


def test_mounting_matches_sample_job(imported):
    cat, cfg = imported.catalog, imported.config
    req = BoqRequest("BC-PNL-004", 8, rows_for(8, 4, 1.134), inverter_kw=6, battery_kwh=11.7)
    res = generate_boq(req, cat, cfg)
    q = {l.role: l.qty for l in res.lines}
    assert q["rail"] == 8 and q["l_foot"] == 24 and q["end_clamp"] == 8 and q["mid_clamp"] == 12 and q["splice"] == 4
    assert q["panel"] == 8
    assert res.choices["strings"] == 1 and q["dc_breaker"] == 1 and q["mc4_pair"] == 2
    assert q["ac_breaker"] == 4 and q["ac_spd"] == 4 and q["enclosure"] == 2 and q["ground_rod"] == 1 and q["earth_lug"] == 4


def test_default_inverter_in_parallel(imported):
    """One default per system kind: the grid-interactive FS-INV-001 on anything with net metering, the off-grid
    FS-INV-008 on off-grid jobs; parallel units when the sizing needs more kW; a per-job override wins."""
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(BoqRequest("BC-PNL-001", 9, rows_for(9, 8, 1.134), inverter_kw=6, battery_kwh=9.6), cat, cfg)   # kind defaults to combination
    inv = next(l for l in res.lines if l.role == "inverter")
    assert inv.code == "FS-INV-001" and inv.qty == 1 and "grid-interactive: yes" in inv.note
    off = generate_boq(BoqRequest("BC-PNL-001", 9, rows_for(9, 8, 1.134), inverter_kw=6, battery_kwh=9.6, kind="off_grid"), cat, cfg)
    assert next(l for l in off.lines if l.role == "inverter").code == "FS-INV-008"   # Felicity 6 kW eco-hybrid off the grid
    big = generate_boq(BoqRequest("BC-PNL-001", 20, rows_for(20, 10, 1.134), inverter_kw=8, inverter_required_kw=7.4, battery_kwh=10, kind="off_grid"), cat, cfg)
    inv2 = next(l for l in big.lines if l.role == "inverter")
    assert inv2.code == "FS-INV-008" and inv2.qty == 2 and "parallel" in inv2.note
    assert next(l for l in big.lines if l.role == "thhn").qty == 2 * 35 and next(l for l in big.lines if l.role == "ac_breaker").qty == 8
    big_grid = generate_boq(BoqRequest("BC-PNL-001", 20, rows_for(20, 10, 1.134), inverter_kw=8, inverter_required_kw=7.4, battery_kwh=10), cat, cfg)
    assert next(l for l in big_grid.lines if l.role == "inverter").qty == 2
    over = generate_boq(BoqRequest("BC-PNL-001", 9, rows_for(9, 8, 1.134), inverter_kw=6, battery_kwh=9.6, inverter_code="BC-INV-002", kind="off_grid"), cat, cfg)
    assert next(l for l in over.lines if l.role == "inverter").code == "BC-INV-002"
    cfg2 = cfg.model_copy(deep=True)
    cfg2.roles.default_inverter_code_grid = ""
    cfg2.roles.default_inverter_code_offgrid = ""
    cheap = generate_boq(BoqRequest("BC-PNL-001", 9, rows_for(9, 8, 1.134), inverter_kw=6, battery_kwh=9.6), cat, cfg2)
    assert next(l for l in cheap.lines if l.role == "inverter").code == select_inverter(6, cat, cfg2, "combination")[0][0].code
    cheap_off = generate_boq(BoqRequest("BC-PNL-001", 9, rows_for(9, 8, 1.134), inverter_kw=6, battery_kwh=9.6, kind="off_grid"), cat, cfg2)
    assert next(l for l in cheap_off.lines if l.role == "inverter").code == select_inverter(6, cat, cfg2, "off_grid")[0][0].code


def test_cheapest_inverter_and_battery(imported):
    cat, cfg = imported.catalog, imported.config
    inv = select_inverter(6, cat, cfg)
    assert inv and inv[0][0].rating >= 6 and inv[0][0].is_hybrid_inverter
    assert all(a[2] <= b[2] for a, b in zip(inv, inv[1:]))
    bats = select_battery(9.6, cat, cfg)
    assert bats and all(n * i.rating >= 9.6 for i, n, c in bats)
    assert all(a[2] <= b[2] for a, b in zip(bats, bats[1:]))
    assert not any("rack" in i.name.lower() or "slave" in i.name.lower() for i, n, c in bats)


def test_gauge_selection_and_drop():
    from solarapp.pricing.config import PricingConfig
    cfg = PricingConfig()
    g, drop, ok = pick_gauge(26.1, 15, 230, 0.03, cfg.wiring.thhn_ampacity, cfg)
    assert ok and g == "8.0"  # 6 kW at 230 V: 26 A x 1.25 = 33 A -> 8.0 mm2 (40 A at 60 C), as on the sample job
    g2, drop2, ok2 = pick_gauge(52, 15, 230, 0.03, cfg.wiring.thhn_ampacity, cfg)
    assert ok2 and float(g2) >= 14
    g3, drop3, ok3 = pick_gauge(14, 25, 420, 0.03, cfg.wiring.pv_cable_ampacity, cfg)
    assert ok3 and g3 == "4"
    g4, drop4, ok4 = pick_gauge(14, 400, 420, 0.03, cfg.wiring.pv_cable_ampacity, cfg)
    assert not ok4 and g4 == "6"


def test_tanauan_like_job_prices(imported):
    cat, cfg = imported.catalog, imported.config
    req = BoqRequest("BC-PNL-001", 9, rows_for(9, 8, 1.134), inverter_kw=6, battery_kwh=9.6)
    res = generate_boq(req, cat, cfg)
    roles = {l.role for l in res.lines}
    assert {"panel", "inverter", "battery", "rail", "thhn", "battery_cable", "battery_breaker", "ats", "pv_cable_red"} <= roles
    priced = price_job(res.lines, cat, cfg, JobInputs(net_metering=False))
    tot = priced["totals"]
    assert tot["kwp"] == pytest.approx(9 * 585 / 1000)
    assert tot["contract_rounded"] % 100 == 0 and tot["contract_rounded"] > 200000
    assert priced["labor"]["pairs"] >= 1 and priced["freight"]["trips"] == 1
    assert not priced["missing_codes"]
    # a battery-less net-metering job has no battery lines
    res2 = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=0), cat, cfg)
    assert not {"battery", "battery_cable", "battery_breaker"} & {l.role for l in res2.lines}
