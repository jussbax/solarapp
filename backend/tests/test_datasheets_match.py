"""Round 12, the datasheet importer against the seed workbook's catalogue: the three tiers of matching (brief 2.2),
the precedence of 2.4 (the owner's edit > the datasheet > the workbook column > the remark), the re-apply after a
materials import (2.6), the manual link, the re-run as a no-op, the dry run's report and the owner-only routes."""
import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from solarapp import models
from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.models import DatasheetSpec, MaterialItem
from solarapp.pricing.catalog import Item
from solarapp.pricing.datasheets import add_item_from_spec, import_datasheets, link_spec, match_rows, note_overrides, read_datasheet_workbook, reapply_datasheets
from solarapp.pricing.importer import read_workbook
from solarapp.pricing.store import import_workbook, load_catalog, load_config

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "datasheets"
FILES = [FIXTURES / f"ALL_{n}_DATA_SHEET.xlsx" for n in ("SOLAR_PANEL", "INVERTER", "BATTERY")]
# the items the brief says find no row (2.2); they keep today's remark inference and the "unknown" warnings
UNMATCHED = {"FS-INV-001", "FS-INV-003", "FS-INV-004", "FS-INV-007", "IAN-INV-035", "BC-INV-002", "BC-INV-003", "BC-INV-005", "BC-INV-006", "BC-INV-007", "BC-INV-008",
             "BC-BAT-003", "BC-BAT-004", "FS-BAT-006", "FS-BAT-008", "FS-BAT-009", "IAN-BAT-002", "IAN-BAT-004", "IAN-BAT-006", "OP-BAT-003", "OP-INV-001", "OP-INV-002", "OP-INV-003"}


def _engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'ds.db'}")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="module")
def seeded(tmp_path_factory):
    """The seed catalogue with the three fixture workbooks imported once; read-only in the tests that share it."""
    engine = _engine(tmp_path_factory.mktemp("ds"))
    with Session(engine) as s:
        import_workbook(s, WB)
        report = import_datasheets(s, FILES)
    return engine, report


def _as_item(row: MaterialItem) -> Item:
    """The catalogue's view of a stored item (the flags such as is_hybrid_inverter live on the Item dataclass)."""
    return Item(**{k: v for k, v in row.model_dump().items() if k != "updated_at"})


def _by_file(session: Session, prefix: str) -> dict[tuple[str, int], DatasheetSpec]:
    return {(r.source_sheet, r.source_row): r for r in session.exec(select(DatasheetSpec)).all() if r.source_file.startswith(prefix)}


def test_the_report_counts_and_the_three_tiers(seeded):
    engine, report = seeded
    assert report.counts == {"rows": 189, "matched": 92, "specs_only": 90, "skipped": 7, "held": 6, "items_changed": 92, "items_untouched": 0}
    assert report.projects_using_changed == [] and not report.dry_run
    with Session(engine) as s:
        inv, bat, pnl = _by_file(s, "ALL_INVERTER"), _by_file(s, "ALL_BATTERY"), _by_file(s, "ALL_SOLAR")
        # exact: a verbatim name (the Deye and Solis rows, the One Solar off-grid rows, the Solar Homes panels)
        assert inv[("Sheet1", 9)].matched_code == "OP-INV-017" and inv[("Sheet1", 9)].match_tier == "exact"
        assert inv[("Sheet2", 12)].matched_code == "IAN-INV-022" and inv[("Sheet3", 13)].matched_code == "OP-INV-029" and pnl[("Sheet1", 4)].matched_code == "OP-PNL-003"
        assert inv[("Sheet2", 4)].matched_code == "IAN-AIO-001" and inv[("Sheet2", 4)].category == "All-in-one System"
        # the maker-word strip on the seven panel rows: each finds the dealer's item for the maker's module (6.1)
        assert {pnl[("Sheet1", r)].matched_code for r in range(7, 14)} == {"IAN-PNL-003", "IAN-PNL-004", "IAN-PNL-001", "OP-PNL-004", "OP-PNL-005", "OP-PNL-006", "IAN-PNL-002"}
        assert pnl[("Sheet1", 8)].matched_code == "IAN-PNL-004" and pnl[("Sheet1", 11)].matched_code == "OP-PNL-005" and pnl[("Sheet1", 12)].matched_code == "OP-PNL-006"
        assert pnl[("Sheet1", 14)].matched_code == "BC-PNL-001" and pnl[("Sheet1", 17)].matched_code == "BC-PNL-004"
        # the longer of two exact rows wins: FS-BAT-003 and -004 take the TG2 variants (160 A and 250 A, as their remarks say)
        assert bat[("Sheet2", 8)].matched_code == "FS-BAT-003" and bat[("Sheet2", 23)].matched_code is None and "takes the longer 'FLA48300TG2'" in bat[("Sheet2", 23)].match_note
        assert bat[("Sheet2", 10)].matched_code == "FS-BAT-004" and bat[("Sheet2", 28)].matched_code is None
        assert s.get(MaterialItem, "FS-BAT-003").continuous_a == 160 and s.get(MaterialItem, "FS-BAT-004").continuous_a == 250
        # contains: the Felicity 6 and 8 kW off-grid rows against the items whose specs add a generation suffix, with the notice
        assert inv[("Sheet5", 7)].matched_code == "FS-INV-005" and inv[("Sheet5", 7)].match_tier == "contains" and "carries a suffix the sheet row lacks" in inv[("Sheet5", 7)].match_note
        assert inv[("Sheet5", 8)].matched_code == "FS-INV-006" and inv[("Sheet5", 8)].match_tier == "contains"
        # ambiguity: the Blue Carbon base 6.5 kW row names both codes; FS-BAT-006's two market variants name the item
        assert inv[("Sheet4", 6)].matched_code is None and inv[("Sheet4", 6)].match_note == "ambiguous: BC-INV-004, BC-INV-005"
        assert bat[("Sheet2", 12)].matched_code is None and bat[("Sheet2", 29)].matched_code is None and "FS-BAT-006 is the base of 2 sheet rows" in bat[("Sheet2", 12)].match_note
        # the token-start rule: the plain 48 V 100 Ah row does not take the smart item; the row with the trailing letter does, by the base tier
        assert bat[("Sheet1", 18)].matched_code is None and bat[("Sheet1", 27)].matched_code == "BC-BAT-002" and bat[("Sheet1", 27)].match_tier == "base"
        assert bat[("Sheet2", 11)].matched_code == "FS-BAT-005" and bat[("Sheet2", 13)].matched_code == "FS-BAT-007" and bat[("Sheet2", 11)].match_tier == "base"
        # no match: the generation differs, the letters are in the other order, the series letter, the HV modules
        assert inv[("Sheet5", 13)].matched_code is None and inv[("Sheet4", 8)].matched_code is None and bat[("Sheet1", 24)].matched_code is None and bat[("Sheet2", 14)].matched_code is None
        matched = {r.matched_code for r in s.exec(select(DatasheetSpec)).all() if r.matched_code}
        assert not (matched & UNMATCHED)
        # one item for three sheet rows (6.7): three specs-only rows naming OP-INV-001
        for r in (4, 5, 6):
            assert inv[("Sheet3", r)].matched_code is None and "one item (OP-INV-001) stands for 3 sheet rows" in inv[("Sheet3", r)].match_note
        # the orphan rows are not stored at all; the held rows are; two models that normalise alike (1.2 kW and 12 kW) stay two rows
        assert ("Sheet2", 33) not in inv and inv[("Sheet2", 5)].held and inv[("Sheet2", 5)].matched_code == "IAN-INV-001"
        assert inv[("Sheet4", 4)].model == "BCT-FXC-1.2KW" and inv[("Sheet4", 9)].model == "BCT-FXC-12KW" and inv[("Sheet4", 4)].model_norm == inv[("Sheet4", 9)].model_norm
        assert len([r for r in s.exec(select(DatasheetSpec)).all()]) == 189 - 7


def test_the_figures_on_the_items_and_the_precedence(seeded):
    engine, report = seeded
    with Session(engine) as s:
        eco = s.get(MaterialItem, "FS-INV-008")
        # the eco-hybrid: the sheet's 139 A over the remark's 135, the new fields filled, the owner's grid flag kept with the conflict reported
        assert eco.battery_max_a == 139 and eco.charge_a_max == 135 and eco.charge_v_max == 58.4 and eco.inverter_type == "off_grid" and eco.phase == 1 and eco.battery_class == "LV"
        assert eco.grid_interactive is True
        line = next(l for l in report.lines if l.code == "FS-INV-008")
        assert line.status == "matched" and line.tier == "exact" and "battery_max_a 135 -> 139" in line.changes and "charge_v_max - -> 58.4" in line.changes
        assert any("grid_interactive kept (item yes, sheet off-grid)" in n for n in line.notices)
        # the Deye 1P hybrids carry the MPPT data the remarks never gave
        deye = s.get(MaterialItem, "OP-INV-017")
        assert deye.mppt_count == 3 and deye.mppt_max_a == 18 and deye.mppt_currents_a == "18/36/36" and _as_item(deye).is_hybrid_inverter
        # a grid-tie unit is no hybrid once the type is on file; a charge controller neither; the wall-type units enter the off-grid pool (6.9)
        assert s.get(MaterialItem, "OP-INV-004").inverter_type == "grid_tie" and not _as_item(s.get(MaterialItem, "OP-INV-004")).is_hybrid_inverter
        wall = s.get(MaterialItem, "OP-INV-029")
        assert wall.inverter_type == "off_grid" and wall.grid_interactive is False and _as_item(wall).is_hybrid_inverter
        # batteries: the sheet's maximum is the continuous rating; the 21 items with none today take it
        assert s.get(MaterialItem, "BC-BAT-001").continuous_a == 100 and s.get(MaterialItem, "OP-BAT-004").continuous_a == 200 and s.get(MaterialItem, "IAN-BAT-008").nominal_v == 51.2
        bat = s.get(MaterialItem, "FS-BAT-002")
        assert bat.continuous_a == 150 and bat.discharge_a_recommended == 100 and bat.charge_a_max == 40 and bat.charge_v_max == 57.6 and bat.capacity_ah == 200
        # the rating fills only when blank: FS-BAT-002 keeps 10 kWh with the 10.24 notice; the differences the brief lists are reported
        assert bat.rating == 10
        notes = {l.code: " ".join(l.notices) for l in report.lines if l.code}
        assert "the item's rating is 10 kWh and the sheet says 10.24 kWh; the item's rating stands" in notes["FS-BAT-002"]
        assert "15 kWh and the sheet says 15.36 kWh" in notes["FS-BAT-003"] and "25 kWh and the sheet says 25.6 kWh" in notes["FS-BAT-004"]
        assert "rating" not in notes["BC-PNL-001"]                     # all 14 panel rows agree with their items
        # held: the Felicity 100 Ah base row's 150 A is not applied (1.3); the Solis grid-tie rows keep no battery figures
        assert s.get(MaterialItem, "FS-BAT-001").continuous_a == 100
        solis = s.get(MaterialItem, "IAN-INV-001")
        assert solis.inverter_type == "grid_tie" and solis.phase == 1 and solis.battery_max_a is None and solis.charge_v_max is None and solis.battery_class == ""
        assert next(l for l in report.lines if l.code == "IAN-INV-001").status == "held"
        # the stamp on the pricing config, never a price
        cfg = load_config(s)
        assert cfg.datasheets_imported_at and "ALL_INVERTER_DATA_SHEET.xlsx" in cfg.datasheets_imported_from
        # the catalogue the engine reads carries the fields
        cat = load_catalog(s)
        assert cat.get("BC-PNL-001").voc_v == 53.08 and cat.get("BC-PNL-001").max_system_voltage_v == 1500 and cat.get("BC-PNL-001").isc_a == 13.53


def test_a_rerun_is_a_no_op_and_a_materials_reimport_keeps_the_datasheet_figures(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        import_workbook(s, WB)
        first = import_datasheets(s, FILES)
        assert first.counts["items_changed"] == 92
        second = import_datasheets(s, FILES)
        assert second.counts["items_changed"] == 0 and second.counts["items_untouched"] == 92 and second.counts["matched"] == 92
        assert all(l.changes == [] for l in second.lines if l.status in ("matched", "held"))
        # the materials workbook re-import writes the remark's 135 A back; the re-apply at the end restores the sheet's 139 A (2.4, 2.6)
        r = import_workbook(s, WB, replace_config=False)
        assert r["updated"] == 362 and r["datasheets"]["matched"] == 92
        eco = s.get(MaterialItem, "FS-INV-008")
        assert eco.battery_max_a == 139 and eco.charge_a_max == 135 and eco.inverter_type == "off_grid"
        assert s.get(MaterialItem, "OP-INV-017").mppt_count == 3 and s.get(MaterialItem, "BC-BAT-001").continuous_a == 100
        # the stamps survive a workbook import that replaces the settings
        import_workbook(s, WB, replace_config=True)
        assert load_config(s).datasheets_imported_at and s.get(MaterialItem, "FS-INV-008").battery_max_a == 139


def test_an_override_survives_a_rerun_and_resetting_to_the_datasheet_lifts_it(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        import_workbook(s, WB)
        import_datasheets(s, FILES)
        eco = s.get(MaterialItem, "FS-INV-008")
        eco.battery_max_a = 150                      # the owner types over the datasheet's 139 A on the Materials page
        s.add(eco)
        s.commit()
        note_overrides(s, "FS-INV-008", {"battery_max_a": 150, "name": eco.name})
        spec = s.exec(select(DatasheetSpec).where(DatasheetSpec.matched_code == "FS-INV-008")).one()
        assert spec.overridden_fields == ["battery_max_a"]
        import_datasheets(s, FILES)
        assert s.get(MaterialItem, "FS-INV-008").battery_max_a == 150
        # "reset to datasheet": typing the sheet's own figure takes the field off the list
        eco = s.get(MaterialItem, "FS-INV-008")
        eco.battery_max_a = 139
        s.add(eco)
        s.commit()
        note_overrides(s, "FS-INV-008", {"battery_max_a": 139})
        assert s.exec(select(DatasheetSpec).where(DatasheetSpec.matched_code == "FS-INV-008")).one().overridden_fields == []


def test_a_blank_rating_is_filled_and_the_held_figures_apply_only_on_the_owners_word(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        import_workbook(s, WB)
        panel = s.get(MaterialItem, "IAN-PNL-004")
        panel.rating = None
        s.add(panel)
        s.commit()
        report = import_datasheets(s, FILES, apply_held=True)
        assert s.get(MaterialItem, "IAN-PNL-004").rating == 630 and s.get(MaterialItem, "IAN-PNL-004").rating_unit == "W"
        assert "rating - -> 630 W" in next(l for l in report.lines if l.code == "IAN-PNL-004").changes
        # with --apply-held the Solis grid-tie rows' battery figures and the 150 A go on
        assert report.counts["held"] == 0
        solis = s.get(MaterialItem, "IAN-INV-001")
        assert solis.battery_max_a == 135 and solis.charge_a_max == 135 and solis.charge_v_max == 60 and solis.battery_class == ""   # the class is not on the row (1.2)
        assert s.get(MaterialItem, "FS-BAT-001").continuous_a == 150


def test_the_dry_run_writes_the_report_and_nothing_else(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        import_workbook(s, WB)
        report = import_datasheets(s, FILES, dry_run=True)
        assert report.dry_run and report.counts["matched"] == 92 and report.counts["held"] == 6
        out = tmp_path / "report.csv"
        report.write_csv(out)
        rows = list(csv.reader(out.open(encoding="utf-8")))
        assert rows[0] == ["status", "code", "where", "category", "brand", "model", "tier", "changes", "notices", "note"]
        statuses = {r[0] for r in rows[1:] if r}
        assert {"matched", "held", "specs-only", "skipped", "summary"} <= statuses
        held = [r for r in rows[1:] if r and r[0] == "held"]
        assert len(held) == 6 and {r[1] for r in held} == {"IAN-INV-001", "IAN-INV-002", "IAN-INV-003", "IAN-INV-004", "IAN-INV-005", "FS-BAT-001"}
        assert any(r[0] == "summary" and "dry run" in r[1] for r in rows if r)
        s.expire_all()
        assert s.get(MaterialItem, "FS-INV-008").battery_max_a == 135 and s.exec(select(DatasheetSpec)).first() is None
        assert load_config(s).datasheets_imported_at is None


def test_manual_link_add_item_and_the_rematch_after_a_rename(tmp_path):
    engine = _engine(tmp_path)
    with Session(engine) as s:
        import_workbook(s, WB)
        import_datasheets(s, FILES)
        bat = _by_file(s, "ALL_BATTERY")
        # the owner links FS-BAT-006 to the 230 Ah IP65 row by hand: applied at once, never moved by a later run
        r = link_spec(s, bat[("Sheet2", 12)].id, "FS-BAT-006")
        assert "discharge_a_recommended - -> 115" in r["changes"] and s.get(MaterialItem, "FS-BAT-006").discharge_a_recommended == 115 and s.get(MaterialItem, "FS-BAT-006").continuous_a == 150
        with pytest.raises(ValueError):
            link_spec(s, bat[("Sheet2", 29)].id, "FS-BAT-006")
        import_datasheets(s, FILES)
        spec = s.get(DatasheetSpec, bat[("Sheet2", 12)].id)
        assert spec.matched_code == "FS-BAT-006" and spec.match_tier == "manual"
        # "Add as item": the row becomes an inactive item at list price 0 with the datasheet figures
        inv = _by_file(s, "ALL_INVERTER")
        item = add_item_from_spec(s, inv[("Sheet5", 13)].id, "FS-INV-101")
        assert item.code == "FS-INV-101" and item.active is False and item.list_price == 0 and item.rating == 6 and item.battery_max_a == 130 and item.inverter_type == "hybrid"
        assert s.get(DatasheetSpec, inv[("Sheet5", 13)].id).matched_code == "FS-INV-101"
        with pytest.raises(ValueError):
            add_item_from_spec(s, inv[("Sheet5", 14)].id, "FS-INV-101")
        # a renamed item is picked up after the materials import's re-match; an existing match is never moved
        bc5 = s.get(MaterialItem, "BC-INV-005")
        bc5.spec = "BCT-FXC-6.5KW-H-P"
        s.add(bc5)
        s.commit()
        reapply_datasheets(s)
        assert s.get(DatasheetSpec, inv[("Sheet4", 8)].id).matched_code == "BC-INV-005" and s.get(MaterialItem, "BC-INV-005").battery_max_a == 120
        assert s.get(DatasheetSpec, inv[("Sheet4", 7)].id).matched_code == "BC-INV-004"
        # an item that is gone frees its row; the row says so
        s.delete(s.get(MaterialItem, "OP-INV-029"))
        s.commit()
        reapply_datasheets(s)
        assert s.get(DatasheetSpec, inv[("Sheet3", 13)].id).matched_code is None


def test_a_category_clash_is_specs_only_and_the_matcher_is_pure():
    imported = read_workbook(WB)
    items = dict(imported.catalog.items)
    items["X-ACC-001"] = Item(code="X-ACC-001", category="Accessories", supplier="Blue Carbon", name="BCT-FXC-12KW")
    rows = [r for r in read_datasheet_workbook(FILES[1]) if not r.skipped]
    match_rows(rows, items)
    clash = next(r for r in rows if r.model == "BCT-FXC-12KW")
    assert clash.matched_code is None and clash.match_note == "matches X-ACC-001 of category 'Accessories', not the sheet's 'Inverter'; specs-only"
    assert next(r for r in rows if r.model == "IVAM6048P1G1").matched_code == "FS-INV-008"
    # an item already taken is never given twice
    rows2 = [r for r in read_datasheet_workbook(FILES[1]) if not r.skipped]
    match_rows(rows2, items, taken={"FS-INV-008": "elsewhere"})
    r = next(r for r in rows2 if r.model == "IVAM6048P1G1")
    assert r.matched_code is None and "already matched to another datasheet row" in r.match_note


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        yield c


def test_the_routes_upload_list_link_and_note_overrides(client):
    # the upload reads the kind from the sheets; a dry run writes nothing
    with open(FILES[1], "rb") as fh:
        r = client.post("/api/pricing/datasheets?dry_run=true", files={"file": ("ALL_INVERTER_DATA_SHEET.xlsx", fh, "application/octet-stream")})
    assert r.status_code == 200, r.text
    assert r.json()["dry_run"] and r.json()["counts"]["matched"] == 51 and "FS-INV-008" in r.json()["changed_codes"]
    assert client.get("/api/pricing/items/FS-INV-008").json()["battery_max_a"] == 135
    for f in FILES:
        with open(f, "rb") as fh:
            r = client.post("/api/pricing/datasheets", files={"file": (f.name, fh, "application/octet-stream")})
        assert r.status_code == 200, r.text
    assert client.get("/api/pricing/items/FS-INV-008").json()["battery_max_a"] == 139
    assert client.get("/api/pricing/status").json()["item_count"] == 362
    page = client.get("/api/pricing/datasheets", params={"category": "Inverter"}).json()
    rows = page["rows"]
    assert all(r["category"] == "Inverter" for r in rows) and any(r["matched_code"] is None for r in rows) and any(r["held"] for r in rows)
    eco = page["items"]["FS-INV-008"]
    assert eco["source"] == "datasheet" and eco["provenance"]["battery_max_a"] == "datasheet" and eco["datasheet"]["file"] == "ALL_INVERTER_DATA_SHEET.xlsx" and eco["datasheet"]["tier"] == "exact"
    assert page["items"]["FS-INV-001"]["datasheet"] is None and page["items"]["FS-INV-001"]["provenance"]["battery_max_a"] == "remarks"
    # the owner types over a figure: the page says "typed" and the override is kept on the next upload
    r = client.put("/api/pricing/items/FS-INV-008", json={"battery_max_a": 150})
    assert r.status_code == 200 and r.json()["battery_max_a"] == 150
    page = client.get("/api/pricing/datasheets", params={"category": "Inverter"}).json()
    assert page["items"]["FS-INV-008"]["provenance"]["battery_max_a"] == "typed" and page["items"]["FS-INV-008"]["datasheet"]["overridden"] == ["battery_max_a"]
    with open(FILES[1], "rb") as fh:
        client.post("/api/pricing/datasheets", files={"file": (FILES[1].name, fh, "application/octet-stream")})
    assert client.get("/api/pricing/items/FS-INV-008").json()["battery_max_a"] == 150
    # a manual link and an added item through the routes
    row = next(r for r in rows if r["model"] == "BCT-FXC-6.5KW")
    r = client.post(f"/api/pricing/datasheets/{row['id']}/link", json={"code": "BC-INV-005"})
    assert r.status_code == 200 and r.json()["code"] == "BC-INV-005"
    assert client.post(f"/api/pricing/datasheets/{row['id']}/link", json={"code": "NOPE-000"}).status_code == 404
    row2 = next(r for r in rows if r["model"] == "IVGM6KLP1G1")
    r = client.post(f"/api/pricing/datasheets/{row2['id']}/add-item", json={"code": "FS-INV-102"})
    assert r.status_code == 201 and r.json()["active"] is False and r.json()["list_price"] == 0 and r.json()["rating"] == 6
    assert client.post(f"/api/pricing/datasheets/{row2['id']}/add-item", json={"code": "FS-INV-102"}).status_code == 409
    # not a workbook, and an engineer cannot import
    r = client.post("/api/pricing/datasheets", files={"file": ("x.xlsx", b"not a zip", "application/octet-stream")})
    assert r.status_code == 422
