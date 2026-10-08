"""Public estimate: four questions, no login. Rate limited per browser and per address.

These routes are the only ones a website on another origin calls (see
Settings.public_origins); everything else stays behind the login and, in
production, behind Cloudflare Access.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlmodel import Session

from ..auth import current_user
from ..config import Settings, get_settings
from ..core.dataset import PvgisDataset
from ..core.quick import GOAL_LABEL, PATTERN_LABEL, quick_estimate
from ..core.towns import towns_payload
from ..db import get_session
from ..models import Assessment, QuickEstimateLog
from ..notify import send_lead_notice, smtp_configured
from ..pricing.job import PricingContext
from ..pricing.store import load_catalog, load_config
from ..profile import public_profile, warranty_lines
from ..schemas import AssessmentDoc, BillEntry, EnergyAudit, LeadInfo, ProgramJob, QuickLead, QuickRequest
from .deps import get_pvgis



def internal_or_user(request: Request, settings: Settings = Depends(get_settings), user: str | None = Depends(current_user)) -> None:
    """With an internal token configured, only the public website process (token) or a signed-in user may call these."""
    if not settings.internal_token or user:
        return
    if request.headers.get("x-internal-token", "") != settings.internal_token:
        raise HTTPException(status_code=404, detail="Not found")


router = APIRouter(prefix="/api/quick", tags=["quick"], dependencies=[Depends(internal_or_user)])
_hits: dict[str, deque] = defaultdict(deque)
ADDRESS_MULTIPLIER = 20  # mobile networks put thousands of phones behind one address
UNAVAILABLE = "The estimate isn't available right now. Please try again later or message us on Facebook."


def _bucket_ok(key: str, limit: int, now: float) -> bool:
    q = _hits[key]
    while q and now - q[0] > 3600:
        q.popleft()
    return len(q) < limit


def _client_ip(request: Request) -> str:
    return request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?")


def _throttle(request: Request, limit: int) -> None:
    """Limit per browser (X-Visitor token) and, more loosely, per address, so one shared
    mobile address does not lock out a whole town while a script cannot run unlimited either."""
    ip = _client_ip(request)
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


def _source_label(src) -> str:
    if src.utm_source:
        return src.utm_source + (f"/{src.utm_campaign}" if src.utm_campaign else "")
    if src.referrer:
        host = urlparse(src.referrer).netloc
        return host or "referral"
    return "direct"


@router.get("/status")
def quick_status(session: Session = Depends(get_session), settings: Settings = Depends(get_settings), pvgis: PvgisDataset = Depends(get_pvgis)) -> dict:
    """What the public page needs before the first question: whether the estimate works, who you are, and the towns."""
    cfg = load_config(session)
    profile = public_profile(session, settings)
    return {
        "enabled": cfg.quick.enabled and pvgis.available and not pvgis.synthetic,
        "data": pvgis.available,
        "profile": profile,
        "warranty": warranty_lines(profile),
        "towns": towns_payload(),
        "public_url": settings.public_url,
        "estimate_url": settings.estimate_url,
    }


@router.post("/estimate")
def estimate(body: QuickRequest, request: Request, session: Session = Depends(get_session), pvgis: PvgisDataset = Depends(get_pvgis)) -> dict:
    ctx = _ctx(session)
    if not ctx.config.quick.enabled:
        raise HTTPException(status_code=404, detail=UNAVAILABLE)
    if not pvgis.available or pvgis.synthetic:
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    _throttle(request, ctx.config.quick.max_requests_per_hour)
    try:
        out = quick_estimate(body, pvgis, ctx)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError:
        raise HTTPException(status_code=503, detail=UNAVAILABLE)
    src = request.headers.get("x-source", "")[:100]
    session.add(QuickEstimateLog(
        goal=body.goal, pattern=body.pattern, monthly_kwh=float(out["inputs"]["monthly_kwh"]), town=out["inputs"]["town"],
        lat=float(out["inputs"]["lat"]), lon=float(out["inputs"]["lon"]), panels=int(out["system"]["panels"]), kwp=float(out["system"]["kwp"]),
        battery_kwh=float(out["system"]["battery_kwh"]), price=float(out["price"]["total"]), source=src.split("/")[0], campaign=src.split("/", 1)[1] if "/" in src else "",
        visitor=(request.headers.get("x-visitor") or "")[:64],
    ))
    session.commit()
    return out


@router.post("/lead")
def lead(body: QuickLead, request: Request, tasks: BackgroundTasks, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> dict:
    """Keep the visitor's details as a lead on the job list, with the four answers and what they saw."""
    cfg = load_config(session)
    if not cfg.quick.enabled:
        raise HTTPException(status_code=404, detail=UNAVAILABLE)
    if body.website.strip():
        return {"ok": True}  # a bot filled the hidden field; pretend it worked
    _throttle(request, cfg.quick.max_requests_per_hour)
    try:
        from ..core.quick import resolve_location
        where = resolve_location(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    kwh = body.monthly_kwh or ((body.monthly_php or 0) / cfg.economics.tariff_php_per_kwh)
    now = datetime.now(timezone.utc)
    est = body.estimate
    wants = {"net_metering": "a lower bill, no battery", "combination": "a lower bill and backup in brownouts", "off_grid": "to go off the grid"}[body.goal]
    seen = f" Saw: {est.panels} panels, {est.kwp:.2f} kWp{', ' + format(est.battery_kwh, '.0f') + ' kWh battery' if est.battery_kwh else ''}, ₱{est.price:,.0f}." if est.panels else ""
    notes = (f"From the website estimate, {now.strftime('%-d %b %Y')}. Contact: {body.contact.strip()}"
             f"{' (best time: ' + body.preferred_time + ')' if body.preferred_time else ''}. Wants: {wants}. "
             f"Uses power {PATTERN_LABEL[body.pattern]}. Bill: about {kwh:,.0f} kWh"
             f"{' (₱' + format(body.monthly_php, ',.0f') + ')' if body.monthly_php else ''}.{seen} "
             f"Location: {where['label']}{'; pin placed by the customer, confirm on the visit' if not body.town else ''}.")
    address = body.address.strip() or (f"{where['town']}, {where['province']}" if where["town"] else "")
    doc = AssessmentDoc(
        customer_name=body.name.strip(), address=address, notes=notes, lat=where["lat"], lon=where["lon"],
        audit=EnergyAudit(bills=[BillEntry(id="lead", billing_month=now.strftime("%Y-%m"), kwh=float(kwh) if kwh else 0.0, amount_php=body.monthly_php)], system={"kind": body.goal}),
        program=ProgramJob(stage="lead"),
        lead=LeadInfo(contact=body.contact.strip(), town=where["label"], preferred_time=body.preferred_time, consent=body.consent,
                      created_at=now.isoformat(), source=body.source, estimate=est),
    )
    a = Assessment(customer_name=doc.customer_name, address=doc.address, doc=doc.model_dump(mode="json"))
    session.add(a)
    session.commit()
    session.refresh(a)
    if smtp_configured(settings):
        link = f"{settings.public_url.rstrip('/')}/assessments/{a.id}" if settings.public_url else f"assessment #{a.id}"
        tasks.add_task(send_lead_notice, settings, f"New solar lead: {doc.customer_name} ({where['label']})", f"{notes}\n\nSource: {_source_label(body.source)}\nOpen: {link}\n")
    return {"ok": True, "id": a.id, "goal_label": GOAL_LABEL[body.goal]}
