from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from solarapp import models  # noqa: F401
from solarapp.pricing.store import catalog_status, import_workbook, load_catalog, load_config, save_config

WB = Path(__file__).resolve().parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"


def test_import_persist_and_reimport(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 't.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        r = import_workbook(s, WB)
        assert r["added"] == 362 and r["updated"] == 0 and r["suppliers"] == 4
        cat = load_catalog(s)
        assert len(cat.items) == 362 and cat.get("FS-BAT-006").rating == 11.7
        cfg = load_config(s)
        assert cfg.imported_from == "PLD_Materials_DB.xlsx" and cfg.tools.charge_per_installation_day > 900
        # the app is the master: an edit survives a re-import that keeps config, and typed dimensions survive
        item = s.get(models.MaterialItem, "OP-PNL-004")
        item.panel_length_m, item.panel_width_m = 2.384, 1.134
        s.add(item); s.commit()
        cfg.job.lgu_permit_cfei = 6000
        save_config(s, cfg)
        r2 = import_workbook(s, WB, replace_config=False)
        assert r2["added"] == 0 and r2["updated"] == 362
        assert s.get(models.MaterialItem, "OP-PNL-004").panel_length_m == 2.384
        assert load_config(s).job.lgu_permit_cfei == 6000
        st = catalog_status(s)
        assert st["item_count"] == 362 and st["supplier_count"] == 4
