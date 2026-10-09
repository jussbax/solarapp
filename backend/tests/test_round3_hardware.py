"""Round 3, batch 1 (hardware that is wrong): the net-metering inverter rule and the parallel rule (E-01), the
battery on continuous current and the battery circuit coordination that holds the customer documents (E-03), the
AC side sized breaker-first with the conductor from the breaker (E-04), the certificate on file (E-05), the BOM
counts and the roles the BOM used to omit (E-06), the paper slips in these files (E-12) and the BOM export (E-14)."""
import dataclasses
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solarapp.api.assessments import _pack_note
from solarapp.config import Settings
from solarapp.core.simulation import ThermalModel
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.pricing.boq import NO_ITEM_PREFIX, BoqRequest, battery_current_ok, choose_inverter_units, generate_boq, next_standard_size, pass_through_check, rows_for, select_battery
from solarapp.pricing.catalog import electrical_from_remarks
from solarapp.pricing.config import BoqRoles, PricingConfig
from solarapp.pricing.importer import electrical_columns, electrical_values, read_workbook
from tests.test_documents import LAGUNA_DOC

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"


@pytest.fixture(scope="module")
def imported():
    return read_workbook(WB)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def _req(kind="combination", required=4.95, battery=0.0, panels=11, **kw) -> BoqRequest:
    return BoqRequest("BC-PNL-001", panels, rows_for(panels, 6, 2.278), inverter_kw=6, inverter_required_kw=required, battery_kwh=battery, kind=kind, **kw)


def _line(res, role):
    return next(l for l in res.lines if l.role == role)


def _codes(res) -> set[str]:
    return {w["code"] for w in res.warnings}


# ---------------------------------------------------------------- E-01: the net-metering inverter and the parallel rule
def test_net_metering_takes_one_unit_on_the_array_rule_and_checks_the_pass_through(imported):
    """The Santo Tomas case: 11 panels (6.43 kWp, 4.95 kW on the PV rule) with a 6.31 kW house peak gets ONE
    eco-hybrid, not two in parallel; the peak is checked against the unit's AC input rating instead."""
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(_req("net_metering", required=4.95, peak_load_kw=6.31), cat, cfg)
    inv = _line(res, "inverter")
    assert inv.code == "FS-INV-008" and inv.qty == 1 and "parallel" not in inv.note
    assert _line(res, "ac_breaker").qty == 3 and _line(res, "enclosure").qty == 1 and _line(res, "thhn").qty == 110
    # the seed item has no AC input rating: the pass-through check says so
    assert "inverter_pass_through_unknown" in _codes(res) and res.choices["pass_through"]["ok"] is None
    assert res.choices["pass_through"]["house_peak_kw"] == 6.31 and res.choices["pass_through"]["house_peak_a"] == pytest.approx(6310 / 230)
    # with a rating on the item: fine when it covers the peak, a warning when it does not; off the grid kinds with a battery there is no check
    ok = dataclasses.replace(cat.get("FS-INV-008"), ac_input_a=50.0)
    block, w = pass_through_check(ok, 1, 6.31, 230)
    assert block["ok"] is True and w == []
    block, w = pass_through_check(dataclasses.replace(ok, ac_input_a=20.0), 1, 6.31, 230)
    assert block["ok"] is False and w[0]["code"] == "inverter_pass_through" and not w[0].get("hard")
    hybrid = generate_boq(_req("combination", required=4.79, battery=13.6, peak_load_kw=4.79), cat, cfg)
    assert "pass_through" not in hybrid.choices and not _codes(hybrid) & {"inverter_pass_through", "inverter_pass_through_unknown"}


def test_parallel_rule_tolerance_then_a_single_larger_unit_then_parallel(imported):
    cat, cfg = imported.catalog, imported.config
    eco = cat.get("FS-INV-008")
    # within the tolerance (default 10%): one unit, warned
    unit, n, w = choose_inverter_units(eco, 6.31, False, cat, cfg, "combination")
    assert unit.code == "FS-INV-008" and n == 1 and w[0]["code"] == "inverter_overshoot_tolerated" and "5% over" in w[0]["message"]
    # tolerance 0: the cheapest single grid-interactive unit that fits, warned with the parallel price
    cfg0 = cfg.model_copy(deep=True)
    cfg0.roles.inverter_parallel_tolerance_pct = 0
    unit, n, w = choose_inverter_units(eco, 6.31, False, cat, cfg0, "combination")
    assert unit.code != "FS-INV-008" and n == 1 and unit.grid_interactive is True and unit.rating >= 6.31
    assert w[0]["code"] == "inverter_stepped_up" and "2 × FS-INV-008 in parallel" in w[0]["message"]
    # the owner's per-job pick is never swapped: it goes parallel, warned
    unit, n, w = choose_inverter_units(eco, 6.31, True, cat, cfg0, "combination")
    assert unit.code == "FS-INV-008" and n == 2 and w[0]["code"] == "inverter_parallel"
    # nothing single fits (30 kW on a grid job: the 3-phase units are excluded): parallel default units, warned
    res = generate_boq(_req("net_metering", required=30.0, panels=40), cat, cfg)
    inv = _line(res, "inverter")
    assert inv.code == "FS-INV-008" and inv.qty == 5 and "inverter_parallel" in _codes(res)
    # the setting is a plain percentage with the class default of 10
    assert BoqRoles().inverter_parallel_tolerance_pct == 10


# ---------------------------------------------------------------- E-03: the battery on continuous current, the circuit that must hold
def test_battery_is_picked_on_continuous_current_before_the_cheapest_kwh(imported):
    """The Pila case: 13.6 kWh for an inverter that draws 135 A. BC-BAT-004 (15.36 kWh, 100 A) is the cheapest
    kWh and fails the current; FS-BAT-003 (15 kWh, 160 A) is picked. Unknown ratings rank between, never first."""
    cat, cfg = imported.catalog, imported.config
    opts = select_battery(13.6, cat, cfg, 135.0)
    assert opts[0][0].code == "FS-BAT-003" and opts[0][1] == 1
    ranks = [battery_current_ok(i, n, 135.0) for i, n, c in opts]
    first_unknown = ranks.index(None) if None in ranks else len(ranks)
    first_fail = ranks.index(False) if False in ranks else len(ranks)
    assert all(r is True for r in ranks[:first_unknown]) and first_unknown <= first_fail
    assert next(i.code for i, n, c in opts if battery_current_ok(i, n, 135.0) is False) == "BC-BAT-004"
    # without a current the old rule stands (cheapest kWh first)
    assert select_battery(13.6, cat, cfg)[0][0].code == "BC-BAT-004"
    res = generate_boq(_req("combination", required=4.79, battery=13.6), cat, cfg)
    bat = _line(res, "battery")
    assert bat.code == "FS-BAT-003" and bat.qty == 1 and "160 A continuous against 135 A" in bat.note
    assert res.choices["battery_nominal_kwh"] == 15.0 and res.choices["battery_options"][0]["current_ok"] is True
    assert not _codes(res) & {"battery_current", "battery_circuit", "battery_current_unknown"}
    # a battery without a rating on its item: a plain reminder, the documents are not held
    cat2 = deepcopy(cat)
    cat2.get("FS-BAT-003").continuous_a = None
    res2 = generate_boq(_req("combination", required=4.79, battery=13.6, battery_code="FS-BAT-003"), cat2, cfg)
    w = next(x for x in res2.warnings if x["code"] == "battery_current_unknown")
    assert not w.get("hard") and not w.get("blocks_documents")


def test_battery_breaker_and_cable_coordinate_or_the_design_is_blocked(imported):
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(_req("combination", required=4.79, battery=13.6), cat, cfg)
    circuit = res.choices["battery_circuit"]
    assert circuit["current_a"] == 135 and circuit["breaker_min_a"] == pytest.approx(168.75) and circuit["breaker_a"] == 250
    assert circuit["cable_gauge"] == "70" and circuit["cable_ampacity_a"] == 270 and circuit["ok"]
    assert _line(res, "battery_cable").code == cfg.roles.battery_cable_pair["70"] and "250 A breaker" in _line(res, "battery_cable").note
    # no lug pair carries the breaker: a hard warning that holds the documents (never a silent print)
    cfg2 = cfg.model_copy(deep=True)
    cfg2.wiring.battery_cable_ampacity = {"16": 100, "25": 140, "35": 170}
    res2 = generate_boq(_req("combination", required=4.79, battery=13.6), cat, cfg2)
    w = next(x for x in res2.warnings if x["code"] == "battery_circuit")
    assert w["hard"] and w["blocks_documents"] and "250 A breaker" in w["message"] and not res2.choices["battery_circuit"]["ok"]
    # no breaker large enough: the same hard warning
    cfg3 = cfg.model_copy(deep=True)
    cfg3.roles.battery_breaker_pattern = "DC BATTERY BREAKER 125A"
    cfg3.roles.battery_breaker_fallback = "IAN-PRT-001"
    res3 = generate_boq(_req("combination", required=4.79, battery=13.6), cat, cfg3)
    w3 = next(x for x in res3.warnings if x["code"] == "battery_circuit")
    assert w3["hard"] and w3["blocks_documents"] and "at least 169 A" in w3["message"]


def test_a_blocked_design_refuses_the_customer_documents_on_the_server(client):
    """The stale mechanism with a second reason: pricing.design_blocked names the rule, the proposal, roof check
    and card answer 409 with "design_blocked", the internal program and the BOM export still print."""
    doc = deepcopy(LAGUNA_DOC)
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    pr, sizing = res["pricing"], res["sizing"]
    assert pr["design_blocked"] == [] and "inverter_certificate" in pr
    assert sizing["battery"]["sized_nominal_kwh"] == sizing["battery"]["installed_kwh"] and sizing["battery"]["sized_usable_kwh"] == sizing["battery"]["usable_kwh"]
    need = float(sizing["battery"]["installed_kwh"])
    # the owner picks a 100 A battery whose single unit covers the kWh: the bank cannot deliver the inverter's 135 A
    code = "BC-BAT-003" if need <= 10.24 else "BC-BAT-004" if need <= 15.36 else None
    if code is None:
        pytest.skip("the Laguna case needs more than one 100 A pack, which passes the current rule")
    doc["pricing"] = {"battery_code": code}
    r = client.post(f"/api/assessments/{aid}/compute", json=doc)
    assert r.status_code == 200, r.text
    pr = r.json()["results"]["pricing"]
    assert pr["design_blocked"] == ["battery_current"]
    hard = next(w for w in pr["warnings"] if w["code"] == "battery_current")
    assert hard["hard"] and hard["blocks_documents"]
    from tests.conftest import real_weather
    real_weather(aid, client)
    for name in ("quotation.pdf", "report.pdf", "card.png"):
        answer = client.get(f"/api/assessments/{aid}/{name}")
        assert answer.status_code == 409 and answer.json()["detail"].startswith("design_blocked: ") and "battery_current" in answer.json()["detail"]
    assert client.get(f"/api/assessments/{aid}/program.pdf").status_code == 200
    assert client.get(f"/api/assessments/{aid}/bom.csv").status_code == 200
    # the fix: a battery rated for the current; the documents print again
    doc["pricing"] = {"battery_code": "FS-BAT-003"}
    assert client.post(f"/api/assessments/{aid}/compute", json=doc).json()["results"]["pricing"]["design_blocked"] == []
    real_weather(aid, client)
    assert client.get(f"/api/assessments/{aid}/quotation.pdf").status_code == 200


# ---------------------------------------------------------------- E-04: the AC side, breaker first, conductor from the breaker
def test_ac_breakers_round_up_to_the_standard_size_and_the_conductor_follows(imported):
    cat, cfg = imported.catalog, imported.config
    assert next_standard_size(32.6, cfg.wiring.ac_breaker_sizes_a) == 40 and next_standard_size(62.6, cfg.wiring.ac_breaker_sizes_a) == 63
    assert next_standard_size(400, cfg.wiring.ac_breaker_sizes_a) is None
    assert cfg.wiring.thhn_ampacity["3.5"] == 20   # the 60 C column; the 25 A entry was wrong
    res = generate_boq(_req("combination", required=4.79, battery=13.6), cat, cfg)
    ch = res.choices
    # 6 kW at 230 V: 26 A x 1.25 = 33 A -> 40 A; 8.0 mm2 THHN carries 40 A, so the breaker protects the conductor
    assert ch["ac_current_a"] == pytest.approx(6000 / 230) and ch["ac_breaker_a"] == 40 and ch["ac_gauge"] == "8.0"
    assert not ch["ac_grid_rating_known"] and ch["ac_grid_breaker_a"] == 40 and "ac_grid_rating_unknown" in _codes(res)
    b = _line(res, "ac_breaker")
    assert b.qty == 3 and "1 inverter-output breaker at 40 A" in b.note and "2 grid-side breakers at 40 A" in b.note
    t = _line(res, "thhn")
    assert t.qty == 1 * 2 * 15 + 2 * 2 * 15 + 20 and "8.0 mm2 (40 A) for the 40 A breakers" in t.note
    # the role item is listed in 32 and 63 A only: the BOM says the 40 A size must be added
    assert "the circuits need 40 A" in next(w for w in res.warnings if w["code"] == "ac_breaker_size")["message"]
    # a unit with its AC input rating on file: the grid side is sized on it and gets its own, larger conductor
    cat2 = deepcopy(cat)
    cat2.get("FS-INV-008").ac_input_a = 50.0
    res2 = generate_boq(_req("combination", required=4.79, battery=13.6), cat2, cfg)
    ch2 = res2.choices
    assert ch2["ac_grid_rating_known"] and ch2["ac_grid_current_a"] == 50 and ch2["ac_grid_breaker_a"] == 63 and ch2["ac_grid_gauge"] == "22"
    assert ch2["ac_breaker_a"] == 40 and ch2["ac_gauge"] == "8.0"
    roles = {l.role: l for l in res2.lines}
    assert roles["thhn"].qty == 1 * 2 * 15 + 20 and roles["thhn_grid"].qty == 2 * 2 * 15 and roles["thhn_grid"].code == cfg.roles.thhn["22"]
    assert "ac_grid_rating_unknown" not in _codes(res2) and "2 grid-side breakers at 63 A" in roles["ac_breaker"].note
    # the ATS and the disconnect follow the grid side
    assert "63 A" in roles["ac_disconnect"].note and "ats" in roles
    # nothing in the THHN list carries the breaker: a hard warning that holds the documents
    cfg3 = cfg.model_copy(deep=True)
    cfg3.wiring.thhn_ampacity = {"3.5": 20, "5.5": 30}
    res3 = generate_boq(_req("combination", required=4.79, battery=13.6), cat, cfg3)
    w = next(x for x in res3.warnings if x["code"] == "ac_circuit")
    assert w["hard"] and w["blocks_documents"]


# ---------------------------------------------------------------- E-05: the certificate on file
def test_certificate_missing_is_warned_on_grid_jobs_and_carried_for_the_proposal(imported):
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(_req("net_metering", required=4.95), cat, cfg)
    w = next(x for x in res.warnings if x["code"] == "inverter_certificate_missing")
    assert not w.get("hard") and "confirm the listing with the maker before the DU application" in w["message"]
    assert res.choices["inverter_certifications"] == ""
    off = generate_boq(_req("off_grid", required=4.95, battery=13.6), cat, cfg)
    assert "inverter_certificate_missing" not in _codes(off)
    cat2 = deepcopy(cat)
    cat2.get("FS-INV-008").certifications = "IEC 62116 (verify)"
    res2 = generate_boq(_req("net_metering", required=4.95), cat2, cfg)
    assert "inverter_certificate_missing" not in _codes(res2) and res2.choices["inverter_certifications"] == "IEC 62116 (verify)"
    # an unmarked unit keeps the older note; a unit marked unable to export keeps its hard warning
    res3 = generate_boq(_req("net_metering", required=4.95, inverter_code="BC-INV-006"), cat, cfg)
    assert "inverter_certificate_unknown" in _codes(res3) and "inverter_certificate_missing" not in _codes(res3)


# ---------------------------------------------------------------- E-06: counts and the roles the BOM used to omit
def test_bom_counts_spds_enclosures_and_the_transfer_switch(imported):
    cat, cfg = imported.catalog, imported.config
    one = generate_boq(_req("combination", required=4.79, battery=13.6, panels=7), cat, cfg)   # 1 string on a 2-MPPT unit
    assert _line(one, "dc_spd").qty == 1 and _line(one, "ac_spd").qty == 1 and _line(one, "enclosure").qty == 1
    two = generate_boq(_req("net_metering", required=4.95, panels=11), cat, cfg)                # 2 strings on 2 MPPTs
    assert _line(two, "dc_spd").qty == 2 and _line(two, "dc_breaker").qty == 2 and two.choices["dc_spds"] == 2
    three = generate_boq(_req("net_metering", required=4.95, panels=25), cat, cfg)              # 3 strings share 2 MPPT inputs
    assert _line(three, "dc_spd").qty == 2
    # the ATS: unknown on the item -> priced with a warning; built in -> no ATS line; none -> priced without the warning
    assert "ats_unknown" in _codes(one) and _line(one, "ats").qty == 1
    cat2 = deepcopy(cat)
    cat2.get("FS-INV-008").has_transfer_switch = True
    built_in = generate_boq(_req("combination", required=4.79, battery=13.6, panels=7), cat2, cfg)
    assert not any(l.role == "ats" for l in built_in.lines) and built_in.choices["ats"] == "built-in" and "ats_unknown" not in _codes(built_in)
    cat2.get("FS-INV-008").has_transfer_switch = False
    external = generate_boq(_req("combination", required=4.79, battery=13.6, panels=7), cat2, cfg)
    assert _line(external, "ats").qty == 1 and "ats_unknown" not in _codes(external)
    # the flag reads from the workbook column or the remark
    assert electrical_from_remarks("Inverter", "6 kW hybrid", "", "built-in ATS; 2 MPPT 20A each")["has_transfer_switch"] is True
    assert electrical_from_remarks("Inverter", "6 kW hybrid", "", "no internal transfer, external ATS needed")["has_transfer_switch"] is False
    assert "has_transfer_switch" not in electrical_from_remarks("Inverter", "6 kW hybrid", "", "2 MPPT 20A each")
    cols = electrical_columns(("Code", "Transfer switch (built in)", "Battery max A"))
    assert cols == {"has_transfer_switch": 1, "battery_max_a": 2}
    assert electrical_values(("X", "yes", 120), cols, "Inverter", "6 kW hybrid", "", "")["has_transfer_switch"] is True


def test_omitted_roles_are_on_the_bom_with_quantities_and_never_an_invented_price(imported):
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(_req("net_metering", required=4.95, panels=11), cat, cfg)
    roles = {l.role: l for l in res.lines}
    # bonding along the array: the rail-line length of every row plus the jumpers; lugs per panel and per rail line
    rows = [r for r in res.choices["rows"] if r["panels"] > 0]
    assert roles["array_bonding"].code == "IAN-WIR-029" and roles["array_bonding"].qty == pytest.approx(sum(r["length_m"] for r in rows) + 2 * len(rows), abs=0.1)
    assert roles["earth_lug"].qty == 4 + 11 * 1 + 2 * len(rows) * 1
    # fasteners come with the L-foot set, placards are consumables and monitoring is in the inverter (the owner, round 4):
    # no NO-ITEM line and no "role without item" warning on the seed list
    assert not any(l.code.startswith(NO_ITEM_PREFIX) for l in res.lines)
    assert not [w for w in res.warnings if w["code"] == "role_without_item"]
    # the visible AC disconnect, rated for the grid side; the export limiter as an optional role with its warning on net metering
    assert roles["ac_disconnect"].code == "IAN-PRT-030" and "lockable" in roles["ac_disconnect"].note
    assert "export_limiter" in _codes(res) and "export_limiter" not in roles
    cfg2 = cfg.model_copy(deep=True)
    cfg2.roles.export_limiter = "IAN-ACC-008"
    res2 = generate_boq(_req("net_metering", required=4.95, panels=11), cat, cfg2)
    roles2 = {l.role: l for l in res2.lines}
    assert roles2["export_limiter"].code == "IAN-ACC-008" and "export_limiter" not in _codes(res2)
    off = generate_boq(_req("off_grid", required=4.95, battery=13.6, panels=11), cat, cfg)
    assert "export_limiter" not in _codes(off) and not any(l.role == "export_limiter" for l in off.lines)
    # priced: the NO-ITEM lines cost nothing and are not "missing codes" in the warnings
    from solarapp.pricing.engine import JobInputs, price_job
    priced = price_job(res.lines, cat, cfg, JobInputs(net_metering=True))
    assert not [l for l in priced["lines"] if l["code"].startswith(NO_ITEM_PREFIX)]
    # a role the owner blanks still puts its line on the BOM, named by its role, with the quantity and no price
    cfg3 = cfg.model_copy(deep=True)
    cfg3.roles.ac_disconnect = ""
    res3 = generate_boq(_req("net_metering", required=4.95, panels=11), cat, cfg3)
    priced3 = price_job(res3.lines, cat, cfg3, JobInputs(net_metering=True))
    no_item = [l for l in priced3["lines"] if l["code"].startswith(NO_ITEM_PREFIX)]
    assert len(no_item) == 1 and no_item[0]["name"] == "Ac disconnect (no item in the materials list)"
    assert no_item[0]["landed"] == 0 and no_item[0]["selling"] == 0 and not no_item[0]["found"]


def test_old_per_inverter_counts_migrate_once(imported):
    """A config saved before the AC circuit split carried 4 breakers, 4 SPDs and 2 enclosures per inverter; it takes
    the new defaults; a config that already has the grid-side count keeps what the owner typed."""
    old = BoqRoles.model_validate({"ac_breakers_per_inverter": 4, "ac_spds_per_inverter": 4, "enclosures": 2})
    assert (old.ac_breakers_per_inverter, old.ac_spds_per_inverter, old.enclosures, old.ac_grid_breakers_per_inverter) == (1, 1, 1, 2)
    new = BoqRoles.model_validate({"ac_breakers_per_inverter": 2, "ac_spds_per_inverter": 2, "enclosures": 2, "ac_grid_breakers_per_inverter": 1})
    assert (new.ac_breakers_per_inverter, new.ac_spds_per_inverter, new.enclosures, new.ac_grid_breakers_per_inverter) == (2, 2, 2, 1)
    assert imported.config.roles.ac_breakers_per_inverter == 1 and imported.config.roles.ac_disconnect == "IAN-PRT-030"
    assert PricingConfig().roles.enclosures == 1


# ---------------------------------------------------------------- E-12 and E-14: the slips and the export
def test_bom_notes_read_in_the_plural_and_the_thermal_rise_in_degrees(imported):
    cat, cfg = imported.catalog, imported.config
    res = generate_boq(BoqRequest("BC-PNL-001", 2, rows_for(2, 2, 2.278), inverter_kw=6, battery_kwh=0, kind="net_metering"), cat, cfg)
    assert _line(res, "rail").note.startswith("1 row, 2 lines each") and _line(res, "pv_cable_red").note.startswith("1 string x")
    big = generate_boq(_req("net_metering", required=4.95, panels=11), cat, cfg)
    assert _line(big, "rail").note.startswith("2 rows, 2 lines each") and _line(big, "pv_cable_red").note.startswith("2 strings x")
    assert ThermalModel("site_rise", 26.9).describe() == "site-measured rise of 26.9 °C per kW/m² above ambient"


def test_pack_rounding_note():
    assert _pack_note(35, "m", "150 m box rate", "THHN 8.0mm2 EURO WIRES (150 m box rate)") == "1 × 150 m box"
    assert _pack_note(230, "m", "100 m roll, P4,650", "Solar cable 4mm2, red") == "3 × 100 m roll"
    assert _pack_note(30, "m", "m", "FLEX CONDUIT 32mm") == "" and _pack_note(2, "pc", "pc", "Cable TRAY 60*60 - 2METER") == ""
