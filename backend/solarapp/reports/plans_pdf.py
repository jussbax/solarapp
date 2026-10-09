"""The plans for the PEE: the drawing set the Professional Electrical Engineer signs and seals, A3 landscape
(420 × 297 mm), drawn with ReportLab from the geometry, the BOM and the settings the results already hold.

Sheets: 1 cover and general notes; one array layout per roof face that holds panels, at the largest standard scale
that fits the sheet; the equipment and circuit schedule; a last sheet that says what is not yet in the set and why,
with the energy audit's schedule of loads when the audit has appliances. Every page carries the title block
(company, project, sheet name and number, date and revision, the PEE's signature block from the company profile).

Nothing here is invented: every figure comes from the results, the BOM lines, the materials list or the pricing
settings; a figure the app does not hold prints as a blank line (BLANK). No code clause numbers and no standards
are named unless the materials list records them (the inverter's certificate); where the signing engineer adds the
clause the line reads "per the applicable code, to be completed by the signing engineer"."""
from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

from ..schemas import AssessmentDoc
from . import brand
from .drawings import fit_scale, plan_drawing

PAGE_W, PAGE_H = landscape(A3)              # 1190.55 × 841.89 pt: 420 × 297 mm
SHEET_SIZE = "A3 landscape, 420 × 297 mm"
MARGIN = 10 * mm
TITLE_H = 30 * mm                           # the title block strip along the bottom of every sheet
FRAME_W = PAGE_W - 2 * MARGIN
FRAME_H = PAGE_H - 2 * MARGIN - TITLE_H
BLANK = "__________"                        # a figure the app does not hold: a line for the signing engineer, never a guess
TO_COMPLETE = "per the applicable code, to be completed by the signing engineer"
KIND_LABEL = {
    "net_metering": "Grid-interactive, no battery (net metering)",
    "combination": "Hybrid: grid-interactive with a battery (net metering)",
    "off_grid": "Battery with the grid as backup; nothing exported",
}


# ---- small formatting helpers: a missing value is a blank line, never a number

def _f(v: Any, nd: int = 1, unit: str = "") -> str:
    if v is None or v == "":
        return BLANK
    try:
        x = float(v)
    except (TypeError, ValueError):
        return escape(str(v))
    s = f"{x:,.{nd}f}" if nd else f"{x:,.0f}"
    return s + (f" {unit}" if unit else "")


def _g(v: Any, unit: str = "") -> str:
    """A number as a person says it: 2.4, 10, 0.3."""
    if v is None or v == "":
        return BLANK
    try:
        x = float(v)
    except (TypeError, ValueError):
        return escape(str(v))
    return f"{x:g}" + (f" {unit}" if unit else "")


def _pct(v: Any) -> str:
    return BLANK if v is None else f"{float(v) * 100:.1f} %"


def _text_or_blank(v: Any) -> str:
    s = str(v or "").strip()
    return escape(s) if s else BLANK


def _d(s: Optional[str]) -> str:
    if not s:
        return BLANK
    try:
        return datetime.fromisoformat(str(s)).strftime("%d %b %Y")
    except ValueError:
        return escape(str(s)[:10])


def _dt(s: Optional[str]) -> str:
    if not s:
        return BLANK
    try:
        return datetime.fromisoformat(str(s)).strftime("%d %b %Y %H:%M")
    except ValueError:
        return escape(str(s)[:16])


# ---- the title block: drawn on every page when the document is saved, so "Sheet n of N" knows N

class SheetMarker(Flowable):
    """A zero-height flowable at the top of each sheet's story: it names the sheet on the canvas so the title block
    can print it. The name stays on a page the sheet overflows to."""

    def __init__(self, name: str, scale: Optional[int] = None):
        super().__init__()
        self.name, self.scale = name, scale
        self.width = self.height = 0

    def wrap(self, aw, ah):  # noqa: ANN001
        return 0, 0

    def draw(self):
        self.canv.sheet_name = self.name
        self.canv.sheet_scale = self.scale


def _canvas_class(info: dict):
    """A canvas that remembers every page and draws the title block with the page count on save."""
    F, FS, FB = brand.fonts()

    class SheetCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages: list[dict] = []
            self.sheet_name = ""
            self.sheet_scale = None

        def showPage(self):  # noqa: N802
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for i, state in enumerate(self._pages):
                self.__dict__.update(state)
                self._title_block(i + 1, total)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def _title_block(self, n: int, total: int) -> None:
            c = self
            c.saveState()
            # the sheet frame and the strip
            c.setStrokeColor(brand.BLACK)
            c.setLineWidth(0.9)
            c.rect(MARGIN, MARGIN, FRAME_W, PAGE_H - 2 * MARGIN)
            y0 = MARGIN
            c.line(MARGIN, y0 + TITLE_H, MARGIN + FRAME_W, y0 + TITLE_H)
            c.setLineWidth(0.5)
            # four cells: company | project | sheet | signature
            xs = [MARGIN, MARGIN + 108 * mm, MARGIN + 220 * mm, MARGIN + 300 * mm, MARGIN + FRAME_W]
            for x in xs[1:-1]:
                c.line(x, y0, x, y0 + TITLE_H)
            pad, top = 3 * mm, y0 + TITLE_H - 3 * mm

            def put(x: float, y: float, text: str, size: float = 7.5, font: str = F, color=brand.GRAY, max_w: Optional[float] = None) -> None:
                c.setFont(font, size)
                c.setFillColor(color)
                t = text
                if max_w is not None:
                    from reportlab.pdfbase import pdfmetrics
                    while t and pdfmetrics.stringWidth(t, font, size) > max_w:
                        t = t[:-1]
                c.drawString(x, y, t)

            # company
            x = xs[0] + pad
            w = xs[1] - xs[0] - 2 * pad
            put(x, top - 7, info["company_name"] or BLANK, 9.5, FB, brand.BLACK, w)
            for k, line in enumerate(info["company_lines"][:3]):
                put(x, top - 17 - k * 9.5, line, 7, F, brand.GRAY, w)
            # project
            x = xs[1] + pad
            w = xs[2] - xs[1] - 2 * pad
            put(x, top - 7, "PV system plans: " + (info["customer"] or BLANK), 9, FB, brand.BLACK, w)
            put(x, top - 17, info["address"] or BLANK, 7, F, brand.GRAY, w)
            put(x, top - 26.5, f"Project {info['project_no']}  ·  {info['system']}", 7, F, brand.GRAY, w)
            put(x, top - 36, f"Date {info['today']}  ·  Rev. 0, calculated {info['computed']}", 7, F, brand.GRAY, w)
            put(x, top - 45.5, "INTERNAL DRAWING SET FOR THE SIGNING ENGINEER; NOT A CUSTOMER DOCUMENT", 5.5, F, brand.MUTED, w)
            # sheet
            x = xs[2] + pad
            w = xs[3] - xs[2] - 2 * pad
            put(x, top - 7, self.sheet_name or "", 9, FB, brand.BLACK, w)
            put(x, top - 18, f"Sheet {n} of {total}", 10, FB, brand.BLACK, w)
            scale = f"Scale 1:{self.sheet_scale} on {SHEET_SIZE}" if self.sheet_scale else f"Not to scale  ·  {SHEET_SIZE}"
            put(x, top - 28, scale, 7, F, brand.GRAY, w)
            put(x, top - 37.5, "Dimensions in metres unless marked", 7, F, brand.GRAY, w)
            put(x, top - 47, "Generated by the office system from the current calculation", 5.5, F, brand.MUTED, w)
            # signature block for the PEE
            x = xs[3] + pad
            w = xs[4] - xs[3] - 2 * pad
            put(x, top - 7, "Signed and sealed by the Professional Electrical Engineer", 7, FS, brand.BLACK, w)
            put(x, top - 18, "Name: " + (info["pee_name"] or BLANK + BLANK), 7.5, F, brand.GRAY, w)
            put(x, top - 28, "PRC No.: " + (info["pee_license"] or BLANK) + "    PTR No.: " + BLANK, 7.5, F, brand.GRAY, w)
            put(x, top - 38, "TIN: " + BLANK + "    Signature: " + BLANK + "  Date: " + BLANK, 7.5, F, brand.GRAY, w)
            put(x, top - 47.5, "Seal", 6, F, brand.MUTED, w)
            c.restoreState()

    return SheetCanvas


# ---- the data behind the sheets

def _lines_by_role(pricing: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for l in pricing.get("lines") or []:
        out.setdefault(str(l.get("role") or ""), []).append(l)
    return out


def _line(by_role: dict[str, list[dict]], role: str) -> Optional[dict]:
    ls = by_role.get(role) or []
    return ls[0] if ls else None


def _item_text(l: Optional[dict], with_qty: bool = True) -> str:
    """"2 pc IAN-PRT-018 DC SPD 1000V" or the blank line; a role without an item says so."""
    if l is None:
        return BLANK
    code = str(l.get("code") or "")
    if code.startswith("NO-ITEM-") or not l.get("found", True):
        return f"no item in the materials list yet ({escape(str(l.get('role') or ''))}): qty {_g(l.get('qty'))} {escape(str(l.get('unit') or ''))}".strip()
    q = ""
    if with_qty:
        qty = float(l.get("qty") or 0)
        q = f"{int(qty) if qty.is_integer() else round(qty, 1):g} {escape(str(l.get('unit') or ''))} "
    return f"{q}{escape(str(l.get('name') or code))} ({escape(code)})"


def _rating(l: Optional[dict], unit: str) -> str:
    if l is None or l.get("rating") in (None, ""):
        return BLANK
    return _g(l.get("rating"), unit)


def _company_lines(company: dict) -> list[str]:
    lines = []
    contact = (company.get("company_contact") or "").strip()
    if contact:
        lines.append(contact)
    else:
        for k in ("address", "phone", "email"):
            v = (company.get(k) or "").strip()
            if v:
                lines.append(v)
    return lines


def _strings_per_face(face: dict) -> list[tuple[int, list[int]]]:
    """[(string number, [panel numbers])] for the used panels of one face, as the current rule numbered them."""
    by: dict[int, list[int]] = {}
    for p in face.get("panels") or []:
        if p.get("used") and p.get("string"):
            by.setdefault(int(p["string"]), []).append(int(p.get("n") or 0))
    return [(s, sorted(ns)) for s, ns in sorted(by.items())]


def _ranges(ns: list[int]) -> str:
    """1–8 for a run, 1–3, 5 for gaps."""
    if not ns:
        return ""
    out, start, prev = [], ns[0], ns[0]
    for n in ns[1:]:
        if n == prev + 1:
            prev = n
            continue
        out.append(f"{start}–{prev}" if start != prev else str(start))
        start = prev = n
    out.append(f"{start}–{prev}" if start != prev else str(start))
    return ", ".join(out)


def _rows_from_eave(face: dict) -> str:
    counts: dict[int, int] = {}
    for p in face.get("panels") or []:
        counts[int(p.get("row") or 0)] = counts.get(int(p.get("row") or 0), 0) + 1
    return ", ".join(str(counts[r]) for r in sorted(counts)) if counts else "0"


# ---- the builder

def build_plans_pdf(doc: AssessmentDoc, results: dict, company: dict, items: Optional[dict[str, dict]] = None,
                    config: Optional[dict] = None, project_no: str = "", today: Optional[date] = None) -> bytes:
    """The A3 drawing set as PDF bytes. `items` is the materials list by code (dicts of the Item fields) for the
    models' specs and electrical data; `config` is the pricing settings as a dict (wiring rules and BOM item roles)."""
    items = items or {}
    cfg = config or {}
    wiring = cfg.get("wiring") or {}
    roles = cfg.get("roles") or {}
    today = today or date.today()
    pricing = results.get("pricing") or {}
    sizing = results.get("sizing") or {}
    choices = pricing.get("choices") or {}
    audit = results.get("audit") or {}
    geometry = list(results.get("geometry") or [])
    faces_with_panels = [g for g in geometry if (g.get("panels") or [])]
    by_role = _lines_by_role(pricing)
    panel_l, inv_l, bat_l = _line(by_role, "panel"), _line(by_role, "inverter"), _line(by_role, "battery")
    panel_item = items.get(str((panel_l or {}).get("code") or "")) or {}
    inv_item = items.get(str((inv_l or {}).get("code") or "")) or {}
    bat_item = items.get(str((bat_l or {}).get("code") or "")) or {}
    kind = str(sizing.get("kind") or "")
    kwp = float((pricing.get("totals") or {}).get("kwp") or sizing.get("kwp") or 0)
    panels_n = int(sizing.get("panels") or 0)
    units = int(choices.get("inverter_units") or (inv_l or {}).get("qty") or 1)
    strings = int(choices.get("strings") or 0)
    per_string = int(choices.get("panels_per_string") or 0)
    max_per_string = doc.pricing.max_panels_per_string or roles.get("max_panels_per_string")
    pv_run = doc.pricing.pv_run_m if doc.pricing.pv_run_m is not None else wiring.get("pv_run_m")
    ac_run = doc.pricing.ac_run_m if doc.pricing.ac_run_m is not None else wiring.get("ac_run_m")
    gnd_run = doc.pricing.grounding_run_m if doc.pricing.grounding_run_m is not None else wiring.get("grounding_run_m")
    conduit = doc.pricing.conduit_m if doc.pricing.conduit_m is not None else wiring.get("conduit_m")
    thhn_amp = wiring.get("thhn_ampacity") or {}
    n_cond = wiring.get("ac_conductors_per_circuit")
    inv_name = (inv_l or {}).get("name") or BLANK
    bat_name = (bat_l or {}).get("name") or BLANK
    system_short = f"{kwp:.2f} kWp, {panels_n} panels" + (f", {units} × {inv_name}" if inv_l else "")

    info = {
        "company_name": (company.get("company_name") or "").strip(), "company_lines": _company_lines(company),
        "customer": doc.customer_name or "", "address": doc.address or "", "project_no": project_no or BLANK,
        "system": system_short, "today": today.strftime("%d %b %Y"), "computed": _dt(results.get("computed_at")),
        "pee_name": (company.get("pee_name") or "").strip(), "pee_license": (company.get("pee_license") or "").strip(),
    }

    # styles
    ss = getSampleStyleSheet()
    F, FS, FB = brand.fonts()
    # A3 has room: the tables read at 8.5 pt, the notes at 8.5, the headings at 11 and 16
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontName=FB, fontSize=16, leading=19, spaceAfter=3, alignment=0, textColor=brand.BLACK)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName=FB, fontSize=11, leading=13, spaceBefore=7, spaceAfter=3, textColor=brand.BLACK)
    body = ParagraphStyle("body", parent=ss["Normal"], fontName=F, fontSize=9, leading=12, textColor=brand.GRAY)
    small = ParagraphStyle("small", parent=ss["Normal"], fontName=F, fontSize=8, leading=10.5, textColor=brand.MUTED)
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontName=F, fontSize=8.5, leading=10.5, textColor=brand.GRAY)
    cellb = ParagraphStyle("cellb", parent=cell, fontName=FS, textColor=brand.BLACK)
    note = ParagraphStyle("note", parent=body, fontSize=8.5, leading=11.5, leftIndent=10, firstLineIndent=-10, spaceAfter=3)
    grid = TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("FONTNAME", (0, 0), (-1, -1), F), ("FONTNAME", (0, 0), (-1, 0), FB),
        ("BACKGROUND", (0, 0), (-1, 0), brand.OFF_WHITE), ("GRID", (0, 0), (-1, -1), 0.25, brand.LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ])
    kv_style = TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("FONTNAME", (0, 0), (-1, -1), F), ("FONTNAME", (0, 0), (0, -1), FS), ("TEXTCOLOR", (0, 0), (0, -1), brand.BLACK),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, brand.LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ])
    two_col = TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                          ("RIGHTPADDING", (0, 0), (0, -1), 6 * mm), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)])

    def P(t: str, st=cell) -> Paragraph:
        return Paragraph(t, st)

    def kv(rows: list[tuple[str, str]], widths=(48 * mm, 140 * mm)) -> Table:
        t = Table([[P(k, cellb), P(v)] for k, v in rows], colWidths=list(widths), hAlign="LEFT")
        t.setStyle(kv_style)
        return t

    def table(head: list[str], rows: list[list], widths: list[float]) -> Table:
        data = [[P(h, cellb) for h in head]] + [[c if isinstance(c, Paragraph) else P(str(c)) for c in r] for r in rows]
        t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
        t.setStyle(grid)
        return t

    # ---------------- sheet 1: cover and general notes
    sheet_names = ["Cover and general notes"] + [f"Array layout: {g.get('name') or 'Roof'}" for g in faces_with_panels] + ["Equipment and circuit schedule", "Not yet in this set; schedule of loads"]
    story: list = [SheetMarker(sheet_names[0])]
    story.append(Paragraph(f"PV system plans: {escape(doc.customer_name or BLANK)}", h1))
    story.append(Paragraph(f"{escape(doc.address or BLANK)} · pin {doc.lat:.5f}, {doc.lon:.5f} · {escape(KIND_LABEL.get(kind, 'solar PV system'))}", body))

    grid_flag = choices.get("inverter_grid_interactive")
    cert = str(pricing.get("inverter_certificate") or "").strip()
    export_line = _line(by_role, "export_limiter")
    sys_rows = [
        ("System kind", escape(KIND_LABEL.get(kind, BLANK))),
        ("Array", f"{panels_n} × {escape(str((panel_l or {}).get('name') or BLANK))} {_rating(panel_l, 'W')} = {kwp:.2f} kWp"),
        ("Roof maximum", f"{_g(sizing.get('roof_max_panels'))} panels, {_f(sizing.get('roof_max_kwp'), 2, 'kWp')} (the positions the faces hold)"),
        ("Inverter", f"{units} × {escape(str(inv_name))} ({_rating(inv_l, 'kW')}; {escape(str((inv_l or {}).get('code') or ''))})"
                     + ("" if grid_flag is None else (", grid-interactive" if grid_flag else ", off-grid type: cannot export"))),
        ("Inverter certificate", escape(cert) if cert else "none on file (to be confirmed with the maker before the DU application)"),
        ("Battery", "none (net metering, no battery)" if kind == "net_metering" else
         f"{_g(choices.get('battery_units') or (bat_l or {}).get('qty'))} × {escape(str(bat_name))} ({_rating(bat_l, 'kWh')}) = {_f(choices.get('battery_nominal_kwh'), 2, 'kWh')} nominal; "
         f"sized {_f((sizing.get('battery') or {}).get('sized_nominal_kwh'), 2, 'kWh')} nominal, {_f((sizing.get('battery') or {}).get('sized_usable_kwh'), 2, 'kWh')} usable"),
        ("Strings", f"{strings} × {per_string} panels (the current rule: up to {_g(max_per_string)} panels per string"
                    + (f"; set to {doc.pricing.strings_override} strings on this job" if doc.pricing.strings_override else "") + ")"),
        ("Grid connection", f"{_g(wiring.get('ac_voltage'), 'V')} AC at the service, {_g(n_cond)} conductors (line and neutral) per circuit as the wiring rules hold; "
                            f"net metering: {'yes' if kind != 'off_grid' else 'no (no export)'}; point of interconnection: {BLANK}"),
        ("Export limit", _item_text(export_line) if export_line else ("none priced (verify the DU's rule)" if kind != "off_grid" else "not applicable")),
        ("Annual production", f"{_f(sizing.get('annual_production_kwh'), 0, 'kWh')} at the meter (the sizing's estimate)"),
    ]
    left_col = [Paragraph("The system", h2), kv(sys_rows, (34 * mm, 156 * mm))]

    face_rows = []
    for g in geometry:
        n = len(g.get("panels") or [])
        used = g.get("used")
        ridge = f", ridge {_g(g.get('ridge_m'), 'm')}" if (g.get("shape") == "hip") else ""
        face_rows.append([
            P(escape(str(g.get("name") or "Roof")), cellb), {"rect": "rectangle", "hip": "hip", "tri": "triangle"}.get(str(g.get("shape") or ""), str(g.get("shape") or "")),
            f"{_g(g.get('eave_m'))} × {_g(g.get('slope_m'))} m{ridge}", f"{_g(g.get('tilt_deg'))}°", f"{_g(g.get('azimuth_deg'))}° ({escape(str(g.get('compass') or ''))})",
            (f"{used} of {n}" if used is not None else str(n)) if n else "none fit", escape(str(g.get("orientation") or "")) if n else "",
        ])
    faces_t = table(["Face", "Shape", "Eave × slope", "Tilt", "Looks toward", "Panels", "Panels laid"], face_rows, [42 * mm, 22 * mm, 38 * mm, 12 * mm, 32 * mm, 20 * mm, 22 * mm])

    def elec(it: dict, key: str, unit: str, nd: int = 1) -> str:
        return _f(it.get(key), nd, unit) if it.get(key) not in (None, "") else BLANK

    model_rows = [
        ["Panel", escape(str((panel_l or {}).get("code") or BLANK)), P(escape(str((panel_l or {}).get("name") or BLANK)) + (f"<br/>{escape(str(panel_item.get('spec') or ''))}" if panel_item.get("spec") else "")),
         _rating(panel_l, "W"), P(f"{_g(faces_with_panels[0].get('panel_length_m') if faces_with_panels else None)} × {_g(faces_with_panels[0].get('panel_width_m') if faces_with_panels else None)} m<br/>"
                                  f"Voc {elec(panel_item, 'voc_v', 'V')}, Vmp {elec(panel_item, 'vmp_v', 'V')}, Isc {elec(panel_item, 'isc_a', 'A')}, Imp {elec(panel_item, 'imp_a', 'A')}")],
        ["Inverter", escape(str((inv_l or {}).get("code") or BLANK)), P(escape(str(inv_name)) + (f"<br/>{escape(str(inv_item.get('spec') or ''))}" if inv_item.get("spec") else "")),
         _rating(inv_l, "kW"), P(f"max PV {elec(inv_item, 'max_pv_voltage_v', 'V', 0)}, MPPT {elec(inv_item, 'mppt_min_v', 'V', 0)} to {elec(inv_item, 'mppt_max_v', 'V', 0)} × {_g(inv_item.get('mppt_count'))}, "
                                 f"{elec(inv_item, 'mppt_max_a', 'A', 0)} per MPPT<br/>AC input {elec(inv_item, 'ac_input_a', 'A', 0)}, battery {elec(inv_item, 'battery_max_a', 'A', 0)}; certificate: {escape(cert) if cert else BLANK}")],
    ]
    if kind != "net_metering":
        model_rows.append(["Battery", escape(str((bat_l or {}).get("code") or BLANK)), P(escape(str(bat_name)) + (f"<br/>{escape(str(bat_item.get('spec') or ''))}" if bat_item.get("spec") else "")),
                           _rating(bat_l, "kWh"), P(f"continuous {elec(bat_item, 'continuous_a', 'A', 0)}; {_g(choices.get('battery_units') or (bat_l or {}).get('qty'))} in the bank")])
    models_t = table(["Role", "Code", "Model (materials list)", "Rating", "Data on file (blank = not on the Materials page yet)"], model_rows, [18 * mm, 26 * mm, 56 * mm, 16 * mm, 72 * mm])
    right_col = [Paragraph("Roof faces", h2), faces_t, Paragraph("Panel and inverter models from the materials list", h2), models_t]

    top = Table([[left_col, right_col]], colWidths=[196 * mm, 194 * mm], hAlign="LEFT")
    top.setStyle(two_col)
    story.append(top)

    # general notes: facts the app holds, nothing else
    inset = float(doc.setback_m or 0) / 2.0
    rail_l, lfr = roles.get("rail_length_m"), roles.get("l_feet_per_rail")
    fpf = roles.get("fasteners_per_l_foot")
    gnd_rod, bonding, lugs = _line(by_role, "ground_rod"), _line(by_role, "array_bonding"), _line(by_role, "earth_lug")
    thhn_l = _line(by_role, "thhn")
    notes = [
        f"<b>1. Setback and spacing.</b> Panels are kept {inset:g} m from every edge of a face (a setback of {_g(doc.setback_m)} m per dimension on this project) and "
        + (f"{_g(doc.gap_m)} m apart along a row." if float(doc.gap_m or 0) > 0 else "touching along a row, the mid-clamps between them.")
        + " A hatched strip on a layout sheet is a strip that holds no panels (a wall beside the face); the dotted line is the setback line.",
        f"<b>2. Panels.</b> {panels_n} panels of {_rating(panel_l, 'W')} are laid as the layout sheets show, numbered from the eave up and left to right on each face; "
        f"solid panels belong to this system, dashed ones are positions the faces could still hold. Panel size {_g(faces_with_panels[0].get('panel_length_m') if faces_with_panels else None)} × "
        f"{_g(faces_with_panels[0].get('panel_width_m') if faces_with_panels else None)} m from the materials list.",
        f"<b>3. Mounting (the BOM's rule).</b> Each row sits on two rail lines of {_g(rail_l, 'm')} rails, {_g(lfr)} L-feet per rail, {_g(fpf)} fasteners per L-foot into the purlins "
        f"(verify with the rail maker's manual and the roof sheet); end clamps 4 per row, mid-clamps 2 per panel gap, a splice at every rail joint. "
        f"The roof's construction, the purlin spacing and the uplift check are not in this set: {TO_COMPLETE}.",
        f"<b>4. Strings.</b> {strings} strings of {per_string} panels (up to {_g(max_per_string)} per string by the current rule), S1 upwards as the layout sheets label them; "
        f"one DC breaker per string ({_item_text(_line(by_role, 'dc_breaker'), with_qty=False)}); DC SPDs: {_item_text(_line(by_role, 'dc_spd'))}, "
        + ("one per MPPT input in use." if inv_item.get("mppt_count") else "one per inverter (the MPPT count is not on the item; verify)."),
        f"<b>5. Grounding and bonding (the BOM).</b> Ground rod: {_item_text(gnd_rod)}. Array bonding conductor: {_item_text(bonding)}, along the rail lines with jumpers between rows "
        f"(bare copper where the LGU asks; the gauge to be verified by the signing engineer). Earth lugs: {_item_text(lugs)}. Grounding run: {_g(gnd_run, 'm')} per inverter on the "
        f"{escape(str(choices.get('ac_gauge') or BLANK))} mm² THHN of the AC circuits. The equipment and electrode grounding conductor sizes: {TO_COMPLETE}.",
        f"<b>6. Conductors and protection.</b> Breakers and conductors as the circuit schedule sheet lists them, from the wiring rules on file (THHN ampacity table, {', '.join(f'{k} mm² {v:g} A' for k, v in thhn_amp.items())}; "
        f"verify the table edition). Derating, conduit fill and the short-circuit note: {TO_COMPLETE}.",
        f"<b>7. Labels and placards.</b> PV system labels and placards at the service, the disconnect, the inverter and the DC box are miscellaneous supplies, not a BOM line; "
        f"what the LGU and the DU ask for: {TO_COMPLETE}.",
        f"<b>8. Code references.</b> No clause is cited by the office system; the articles that apply to the array, the storage battery and the mounting: {TO_COMPLETE}.",
    ]
    index_lines = [f"Sheet {i + 1}: {escape(n)}" for i, n in enumerate(sheet_names)]
    notes_left = [Paragraph("General notes", h2)] + [Paragraph(n, note) for n in notes[:4]]
    notes_right = [Paragraph("&nbsp;", h2)] + [Paragraph(n, note) for n in notes[4:]] + [Paragraph("Sheets in this set", h2)] + [Paragraph(l, body) for l in index_lines]
    bottom = Table([[notes_left, notes_right]], colWidths=[196 * mm, 194 * mm], hAlign="LEFT")
    bottom.setStyle(two_col)
    story.append(bottom)

    # ---------------- one sheet per roof face with panels
    DRAW_W, DRAW_H, SIDE_W = 272 * mm, 226 * mm, 112 * mm
    for g in faces_with_panels:
        story.append(PageBreak())
        scale = fit_scale(g, 272, 226, font_pt=7)
        story.append(SheetMarker(f"Array layout: {g.get('name') or 'Roof'}", scale))
        story.append(Paragraph(f"Array layout: {escape(str(g.get('name') or 'Roof'))}  ·  scale 1:{scale}", h1))
        drawing = plan_drawing(g, 272, highlight_used=g.get("used") is not None, dimensions=True, scale_denominator=scale, string_labels=True, north_arrow=True, font_pt=7, legend=False)
        n = len(g.get("panels") or [])
        used = g.get("used")
        watt = float((panel_l or {}).get("rating") or 0)
        face_kwp = (used if used is not None else n) * watt / 1000.0
        facts = [
            ("Shape", {"rect": "rectangle", "hip": "hip (trapezoid)", "tri": "triangle"}.get(str(g.get("shape") or ""), str(g.get("shape") or ""))),
            ("Eave", _g(g.get("eave_m"), "m")), ("Slope (eave to ridge)", _g(g.get("slope_m"), "m")),
        ]
        if g.get("shape") == "hip":
            facts.append(("Ridge", _g(g.get("ridge_m"), "m")))
        facts += [
            ("Tilt", f"{_g(g.get('tilt_deg'))}°"), ("Looks toward", f"{_g(g.get('azimuth_deg'))}° ({escape(str(g.get('compass') or ''))}); north as the arrow shows"),
            ("Panels on this face", (f"{used} of {n} positions used" if used is not None else f"{n} positions") + (f"; {g.get('left_out')} left out for vents or marked areas" if int(g.get("left_out") or 0) else "")),
            ("kWp on this face", f"{face_kwp:.2f} kWp" if watt else BLANK),
            ("Panels laid", f"{escape(str(g.get('orientation') or BLANK))}, {_g(g.get('panel_length_m'))} × {_g(g.get('panel_width_m'))} m each"),
            ("Rows from the eave", _rows_from_eave(g)),
            ("Spacing", (f"{_g(g.get('gap_m'))} m between panels" if float(g.get("gap_m") or 0) > 0 else "panels touching, mid-clamps between them")),
            ("Setback", f"{float(g.get('setback_m') or 0) / 2:g} m from each edge (setback {_g(g.get('setback_m'))} m per dimension)"),
        ]
        cuts = g.get("cuts") or {}
        strip_txt = ", ".join(f"{e} {float(cuts[e]):g} m" for e in ("eave", "ridge", "left", "right") if float(cuts.get(e) or 0) > 0)
        if strip_txt:
            facts.append(("No-panel strips", strip_txt + " (hatched)"))
        side_col: list = [Paragraph("The face", h2), kv(facts, (34 * mm, 76 * mm))]
        strs = _strings_per_face(g)
        side_col.append(Paragraph("Strings on this face", h2))
        if strs:
            side_col.append(kv([(f"S{s}", f"panels {_ranges(ns)} ({len(ns)})") for s, ns in strs], (34 * mm, 76 * mm)))
            side_col.append(Paragraph(f"String numbers follow the current rule ({strings} strings of {per_string}, filled from the best face, rows from the eave up). "
                                      f"The string table (Voc at the coldest cell, Vmp at the hottest, Isc per MPPT) waits on the datasheets; see the last sheet.", small))
        else:
            side_col.append(Paragraph("No panel of the sized system sits on this face." if used is not None else "The system is not sized yet; the strings follow the energy audit.", small))
        obstacles = list(g.get("obstacles") or [])
        markers = [o for o in obstacles if o.get("kind") == "shade"]
        walls = [o for o in obstacles if o.get("kind") == "wall"]
        side_col.append(Paragraph("Obstacles and shade, as surveyed", h2))
        if markers or walls:
            ob_rows = [(chr(65 + i), escape(str(o.get("label") or ""))) for i, o in enumerate(markers)] + [("Hatched", escape(str(o.get("label") or ""))) for o in walls]
            side_col.append(kv(ob_rows, (20 * mm, 90 * mm)))
        else:
            side_col.append(Paragraph("None recorded on this face.", small))
        side_col.append(Paragraph("Legend", h2))
        side_col.append(Paragraph("Solid gold: a panel of this system, numbered, its string under the number. Dashed white: a position the face can still hold. "
                                  "Dotted line: the setback line. Hatched: a strip that holds no panels. Lettered circle: a tree or building on the edge it shades from. "
                                  "Near dimension figures: the strips that hold no panels; outer figures: the face. The eave is the lower edge; the arrow points north.", small))
        row = Table([[drawing, side_col]], colWidths=[DRAW_W + 4 * mm, SIDE_W], hAlign="LEFT")
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                 ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        story.append(row)

    # ---------------- equipment and circuit schedule
    story.append(PageBreak())
    story.append(SheetMarker("Equipment and circuit schedule"))
    story.append(Paragraph("Equipment and circuit schedule", h1))
    story.append(Paragraph("From the bill of materials and the design choices of the current calculation. Where the figure is a rule's figure rather than a datasheet's, the line says so.", body))
    ats = choices.get("ats")
    eq_rows = [
        ["Panels", _item_text(panel_l), _rating(panel_l, "W"), P(f"Voc {elec(panel_item, 'voc_v', 'V')}, Vmp {elec(panel_item, 'vmp_v', 'V')}, Isc {elec(panel_item, 'isc_a', 'A')}, Imp {elec(panel_item, 'imp_a', 'A')}; "
                                                                 f"temperature coefficient of Voc {elec(panel_item, 'temp_coeff_voc_pct', '%/°C', 2)}")],
        ["Inverter", _item_text(inv_l), _rating(inv_l, "kW"), P(f"grid-interactive: {'yes' if grid_flag else 'no' if grid_flag is False else 'not marked'}; certificate: {escape(cert) if cert else BLANK}; "
                                                                f"AC input {elec(inv_item, 'ac_input_a', 'A', 0)}; battery current {elec(inv_item, 'battery_max_a', 'A', 0)}; MPPT inputs {_g(inv_item.get('mppt_count'))}; "
                                                                f"transfer switch: {'built in' if ats == 'built-in' else 'external (see AC side)' if inv_item.get('has_transfer_switch') is False else 'not on the item; an external ATS is priced'}")],
    ]
    if kind != "net_metering":
        eq_rows.append(["Battery", _item_text(bat_l), _rating(bat_l, "kWh"), P(f"bank {_f(choices.get('battery_nominal_kwh'), 2, 'kWh')} nominal; continuous discharge {elec(bat_item, 'continuous_a', 'A', 0)} per unit "
                                                                               f"against {_f(choices.get('battery_current_a'), 0, 'A')} from the inverter")])
    for role, label in (("monitoring", "Monitoring"), ("export_limiter", "Export limiter"), ("enclosure", "Enclosure")):
        l = _line(by_role, role)
        if l is not None:
            eq_rows.append([label, _item_text(l), "", P(escape(str(l.get("note") or "")))])
    eq_t = table(["Equipment", "Item (materials list)", "Rating", "Data and notes"], eq_rows, [22 * mm, 70 * mm, 18 * mm, 80 * mm])

    i_str, v_str = choices.get("string_current_a"), choices.get("string_voltage_v")
    dc_rows = [
        ["Strings", f"{strings} × {per_string} panels", P(f"up to {_g(max_per_string)} per string by the current rule; S1 upwards on the layout sheets")],
        ["String current, Imp", _f(i_str, 1, "A"), P(f"the rule's figure: panel watts over the wiring rules' {_g(wiring.get('panel_vmp_v'), 'V')} per panel; the datasheet's Imp is {elec(panel_item, 'imp_a', 'A')}")],
        ["String voltage at Vmp", _f(v_str, 0, "V"), P(f"{per_string} × {_g(wiring.get('panel_vmp_v'), 'V')} by the rule; Voc at the coldest cell and the inverter's window wait on the datasheets (last sheet)")],
        ["PV cable (+)", _item_text(_line(by_role, "pv_cable_red")), P(f"{escape(str(choices.get('pv_gauge') or BLANK))} mm², {_g(pv_run, 'm')} home run per conductor per string; drop {_pct(choices.get('pv_drop'))} against the {_pct(wiring.get('dc_drop_limit'))} limit")],
        ["PV cable (−)", _item_text(_line(by_role, "pv_cable_black")), P("the same run")],
        ["Connectors", _item_text(_line(by_role, "mc4_pair")), P(f"{_g(roles.get('mc4_pairs_per_string'))} pairs per string")],
        ["DC breaker", _item_text(_line(by_role, "dc_breaker")), P("one per string, in the DC box; it is the DC disconnect of each string")],
        ["DC SPD", _item_text(_line(by_role, "dc_spd")), P(escape(str((_line(by_role, "dc_spd") or {}).get("note") or "")))],
        ["DC disconnect", "the string breakers above", P("no separate DC disconnect is on the BOM; whether the LGU or the DU asks for one: " + TO_COMPLETE)],
    ]
    dc_t = table(["DC side", "Item or figure", "Notes"], dc_rows, [32 * mm, 64 * mm, 94 * mm])

    amp = lambda gauge: _f(thhn_amp.get(str(gauge)), 0, "A") if gauge is not None and str(gauge) in thhn_amp else BLANK  # noqa: E731
    inv_circ, grid_circ = roles.get("ac_breakers_per_inverter"), roles.get("ac_grid_breakers_per_inverter")
    grid_known = choices.get("ac_grid_rating_known")
    ac_rows = [
        ["Inverter output circuit", f"{_g(inv_circ)} per inverter × {units}", P(f"{_f(choices.get('ac_current_a'), 1, 'A')} at {_g(wiring.get('ac_voltage'), 'V')}; breaker {_g(choices.get('ac_breaker_a'), 'A')} "
                                                                                 f"(1.25 × the current, next standard size); conductor {escape(str(choices.get('ac_gauge') or BLANK))} mm² THHN ({amp(choices.get('ac_gauge'))}), "
                                                                                 f"{_g(n_cond)} conductors × {_g(ac_run, 'm')}; drop {_pct(choices.get('ac_drop'))} against {_pct(wiring.get('ac_drop_limit'))}")],
        ["Grid-side circuits", f"{_g(grid_circ)} per inverter × {units}", P(f"the grid feed to the inverter's AC input and the maintenance bypass: {_f(choices.get('ac_grid_current_a'), 1, 'A')} "
                                                                             + ("(the inverter's AC input rating)" if grid_known else "(the inverter's output: its AC input rating is not on the item)")
                                                                             + f"; breaker {_g(choices.get('ac_grid_breaker_a'), 'A')}; conductor {escape(str(choices.get('ac_grid_gauge') or BLANK))} mm² THHN ({amp(choices.get('ac_grid_gauge'))}); "
                                                                             f"drop {_pct(choices.get('ac_grid_drop'))}")],
        ["AC breakers", _item_text(_line(by_role, "ac_breaker")), P(escape(str((_line(by_role, "ac_breaker") or {}).get("note") or "")))],
        ["AC conductors", _item_text(thhn_l), P(escape(str((thhn_l or {}).get("note") or "")))],
    ]
    if _line(by_role, "thhn_grid"):
        ac_rows.append(["AC conductors, grid side", _item_text(_line(by_role, "thhn_grid")), P(escape(str(_line(by_role, "thhn_grid").get("note") or "")))])
    ac_rows += [
        ["AC disconnect", _item_text(_line(by_role, "ac_disconnect")), P(escape(str((_line(by_role, "ac_disconnect") or {}).get("note") or "")))],
        ["AC SPD", _item_text(_line(by_role, "ac_spd")), P(escape(str((_line(by_role, "ac_spd") or {}).get("note") or "")))],
        ["Transfer switch", "built into the inverter" if ats == "built-in" else _item_text(_line(by_role, "ats")), P(escape(str((_line(by_role, "ats") or {}).get("note") or "")) if ats != "built-in" else "the inverter's own transfer switch, as its item says")],
        ["Conduit and tray", f"{_item_text(_line(by_role, 'conduit'))}; {_item_text(_line(by_role, 'cable_tray'))}", P(f"conduit allowance {_g(conduit, 'm')}; conduit fill: {TO_COMPLETE}")],
    ]
    ac_t = table(["AC side", "Item or count", "Figures"], ac_rows, [32 * mm, 54 * mm, 104 * mm])

    bc = choices.get("battery_circuit") or {}
    bat_rows = []
    if kind != "net_metering" and bc:
        bat_rows = [
            ["Inverter battery current", _f(bc.get("current_a"), 0, "A"), P("the inverter's own limit when the item carries it, else its rated output over the battery voltage")],
            ["Battery breaker", _item_text(_line(by_role, "battery_breaker")), P(f"at least {_f(bc.get('breaker_min_a'), 0, 'A')} (1.25 × the current); chosen {_f(bc.get('breaker_a'), 0, 'A')}")],
            ["Battery cable", _item_text(_line(by_role, "battery_cable")), P(f"{escape(str(bc.get('cable_gauge') or BLANK))} mm² lug pairs, {_f(bc.get('cable_ampacity_a'), 0, 'A')} ampacity at or above the breaker; "
                                                                             f"{'coordinated' if bc.get('ok') else 'NOT coordinated (a hard warning holds the customer documents)'}")],
        ]
    bat_t = table(["Battery circuit", "Item or figure", "Notes"], bat_rows, [32 * mm, 64 * mm, 94 * mm]) if bat_rows else None

    gnd_rows = [
        ["Ground rod", _item_text(gnd_rod), P("electrode; the grounding electrode conductor size: " + TO_COMPLETE)],
        ["Array bonding", _item_text(bonding), P(escape(str((bonding or {}).get("note") or "")))],
        ["Earth lugs", _item_text(lugs), P(escape(str((lugs or {}).get("note") or "")))],
        ["Grounding run", f"{_g(gnd_run, 'm')} per inverter", P(f"on the {escape(str(choices.get('ac_gauge') or BLANK))} mm² THHN line of the AC circuits (the BOM's conductor); the equipment grounding conductor size: {TO_COMPLETE}")],
    ]
    gnd_t = table(["Grounding", "Item", "Notes"], gnd_rows, [32 * mm, 64 * mm, 94 * mm])
    drop_rows = [
        ["PV strings", _pct(choices.get("pv_drop")), _pct(wiring.get("dc_drop_limit")), f"{_g(pv_run, 'm')} per conductor"],
        ["Inverter output", _pct(choices.get("ac_drop")), _pct(wiring.get("ac_drop_limit")), f"{_g(ac_run, 'm')}"],
        ["Grid side", _pct(choices.get("ac_grid_drop")), _pct(wiring.get("ac_drop_limit")), f"{_g(ac_run, 'm')}"],
    ]
    drop_t = table(["Voltage drop (the BOQ's check)", "Drop", "Limit", "Run"], drop_rows, [60 * mm, 24 * mm, 24 * mm, 82 * mm])

    left_sched = [Paragraph("Equipment", h2), eq_t, Paragraph("DC side", h2), dc_t]
    if bat_t is not None:
        left_sched += [Paragraph("Battery circuit", h2), bat_t]
    right_sched = [Paragraph("AC side", h2), ac_t, Paragraph("Grounding and bonding", h2), gnd_t, Paragraph("Voltage drop", h2), drop_t]
    sched = Table([[left_sched, right_sched]], colWidths=[196 * mm, 194 * mm], hAlign="LEFT")
    sched.setStyle(two_col)
    story.append(sched)

    # ---------------- the last sheet: what is not here, and the audit's schedule of loads
    story.append(PageBreak())
    story.append(SheetMarker("Not yet in this set; schedule of loads"))
    story.append(Paragraph("Not yet in this set, and why", h1))
    panel_missing = [k for k, lbl in (("voc_v", "Voc"), ("vmp_v", "Vmp"), ("isc_a", "Isc"), ("imp_a", "Imp"), ("temp_coeff_voc_pct", "temperature coefficient of Voc")) if panel_item.get(k) in (None, "")]
    inv_missing = [k for k in ("max_pv_voltage_v", "mppt_min_v", "mppt_max_v", "mppt_count", "mppt_max_a") if inv_item.get(k) in (None, "")]
    panel_lbl = {"voc_v": "Voc", "vmp_v": "Vmp", "isc_a": "Isc", "imp_a": "Imp", "temp_coeff_voc_pct": "the temperature coefficient of Voc"}
    inv_lbl = {"max_pv_voltage_v": "the maximum PV voltage", "mppt_min_v": "the MPPT window (low)", "mppt_max_v": "the MPPT window (high)", "mppt_count": "the MPPT count", "mppt_max_a": "the current per MPPT"}
    datasheet_state = (
        ("the panel's " + ", ".join(panel_lbl[k] for k in panel_missing) if panel_missing else "the panel's data is on file")
        + "; " + ("the inverter's " + ", ".join(inv_lbl[k] for k in inv_missing) if inv_missing else "the inverter's data is on file")
    )
    missing = [
        ("Single-line diagram", f"Waits on the panel and inverter datasheets the owner enters on the Materials page: {datasheet_state}. "
                                "The circuit schedule sheet already carries every breaker, conductor and disconnect the diagram will show."),
        ("String table (Voc at the coldest cell, Vmp at the hottest, Isc per MPPT, the margins against the inverter's window)", f"The same datasheets: {datasheet_state}. "
         "The string count and the panels per string are on the layout sheets by the current rule."),
        ("Schedule of loads in the permit's format, with the PV system as a source and the point of interconnection",
         "The energy audit's figures are tabled on this sheet; the format, the circuit grouping and the point of interconnection are the signing engineer's."),
        ("Design analysis: conductor derating, OCPD per circuit beyond the breakers listed, conduit fill, the short-circuit note", TO_COMPLETE + "; the breakers, conductors and drops the BOQ computed are on the circuit schedule sheet."),
        ("Mounting detail (rail, foot, fastener, penetration seal) and the roof construction", "Not drawn. The mounting items and their counts are on the cover's general notes; the roof construction, purlin spacing and uplift check are not in the app yet."),
        ("Wind zone for the mounting", "Not in the app; " + TO_COMPLETE + "."),
        ("Vicinity map and site plan", f"Not in the set. The project pin is {doc.lat:.5f}, {doc.lon:.5f} ({escape(doc.address or BLANK)})."),
        ("Title sheet items beyond the signature block (PTR, TIN)", "Blank lines in the title block for the signing engineer; the company profile holds the PEE's name and PRC number only."),
    ]
    miss_t = Table([[P("Item", cellb), P("Why it is not here, and where it stands", cellb)]] + [[P(a, cellb), P(b)] for a, b in missing], colWidths=[70 * mm, 120 * mm], hAlign="LEFT")
    miss_t.setStyle(kv_style)
    left_last = [miss_t]

    apps = [a for a in (audit.get("appliances") or []) if a.get("status") in ("existing", "future", None)]
    right_last: list = [Paragraph("Schedule of loads: the energy audit's figures", h2)]
    if apps:
        bills = (audit.get("audit_vs_bill") or {}).get("bills") or []
        rows = []
        tot_w, tot_audit, tot_rec = 0.0, 0.0, 0.0
        for a in apps:
            qty = float(a.get("quantity") or 1)
            w = float(a.get("input_power_w") or 0)
            rows.append([P(escape(str(a.get("name") or ""))), "planned" if a.get("status") == "future" else "existing", _g(qty), _f(w, 0), _f(qty * w, 0),
                         _f(a.get("hours_per_day"), 1), _f(a.get("kwh_per_day_audit"), 2), _f(a.get("kwh_per_day_reconciled"), 2), _f(a.get("share_pct"), 0)])
            tot_w += qty * w
            tot_audit += float(a.get("kwh_per_day_audit") or 0)
            tot_rec += float(a.get("kwh_per_day_reconciled") or 0)
        rows.append([P("Total", cellb), "", "", "", _f(tot_w, 0), "", _f(tot_audit, 2), _f(tot_rec, 2), "100"])
        loads_t = table(["Appliance", "Status", "Qty", "W each", "W total", "h/day", "kWh/day (audit)", "kWh/day (to the bill)", "Share %"], rows,
                        [44 * mm, 20 * mm, 10 * mm, 16 * mm, 18 * mm, 14 * mm, 22 * mm, 26 * mm, 16 * mm])
        right_last.append(loads_t)
        peak = audit.get("peak_detail") or {}
        bill_txt = f"reconciled to the bill of {escape(str(bills[0].get('billing_month') or ''))} ({_f(bills[0].get('kwh'), 0, 'kWh')})" if bills else "no bill on the audit, so unreconciled"
        right_last.append(Paragraph(f"These are the audit's figures as calculated ({bill_txt}); connected load {_f(tot_w, 0, 'W')}, peak demand "
                                    f"{_f(peak.get('kw'), 2, 'kW')} at {escape(str(peak.get('label') or BLANK))} by the hourly profile. "
                                    f"The PV system as a source: {kwp:.2f} kWp of panels on {units} × {_rating(inv_l, 'kW')} inverter"
                                    + ("" if kind == "net_metering" else f", battery {_f(choices.get('battery_nominal_kwh'), 2, 'kWh')}") + ". The permit's schedule of loads is drawn up by the signing engineer.", small))
    else:
        right_last.append(Paragraph("The energy audit has no appliances yet, so there is no schedule of loads to table.", body))
    last = Table([[left_last, right_last]], colWidths=[196 * mm, 194 * mm], hAlign="LEFT")
    last.setStyle(two_col)
    story.append(last)

    # build
    buf = io.BytesIO()
    pdf = BaseDocTemplate(buf, pagesize=landscape(A3), leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN + TITLE_H,
                          title=f"PV system plans: {doc.customer_name or ''}", author=company.get("company_name", ""))
    frame = Frame(MARGIN, MARGIN + TITLE_H, FRAME_W, FRAME_H, leftPadding=4 * mm, rightPadding=4 * mm, topPadding=3 * mm, bottomPadding=2 * mm, id="sheet")
    pdf.addPageTemplates([PageTemplate(id="sheet", frames=[frame])])
    pdf.build(story, canvasmaker=_canvas_class(info))
    return buf.getvalue()
