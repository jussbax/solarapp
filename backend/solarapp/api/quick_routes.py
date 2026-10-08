"""Public quick estimate: four questions, no login. Rate limited per visitor address."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from ..core.dataset import PvgisDataset
from ..core.quick import quick_estimate
from ..db import get_session
from ..models import Assessment
from ..pricing.job import PricingContext
from ..pricing.store import load_catalog, load_config
from ..schemas import AssessmentDoc, BillEntry, EnergyAudit, ProgramJob, QuickLead, QuickRequest
from .deps import get_pvgis

router = APIRouter(prefix="/api/quick", tags=["quick"])
_hits: dict[str, deque] = defaultdict(deque)


ADDRESS_MULTIPLIER = 20  # mobile networks put thousands of phones behind one address


def _bucket_ok(key: str, limit: int, now: float) -> bool:
    q = _hits[key]
    while q and now - q[0] > 3600:
        q.popleft()
    return len(q) < limit


def _throttle(request: Request, limit: int) -> None:
    """Limit per browser (X-Visitor token) and, more loosely, per address, so one shared
    mobile address does not lock out a whole town while a script cannot run unlimited either."""
    ip = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?")
    token = (request.headers.get("x-visitor") or "").strip()[:64]
    now = time.time()
    keys = [(f"ip:{ip}", limit * ADDRESS_MULTIPLIER)]
    keys.append((f"v:{ip}:{token}", limit) if token else (f"ip-only:{ip}", limit))
    if not all(_bucket_ok(k, lim, now) for k, lim in keys):
        raise HTTPException(status_code=429, detail="You've run a lot of estimates in a short time. Please try again in an hour.")
    for k, _ in keys:
        _hits[k].append(now)


def _ctx(session: Session) -> PricingContext:
    return PricingContext(load_catalog(session), load_config(session))


@router.get("/status")
def quick_status(session: Session = Depends(get_session), pvgis: PvgisDataset = Depends(get_pvgis)) -> dict:
    cfg = load_config(session)
    return {"enabled": cfg.quick.enabled and pvgis.available and not pvgis.synthetic, "data": pvgis.available}


@router.post("/estimate")
def estimate(body: QuickRequest, request: Request, session: Session = Depends(get_session), pvgis: PvgisDataset = Depends(get_pvgis)) -> dict:
    ctx = _ctx(session)
    if not ctx.config.quick.enabled:
        raise HTTPException(status_code=404, detail="The estimate isn't available right now. Please try again later or message us on Facebook.")
    if not pvgis.available or pvgis.synthetic:
        raise HTTPException(status_code=503, detail="The estimate isn't available right now. Please try again later or message us on Facebook.")
    _throttle(request, ctx.config.quick.max_requests_per_hour)
    try:
        return quick_estimate(body, pvgis, ctx)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/lead")
def lead(body: QuickLead, request: Request, session: Session = Depends(get_session)) -> dict:
    """Keep the visitor's details as a lead on the job list, with the four answers."""
    cfg = load_config(session)
    if not cfg.quick.enabled:
        raise HTTPException(status_code=404, detail="The estimate isn't available right now. Please try again later or message us on Facebook.")
    _throttle(request, cfg.quick.max_requests_per_hour)
    kwh = body.monthly_kwh or ((body.monthly_php or 0) / cfg.economics.tariff_php_per_kwh)
    notes = (f"Quick estimate lead. Contact: {body.contact}. Goal: {body.goal}. Usage: {body.pattern}. "
             f"Monthly: {body.monthly_kwh or '-'} kWh / PHP {body.monthly_php or '-'}.")
    doc = AssessmentDoc(
        customer_name=body.name.strip(), address=body.address.strip(), notes=notes, lat=body.lat, lon=body.lon,
        audit=EnergyAudit(bills=[BillEntry(id="lead", billing_month=time.strftime("%Y-%m"), kwh=float(kwh) if kwh else 0.0, amount_php=body.monthly_php)], system={"kind": body.goal}),
        program=ProgramJob(stage="lead"),
    )
    a = Assessment(customer_name=doc.customer_name, address=doc.address, doc=doc.model_dump(mode="json"))
    session.add(a)
    session.commit()
    return {"ok": True}
