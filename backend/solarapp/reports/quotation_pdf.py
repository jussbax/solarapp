"""Customer proposal laid out like a utility statement: header strip, total box, summary of charges,
bill chart, system information, savings, reminders, payment schedule; details, your questions,
and the acceptance block on page two.

Structure only: the company's own name and colours, no utility branding. No internal costs,
markups, freight or labour detail. Everything the customer sees is in plain words.
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
from reportlab.platypus import CondPageBreak, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from xml.sax.saxutils import escape  # noqa: E402

from ..profile import warranty_lines  # noqa: E402
from ..schemas import AssessmentDoc  # noqa: E402
from . import brand  # noqa: E402
from .drawings import plan_blocks  # noqa: E402

KIND_LABEL = {"off_grid": "Battery first, nothing sold back (the grid as backup)", "net_metering": "Solar with net metering, no battery", "combination": "Hybrid solar with battery and net metering"}
NIGHT_HOURS = set(range(18, 24)) | set(range(0, 6))   # 6 pm to 6 am: the night the battery is asked to carry
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ACCENT = brand.BLACK
ACCENT_LIGHT = brand.OFF_WHITE
GOLD = brand.GOLD
INK = brand.GRAY
MUTED = brand.MUTED
LINE = brand.LINE
C_NOW, C_SOLAR = brand.C_ORANGE, brand.C_GOLD


def php(v: float) -> str:
    return f"PHP {v:,.2f}"


def php0(v: float) -> str:
    return f"PHP {v:,.0f}"


def php_about(v: float) -> str:
    """A savings figure as a person says it: "about PHP 1.41 million", "about PHP 61,000", "about PHP 3,800"."""
    a = abs(float(v))
    if a >= 1_000_000:
        text = f"PHP {a / 1_000_000:.2f}".rstrip("0").rstrip(".") + " million"
    elif a >= 10_000:
        text = f"PHP {round(a, -3):,.0f}"
    else:
        text = f"PHP {round(a, -2):,.0f}"
    return f"about {'-' if v < 0 else ''}{text}"


def years_about(y: float) -> str:
    """Payback rounded to the half year: "about 5 years", "about 3½ years", "under a year"."""
    half = round(float(y) * 2) / 2
    if half < 1:
        return "under a year"
    whole = int(half)
    if half == whole:
        return f"about {whole} {'year' if whole == 1 else 'years'}"
    return f"about {whole}½ years"


def _ampm(hhmm: str) -> str:
    """"06:15" -> "6:15 am", for the customer."""
    try:
        h, m = (int(x) for x in str(hhmm).split(":")[:2])
    except ValueError:
        return str(hhmm)
    return f"{(h % 12) or 12}:{m:02d} {'am' if h < 12 else 'pm'}"


def _d(s: str | None) -> str:
    return datetime.fromisoformat(s).strftime("%-d %b %Y") if s else ""


def _qty(q: float) -> str:
    q = float(q)
    return f"{int(q)}" if q.is_integer() else f"{round(q, 1):g}"


def _handle(url: str) -> str:
    """m.me/page from a Messenger link, facebook.com/page from a page link; the text as typed otherwise."""
    u = (url or "").strip()
    for pre in ("https://", "http://", "www."):
        if u.lower().startswith(pre):
            u = u[len(pre):]
    return u.rstrip("/")


def contact_line(company: dict) -> str:
    parts = [company.get("company_name") or "", company.get("address") or ""]
    if company.get("phone"):
        parts.append(company["phone"])
    if company.get("messenger"):
        parts.append(_handle(company["messenger"]))
    if company.get("facebook"):
        parts.append(_handle(company["facebook"]))
    if company.get("email"):
        parts.append(company["email"])
    return " · ".join(p for p in parts if p)


def bom_battery_kwh(pricing: dict) -> float:
    """Battery the customer pays for: BOM units × the catalogue kWh rating; 0 when the BOM has no battery line."""
    total = 0.0
    for l in pricing.get("lines") or []:
        if not l.get("found", True) or not l.get("rating"):
            continue
        if (l.get("role") == "battery" or l.get("category") == "Battery") and (l.get("rating_unit") or "").lower() == "kwh":
            total += float(l["qty"]) * float(l["rating"])
    return total


def customer_battery_kwh(pricing: dict, sizing: dict) -> float:
    """One battery figure for the whole proposal: the BOM's, falling back to the sizing only when there is no BOM line."""
    return bom_battery_kwh(pricing) or float((sizing.get("battery") or {}).get("installed_kwh") or 0)


def customer_inverter_text(pricing: dict, sizing: dict) -> str:
    """The inverter the customer pays for, from the BOM lines (units times the catalogue kW), so the proposal never
    says "10 kW" while the parts list carries two 6 kW units; the sizing's figure only when there is no BOM line."""
    units, kw = 0, 0.0
    for l in pricing.get("lines") or []:
        if not l.get("found", True) or not (l.get("role") == "inverter" or l.get("category") == "Inverter"):
            continue
        q = int(round(float(l.get("qty") or 0)))
        if q <= 0:
            continue
        units += q
        if (l.get("rating_unit") or "").lower() == "kw" and l.get("rating"):
            kw = float(l["rating"])
    if units and kw:
        return f"{units} × {kw:g} kW hybrid inverter ({units * kw:g} kW in all)" if units > 1 else f"{kw:g} kW hybrid inverter"
    inv = sizing.get("inverter") or {}
    if not inv:
        return "-"
    n = int(inv.get("units", 1) or 1)
    return (f"{n} × " if n > 1 else "") + f"{inv.get('size_kw', 0):g} kW hybrid inverter"


def inverter_certificate(pricing: dict) -> str:
    """The grid listing of the inverter in the BOM (IEC 61727 / 62116 or the like), when the item carries one."""
    for l in pricing.get("lines") or []:
        if l.get("found", True) and (l.get("role") == "inverter" or l.get("category") == "Inverter") and l.get("certifications"):
            return str(l["certifications"])
    return ""


def night_kwh(sizing: dict) -> float | None:
    """What the house uses from 6 pm to 6 am on an average month's day, from the sizing's hourly balance (the
    reconciled load at the meter, the same balance the savings come from). None without a balance."""
    loads = [p.get("load") for p in (sizing.get("profiles") or {}).values() if p.get("load") and len(p["load"]) == 24]
    if not loads:
        return None
    avg = [sum(float(l[h]) for l in loads) / len(loads) for h in range(24)]
    return sum(avg[h] for h in NIGHT_HOURS)


def _window_hours(start: str, end: str) -> set[int]:
    s, e = int(str(start)[:2]), int(str(end)[:2])
    return set(range(s, 24)) | set(range(0, e)) if e <= s else set(range(s, e))   # end at or before start crosses midnight; equal = 24 h


def aircon_at_night(doc: AssessmentDoc) -> bool:
    """Whether an aircon (existing or planned) is inside the 6 pm to 6 am figure, so the sentence can say so."""
    for a in doc.audit.appliances:
        if a.status in ("existing", "future") and a.category.startswith("aircon") and any(_window_hours(w.start, w.end) & NIGHT_HOURS for w in a.windows):
            return True
    return False


def battery_carries(doc: AssessmentDoc, sizing: dict, battery_kwh: float) -> tuple[str, bool]:
    """What the battery carries, in the customer's words, from the hourly balance already in the results: usable = the
    battery the customer pays for × the depth of discharge the sizing designs to; night = the reconciled load summed
    6 pm to 6 am. Returns the clause and whether the battery holds the whole night. Empty without a balance."""
    if battery_kwh <= 0 or sizing.get("kind") == "net_metering":
        return "", False
    night = night_kwh(sizing)
    if not night:
        return "", False
    dod = float((sizing.get("battery") or {}).get("depth_of_discharge") or 0.85)
    usable = battery_kwh * dod
    ac = aircon_at_night(doc)
    if usable >= night:
        return f"enough for a whole night of your usual use (about {night:.0f} kWh from 6 pm to 6 am{', aircon included' if ac else ''}, against {usable:.0f} kWh usable)", True
    hours = usable / (night / len(NIGHT_HOURS))
    loads = "your evening use, aircon included" if ac else "your evening use (lights, fans, refrigerator, TV, Wi-Fi; aircon shortens that)"
    return f"about {hours:.0f} hours of {loads}, from {usable:.0f} kWh usable against about {night:.0f} kWh used from 6 pm to 6 am", False


def battery_row(doc: AssessmentDoc, sizing: dict, battery_kwh: float) -> str:
    """The Battery line of System information: the unit the customer pays for and what it carries."""
    unit = f"{battery_kwh:.0f} kWh lithium battery (LiFePO4)"
    clause, _ = battery_carries(doc, sizing, battery_kwh)
    if not clause:
        return unit
    return f"{unit}, {clause}, recharged by the panels the next day" + ("; in the rainy season the grid covers the rest." if sizing.get("kind") == "combination" else ".")


def battery_backup_line(sizing: dict) -> str:
    """The battery-first kind only: the evenings it is designed to carry and, from the balance over a real year of
    weather, how often the grid still has to step in ("no export" only means nothing is sold back). The hybrid's
    line is the Battery row itself (what it carries)."""
    kind = sizing.get("kind", "")
    aut = (sizing.get("battery") or {}).get("days_of_autonomy")
    if kind != "off_grid" or not aut:
        return ""
    evenings = "one evening" if float(aut) == 1 else f"{aut:g} evenings"
    hy = sizing.get("hourly_year") or {}
    line = f"Designed to carry {evenings} without sun; the grid steps in only when the panels and the battery fall short, and nothing is sent back to it."
    if hy.get("available"):
        hours, days = int(hy.get("loss_of_load_hours") or 0), int(hy.get("loss_of_load_days") or 0)
        if hours > 0:
            line += f" In a typical year of weather (PVGIS records) that is about {hours} {'hour' if hours == 1 else 'hours'} on {days} {'day' if days == 1 else 'days'}, mostly in long rainy spells."
        else:
            line += " In a typical year of weather (PVGIS records) the battery does not run out."
    return line


def coverage_row(sizing: dict) -> list[str] | None:
    """The share of the house's usage served by the system, named by what serves it, so it is never mistaken for
    the production ratio ("N% of what you use") printed on the production row and the website."""
    cov = sizing.get("coverage_pct")
    if cov is None:
        return None
    kind = sizing.get("kind", "")
    if kind == "net_metering":
        return ["Used straight from the panels", f"{cov:.0f}% of your usage; the rest of the day's solar goes to the grid and is credited on your bill"]
    if kind == "off_grid":
        return ["Covered by the panels and the battery", f"{cov:.0f}% of your usage"]
    return ["Covered by solar, by day and from the battery", f"{cov:.0f}% of your usage"]


def production_row(sizing: dict, production: dict | None) -> list[str] | None:
    """Solar power made at the meter, with the ratio to the house's usage the website estimate printed."""
    annual = sizing.get("annual_production_kwh") or (production or {}).get("annual_kwh_ac") or (production or {}).get("annual_kwh")
    if not annual:
        return None
    cons = float(sizing.get("annual_consumption_kwh") or 0)
    ratio = f", {annual / cons * 100:.0f}% of what you use" if cons > 0 else ""
    return ["Solar power made", f"about {annual:,.0f} kWh a year at your meter{ratio}"]


def move_house_answer(kind: str) -> str:
    """The website's corrected answer, per kind: no resale value, no transfer the owner cannot verify."""
    if kind == "off_grid":
        return "The system stays with the house, and the new owner keeps using it. We hand over the plans and the papers."
    return "The system stays with the house. Net metering is tied to the service connection, so the new owner continues it with the electric company; we help with the paperwork."


def in_short(doc: AssessmentDoc, results: dict, n_panels: int, kwp: float, battery_kwh: float) -> str:
    """The customer's situation and the solution in one block, every figure from the results; a missing figure drops
    its sentence. The price is given before VAT, as VAT, and VAT included (the owner's rule)."""
    sizing = results.get("sizing") or {}
    eco = results.get("economics") or {}
    eco = eco if eco.get("available") else {}
    cust = (results.get("pricing") or {}).get("customer") or {}
    kind = sizing.get("kind", "")
    parts: list[str] = []
    bill_today, bill_kwh = eco.get("bill_today_monthly"), eco.get("bill_today_kwh")
    if bill_today:
        s = f"Your bill today is {php0(bill_today)} a month" + (f" for {bill_kwh:,.0f} kWh" if bill_kwh else "")
        if eco.get("includes_future_loads") and eco.get("bill_before_monthly"):
            s += f"; with the appliances you plan to add it would be about {php0(eco['bill_before_monthly'])}"
        parts.append(s + ".")
    has_battery = battery_kwh > 0 and kind != "net_metering"
    system = f"{n_panels} {'panel' if n_panels == 1 else 'panels'}" + (f" ({kwp:.2f} kWp)" if kwp else "") + (f" and a {battery_kwh:.0f} kWh battery" if has_battery else "")
    cov, after = sizing.get("coverage_pct"), eco.get("bill_after_monthly")
    if n_panels and (cov is not None or after is not None):
        s = system
        if cov is not None:
            s += f" cover {cov:.0f}% of what the house uses"
        if after is not None:
            s += f"{':' if cov is not None else ''} the bill comes down to about {php0(after)} a month"
        if kind == "net_metering":
            s += "; there is no battery, so the house runs on the grid at night and in a brownout"
        elif has_battery:
            _, whole_night = battery_carries(doc, sizing, battery_kwh)
            if kind == "off_grid":
                hy = sizing.get("hourly_year") or {}
                hours = int(hy.get("loss_of_load_hours") or 0) if hy.get("available") else 0
                s += ", the battery carries the house at night, nothing is sold back, and the grid steps in only in long rainy spells" + (f" (about {hours} hours a year)" if hours else "")
            else:
                s += f", and the battery carries your {'whole night' if whole_night else 'evening'} when the grid drops"
        parts.append(s + ".")
    total = float(cust.get("total") or 0)
    if total > 0:
        tax = sum(float(x["amount"]) for x in cust.get("sections", []) if x.get("key") == "tax")
        s = f"{php0(total - tax)} before VAT and {php0(tax)} VAT: {php0(total)} installed, permits and VAT included" if tax > 0 else f"{php0(total)} installed, permits included"
        if eco.get("payback_years") is not None:
            s += f"; it pays for itself in {years_about(eco['payback_years'])}"
        parts.append(s + ".")
    return " ".join(parts)


def installation_day_lines(prog: dict, kind: str, has_battery: bool, outage_hours: float | None) -> list[str]:
    """The customer's side of installation day, from the program's own figures (crew, arrival, finish) plus the
    owner's outage setting; blank leaves the length unstated. The papers are only those the app already asks for."""
    if not prog.get("available"):
        return []
    inst = prog.get("install") or {}
    crew = int((inst.get("crew") or {}).get("persons") or 0)
    frame = inst.get("frame") or {}
    days = int(inst.get("days") or 1)
    arrive, done = frame.get("arrive"), frame.get("pack_up_end")
    s = f"Our crew of {crew}" if crew else "Our crew"
    if arrive:
        s += f" arrives about {_ampm(arrive)}" + (f" on each of the {days} days" if days > 1 else "")
    if done:
        s += f" and is usually done by about {_ampm(done)}" + (" on the last day" if days > 1 else "")
    lines = [s + ". We need someone at home, the gate open for the materials, and access to the roof, the panel board and the wall where the inverter" + (" and the battery go." if has_battery else " goes.")]
    outage = f" for about {outage_hours:g} {'hour' if outage_hours == 1 else 'hours'}" if outage_hours else ""
    lines.append(f"Your power is off{outage} while we connect the inverter to your panel board; we tell you before we switch it off.")
    if kind != "off_grid":
        lines.append("What we need from you: a copy of your latest electric bill and your signature on the net metering forms we prepare. If your electric company asks for anything more, we confirm the list with you.")
    return lines


def customer_sections(cust: dict) -> list[dict]:
    """The proposal's charge sections: the tools charge folded into Installation and permits as one of its lines.
    The engine's customer block and the internal build-up keep it separate."""
    sections = [dict(s, items=list(s.get("items", []))) for s in cust["sections"]]
    labor = next((s for s in sections if s["key"] == "labor"), None)
    equip = next((s for s in sections if s["key"] == "equipment"), None)
    if labor is None or equip is None:
        return sections
    labor["items"][1:1] = equip["items"]  # after the crew line
    labor["amount"] = float(labor["amount"]) + float(equip["amount"])
    return [s for s in sections if s["key"] != "equipment"]


def payment_rows(payments: list[dict]) -> list[dict]:
    """Payment lines for the customer. The delivery and switch-on milestones on one day (a one-day installation)
    print as one line, "On installation day, after switch-on and testing"; any other same-day line says so."""
    groups: list[list[dict]] = []
    for p in payments:
        if groups and groups[-1][0]["date"] == p["date"]:
            groups[-1].append(p)
        else:
            groups.append([p])
    rows: list[dict] = []
    for g in groups:
        if len(g) > 1 and {p["key"] for p in g} <= {"delivery", "completion"}:
            rows.append({"key": "installation_day", "label": "On installation day, after switch-on and testing", "date": g[0]["date"],
                         "amount": sum(float(p["amount"]) for p in g), "share": sum(float(p["share"]) for p in g)})
            continue
        rows.append(dict(g[0]))
        rows += [dict(p, label=f"Same day, {p['label'][:1].lower() + p['label'][1:]}") for p in g[1:]]
    return rows


def lead_estimate_sentence(doc: AssessmentDoc, eco: dict | None, n_panels: int = 0, battery_kwh: float = 0.0, total: float = 0.0) -> str:
    """The bridge from the website estimate to the measured proposal, when the record started as a website lead:
    what the estimate was, then what it is now and why (measured, and the planned appliances when they count)."""
    est = doc.lead.estimate if doc.lead else None
    if not est or not est.price:
        return ""
    when = ""
    if doc.lead.created_at:
        try:
            when = " on " + datetime.fromisoformat(doc.lead.created_at).strftime("%-d %b %Y")
        except ValueError:
            when = ""
    panels = f"{est.panels} {'panel' if est.panels == 1 else 'panels'}"
    battery = f" and a {est.battery_kwh:.0f} kWh battery" if est.battery_kwh >= 0.5 else ""
    future = bool((eco or {}).get("includes_future_loads")) or any(a.status == "future" for a in doc.audit.appliances)
    why = "Measured on your roof" + (" and with the appliances you plan to add" if future else "")
    if n_panels and total:
        now = f"{n_panels} {'panel' if n_panels == 1 else 'panels'}" + (f" and a {battery_kwh:.0f} kWh battery" if battery_kwh >= 0.5 else "")
        return f"Your website estimate{when} was PHP {est.price:,.0f} for {panels}{battery}. {why}, it is {now} at PHP {total:,.0f}."
    return f"Your website estimate{when} was PHP {est.price:,.0f} for {panels}{battery}. This proposal is measured on your roof{' and includes the appliances you plan to add' if future else ''}."


def what_you_get(sizing: dict, prog: dict, has_warranties: bool) -> list[str]:
    """What the firm delivers, in the customer's words: the promises the website already makes, nothing new."""
    lines = ["A system designed to your bill from the readings we took on your roof.", "Every part on page 2 with its quantity."]
    if prog.get("available"):
        lines.append("The schedule on page 2, with dates.")
    papers = "Electrical plans signed and sealed by a Professional Electrical Engineer, the electrical permit and final inspection"
    if sizing.get("kind") != "off_grid":
        papers += ", the ERC certificate of compliance and the net metering application"
    lines.append(papers + ", all filed by us.")
    lines.append("A test and switch-on report on installation day" + (", and the warranties listed after Your questions." if has_warranties else "."))
    return lines


def _bill_chart(eco: dict | None, sizing: dict | None, audit: dict | None) -> tuple[Image | None, str]:
    """Pesos before and after by month when the savings exist; kWh used otherwise."""
    fig, ax = plt.subplots(figsize=(4.2, 2.0), dpi=160)
    x = range(12)
    title = "YOUR BILL, MONTH BY MONTH"
    if eco and eco.get("available"):
        before = [m["bill_before"] for m in eco["monthly"]]
        after = [m["bill_after"] for m in eco["monthly"]]
        ax.bar([i - 0.2 for i in x], before, color=C_NOW, width=0.4, label="Without solar")
        ax.bar([i + 0.2 for i in x], after, color=C_SOLAR, width=0.4, label="With solar")
        ax.set_ylabel("PHP per month", fontsize=6)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k" if v >= 1000 else f"{v:.0f}"))
    else:
        title = "YOUR ELECTRICITY USE"
        if sizing:
            cons = [m["consumption_kwh"] for m in sizing["monthly"]]
        elif audit:
            days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            cons = [d * k for d, k in zip(audit["daily_kwh_by_month"], days)]
        else:
            plt.close(fig)
            return None, ""
        ax.bar(x, cons, color=C_NOW, width=0.72, label="kWh used")
        ax.set_ylabel("kWh per month", fontsize=6)
    ax.set_xticks(list(x))
    ax.set_xticklabels(MONTHS, fontsize=6)
    ax.tick_params(axis="y", labelsize=6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=6, frameon=False, loc="upper left", bbox_to_anchor=(0, 1.12), ncol=2)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=84 * mm, height=40 * mm), title


def build_quotation_pdf(doc: AssessmentDoc, results: dict, company: dict, proposal_no: str = "", outage_hours: float | None = None) -> bytes:
    """``outage_hours`` is the owner's Program setting (hours the customer's power is off on installation day); None or 0 leaves it unstated."""
    pricing = results["pricing"]
    sizing = results.get("sizing") or {}
    eco = results.get("economics") or {}
    prog = results.get("program") or {}
    cust = pricing["customer"]
    sections = customer_sections(cust)
    lines = pricing["lines"]
    battery_kwh = customer_battery_kwh(pricing, sizing)
    wl = warranty_lines(company)
    _sec = {s["key"]: float(s["amount"]) for s in cust["sections"]}
    _base = _sec.get("materials", 0) + _sec.get("labor", 0) + _sec.get("equipment", 0)
    vat_rate = (_sec.get("tax", 0) / _base) if _base > 0 else 0.12
    buf = io.BytesIO()
    footer = contact_line(company)
    F, FS, FB = brand.fonts()

    def on_page(canvas, d) -> None:
        canvas.saveState()
        canvas.setFont(F, 6.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(14 * mm, 8 * mm, footer[:150])
        canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, f"Proposal {proposal_no or '-'} · page {d.page}")
        canvas.restoreState()

    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=14 * mm,
                            title="Solar proposal", author=company.get("company_name", ""))
    ss = getSampleStyleSheet()
    brand_style = ParagraphStyle("brand", parent=ss["Normal"], fontName=FB, fontSize=15, leading=18, textColor=ACCENT)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontName=F, fontSize=8, leading=10, textColor=MUTED)
    h2 = ParagraphStyle("h2", parent=ss["Normal"], fontName=FB, fontSize=9.5, leading=12, textColor=colors.white)
    body = ParagraphStyle("body", parent=ss["Normal"], fontName=F, fontSize=8.5, leading=11, textColor=INK)
    small = ParagraphStyle("small", parent=ss["Normal"], fontName=F, fontSize=7, leading=9, textColor=MUTED)
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontName=F, fontSize=8, leading=10, textColor=INK)
    cell_r = ParagraphStyle("cell_r", parent=cell, alignment=2)
    big = ParagraphStyle("big", parent=ss["Normal"], fontName=FB, fontSize=20, leading=24, textColor=GOLD, alignment=2)
    big_lbl = ParagraphStyle("big_lbl", parent=ss["Normal"], fontName=F, fontSize=8, leading=10, textColor=colors.white)
    q_style = ParagraphStyle("q", parent=body, fontName=FB, spaceBefore=4)
    today = datetime.now()
    validity = int(pricing.get("quotation_validity_days") or 15)
    valid = today + timedelta(days=validity)

    def section(title: str, width: float = 184 * mm) -> Table:
        t = Table([[Paragraph(title, h2)]], colWidths=[width])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT), ("LINEBEFORE", (0, 0), (0, -1), 3, GOLD), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        return t

    def kv(rows: list[list], widths: list[float], bold_last: bool = False) -> Table:
        cell_b = ParagraphStyle("cell_b", parent=cell, fontName=FB)
        cell_rb = ParagraphStyle("cell_rb", parent=cell_r, fontName=FB)
        data = [[Paragraph(str(a), cell_b if (bold_last and i == len(rows) - 1) else cell), Paragraph(str(b), cell_rb if (bold_last and i == len(rows) - 1) else cell_r)] for i, (a, b) in enumerate(rows)]
        t = Table(data, colWidths=widths)
        st = [("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        if bold_last:
            st += [("BACKGROUND", (0, -1), (-1, -1), brand.GOLD_BG), ("LINEABOVE", (0, -1), (-1, -1), 0.8, GOLD)]
        t.setStyle(TableStyle(st))
        return t

    story = []
    # ---- header strip: company left, proposal number, dates right
    right = [["Proposal No.", proposal_no or "-"], ["Proposal date", today.strftime("%-d %b %Y")], ["Valid until", valid.strftime("%-d %b %Y")]]
    rt = Table([[Paragraph(a, small), Paragraph(f"<b>{b}</b>", cell_r)] for a, b in right], colWidths=[26 * mm, 32 * mm])
    rt.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    left = [Paragraph(escape(company.get("company_name") or "Solar proposal"), brand_style)]
    contact = company.get("company_contact") or contact_line({k: v for k, v in company.items() if k != "company_name"})
    if contact:
        left.append(Paragraph(escape(contact), sub))
    left.append(Paragraph("SOLAR SYSTEM PROPOSAL", ParagraphStyle("t", parent=sub, fontName=FB, textColor=GOLD, fontSize=9, spaceBefore=4)))
    mark = brand.logo(14 * mm)
    head = Table([[mark or "", left, rt]], colWidths=[18 * mm, 100 * mm, 64 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 1.5, GOLD), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    story.append(head)
    story.append(Spacer(1, 5))

    # ---- customer block and total box, with the solar and battery parts named
    mat = next((s for s in cust["sections"] if s["key"] == "materials"), {"items": []})
    battery_item = next((i for i in mat["items"] if i["key"] == "Battery"), None)
    battery_part = float(battery_item["amount"]) * (1 + vat_rate) if battery_item else 0.0
    # the customer block names the customer and the address only: no map pin on a signed document (a pin from a website
    # booking is the town centre until the roof visit)
    cust_block = [
        Paragraph(f"<b>{escape(doc.customer_name or '-')}</b>", ParagraphStyle("cn", parent=body, fontSize=10, leading=13)),
        Paragraph(escape(doc.address or ""), body),
    ]
    tot_rows = [[Paragraph("TOTAL CONTRACT PRICE (VAT INCLUDED)", big_lbl)], [Paragraph(php(cust["total"]), big)]]
    if battery_part > 0:
        tot_rows.append([Paragraph(f"Solar system {php0(cust['total'] - battery_part)} · battery for brownouts {php0(battery_part)}", ParagraphStyle("bl2", parent=big_lbl, alignment=2))])
    if eco.get("available") and float(eco.get("bill_today_monthly") or 0) > 0:
        tot_rows.append([Paragraph(f"That is about {float(cust['total']) / float(eco['bill_today_monthly']):.0f} months of your bill today", ParagraphStyle("bl3", parent=big_lbl, alignment=2))])
    tot = Table(tot_rows, colWidths=[64 * mm])  # "Valid until" prints once, in the header strip
    tot.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (0, 0), 6), ("BOTTOMPADDING", (0, -1), (0, -1), 6)]))
    cb = Table([[cust_block, tot]], colWidths=[118 * mm, 64 * mm])
    cb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(cb)
    story.append(Spacer(1, 6))

    # ---- two columns: left chart + system information; right summary of charges + savings
    inv = sizing.get("inverter") or {}
    bat = sizing.get("battery") or {}
    panel = pricing.get("panel") or {}
    n_panels = int(next((l["qty"] for l in lines if l.get("category") == "Solar Panel"), 0))
    wp = panel.get("watt_peak") or next((l.get("rating") for l in lines if l.get("category") == "Solar Panel"), 0) or 0
    kwp = float((pricing.get("totals") or {}).get("kwp") or 0)

    # ---- in short: the customer's situation and the solution, before any table (every figure from the results)
    summary = in_short(doc, results, n_panels, kwp, battery_kwh)
    if summary:
        box = Table([[Paragraph(f"<b>In short.</b> {escape(summary)}", ParagraphStyle("short", parent=body, fontSize=9, leading=12.5))]], colWidths=[184 * mm])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), brand.GOLD_BG), ("LINEBEFORE", (0, 0), (0, -1), 3, GOLD), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        story.append(box)
        story.append(Spacer(1, 6))
    sysinfo = [
        ["System type", KIND_LABEL.get(sizing.get("kind", ""), "Solar PV system")],
        ["Solar panels", f"{n_panels} × {wp:.0f} W" if wp else f"{n_panels}"],
        ["System size", f"{pricing['totals']['kwp']:.2f} kWp (the size of the solar array)"],
        ["Inverter", customer_inverter_text(pricing, sizing)],
    ]
    certs = inverter_certificate(pricing)
    if certs:
        sysinfo.append(["Inverter certificate", escape(certs)])
    elif sizing.get("kind") != "off_grid":
        sysinfo.append(["Inverter certificate", "to be confirmed with the maker before the net metering application"])
    if battery_kwh > 0 and sizing.get("kind") != "net_metering":
        sysinfo.append(["Battery", battery_row(doc, sizing, battery_kwh)])   # the unit the customer pays for, and what it carries
        backup = battery_backup_line(sizing)
        if backup:
            sysinfo.append(["Battery backup", backup])
    if company.get("brands"):
        sysinfo.append(["Brands", escape(company["brands"])])
    # at the meter: the sizing's balance carries the system losses; the roof simulation's AC figure is the fallback
    for row in (production_row(sizing, results.get("production")), coverage_row(sizing)):
        if row:
            sysinfo.append(row)
    left_col = []
    chart, chart_title = _bill_chart(eco if eco.get("available") else None, sizing or None, results.get("audit"))
    if chart is not None:
        left_col += [section(chart_title, 90 * mm), Spacer(1, 3), chart, Spacer(1, 4)]
    left_col += [section("SYSTEM INFORMATION", 90 * mm), kv(sysinfo, [36 * mm, 54 * mm]), Spacer(1, 4), section("WHAT YOU GET", 90 * mm), Spacer(1, 2)]
    left_col += [Paragraph(f"· {w}", small) for w in what_you_get(sizing, prog, bool(wl))]

    charges = [[s["label"], php(s["amount"])] for s in sections] + [["TOTAL CONTRACT PRICE", php(cust["total"])]]
    right_col = [section("SUMMARY OF CHARGES", 90 * mm), kv(charges, [52 * mm, 38 * mm], bold_last=True), Spacer(1, 4)]
    if eco.get("available"):
        a = eco["assumptions"]
        future = bool(eco.get("includes_future_loads"))
        sav = [["Your bill today (per month)", php(eco["bill_today_monthly"])]]
        if future:
            sav.append(["With the appliances you plan to add, before solar", php(eco["bill_before_monthly"])])
        sav.append(["Your bill with solar (per month)", php(eco["bill_after_monthly"])])
        if future:
            sav.append(["Savings against your bill today", php(float(eco["bill_today_monthly"]) - float(eco["bill_after_monthly"]))])
        sav += [
            ["Monthly savings" + (" (against the bill with the new appliances)" if future else ""), php(eco["savings_monthly"])],
            ["Savings in the first year", php_about(eco["year1"]["savings"])],   # savings are estimates: said as a person says them, not to the centavo
            ["Pays for itself in", f"{eco['payback_years']:.1f} years" if eco.get("payback_years") is not None else f"more than {a['analysis_years']} years"],
            [f"Saved over {a['analysis_years']} years", php_about(eco["lifetime_net"])],
        ]
        if eco.get("irr") is not None:
            sav.append(["Yearly return on your money", f"{eco['irr'] * 100:.0f}%"])
        sav.append(["CO2 avoided", f"about {eco['co2_t_per_year']:.1f} tonnes a year"])
        right_col += [section("YOUR SAVINGS", 90 * mm), kv(sav, [52 * mm, 38 * mm])]
    cols = Table([[left_col, right_col]], colWidths=[92 * mm, 92 * mm])
    cols.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(cols)
    story.append(Spacer(1, 4))

    # ---- the roof: the panels of the proposed system as they will sit, under the system information
    plans = plan_blocks(results.get("geometry") or [], 184, cell, small, columns=2, highlight_used=True, max_height_mm=38, gutter_mm=4)
    if plans:
        story.append(KeepTogether([section("YOUR ROOF, AS THE PANELS WILL SIT"), Spacer(1, 2), plans[0]]))
        story += plans[1:]
        story.append(Spacer(1, 4))

    # ---- reminders and the payment schedule
    reminders = [
        "The price includes delivery, installation by our crew, testing and switch-on, and the permits listed.",
        "Quantities are based on your roof check and may change after the final check before installation. We will confirm any change with you first.",
        f"This proposal is good for {validity} days from the proposal date.",
    ]
    bridge = lead_estimate_sentence(doc, eco, n_panels, battery_kwh if sizing.get("kind") != "net_metering" else 0.0, float(cust["total"]))
    if bridge:
        reminders.insert(0, bridge)
    if battery_kwh > 0 and sizing.get("kind") != "net_metering" and night_kwh(sizing):
        reminders.append(f"The battery's night figures use the appliance hours from your energy audit and assume {float(bat.get('depth_of_discharge') or 0.85) * 100:.0f}% of its rating is usable each night (the depth of discharge we design to).")
    if eco.get("available"):
        a = eco["assumptions"]
        src = "from your latest bill" if str(a.get("tariff_source", "")).startswith("bill") else "our usual rate; your bill may differ"
        line = (f"Savings are estimates. They assume PHP {a['tariff_php_per_kwh']:.2f} per kWh ({src}) rising {a['tariff_escalation'] * 100:.0f}% a year, "
                f"panels losing {a['degradation'] * 100:.1f}% of output a year")
        if eco["kind"] != "off_grid":
            line += f", a net metering credit of PHP {a['export_rate_php_per_kwh']:.2f} per kWh for power sent to the grid"
        line += f", upkeep of about PHP {a['om_per_year']:,.0f} a year"
        if a["battery_replacement_cost"] > 0:
            line += f", a new battery after {a['battery_life_years']} years"
        if a["inverter_replacement_cost"] > 0:
            line += f" and a new inverter after {a['inverter_life_years']} years"
        line += ". Your real savings depend on how much power you use and on your electric company's rates."
        reminders.append(line)
    if prog.get("available") and prog.get("assumptions"):
        reminders.append("Permit and net metering dates are estimates. They depend on the city or municipal office and on your electric company.")
    story.append(section("REMINDERS"))
    for r in reminders:
        story.append(Paragraph(r, small))
    story.append(Spacer(1, 6))

    stub_rows = [["PAYMENT SCHEDULE", "Due", "Amount"]]
    if prog.get("available"):
        for p in payment_rows(prog["payments"]):
            stub_rows.append([f"{p['label']} ({p['share'] * 100:.0f}%)", _d(p["date"]), php(p["amount"])])
    else:
        stub_rows.append(["On signing", "", php(cust["total"])])
    stub_rows.append(["Total", "", php(cust["total"])])
    stub = Table(stub_rows, colWidths=[104 * mm, 36 * mm, 44 * mm])
    stub.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, MUTED, None, (3, 3)),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, -1), F), ("FONTNAME", (0, 0), (-1, 0), FB), ("TEXTCOLOR", (0, 0), (-1, 0), brand.GOLD_DARK),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"), ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINE), ("FONTNAME", (0, -1), (-1, -1), FB),
        ("TOPPADDING", (0, 0), (-1, 0), 8), ("BACKGROUND", (0, -1), (-1, -1), ACCENT_LIGHT),
    ]))
    caption = Paragraph(f"Payment schedule for proposal {escape(proposal_no or '-')}, {escape(doc.customer_name or '-')}. Please keep this for your records.", small)
    story.append(KeepTogether([caption, stub]))  # the stub moves as one block; its total row never sits alone on a page

    # ---- page two: details of charges, schedule, your questions, acceptance
    story.append(CondPageBreak(120 * mm))  # a new page unless the stub already spilled over and left the room
    story.append(section("DETAILS OF CHARGES"))
    rows = [["Item", "Qty", "Unit", "Amount"]]
    styles = [
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, -1), F), ("BACKGROUND", (0, 0), (-1, 0), ACCENT_LIGHT), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("ALIGN", (3, 0), (3, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    for s in sections:
        rows.append([s["label"], "", "", ""])
        r = len(rows) - 1
        styles += [("FONTNAME", (0, r), (-1, r), FB), ("SPAN", (0, r), (2, r)), ("TEXTCOLOR", (0, r), (-1, r), brand.GOLD_DARK)]
        for i in s.get("items", []):
            unit = i.get("unit", "")
            qty = _qty(i["qty"])
            if unit == "person-day":
                qty, unit = f"{qty} person-days" if float(i["qty"]) != 1 else "1 person-day", ""
            rows.append([Paragraph(escape(i["name"]), cell), qty, unit, php(i["amount"])])
        rows.append([f"{s['label']} subtotal", "", "", php(s["amount"])])
        r = len(rows) - 1
        styles += [("FONTNAME", (3, r), (3, r), FB), ("SPAN", (0, r), (2, r)), ("ALIGN", (0, r), (0, r), "RIGHT")]
    rows.append(["TOTAL CONTRACT PRICE (VAT INCLUDED)", "", "", php(cust["total"])])
    r = len(rows) - 1
    styles += [("FONTNAME", (0, r), (-1, r), FB), ("BACKGROUND", (0, r), (-1, r), ACCENT_LIGHT), ("SPAN", (0, r), (2, r))]
    dt = Table(rows, colWidths=[116 * mm, 14 * mm, 20 * mm, 34 * mm], repeatRows=1)
    dt.setStyle(TableStyle(styles))
    story.append(dt)
    story.append(Spacer(1, 8))

    if prog.get("available"):
        story.append(section("SCHEDULE"))
        srows = [["Date", "Milestone"]]
        for e in prog["customer_schedule"]:
            when = _d(e["date"]) + (f" to {_d(e['end'])}" if e.get("end") and e["end"] != e["date"] else "")
            srows.append([when, Paragraph(escape(e["label"]), cell)])
        st2 = Table(srows, colWidths=[50 * mm, 134 * mm])
        st2.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("FONTNAME", (0, 0), (-1, -1), F), ("BACKGROUND", (0, 0), (-1, 0), ACCENT_LIGHT), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(st2)
        story.append(Spacer(1, 8))

    # ---- the customer's side of installation day: who comes when, what we need, the power cut, the papers
    kind = sizing.get("kind", "")
    bat_kwh = battery_kwh  # the same figure as System information
    day_lines = installation_day_lines(prog, kind, bat_kwh > 0 and kind != "net_metering", outage_hours)
    if day_lines:
        story.append(KeepTogether([section("ON INSTALLATION DAY"), Spacer(1, 2)] + [Paragraph(x, body) for x in day_lines] + [Spacer(1, 8)]))

    # ---- your questions: the objections, answered on paper
    ev = {e["key"]: e for e in prog.get("events", [])} if prog.get("available") else {}
    days = int((prog.get("install") or {}).get("days") or 1) if prog.get("available") else 1
    qa: list[tuple[str, str]] = []
    carries, _ = battery_carries(doc, sizing, bat_kwh)
    if kind == "off_grid":
        hy = sizing.get("hourly_year") or {}
        tail = ""
        if hy.get("available") and int(hy.get("loss_of_load_hours") or 0) > 0:
            tail = f" In a long rainy spell the battery can run out and the grid takes over: in a typical year of weather that is about {int(hy['loss_of_load_hours'])} hours on {int(hy['loss_of_load_days'])} days."
        qa.append(("What happens in a brownout?", f"The house runs on the panels and the {bat_kwh:.0f} kWh battery first, every day{f'; the battery is {carries}' if carries else ''}. The grid only steps in when both fall short, so a brownout changes little.{tail}"))
    elif bat_kwh > 0:
        what = f": {carries}" if carries else f". A {bat_kwh:.0f} kWh battery carries lights, fans, the refrigerator, TV and wifi through a typical evening; running aircon shortens that"
        qa.append(("What happens in a brownout?", f"The battery takes over the moment the grid drops{what}. By day the panels recharge it."))
    else:
        qa.append(("What happens in a brownout?", "A system without a battery switches off during a brownout, as the safety rules require, and restarts on its own when the grid returns. A battery can be added later if you want backup."))
    if kind != "off_grid":
        gap = ""
        if ev.get("commissioning") and ev.get("meter_installed"):
            gap = f" Between switch-on ({_d(ev['commissioning']['date'])}) and the two-way meter ({_d(ev['meter_installed']['date'])}) the system already cuts your daytime bill, but power sent to the grid is not yet credited."
        qa.append(("Who handles net metering?", "We prepare and file the net metering application, the ERC certificate of compliance (the net metering certificate) and the two-way meter request with your electric company; you sign the forms." + gap))
    qa.append(("What if we move house?", move_house_answer(kind)))
    qa.append(("Who looks after it?", "Rinse the panels with water two or three times a year, more in the dry season. The inverter shows its output on its screen or app, and we check the system at switch-on and whenever you ask."))
    qa.append(("What does the installation do to the roof?", f"The rails clamp to the roof framing through the sheet with sealed fasteners. Installation takes {days} {'day' if days == 1 else 'days'} and leaves no open holes."))
    first = True
    for q, ans in qa:
        block = [Paragraph(q, q_style), Paragraph(ans, body)]
        story.append(KeepTogether(([section("YOUR QUESTIONS"), Spacer(1, 2)] if first else []) + block))
        first = False
    if wl:
        story.append(Paragraph("Warranties", q_style))
        for w in wl:
            story.append(Paragraph(w, body))
    if company.get("pee_name") or company.get("pee_license"):
        who = company.get("pee_name") or "our Professional Electrical Engineer"
        lic = f", PRC No. {company['pee_license']}" if company.get("pee_license") else ""
        story.append(Paragraph(f"Electrical plans are signed and sealed by {who}, Professional Electrical Engineer{lic}.", body))
    story.append(Spacer(1, 10))

    # ---- acceptance block
    down = next((p for p in prog["payments"] if p.get("key") == "downpayment"), None) if prog.get("available") else None
    accept = ["To accept this proposal, sign below and send us a photo on Messenger, or sign on our next visit."]
    if down:
        accept.append(f"The downpayment of {php(down['amount'])} is due on signing" + (f", to: {escape(company['payment_details'])}." if company.get("payment_details") else "."))
    sig_style = ParagraphStyle("sig", parent=small, textColor=INK)
    sig = Table([
        [Paragraph("Accepted by the customer", sig_style), Paragraph(f"For {company.get('company_name') or 'the company'}", sig_style)],
        [Spacer(1, 26), Spacer(1, 26)],
        [Paragraph(f"{escape(doc.customer_name or 'Name')} · signature · date", sig_style), Paragraph(f"{escape(company.get('owner_name') or 'Name')} · signature · date", sig_style)],
    ], colWidths=[92 * mm, 92 * mm])
    sig.setStyle(TableStyle([("LINEBELOW", (0, 1), (-1, 1), 0.6, INK), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    story.append(KeepTogether([section("TO ACCEPT THIS PROPOSAL"), Spacer(1, 3)] + [Paragraph(a, body) for a in accept] + [Spacer(1, 6), sig]))
    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()
