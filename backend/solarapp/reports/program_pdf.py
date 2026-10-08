"""Internal program of works: schedule, installation days by the hour, cashflow."""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from xml.sax.saxutils import escape

from ..schemas import AssessmentDoc
from . import brand


def php(v: float) -> str:
    return f"{v:,.0f}"


def _d(s: str | None) -> str:
    return datetime.fromisoformat(s).strftime("%d %b %Y") if s else ""


def build_program_pdf(doc: AssessmentDoc, results: dict, company: dict) -> bytes:
    prog = results["program"]
    pricing = results["pricing"]
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title="Program of works", author=company.get("company_name", ""))
    ss = getSampleStyleSheet()
    F, FS, FB = brand.fonts()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontName=FB, fontSize=15, leading=18, spaceAfter=2, alignment=0, textColor=brand.BLACK)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName=FB, fontSize=11, spaceBefore=8, spaceAfter=4, textColor=brand.BLACK)
    body = ParagraphStyle("body", parent=ss["Normal"], fontName=F, fontSize=9, leading=12, textColor=brand.GRAY)
    small = ParagraphStyle("small", parent=ss["Normal"], fontName=F, fontSize=7.5, leading=10, textColor=brand.MUTED)
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontName=F, fontSize=7.5, leading=9.5, textColor=brand.GRAY)
    grid = TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, -1), F), ("FONTNAME", (0, 0), (-1, 0), FB), ("BACKGROUND", (0, 0), (-1, 0), brand.OFF_WHITE),
        ("GRID", (0, 0), (-1, -1), 0.25, brand.LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])

    mark = brand.logo(12 * mm)
    head = Table([[mark or "", Paragraph(f"Program of works: {escape(doc.customer_name or '-')}", h1)]], colWidths=[16 * mm, 240 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 1.5, brand.GOLD), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    story = [head]
    story.append(Paragraph(f"INTERNAL, NOT FOR THE CUSTOMER · {escape(doc.address)} · {pricing['totals']['kwp']:.2f} kWp · contract PHP {php(pricing['totals']['contract_rounded'])}", small))
    story.append(Paragraph("Schedule", h2))
    rows = [["Date", "Until", "Activity", "Customer sees"]]
    for e in prog["events"]:
        amt = f" PHP {php(e['amount'])}" if e.get("amount") else ""
        rows.append([_d(e["date"]), _d(e.get("end")), Paragraph(e["label"] + amt, cell), "yes" if e.get("customer") else ""])
    t = Table(rows, colWidths=[24 * mm, 24 * mm, 180 * mm, 24 * mm], repeatRows=1)
    t.setStyle(grid)
    story.append(t)
    if prog.get("assumptions"):
        story.append(Spacer(1, 4))
        for a in prog["assumptions"]:
            story.append(Paragraph("Assumption: " + a, small))
    for w in prog.get("warnings", []):
        story.append(Paragraph("Note: " + w["message"], small))

    inst = prog["install"]
    story.append(Paragraph(f"Installation: {inst['days']} {'day' if inst['days'] == 1 else 'days'}, {inst['crew']['description']}; {inst['crew']['roof_pairs']} roof {'pair' if inst['crew']['roof_pairs'] == 1 else 'pairs'}, {inst['crew']['ground_persons']} on the ground", h2))
    fr = inst["frame"]
    story.append(Paragraph(f"Depart base {fr['depart']}, on site {fr['arrive']}, work from {fr['work_start']}, lunch {fr['lunch_start']} to {fr['lunch_end']}, "
                           f"{fr['productive_hours']:g} productive hours a day, back at base about {fr['back_at_base']}. Man-hours: roof {inst['man_hours']['roof']:.1f}, ground {inst['man_hours']['ground']:.1f}, hand-off {inst['man_hours']['handoff']:.1f}.", body))
    for day in inst["hourly"]:
        story.append(Paragraph(f"Day {day['day']}: {_d(prog['install_start']) if day['day'] == 1 else ''}", h2) if day["day"] == 1 else Paragraph(f"Day {day['day']}", h2))
        rows = [["Hour", "Roof crew", "Ground crew"]]
        for r in day["rows"]:
            rows.append([r["time"], Paragraph(r["roof"], cell), Paragraph(r["ground"], cell)])
        t = Table(rows, colWidths=[16 * mm, 118 * mm, 118 * mm], repeatRows=1)
        t.setStyle(grid)
        story.append(t)
    story.append(Paragraph("Task list", h2))
    rows = [["Day", "From", "To", "Crew", "Persons", "Task"]]
    for s in inst["segments"]:
        rows.append([str(s["day"] + 1), s["start_time"], s["end_time"], s["stream"], str(s["crew"]), Paragraph(s["task"], cell)])
    t = Table(rows, colWidths=[12 * mm, 16 * mm, 16 * mm, 18 * mm, 18 * mm, 172 * mm], repeatRows=1)
    t.setStyle(grid)
    story.append(t)

    story.append(PageBreak())
    cf = prog["cashflow"]
    story.append(Paragraph("Cashflow", h2))
    story.append(Paragraph(f"Cash in PHP {php(cf['total_in'])}, cash out PHP {php(cf['total_out'])}, cash margin PHP {php(cf['cash_margin'])}. "
                           f"Lowest balance PHP {php(cf['lowest_balance'])} on {_d(cf['lowest_balance_date'])}. "
                           f"Kept in the company as allocations (not cash): handling, wastage and storage PHP {php(cf['noncash']['handling_wastage_storage'])}, "
                           f"truck ownership and maintenance PHP {php(cf['noncash']['truck_ownership_maintenance'])}, tools PHP {php(cf['noncash']['tools'])}.", body))
    rows = [["Date", "Item", "In", "Out", "Balance"]]
    for f in cf["flows"]:
        rows.append([_d(f["date"]), Paragraph(f["label"], cell), php(f["inflow"]) if f["inflow"] else "", php(f["outflow"]) if f["outflow"] else "", php(f["balance"])])
    t = Table(rows, colWidths=[24 * mm, 150 * mm, 28 * mm, 28 * mm, 30 * mm], repeatRows=1)
    t.setStyle(grid)
    t.setStyle(TableStyle([("ALIGN", (2, 1), (-1, -1), "RIGHT")]))
    story.append(t)
    pdf.build(story)
    return buf.getvalue()
