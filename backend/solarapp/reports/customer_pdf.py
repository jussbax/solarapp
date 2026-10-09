"""Your roof check: the customer's PDF after the roof visit. Only what the customer cares about."""
from __future__ import annotations

import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from xml.sax.saxutils import escape  # noqa: E402

from ..core.towns import nearest_town  # noqa: E402
from ..schemas import AssessmentDoc  # noqa: E402
from . import brand  # noqa: E402
from .card import estimate_line, reading_lines  # noqa: E402
from .drawings import plan_blocks  # noqa: E402
from .quotation_pdf import contact_line  # noqa: E402

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
COMPASS = ["North", "North-northeast", "Northeast", "East-northeast", "East", "East-southeast", "Southeast", "South-southeast", "South", "South-southwest", "Southwest", "West-southwest", "West", "West-northwest", "Northwest", "North-northwest"]


def compass(azimuth: float) -> str:
    return COMPASS[int(((azimuth % 360) + 11.25) // 22.5) % 16]


def pin_is_the_house(lat: float | None, lon: float | None) -> bool:
    """A website booking without a pin starts the project on the town centre; that pin is not the house and is not
    printed. A pin more than 50 m from every listed town centre was placed by someone."""
    if lat is None or lon is None:
        return False
    _, km = nearest_town(lat, lon)
    return km > 0.05


def panel_line(panel: dict, pricing: dict | None) -> str:
    """"585 W panel (Blue Carbon)": the rating and the supplier from the materials list, never the catalogue string."""
    wp = float(panel.get("watt_peak") or 0)
    supplier = next((l.get("supplier") for l in (pricing or {}).get("lines") or [] if l.get("category") == "Solar Panel" and l.get("supplier")), "")
    return f"{wp:.0f} W panel" + (f" ({supplier})" if supplier else "")


def _chart(monthly: list[float]) -> Image:
    fig, ax = plt.subplots(figsize=(6.6, 2.6), dpi=150)
    ax.bar(MONTHS, monthly, color=brand.C_GOLD)
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
    audit = results.get("audit") or {}
    bills = (audit.get("audit_vs_bill") or {}).get("bills") or []
    bill_kwh = float(bills[0]["kwh"]) if bills else None
    footer = contact_line(company)
    F, FS, FB = brand.fonts()

    def on_page(canvas, d) -> None:
        canvas.saveState()
        canvas.setFont(F, 6.5)
        canvas.setFillColor(brand.MUTED)
        canvas.drawString(18 * mm, 9 * mm, footer[:150])
        canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Roof check · page {d.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Your roof check", author=company.get("company_name", ""))
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontName=FB, fontSize=16, leading=19, spaceAfter=2, alignment=0, textColor=brand.BLACK)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontName=F, textColor=brand.MUTED, fontSize=8.5)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName=FB, fontSize=11.5, spaceBefore=10, spaceAfter=4, textColor=brand.BLACK)
    body = ParagraphStyle("body", parent=ss["Normal"], fontName=F, fontSize=9.5, leading=13, textColor=brand.GRAY)
    small = ParagraphStyle("small", parent=ss["Normal"], fontName=F, fontSize=8, leading=11, textColor=brand.MUTED)

    story = []
    left = [Paragraph(escape(company.get("company_name") or "Your roof check"), h1)]
    contact = company.get("company_contact") or contact_line({k: v for k, v in company.items() if k != "company_name"})
    if contact:
        left.append(Paragraph(escape(contact), sub))
    mark = brand.logo(14 * mm)
    head = Table([[mark or "", left]], colWidths=[18 * mm, 156 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 1.5, brand.GOLD), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    story.append(head)
    story.append(Paragraph("Your roof check", h2))
    when = datetime.now().strftime("%-d %b %Y")
    story.append(Paragraph(f"Prepared for <b>{escape(doc.customer_name or '-')}</b> on {when}", body))
    if doc.address:
        story.append(Paragraph(escape(doc.address), body))
    if pin_is_the_house(doc.lat, doc.lon):
        story.append(Paragraph(f"Map pin: {doc.lat:.5f}, {doc.lon:.5f}", small))
    story.append(Spacer(1, 6))

    # the customer's figures are at the meter (contract C2); the simulation's own figures stay at the panels
    annual_ac = float(prod.get("annual_kwh_ac") or prod["annual_kwh"])
    monthly_ac = [float(v) for v in (prod.get("monthly_kwh_ac") or prod["monthly_kwh"])]
    avg_ac = float(prod.get("avg_monthly_kwh_ac") or prod["avg_monthly_kwh"])
    loss = float(prod.get("loss_factor") or 1.0)
    kpi = [
        ["Panels your roof can hold", f"{prod['total_panels']} × {panel['watt_peak']:.0f} W"],
        ["Panel", panel_line(panel, results.get("pricing"))],
        ["System size", f"{prod['system_kwp']:.2f} kWp (the size of the solar array)"],
        ["Solar power made in a year", f"about {annual_ac:,.0f} kWh at your meter"],
        ["In a typical month", f"about {avg_ac:,.0f} kWh"],
    ]
    if bill_kwh:
        ratio = avg_ac / bill_kwh
        kpi.append(["Your bill shows", f"{bill_kwh:,.0f} kWh a month" + (f", so the full roof makes around {ratio:.1f} times what you use" if ratio >= 1.05 else f", about {ratio * 100:.0f}% of which the full roof can make")])
    key_style = ParagraphStyle("key", parent=body, fontSize=10, leading=13, textColor=brand.MUTED)
    val_style = ParagraphStyle("val", parent=body, fontName=FB, fontSize=10, leading=13, textColor=brand.GRAY)
    t = Table([[Paragraph(a, key_style), Paragraph(b, val_style)] for a, b in kpi], colWidths=[70 * mm, 100 * mm])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, brand.LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Paragraph("This is what the roof can hold. The system we propose after the energy audit is usually smaller, sized to your bill.", small))
    if estimate_line(doc):
        story.append(Paragraph(escape(estimate_line(doc)), small))   # the bridge from the website estimate, the same line as the card

    story.append(Paragraph("What your roof can make each month, at your meter", h2))
    story.append(_chart(monthly_ac))
    rows = [["Month"] + MONTHS + ["Year"]]
    rows.append(["kWh"] + [f"{v:,.0f}" for v in monthly_ac] + [f"{annual_ac:,.0f}"])
    mt = Table(rows, colWidths=[14 * mm] + [11.5 * mm] * 12 + [18 * mm])
    mt.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("FONTNAME", (0, 0), (-1, -1), F),
        ("BACKGROUND", (0, 0), (-1, 0), brand.OFF_WHITE),
        ("GRID", (0, 0), (-1, -1), 0.25, brand.LINE),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (-1, 1), (-1, 1), FB),
    ]))
    story.append(mt)

    story.append(Paragraph("Your roof", h2))
    face_rows = [["Roof face", "Size (m, eave × slope)", "Pitch", "Faces", "Panels"]]
    for f in doc.faces:
        cnt = selected["faces"][f.id]["count"]
        face_rows.append([escape(f.name), f"{f.length_m:g} × {f.width_m:g}", f"{f.tilt_deg:g}°", f"{compass(f.azimuth_deg)} ({f.azimuth_deg:g}°)", str(cnt)])
    ft = Table(face_rows, colWidths=[50 * mm, 40 * mm, 20 * mm, 40 * mm, 20 * mm])
    ft.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("FONTNAME", (0, 0), (-1, -1), F),
        ("BACKGROUND", (0, 0), (-1, 0), brand.OFF_WHITE),
        ("GRID", (0, 0), (-1, -1), 0.25, brand.LINE),
        ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
    ]))
    story.append(ft)

    # the plan of each face: the panels as they will sit, two faces to a row, each row with its captions
    caption = ParagraphStyle("caption", parent=body, fontSize=8.5, leading=11)
    plans = plan_blocks(results.get("geometry") or [], 174, caption, small, columns=2, max_height_mm=58)
    if plans:
        story.append(KeepTogether([Paragraph("Your roof, as the panels will sit", h2), plans[0]]))
        story += plans[1:]
        story.append(Paragraph("Panels are numbered from the eave up. The dashed line is the setback we keep from every edge; a hatched strip is shaded by a wall in the main hours, so no panels go there.", small))

    # the readings are the proof: the same lines the card prints
    story.append(Paragraph("Measured on your roof", h2))
    for line in reading_lines(results):
        story.append(Paragraph(escape(line), body))

    notes = [
        "We estimated production hour by hour for a typical year of weather at your location (PVGIS records), using your roof's pitch and direction.",
        "We adjusted it with readings taken on your roof: a test panel, a sunlight meter and a power meter.",
        (f"The figures are what reaches your meter: about {(1 - loss) * 100:.0f}% of what the panels make is lost in the inverter, the cables and dust on the panels. " if loss < 1 else "")
        + "They are for a typical year. Real weather varies, so some years will be higher and some lower.",
        "This is a roof check, not a quotation.",
    ]
    tail = [Paragraph("About this roof check", h2)] + [Paragraph(n, small) for n in notes]
    tail += [
        Paragraph("Next step: your free energy audit", h2),
        Paragraph("We'll go through your bill and the appliances you use, then size the system and send you a proposal with the price, the savings and the schedule. Please have your latest bill ready.", body),
    ]
    story.append(KeepTogether(tail))  # the closing notes and the next step move together, so a page never holds one lone paragraph
    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
