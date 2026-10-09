from __future__ import annotations

from typing import Optional

import logging
import re
import unicodedata
from urllib.parse import quote

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
from ..reports.quotation_pdf import build_quotation_pdf, customer_battery_kwh
from ..schemas import JOB_STAGES, AssessmentDoc, AssessmentOut, AssessmentSummary
from .appliances import remember_appliances
from .deps import get_nasa, get_pvgis
from .settings_routes import company_settings

log = logging.getLogger("solarapp.audit")


def _download_name(prefix: str, a: Assessment, ext: str, inline: bool = False) -> dict:
    """A Content-Disposition that survives quotes and non-Latin names (customer names come from the public form)."""
    raw = (a.customer_name or f"assessment-{a.id}").strip()
    ascii_name = re.sub(r"[^A-Za-z0-9_-]+", "_", unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()).strip("_")[:60] or f"assessment-{a.id}"
    kind = "inline" if inline else "attachment"
    return {"Content-Disposition": f"{kind}; filename=\"{prefix}-{ascii_name}.{ext}\"; filename*=UTF-8''{quote(f'{prefix}-{raw}.{ext}')}"}


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
    """The project list: engineering facts only. The lead's contact, source and what they saw live on the leads inbox (/api/leads)."""
    rows = session.exec(select(Assessment).order_by(Assessment.updated_at.desc())).all()
    out = []
    for a in rows:
        results = a.results or {}
        prod = results.get("production") or {}
        sizing = results.get("sizing") or {}
        if sizing:  # the sized system rather than the roof maximum
            prod = {"system_kwp": sizing.get("kwp"), "annual_kwh": sizing.get("annual_production_kwh"), "total_panels": sizing.get("panels")}
        pricing = results.get("pricing") or {}
        doc = a.doc or {}
        battery = None
        if sizing and (sizing.get("kind") or "") != "net_metering":
            try:
                battery = customer_battery_kwh(pricing if pricing.get("available") else {}, sizing) or None
            except (KeyError, TypeError, ValueError):
                battery = None
        stage = (doc.get("program") or {}).get("stage", "assessed")
        out.append(AssessmentSummary(
            id=a.id, created_at=a.created_at, updated_at=a.updated_at, customer_name=a.customer_name,
            address=a.address, has_results=a.results is not None, results_stale=a.results_stale,
            stage=stage if stage in JOB_STAGES else "assessed",
            contract_php=(pricing.get("totals") or {}).get("contract_rounded") if pricing.get("available") else None,
            system_kwp=prod.get("system_kwp"), annual_kwh=prod.get("annual_kwh"), panel_count=prod.get("total_panels"),
            kind=((doc.get("audit") or {}).get("system") or {}).get("kind"),
            face_count=len(doc.get("faces") or []), battery_kwh=battery, computed_at=results.get("computed_at") if a.results else None,
            lead_id=doc.get("lead_id"),
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
        # the card's next-step line is printed, never computed: changing it leaves the results fresh
        affects_results = {k: v for k, v in new_doc.items() if k != "card_next_step"} != {k: v for k, v in (a.doc or {}).items() if k != "card_next_step"}
        a.doc = new_doc
        a.customer_name, a.address = doc.customer_name, doc.address
        if affects_results:
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
    log.info("assessment deleted id=%s", assessment_id)
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


STALE_DETAIL = "Inputs changed since the last calculation. Calculate again first."


def _fresh_results(a: Assessment) -> dict:
    """The one stale rule for every document: results must exist and match the saved inputs."""
    if not a.results:
        raise HTTPException(status_code=409, detail="Calculate first.")
    if a.results_stale:
        raise HTTPException(status_code=409, detail=STALE_DETAIL)
    return a.results


@router.get("/{assessment_id}/report.pdf")
def customer_report(
    assessment_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    a = _get(session, assessment_id)
    results = _fresh_results(a)
    if (results.get("dataset") or {}).get("synthetic"):
        raise HTTPException(status_code=409, detail="Customer documents are disabled while test weather data is in use.")
    company = company_settings(session, settings)
    pdf = build_customer_pdf(AssessmentDoc.model_validate(a.doc), results, company)
    return Response(pdf, media_type="application/pdf", headers=_download_name("roof-check", a, "pdf"))


@router.get("/{assessment_id}/quotation.pdf")
def customer_quotation(
    assessment_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    a = _get(session, assessment_id)
    results = _fresh_results(a)
    if (results.get("dataset") or {}).get("synthetic"):
        raise HTTPException(status_code=409, detail="Customer documents are disabled while test weather data is in use.")
    if not (results.get("pricing") or {}).get("available"):
        raise HTTPException(status_code=409, detail="Calculate first. Pricing needs the panel linked to the materials list.")
    company = company_settings(session, settings)
    pdf = build_quotation_pdf(AssessmentDoc.model_validate(a.doc), results, company, proposal_no=f"P-{a.created_at.year}-{a.id:04d}",
                              outage_hours=load_config(session).program.installation_outage_hours)
    return Response(pdf, media_type="application/pdf", headers=_download_name("proposal", a, "pdf"))


@router.get("/{assessment_id}/program.pdf")
def program_of_works(
    assessment_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    a = _get(session, assessment_id)
    results = _fresh_results(a)
    if not (results.get("program") or {}).get("available"):
        raise HTTPException(status_code=409, detail="Calculate first. Pricing needs the panel linked to the materials list.")
    company = company_settings(session, settings)
    pdf = build_program_pdf(AssessmentDoc.model_validate(a.doc), results, company)
    return Response(pdf, media_type="application/pdf", headers=_download_name("program-of-works", a, "pdf"))


@router.get("/{assessment_id}/card.png")
def client_card(
    assessment_id: int,
    next_step: Optional[str] = None,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Phone-sized image of the roof check result for the customer. The next step comes from the query
    string when given, else from the record's saved card_next_step."""
    a = _get(session, assessment_id)
    results = _fresh_results(a)
    if (results.get("dataset") or {}).get("synthetic"):
        raise HTTPException(status_code=409, detail="The card is disabled while test weather data is in use.")
    company = company_settings(session, settings)
    doc = AssessmentDoc.model_validate(a.doc)
    step = doc.card_next_step if next_step is None else next_step
    png = build_client_card(doc, results, company, next_step=step[:120], public_url=settings.estimate_url)
    return Response(png, media_type="image/png", headers=_download_name("roof-check", a, "png", inline=True))


# ---- bill of materials export: the generated list with the owner's edits, as the pricing results hold it

BOM_COLUMNS = ["code", "item", "supplier", "qty", "unit", "role", "note"]


def _bom_rows(a: Assessment) -> list[list]:
    """One row per BOM line (code, item, supplier, qty, unit, role, note); the one stale rule applies, and a record
    without priced results is refused the same way the proposal is."""
    results = _fresh_results(a)
    pricing = results.get("pricing") or {}
    if not pricing.get("available"):
        raise HTTPException(status_code=409, detail="Calculate first. Pricing needs the panel linked to the materials list.")
    rows: list[list] = []
    for l in pricing.get("lines") or []:
        qty = float(l.get("qty") or 0)
        rows.append([
            l.get("code") or "", l.get("name") or ("" if l.get("found", True) else "not in the materials list"), l.get("supplier") or "",
            int(qty) if qty.is_integer() else round(qty, 2), l.get("unit") or "", l.get("role") or "", l.get("note") or "",
        ])
    return rows


@router.get("/{assessment_id}/bom.csv")
def bom_csv(assessment_id: int, session: Session = Depends(get_session)) -> Response:
    """The bill of materials as CSV (UTF-8 with a byte-order mark, so spreadsheets open it as typed)."""
    import csv
    import io

    a = _get(session, assessment_id)
    rows = _bom_rows(a)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(BOM_COLUMNS)
    w.writerows(rows)
    return Response(buf.getvalue().encode("utf-8-sig"), media_type="text/csv; charset=utf-8", headers=_download_name("bom", a, "csv"))


@router.get("/{assessment_id}/bom.xlsx")
def bom_xlsx(assessment_id: int, session: Session = Depends(get_session)) -> Response:
    """The bill of materials as a workbook: one sheet, a bold header, the columns sized to read."""
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    a = _get(session, assessment_id)
    rows = _bom_rows(a)
    wb = Workbook()
    ws = wb.active
    ws.title = "BOM"
    ws.append(BOM_COLUMNS)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="FAF4E1")
    for r in rows:
        ws.append(r)
    for i, width in enumerate([16, 44, 18, 8, 8, 16, 48], start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    for row in ws.iter_rows(min_row=2, min_col=4, max_col=4):
        for c in row:
            c.alignment = Alignment(horizontal="right")
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=_download_name("bom", a, "xlsx"))
