from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, or_, select

from ..auth import require_user
from ..core.audit import categories_for_ui
from ..db import get_session
from ..models import ApplianceCatalog, utcnow
from ..schemas import ApplianceCatalogIn, ApplianceCatalogOut, AssessmentDoc

router = APIRouter(prefix="/api/appliances", tags=["appliances"], dependencies=[Depends(require_user)])


def _key(name: str, brand: str, model: str) -> tuple[str, str, str]:
    return name.strip().lower(), brand.strip().lower(), model.strip().lower()


def remember_appliances(session: Session, doc: AssessmentDoc) -> None:
    """Add every appliance typed in an audit to the catalogue (clean slate that grows)."""
    changed = False
    for e in doc.audit.appliances:
        if not e.name.strip() or e.input_power_w <= 0:
            continue
        n, b, m = _key(e.name, e.brand, e.model)
        row = session.exec(select(ApplianceCatalog).where(ApplianceCatalog.name == e.name.strip()).where(ApplianceCatalog.brand == e.brand.strip()).where(ApplianceCatalog.model == e.model.strip())).first()
        if row is None:
            for cand in session.exec(select(ApplianceCatalog).where(ApplianceCatalog.name.ilike(e.name.strip()))).all():
                if _key(cand.name, cand.brand, cand.model) == (n, b, m):
                    row = cand
                    break
        if row is None:
            session.add(ApplianceCatalog(name=e.name.strip(), brand=e.brand.strip(), model=e.model.strip(), category=e.category, input_power_w=e.input_power_w, use_count=1))
        else:
            row.category, row.input_power_w, row.use_count, row.updated_at = e.category, e.input_power_w, row.use_count + 1, utcnow()
            session.add(row)
        changed = True
    if changed:
        session.commit()


def _out(r: ApplianceCatalog) -> ApplianceCatalogOut:
    return ApplianceCatalogOut(id=r.id, name=r.name, brand=r.brand, model=r.model, category=r.category, input_power_w=r.input_power_w, use_count=r.use_count)


@router.get("/categories")
def categories() -> list[dict]:
    return categories_for_ui()


@router.get("", response_model=list[ApplianceCatalogOut])
def search(q: str = "", limit: int = 20, session: Session = Depends(get_session)) -> list[ApplianceCatalogOut]:
    stmt = select(ApplianceCatalog)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(ApplianceCatalog.name.ilike(like), ApplianceCatalog.brand.ilike(like), ApplianceCatalog.model.ilike(like)))
    rows = session.exec(stmt.order_by(ApplianceCatalog.use_count.desc(), ApplianceCatalog.name).limit(max(1, min(limit, 100)))).all()
    return [_out(r) for r in rows]


@router.post("", response_model=ApplianceCatalogOut, status_code=201)
def add(body: ApplianceCatalogIn, session: Session = Depends(get_session)) -> ApplianceCatalogOut:
    row = ApplianceCatalog(name=body.name.strip(), brand=body.brand.strip(), model=body.model.strip(), category=body.category, input_power_w=body.input_power_w)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _out(row)


@router.delete("/{item_id}", status_code=204)
def remove(item_id: int, session: Session = Depends(get_session)) -> Response:
    row = session.get(ApplianceCatalog, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(row)
    session.commit()
    return Response(status_code=204)
