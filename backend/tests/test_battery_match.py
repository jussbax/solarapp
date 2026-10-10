"""Round 12, the battery checks on the datasheet figures (brief 3.5 to 3.8), each hand-worked from the brief's own
figures: the battery circuit on the larger of discharge and charge (the eco-hybrid's 139 A, breaker ≥ 173.75 A, the
same 250 A breaker and 70 mm² pair as before), the soft recommended-rate check, the charge check (135 A against
60 A: set 60, three units for the full rate), the voltage match that blocks a 25.6 V pack on a 48 V port, and Ah
against kWh. Where the figures are absent the BOQ behaves as it did (test_boq, test_design_rules run unchanged)."""
import dataclasses
from copy import deepcopy
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from solarapp.pricing.boq import BoqRequest, generate_boq, rows_for
from solarapp.pricing.catalog import Item
from solarapp.pricing.config import PricingConfig
from solarapp.pricing.datasheets import import_datasheets
from solarapp.pricing.design_checks import ah_kwh_check, battery_soft_checks, charge_check, inverter_battery_current, voltage_class, voltage_match
from solarapp.pricing.importer import read_workbook
from solarapp.pricing.store import import_workbook, load_catalog

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "datasheets"
FILES = [FIXTURES / f"ALL_{n}_DATA_SHEET.xlsx" for n in ("SOLAR_PANEL", "INVERTER", "BATTERY")]


@pytest.fixture(scope="module")
def catalogs(tmp_path_factory):
    """(the seed alone, the seed with the three fixture datasheets applied, the config)."""
    imported = read_workbook(WB)
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('bm') / 'bm.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        import_workbook(s, WB)
        import_datasheets(s, FILES)
        with_ds = load_catalog(s)
    return imported.catalog, with_ds, imported.config


def _line(res, role):
    return next(l for l in res.lines if l.role == role)


def test_the_eco_hybrid_circuit_on_the_sheets_figures(catalogs):
    seed, cat, cfg = catalogs
    eco = cat.get("FS-INV-008")
    assert eco.battery_max_a == 139 and eco.charge_a_max == 135
    cur = inverter_battery_current(eco, 6.0, 51.2)
    assert cur["amps"] == 139 and cur["source"] == "datasheet" and "the larger of discharge 139 A and charge 135 A" in cur["basis"]
    # the same job as test_design_rules pins at 168.75 A: now 173.75 A, the same 250 A breaker, the same 70 mm² lug pairs; only the note moves
    res = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, battery_code="FS-BAT-002", kind="combination"), cat, cfg)
    assert res.choices["battery_current_a"] == 139 and res.choices["battery_breaker_min_a"] == pytest.approx(173.75) and res.choices["battery_current_source"] == "datasheet"
    bb = _line(res, "battery_breaker")
    assert cat.get(bb.code).amps_in_name() == 250 and "1.25 × 139 A" in bb.note
    assert "70 mm2" in _line(res, "battery_cable").note and res.choices["battery_circuit"]["ok"]
    # FS-BAT-002 now carries the sheet's 150 A maximum: the bank holds the 139 A (it fell short at 120 A before)
    assert not {w["code"] for w in res.warnings} & {"battery_current", "battery_current_unknown"}
    assert "150 A continuous against 139 A" in _line(res, "battery").note
    # the seed alone still says 135 A and 168.75 A
    old = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, battery_code="FS-BAT-002", kind="combination"), seed, cfg)
    assert old.choices["battery_current_a"] == 135 and old.choices["battery_breaker_min_a"] == pytest.approx(168.75) and old.choices["battery_current_source"] == "item"
    # FS-INV-002: the larger of 174 and 190 is 190, as the remark already said
    assert inverter_battery_current(cat.get("FS-INV-002"), 8.0, 51.2)["amps"] == 190
    # no figure at all: the rated output over the battery voltage, the battery's own nominal voltage when it carries one
    bare = dataclasses.replace(eco, battery_max_a=None, charge_a_max=None)
    assert inverter_battery_current(bare, 6.0, 51.2) == {"amps": pytest.approx(117.1875), "source": "rule", "basis": "6 kW over 51.2 V (no battery current on the item)"}
    cat2 = deepcopy(cat)
    cat2.items["FS-INV-008"] = bare
    res2 = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, battery_code="FS-BAT-002", kind="combination"), cat2, cfg)
    assert res2.choices["battery_current_source"] == "rule" and res2.choices["battery_current_a"] == pytest.approx(6000 / 51.2)
    # two battery inputs on the inverter (every such unit on the sheets is 3P/HV; here the eco-hybrid given two): one circuit priced, the ordinary verify
    cat3 = deepcopy(cat)
    cat3.items["FS-INV-008"] = dataclasses.replace(eco, battery_inputs=2)
    res3 = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, battery_code="FS-BAT-002", kind="combination"), cat3, cfg)
    w3 = next(w for w in res3.warnings if w["code"] == "battery_inputs_verify")
    assert "two battery inputs on the datasheet (139 A each); the second circuit is not priced; verify" in w3["message"] and not w3.get("hard")
    assert _line(res3, "battery_breaker").qty == 1


def test_the_soft_recommended_rate_and_the_charge_check(catalogs):
    seed, cat, cfg = catalogs
    eco = cat.get("FS-INV-008")
    # FS-BAT-003 (the TG2 row: 160 A max, 150 A recommended) against 139 A: passes both
    w3 = battery_soft_checks(cat.get("FS-BAT-003"), 1, eco, 1, 139.0)
    assert [x["code"] for x in w3] == ["battery_charge_current", "battery_ah_kwh"]     # the recommended rate passes; the 15 vs 15.36 kWh (2.4 %) is said (3.8)
    assert w3[0]["message"] == "The inverter can charge at 135 A and the bank accepts 60 A (1 × 60 A): set the inverter's maximum charge current to 60 A, or the BMS limits or trips. Units needed for the full rate: 3."
    # the 230 Ah IP65 row (150 A max, 115 A recommended) against 139 A: passes the hard check, gets the soft one
    ip65 = Item(code="X-BAT-230", category="Battery", supplier="Felicity Solar", name="230 Ah IP65", rating=11.78, rating_unit="kWh", continuous_a=150, discharge_a_recommended=115, nominal_v=51.2, capacity_ah=230, charge_a_max=46)
    w = battery_soft_checks(ip65, 1, eco, 1, 139.0)
    soft = next(x for x in w if x["code"] == "battery_discharge_recommended")
    assert "deliver 115 A at the recommended continuous rate and the inverter draws up to 139 A: within the BMS maximum (150 A) but above the recommended rate" in soft["message"]
    assert "Verify the warranty condition with the maker" in soft["message"]
    assert not any(x["code"] == "battery_discharge_recommended" for x in battery_soft_checks(ip65, 2, eco, 1, 139.0))   # two units: 230 A recommended
    # the charge check (3.6): the eco-hybrid's 135 A against 60 A per unit → set 60 A, or 3 units for the full 135 A
    c = charge_check(eco, cat.get("FS-BAT-003"), 1)
    assert c == {"inverter_a": 135, "per_unit_a": 60, "units": 1, "accept_a": 60, "ok": False, "units_for_full_rate": 3}
    assert charge_check(eco, cat.get("FS-BAT-003"), 3)["ok"] is True
    # a 12 kW Deye 1P hybrid (250 A) against a 314 Ah pack at 62.8 A: set 62.8 A, or 4 units
    c2 = charge_check(cat.get("OP-INV-017"), cat.get("OP-BAT-006"), 1)
    assert c2["inverter_a"] == 250 and c2["accept_a"] == 62.8 and c2["units_for_full_rate"] == 4 and c2["ok"] is False
    assert charge_check(seed.get("FS-INV-008"), seed.get("FS-BAT-003"), 1) is None       # no figures on the seed alone
    # in the BOQ: the block and the ordinary warning
    res = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=15, battery_code="FS-BAT-003", kind="combination"), cat, cfg)
    assert res.choices["battery_charge"] == {"inverter_a": 135, "per_unit_a": 60, "units": 1, "accept_a": 60, "ok": False, "units_for_full_rate": 3}
    assert any(w["code"] == "battery_charge_current" and not w.get("hard") for w in res.warnings)
    assert next(o for o in res.choices["battery_options"] if o["code"] == "FS-BAT-003")["discharge_a_recommended"] == 150


def test_the_voltage_match(catalogs):
    seed, cat, cfg = catalogs
    assert (voltage_class(16), voltage_class(16.1), voltage_class(32), voltage_class(51.2), voltage_class(64), voltage_class(64.1)) == (12, 24, 24, 48, 48, "HV")
    deye = cat.get("OP-INV-017")                # 60 V port, LV class not on its row
    fel = cat.get("FS-BAT-002")                 # 51.2 V, ceiling 57.6 V
    block, w = voltage_match(deye, fel)
    assert block["class_ok"] is True and block["ceiling_ok"] is False and [x["code"] for x in w] == ["battery_charge_voltage"]
    assert "charges to 60 V and the ceiling of FS-BAT-002 is 57.6 V: set the charge voltage to 57.6 V or lower" in w[0]["message"] and not w[0].get("hard")
    bc_inv, bc_bat = cat.get("BC-INV-004"), cat.get("BC-BAT-002")   # 58.4 V against a 60 V ceiling: both pass
    block2, w2 = voltage_match(bc_inv, bc_bat)
    assert block2["class_ok"] is True and block2["ceiling_ok"] is True and w2 == []
    # BC-BAT-001 (25.6 V) on any 48 V port: V1 blocks
    block3, w3 = voltage_match(deye, cat.get("BC-BAT-001"))
    assert block3["class_ok"] is False and w3[0]["code"] == "battery_voltage_class" and w3[0]["hard"] and w3[0]["blocks_documents"]
    assert "BC-BAT-001 is a 24 V pack (LV)" in w3[0]["message"] and "is a 48 V port" in w3[0]["message"]
    # an LV pack on an HV port, and the classes typed on both
    hv_port = cat.get("OP-INV-023")             # 1000 V, HV
    _, w4 = voltage_match(hv_port, fel)
    assert w4[0]["code"] == "battery_voltage_class" and "high-voltage port (HV)" in w4[0]["message"]
    assert voltage_match(seed.get("FS-INV-008"), seed.get("FS-BAT-002"))[0]["class_ok"] is None    # nothing on file: nothing checked
    # in the BOQ: the per-job pick of a 24 V pack holds the documents; the exclude words keep it out of the automatic choice as before
    res = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=5, inverter_code="OP-INV-017", battery_code="BC-BAT-001", kind="off_grid"), cat, cfg)
    assert res.choices["battery_voltage_match"]["class_ok"] is False and any(w["code"] == "battery_voltage_class" and w["blocks_documents"] for w in res.warnings)
    auto = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=5, inverter_code="OP-INV-017", kind="off_grid"), cat, cfg)
    assert auto.choices["battery_code"] != "BC-BAT-001" and not any(w["code"] == "battery_voltage_class" for w in auto.warnings)


def test_ah_against_kwh(catalogs):
    seed, cat, cfg = catalogs
    a = ah_kwh_check(cat.get("BC-BAT-001"))     # 25.6 × 200 = 5.12 against 5.12
    assert a["ok"] and a["deviation_pct"] == pytest.approx(0.0, abs=1e-9)
    small = Item(code="X", category="Battery", supplier="s", name="x", rating=3.07, rating_unit="kWh", nominal_v=25.6, capacity_ah=120)
    assert ah_kwh_check(small)["deviation_pct"] == pytest.approx(0.065, abs=0.001) and ah_kwh_check(small)["ok"]     # 3.072 against 3.07: 0.07 %
    wrong = Item(code="X", category="Battery", supplier="s", name="x", rating=6, rating_unit="kWh", nominal_v=51.2, capacity_ah=100)
    r = ah_kwh_check(wrong)
    assert r["ok"] is False and r["kwh_calc"] == pytest.approx(5.12) and r["deviation_pct"] == pytest.approx(14.67, abs=0.01)
    assert ah_kwh_check(cat.get("OP-BAT-012")) is None           # no nominal voltage on the sheet: skipped
    assert ah_kwh_check(seed.get("FS-BAT-002")) is None          # nothing on the seed alone
    w = battery_soft_checks(wrong, 1, None, 1, 50.0)
    assert [x["code"] for x in w] == ["battery_ah_kwh"] and "51.2 V × 100 Ah = 5.12 kWh against the 6 kWh on file (14.7 %)" in w[0]["message"]
    # FS-BAT-002 keeps the item's 10 kWh against the sheet's 51.2 × 200 = 10.24: 2.4 %, the ordinary warning on a job that prices it
    res = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, battery_code="FS-BAT-002", kind="combination"), cat, cfg)
    assert res.choices["battery_ah_kwh"]["ok"] is False and res.choices["battery_ah_kwh"]["deviation_pct"] == pytest.approx(2.4)
    assert any(w["code"] == "battery_ah_kwh" for w in res.warnings)
    assert "battery_ah_kwh" not in generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, battery_code="FS-BAT-002", kind="combination"), seed, cfg).choices


def test_without_the_figures_the_sample_jobs_do_not_move(catalogs):
    seed, cat, cfg = catalogs
    res = generate_boq(BoqRequest("BC-PNL-004", 8, rows_for(8, 4, 1.134), inverter_kw=6, battery_kwh=11.7), seed, PricingConfig())
    q = {l.role: l.qty for l in res.lines}
    assert res.choices["strings"] == 1 and q["dc_breaker"] == 1 and q["mc4_pair"] == 2 and res.choices["string_current_a"] == pytest.approx(630 / 42)
    assert res.choices["battery_breaker_min_a"] == pytest.approx(168.75)
    codes = {w["code"] for w in res.warnings}
    assert "string_rule_fallback" in codes and not codes & {"string_voltage_cold", "battery_voltage_class", "battery_charge_current", "battery_ah_kwh", "mppt_current", "dc_breaker_rating"}
    assert res.choices["battery_voltage_match"]["class_ok"] is None and "battery_charge" not in res.choices
