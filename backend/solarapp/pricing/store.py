"""Persist and load the catalog and pricing configuration (SQLite)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from ..models import AppSetting, MaterialItem, MaterialSupplier, utcnow
from .catalog import ELECTRICAL_FIELDS, Catalog, Item, Supplier
from .config import PricingConfig
from .datasheets import reapply_datasheets
from .importer import ImportResult, read_workbook

CONFIG_KEY = "pricing_config"
SEED_PATH = Path(__file__).resolve().parent.parent.parent / "data_seed" / "PLD_Materials_DB.xlsx"
# fields the owner types in the app that a re-import must not blank out when the workbook has no value for them
KEEP_WHEN_BLANK = ("panel_length_m", "panel_width_m") + ELECTRICAL_FIELDS


def ensure_material_columns(session: Session) -> list[str]:
    """SQLite keeps the table it was created with; columns added to MaterialItem since (the electrical data)
    are added here at startup so an existing database keeps working. Returns the columns added."""
    present = {row[1] for row in session.exec(text("PRAGMA table_info(material_items)")).all()}
    if not present:
        return []
    added: list[str] = []
    for col in MaterialItem.__table__.columns:
        if col.name in present:
            continue
        kind = col.type.__class__.__name__.upper()
        sql_type = "INTEGER" if kind in ("INTEGER", "BOOLEAN") else "REAL" if kind == "FLOAT" else "VARCHAR"
        default = " DEFAULT ''" if sql_type == "VARCHAR" and not col.nullable else ""
        session.exec(text(f"ALTER TABLE material_items ADD COLUMN {col.name} {sql_type}{default}"))
        added.append(col.name)
    if added:
        session.commit()
    return added


def load_config(session: Session) -> PricingConfig:
    row = session.get(AppSetting, CONFIG_KEY)
    if row and row.value:
        try:
            return PricingConfig.model_validate_json(row.value)
        except Exception:  # noqa: BLE001
            pass
    return PricingConfig()


def save_config(session: Session, cfg: PricingConfig) -> None:
    row = session.get(AppSetting, CONFIG_KEY) or AppSetting(key=CONFIG_KEY)
    row.value = cfg.model_dump_json()
    session.add(row)
    session.commit()


def load_catalog(session: Session, include_inactive: bool = False) -> Catalog:
    items: dict[str, Item] = {}
    for r in session.exec(select(MaterialItem)).all():
        if not include_inactive and not r.active:
            continue
        d = r.model_dump()
        d.pop("updated_at", None)
        items[r.code] = Item(**d)
    sups = {r.name: Supplier(**r.model_dump()) for r in session.exec(select(MaterialSupplier)).all()}
    return Catalog(items, sups)


def catalog_status(session: Session) -> dict:
    n = len(session.exec(select(MaterialItem.code)).all())
    cfg = load_config(session)
    return {"item_count": n, "supplier_count": len(session.exec(select(MaterialSupplier.name)).all()),
            "imported_from": cfg.imported_from, "imported_at": cfg.imported_at, "seed_available": SEED_PATH.exists()}


def persist_import(session: Session, result: ImportResult, replace_config: bool = True) -> dict:
    """Upsert items by code and suppliers by name. Prices and specs follow the workbook; panel
    dimensions typed in the app are kept when the workbook has none; items absent from the
    workbook are left untouched."""
    added = updated = 0
    for it in result.catalog.items.values():
        row = session.get(MaterialItem, it.code)
        data = asdict(it)
        if row is None:
            session.add(MaterialItem(**data))
            added += 1
        else:
            for k, v in data.items():
                if k in KEEP_WHEN_BLANK and v in (None, ""):
                    continue
                if k == "active":
                    continue
                setattr(row, k, v)
            row.updated_at = utcnow()
            session.add(row)
            updated += 1
    for s in result.catalog.suppliers.values():
        row = session.get(MaterialSupplier, s.name)
        if row is None:
            session.add(MaterialSupplier(**asdict(s)))
        else:
            for k, v in asdict(s).items():
                setattr(row, k, v)
            session.add(row)
    session.commit()
    # round 12: the workbook row wrote the remark inference back over every electrical field it produced; the
    # datasheet figures sit above it in the precedence (brief 2.4), so they go back on at the end of every import
    datasheets = reapply_datasheets(session)
    if replace_config:
        old = load_config(session)
        result.config.datasheets_imported_from, result.config.datasheets_imported_at = old.datasheets_imported_from, old.datasheets_imported_at
        save_config(session, result.config)
    else:
        cfg = load_config(session)
        cfg.imported_from, cfg.imported_at = result.config.imported_from, result.config.imported_at
        save_config(session, cfg)
    return {"added": added, "updated": updated, "suppliers": result.supplier_count, "warnings": result.warnings, "datasheets": datasheets}


def import_workbook(session: Session, path: str | Path, replace_config: bool = True) -> dict:
    return persist_import(session, read_workbook(path), replace_config)


def ensure_seeded(session: Session) -> Optional[dict]:
    """Startup: add any new material columns, then load the seed workbook when the materials table is empty."""
    ensure_material_columns(session)
    if session.exec(select(MaterialItem.code)).first() is None and SEED_PATH.exists():
        return import_workbook(session, SEED_PATH)
    return None
