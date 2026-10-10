"""Round 13, item 2 (docs/audits/round-13/engineer-brief.md, section 2): the design analysis. The settings tables (2.3: every
value a cited stand-in with its source and a verify flag, every temperature an assumption), the hand-worked cases of 2.6 on
the engine's pure pieces (the 6 kW inverter output at 30 and 35 °C, the 630 W string in free air and in a rooftop conduit
under the two band tables, the battery circuit, the 10.7 % conduit fill, the EGC sizes), the severities of 2.4, the
short-circuit note (2.3), the sample job's BOM unchanged with seven rows and no blocking code, and the sheet itself through
the API on the Pila record: "not checked" with the reason on the seed alone, pass with the figures typed, refused when a
conductor is not protected at temperature."""
import math
import re
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, create_engine

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.pricing.boq import BoqRequest, generate_boq, rows_for
from solarapp.pricing.catalog import Item
from solarapp.pricing.config import DeratingRules, GroundingRules, PricingConfig, settings_version
from solarapp.pricing.design_analysis import (analyse_design, bundling_factor, conduit_fill_pct, derate_circuit, egc_required_mm2, fill_limit_pct, next_standard_size,
                                              rooftop_adder, short_circuit_note, temperature_factor)
from solarapp.pricing.design_checks import _circuit
from solarapp.pricing.engine import JobInputs, price_job
from solarapp.pricing.importer import read_workbook
from solarapp.pricing.store import ensure_material_columns, load_catalog
from tests.test_drawings import PILA_DOC

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "datasheets"
FILES = [FIXTURES / f"ALL_{n}_DATA_SHEET.xlsx" for n in ("SOLAR_PANEL", "INVERTER", "BATTERY")]


@pytest.fixture(scope="module")
def imported():
    return read_workbook(WB)


def _wire(code: str, name: str, **kw) -> Item:
    return Item(code=code, category="Wires and Terminations", supplier="S", name=name, **kw)


def _pv_row(i_cont: float, i_design: float, ocpd: float, placement: str = "rooftop_free_air", egc: float = 10.0) -> dict:
    """The brief's 630 W string (2.6): two 4 mm² PV wires, the continuous current 1.25 × Isc 16.18 A = 20.22 A (the PV article's
    circuit current, review finding 2), I_cond 25.28 A as the design current, the 32 A breaker."""
    r = _circuit("C1", "PV string (each)", "dc_pv")
    r["conductors"].update({"n_total": 2, "n_current_carrying": 2, "size_mm2": 4.0, "type": "PV wire"})
    r.update({"run_m": 25, "voltage_v": 366.3, "i_continuous_a": i_cont, "i_design_a": i_design, "ocpd_a": ocpd, "ocpd_code": "IAN-PRT-010", "placement": placement,
              "egc_provided_mm2": egc, "egc_provided_code": "IAN-WIR-029", "ampacity_rule_a": 40.0})
    return r


def _ac_row(cid: str = "C4", kind: str = "ac_inverter_output", placement: str = "indoor_conduit") -> dict:
    """The brief's 6 kW inverter output (2.6): 26.1 A, design 32.6 A, the 40 A breaker, 8.0 mm² THHN, line and neutral."""
    r = _circuit(cid, "Inverter output", kind)
    r["conductors"].update({"n_total": 2, "n_current_carrying": 2, "size_mm2": 8.0, "type": "THHN"})
    r.update({"run_m": 15, "voltage_v": 230.0, "i_continuous_a": 6000 / 230, "i_design_a": 6000 / 230 * 1.25, "ocpd_a": 40.0, "ocpd_code": "IAN-PRT-027", "placement": placement,
              "conduit_code": "IAN-ENC-011", "egc_provided_mm2": 8.0, "egc_provided_code": "IAN-WIR-004", "ampacity_rule_a": 40.0})
    return r


# ---------------------------------------------------------------- the settings (2.3)

def test_the_settings_tables_are_the_briefs_cited_stand_ins_and_move_the_version():
    cfg = PricingConfig()
    w, d, g = cfg.wiring, cfg.derating, cfg.grounding
    assert w.thhn_ampacity_75c == {"3.5": 25, "5.5": 35, "8.0": 50, "14": 65, "22": 85, "30": 115} and w.thhn_ampacity_90c == {"3.5": 30, "5.5": 40, "8.0": 55, "14": 75, "22": 95, "30": 130}
    assert set(w.thhn_ampacity_90c) == set(w.thhn_ampacity) and "310.15(B)(16)" in w.thhn_ampacity_source and w.thhn_ampacity_verified is False
    assert (d.ambient_outdoor_c, d.ambient_indoor_c, d.conduit_height_above_roof_mm, d.default_insulation_c, d.inverter_fault_factor) == (35, 30, 25, 90, 1.5)
    assert d.rooftop_adder_c == {"0": 33, "13": 22, "90": 17, "300": 14, "900": 8} and "310.15(B)(3)(c)" in d.rooftop_adder_source
    assert d.bundling_factor_pct == {"1": 100, "4": 80, "7": 70, "10": 50, "21": 45, "31": 40, "41": 35} and d.conduit_fill_limit_pct == {"1": 53, "2": 31, "3": 40}
    assert d.next_size_up_max_a == 800 and d.terminal_rating_c == 75
    assert g.egc_by_ocpd == {"15": 2.0, "20": 3.5, "30": 5.5, "40": 5.5, "60": 5.5, "100": 8.0, "200": 14, "300": 22, "400": 30} and g.gec_rod_max_mm2 == 14
    # every table carries its source and starts unverified; a change to any of them flags the quoted jobs
    for block, keys in ((d, ("rooftop_adder", "temperature_correction", "bundling_factor", "conduit_fill", "next_size_up", "terminal_rule")), (g, ("egc", "gec"))):
        for k in keys:
            assert "NEC" in getattr(block, f"{k}_source") and getattr(block, f"{k}_verified") is False
    v = settings_version(cfg)
    c2 = cfg.model_copy(deep=True)
    c2.derating.rooftop_adder_c = {"0": 33}
    c3 = cfg.model_copy(deep=True)
    c3.grounding.egc_verified = True
    assert settings_version(c2) != v and settings_version(c3) != v
    # an older config takes the blocks' defaults
    old = PricingConfig.model_validate({"wiring": {"pv_run_m": 20}})
    assert old.derating == DeratingRules() and old.grounding == GroundingRules() and old.wiring.thhn_ampacity_90c["8.0"] == 55


def test_the_temperature_formula_against_the_nec_table_and_the_band_tables():
    """The formula the NEC permits in place of its table; the 90 °C column's figures (NEC 2014 Table 310.15(B)(2)(a)) sit here,
    not in the code: at each band's top the formula is within 0.01 of the table."""
    table = {35: 0.96, 40: 0.91, 45: 0.87, 50: 0.82, 55: 0.76, 60: 0.71, 65: 0.65, 70: 0.58, 75: 0.50}
    for t, f in table.items():
        assert temperature_factor(90, t) == pytest.approx(f, abs=0.01)
    assert temperature_factor(90, 30) == 1.0 and temperature_factor(90, 90) is None and temperature_factor(90, 95) is None
    d = DeratingRules()
    assert rooftop_adder(25, d.rooftop_adder_c) == 22 and rooftop_adder(0, d.rooftop_adder_c) == 33 and rooftop_adder(100, d.rooftop_adder_c) == 17 and rooftop_adder(1200, d.rooftop_adder_c) == 8
    assert rooftop_adder(25, {"0": 33}) == 33          # the 2017-style single adder the owner may set
    assert bundling_factor(2, d.bundling_factor_pct) == 1.0 and bundling_factor(4, d.bundling_factor_pct) == 0.8 and bundling_factor(12, d.bundling_factor_pct) == 0.5 and bundling_factor(45, d.bundling_factor_pct) == 0.35
    assert fill_limit_pct(1, d.conduit_fill_limit_pct) == 53 and fill_limit_pct(2, d.conduit_fill_limit_pct) == 31 and fill_limit_pct(3, d.conduit_fill_limit_pct) == 40 and fill_limit_pct(9, d.conduit_fill_limit_pct) == 40
    g = GroundingRules()
    assert egc_required_mm2(32, g.egc_by_ocpd) == (40, 5.5) and egc_required_mm2(40, g.egc_by_ocpd) == (40, 5.5) and egc_required_mm2(250, g.egc_by_ocpd) == (300, 22) and egc_required_mm2(500, g.egc_by_ocpd) is None
    assert next_standard_size(29.7, [16, 20, 25, 32, 40]) == 32 and next_standard_size(24.2, [16, 20, 25, 32, 40]) == 25 and next_standard_size(50, [16, 32]) is None


# ---------------------------------------------------------------- the hand-worked cases (2.6)

def test_the_6_kw_inverter_output_at_30_and_35_degrees(imported):
    cfg = PricingConfig()
    thhn = imported.catalog.get("IAN-WIR-004")
    conduit = imported.catalog.get("IAN-ENC-011")
    row = _ac_row()
    out = derate_circuit(row, cfg, thhn, conduit)
    # base 90 °C 55 A, indoor 30 °C F_temp 1.00, 2 current-carrying F_fill 1.00 → 55 A ≥ 40 ✓; terminal 75 °C 50 A ≥ 40 and ≥ 32.6 ✓
    assert row["ambient_c"] == 30 and row["t_conductor_c"] == 30 and row["conductors"]["insulation_c"] == 90 and row["ampacity_base_a"] == 55 and row["ampacity_base_column"] == "THHN 90 °C column"
    assert row["f_temp"] == 1.0 and row["f_fill"] == 1.0 and row["ampacity_derated_a"] == 55 and row["ampacity_terminal_a"] == 50
    assert row["checks"]["ocpd_le_derated"] is True and row["checks"]["next_size_up_used"] is False and row["checks"]["terminal_ge_design"] is True
    assert row["egc_required_mm2"] == 5.5 and row["checks"]["egc_ok"] is True
    # the fill is not checked: the area and the inside diameter are not on the seed's items, so the row is "not checked" with the reason
    assert row["checks"]["fill_ok"] is None and row["fill_limit_pct"] == 40 and row["status"] == "not checked" and out["warnings"] == []
    assert out["not_checked"] == ["fill: the conductor's area is not on the item (IAN-WIR-004); the conduit's inside diameter is not on the item (IAN-ENC-011)"]
    assert "ambient assumed 30 °C" in out["qualifiers"] and "insulation assumed 90 °C" in out["qualifiers"] and "THHN columns: verify" in out["qualifiers"]
    assert any("F_temp 1.000 = sqrt((90 − 30) / (90 − 30))" in n for n in row["notes"]) and not any("later step" in n for n in row["notes"])
    # at 35 °C outdoors: F_temp = sqrt(55/60) = 0.957 → 52.7 A, still a pass of the breaker check
    row = _ac_row()
    derate_circuit(row, cfg, thhn, conduit, ambient_c=35)
    assert row["f_temp"] == pytest.approx(math.sqrt(55 / 60), abs=1e-6) and row["ampacity_derated_a"] == pytest.approx(52.66, abs=0.01) and row["checks"]["ocpd_le_derated"] is True
    # with the item figures typed the row passes, qualified by the assumptions and the tables still to verify (2.5: never a bare "pass")
    thhn2 = deepcopy(thhn)
    thhn2.overall_area_mm2, thhn2.insulation_c = 23.61, 90
    conduit2 = deepcopy(conduit)
    conduit2.inner_diameter_mm = 29
    row = _ac_row()
    out = derate_circuit(row, cfg, thhn2, conduit2)
    assert row["status"] == "pass" and "insulation assumed 90 °C" not in out["qualifiers"] and "ambient assumed 30 °C" in out["qualifiers"]
    # the terminal rule fails when the 75 °C column is below the breaker: hard, blocks
    cfg2 = cfg.model_copy(deep=True)
    cfg2.wiring.thhn_ampacity_75c["8.0"] = 30
    row = _ac_row()
    out = derate_circuit(row, cfg2, thhn2, conduit2)
    assert row["checks"]["terminal_ge_design"] is False and row["status"] == "fail"
    assert [(w["code"], w["hard"], w["blocks_documents"]) for w in out["warnings"]] == [("terminal_ampacity", True, True)]


def test_the_630_w_string_in_free_air_and_in_a_rooftop_conduit_under_both_band_tables(imported):
    """I_cond 25.28 A, breaker 32 A, 4 mm² PV wire at the app's 40 A (verify), free air under the array at 35 °C: F = 0.957 →
    38.3 A ≥ 32 ✓ pass. In a conduit 25 mm above the roof under the 2014 bands (+22 → 57 °C): F = sqrt(33/60) = 0.742 → 29.7 A
    < 32 A, the next standard size above 29.7 is 32 → pass "next size up". Under a single +33 band (→ 68 °C): F = sqrt(22/60) =
    0.606 → 24.2 A < 25.28 A → fail, conductor_derated, the 6 mm² cable is needed: both outcomes stated, the settings decide."""
    cfg = PricingConfig()
    pv = imported.catalog.get("BC-WIR-001")
    row = _pv_row(20.22, 25.28, 32)
    out = derate_circuit(row, cfg, pv, None)
    assert row["ambient_c"] == 35 and row["rooftop_adder_c"] == 0 and row["ampacity_base_a"] == 40 and row["f_temp"] == pytest.approx(0.957, abs=0.001)
    assert row["ampacity_derated_a"] == pytest.approx(38.3, abs=0.05) and row["checks"]["ocpd_le_derated"] is True and row["status"] == "pass"
    assert "the cable's rating: verify" in out["qualifiers"] and "ambient assumed 35 °C" in out["qualifiers"] and row["ampacity_terminal_a"] is None
    assert any("no 75 °C column on file for the PV wire" in q for q in out["qualifiers"]) and row["egc_required_mm2"] == 5.5 and row["checks"]["egc_ok"] is True
    # the project cell's typical-year maximum, ceiled, replaces the setting when higher: 36.2 → 37 °C, no longer an assumption
    row = _pv_row(20.22, 25.28, 32)
    out = derate_circuit(row, cfg, pv, None, tmy_max_air_c=36.2)
    assert row["ambient_c"] == 37 and not any("ambient assumed" in q for q in out["qualifiers"]) and row["f_temp"] == pytest.approx(math.sqrt(53 / 60), abs=1e-6)
    # in a rooftop conduit 25 mm above the roof, the 2014 bands: +22 °C → 57 °C
    row = _pv_row(20.22, 25.28, 32, placement="rooftop_conduit")
    out = derate_circuit(row, cfg, pv, imported.catalog.get("IAN-ENC-011"))
    assert row["rooftop_adder_c"] == 22 and row["t_conductor_c"] == 57 and row["f_temp"] == pytest.approx(math.sqrt(33 / 60), abs=1e-6) and row["ampacity_derated_a"] == pytest.approx(29.66, abs=0.01)
    assert row["checks"]["ocpd_le_derated"] is False and row["checks"]["next_size_up_used"] is True and "next size up" in out["qualifiers"] and out["warnings"] == []
    assert row["status"] == "not checked" and out["not_checked"][0].startswith("fill: the conductor's area is not on the item (BC-WIR-001)")   # the fill waits on the items
    # the 2017-style single adder the owner may set: +33 → 68 °C → 24.2 A below the 25.28 A design current: fail, hard, blocks
    cfg2 = cfg.model_copy(deep=True)
    cfg2.derating.rooftop_adder_c = {"0": 33}
    row = _pv_row(20.22, 25.28, 32, placement="rooftop_conduit")
    out = derate_circuit(row, cfg2, pv, imported.catalog.get("IAN-ENC-011"))
    assert row["t_conductor_c"] == 68 and row["f_temp"] == pytest.approx(math.sqrt(22 / 60), abs=1e-6) and row["ampacity_derated_a"] == pytest.approx(24.2, abs=0.05)
    assert row["checks"]["ocpd_le_derated"] is False and row["checks"]["next_size_up_used"] is False and row["status"] == "fail"
    w = out["warnings"][0]
    assert w["code"] == "conductor_derated" and w["hard"] and w["blocks_documents"] and "32 A breaker is above the 24.2 A" in w["message"] and "next standard size above 24.2 A is 25 A" in w["message"]
    # the maker's ampacity typed on the cable replaces the table figure and drops the "verify the cable's rating" qualifier
    pv2 = deepcopy(pv)
    pv2.ampacity_a, pv2.insulation_c = 44, 90
    row = _pv_row(20.22, 25.28, 32)
    out = derate_circuit(row, cfg, pv2, None)
    assert row["ampacity_base_a"] == 44 and "the cable's rating: verify" not in out["qualifiers"] and "insulation assumed 90 °C" not in out["qualifiers"]


def test_the_battery_circuit_holds_on_the_cable_table_and_is_not_checked_without_a_rack_egc(imported):
    cfg = PricingConfig()
    row = _circuit("C3", "Battery", "dc_battery")
    row["conductors"].update({"n_total": 2, "n_current_carrying": 2, "size_mm2": 70.0, "type": "battery cable"})
    row.update({"voltage_v": 51.2, "i_continuous_a": 139.0, "i_design_a": 173.75, "ocpd_a": 250.0, "ocpd_code": "IAN-PRT-003", "placement": "indoor_free_air", "ampacity_rule_a": 270.0})
    out = derate_circuit(row, cfg, imported.catalog.get("OP-WIR-009"), None)
    assert row["ampacity_base_a"] == 270 and row["ampacity_derated_a"] == 270 and row["checks"]["ocpd_le_derated"] is True
    # review finding 12: the blank "provided" is a missing BOM role, so the row is "not checked" naming it, never a pass with a verify note
    assert row["egc_required_mm2"] == 22 and row["egc_provided_mm2"] is None and row["checks"]["egc_ok"] is None and row["status"] == "not checked"
    assert out["not_checked"] == ["EGC: no battery-rack EGC role on the BOM (Pricing settings › BOM item roles)"] and "the cable's rating: verify" in out["qualifiers"]
    # a 250 A breaker above a 210 A cable: no standard-size list applies to the battery breaker, so the next-size-up rule does not rescue it
    row["conductors"]["size_mm2"] = 50.0
    row["ampacity_rule_a"] = 210.0
    out = derate_circuit(row, cfg, imported.catalog.get("OP-WIR-008"), None)
    assert row["ampacity_derated_a"] == 210 and row["status"] == "fail" and out["warnings"][0]["code"] == "conductor_derated" and "no standard-size list applies" in out["warnings"][0]["message"]


def test_the_conduit_fill_and_the_egc_sizes(imported):
    """3 × 8.0 mm² THHN (line, neutral and the grounding run) in the 32 mm flexible conduit with an inside diameter of 29 mm:
    Σ = 3 × 23.61 = 70.8 mm², area 660.5 mm², 10.7 % ≤ 40 % ✓; with the diameter blank → "not checked". The EGC: the 40 A AC
    circuit needs 5.5 mm² on the 8.0 mm² line → pass; the PV row (32 A) needs 5.5 mm² against the 10 mm² bonding → pass; a
    bonding role on the 3.5 mm² wire → fail, egc_undersized (hard, not blocking)."""
    cfg = PricingConfig()
    assert conduit_fill_pct([23.61] * 3, 29) == pytest.approx(70.83 / 660.52 * 100, abs=0.01) == pytest.approx(10.72, abs=0.01)
    assert conduit_fill_pct([23.61], 0) is None
    thhn = deepcopy(imported.catalog.get("IAN-WIR-004"))
    thhn.overall_area_mm2 = 23.61
    conduit = deepcopy(imported.catalog.get("IAN-ENC-011"))
    conduit.inner_diameter_mm = 29
    row = _ac_row()
    out = derate_circuit(row, cfg, thhn, conduit)
    assert row["fill_pct"] == pytest.approx(10.72, abs=0.01) and row["fill_limit_pct"] == 40 and row["checks"]["fill_ok"] is True and row["conductor_area_mm2"] == 23.61 and row["conduit_inner_diameter_mm"] == 29
    assert any("fill 10.7 % = 3 × 23.61 mm²" in n for n in row["notes"]) and row["status"] == "pass"
    # a 16 mm conduit: 70.8 / 201.1 = 35.2 % ≤ 40 holds; a 13 mm one: 53.4 % → over, hard, not blocking
    small = deepcopy(conduit)
    small.inner_diameter_mm = 13
    row = _ac_row()
    out = derate_circuit(row, cfg, thhn, small)
    assert row["fill_pct"] == pytest.approx(53.4, abs=0.1) and row["checks"]["fill_ok"] is False and row["status"] == "fail"
    assert [(w["code"], w["hard"], w.get("blocks_documents")) for w in out["warnings"]] == [("conduit_fill", True, None)]
    # the diameter blank → not checked, the reason names the item
    blank = deepcopy(conduit)
    blank.inner_diameter_mm = None
    row = _ac_row()
    out = derate_circuit(row, cfg, thhn, blank)
    assert row["fill_pct"] is None and row["status"] == "not checked" and out["not_checked"] == ["fill: the conduit's inside diameter is not on the item (IAN-ENC-011)"]
    # the EGC sizes
    row = _ac_row()
    derate_circuit(row, cfg, thhn, conduit)
    assert row["egc_required_mm2"] == 5.5 and row["egc_provided_mm2"] == 8.0 and row["checks"]["egc_ok"] is True
    row = _pv_row(20.22, 25.28, 32)
    derate_circuit(row, cfg, imported.catalog.get("BC-WIR-001"), None)
    assert row["egc_required_mm2"] == 5.5 and row["checks"]["egc_ok"] is True
    row = _pv_row(20.22, 25.28, 32, egc=3.5)
    out = derate_circuit(row, cfg, imported.catalog.get("BC-WIR-001"), None)
    assert row["checks"]["egc_ok"] is False and row["status"] == "fail"
    assert [(w["code"], w["hard"], w.get("blocks_documents")) for w in out["warnings"]] == [("egc_undersized", True, None)] and "array bonding conductor is 3.5 mm²" in out["warnings"][0]["message"]


def test_the_short_circuit_note_prints_blank_lines_and_the_labelled_assumption_until_typed(imported):
    cfg = PricingConfig()
    cat = imported.catalog
    inv, bat = cat.get("FS-INV-008"), cat.get("FS-BAT-006")
    brk = [cat.get("IAN-PRT-009"), cat.get("IAN-PRT-027"), cat.get("IAN-PRT-003")]
    sc = short_circuit_note({}, inv, bat, 1, 6000 / 230, brk, cfg)
    assert sc["utility_text"] == "BLANK kA (from the DU; verify)" and sc["inverter"]["assumed"] and sc["inverter"]["amps"] == pytest.approx(1.5 * 6000 / 230)
    assert sc["inverter"]["text"].startswith("assumption: 1.5 × rated output current for one cycle, 39 A") and sc["battery"]["text"] == "BLANK A (the BMS's short-circuit trip of FS-BAT-006: not on the item; verify with the maker)"
    assert sc["aic_text"].startswith("breaker interrupting ratings (AIC) at or above the fault level at each point: BLANK") and len(sc["unknown"]) == 6
    # typed: the DU's figure from the service block, the inverter's and the battery's from the items, the AIC compared
    inv2, bat2 = deepcopy(inv), deepcopy(bat)
    inv2.fault_current_a, bat2.fault_current_a = 45, 1200
    b2 = deepcopy(brk[1])
    b2.aic_ka = 6
    b3 = deepcopy(brk[2])
    b3.aic_ka = 15
    sc = short_circuit_note({"du_name": "FLECO", "fault_level_ka": 10}, inv2, bat2, 2, 6000 / 230, [brk[0], b2, b3], cfg)
    assert sc["utility_ka"] == 10 and "10 kA at the service, as the office typed from FLECO (verify)" == sc["utility_text"]
    assert sc["inverter"] == {"amps": 90, "assumed": False, "text": "90 A (FS-INV-008: maximum output fault current on the item, × 2 units)"} and sc["battery"]["amps"] == 1200
    assert [a["ok"] for a in sc["aic"]] == [None, False, True] and "IAN-PRT-027 6 kA below the DU's figure: does NOT hold" in sc["aic_text"] and "IAN-PRT-003 15 kA at or above the DU's figure: holds" in sc["aic_text"]
    assert sc["unknown"] == ["the interrupting rating of IAN-PRT-009 (Materials page)"]


# ---------------------------------------------------------------- the sample job (2.6, last bullet)

def test_the_sample_job_keeps_its_bom_and_totals_with_seven_rows_and_no_blocking_code(imported):
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(BoqRequest("BC-PNL-004", 8, rows_for(8, 4, 1.134), inverter_kw=6, battery_kwh=11.7), cat, cfg)
    before = [(l.code, l.qty, l.role) for l in res.lines]
    ch = res.choices
    out = analyse_design(ch, res.lines, cat, cfg, inverter=cat.get(ch["inverter_code"]), battery=cat.get(ch["battery_code"]), units=ch["inverter_units"], tmy_max_air_c=33.4, service={})
    assert [(l.code, l.qty, l.role) for l in res.lines] == before
    assert price_job(res.lines, cat, cfg, JobInputs(net_metering=True))["totals"]["contract_rounded"] == price_job(generate_boq(BoqRequest("BC-PNL-004", 8, rows_for(8, 4, 1.134), inverter_kw=6, battery_kwh=11.7), cat, cfg).lines, cat, cfg, JobInputs(net_metering=True))["totals"]["contract_rounded"]
    rows = {c["id"]: c for c in ch["circuits"]}
    assert list(rows) == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"] and not [w for w in out["warnings"] if w.get("blocks_documents")]
    assert [w["code"] for w in out["warnings"]] == ["derating_not_checked", "fault_level_unknown"] and ch["design_analysis"]["blocking"] == []
    # the seed alone: the breaker's rating is not checked without Isc, the fill waits on the items, the battery passes on the table with "verify"
    assert rows["C1"]["status"] == "not checked" and rows["C1"]["not_checked"] == ["the breaker's rating is not checked without Isc on file"] and rows["C1"]["ampacity_derated_a"] == pytest.approx(38.3, abs=0.05)
    assert rows["C3"]["status"] == "not checked" and rows["C4"]["status"] == rows["C5"]["status"] == rows["C6"]["status"] == "not checked" and rows["C2"]["status"] == "not checked"
    assert rows["C7"]["status"] == "pass" and rows["C7"]["egc_required_mm2"] == 5.5 and rows["C7"]["egc_provided_mm2"] == 8.0 and rows["C7"]["checks"]["egc_ok"] is True
    assert not any("later step" in n for c in ch["circuits"] for n in c["notes"])
    da = ch["design_analysis"]
    assert da["ambient"]["outdoor_c"] == 35 and da["ambient"]["outdoor_source"] == "setting" and [t["verified"] for t in da["tables"]] == [False] * 10
    assert any(a.startswith("outdoor ambient 35 °C") and "assumption" in a for a in da["assumptions"]) and da["gec"]["gauge_mm2"] == 8.0 and "at most 14 mm²" in da["gec"]["text"]
    assert [n["id"] for n in da["not_checked"]] == ["C1", "C3", "C4", "C5", "C6"]   # C3: the battery rack's EGC role (review finding 12)
    w = out["warnings"][0]
    assert "C4: fill: the conductor's area is not on the item (IAN-WIR-004)" in w["message"] and not w.get("hard")


def test_the_item_fields_round_trip_and_an_older_database_gets_the_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE material_items (code VARCHAR PRIMARY KEY, category VARCHAR, supplier VARCHAR, name VARCHAR, spec VARCHAR, unit VARCHAR, "
            "sold_as VARCHAR, list_price FLOAT, rating FLOAT, rating_unit VARCHAR, weight_kg FLOAT, volume_m3 FLOAT, weight_source VARCHAR, storage FLOAT, "
            "price_list_date VARCHAR, remarks VARCHAR, panel_length_m FLOAT, panel_width_m FLOAT, active BOOLEAN, updated_at DATETIME)"))
        conn.execute(text("INSERT INTO material_items (code, category, supplier, name, spec, unit, sold_as, list_price, rating_unit, weight_kg, volume_m3, weight_source, storage, price_list_date, remarks, active, updated_at) "
                          "VALUES ('X-WIR-001', 'Wires and Terminations', 'S', 'THHN 8.0mm2', '', 'm', 'm', 1, '', 0, 0, '', 0, '', '', 1, '2026-01-01 00:00:00')"))
        conn.execute(text("CREATE TABLE material_suppliers (name VARCHAR PRIMARY KEY, pickup_address VARCHAR, dealer_discount FLOAT, payment_fee FLOAT, delivers_free BOOLEAN, price_list_date VARCHAR, prices_note VARCHAR, warranty VARCHAR, remarks VARCHAR)"))
    with Session(engine) as s:
        added = ensure_material_columns(s)
        assert {"overall_area_mm2", "inner_diameter_mm", "insulation_c", "ampacity_a", "fault_current_a", "aic_ka"} <= set(added)
        item = load_catalog(s).get("X-WIR-001")
        assert item is not None and item.overall_area_mm2 is None and item.insulation_c is None and item.aic_ka is None


# ---------------------------------------------------------------- the sheet through the API

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def _pdf_pages(pdf: bytes, layout: bool = True) -> list[str]:
    """The pages' text: in layout mode (the sheet count, the title block, the cover's index) or in reading order, which keeps a
    table cell's wrapped phrase whole where the layout mode interleaves the eighteen columns line by line."""
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    args = ["pdftotext"] + (["-layout"] if layout else []) + ["-", "-"]
    text = subprocess.run(args, input=pdf, capture_output=True, check=True).stdout.decode()
    return [p for p in text.split("\f") if p.strip()]


def _flat(s: str) -> str:
    return " ".join(s.split())


def test_the_sheet_prints_not_checked_with_the_reason_on_the_seed_then_passes_with_the_figures_typed(client):
    aid = client.post("/api/assessments", json=deepcopy(PILA_DOC)).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    pr = res["pricing"]
    rows = {c["id"]: c for c in pr["choices"]["circuits"]}
    da = pr["choices"]["design_analysis"]
    assert pr["design_blocked"] == [] and {w["code"] for w in pr["warnings"]} >= {"derating_not_checked", "fault_level_unknown"}
    assert rows["C1"]["status"] == "not checked" and rows["C4"]["status"] == "not checked" and rows["C3"]["status"] == "not checked" and rows["C7"]["status"] == "pass"
    assert rows["C4"]["ampacity_derated_a"] == 55 and rows["C4"]["qualifiers"] and da["short_circuit"]["utility_ka"] is None and da["ambient"]["tmy_max_air_c"] is not None
    # the item figures round-trip through the API
    assert client.put("/api/pricing/items/IAN-WIR-004", json={"overall_area_mm2": 23.61, "insulation_c": 90}).json()["overall_area_mm2"] == 23.61
    got = client.get("/api/pricing/items/IAN-WIR-004").json()
    assert got["overall_area_mm2"] == 23.61 and got["insulation_c"] == 90 and got["inner_diameter_mm"] is None
    assert client.put("/api/pricing/items/IAN-WIR-004", json={"overall_area_mm2": -1}).status_code == 422
    client.put("/api/settings", json={"company_name": "Test Solar", "pee_name": "Juan dela Cruz", "pee_license": "0012345"})
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 200
    pages = _pdf_pages(r.content)
    reading = _pdf_pages(r.content, layout=False)
    # cover, the site sheet, two layouts, the schedule, the design analysis, the last sheet: seven sheets, the analysis named on the cover
    assert len(pages) == len(reading) == 10 and re.search(r"Sheet 8\s+Design analysis", pages[0])
    sheet = pages[7]
    flat = _flat(reading[7])
    assert "Design analysis: conductor derating, overcurrent protection, conduit fill and grounding" in sheet and "Sheet 8 of 10" in sheet and "Not to scale" in sheet
    for cid in ("C1", "C2", "C3", "C4", "C5", "C6", "C7"):
        assert re.search(rf"\b{cid}\b", sheet)
    assert "not checked: the breaker's rating is not checked without Isc on file" in flat
    assert "not checked: fill: the conductor's area is not on the item (IAN-WIR-004); the conduit's inside diameter is not on the item (IAN-ENC-011)" in flat
    assert "not checked: EGC: no battery-rack EGC role on the BOM (Pricing settings › BOM item roles)" in flat   # the battery row (review finding 12)
    assert "__________ kA (from the DU; verify)" in flat and "assumption: 1.5 × rated output current for one cycle" in flat and "the AIC is not on the breaker items; verify" in flat
    assert "GEC: 8 mm²" in flat and "at most 14 mm² for a rod electrode" in flat and flat.count("VERIFY") >= 10 and "confirmed in Settings" not in flat
    assert "assumption: outdoor ambient 35 °C" in flat and "assumption: indoor ambient 30 °C" in flat and "NEC 2014 Table 310.15(B)(16)" in flat
    assert "to be completed by the signing engineer" not in sheet          # the sheet carries the figures or the reason, never the old placeholder
    last = _flat(reading[-1])
    assert "Design analysis: rows not checked" in last and "C4: fill: the conductor's area is not on the item" in last
    assert "conduit fill: the design analysis sheet" in _flat(reading[6]) and "Derating, the breaker against the derated ampacity" in _flat(reading[0])
    # the datasheets, a 500 V input, the areas, the conduit's diameter, the breaker's AIC and the DU's fault level typed: the rows pass
    for f in FILES:
        with open(f, "rb") as fh:
            assert client.post("/api/pricing/datasheets", files={"file": (f.name, fh, "application/octet-stream")}).status_code == 200
    assert client.put("/api/pricing/items/FS-INV-008", json={"max_pv_voltage_v": 500, "fault_current_a": 45}).status_code == 200
    assert client.put("/api/pricing/items/IAN-ENC-011", json={"inner_diameter_mm": 29}).status_code == 200
    assert client.put("/api/pricing/items/IAN-PRT-027", json={"aic_ka": 6}).status_code == 200
    doc = client.get(f"/api/assessments/{aid}").json()["doc"]
    doc["service"] = {"du_name": "FLECO", "fault_level_ka": 10}
    res = client.post(f"/api/assessments/{aid}/compute", json=doc).json()["results"]
    pr = res["pricing"]
    rows = {c["id"]: c for c in pr["choices"]["circuits"]}
    # the review's finding 1: the 40 A breaker's 6 kA interrupting rating is below the DU's 10 kA at the service: a hard warning
    # that holds the customer documents and the plans (409), named on the sheet's short-circuit note
    assert pr["design_blocked"] == ["aic_below_fault"] and pr["choices"]["design_analysis"]["blocking"] == ["aic_below_fault"]
    w = next(w for w in pr["warnings"] if w["code"] == "aic_below_fault")
    assert w["hard"] is True and w["blocks_documents"] is True and "BOM item roles" in w["message"] and "verify the DU's figure" in w["message"]
    assert w["message"].startswith("IAN-PRT-027: interrupting rating 6 kA is below the DU's 10 kA at the service")
    assert "IAN-PRT-027 6 kA below the DU's figure: does NOT hold (aic_below_fault" in pr["choices"]["design_analysis"]["short_circuit"]["aic_text"]
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 409 and "aic_below_fault" in r.json()["detail"]
    assert client.get(f"/api/assessments/{aid}/report.pdf").status_code == 409
    # the review's finding 2: the PV string's continuous current is the PV article's 1.25 × Isc = 16.91 A (Isc 13.53 A), its
    # design current 1.25 × that = 21.14 A, so the next-size-up test compares the derated ampacity with 16.91 A, not Imp
    assert rows["C1"]["i_continuous_a"] == pytest.approx(16.91, abs=0.01) and rows["C1"]["i_design_a"] == pytest.approx(21.14, abs=0.01)
    assert any("1.25 × Isc 13.53 A = 16.91 A, the PV article's circuit current" in n for n in rows["C1"]["notes"])
    # a 10 kA breaker holds: nothing blocks, every applicable row passes
    assert client.put("/api/pricing/items/IAN-PRT-027", json={"aic_ka": 10}).status_code == 200
    res = client.post(f"/api/assessments/{aid}/compute", json=doc).json()["results"]
    pr = res["pricing"]
    rows = {c["id"]: c for c in pr["choices"]["circuits"]}
    assert pr["design_blocked"] == [] and "aic_below_fault" not in {w["code"] for w in pr["warnings"]}
    # the battery rack's EGC is the one row left "not checked" in the typed state (review finding 12), and the warning names it
    w = next(w for w in pr["warnings"] if w["code"] == "derating_not_checked")
    assert "C3: EGC: no battery-rack EGC role on the BOM" in w["message"] and not w.get("hard")
    assert rows["C1"]["status"] == "pass" and rows["C1"]["ocpd_a"] == 25 and rows["C1"]["ampacity_derated_a"] == pytest.approx(38.3, abs=0.05)
    assert rows["C4"]["status"] == "pass" and rows["C4"]["fill_pct"] == pytest.approx(10.72, abs=0.01) and rows["C4"]["checks"]["fill_ok"] is True
    da = pr["choices"]["design_analysis"]
    assert da["short_circuit"]["utility_ka"] == 10 and da["short_circuit"]["inverter"]["assumed"] is False and [n["id"] for n in da["not_checked"]] == ["C3"]
    pages = _pdf_pages(client.get(f"/api/assessments/{aid}/plans.pdf").content, layout=False)
    sheet = next(p for p in pages if "Design analysis: conductor derating" in p)
    flat = _flat(sheet)
    assert "10.7 % / 40 %" in flat and "pass (ambient assumed 30 °C; THHN columns: verify; EGC table: verify)" in flat and "pass (ambient assumed 35 °C" in flat
    assert "10 kA at the service, as the office typed from FLECO (verify)" in flat and "45 A (FS-INV-008: maximum output fault current on the item)" in flat
    assert "IAN-PRT-027 10 kA at or above the DU's figure: holds" in flat and "IAN-PRT-009 __________" in flat and "16.91 A" in flat and "21.14 A" in flat
    assert "C1: 1.25 × 1.25 × Isc)" in flat   # the column head "Design A (× 1.25; C1: 1.25 × 1.25 × Isc)", wrapped in its cell
    assert "Design analysis: rows not checked" in _flat(pages[-1]) and "C3: EGC: no battery-rack EGC role on the BOM" in _flat(pages[-1])
    # a table ticked confirmed prints so
    cfg = client.get("/api/pricing/config").json()
    cfg["grounding"]["egc_verified"] = True
    assert client.put("/api/pricing/config", json=cfg).status_code == 200
    assert client.post(f"/api/assessments/{aid}/compute", json=doc).status_code == 200
    flat = _flat(next(p for p in _pdf_pages(client.get(f"/api/assessments/{aid}/plans.pdf").content, layout=False) if "Design analysis: conductor derating" in p))
    assert "EGC table: verify" not in flat and "pass (ambient assumed 30 °C; THHN columns: verify)" in flat and "confirmed in Settings" in flat


def test_a_conductor_the_breaker_does_not_protect_at_temperature_holds_the_documents(client):
    """An indoor ambient of 85 °C (the owner's setting, not a figure the app invents): the 8.0 mm² THHN carries 55 × sqrt(5/60)
    = 15.9 A, the 40 A breaker is far above it and 16 A is the next size, so conductor_derated blocks the plans like the
    round-3 AC coordination; back at 30 °C the set builds again."""
    cfg = client.get("/api/pricing/config").json()
    saved = deepcopy(cfg)
    cfg["derating"]["ambient_indoor_c"] = 85
    assert client.put("/api/pricing/config", json=cfg).status_code == 200
    aid = client.post("/api/assessments", json=deepcopy(PILA_DOC)).json()["id"]
    res = client.post(f"/api/assessments/{aid}/compute").json()["results"]
    pr = res["pricing"]
    assert pr["design_blocked"] == ["conductor_derated"] * 3 or set(pr["design_blocked"]) == {"conductor_derated"}
    rows = {c["id"]: c for c in pr["choices"]["circuits"]}
    assert rows["C4"]["status"] == "fail" and rows["C4"]["ampacity_derated_a"] == pytest.approx(55 * math.sqrt(5 / 60), abs=0.01) and rows["C3"]["status"] == "fail"
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 409 and r.json()["detail"].startswith("design_blocked: ")
    assert client.put("/api/pricing/config", json=saved).status_code == 200
    res = client.post(f"/api/assessments/{aid}/compute").json()["results"]
    assert res["pricing"]["design_blocked"] == [] and client.get(f"/api/assessments/{aid}/plans.pdf").status_code == 200
