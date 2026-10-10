"""Materials database, pricing settings and workbook import."""
from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from starlette.concurrency import run_in_threadpool

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, func, select

from ..auth import require_owner, require_user
from ..db import get_session
from ..models import MaterialItem, MaterialSupplier, utcnow
from ..pricing.config import PricingConfig, settings_version
from ..pricing.datasheets import add_item_from_spec, apply_held_spec, datasheet_page, import_datasheets, link_spec, note_overrides, withdraw_held_spec
from ..pricing.importer import read_workbook
from ..pricing.store import SEED_PATH, catalog_status, load_config, persist_import, save_config
from ..schemas import DatasheetLink, MaterialItemIn, MaterialItemPatch

MAX_UPLOAD, MAX_UNZIPPED = 10 * 1024 * 1024, 200 * 1024 * 1024
log = logging.getLogger("solarapp.audit")

router = APIRouter(prefix="/api/pricing", tags=["pricing"], dependencies=[Depends(require_user)])


@router.get("/status")
def status(session: Session = Depends(get_session)) -> dict:
    # settings_version: the fingerprint a priced project stores; a project whose stored one differs is flagged in the list
    return {**catalog_status(session), "settings_version": settings_version(load_config(session))}


@router.get("/config", response_model=PricingConfig)
def get_config(session: Session = Depends(get_session)) -> PricingConfig:
    return load_config(session)


@router.put("/config", response_model=PricingConfig, dependencies=[Depends(require_owner)])
def put_config(cfg: PricingConfig, session: Session = Depends(get_session)) -> PricingConfig:
    old = load_config(session)
    cfg.imported_from, cfg.imported_at = old.imported_from, old.imported_at
    save_config(session, cfg)
    before, after = settings_version(old), settings_version(cfg)
    if before != after:  # every priced project now carries the old version and is flagged; quoted jobs re-price only on confirmation
        log.info("pricing settings changed version %s -> %s", before, after)
    return cfg


@router.post("/config/reset", response_model=PricingConfig, dependencies=[Depends(require_owner)])
def reset_config(session: Session = Depends(get_session)) -> PricingConfig:
    old = load_config(session)
    cfg = PricingConfig(imported_from=old.imported_from, imported_at=old.imported_at)
    save_config(session, cfg)
    return cfg


@router.post("/import", dependencies=[Depends(require_owner)])
async def import_upload(
    file: UploadFile = File(...),
    keep_config: bool = Query(False, description="update items and suppliers only; keep the app's pricing settings"),
    session: Session = Depends(get_session),
) -> dict:
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="Upload the materials workbook as .xlsx")
    if file.size is not None and file.size > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="The workbook is larger than 10 MB.")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="The workbook is larger than 10 MB.")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "materials.xlsx"
        path.write_bytes(data)
        try:
            with zipfile.ZipFile(path) as z:
                infos = z.infolist()
                if len(infos) > 2000 or sum(i.file_size for i in infos) > MAX_UNZIPPED:
                    raise HTTPException(status_code=422, detail="The workbook is unreasonably large inside.")
        except zipfile.BadZipFile:
            raise HTTPException(status_code=422, detail="That is not an .xlsx workbook.")
        try:
            result = await run_in_threadpool(read_workbook, path)  # parsing is slow; keep the server answering meanwhile
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=f"Could not read the workbook. It needs the same sheets as PLD_Materials_DB. ({e})")
    report = persist_import(session, result, replace_config=not keep_config)
    log.info("materials imported file=%r added=%s updated=%s", (file.filename or "")[:80], report.get("added"), report.get("updated"))
    return report


@router.post("/import-seed", dependencies=[Depends(require_owner)])
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


@router.post("/items", response_model=MaterialItem, status_code=201, dependencies=[Depends(require_owner)])
def create_item(body: MaterialItemIn, session: Session = Depends(get_session)) -> MaterialItem:
    if session.get(MaterialItem, body.code) is not None:
        raise HTTPException(status_code=409, detail="An item with this code exists already")
    row = MaterialItem(**body.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.put("/items/{code}", response_model=MaterialItem, dependencies=[Depends(require_owner)])
def update_item(code: str, body: MaterialItemPatch, session: Session = Depends(get_session)) -> MaterialItem:
    row = session.get(MaterialItem, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    patch = body.model_dump(exclude_unset=True)
    for k, v in patch.items():
        setattr(row, k, v)
    row.updated_at = utcnow()
    session.add(row)
    session.commit()
    note_overrides(session, code, patch)   # round 12: a figure typed over the datasheet's is kept on the next run
    session.refresh(row)
    return row


@router.delete("/items/{code}", status_code=204, dependencies=[Depends(require_owner)])
def delete_item(code: str, session: Session = Depends(get_session)):
    row = session.get(MaterialItem, code)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(row)
    session.commit()


# ---- round 12: the maker's datasheet workbooks (docs/audits/round-12/engineer-brief.md, 5.1 and 2.5)

async def _read_upload(file: UploadFile, what: str) -> bytes:
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail=f"Upload the {what} as .xlsx")
    if file.size is not None and file.size > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="The workbook is larger than 10 MB.")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="The workbook is larger than 10 MB.")
    return data


@router.post("/datasheets", dependencies=[Depends(require_owner)])
async def import_datasheet_upload(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="report what would change and write nothing"),
    apply_held: bool = Query(False, description="apply the held figures too (only on the owner's word: brief 6.4, 6.8)"),
    session: Session = Depends(get_session),
) -> dict:
    """One datasheet workbook (panels, inverters or batteries; the kind is read from the sheets, not the name): the
    per-row report of the importer, the same one `python -m solarapp.pricing.datasheets` prints."""
    data = await _read_upload(file, "datasheet workbook")
    name = Path(file.filename or "datasheet.xlsx").name
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / name
        path.write_bytes(data)
        try:
            with zipfile.ZipFile(path) as z:
                infos = z.infolist()
                if len(infos) > 2000 or sum(i.file_size for i in infos) > MAX_UNZIPPED:
                    raise HTTPException(status_code=422, detail="The workbook is unreasonably large inside.")
        except zipfile.BadZipFile:
            raise HTTPException(status_code=422, detail="That is not an .xlsx workbook.")
        try:
            report = await run_in_threadpool(import_datasheets, session, [path], {str(path): name}, dry_run, apply_held)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=f"Could not read the datasheet workbook. ({e})")
    log.info("datasheets imported file=%r counts=%s dry_run=%s", name[:80], report.counts, dry_run)
    return report.to_dict()


@router.get("/datasheets")
def datasheet_rows(category: Optional[str] = None, session: Session = Depends(get_session)) -> dict:
    """The specs rows and, per equipment item, where each electrical figure came from (the Materials page's view)."""
    return datasheet_page(session, category)


@router.post("/datasheets/{spec_id}/link", dependencies=[Depends(require_owner)])
def datasheet_link(spec_id: int, body: DatasheetLink, session: Session = Depends(get_session)) -> dict:
    """"Link to item": a manual match, applied at once and never moved by a later run."""
    try:
        return link_spec(session, spec_id, body.code)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/datasheets/{spec_id}/apply-held", dependencies=[Depends(require_owner)])
def datasheet_apply_held(spec_id: int, session: Session = Depends(get_session)) -> dict:
    """The owner confirms one held row (the answers to the brief's 6.4 and 6.8 differ): the held figures go on and stay on."""
    try:
        return apply_held_spec(session, spec_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/datasheets/{spec_id}/withdraw-held", dependencies=[Depends(require_owner)])
def datasheet_withdraw_held(spec_id: int, session: Session = Depends(get_session)) -> dict:
    """The owner takes the confirmation back: the row is held again and the item returns to its remark's figure."""
    try:
        return withdraw_held_spec(session, spec_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/datasheets/{spec_id}/add-item", response_model=MaterialItem, status_code=201, dependencies=[Depends(require_owner)])
def datasheet_add_item(spec_id: int, body: DatasheetLink, session: Session = Depends(get_session)) -> MaterialItem:
    """"Add as item": the datasheet row as a new, inactive item at list price 0 with the owner's code."""
    try:
        return add_item_from_spec(session, spec_id, body.code, body.supplier or "")
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
