"""Customer proposal laid out like a utility statement: header strip, total box, summary of charges,
consumption chart, system information, savings, payment stub, details on page two.

Structure only: the company's own name and colours, no utility branding. No internal costs,
markups, freight or labour detail.
"""
from __future__ import annotations

import io
from datetime import datetime, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from ..schemas import AssessmentDoc  # noqa: E402

KIND_LABEL = {"off_grid": "Off-grid solar with battery (no grid import)", "net_metering": "Grid-tied solar with net metering", "combination": "Hybrid solar with battery and net metering"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ACCENT = colors.HexColor("#2b7a78")
ACCENT_LIGHT = colors.HexColor("#e6f2f2")
INK = colors.HexColor("#222222")
MUTED = colors.HexColor("#555555")
LINE = colors.HexColor("#cfd8d8")
# chart colours validated for colour-blind separation on a light surface
C_NOW, C_SOLAR = "#c84f2b", "#0b9b8d"


def php(v: float) -> str:
    return f"PHP {v:,.2f}"


def _d(s: str | None) -> str:
    return datetime.fromisoformat(s).strftime("%d %b %Y") if s else ""


def _qty(q: float) -> str:
    q = float(q)
    return f"{int(q)}" if q.is_integer() else f"{round(q, 1):g}"


def _consumption_chart(eco: dict | None, sizing: dict | None, audit: dict | None) -> Image | None:
    if eco and eco.get("available"):
        cons = [m["consumption_kwh"] for m in eco["monthly"]]
        imp = [m["import_kwh"] for m in eco["monthly"]]
        label_b = "From the grid with solar"
    elif sizing:
        cons = [m["consumption_kwh"] for m in sizing["monthly"]]
        imp = [m["import_kwh"] for m in sizing["monthly"]]
        label_b = "From the grid with solar"
    elif audit:
        days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        cons = [d * k for d, k in zip(audit["daily_kwh_by_month"], days)]
        imp, label_b = None, ""
    else:
        return None
    fig, ax = plt.subplots(figsize=(4.2, 2.2), dpi=160)
    x = range(12)
    ax.bar(x, cons, color=C_NOW, width=0.72, label="Your consumption now")
    if imp is not None:
        ax.bar(x, imp, color=C_SOLAR, width=0.72, label=label_b)
    ax.set_xticks(list(x))
    ax.set_xticklabels(MONTHS, fontsize=6)
    ax.tick_params(axis="y", labelsize=6)
    ax.set_ylabel("kWh per month", fontsize=6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=6, frameon=False, loc="upper left", bbox_to_anchor=(0, 1.12), ncol=2)
    for i, v in enumerate(cons):
        ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=5, color="#555555")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=84 * mm, height=44 * mm)


def build_quotation_pdf(doc: AssessmentDoc, results: dict, company: dict, proposal_no: str = "") -> bytes:
    pricing = results["pricing"]
    sizing = results.get("sizing") or {}
    eco = results.get("economics") or {}
    prog = results.get("program") or {}
    cust = pricing["customer"]
    lines = pricing["lines"]
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title="Solar proposal", author=company.get("company_name", ""))
    ss = getSampleStyleSheet()
    brand = ParagraphStyle("brand", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=ACCENT)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=8, leading=10, textColor=MUTED)
    h2 = ParagraphStyle("h2", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.white)
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=8.5, leading=11, textColor=INK)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=7, leading=9, textColor=MUTED)
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontSize=8, leading=10, textColor=INK)
    cell_r = ParagraphStyle("cell_r", parent=cell, alignment=2)
    big = ParagraphStyle("big", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.white, alignment=2)
    big_lbl = ParagraphStyle("big_lbl", parent=ss["Normal"], fontSize=8, leading=10, textColor=colors.white)
    today = datetime.now()
    valid = today + timedelta(days=int(pricing.get("quotation_validity_days") or 15))

    def section(title: str, width: float = 184 * mm) -> Table:
        t = Table([[Paragraph(title, h2)]], colWidths=[width])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        return t

    def kv(rows: list[list], widths: list[float], bold_last: bool = False) -> Table:
        data = [[Paragraph(str(a), cell), Paragraph(str(b), cell_r)] for a, b in rows]
        t = Table(data, colWidths=widths)
        st = [("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        if bold_last:
            st += [("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("BACKGROUND", (0, -1), (-1, -1), ACCENT_LIGHT)]
        t.setStyle(TableStyle(st))
        return t

    story = []
    # ---- header strip: company left, proposal number, dates right
    right = [
        ["Proposal No.", proposal_no or "-"], ["Statement date", today.strftime("%d %b %Y")], ["Valid until", valid.strftime("%d %b %Y")],
    ]
    rt = Table([[Paragraph(a, small), Paragraph(f"<b>{b}</b>", cell_r)] for a, b in right], colWidths=[26 * mm, 32 * mm])
    rt.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    left = [Paragraph(company.get("company_name") or "Solar proposal", brand)]
    if company.get("company_contact"):
        left.append(Paragraph(company["company_contact"], sub))
    left.append(Paragraph("SOLAR SYSTEM PROPOSAL", ParagraphStyle("t", parent=sub, fontName="Helvetica-Bold", textColor=INK, fontSize=9, spaceBefore=4)))
    head = Table([[left, rt]], colWidths=[118 * mm, 64 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 1.2, ACCENT), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(head)
    story.append(Spacer(1, 5))

    # ---- customer block and total box
    cust_block = [
        Paragraph(f"<b>{doc.customer_name or '-'}</b>", ParagraphStyle("cn", parent=body, fontSize=10, leading=13)),
        Paragraph(doc.address or "", body),
        Paragraph(f"Site {doc.lat:.5f}, {doc.lon:.5f}" if doc.lat is not None and doc.lon is not None else "", small),
    ]
    tot = Table([[Paragraph("TOTAL CONTRACT PRICE, VAT INCLUSIVE", big_lbl)], [Paragraph(php(cust["total"]), big)],
                 [Paragraph(f"Valid until {valid.strftime('%d %b %Y')}", ParagraphStyle("bl2", parent=big_lbl, alignment=2))]], colWidths=[64 * mm])
    tot.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (0, 0), 6), ("BOTTOMPADDING", (0, -1), (0, -1), 6)]))
    cb = Table([[cust_block, tot]], colWidths=[118 * mm, 64 * mm])
    cb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(cb)
    story.append(Spacer(1, 6))

    # ---- two columns: left consumption chart + system information; right summary of charges + savings
    inv = sizing.get("inverter") or {}
    bat = sizing.get("battery") or {}
    panel = pricing.get("panel") or {}
    n_panels = int(next((l["qty"] for l in lines if l.get("category") == "Solar Panel"), 0))
    sysinfo = [
        ["System type", KIND_LABEL.get(sizing.get("kind", ""), "Solar PV system")],
        ["Solar panels", f"{n_panels} x {panel.get('name') or (str(panel.get('watt_peak', 0)) + ' W panel')}"],
        ["System size", f"{pricing['totals']['kwp']:.2f} kWp"],
        ["Inverter", f"{int(inv.get('units', 1))} x {inv.get('size_kw', 0):g} kW hybrid" if inv else "-"],
    ]
    if bat.get("installed_kwh", 0) > 0 and sizing.get("kind") != "net_metering":
        bl = next((l for l in lines if l.get("category") == "Battery"), None)
        sysinfo.append(["Battery", f"{_qty(bl['qty'])} x {bl['name']}" if bl else f"{bat['installed_kwh']:.1f} kWh"])
    annual = sizing.get("annual_production_kwh") or (results.get("production") or {}).get("annual_kwh")
    if annual:
        sysinfo.append(["Estimated production", f"{annual:,.0f} kWh a year"])
    if sizing.get("coverage_pct") is not None:
        sysinfo.append(["Of your consumption covered", f"{sizing['coverage_pct']:.0f}%"])
    left_col = []
    chart = _consumption_chart(eco if eco.get("available") else None, sizing or None, results.get("audit"))
    if chart is not None:
        left_col += [section("YOUR ELECTRICITY CONSUMPTION", 90 * mm), Spacer(1, 3), chart, Spacer(1, 4)]
    left_col += [section("SYSTEM INFORMATION", 90 * mm), kv(sysinfo, [36 * mm, 54 * mm])]

    charges = [[s["label"], php(s["amount"])] for s in cust["sections"]] + [["TOTAL CONTRACT PRICE", php(cust["total"])]]
    right_col = [section("SUMMARY OF CHARGES", 90 * mm), kv(charges, [52 * mm, 38 * mm], bold_last=True), Spacer(1, 4)]
    if eco.get("available"):
        a = eco["assumptions"]
        sav = [["Your electricity bill today, monthly", php(eco["bill_today_monthly"])]]
        if eco.get("includes_future_loads"):
            sav.append(["With your planned appliances, no solar", php(eco["bill_before_monthly"])])
        sav += [
            ["Estimated bill with solar, monthly", php(eco["bill_after_monthly"])],
            ["Monthly savings", php(eco["savings_monthly"])],
            ["Savings in the first year", php(eco["year1"]["savings"])],
            ["Payback", f"{eco['payback_years']:.1f} years" if eco.get("payback_years") is not None else f"beyond {a['analysis_years']} years"],
            [f"Net savings over {a['analysis_years']} years", php(eco["lifetime_net"])],
        ]
        if eco.get("irr") is not None:
            sav.append(["Return on the investment", f"{eco['irr'] * 100:.0f}% a year"])
        sav.append(["Carbon avoided", f"about {eco['co2_t_per_year']:.1f} t CO2 a year"])
        right_col += [section("YOUR SAVINGS", 90 * mm), kv(sav, [52 * mm, 38 * mm])]
    cols = Table([[left_col, right_col]], colWidths=[92 * mm, 92 * mm])
    cols.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(cols)
    story.append(Spacer(1, 6))

    # ---- reminders and the payment stub
    reminders = [
        "Prices include delivery to site, installation by our crew, testing and commissioning, and the permits listed.",
        "Quantities are from the roof assessment and may be adjusted after the final site survey.",
        f"This proposal is valid for {int(pricing.get('quotation_validity_days') or 15)} days from the statement date.",
    ]
    if eco.get("available"):
        a = eco["assumptions"]
        line = (f"Savings are estimates based on {a['tariff_php_per_kwh']:.2f} PHP per kWh ({'your latest bill' if a['tariff_source'].startswith('bill') else 'an assumed rate'}), "
                f"electricity prices rising {a['tariff_escalation'] * 100:.0f}% a year, panel output declining {a['degradation'] * 100:.1f}% a year")
        if eco["kind"] != "off_grid":
            line += f", export credited at {a['export_rate_php_per_kwh']:.2f} PHP per kWh under net metering"
        line += f", yearly upkeep of PHP {a['om_per_year']:,.0f}"
        if a["battery_replacement_cost"] > 0:
            line += f", a battery replacement after {a['battery_life_years']} years"
        if a["inverter_replacement_cost"] > 0:
            line += f" and an inverter replacement after {a['inverter_life_years']} years"
        line += ". Actual savings depend on your consumption and the utility's rates."
        reminders.append(line)
    if prog.get("available") and prog.get("assumptions"):
        reminders.append("Permit and utility dates are estimates and depend on the local government and the distribution utility.")
    story.append(section("REMINDERS"))
    for r in reminders:
        story.append(Paragraph(r, small))
    story.append(Spacer(1, 8))

    stub_rows = [["PAYMENT SCHEDULE", "Due", "Amount"]]
    if prog.get("available"):
        for p in prog["payments"]:
            stub_rows.append([f"{p['label']} ({p['share'] * 100:.0f}%)", _d(p["date"]), php(p["amount"])])
    else:
        stub_rows.append(["On signing", "", php(cust["total"])])
    stub_rows.append(["Total", "", php(cust["total"])])
    stub = Table(stub_rows, colWidths=[104 * mm, 36 * mm, 44 * mm])
    stub.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, MUTED, None, (3, 3)),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (-1, 0), ACCENT),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"), ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINE), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, 0), 8), ("BACKGROUND", (0, -1), (-1, -1), ACCENT_LIGHT),
    ]))
    story.append(Paragraph(f"Please keep this stub for your payments. Proposal {proposal_no or '-'} for {doc.customer_name or '-'}.", small))
    story.append(stub)

    # ---- page two: details of charges, schedule
    story.append(PageBreak())
    story.append(section("DETAILS OF CHARGES"))
    rows = [["Item", "Qty", "Unit", "Amount"]]
    styles = [
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (-1, 0), ACCENT_LIGHT), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("ALIGN", (3, 0), (3, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    for s in cust["sections"]:
        rows.append([s["label"], "", "", ""])
        r = len(rows) - 1
        styles += [("FONTNAME", (0, r), (-1, r), "Helvetica-Bold"), ("SPAN", (0, r), (2, r)), ("TEXTCOLOR", (0, r), (-1, r), ACCENT)]
        for i in s.get("items", []):
            rows.append([Paragraph(i["name"], cell), _qty(i["qty"]), i.get("unit", ""), php(i["amount"])])
        rows.append([f"{s['label']} subtotal", "", "", php(s["amount"])])
        r = len(rows) - 1
        styles += [("FONTNAME", (3, r), (3, r), "Helvetica-Bold"), ("SPAN", (0, r), (2, r)), ("ALIGN", (0, r), (0, r), "RIGHT")]
    rows.append(["TOTAL CONTRACT PRICE, VAT INCLUSIVE", "", "", php(cust["total"])])
    r = len(rows) - 1
    styles += [("FONTNAME", (0, r), (-1, r), "Helvetica-Bold"), ("BACKGROUND", (0, r), (-1, r), ACCENT_LIGHT), ("SPAN", (0, r), (2, r))]
    dt = Table(rows, colWidths=[116 * mm, 14 * mm, 20 * mm, 34 * mm], repeatRows=1)
    dt.setStyle(TableStyle(styles))
    story.append(dt)
    story.append(Spacer(1, 8))

    if prog.get("available"):
        story.append(section("SCHEDULE"))
        srows = [["Date", "Milestone"]]
        for e in prog["customer_schedule"]:
            when = _d(e["date"]) + (f" to {_d(e['end'])}" if e.get("end") and e["end"] != e["date"] else "")
            srows.append([when, Paragraph(e["label"], cell)])
        st2 = Table(srows, colWidths=[50 * mm, 134 * mm])
        st2.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (-1, 0), ACCENT_LIGHT), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(st2)
    pdf.build(story)
    return buf.getvalue()
