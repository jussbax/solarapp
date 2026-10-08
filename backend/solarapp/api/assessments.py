from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from ..auth import require_user
from ..compute import ComputeError, compute_results
from ..config import Settings, get_settings
from ..core.dataset import NasaReference, PvgisDataset
from ..db import get_session
from ..models import Assessment, utcnow
from ..pricing.job import PricingContext
from ..pricing.store import load_catalog, load_config
from ..reports.card import build_client_card
from ..reports.customer_pdf import build_customer_pdf
from ..reports.program_pdf import build_program_pdf
from ..reports.quotation_pdf import build_quotation_pdf
from ..schemas import AssessmentDoc, AssessmentOut, AssessmentSummary
from .appliances import remember_appliances
from .deps import get_nasa, get_pvgis
from .settings_routes import company_settings

router = APIRouter(prefix="/api/assessments", tags=["assessments"], dependencies=[Depends(require_user)])


def _get(session: Session, assessment_id: int) -> Assessment:
    a = session.get(Assessment, assessment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return a


def _out(a: Assessment) -> AssessmentOut:
    return AssessmentOut(
        id=a.id, created_at=a.created_at, updated_at=a.updated_at,
        doc=AssessmentDoc.model_validate(a.doc), results=a.results, results_stale=a.results_stale,
    )


@router.get("", response_model=list[AssessmentSummary])
def list_assessments(session: Session = Depends(get_session)) -> list[AssessmentSummary]:
    rows = session.exec(select(Assessment).order_by(Assessment.updated_at.desc())).all()
    out = []
    for a in rows:
        prod = (a.results or {}).get("production") or {}
        sizing = (a.results or {}).get("sizing") or {}
        if sizing:  # the sized system rather than the roof maximum
            prod = {"system_kwp": sizing.get("kwp"), "annual_kwh": sizing.get("annual_production_kwh"), "total_panels": sizing.get("panels")}
        pricing = (a.results or {}).get("pricing") or {}
        out.append(AssessmentSummary(
            id=a.id, created_at=a.created_at, updated_at=a.updated_at, customer_name=a.customer_name,
            address=a.address, has_results=a.results is not None, results_stale=a.results_stale,
            stage=((a.doc or {}).get("program") or {}).get("stage", "assessed"),
            contract_php=(pricing.get("totals") or {}).get("contract_rounded") if pricing.get("available") else None,
            system_kwp=prod.get("system_kwp"), annual_kwh=prod.get("annual_kwh"), panel_count=prod.get("total_panels"),
        ))
    return out


@router.post("", response_model=AssessmentOut, status_code=201)
def create_assessment(doc: AssessmentDoc, session: Session = Depends(get_session)) -> AssessmentOut:
    a = Assessment(customer_name=doc.customer_name, address=doc.address, doc=doc.model_dump(mode="json"))
    session.add(a)
    session.commit()
    session.refresh(a)
    return _out(a)


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(assessment_id: int, session: Session = Depends(get_session)) -> AssessmentOut:
    return _out(_get(session, assessment_id))


@router.put("/{assessment_id}", response_model=AssessmentOut)
def update_assessment(assessment_id: int, doc: AssessmentDoc, session: Session = Depends(get_session)) -> AssessmentOut:
    a = _get(session, assessment_id)
    new_doc = doc.model_dump(mode="json")
    if new_doc != a.doc:
        a.doc = new_doc
        a.customer_name, a.address = doc.customer_name, doc.address
        a.results_stale = a.results is not None
        a.updated_at = utcnow()
        session.add(a)
        session.commit()
        session.refresh(a)
        remember_appliances(session, doc)
    return _out(a)


@router.delete("/{assessment_id}", status_code=204)
def delete_assessment(assessment_id: int, session: Session = Depends(get_session)) -> Response:
    a = _get(session, assessment_id)
    session.delete(a)
    session.commit()
    return Response(status_code=204)


@router.post("/{assessment_id}/compute", response_model=AssessmentOut)
def compute_assessment(
    assessment_id: int,
    doc: Optional[AssessmentDoc] = None,
    session: Session = Depends(get_session),
    pvgis: PvgisDataset = Depends(get_pvgis),
    nasa: NasaReference = Depends(get_nasa),
) -> AssessmentOut:
    """Save the document (if sent) and compute results."""
    a = _get(session, assessment_id)
    if doc is not None:
        a.doc = doc.model_dump(mode="json")
        a.customer_name, a.address = doc.customer_name, doc.address
    parsed = AssessmentDoc.model_validate(a.doc)
    ctx = PricingContext(load_catalog(session), load_config(session))
    try:
        a.results = compute_results(parsed, pvgis, nasa, ctx)
    except ComputeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    a.results_stale = False
    a.updated_at = utcnow()
    session.add(a)
    session.commit()
    session.refresh(a)
    remember_appliances(session, parsed)
    return _out(a)


@router.get("/{assessment_id}/report.pdf")
def customer_report(
    assessment_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    a = _get(session, assessment_id)
    if not a.results:
        raise HTTPException(status_code=409, detail="Compute the assessment first.")
    if (a.results.get("dataset") or {}).get("synthetic"):
        raise HTTPException(status_code=409, detail="Customer PDF is disabled while synthetic test data is in use.")
    company = company_settings(session, settings)
    pdf = build_customer_pdf(AssessmentDoc.model_validate(a.doc), a.results, company, stale=a.results_stale)
    name = (a.customer_name or f"assessment-{a.id}").strip().replace(" ", "_")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="solar-assessment-{name}.pdf"'})


@router.get("/{assessment_id}/quotation.pdf")
def customer_quotation(
    assessment_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    a = _get(session, assessment_id)
    pricing = (a.results or {}).get("pricing") or {}
    if not pricing.get("available"):
        raise HTTPException(status_code=409, detail="Compute the assessment with pricing first.")
    if a.results_stale:
        raise HTTPException(status_code=409, detail="Inputs changed since the last compute. Save and compute again first.")
    company = company_settings(session, settings)
    pdf = build_quotation_pdf(AssessmentDoc.model_validate(a.doc), a.results, company, proposal_no=f"P-{a.created_at.year}-{a.id:04d}")
    name = (a.customer_name or f"assessment-{a.id}").strip().replace(" ", "_")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="solar-quotation-{name}.pdf"'})


@router.get("/{assessment_id}/program.pdf")
def program_of_works(
    assessment_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    a = _get(session, assessment_id)
    program = (a.results or {}).get("program") or {}
    if not program.get("available"):
        raise HTTPException(status_code=409, detail="Compute the assessment with pricing first.")
    company = company_settings(session, settings)
    pdf = build_program_pdf(AssessmentDoc.model_validate(a.doc), a.results, company)
    name = (a.customer_name or f"assessment-{a.id}").strip().replace(" ", "_")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="program-of-works-{name}.pdf"'})


@router.get("/{assessment_id}/card.png")
def client_card(
    assessment_id: int,
    next_step: str = "",
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Phone-sized image of the roof check result for the customer."""
    a = _get(session, assessment_id)
    if not a.results:
        raise HTTPException(status_code=409, detail="Compute the assessment first.")
    if (a.results.get("dataset") or {}).get("synthetic"):
        raise HTTPException(status_code=409, detail="The client card is disabled while synthetic test data is in use.")
    company = company_settings(session, settings)
    png = build_client_card(AssessmentDoc.model_validate(a.doc), a.results, company, next_step=next_step[:120])
    name = (a.customer_name or f"assessment-{a.id}").strip().replace(" ", "_")
    return Response(png, media_type="image/png", headers={"Content-Disposition": f'inline; filename="roof-check-{name}.png"'})
