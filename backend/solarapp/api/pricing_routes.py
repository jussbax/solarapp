"""Materials database, pricing settings and workbook import."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, func, select

from ..auth import require_user
from ..db import get_session
from ..models import MaterialItem, MaterialSupplier, utcnow
from ..pricing.config import PricingConfig
from ..pricing.importer import read_workbook
from ..pricing.store import SEED_PATH, catalog_status, load_config, persist_import, save_config
from ..schemas import MaterialItemIn, MaterialItemPatch

router = APIRouter(prefix="/api/pricing", tags=["pricing"], dependencies=[Depends(require_user)])


@router.get("/status")
def status(session: Session = Depends(get_session)) -> dict:
    return catalog_status(session)


@router.get("/config", response_model=PricingConfig)
def get_config(session: Session = Depends(get_session)) -> PricingConfig:
    return load_config(session)


@router.put("/config", response_model=PricingConfig)
def put_config(cfg: PricingConfig, session: Session = Depends(get_session)) -> PricingConfig:
    old = load_config(session)
    cfg.imported_from, cfg.imported_at = old.imported_from, old.imported_at
    save_config(session, cfg)
    return cfg


@router.post("/config/reset", response_model=PricingConfig)
def reset_config(session: Session = Depends(get_session)) -> PricingConfig:
    old = load_config(session)
    cfg = PricingConfig(imported_from=old.imported_from, imported_at=old.imported_at)
    save_config(session, cfg)
    return cfg


@router.post("/import")
async def import_upload(
    file: UploadFile = File(...),
    keep_config: bool = Query(False, description="update items and suppliers only; keep the app's pricing settings"),
    session: Session = Depends(get_session),
) -> dict:
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="Upload the materials workbook as .xlsx")
    data = await file.read()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / (Path(file.filename or "materials.xlsx").name)
        path.write_bytes(data)
        try:
            result = read_workbook(path)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=f"Could not read the workbook: {e}")
    return persist_import(session, result, replace_config=not keep_config)


@router.post("/import-seed")
def import_seed(keep_config: bool = Query(False), session: Session = Depends(get_session)) -> dict:
    if not SEED_PATH.exists():
        raise HTTPException(status_code=404, detail="No bundled workbook in this build.")
    return persist_import(session, read_workbook(SEED_PATH), replace_config=not keep_config)


@router.get("/categories")
def categories(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(select(MaterialItem.category, func.count()).group_by(MaterialItem.category).order_by(MaterialItem.category)).all()
    return [{"name": c, "count": n} for c, n in rows]


@router.get("/suppliers", response_model=list[MaterialSupplier])
def suppliers(session: Session = Depends(get_session)) -> list[MaterialSupplier]:
    return list(session.exec(select(MaterialSupplier).order_by(MaterialSupplier.name)).all())


@router.get("/items", response_model=list[MaterialItem])
def items(
    q: str = "",
    category: Optional[str] = None,
    supplier: Optional[str] = None,
    include_inactive: bool = False,
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> list[MaterialItem]:
    stmt = select(MaterialItem)
    if category:
        stmt = stmt.where(MaterialItem.category == category)
    if supplier:
        stmt = stmt.where(MaterialItem.supplier == supplier)
    if not include_inactive:
        stmt = stmt.where(MaterialItem.active == True)  # noqa: E712
    for word in q.split():
        like = f"%{word}%"
        stmt = stmt.where((MaterialItem.name.ilike(like)) | (MaterialItem.code.ilike(like)) | (MaterialItem.spec.ilike(like)))
    stmt = stmt.order_by(MaterialItem.category, MaterialItem.code).limit(limit)
    return list(session.exec(stmt).all())


@router.get("/items/{code}", response_model=MaterialItem)
def get_item(code: str, session: Session = Depends(get_session)) -> MaterialItem:
    row = session.get(MaterialItem, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return row


@router.post("/items", response_model=MaterialItem, status_code=201)
def create_item(body: MaterialItemIn, session: Session = Depends(get_session)) -> MaterialItem:
    if session.get(MaterialItem, body.code) is not None:
        raise HTTPException(status_code=409, detail="An item with this code exists already")
    row = MaterialItem(**body.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.put("/items/{code}", response_model=MaterialItem)
def update_item(code: str, body: MaterialItemPatch, session: Session = Depends(get_session)) -> MaterialItem:
    row = session.get(MaterialItem, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/items/{code}", status_code=204)
def delete_item(code: str, session: Session = Depends(get_session)):
    row = session.get(MaterialItem, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(row)
    session.commit()
