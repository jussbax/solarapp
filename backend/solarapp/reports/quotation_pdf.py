"""Customer quotation: Equipment, Materials, Labor, Tax. No internal costs, markups or freight detail."""
from __future__ import annotations

import io
from datetime import datetime, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..schemas import AssessmentDoc

KIND_LABEL = {"off_grid": "Off-grid solar with battery (no grid import)", "net_metering": "Grid-tied solar with net metering", "combination": "Hybrid solar with battery and net metering"}


def php(v: float) -> str:
    return f"PHP {v:,.2f}"


def build_quotation_pdf(doc: AssessmentDoc, results: dict, company: dict) -> bytes:
    pricing = results["pricing"]
    sizing = results.get("sizing") or {}
    cust = pricing["customer"]
    lines = pricing["lines"]
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Solar system quotation", author=company.get("company_name", ""))
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], textColor=colors.HexColor("#555555"), fontSize=9)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#555555"))
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontSize=8.5, leading=11)

    story = []
    story.append(Paragraph(company.get("company_name") or "Solar system quotation", h1))
    if company.get("company_contact"):
        story.append(Paragraph(company["company_contact"], sub))
    story.append(Paragraph("Quotation", h2))
    today = datetime.now()
    valid = today + timedelta(days=int(pricing.get("quotation_validity_days") or 15))
    story.append(Paragraph(f"Prepared for <b>{doc.customer_name or '-'}</b> on {today.strftime('%d %b %Y')}. Valid until {valid.strftime('%d %b %Y')}.", body))
    if doc.address:
        story.append(Paragraph(doc.address, body))
    story.append(Spacer(1, 6))

    inv = sizing.get("inverter") or {}
    bat = sizing.get("battery") or {}
    panel = pricing.get("panel") or {}
    n_panels = int(next((l["qty"] for l in lines if l.get("category") == "Solar Panel"), 0))
    kpi = [
        ["System", KIND_LABEL.get(sizing.get("kind", ""), "Solar PV system")],
        ["Solar panels", f"{n_panels} x {panel.get('name') or (str(panel.get('watt_peak', 0)) + ' W panel')}"],
        ["System size", f"{pricing['totals']['kwp']:.2f} kWp"],
        ["Inverter", f"{int(inv.get('units', 1))} x {inv.get('size_kw', 0):g} kW hybrid" if inv else "-"],
    ]
    if bat.get("installed_kwh", 0) > 0 and sizing.get("kind") != "net_metering":
        bl = next((l for l in lines if l.get("category") == "Battery"), None)
        kpi.append(["Battery", f"{bl['qty']:g} x {bl['name']}" if bl else f"{bat['installed_kwh']:.1f} kWh"])
    annual = sizing.get("annual_production_kwh") or (results.get("production") or {}).get("annual_kwh")
    if annual:
        kpi.append(["Estimated production", f"{annual:,.0f} kWh per year"])
    t = Table(kpi, colWidths=[50 * mm, 120 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10), ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#444444")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"), ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#dddddd")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    story.append(Paragraph("Price", h2))
    rows = [["Section", "Description", "Amount"]]
    materials_names = sorted({l["category"] for l in lines if l.get("category") not in ("Solar Panel", "Inverter", "Battery", "All-in-one System")})
    desc = {
        "equipment": ", ".join(f"{int(i['qty']) if float(i['qty']).is_integer() else i['qty']} x {i['name']}" for i in cust["sections"][0].get("items", [])),
        "materials": "Mounting, wiring, protection, enclosures, grounding and consumables" if materials_names else "-",
        "labor": "Installation, commissioning, mobilization, permits and fees",
        "tax": "Value added tax",
    }
    for s in cust["sections"]:
        rows.append([s["label"], Paragraph(desc.get(s["key"], ""), cell), php(s["amount"])])
    rows.append(["Total", "", php(cust["total"])])
    pt = Table(rows, colWidths=[32 * mm, 98 * mm, 40 * mm])
    pt.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f3")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")), ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f7fafa")),
    ]))
    story.append(pt)
    story.append(Paragraph(f"Total contract price {php(cust['total'])}, inclusive of VAT.", body))

    story.append(Paragraph("Scope", h2))
    scope_rows = [["Item", "Qty", "Unit"]]
    for l in lines:
        q = l["qty"]
        scope_rows.append([Paragraph(l["name"], cell), f"{int(q) if float(q).is_integer() else q:g}", l.get("unit") or ""])
    st = Table(scope_rows, colWidths=[130 * mm, 20 * mm, 20 * mm], repeatRows=1)
    st.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f3")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(st)

    prog = results.get("program") or {}
    if prog.get("available"):
        story.append(Paragraph("Schedule", h2))
        rows = [["Date", "Milestone"]]
        for e in prog["customer_schedule"]:
            when = datetime.fromisoformat(e["date"]).strftime("%d %b %Y")
            if e.get("end") and e["end"] != e["date"]:
                when += " to " + datetime.fromisoformat(e["end"]).strftime("%d %b %Y")
            rows.append([when, Paragraph(e["label"], cell)])
        st2 = Table(rows, colWidths=[50 * mm, 120 * mm])
        st2.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f3")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(st2)
        if prog.get("assumptions"):
            story.append(Paragraph("Permit and utility dates are estimates and depend on the local government and the distribution utility.", small))
        story.append(Paragraph("Payment terms", h2))
        rows = [["Due", "Payment", "Amount"]]
        for p in prog["payments"]:
            rows.append([datetime.fromisoformat(p["date"]).strftime("%d %b %Y"), Paragraph(f"{p['label']} ({p['share'] * 100:.0f}%)", cell), php(p["amount"])])
        rows.append(["", "Total", php(cust["total"])])
        pt2 = Table(rows, colWidths=[40 * mm, 90 * mm, 40 * mm])
        pt2.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f3")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cccccc")), ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(pt2)

    story.append(Paragraph("Terms", h2))
    for n in [
        "Prices include delivery to site, installation by our crew, testing and commissioning, and the permits listed.",
        "Quantities are from the roof assessment and may be adjusted after the final site survey.",
        f"This quotation is valid for {int(pricing.get('quotation_validity_days') or 15)} days from the date above.",
    ]:
        story.append(Paragraph(n, small))
    pdf.build(story)
    return buf.getvalue()
