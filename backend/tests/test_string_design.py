"""Round 12: the string design. The settings block (section 3 head: every value an assumption that moves the
settings version), the two TMY figures per project (T_cold and T_hot from the cell's typical-year extremes), and the
hand-worked checks of 3.1 to 3.4 on the brief's own figures."""
import dataclasses
import math
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.pricing.boq import BoqRequest, generate_boq, pick_gauge, rows_for
from solarapp.pricing.config import PricingConfig, StringDesign, settings_version
from solarapp.pricing.datasheets import import_datasheets
from solarapp.pricing.design_checks import design_temperatures, faiman_rise_c_per_kw, mppt_assignment, mppt_inputs, string_current, string_plan
from solarapp.pricing.importer import read_workbook
from solarapp.pricing.store import import_workbook, load_catalog
from tests.test_documents import LAGUNA_DOC

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "datasheets"
FILES = [FIXTURES / f"ALL_{n}_DATA_SHEET.xlsx" for n in ("SOLAR_PANEL", "INVERTER", "BATTERY")]
# the quick estimate's rounded price (₱1,000) on the sample request: with the seed alone, and with the three datasheets applied (brief 4.5)
QUICK_PRICE_SEED = 314000
QUICK_PRICE_WITH_DATASHEETS = 326000


def _line(res, role):
    return next(l for l in res.lines if l.role == role)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def test_the_settings_block_is_the_briefs_and_moves_the_version():
    sd = PricingConfig().string_design
    assert (sd.design_cold_c, sd.cold_margin_c, sd.design_hot_cell_c) == (14, 5, 70)
    assert (sd.temp_coeff_voc_default_pct, sd.temp_coeff_pmax_default_pct, sd.temp_coeff_isc_default_pct) == (-0.30, -0.35, 0.05)
    assert sd.isc_irradiance_factor == 1.25 and sd.dc_breaker_sizes_a == [16, 20, 25, 32, 40, 50, 63]
    cfg, cfg2 = PricingConfig(), PricingConfig()
    cfg2.string_design.design_cold_c = 10
    assert settings_version(cfg) != settings_version(cfg2)                     # a change flags quoted jobs
    cfg3 = PricingConfig(datasheets_imported_at="2026-10-10T00:00:00+00:00", datasheets_imported_from="x.xlsx")
    assert settings_version(cfg) == settings_version(cfg3)                     # the import stamp never does
    assert PricingConfig.model_validate({"wiring": {"pv_run_m": 20}}).string_design == StringDesign()   # an older config takes the block's defaults


def test_the_design_temperatures_take_the_wider_of_the_setting_and_the_cell():
    sd = StringDesign()
    t = design_temperatures(sd, None, None, 19.3, 34.1, 30.2)
    # floor(19.3) − 5 = 14, not below the 14 °C setting; 34.1 + 30.2 = 64.3, not above 70
    assert t["t_cold_c"] == 14 and t["cold_source"] == "setting" and t["tmy_cold_c"] == 14 and t["t_hot_c"] == 70 and t["hot_source"] == "setting" and t["tmy_hot_cell_c"] == pytest.approx(64.3)
    t2 = design_temperatures(sd, None, None, 16.8, 38.0, 37.0)
    assert t2["t_cold_c"] == 11 and t2["cold_source"] == "tmy" and t2["t_hot_c"] == 75 and t2["hot_source"] == "tmy"
    # the project's own figure stands in for the setting: a record low typed lower wins, a typed hot figure above the cell's stands
    t3 = design_temperatures(sd, 9.0, 80.0, 19.3, 34.1, 30.2)
    assert t3["t_cold_c"] == 9 and t3["cold_source"] == "project" and t3["t_hot_c"] == 80 and t3["hot_source"] == "project" and t3["cold_setting_c"] == 9
    # without a TMY (the website estimate) the settings alone
    t4 = design_temperatures(sd, None, None, None, None, None)
    assert t4["t_cold_c"] == 14 and t4["t_hot_c"] == 70 and t4["tmy_min_air_c"] is None
    # the Faiman rise at 1 kW/m² with the PVGIS constants: 37.2 °C still, about 30 at 1 m/s
    assert faiman_rise_c_per_kw(26.9, 6.2, 0.0) == pytest.approx(37.17, abs=0.01) and faiman_rise_c_per_kw(26.9, 6.2, 1.0) == pytest.approx(30.21, abs=0.01)


def test_results_carry_the_site_figures_and_the_project_override(client):
    aid = client.post("/api/assessments", json=deepcopy(LAGUNA_DOC)).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    site = r.json()["results"]["site"]
    sd = StringDesign()
    assert site["tmy_min_air_c"] < site["tmy_max_air_c"] and site["rise_c_per_kw"] > 0 and site["rise_source"] in ("site", "faiman")
    assert site["t_cold_c"] == min(sd.design_cold_c, math.floor(site["tmy_min_air_c"]) - sd.cold_margin_c)
    assert site["t_hot_c"] == pytest.approx(max(sd.design_hot_cell_c, site["tmy_max_air_c"] + site["rise_c_per_kw"]))
    assert site["cold_setting_c"] == 14 and site["hot_setting_c"] == 70
    # the pricing carries the same two figures into the string design block
    ch = r.json()["results"]["pricing"]["choices"]
    assert ch["string_design"]["t_cold_c"] == site["t_cold_c"] and ch["string_design"]["t_hot_c"] == pytest.approx(site["t_hot_c"])
    doc = client.get(f"/api/assessments/{aid}").json()["doc"]
    doc["pricing"] = {"design_cold_c": 5, "design_hot_cell_c": 90}
    res = client.post(f"/api/assessments/{aid}/compute", json=doc).json()["results"]
    assert res["site"]["t_cold_c"] <= 5 and res["site"]["cold_setting_c"] == 5 and res["site"]["t_hot_c"] >= 90 and res["site"]["hot_source"] == "project"
    assert res["pricing"]["choices"]["string_design"]["t_cold_c"] == res["site"]["t_cold_c"]


# ---------------------------------------------------------------- 3.1 to 3.4: the strings, the current, the breaker, the MPPT inputs

@pytest.fixture(scope="module")
def catalogs(tmp_path_factory):
    imported = read_workbook(WB)
    engine = create_engine(f"sqlite:///{tmp_path_factory.mktemp('sd') / 'sd.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        import_workbook(s, WB)
        import_datasheets(s, FILES)
        with_ds = load_catalog(s)
    return imported.catalog, with_ds, imported.config


def _with_500v(cat, code="FS-INV-008"):
    """The catalogue with the default inverter given a 500 V input (no sheet carries one yet: brief 6.6)."""
    cat2 = deepcopy(cat)
    cat2.items[code] = dataclasses.replace(cat2.items[code], max_pv_voltage_v=500)
    return cat2


def test_strings_from_the_cold_voc(catalogs):
    seed, cat, cfg = catalogs
    sd = cfg.string_design
    inv = dataclasses.replace(cat.get("FS-INV-008"), max_pv_voltage_v=500)
    # the 630 W panel (Voc 48.90, Vmp 40.70): 50.51 V at 14 °C, nine per string on a 500 V input; the fixed ten would be 505.1 V
    p = string_plan(cat.get("IAN-PNL-004"), inv, sd, 14.0, 70.0, 20, None, 10)
    assert p.available and p.voc_cold_v == pytest.approx(50.51, abs=0.005) and p.n_max == 9 and p.v_limit_v == 500 and p.limit_source == "inverter"
    assert p.vmp_hot_v == pytest.approx(34.29, abs=0.005) and p.vmp_cold_v == pytest.approx(40.70 * (1 + 0.0035 * 11), abs=0.005)   # the cold Vmp is the higher one
    assert p.per_string_cap == 9 and p.strings == 3 and p.per_string == 7 and p.n_min == 1
    assert p.coefficients["voc"].default and p.coefficients["voc"].value == -0.30 and [w["code"] for w in p.warnings] == ["temp_coeff_default"]
    assert "default temperature coefficient -0.3 %/°C for Voc (IAN-PNL-004 has none on file; an assumption)" in p.warnings[0]["message"]
    # the owner's 630 W bifacial (Voc 55.54): 57.37 V, eight; the 585 W monofacial the quick estimate uses (53.08): 54.83 V, nine
    assert string_plan(cat.get("BC-PNL-004"), inv, sd, 14.0, 70.0, 10, None, 10).voc_cold_v == pytest.approx(57.37, abs=0.005)
    assert string_plan(cat.get("BC-PNL-004"), inv, sd, 14.0, 70.0, 10, None, 10).n_max == 8
    assert string_plan(cat.get("BC-PNL-001"), inv, sd, 14.0, 70.0, 10, None, 10).voc_cold_v == pytest.approx(54.83, abs=0.005)
    assert string_plan(cat.get("BC-PNL-001"), inv, sd, 14.0, 70.0, 10, None, 10).n_max == 9
    # at Pila's own cell without the dataset-wide floor (16 °C) the 630 W panel gives 50.22 V and still nine
    p16 = string_plan(cat.get("IAN-PNL-004"), inv, sd, 16.0, 70.0, 20, None, 10)
    assert p16.voc_cold_v == pytest.approx(50.22, abs=0.005) and p16.n_max == 9
    # the panel's own coefficient replaces the default and the warning goes
    own = dataclasses.replace(cat.get("IAN-PNL-004"), temp_coeff_voc_pct=-0.25)
    po = string_plan(own, inv, sd, 14.0, 70.0, 20, None, 10)
    assert not po.coefficients["voc"].default and po.voc_cold_v == pytest.approx(48.90 * (1 + 0.0025 * 11), abs=0.005) and po.warnings == []
    # the forced ten (strings override): the hard warning that holds the documents; the generator itself never produces it
    pf = string_plan(cat.get("IAN-PNL-004"), inv, sd, 14.0, 70.0, 20, 2, 10)
    assert pf.per_string == 10 and pf.forced
    w = next(x for x in pf.warnings if x["code"] == "string_voltage_cold")
    assert w["hard"] and w["blocks_documents"] and "A string of 10 × IAN-PNL-004 reaches 505.1 V at 14 °C" in w["message"] and "above the inverter's 500 V maximum PV voltage" in w["message"]
    assert "The generator uses 9 per string; this job forces 10" in w["message"]
    # the MPPT window, given in the test (no sheet has it): n_min from Vmp_hot, the hot warning below it, the window's cap on top
    win = dataclasses.replace(inv, mppt_min_v=120, mppt_max_v=450)
    pw = string_plan(cat.get("IAN-PNL-004"), win, sd, 14.0, 70.0, 20, None, 10)
    assert pw.n_min == 4 and pw.n_max_window == int(450 // pw.vmp_cold_v) and pw.n_max == 9 and not any(x["code"] == "string_voltage_hot" for x in pw.warnings)
    few = string_plan(cat.get("IAN-PNL-004"), win, sd, 14.0, 70.0, 6, 3, 10)      # 2 per string: 68.6 V at 70 °C, below 120 V
    hot = next(x for x in few.warnings if x["code"] == "string_voltage_hot")
    assert "2 panels per string give 68.6 V at 70 °C, below the MPPT window's low end 120 V" in hot["message"] and "Use at least 4 per string" in hot["message"] and not hot.get("hard")
    # the panel's system voltage binds when it is the lower of the two
    low = dataclasses.replace(cat.get("OP-PNL-003"), max_system_voltage_v=600)       # the 100 W panel: 600 V (the lower of its two ratings)
    pl = string_plan(low, dataclasses.replace(inv, max_pv_voltage_v=1000), sd, 14.0, 70.0, 20, None, 30)
    assert pl.v_limit_v == 600 and pl.limit_source == "panel"
    # the fallback: no Voc, or no maximum PV voltage, says which and keeps the fixed rule
    fb = string_plan(seed.get("BC-PNL-001"), inv, sd, 14.0, 70.0, 20, None, 10)
    assert not fb.available and fb.reason == "BC-PNL-001 has no Voc on file" and fb.strings == 2 and fb.per_string == 10
    assert fb.warnings[0]["code"] == "string_rule_fallback" and "the strings follow the fixed rule of 10 per string" in fb.warnings[0]["message"]
    fb2 = string_plan(cat.get("IAN-PNL-004"), cat.get("FS-INV-008"), sd, 14.0, 70.0, 20, None, 10)
    assert not fb2.available and fb2.reason == "FS-INV-008 6 kW low-voltage eco-hybrid inverter has no maximum PV voltage on file"


def test_the_string_current_the_conductor_and_the_breaker(catalogs):
    seed, cat, cfg = catalogs
    # the 630 W panel: I_string 15.48 A (the rule gave 15.0), I_design 20.23 A, I_cond 25.28 A → 4 mm² holds, OCPD 32 A
    sc = string_current(cat.get("IAN-PNL-004"), 9, cfg, 70.0)
    assert sc["source"] == "datasheet" and sc["i_string_a"] == 15.48 and sc["v_string_v"] == pytest.approx(366.3) and sc["i_design_a"] == pytest.approx(20.225)
    assert sc["i_cond_a"] == pytest.approx(25.28125) and sc["ocpd_a"] == 32 and sc["isc_hot_a"] == pytest.approx(16.18 * (1 + 0.0005 * 45), abs=0.001)
    g, drop, ok = pick_gauge(sc["i_string_a"], 25, sc["v_string_v"], 0.03, cfg.wiring.pv_cable_ampacity, cfg, min_ampacity=sc["i_cond_a"])
    assert ok and g == "4"
    assert string_current(cat.get("IAN-PNL-001"), 9, cfg, 70.0)["ocpd_a"] == 32          # 720 W, Isc 18.59: 29.05 A → 32 A
    assert string_current(cat.get("BC-PNL-004"), 9, cfg, 70.0)["ocpd_a"] == 25           # the 630 W bifacial, Isc 15.15: 23.67 A → 25 A
    rule = string_current(seed.get("IAN-PNL-004"), 10, cfg, 70.0)
    assert rule["source"] == "rule" and rule["i_string_a"] == pytest.approx(15.0) and rule["v_string_v"] == 420 and rule["ocpd_a"] is None
    # in the BOQ on a 500 V input: ten 630 W panels go from one string to two (5 + 5): +1 DC breaker, +2 MC4 pairs, +25 m red and black
    cat2 = _with_500v(cat)
    rows = rows_for(10, 5, 1.134)
    before = generate_boq(BoqRequest("IAN-PNL-004", 10, rows, inverter_kw=6, battery_kwh=0, kind="net_metering"), seed, cfg)
    after = generate_boq(BoqRequest("IAN-PNL-004", 10, rows, inverter_kw=6, battery_kwh=0, kind="net_metering"), cat2, cfg)
    qb, qa = {l.role: l.qty for l in before.lines}, {l.role: l.qty for l in after.lines}
    assert before.choices["strings"] == 1 and after.choices["strings"] == 2 and after.choices["panels_per_string"] == 5
    assert qa["dc_breaker"] == qb["dc_breaker"] + 1 and qa["mc4_pair"] == qb["mc4_pair"] + 2 and qa["pv_cable_red"] == qb["pv_cable_red"] + 25 and qa["pv_cable_black"] == qb["pv_cable_black"] + 25
    assert after.choices["string_current_a"] == 15.48 and after.choices["string_voltage_v"] == pytest.approx(5 * 40.70) and after.choices["string_design"]["n_max"] == 9
    assert after.choices["string_design"]["available"] and after.choices["string_design"]["voc_cold_v"] == pytest.approx(50.51, abs=0.005)
    # the DC breaker by rating: the role item (16/25 A) is below the 25.28 A the string needs, so the 32 A one is used with the ordinary warning
    dc = _line(after, "dc_breaker")
    assert dc.code == "IAN-PRT-010" and "32 A" in dc.note and "datasheet" in dc.note
    w = next(x for x in after.warnings if x["code"] == "dc_breaker_rating")
    assert "25 A DC breaker IAN-PRT-009 is below the 25.28 A the string needs (1.25 × 1.25 × Isc 16.18 A)" in w["message"] and "IAN-PRT-010" in w["message"] and not w.get("hard")
    assert after.choices["dc_breaker"]["ocpd_a"] == 32 and after.choices["dc_breaker"]["role_rating_a"] == 25 and after.choices["dc_breaker"]["code"] == "IAN-PRT-010"
    assert _line(before, "dc_breaker").code == "IAN-PRT-009" and "dc_breaker_rating" not in {x["code"] for x in before.warnings}
    # the 585 W monofacial (Isc 13.53: 21.14 A) keeps the role item, which covers it
    est = generate_boq(BoqRequest("BC-PNL-001", 10, rows, inverter_kw=6, battery_kwh=0, kind="net_metering"), cat2, cfg)
    assert _line(est, "dc_breaker").code == "IAN-PRT-009" and est.choices["dc_breaker"]["ocpd_a"] == 25
    # the PV cable note says where the figure came from; the BOM carries the datasheet/rule words
    assert "Imp from the datasheet" in _line(after, "pv_cable_red").note and "the rule's current" in _line(before, "pv_cable_red").note
    # the forced ten on a 500 V input holds the documents through the job
    forced = generate_boq(BoqRequest("IAN-PNL-004", 10, rows, inverter_kw=6, battery_kwh=0, kind="net_metering", strings_override=1), cat2, cfg)
    assert any(x["code"] == "string_voltage_cold" and x["blocks_documents"] for x in forced.warnings) and forced.choices["panels_per_string"] == 10


def test_parallel_strings_per_mppt(catalogs):
    seed, cat, cfg = catalogs
    six = cat.get("OP-INV-018")        # "MPPT 18/18A"
    twelve = cat.get("OP-INV-017")     # "MPPT 18/36/36A"
    assert mppt_inputs(six) == [18, 18] and mppt_inputs(twelve) == [18, 36, 36] and mppt_inputs(seed.get("FS-INV-001")) == [18, 18] and mppt_inputs(seed.get("OP-INV-029")) == []
    # one string per input: 15.48 ≤ 18, fine
    per, w = mppt_assignment(six, 2, 9, 18, 15.48)
    assert w == [] and [p["strings"] for p in per] == [1, 1] and per[0]["amps_at_imp"] == 15.48
    # a 20-panel job at 9 per string is 3 strings on 2 inputs: one input takes 2 × 15.48 = 30.96 A > 18 A
    per, w = mppt_assignment(six, 3, 7, 20, 15.48)
    assert [p["strings"] for p in per] == [2, 1] and per[0]["amps_at_imp"] == pytest.approx(30.96) and per[0]["ok"] is False
    assert w[0]["code"] == "mppt_current" and "2 strings in parallel on MPPT 1 draw 30.96 A at Imp, above the input's 18 A" in w[0]["message"] and "verify the input's short-circuit rating" in w[0]["message"]
    assert "Unequal strings on one input mismatch at Vmp" in w[0]["message"]    # 20 panels over 3 strings: 7, 7, 6
    # the 12 kW unit: the extra string lands on a 36 A input, 30.96 ≤ 36, fine
    per, w = mppt_assignment(twelve, 4, 5, 20, 15.48)
    assert w == [] and [p["limit_a"] for p in per] == [36, 36, 18] and [p["strings"] for p in per] == [2, 1, 1]
    assert mppt_assignment(seed.get("OP-INV-029"), 3, 7, 20, 15.48) == ([], [])     # no MPPT data: nothing checked
    # in the BOQ: the block, the warning, and the DC SPD count from the Deye MPPT count the remarks never gave
    cat2 = _with_500v(cat, "OP-INV-018")
    res = generate_boq(BoqRequest("IAN-PNL-004", 20, rows_for(20, 10, 1.134), inverter_kw=6, battery_kwh=0, inverter_code="OP-INV-018", kind="net_metering"), cat2, cfg)
    assert res.choices["strings"] == 3 and [p["strings"] for p in res.choices["string_design"]["per_mppt"]] == [2, 1]
    assert any(x["code"] == "mppt_current" for x in res.warnings) and _line(res, "dc_spd").qty == 2


def test_the_quick_estimate_price_with_and_without_the_datasheets(catalogs, tmp_path):
    """The website estimate is untouched (brief 4.5): the same BOQ with the same catalogue. Its rounded price with the
    seed alone is pinned; with the fixture loaded the test states the figure it becomes (the battery choice moves to the
    15 kWh unit whose recommended rate covers the eco-hybrid's 139 A, the review's ranking)."""
    from solarapp.core.dataset import PvgisDataset
    from solarapp.core.quick import quick_estimate
    from solarapp.data_download.cli import write_synthetic
    from solarapp.pricing.job import PricingContext
    from solarapp.schemas import QuickRequest

    seed, cat, cfg = catalogs
    write_synthetic(tmp_path, (14.0, 14.5, 121.0, 121.5), 0.25)
    pvgis = PvgisDataset(tmp_path)
    req = QuickRequest(goal="combination", town="Pila", province="Laguna", monthly_kwh=338, pattern="evening")
    q0 = quick_estimate(req, pvgis, PricingContext(seed, cfg))
    q1 = quick_estimate(req, pvgis, PricingContext(cat, cfg))
    assert q0["price"]["total"] == QUICK_PRICE_SEED
    assert q1["price"]["total"] == QUICK_PRICE_WITH_DATASHEETS
    assert q0["system"]["panels"] == q1["system"]["panels"] and q0["system"]["inverter_kw"] == q1["system"]["inverter_kw"]
    assert "warnings" in q1 and not any("string" in w for w in q1["warnings"])    # no string table, no engineering warnings on the website
