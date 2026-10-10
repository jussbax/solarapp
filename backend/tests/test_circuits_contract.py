"""Round 13, step 1 (brief 2.1 and 2.6): `pricing.choices.circuits`, the per-circuit records the design analysis and the
single-line diagram read, written by the BOQ from the figures it already computes. The round-3 sample job (8 panels,
6 kW, 11.7 kWh, no datasheets) keeps its BOM and carries seven rows and no blocking code; every record carries the
figures the BOQ prints (the gauge, the run, the current, the breaker, the drop, the conduit); a figure the generator has
not computed is None with its reason; no row reads "pass" before the design analysis derates it; with the datasheets
the PV row carries 1.25 × 1.25 × Isc and the DC breaker the generator chose."""
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.pricing.boq import BoqRequest, generate_boq, rows_for
from solarapp.pricing.design_checks import CIRCUIT_ROWS, mm2_in_text
from solarapp.pricing.engine import JobInputs, price_job
from solarapp.pricing.importer import read_workbook
from tests.test_drawings import PILA_DOC

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "datasheets"
FILES = [FIXTURES / f"ALL_{n}_DATA_SHEET.xlsx" for n in ("SOLAR_PANEL", "INVERTER", "BATTERY")]
KEYS = {"id", "name", "kind", "applies", "count", "conductors", "run_m", "voltage_v", "i_continuous_a", "i_design_a", "ocpd_a", "ocpd_code", "placement",
        "conduit_code", "conduit_inner_diameter_mm", "ambient_c", "rooftop_adder_c", "t_conductor_c", "ampacity_rule_a", "ampacity_rule_column", "ampacity_base_a",
        "ampacity_terminal_a", "f_temp", "f_fill", "ampacity_derated_a", "fill_pct", "fill_limit_pct", "egc_required_mm2", "egc_provided_mm2", "egc_provided_code",
        "drop_pct", "checks", "status", "notes"}


@pytest.fixture(scope="module")
def imported():
    return read_workbook(WB)


def _line(res, role):
    return next(l for l in res.lines if l.role == role)


def _rows(res) -> dict[str, dict]:
    return {c["id"]: c for c in res.choices["circuits"]}


def test_the_sample_job_carries_seven_rows_with_the_boqs_figures_and_keeps_its_bom(imported):
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(BoqRequest("BC-PNL-004", 8, rows_for(8, 4, 1.134), inverter_kw=6, battery_kwh=11.7), cat, cfg)
    ch = res.choices
    rows = ch["circuits"]
    assert [c["id"] for c in rows] == [cid for cid, _, _ in CIRCUIT_ROWS] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    assert all(set(c) == KEYS for c in rows) and not [w for w in res.warnings if w.get("blocks_documents")]
    by = _rows(res)
    # C1, the PV string: the gauge, the run, the current, the voltage, the drop and the DC breaker the BOM prints; no Isc on file, so the rule's design current
    c1 = by["C1"]
    assert c1["applies"] and c1["count"] == ch["strings"] == 1 and c1["kind"] == "dc_pv"
    assert c1["conductors"] == {"n_total": 2, "n_current_carrying": 2, "size_mm2": float(ch["pv_gauge"]), "insulation_c": None, "type": "PV wire"}
    assert c1["run_m"] == ch["pv_run_m"] == cfg.wiring.pv_run_m == 25 and c1["voltage_v"] == ch["string_voltage_v"]
    assert c1["i_continuous_a"] == ch["string_current_a"] and c1["i_design_a"] == pytest.approx(ch["string_current_a"] * 1.25)
    assert c1["ocpd_code"] == _line(res, "dc_breaker").code == "IAN-PRT-009" and c1["ocpd_a"] is None   # the rating is not checked without Isc
    assert c1["drop_pct"] == ch["pv_drop"] and c1["placement"] == "rooftop_free_air" and c1["conduit_code"] is None
    assert c1["ampacity_rule_a"] == cfg.wiring.pv_cable_ampacity[ch["pv_gauge"]] == 40 and "PV cable table" in c1["ampacity_rule_column"]
    assert c1["egc_provided_mm2"] == 10 and c1["egc_provided_code"] == "IAN-WIR-029"   # the bonding role's item names its size
    assert c1["checks"]["ampacity_ge_ocpd"] is None and c1["status"] == "not checked" and any("not checked without Isc" in n for n in c1["notes"])
    # C2 does not apply: one string, nothing joins
    assert by["C2"]["applies"] is False and by["C2"]["count"] == 0 and by["C2"]["i_continuous_a"] is None
    # C3, the battery circuit: the inverter's current, the breaker's minimum and the breaker chosen, the lug pairs' gauge and table ampacity
    c3, bc = by["C3"], ch["battery_circuit"]
    assert c3["applies"] and c3["count"] == 1 and c3["conductors"]["size_mm2"] == float(bc["cable_gauge"]) and c3["conductors"]["type"] == "battery cable"
    assert c3["i_continuous_a"] == bc["current_a"] == ch["battery_current_a"] and c3["i_design_a"] == bc["breaker_min_a"] == pytest.approx(1.25 * bc["current_a"])
    assert c3["ocpd_a"] == bc["breaker_a"] and c3["ocpd_code"] == _line(res, "battery_breaker").code and c3["ampacity_rule_a"] == bc["cable_ampacity_a"]
    assert c3["checks"]["design_le_ocpd"] is True and c3["checks"]["ampacity_ge_ocpd"] is True and c3["status"] == "not checked"
    assert c3["run_m"] is None and c3["drop_pct"] is None and c3["egc_provided_mm2"] is None and any("no battery-rack" in n for n in c3["notes"])
    assert c3["voltage_v"] == 51.2 and any("wiring rules' 51.2 V" in n for n in c3["notes"])   # the seed's battery item has no nominal voltage: the rule's, said so
    # C4, the inverter output: 6 kW at 230 V, the breaker, the THHN gauge and its 60 °C figure, the drop, the EGC on the same line
    c4 = by["C4"]
    assert c4["applies"] and c4["count"] == 1 and c4["i_continuous_a"] == pytest.approx(6000 / 230) and c4["i_design_a"] == pytest.approx(6000 / 230 * 1.25)
    assert c4["ocpd_a"] == ch["ac_breaker_a"] == 40 and c4["ocpd_code"] == "IAN-PRT-027" and c4["conductors"]["size_mm2"] == float(ch["ac_gauge"]) == 8.0
    assert c4["conductors"]["n_total"] == c4["conductors"]["n_current_carrying"] == 2 and c4["conductors"]["type"] == "THHN"
    assert c4["run_m"] == ch["ac_run_m"] == 15 and c4["voltage_v"] == 230 and c4["drop_pct"] == ch["ac_drop"]
    assert c4["ampacity_rule_a"] == cfg.wiring.thhn_ampacity["8.0"] == 40 and "60 °C" in c4["ampacity_rule_column"]
    assert c4["placement"] == "indoor_conduit" and c4["conduit_code"] == _line(res, "conduit").code == "IAN-ENC-011" and c4["conduit_inner_diameter_mm"] is None
    assert c4["egc_provided_mm2"] == 8.0 and c4["egc_provided_code"] == _line(res, "thhn").code
    assert c4["checks"]["design_le_ocpd"] is True and c4["checks"]["ampacity_ge_ocpd"] is True and c4["checks"]["ocpd_le_derated"] is None and c4["status"] == "not checked"
    # C5 and C6, the grid side: the same figures, the feed and the bypass, one each per inverter
    for cid in ("C5", "C6"):
        c = by[cid]
        assert c["applies"] and c["count"] == 1 and c["i_continuous_a"] == ch["ac_grid_current_a"] and c["ocpd_a"] == ch["ac_grid_breaker_a"]
        assert c["conductors"]["size_mm2"] == float(ch["ac_grid_gauge"]) and c["drop_pct"] == ch["ac_grid_drop"] and c["status"] == "not checked"
    assert any("AC input rating is not on the item" in n for n in by["C5"]["notes"])   # the seed's eco-hybrid has none
    # C7, the equipment grounding: the grounding run on the THHN line, the array bonding named
    c7 = by["C7"]
    assert c7["applies"] and c7["run_m"] == ch["grounding_run_m"] == 20 and c7["conductors"]["size_mm2"] == 8.0 and c7["conductors"]["n_current_carrying"] == 0
    assert c7["egc_provided_mm2"] == 8.0 and c7["ocpd_a"] is None and any("IAN-WIR-029" in n and "10 mm²" in n for n in c7["notes"])
    # the derated figures are None on every row, and no row reads "pass" (the design analysis is a later step)
    for c in rows:
        assert c["ampacity_derated_a"] is None and c["f_temp"] is None and c["fill_pct"] is None and c["egc_required_mm2"] is None and c["ambient_c"] is None
        assert c["status"] in ("not checked", "fail") and c["status"] != "pass"
        assert c["checks"]["ocpd_le_derated"] is None and c["checks"]["fill_ok"] is None and c["checks"]["egc_ok"] is None
    # the BOM and the totals are the round-3 sample's (test_boq pins the mounting; the price is the engine's as before)
    q = {l.role: l.qty for l in res.lines}
    assert q["rail"] == 8 and q["l_foot"] == 24 and q["ac_breaker"] == 3 and q["dc_breaker"] == 1
    priced = price_job(res.lines, cat, cfg, JobInputs(net_metering=True))
    assert priced["totals"]["contract_rounded"] > 200000 and priced["missing_codes"] == []


def test_a_net_metering_job_has_no_battery_row_and_the_rows_keep_their_numbers(imported):
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=0, kind="net_metering"), cat, cfg)
    by = _rows(res)
    assert [c["id"] for c in res.choices["circuits"]] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    assert by["C3"]["applies"] is False and by["C3"]["count"] == 0 and by["C3"]["ocpd_a"] is None and "no battery on this job" in by["C3"]["notes"]
    assert by["C4"]["applies"] and by["C1"]["applies"] and by["C7"]["applies"]


def test_a_failed_boq_coordination_reads_fail_on_its_row(imported):
    """The hard ac_circuit warning (round 3): a unit whose output no standard breaker covers; the inverter-output row says so."""
    cat, cfg = imported.catalog, imported.config
    big = next(i for i in cat.by_category("Inverter") if i.rating and (i.rating_unit or "").lower() == "kw" and i.rating >= 80)
    res = generate_boq(BoqRequest("BC-PNL-001", 40, rows_for(40, 10, 1.134), inverter_kw=80, battery_kwh=0, kind="net_metering", inverter_code=big.code), cat, cfg)
    assert any(w["code"] == "ac_circuit" and w.get("blocks_documents") for w in res.warnings)
    c4 = _rows(res)["C4"]
    assert c4["ocpd_a"] is None and c4["checks"]["design_le_ocpd"] is None and any("no standard breaker size" in n for n in c4["notes"])
    cfg2 = cfg.model_copy(deep=True)
    cfg2.wiring.ac_breaker_sizes_a = [16, 20, 25, 32, 40]   # a breaker list that stops at 40 A: the 6 kW unit's output needs it, the grid side (on a 50 A input) does not fit
    small = generate_boq(BoqRequest("BC-PNL-001", 9, rows_for(9, 8, 1.134), inverter_kw=6, battery_kwh=9.6), cat, cfg2)
    c4 = _rows(small)["C4"]
    assert c4["ocpd_a"] == 40 and c4["checks"]["design_le_ocpd"] is True


def test_mm2_in_text_reads_the_items_sizes():
    assert mm2_in_text("THHN 8.0mm2 EURO WIRES") == 8.0 and mm2_in_text("JOCA GROUNDING WIRE 10mm2", "") == 10 and mm2_in_text("70mm2 - 1M w/ LUG PAIR") == 70
    assert mm2_in_text("Solar cable 4 mm², red") == 4 and mm2_in_text("EARTH LUG", None) is None


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def test_the_project_results_carry_the_block_and_the_datasheets_fill_the_pv_row(client):
    """Through the API: the Pila sample's results carry the seven rows; with the datasheets and a 500 V input on the
    inverter the PV row's continuous current is 1.25 × Isc, its design current 1.25 × 1.25 × Isc and its OCPD the DC breaker the generator chose; the
    strings on the MPPT inputs decide the combined row; the set's sheet count is unchanged (nothing on the sheets
    reads the block yet)."""
    aid = client.post("/api/assessments", json=deepcopy(PILA_DOC)).json()["id"]
    res = client.post(f"/api/assessments/{aid}/compute").json()["results"]
    ch = res["pricing"]["choices"]
    rows = {c["id"]: c for c in ch["circuits"]}
    assert len(ch["circuits"]) == 7 and rows["C1"]["i_continuous_a"] == ch["string_current_a"] and rows["C4"]["ocpd_a"] == ch["ac_breaker_a"]
    assert rows["C1"]["ocpd_a"] is None and rows["C3"]["applies"] and res["pricing"]["design_blocked"] == []
    for f in FILES:
        with open(f, "rb") as fh:
            assert client.post("/api/pricing/datasheets", files={"file": (f.name, fh, "application/octet-stream")}).status_code == 200
    assert client.put("/api/pricing/items/FS-INV-008", json={"max_pv_voltage_v": 500}).status_code == 200
    res = client.post(f"/api/assessments/{aid}/compute").json()["results"]
    ch = res["pricing"]["choices"]
    sc, dcb = ch["string_design"]["current"], ch["dc_breaker"]
    rows = {c["id"]: c for c in ch["circuits"]}
    c1 = rows["C1"]
    assert sc["source"] == "datasheet" and c1["i_design_a"] == pytest.approx(sc["i_cond_a"]) == pytest.approx(1.25 * 1.25 * sc["isc_a"])
    # the review's finding 2: the continuous current is the PV article's 1.25 × Isc (13.53 A → 16.91 A), not Imp; the design current 1.25 × it
    assert c1["ocpd_a"] == dcb["ocpd_a"] and c1["ocpd_code"] == dcb["code"] and c1["i_continuous_a"] == pytest.approx(1.25 * sc["isc_a"]) == pytest.approx(16.91, abs=0.01)
    assert c1["i_design_a"] == pytest.approx(1.25 * c1["i_continuous_a"]) == pytest.approx(21.14, abs=0.01)
    assert c1["checks"]["design_le_ocpd"] is True and c1["checks"]["ampacity_ge_ocpd"] is (c1["ampacity_rule_a"] >= c1["ocpd_a"])
    joined = [i for i in ch["string_design"]["per_mppt"] if i["strings"] > 1]
    assert rows["C2"]["applies"] is bool(joined)
    assert rows["C3"]["voltage_v"] == 51.2 and not any("wiring rules' 51.2 V" in n for n in rows["C3"]["notes"])   # the datasheet gives the pack's nominal voltage
