"""Website bookings: the CRM's data, kept apart from the project list.

A booking (lead) is not a project. The engineering app shows only the open
ones on its Projects page and starts a project from one (convert): the
customer reference, the pin or town and the bill are copied, and ``lead_id``
on the project is the only link. The statuses, notes, closing reasons and
the funnel counters served here are for the CRM, which takes this router
and the ``leads`` table over; no engineering screen depends on them.
"""
from __future__ import annotations

import copy
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import ValidationError
from sqlalchemy import func
from sqlmodel import Session, select

from ..auth import require_owner, require_user
from ..core.towns import find_town
from ..db import get_session
from ..models import Assessment, Lead, QuickEstimateLog, utcnow
from ..schemas import (
    JOB_STAGES, LEAD_STATUSES, LEGACY_LEAD_STAGES, AssessmentDoc, BillEntry, EnergyAudit, LeadConvertOut, LeadEstimate, LeadFunnel, LeadInfo,
    LeadOut, LeadPatch, LeadSource, ProgramJob,
)

log = logging.getLogger("solarapp.audit")

OUT_OF_AREA = "outside Laguna and Batangas"   # the label the estimate gives a pin far from every listed town
SYSTEM_KINDS = ("off_grid", "net_metering", "combination")

router = APIRouter(prefix="/api/leads", tags=["leads"], dependencies=[Depends(require_user)])


# ---- labels shared with the website route

def source_label(src: LeadSource | dict) -> str:
    """"fb/brownout1" for a tagged link, the referrer's host, or "direct"."""
    if isinstance(src, dict):
        src = LeadSource.model_validate(src)
    if src.utm_source:
        return src.utm_source + (f"/{src.utm_campaign}" if src.utm_campaign else "")
    if src.referrer:
        host = urlparse(src.referrer).netloc
        return host or "referral"
    return "direct"


def place_label(town: str, province: str, lat: Optional[float]) -> str:
    """"Pila, Laguna" for a listed town; "near Pila, Laguna" for a pin in the area; the out-of-area text for a far pin."""
    if town:
        name = f"{town}, {province}" if province else town
        return f"near {name}" if lat is not None else name
    return OUT_OF_AREA if lat is not None else ""


def lead_out(lead: Lead) -> LeadOut:
    try:
        est = LeadEstimate.model_validate(lead.estimate or {})
    except ValidationError:
        est = LeadEstimate()
    src = LeadSource.model_validate(lead.source or {})
    return LeadOut(
        id=lead.id, created_at=lead.created_at, updated_at=lead.updated_at, name=lead.name, contact=lead.contact,
        town=lead.town, province=lead.province, place=place_label(lead.town, lead.province, lead.lat), address=lead.address,
        lat=lead.lat, lon=lead.lon, preferred_time=lead.preferred_time, consent=lead.consent, notice_version=lead.notice_version,
        source=src, source_label=source_label(src), estimate=est, notes=lead.notes, status=lead.status,
        project_id=lead.project_id, closed_reason=lead.closed_reason, anonymised=lead.anonymised_at is not None,
    )


def _get(session: Session, lead_id: int) -> Lead:
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


# ---- the bookings: owner-only, except the open list and the conversion

@router.get("", response_model=list[LeadOut], dependencies=[Depends(require_owner)])
def list_leads(status: Optional[str] = None, q: str = "", limit: int = 500, session: Session = Depends(get_session)) -> list[LeadOut]:
    """Newest first. ``status`` narrows to one status; ``q`` searches name, contact, town, address and notes."""
    stmt = select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc())
    if status:
        if status not in LEAD_STATUSES:
            raise HTTPException(status_code=422, detail=f"Status must be one of {', '.join(LEAD_STATUSES)}.")
        stmt = stmt.where(Lead.status == status)
    rows = session.exec(stmt).all()
    needle = q.strip().lower()
    if needle:
        rows = [r for r in rows if needle in f"{r.name} {r.contact} {r.town} {r.province} {r.address} {r.notes}".lower()]
    return [lead_out(r) for r in rows[: max(1, min(int(limit), 5000))]]


@router.get("/open", response_model=list[LeadOut])
def open_bookings(session: Session = Depends(get_session)) -> list[LeadOut]:
    """The hand-off list for the engineering app: bookings that have no project yet and were not closed, newest first.
    Anyone signed in may start a project from one; everything else about a booking is the owner's (the CRM's)."""
    stmt = select(Lead).where(Lead.status.in_(("new", "contacted", "visit_booked")), Lead.anonymised_at == None).order_by(Lead.created_at.desc(), Lead.id.desc())  # noqa: E711
    return [lead_out(r) for r in session.exec(stmt).all()]


STAGE_RANK = {s: i for i, s in enumerate(JOB_STAGES)}


@router.get("/funnel", response_model=LeadFunnel, dependencies=[Depends(require_owner)])
def funnel(days: int = 30, session: Session = Depends(get_session)) -> LeadFunnel:
    """The last N days: estimates run (estimate log), leads, visits booked and converted (inbox), quoted and signed (projects by stage)."""
    days = max(1, min(int(days), 3650))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    estimates = session.exec(select(QuickEstimateLog).where(QuickEstimateLog.created_at >= since)).all()
    leads = session.exec(select(Lead).where(Lead.created_at >= since)).all()
    projects = session.exec(select(Assessment).where(Assessment.created_at >= since)).all()

    def rank(a: Assessment) -> int:
        return STAGE_RANK.get(((a.doc or {}).get("program") or {}).get("stage", "assessed"), 0)

    by_source: dict[str, int] = {}
    for e in estimates:
        by_source[e.source or "direct"] = by_source.get(e.source or "direct", 0) + 1
    return LeadFunnel(
        days=days, estimates=len(estimates), leads=len(leads),
        visits_booked=sum(1 for l in leads if l.status in ("visit_booked", "converted")),
        converted=sum(1 for l in leads if l.status == "converted"),
        quoted=sum(1 for a in projects if rank(a) >= STAGE_RANK["quoted"]),
        signed=sum(1 for a in projects if rank(a) >= STAGE_RANK["signed"]),
        estimates_by_source=by_source,
    )


@router.get("/{lead_id}", response_model=LeadOut, dependencies=[Depends(require_owner)])
def get_lead(lead_id: int, session: Session = Depends(get_session)) -> LeadOut:
    return lead_out(_get(session, lead_id))


@router.patch("/{lead_id}", response_model=LeadOut, dependencies=[Depends(require_owner)])
def update_lead(lead_id: int, body: LeadPatch, session: Session = Depends(get_session)) -> LeadOut:
    lead = _get(session, lead_id)
    if body.closed_reason is not None:
        lead.closed_reason = body.closed_reason.strip()
    if body.status is not None and body.status != lead.status:
        if body.status == "converted" and lead.project_id is None:
            raise HTTPException(status_code=409, detail="Use Start project to turn a booking into a project.")
        log.info("lead status id=%s %s -> %s%s", lead.id, lead.status, body.status, f" reason={lead.closed_reason!r}" if body.status == "closed" and lead.closed_reason else "")
        lead.status = body.status
        if body.status != "closed" and body.closed_reason is None:
            lead.closed_reason = ""
    if body.notes is not None:
        lead.notes = body.notes.strip()
    lead.updated_at = utcnow()
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead_out(lead)


@router.delete("/{lead_id}", status_code=204, dependencies=[Depends(require_owner)])
def delete_lead(lead_id: int, session: Session = Depends(get_session)) -> Response:
    lead = _get(session, lead_id)
    session.delete(lead)
    session.commit()
    log.info("lead deleted id=%s", lead_id)
    return Response(status_code=204)


def project_from_lead(lead: Lead) -> AssessmentDoc:
    """The engineering project a lead starts: customer reference, pin or town, the bill the visitor typed, the notes, and the estimate they saw."""
    try:
        est = LeadEstimate.model_validate(lead.estimate or {})
    except ValidationError:
        est = LeadEstimate()
    lat, lon = lead.lat, lead.lon
    if lat is None and lead.town:
        t = find_town(lead.town, lead.province)
        if t is not None:
            lat, lon = t[2], t[3]
    bills = []
    if est.monthly_kwh:
        bills.append(BillEntry(id="lead", billing_month=lead.created_at.strftime("%Y-%m"), kwh=float(est.monthly_kwh), amount_php=est.monthly_php))
    kind = est.goal if est.goal in SYSTEM_KINDS else "combination"
    # without a pin the town is the only location, so a landmark keeps it ("Brgy. Labuin, near the chapel, Pila, Laguna")
    # unless the visitor typed the town already; with a pin the address stays as typed (the pin is the house)
    place = place_label(lead.town, lead.province, None) if lead.lat is None else ""
    landmark = lead.address.strip()
    address = landmark if (not place or (lead.town and lead.town.lower() in landmark.lower())) else ", ".join(x for x in (landmark, place) if x)
    return AssessmentDoc(
        customer_name=lead.name.strip(), address=address, notes=lead.notes,
        lat=lat, lon=lon, audit=EnergyAudit(bills=bills, system={"kind": kind}), program=ProgramJob(stage="assessed"),
        # the proposal and the card print "your website estimate was ..." from this; the contact and the source stay on the lead
        lead=LeadInfo(created_at=lead.created_at.isoformat(), estimate=est) if est.price else None,
        lead_id=lead.id,
    )


@router.post("/{lead_id}/convert", response_model=LeadConvertOut)
def convert_lead(lead_id: int, session: Session = Depends(get_session)) -> LeadConvertOut:
    """Start project: create the project from the booking and mark it converted. Calling it again returns the same project."""
    lead = _get(session, lead_id)
    if lead.project_id is not None and session.get(Assessment, lead.project_id) is not None:
        return LeadConvertOut(project_id=lead.project_id, lead=lead_out(lead))
    if lead.anonymised_at is not None:
        raise HTTPException(status_code=409, detail="This lead was anonymised under the retention schedule; there is nothing left to start from.")
    doc = project_from_lead(lead)
    a = Assessment(customer_name=doc.customer_name, address=doc.address, doc=doc.model_dump(mode="json"))
    session.add(a)
    session.commit()
    session.refresh(a)
    lead.status = "converted"
    lead.project_id = a.id
    lead.closed_reason = ""
    lead.updated_at = utcnow()
    session.add(lead)
    session.commit()
    session.refresh(lead)
    log.info("lead converted id=%s project_id=%s", lead.id, a.id)
    return LeadConvertOut(project_id=a.id, lead=lead_out(lead))


# ---- startup migration: lead-stage assessments saved before bookings had their own table

def _parse_place(label: str) -> tuple[str, str, bool]:
    """The old LeadInfo.town label -> (town, province, keep the pin). "near Pila, Laguna" keeps the visitor's pin; "Pila, Laguna" was the town centre."""
    label = (label or "").strip()
    if not label:
        return "", "", False
    if label.startswith("near "):
        town, _, province = label[5:].partition(",")
        return town.strip(), province.strip(), True
    if "," in label:
        town, _, province = label.partition(",")
        return town.strip(), province.strip(), False
    return ("", "", True) if label == OUT_OF_AREA else (label, "", False)


def lead_from_legacy_assessment(a: Assessment) -> Lead:
    doc = a.doc or {}
    info = doc.get("lead") or {}
    stage = (doc.get("program") or {}).get("stage")
    town, province, keep_pin = _parse_place(info.get("town") or "")
    est = dict(info.get("estimate") or {})
    bills = (doc.get("audit") or {}).get("bills") or []
    if bills and est.get("monthly_kwh") is None:
        est["monthly_kwh"] = bills[0].get("kwh") or None
        est["monthly_php"] = bills[0].get("amount_php")
    kind = ((doc.get("audit") or {}).get("system") or {}).get("kind")
    if kind and not est.get("goal"):
        est["goal"] = kind
    try:
        est = LeadEstimate.model_validate(est).model_dump(mode="json")
    except ValidationError:
        pass
    lat = doc.get("lat") if keep_pin else None
    lon = doc.get("lon") if keep_pin else None
    label = (info.get("town") or "").strip()
    address = (doc.get("address") or "").strip()
    if address and address in (label, label.removeprefix("near ")):
        address = ""  # the old route wrote the town label as the address when the visitor gave none; the town fields carry it now
    return Lead(
        created_at=a.created_at, updated_at=a.updated_at, name=a.customer_name or doc.get("customer_name") or "", contact=info.get("contact") or "",
        town=town, province=province, address=address, lat=lat, lon=lon, preferred_time=info.get("preferred_time") or "",
        consent=bool(info.get("consent")), notice_version=info.get("notice_version") or "", source=info.get("source") or {}, estimate=est,
        notes=doc.get("notes") or "", status="contacted" if stage == "contacted" else "new",
        anonymised_at=a.updated_at if doc.get("anonymised") else None,
    )


def migrate_lead_assessments(session: Session) -> dict:
    """Idempotent, run at startup. An assessment at stage "lead" or "contacted" with no results becomes a Lead and is deleted;
    one with results keeps its data and becomes a project at stage "assessed". Every other record is untouched."""
    stage_of = func.json_extract(Assessment.doc, "$.program.stage")
    rows = session.exec(select(Assessment).where(stage_of.in_(LEGACY_LEAD_STAGES))).all()
    moved = kept = 0
    for a in rows:
        if a.results is None:
            session.add(lead_from_legacy_assessment(a))
            session.delete(a)
            moved += 1
        else:
            doc = copy.deepcopy(a.doc or {})  # a new object, so the JSON column is seen as changed
            doc.setdefault("program", {})["stage"] = "assessed"
            a.doc = doc
            session.add(a)
            kept += 1
    session.commit()
    if moved or kept:
        log.info("lead migration: %s lead-stage assessments moved to the bookings table, %s with results kept as projects at stage assessed", moved, kept)
    return {"moved": moved, "kept": kept}
