"""Design rules from the engineering audit: the electrical data on items (contract C4), a grid-interactive
inverter per system kind (E1), the losses after the panels (E4, contract C2), the battery balanced over the
hourly year with days of autonomy (E5), the battery current check (E6), the sized panels on their faces (E10)
and what the customer documents print."""
import dataclasses
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, create_engine

from solarapp.config import Settings
from solarapp.core.sizing import BatterySpec, plan_from_faces, size_system
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.pricing.boq import BoqRequest, battery_current_check, generate_boq, rows_for, select_inverter
from solarapp.pricing.catalog import certifications_in_remarks, infer_grid_interactive
from solarapp.pricing.config import BoqRoles, PricingConfig
from solarapp.pricing.importer import electrical_columns, read_workbook
from solarapp.pricing.job import rows_from_layout
from solarapp.pricing.store import ensure_material_columns, load_catalog
from solarapp.reports.customer_pdf import build_customer_pdf
from solarapp.reports.quotation_pdf import battery_backup_line, inverter_certificate
from solarapp.schemas import AssessmentDoc, CandidatePanel, RoofFace
from tests.test_documents import LAGUNA_DOC
from tests.test_sizing import evening_load, synthetic_production_per_kwp

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


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


def _pdf_text(pdf: bytes) -> str:
    """The PDF's text in reading order with one space between words (the proposal's two columns interleave
    line by line in layout mode, which would split a phrase)."""
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext is not installed")
    return " ".join(subprocess.run(["pdftotext", "-", "-"], input=pdf, capture_output=True, check=True).stdout.decode().split())


# ---------------------------------------------------------------- C4: electrical data on the items
def test_importer_reads_electrical_data_and_infers_grid_interactive(imported):
    cat, cfg = imported.catalog, imported.config
    assert cat.get("FS-INV-001").grid_interactive is True and cat.get("FS-INV-001").certifications == "IEC 61727 / 62116"
    # the eco-hybrid may export (the owner confirmed the selling option with Felicity Solar); any hybrid counts as grid-interactive
    assert cat.get("FS-INV-008").grid_interactive is True and cat.get("FS-INV-008").certifications == ""
    assert cat.get("IAN-INV-025").grid_interactive is True     # a plain "HYBRID" may export; its certificate is still to be recorded
    assert cat.get("FS-INV-002").grid_interactive is None      # the remark says to CHECK the grid certification
    assert cat.get("BC-INV-006").grid_interactive is None      # "(on/off-grid)" is not a listing
    # figures the owner wrote into the remarks are a starting point for the string and current checks
    inv = cat.get("FS-INV-001")
    assert inv.battery_max_a == 135 and inv.mppt_count == 2 and inv.mppt_max_a == 18
    assert cat.get("FS-INV-005").max_pv_voltage_v == 500 and cat.get("BC-INV-007").battery_max_a == 220
    assert cat.get("FS-BAT-002").continuous_a == 120 and cat.get("BC-BAT-003").continuous_a == 100 and cat.get("FS-BAT-004").continuous_a == 250
    assert cat.get("BC-PNL-001").voc_v is None and cat.get("BC-PNL-001").isc_a is None   # no panel columns in the bundled workbook
    # the per-kind defaults: the first grid-interactive hybrid for net metering, the eco-hybrid off the grid
    assert cfg.roles.default_inverter_code_grid == "FS-INV-008" and cfg.roles.default_inverter_code_offgrid == "FS-INV-008"   # the owner's eco-hybrid, both kinds
    # optional columns are found by their header, in any column
    cols = electrical_columns(("Code", "Item", "Voc (V)", "Max PV voltage", "Grid-interactive", "Continuous current (A)", "MPPT count", "Temp coeff Voc (%/C)"))
    assert cols == {"voc_v": 2, "max_pv_voltage_v": 3, "grid_interactive": 4, "continuous_a": 5, "mppt_count": 6, "temp_coeff_voc_pct": 7}
    assert infer_grid_interactive("6 kW hybrid inverter (on/off-grid)") is None
    assert infer_grid_interactive("SOLIS S6-GR1P6K GRID-TIE 6kW") is True
    assert infer_grid_interactive("48V6000W HYBRID OFF-GRID 80A") is False
    assert infer_grid_interactive("8 kW hybrid (grid-tie + backup)", "CHECK: grid certifications in progress") is None
    assert certifications_in_remarks("2 MPPT; IEC 61727 / 62116 not listed") == ""
    assert certifications_in_remarks("UL 1741 and IEC 62116 listed") == "UL 1741; IEC 62116"


def test_old_single_default_inverter_migrates_to_the_off_grid_slot():
    roles = BoqRoles.model_validate({"default_inverter_code": "BC-INV-002"})
    assert roles.default_inverter_code_offgrid == "BC-INV-002" and roles.default_inverter_code_grid == "FS-INV-008"
    assert roles.default_inverter_for("off_grid") == "BC-INV-002" and roles.default_inverter_for("combination") == "FS-INV-008"
    cfg = PricingConfig.model_validate({"roles": {"default_inverter_code": ""}})
    assert cfg.roles.default_inverter_code_offgrid == "" and cfg.system_losses.factor == pytest.approx(0.96 * 0.98 * 0.97 * 0.99)
    assert cfg.sizing.days_of_autonomy == 1.0 and cfg.program.min_task_minutes == {"commissioning": 120, "battery": 60, "inverter": 60}


def test_store_adds_the_new_material_columns_to_an_older_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE material_items (code VARCHAR PRIMARY KEY, category VARCHAR, supplier VARCHAR, name VARCHAR, spec VARCHAR, unit VARCHAR, "
            "sold_as VARCHAR, list_price FLOAT, rating FLOAT, rating_unit VARCHAR, weight_kg FLOAT, volume_m3 FLOAT, weight_source VARCHAR, storage FLOAT, "
            "price_list_date VARCHAR, remarks VARCHAR, panel_length_m FLOAT, panel_width_m FLOAT, active BOOLEAN, updated_at DATETIME)"))
        conn.execute(text("INSERT INTO material_items (code, category, supplier, name, spec, unit, sold_as, list_price, rating_unit, weight_kg, volume_m3, weight_source, storage, price_list_date, remarks, active, updated_at) "
                          "VALUES ('X-INV-001', 'Inverter', 'S', 'old hybrid', '', 'pc', 'pc', 1, 'kW', 0, 0, '', 0, '', '', 1, '2026-01-01 00:00:00')"))
        conn.execute(text("CREATE TABLE material_suppliers (name VARCHAR PRIMARY KEY, pickup_address VARCHAR, dealer_discount FLOAT, payment_fee FLOAT, delivers_free BOOLEAN, price_list_date VARCHAR, prices_note VARCHAR, warranty VARCHAR, remarks VARCHAR)"))
    with Session(engine) as s:
        added = ensure_material_columns(s)
        assert {"grid_interactive", "certifications", "battery_max_a", "continuous_a", "voc_v", "temp_coeff_isc_pct"} <= set(added)
        assert ensure_material_columns(s) == []
        item = load_catalog(s).get("X-INV-001")
        assert item is not None and item.grid_interactive is None and item.certifications == "" and item.continuous_a is None


# ---------------------------------------------------------------- E1: a grid-interactive inverter on grid jobs
def test_grid_job_takes_a_grid_interactive_inverter_and_warns_on_an_off_grid_default(imported):
    cat, cfg = imported.catalog, imported.config
    for kind in ("net_metering", "combination"):
        opts = select_inverter(6, cat, cfg, kind)
        assert opts and all(i.grid_interactive is True for i, n, c in opts)
    assert any(i.grid_interactive is not True for i, n, c in select_inverter(6, cat, cfg, "off_grid"))
    # the configured grid default cannot export (marked so on the Materials page): skipped with a warning that names it
    cat2 = deepcopy(cat)
    cat2.get("FS-INV-008").grid_interactive = False
    cfg2 = cfg.model_copy(deep=True)
    cfg2.roles.default_inverter_code_grid = "FS-INV-008"
    res = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, kind="combination"), cat2, cfg2)
    inv = next(l for l in res.lines if l.role == "inverter")
    assert inv.code != "FS-INV-008" and cat2.get(inv.code).grid_interactive is True
    w = next(w for w in res.warnings if w["code"] == "default_inverter_not_grid")
    assert "FS-INV-008" in w["message"] and "off-grid type" in w["message"]
    assert all(o["grid_interactive"] is True for o in res.choices["inverter_options"])
    assert res.choices["inverter_grid_interactive"] is True   # the grid-tie model steps in; its certificate rides on its line
    # a per-job override whose flag is unknown: the hard warning about the certificate
    # a per-job override whose flag is unknown ("on/off-grid" in the name): an ordinary note to confirm the certificate
    res3 = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=0, inverter_code="BC-INV-006", kind="net_metering"), cat, cfg)
    w3 = next(w for w in res3.warnings if w["code"] == "inverter_certificate_unknown")
    assert not w3.get("hard") and "confirm its anti-islanding certificate" in w3["message"]
    assert "grid-interactive: unknown" in next(l for l in res3.lines if l.role == "inverter").note
    # a per-job override the owner marked as unable to export, on a grid job: the hard warning that the DU will not accept it
    res4 = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, inverter_code="FS-INV-008", kind="combination"), cat2, cfg)
    w4 = next(w for w in res4.warnings if w["code"] == "inverter_not_grid_interactive")
    assert w4.get("hard") and "cannot export" in w4["message"]
    # off the grid none of this applies: the eco-hybrid default, no grid warnings
    res5 = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, kind="off_grid"), cat, cfg)
    assert next(l for l in res5.lines if l.role == "inverter").code == "FS-INV-008"
    assert not {w["code"] for w in res5.warnings} & {"default_inverter_not_grid", "inverter_certificate_unknown", "inverter_not_grid_interactive"}
    # no grid-interactive unit big enough: a plain message, not a silent off-grid pick
    cfg3 = cfg.model_copy(deep=True)
    cfg3.roles.default_inverter_code_grid = ""
    res6 = generate_boq(BoqRequest("BC-PNL-001", 40, rows_for(40, 10, 1.134), inverter_kw=12, inverter_required_kw=30, battery_kwh=0, kind="net_metering"), cat, cfg3)
    inv6 = next((l for l in res6.lines if l.role == "inverter"), None)
    assert inv6 is None or cat.get(inv6.code).grid_interactive is True


# ---------------------------------------------------------------- E6: the battery against the inverter's current
def test_battery_current_and_breaker_checks(imported):
    cat, cfg = imported.catalog, imported.config
    bat, inv = cat.get("FS-BAT-002"), cat.get("FS-INV-001")        # 120 A continuous against 135 A maximum, 117 A rated
    units, w = battery_current_check(bat, 1, inv, 1, 117.2, 135.0)
    assert units == 1 and [x["code"] for x in w] == ["battery_current"] and "117 A" in w[0]["message"]
    weak = dataclasses.replace(bat, continuous_a=50.0)
    units, w = battery_current_check(weak, 1, inv, 1, 117.2, 135.0)
    assert units == 1 and w[0]["code"] == "battery_current_units" and "3 units in parallel" in w[0]["message"]   # ceil(117.2 / 50): the owner's call, not an automatic doubling
    units, w = battery_current_check(weak, 3, inv, 1, 117.2, 135.0)
    assert w == []                                                     # 150 A over three units covers the inverter's maximum
    unknown = dataclasses.replace(bat, continuous_a=None)
    assert battery_current_check(unknown, 1, inv, 1, 117.2, 135.0)[1][0]["code"] == "battery_current_unknown"
    assert battery_current_check(unknown, 1, dataclasses.replace(inv, battery_max_a=None), 1, 117.2, 117.2)[1] == []
    # in the BOQ: the breaker sits at or above 1.25 x the inverter's battery current and the battery's rating bounds it
    res = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, battery_code="FS-BAT-002", kind="combination"), cat, cfg)
    bb = next(l for l in res.lines if l.role == "battery_breaker")
    assert res.choices["battery_current_a"] == 135 and res.choices["battery_breaker_min_a"] == pytest.approx(168.75)
    assert cat.get(bb.code).amps_in_name() >= 168.75 and "1.25 × 135 A" in bb.note and "battery rated 120 A" in bb.note
    assert {w["code"] for w in res.warnings} >= {"battery_current", "battery_breaker"}
    assert "35 mm2" in next(l for l in res.lines if l.role == "battery_cable").note
    big = generate_boq(BoqRequest("BC-PNL-001", 6, rows_for(6, 6, 1.134), inverter_kw=6, battery_kwh=10, battery_code="FS-BAT-004", kind="combination"), cat, cfg)
    assert not {w["code"] for w in big.warnings} & {"battery_current", "battery_current_units", "battery_breaker"}   # 250 A continuous: the window holds
    bb2 = next(l for l in big.lines if l.role == "battery_breaker")
    assert 168.75 <= cat.get(bb2.code).amps_in_name() <= 250


# ---------------------------------------------------------------- E4: losses after the panels
def test_losses_reduce_the_meter_figure_and_grow_the_array():
    cfg = PricingConfig()
    f = cfg.system_losses.factor
    assert f == pytest.approx(0.96 * 0.98 * 0.97 * 0.99) and 0.90 < f < 0.91
    load = evening_load(10.0)   # 3,650 kWh a year: 2.61 kWp at the panels (5 panels), 2.89 kWp at the meter (6 panels)
    per_kwp = synthetic_production_per_kwp()
    dc = size_system(load, per_kwp, 40, 550, "net_metering", 4.0, 1.5, 3.0)
    ac = size_system(load, per_kwp * f, 40, 550, "net_metering", 4.0, 1.5, 3.0)
    assert ac["annual_yield_kwh_per_kwp"] == pytest.approx(dc["annual_yield_kwh_per_kwp"] * f)
    assert ac["target_kwp"] == pytest.approx(dc["target_kwp"] / f)
    assert (dc["panels"], ac["panels"]) == (5, 6)
    same = size_system(load, per_kwp * f, dc["panels"], 550, "net_metering", 4.0, 1.5, 3.0)
    assert same["annual_production_kwh"] == pytest.approx(dc["annual_production_kwh"] * f)
    assert same["annual_production_kwh"] < same["annual_consumption_kwh"] <= ac["annual_production_kwh"]   # the panels' figure covered the year, the meter's does not


# ---------------------------------------------------------------- E5 and E10: the hourly year on the faces the panels occupy
def _year_plan(per_kwp: np.ndarray, dark_days=(), loss: float = 1.0, capacity: int = 12, panel_kw: float = 0.55):
    """Two faces that hold `capacity` panels each: B makes 85% of A. The hourly year repeats the typical day of
    each month, with the listed days of the year dimmed to 15% (a rainy spell)."""
    months = np.concatenate([np.full(d * 24, m + 1) for m, d in enumerate(DAYS)])
    hours = np.tile(np.arange(24), 365)
    dim = np.ones(365)
    dim[list(dark_days)] = 0.15
    year_a = per_kwp[months - 1, hours] * dim[np.arange(365 * 24) // 24] * panel_kw
    faces = []
    for fid, share, yld in (("B", 0.85, 1200.0), ("A", 1.0, 1400.0)):   # B listed first: the order must not matter
        faces.append({"face_id": fid, "name": f"Face {fid}", "panel_count": capacity, "hourly_profile_kw": per_kwp * panel_kw * share * capacity,
                      "specific_yield_kwh_per_kwp": yld * share, "rows": [capacity // 2, capacity // 2], "hourly_kw": year_a * share * capacity})
    return plan_from_faces(faces, loss, months, hours)


def test_hourly_year_balance_reports_loss_of_load_and_autonomy_changes_the_battery():
    load = evening_load(11.0)
    per_kwp = synthetic_production_per_kwp()
    rainy = _year_plan(per_kwp, dark_days=range(200, 205))    # five dark days in a row
    og = size_system(load, per_kwp, 6, 550, "off_grid", 4.0, 1.5, 3.0, battery=BatterySpec(days_of_autonomy=1.0), plan=rainy)
    hy = og["hourly_year"]
    # the grid steps in during the dark spell: no export, but nothing goes unserved and the roof is not filled to chase it
    assert hy["available"] and hy["hours"] == 8760 and hy["meaning"] == "grid_covered"
    assert hy["loss_of_load_hours"] > 0 and hy["loss_of_load_days"] >= 3 and hy["unserved_kwh"] > 0 and hy["worst_month"] == 7
    assert og["annual_unserved_kwh"] == 0 and og["annual_export_kwh"] == 0 and og["annual_import_kwh"] > 0
    assert not any(w["code"] == "autonomy_not_met" for w in og["warnings"])
    assert og["battery"]["days_of_autonomy"] == 1.0
    # two evenings of autonomy: twice the battery, fewer hours without power
    og2 = size_system(load, per_kwp, 6, 550, "off_grid", 4.0, 1.5, 3.0, battery=BatterySpec(days_of_autonomy=2.0), plan=rainy)
    assert og2["battery"]["usable_kwh"] == pytest.approx(2 * og["battery"]["usable_kwh"]) and og2["battery"]["days_of_autonomy"] == 2.0
    assert og2["hourly_year"]["loss_of_load_hours"] < hy["loss_of_load_hours"]
    # a year without a dark spell closes: the loop adds panels over the real year until nothing is unserved
    clear = _year_plan(per_kwp)
    og3 = size_system(load, per_kwp, 24, 550, "off_grid", 4.0, 1.5, 3.0, plan=clear)
    assert og3["hourly_year"]["loss_of_load_hours"] == 0 and og3["annual_unserved_kwh"] == 0 and not og3["roof_limited"]
    assert not any(w["code"] == "autonomy_not_met" for w in og3["warnings"])
    # hybrid: the grid steps in, and every hour of the year balances
    combo = size_system(load, per_kwp, 24, 550, "combination", 4.0, 1.5, 3.0, plan=rainy)
    chy = combo["hourly_year"]
    assert chy["meaning"] == "grid_covered" and chy["loss_of_load_hours"] > 0 and combo["annual_import_kwh"] > 0
    for m in combo["monthly"]:
        assert m["direct_kwh"] + m["battery_kwh"] + m["import_kwh"] == pytest.approx(m["consumption_kwh"], rel=1e-6)
        assert m["consumption_kwh"] == pytest.approx(11.0 * m["days"], rel=1e-6)
    assert sum(len(p["load"]) for p in combo["profiles"].values()) == 12 * 24
    # a net-metering job runs the year too (no battery), with month totals from it
    nm = size_system(load, per_kwp, 24, 550, "net_metering", 4.0, 1.5, 3.0, plan=clear)
    assert nm["hourly_year"]["available"] and nm["battery"]["usable_kwh"] == 0 and nm["battery"]["days_of_autonomy"] is None
    assert nm["annual_production_kwh"] == pytest.approx(sum(m["production_kwh"] for m in nm["monthly"]))


def test_sized_panels_go_to_the_best_face_first_and_the_rows_follow():
    load = evening_load(11.0)
    per_kwp = synthetic_production_per_kwp()
    f = 0.9035
    plan = _year_plan(per_kwp, loss=f)
    nm = size_system(load, per_kwp * 0.925 * f, 24, 550, "net_metering", 4.0, 1.5, 3.0, plan=plan)
    faces = nm["faces"]
    assert faces[0]["face_id"] == "A" and faces[0]["panels"] == min(nm["panels"], 12)   # best face first, whatever the document order
    assert nm["loss_factor"] == f and nm["annual_production_dc_kwh"] == pytest.approx(nm["annual_production_kwh"] / f)
    assert nm["annual_production_kwh"] == pytest.approx(sum(x["annual_kwh"] for x in faces))
    assert faces[0]["rows"][0] == 6 and sum(faces[0]["rows"]) == faces[0]["panels"]
    # the production profile is the sum over the allocated panels, not the whole-roof blend: with every panel on A
    # the yield per kWp is A's, above the blend; the target is the smallest count whose own production covers the year
    if nm["panels"] <= 12:
        assert nm["annual_production_kwh"] / nm["kwp"] == pytest.approx(sum(per_kwp.sum(axis=1) * np.array(DAYS)) * f, rel=1e-3)
    assert nm["annual_production_kwh"] >= nm["annual_consumption_kwh"] and nm["panels"] == nm["target_panels"]
    fewer = size_system(load, per_kwp * 0.925 * f, 24, 550, "net_metering", 4.0, 1.5, 3.0, plan=plan)
    assert fewer["panels"] == nm["panels"]
    # the priced rows follow the allocation, not the document order
    doc = AssessmentDoc(faces=[RoofFace(id="B", name="Face B", length_m=10, width_m=5, tilt_deg=15, azimuth_deg=0), RoofFace(id="A", name="Face A", length_m=10, width_m=5, tilt_deg=15, azimuth_deg=180)])
    selected = {"faces": {fid: {"best": {"rows": [6, 6], "orientation": "landscape"}} for fid in ("A", "B")}}
    panel = CandidatePanel(id="p", name="p", watt_peak=550, length_m=2.278, width_m=1.134)
    rows = rows_from_layout(doc, panel, selected, 8, 0.0, [{"face_id": "A", "panels": 8}])
    assert [r.panels for r in rows] == [6, 2] and rows[0].panel_dim_along_row_m == 2.278
    rows_split = rows_from_layout(doc, panel, selected, 14, 0.0, [{"face_id": "A", "panels": 12}, {"face_id": "B", "panels": 2}])
    assert [r.panels for r in rows_split] == [6, 6, 2]
    assert [r.panels for r in rows_from_layout(doc, panel, selected, 8, 0.0)] == [6, 2]   # without the allocation: document order, same rows here


# ---------------------------------------------------------------- end to end: results and documents
def test_results_carry_the_meter_figures_faces_and_the_hourly_year(client):
    doc = deepcopy(LAGUNA_DOC)
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    prod, sizing, pr, eco = res["production"], res["sizing"], res["pricing"], res["economics"]
    f = PricingConfig().system_losses.factor
    assert prod["loss_factor"] == pytest.approx(f) and prod["annual_kwh_ac"] == pytest.approx(prod["annual_kwh"] * f)
    assert len(prod["monthly_kwh_ac"]) == 12 and prod["faces"][0]["annual_kwh_ac"] == pytest.approx(prod["faces"][0]["annual_kwh"] * f)
    assert "hourly_kw" not in prod and "hourly_kw" not in prod["faces"][0]
    assert sizing["loss_factor"] == pytest.approx(f) and sizing["annual_yield_kwh_per_kwp"] < prod["annual_kwh"] / prod["system_kwp"]
    assert sizing["hourly_year"]["available"] and sizing["hourly_year"]["hours"] == 8760 and sizing["hourly_year"]["meaning"] == "grid_covered"
    assert sizing["battery"]["days_of_autonomy"] == 1.0 and sizing["battery"]["usable_kwh"] > 0
    faces = sizing["faces"]
    assert faces and faces[0]["panels"] >= 1 and sum(x["panels"] for x in faces) == sizing["panels"]
    yields = [x["specific_yield_kwh_per_kwp"] for x in faces]
    assert yields == sorted(yields, reverse=True)   # best face first
    assert sizing["annual_production_kwh"] == pytest.approx(sum(x["annual_kwh"] for x in faces), rel=1e-6)
    assert eco["assumptions"]["loss_factor"] == pytest.approx(f) and eco["year1"]["production_kwh"] == pytest.approx(sizing["annual_production_kwh"])
    # the priced inverter is grid-interactive, with its certificate on the line; the rows follow the allocation
    inv = next(l for l in pr["lines"] if l["role"] == "inverter")
    assert inv["grid_interactive"] is True and inv["code"] == "FS-INV-008"   # the owner's eco-hybrid; certificate to be recorded
    assert sum(x["panels"] for x in pr["choices"]["rows"]) == sizing["panels"]
    assert not any(w["code"] in ("inverter_not_grid_interactive", "inverter_certificate_unknown") for w in pr["warnings"])
    # the proposal: the meter figure and the one honest battery line (the eco-hybrid's certificate is not recorded yet)
    from tests.conftest import real_weather
    real_weather(aid)
    pdf = client.get(f"/api/assessments/{aid}/quotation.pdf")
    assert pdf.status_code == 200
    text_ = _pdf_text(pdf.content)
    assert "kWh a year at your meter" in text_ and "Inverter certificate" not in text_   # the eco-hybrid's certificate is not recorded yet
    assert "Designed to carry 1 evening without sun; in the rainy season the grid covers the rest." in " ".join(text_.split())
    assert inverter_certificate(pr) == ""
    # the roof check prints the meter figures (built directly: the API refuses customer PDFs on test weather)
    roof = _pdf_text(build_customer_pdf(AssessmentDoc.model_validate(r.json()["doc"]), res, {"company_name": "Test"}))
    assert f"about {prod['annual_kwh_ac']:,.0f} kWh at your meter" in roof and "at your meter" in roof
    assert "lost in the inverter, the cables and dust on the panels" in " ".join(roof.split())


def test_off_grid_results_and_proposal_say_how_often_the_battery_runs_out(client):
    doc = deepcopy(LAGUNA_DOC)
    doc["audit"]["system"] = {"kind": "off_grid"}
    aid = client.post("/api/assessments", json=doc).json()["id"]
    r = client.post(f"/api/assessments/{aid}/compute")
    assert r.status_code == 200, r.text
    res = r.json()["results"]
    sizing, pr = res["sizing"], res["pricing"]
    hy = sizing["hourly_year"]
    assert hy["available"] and hy["meaning"] == "grid_covered" and sizing["annual_unserved_kwh"] == 0 and sizing["annual_export_kwh"] == 0
    assert sizing["annual_import_kwh"] == pytest.approx(hy["unserved_kwh"]) if hy["loss_of_load_hours"] else sizing["annual_import_kwh"] == 0
    assert next(l for l in pr["lines"] if l["role"] == "inverter")["code"] == "FS-INV-008"
    line = battery_backup_line(sizing)
    assert line.startswith("Designed to carry 1 evening without sun; the grid steps in only when the panels and the battery fall short, and nothing is sent back to it.")
    if hy["loss_of_load_hours"] > 0:
        assert f"about {hy['loss_of_load_hours']} hours on" in line
    else:
        assert "does not run out" in line
    from tests.conftest import real_weather
    real_weather(aid)
    text_ = " ".join(_pdf_text(client.get(f"/api/assessments/{aid}/quotation.pdf").content).split())
    assert "Designed to carry 1 evening without sun; the grid steps in only when" in text_ and "Inverter certificate" not in text_


def test_quick_estimate_applies_the_losses_and_the_inverter_rule(imported, tmp_path):
    """The website figure is at the meter too, so it and the later proposal agree; its inverter follows the same rule."""
    from solarapp.core.dataset import PvgisDataset
    from solarapp.core.quick import quick_estimate
    from solarapp.pricing.job import PricingContext
    from solarapp.schemas import QuickRequest
    write_synthetic(tmp_path, (14.0, 14.5, 121.0, 121.5), 0.25)
    ctx = PricingContext(imported.catalog, imported.config)
    q = quick_estimate(QuickRequest(goal="net_metering", town="Pila", province="Laguna", monthly_kwh=338, pattern="balanced"), PvgisDataset(tmp_path), ctx)
    f = imported.config.system_losses.factor
    assert q["production"]["loss_factor"] == pytest.approx(f)
    assert q["production"]["annual_kwh"] == pytest.approx(q["production"]["annual_kwh_at_panels"] * f)
    assert any("what reaches your meter" in a for a in q["assumptions"])
    # the same request without the losses would price a smaller array or the same one, never a bigger one
    cfg0 = imported.config.model_copy(deep=True)
    cfg0.system_losses.inverter = cfg0.system_losses.wiring = cfg0.system_losses.soiling = cfg0.system_losses.other = 1.0
    q0 = quick_estimate(QuickRequest(goal="net_metering", town="Pila", province="Laguna", monthly_kwh=338, pattern="balanced"), PvgisDataset(tmp_path), PricingContext(imported.catalog, cfg0))
    assert q0["system"]["panels"] <= q["system"]["panels"] and q0["production"]["loss_factor"] == 1.0


def test_grid_flag_reads_the_name_first_and_the_owner_confirmed_the_eco_hybrid():
    """The owner confirmed with Felicity Solar that the eco-hybrid can sell to the grid: a hybrid is grid-interactive
    whatever the remark calls its type, unless the name says off-grid or the remark says it cannot export."""
    assert infer_grid_interactive("6 kW low-voltage eco-hybrid inverter", "Off-grid high-frequency type, 2 MPPT 20A each") is True
    assert infer_grid_interactive("48V6000W HYBRID OFF-GRID 80A") is False
    assert infer_grid_interactive("8 kW hybrid inverter (on/off-grid)") is None
    assert infer_grid_interactive("6 kW hybrid inverter", "cannot export; island mode only") is False
    assert infer_grid_interactive("Off-grid inverter 5 kW") is False
    assert infer_grid_interactive("6 kW inverter", "grid-tie listed") is True
