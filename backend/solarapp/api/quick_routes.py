"""Public estimate: four questions, no login. Rate limited per browser and per address.

These routes are the only ones the public website process calls (with the
internal token) or, from another origin, a website listed in
Settings.public_origins. Everything else stays behind the login and, in
production, behind Cloudflare Access.
"""
from __future__ import annotations

import hmac
import ipaddress
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlmodel import Session

from ..auth import current_user
from ..config import Settings, get_settings
from ..core.dataset import PvgisDataset
from ..core.quick import GOAL_LABEL, OUT_OF_AREA_KM, PATTERN_LABEL, quick_estimate
from ..core.towns import nearest_town, provinces, towns_payload
from ..db import get_engine, get_session
from ..models import Lead, QuickEstimateLog
from ..notify import lead_notice, send_lead_notice, smtp_configured
from ..pricing.job import PricingContext
from ..pricing.store import load_catalog, load_config
from ..profile import company_profile, public_profile, warranty_lines
from ..schemas import QuickLead, QuickRequest
from .deps import get_pvgis
from .leads import source_label as _source_label

log = logging.getLogger("solarapp.audit")
# no "message us on Facebook" here: the page adds that itself, and only when the profile has a link to message
UNAVAILABLE = "The estimate isn't available right now. Please try again later."
TOO_MANY = "You've run a lot of estimates in a short time. Please try again in an hour."

# ---- client address: proxy headers are honoured only from our own proxies (loopback, Docker and office networks)
_TRUSTED = [ipaddress.ip_network(n) for n in ("127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else ""
    try:
        trusted = any(ipaddress.ip_address(peer) in n for n in _TRUSTED)
    except ValueError:
        trusted = False
    if trusted:
        forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded[:64]
    return peer or "?"


# ---- rate limiter: bounded memory whatever a visitor sends
ADDRESS_MULTIPLIER = 10       # one shared mobile address may hold many phones
MAX_KEYS = 20_000             # beyond this a token flood is under way; drop the per-token buckets
SWEEP_EVERY_S = 300.0
_hits: dict[str, deque] = {}
_lock = threading.Lock()
_last_sweep = 0.0


def _bucket_ok(key: str, limit: int, now: float) -> bool:
    """True when the key may take another hit. Never allocates for a key it has not seen."""
    q = _hits.get(key)
    if q is None:
        return limit > 0
    while q and now - q[0] > 3600:
        q.popleft()
    if not q:
        del _hits[key]
        return limit > 0
    return len(q) < limit


def _sweep(now: float) -> None:
    global _last_sweep
    if now - _last_sweep < SWEEP_EVERY_S and len(_hits) < MAX_KEYS:
        return
    _last_sweep = now
    for k in [k for k, q in _hits.items() if not q or now - q[-1] > 3600]:
        del _hits[k]
    if len(_hits) >= MAX_KEYS:
        for k in [k for k in _hits if k.startswith("v:")]:
            del _hits[k]


def _throttle(request: Request, limit: int) -> None:
    """Limit per browser (X-Visitor token) and, more loosely, per address. A rejected request allocates nothing."""
    ip = client_ip(request)
    token = (request.headers.get("x-visitor") or "").strip()[:64]
    now = time.time()
    with _lock:
        _sweep(now)
        ip_key = f"ip:{ip}"
        if not _bucket_ok(ip_key, limit * ADDRESS_MULTIPLIER, now):
            raise HTTPException(status_code=429, detail=TOO_MANY, headers={"Retry-After": "3600"})
        per_key = f"v:{ip}:{token}" if token else f"ip-only:{ip}"
        if not _bucket_ok(per_key, limit, now):
            raise HTTPException(status_code=429, detail=TOO_MANY, headers={"Retry-After": "3600"})
        for k in (ip_key, per_key):
            _hits.setdefault(k, deque()).append(now)


def internal_or_user(request: Request, settings: Settings = Depends(get_settings), user: str | None = Depends(current_user)) -> None:
    """With an internal token configured, only the public website process (token) or a signed-in user may call these.
    Without one (single-process setups, development) the routes are public by design."""
    if user or not settings.internal_token:
        return
    given = request.headers.get("x-internal-token", "")
    if not hmac.compare_digest(given.encode(), settings.internal_token.encode()):
        raise HTTPException(status_code=404, detail="Not found")


router = APIRouter(prefix="/api/quick", tags=["quick"], dependencies=[Depends(internal_or_user)])


def _ctx(session: Session) -> PricingContext:
    return PricingContext(load_catalog(session), load_config(session), company_profile(session, get_settings()))


def _log_estimate(row: QuickEstimateLog) -> None:
    """Written after the response is sent, so the visitor never waits on the database."""
    try:
        with Session(get_engine()) as s:
            s.add(row)
            s.commit()
    except Exception as e:  # noqa: BLE001 - a lost count must not matter
        logging.getLogger(__name__).warning("estimate not logged: %s", e)


TOWNS_PER_HOUR = 120   # province picks per browser per hour; a visitor changes province a handful of times


@router.get("/towns")
def quick_towns(request: Request, province: str = "") -> list[dict]:
    """One province's cities and municipalities for the picker (the whole country is 1,600 rows; a province is a few dozen)."""
    _throttle(request, TOWNS_PER_HOUR)
    return towns_payload(province)


@router.get("/place")
def quick_place(request: Request, lat: float, lon: float) -> dict:
    """The town nearest a phone's location, so the picker can fill itself in; off the map past OUT_OF_AREA_KM."""
    _throttle(request, TOWNS_PER_HOUR)
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise HTTPException(status_code=422, detail="lat/lon out of range")
    t, km = nearest_town(lat, lon)
    inside = km <= OUT_OF_AREA_KM
    return {"town": t[0] if inside else "", "province": t[1] if inside else "", "km": round(km, 1), "inside": inside}


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
        "provinces": provinces(),        # the picker loads one province's towns on demand (/api/quick/towns)
        "public_url": settings.public_url,
        "estimate_url": settings.estimate_url,
        "proposal_valid_days": cfg.job.quotation_validity_days,   # the thank-you page's "valid N days" is the pricing setting
    }


@router.post("/estimate")
def estimate(body: QuickRequest, request: Request, tasks: BackgroundTasks, session: Session = Depends(get_session), pvgis: PvgisDataset = Depends(get_pvgis)) -> dict:
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
    tasks.add_task(_log_estimate, QuickEstimateLog(
        goal=body.goal, pattern=body.pattern, monthly_kwh=float(out["inputs"]["monthly_kwh"]), town=out["inputs"]["town"],
        lat=round(float(out["inputs"]["lat"]), 2), lon=round(float(out["inputs"]["lon"]), 2),  # a town, not a house
        panels=int(out["system"]["panels"]), kwp=float(out["system"]["kwp"]),
        battery_kwh=float(out["system"]["battery_kwh"]), price=float(out["price"]["total"]), source=src.split("/")[0], campaign=src.split("/", 1)[1] if "/" in src else "",
        visitor=(request.headers.get("x-visitor") or "")[:64],
    ))
    return out


@router.post("/lead")
def lead(body: QuickLead, request: Request, tasks: BackgroundTasks, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> dict:
    """Keep the visitor's details as a booking (not a project), with the four answers and what they saw."""
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
    # the snapshot also keeps what the visitor typed, so "Start project" can prefill the first bill
    snapshot = est.model_copy(update={"goal": est.goal or body.goal, "monthly_kwh": float(kwh) if kwh else None, "monthly_php": body.monthly_php, "pattern": body.pattern})
    pin = not body.town  # a pin from the phone's location; a listed town carries no pin (the town centre is looked up when needed)
    row = Lead(
        name=body.name.strip(), contact=body.contact.strip(), town=where["town"], province=where["province"], address=body.address.strip(),
        lat=where["lat"] if pin else None, lon=where["lon"] if pin else None, preferred_time=body.preferred_time, consent=body.consent,
        notice_version=body.notice_version, source=body.source.model_dump(mode="json"), estimate=snapshot.model_dump(mode="json"), notes=notes, status="new",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    log.info("lead created id=%s ip=%s source=%s", row.id, client_ip(request), _source_label(body.source))
    if smtp_configured(settings):
        link = f"{settings.public_url.rstrip('/')}/?booking={row.id}" if settings.public_url else f"booking #{row.id}"
        promise = (company_profile(session, settings).get("callback_promise") or "").strip() or "within one working day"
        subject, text = lead_notice(
            name=row.name, contact=row.contact, preferred_time=body.preferred_time, wants=wants, uses=PATTERN_LABEL[body.pattern],
            kwh=float(kwh), monthly_php=body.monthly_php, estimate=est, place=where["label"], pin_placed=pin, address=body.address.strip(),
            source=_source_label(body.source), link=link, promise=promise,
        )
        tasks.add_task(send_lead_notice, settings, subject, text)
    return {"ok": True, "id": row.id, "goal_label": GOAL_LABEL[body.goal]}
