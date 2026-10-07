"""Customer-facing PDF: only what the customer cares about."""
from __future__ import annotations

import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from ..schemas import AssessmentDoc  # noqa: E402

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(azimuth: float) -> str:
    return COMPASS[int(((azimuth % 360) + 11.25) // 22.5) % 16]


def _chart(monthly: list[float]) -> Image:
    fig, ax = plt.subplots(figsize=(6.6, 2.6), dpi=150)
    ax.bar(MONTHS, monthly, color="#2b7a78")
    ax.set_ylabel("kWh per month")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    for i, v in enumerate(monthly):
        ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=6)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=170 * mm, height=67 * mm)


def build_customer_pdf(doc: AssessmentDoc, results: dict, company: dict, stale: bool = False) -> bytes:
    prod = results["production"]
    panel = next(p["panel"] for p in results["panels"] if p["panel"]["id"] == results["selected_panel_id"])
    selected = next(p for p in results["panels"] if p["panel"]["id"] == results["selected_panel_id"])

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Solar roof assessment", author=company.get("company_name", ""))
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], textColor=colors.HexColor("#555555"), fontSize=9)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#555555"))

    story = []
    story.append(Paragraph(company.get("company_name") or "Solar roof assessment", h1))
    if company.get("company_contact"):
        story.append(Paragraph(company["company_contact"], sub))
    story.append(Paragraph("Solar roof assessment", h2))
    when = datetime.now().strftime("%d %b %Y")
    story.append(Paragraph(f"Prepared for <b>{doc.customer_name or '-'}</b> on {when}", body))
    if doc.address:
        story.append(Paragraph(doc.address, body))
    story.append(Paragraph(f"Site coordinates: {doc.lat:.5f}, {doc.lon:.5f}", small))
    story.append(Spacer(1, 6))

    kpi = [
        ["Panels", f"{prod['total_panels']} x {panel['watt_peak']:.0f} W"],
        ["Panel model", panel.get("name") or "-"],
        ["System size", f"{prod['system_kwp']:.2f} kWp"],
        ["Estimated production per year", f"{prod['annual_kwh']:,.0f} kWh"],
        ["Average per month", f"{prod['avg_monthly_kwh']:,.0f} kWh"],
    ]
    t = Table(kpi, colWidths=[70 * mm, 100 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#444444")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#dddddd")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    story.append(Paragraph("Expected monthly production", h2))
    story.append(_chart(prod["monthly_kwh"]))
    rows = [["Month"] + MONTHS + ["Year"]]
    rows.append(["kWh"] + [f"{v:,.0f}" for v in prod["monthly_kwh"]] + [f"{prod['annual_kwh']:,.0f}"])
    mt = Table(rows, colWidths=[14 * mm] + [11.5 * mm] * 12 + [18 * mm])
    mt.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f3")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (-1, 1), (-1, 1), "Helvetica-Bold"),
    ]))
    story.append(mt)

    story.append(Paragraph("Roof", h2))
    face_rows = [["Roof face", "Size (m)", "Tilt", "Facing", "Panels"]]
    for f in doc.faces:
        cnt = selected["faces"][f.id]["count"]
        face_rows.append([f.name, f"{f.length_m:g} x {f.width_m:g}", f"{f.tilt_deg:g} deg", f"{compass(f.azimuth_deg)} ({f.azimuth_deg:g} deg)", str(cnt)])
    ft = Table(face_rows, colWidths=[50 * mm, 35 * mm, 25 * mm, 40 * mm, 20 * mm])
    ft.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f3")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")),
        ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
    ]))
    story.append(ft)

    story.append(Paragraph("About this estimate", h2))
    notes = [
        "Production is estimated hour by hour over a typical weather year for this location (PVGIS data) and the roof's tilt and facing.",
    ]
    if results["k"]["source"] == "measured":
        notes.append("The estimate is adjusted with measurements taken on your roof with a calibrated test panel, irradiance meter and MPPT meter.")
    else:
        notes.append("This is a preliminary estimate prepared before on-site measurement. Figures will be refined after the roof visit.")
    notes.append("Figures are production at the solar panels for a typical year. Actual weather varies from year to year.")
    if stale:
        notes.append("Note: inputs were edited after this calculation.")
    for n in notes:
        story.append(Paragraph(n, small))

    pdf.build(story)
    return buf.getvalue()
