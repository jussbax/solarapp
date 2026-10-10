"""The design analysis sheet of the plan set (round 13, docs/audits/round-13/engineer-brief.md, 2.2): one table, a row per
circuit of `pricing.choices.circuits` as the design analysis derated it (`pricing/design_analysis.py`), with pass, fail or
"not checked" and the reason in the last column; under it the short-circuit note, the grounding electrode conductor, the
tables used with their sources and their verify flags, and the assumptions. A3 landscape in the set's style; the title
block comes from the sheet frame `plans_pdf.py` draws on every page.

Nothing is derived here: every figure is the record's, a figure the analysis could not compute prints as a blank line
with its reason (and is recorded in the set's collector for the last sheet, round 13 review finding 5), and a pass is
never printed on an assumption alone (the brackets after "pass" name each one)."""
from __future__ import annotations

from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from ..schemas import AssessmentDoc
from . import brand
from .plans_blanks import BLANK, Blanks

SHEET_NAME = "Design analysis"
# the columns of 2.2, with their widths on the 392 mm the frame leaves between its paddings
COLUMNS: list[tuple[str, float]] = [
    ("Circuit", 28), ("Conductors (n × mm², type, insulation)", 36), ("Run", 12), ("Continuous A", 13), ("Design A (× 1.25; C1: 1.25 × 1.25 × Isc)", 13), ("Base ampacity (column)", 26),
    ("Ambient °C (+ rooftop adder)", 20), ("F_temp", 12), ("F_fill (n current-carrying)", 14), ("Derated A", 14), ("Terminal A (75 °C)", 16), ("OCPD A", 14),
    ("OCPD within the derated A? (next size up?)", 24), ("Drop %", 12), ("Conduit (code, inside Ø)", 28), ("Fill % / limit", 20), ("EGC required / provided", 24), ("Pass", 66),
]


def _g(v: Any, unit: str = "", nd: Optional[int] = None) -> str:
    if v is None or v == "":
        return BLANK
    try:
        x = float(v)
    except (TypeError, ValueError):
        return escape(str(v))
    s = f"{x:.{nd}f}" if nd is not None else f"{x:g}"
    return s + (f" {unit}" if unit else "")


def _yes(v: Optional[bool], yes: str = "holds", no: str = "FAILS") -> str:
    return BLANK if v is None else (yes if v else no)


def _pass_text(row: dict) -> str:
    """The Pass cell: "pass (every assumption and table to verify)", "FAIL: which checks", or "not checked: the reasons"."""
    checks = row.get("checks") or {}
    quals = list(row.get("qualifiers") or [])
    status = str(row.get("status") or "not checked")
    if status == "pass":
        return "pass" + (f" ({'; '.join(escape(q) for q in quals)})" if quals else "")
    if status == "fail":
        why = []
        if checks.get("ocpd_le_derated") is False and checks.get("next_size_up_used") is not True:
            why.append("the breaker is above the derated ampacity and the next-size-up rule does not apply: the breaker does not protect the conductor at temperature (conductor_derated, holds the customer documents)")
        if checks.get("terminal_ge_design") is False:
            why.append("the 75 °C terminal figure is below the design current or the breaker (terminal_ampacity, holds the customer documents)")
        if checks.get("fill_ok") is False:
            why.append("the conduit fill is over the limit (conduit_fill)")
        if checks.get("egc_ok") is False:
            why.append("the EGC provided is below the table (egc_undersized)")
        if checks.get("design_le_ocpd") is False or checks.get("ampacity_ge_ocpd") is False:
            why.append("the BOQ's own coordination fails (see the warnings)")
        return "FAIL: " + ("; ".join(escape(w) for w in why) or "a check fails (see the warnings)")
    # not checked: the reasons only; the checks that did compute show in their own columns, the assumptions in the conductor and ambient cells
    reasons = list(row.get("not_checked") or [])
    return "not checked: " + ("; ".join(escape(r) for r in reasons) if reasons else "the figures are not computed (calculate again)")


def _does_not_apply(row: dict) -> str:
    notes = [n for n in (row.get("notes") or []) if n]
    return "does not apply: " + escape(notes[0]) if notes else "does not apply"


def _values_text(values: Any) -> str:
    """A table's values in one line: "3.5 mm² 20 A, 5.5 mm² 30 A" or the nested columns on their own lines."""
    if values is None:
        return ""
    if isinstance(values, dict) and values and all(isinstance(v, dict) for v in values.values()):
        return "<br/>".join(f"{escape(str(k))}: " + ", ".join(f"{escape(str(a))}: {_g(b)}" for a, b in v.items()) for k, v in values.items())
    if isinstance(values, dict):
        return ", ".join(f"{escape(str(a))}: {_g(b)}" for a, b in values.items())
    return escape(str(values))


def analysis_sheet(doc: AssessmentDoc, results: dict, items: Optional[dict[str, dict]] = None, blanks: Optional[Blanks] = None) -> tuple[str, list]:
    """(the sheet's name, its flowables) for `plans_pdf.build_plans_pdf`, which puts them on their own sheet after the
    schedule sheets and before the last sheet with the set's frame and title block. `items` is the materials list by
    code, for the conduit's and conductor's names; `blanks` the set's collector of blank lines."""
    items = items or {}
    blanks = blanks if blanks is not None else Blanks()

    def blank(item: str, reason: str, **kw) -> str:
        """A blank line on this sheet, recorded with its reason for the last sheet (round 13 review, finding 5)."""
        return blanks.add(SHEET_NAME, item, reason, **kw)
    pricing = results.get("pricing") or {}
    choices = pricing.get("choices") or {}
    rows: list[dict] = list(choices.get("circuits") or [])
    da = choices.get("design_analysis") or {}
    F, FS, FB = brand.fonts()
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("da_h1", parent=ss["Title"], fontName=FB, fontSize=16, leading=19, spaceAfter=3, alignment=0, textColor=brand.BLACK)
    h2 = ParagraphStyle("da_h2", parent=ss["Heading2"], fontName=FB, fontSize=11, leading=13, spaceBefore=6, spaceAfter=3, textColor=brand.BLACK)
    body = ParagraphStyle("da_body", parent=ss["Normal"], fontName=F, fontSize=8.5, leading=11, textColor=brand.GRAY)
    small = ParagraphStyle("da_small", parent=ss["Normal"], fontName=F, fontSize=7.5, leading=9.5, textColor=brand.MUTED)
    cell = ParagraphStyle("da_cell", parent=ss["Normal"], fontName=F, fontSize=7, leading=8.5, textColor=brand.GRAY)
    cellb = ParagraphStyle("da_cellb", parent=cell, fontName=FS, textColor=brand.BLACK)
    note = ParagraphStyle("da_note", parent=body, fontSize=7.5, leading=9.5, leftIndent=8, firstLineIndent=-8, spaceAfter=2)
    grid = TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7), ("FONTNAME", (0, 0), (-1, -1), F), ("FONTNAME", (0, 0), (-1, 0), FB),
        ("BACKGROUND", (0, 0), (-1, 0), brand.OFF_WHITE), ("GRID", (0, 0), (-1, -1), 0.25, brand.LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ])
    kv_style = TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("FONTNAME", (0, 0), (-1, -1), F), ("LINEBELOW", (0, 0), (-1, -1), 0.25, brand.LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 2),
    ])
    two_col = TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                          ("RIGHTPADDING", (0, 0), (-2, -1), 6 * mm), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)])

    def P(t: str, st=cell) -> Paragraph:
        return Paragraph(t, st)

    def name_of(code: Any) -> str:
        it = items.get(str(code or "")) or {}
        return escape(str(it.get("name") or code or BLANK))

    story: list = [Paragraph("Design analysis: conductor derating, overcurrent protection, conduit fill and grounding", h1)]
    if not da:
        story.append(Paragraph("This calculation carries no design analysis (it was made before the analysis existed): calculate again to derate the circuits. "
                               "The rows below are the circuit records as the bill of materials wrote them, every derated figure a blank line.", body))
    else:
        amb = da.get("ambient") or {}
        story.append(Paragraph(f"Each circuit of the schedule (C1 upwards, the same numbers on every sheet) against the derating tables in Pricing settings › Design analysis: "
                               f"ampacity_derated = base (the insulation rating's column) × F_temp × F_fill; the breaker against it, the terminal rule, the conduit fill and the EGC. "
                               f"Outdoor ambient {_g(amb.get('outdoor_c'), '°C')} ({escape(str(amb.get('outdoor_basis') or ''))}); indoor {_g(amb.get('indoor_c'), '°C')} (an assumption). "
                               "A figure the app does not hold is a blank line with its reason; a pass names every assumption and every table still to verify beside it.", body))

    # ---- the table, a row per circuit
    data: list[list] = [[P(h, cellb) for h, _ in COLUMNS]]
    for r in rows:
        c = r.get("conductors") or {}
        checks = r.get("checks") or {}
        applies = bool(r.get("applies"))
        if not applies:
            data.append([P(f"<b>{escape(str(r.get('id')))}</b> {escape(str(r.get('name') or ''))}", cell)] + [P("—") for _ in COLUMNS[1:-1]] + [P(_does_not_apply(r))])
            continue
        size = c.get("size_mm2")
        cid, kind = str(r.get("id") or ""), str(r.get("kind") or "")
        reasons = "; ".join(str(x) for x in (r.get("not_checked") or [])) or "not computed (calculate again)"
        quals = [str(q) for q in (r.get("qualifiers") or [])]

        def cell_v(v: Any, column: str, unit: str = "", nd: Optional[int] = None, reason: Optional[str] = None) -> str:
            """A row's figure, else the blank line recorded with the row's "not checked" reasons (or the one given)."""
            return _g(v, unit, nd) if v not in (None, "") else blank(f"{cid}: {column}", reason or reasons)

        no_conductor = "no conductor on the BOM for this circuit (Pricing settings › BOM item roles)"
        type_txt = escape(str(c.get("type"))) if c.get("type") else blank(f"{cid}: conductor type", no_conductor)
        cond_txt = (f"{cell_v(c.get('n_total'), 'conductor count', reason=no_conductor)} × {_g(size)} mm² {type_txt}" if size is not None
                    else f"{cell_v(c.get('n_total'), 'conductor count', reason=no_conductor)} × {blank(f'{cid}: conductor size', no_conductor)} {escape(str(c.get('type') or ''))}".strip())
        count = int(r.get("count") or 0)
        circuit_txt = f"<b>{escape(cid)}</b> {escape(str(r.get('name') or ''))}" + (f"<br/>× {count}" if count > 1 else "")
        egc_req_reason = "not computed without the breaker's rating" if r.get("ocpd_a") is None else reasons
        egc_prov_reason = next((n for n in (r.get("not_checked") or []) if "EGC" in str(n)), "no item for the role (Pricing settings › BOM item roles)")
        egc_txt = (f"{cell_v(r.get('egc_required_mm2'), 'EGC required', 'mm²', reason=egc_req_reason)} / {cell_v(r.get('egc_provided_mm2'), 'EGC provided', 'mm²', reason=egc_prov_reason)}"
                   + (f"<br/>{escape(str(r.get('egc_provided_code')))}" if r.get("egc_provided_code") else ""))
        if kind == "egc":
            # the grounding run carries no current: the derating cells do not apply (and record nothing); its own size against the largest EGC the circuits need
            na = "n/a"
            cond_txt = f"{cell_v(c.get('n_total'), 'conductor count', reason=no_conductor)} × {cell_v(size, 'conductor size', reason=no_conductor)} mm² {type_txt} (the grounding run)" + (f"<br/>{escape(str(r.get('egc_provided_code')))}" if r.get("egc_provided_code") else "")
            data.append([P(circuit_txt), P(cond_txt), P(cell_v(r.get("run_m"), "run", "m", reason="no grounding run on the record")), P(na), P(na), P(na), P(na), P(na), P(na), P(na), P(na), P(na), P(na), P(na), P("with the AC circuits"), P(na),
                         P(egc_txt), P(_pass_text(r))])
            continue
        cond_txt += f", {cell_v(c.get('insulation_c'), 'insulation rating', '°C')}" + (" (assumed)" if any("insulation assumed" in q for q in quals) else "")
        if r.get("conductor_code"):
            cond_txt += f"<br/>{escape(str(r['conductor_code']))}"
        base_txt = cell_v(r.get("ampacity_base_a"), "base ampacity", "A") + (f"<br/>{escape(str(r.get('ampacity_base_column')))}" if r.get("ampacity_base_column") else "")
        amb_txt = cell_v(r.get("ambient_c"), "ambient") + (f" + {_g(r.get('rooftop_adder_c'))} = {_g(r.get('t_conductor_c'))}" if r.get("rooftop_adder_c") else "")
        if r.get("placement"):
            amb_txt += f"<br/>{escape(str(r['placement']).replace('_', ' '))}"
        ffill_txt = cell_v(r.get("f_fill"), "F_fill", nd=2) + (f" ({_g(c.get('n_current_carrying'))} cc)" if c.get("n_current_carrying") is not None else "")
        ocpd_reason = "the breaker's rating is not checked without Isc on file (the datasheet)" if kind == "dc_pv" else "no breaker rating on the record"
        ocpd_txt = cell_v(r.get("ocpd_a"), "OCPD rating", "A", reason=ocpd_reason) + (f"<br/>{escape(str(r.get('ocpd_code')))}" if r.get("ocpd_code") else "")
        if checks.get("ocpd_le_derated") is None:
            le_txt = blank(f"{cid}: OCPD within the derated ampacity", reasons) + "<br/>not checked"
        elif checks.get("ocpd_le_derated"):
            le_txt = "yes"
        elif checks.get("next_size_up_used"):
            le_txt = "no; next size up: yes (allowed)"
        else:
            le_txt = "NO; next size up: no (FAIL)"
        terminal_reason = next((q for q in quals if "column" in q and "terminal" in q), None)
        term_txt = cell_v(r.get("ampacity_terminal_a"), "terminal ampacity (75 °C)", "A", reason=terminal_reason or reasons)
        placement = str(r.get("placement") or "")
        if placement.endswith("_conduit"):
            conduit_txt = (f"{escape(str(r.get('conduit_code')))} {name_of(r.get('conduit_code'))}" if r.get("conduit_code") else "no conduit on the BOM")
            bore_reason = f"not on the conduit item {r.get('conduit_code') or '(none on the BOM)'} (Materials page)"
            conduit_txt += f"<br/>inside Ø {cell_v(r.get('conduit_inner_diameter_mm'), 'conduit inside diameter', 'mm', reason=bore_reason)}" + ("" if r.get("conduit_inner_diameter_mm") is not None else " (not on the item)")
            fill_txt = (f"{float(r['fill_pct']):.1f} % / {_g(r.get('fill_limit_pct'))} %" if r.get("fill_pct") is not None else f"{blank(f'{cid}: conduit fill', reasons)} / {_g(r.get('fill_limit_pct'))} %<br/>not checked")
        else:
            conduit_txt = "free air"
            fill_txt = "n/a"
        if kind == "dc_battery":
            run_txt, drop_txt = "lug pairs", "n/a (on ampacity)"
        else:
            run_txt = cell_v(r.get("run_m"), "run", "m", reason="no run on the record")
            drop_txt = f"{float(r['drop_pct']) * 100:.1f} %" if r.get("drop_pct") is not None else blank(f"{cid}: voltage drop", "the BOQ computed no drop for this circuit")
        data.append([
            P(circuit_txt), P(cond_txt), P(run_txt), P(cell_v(r.get("i_continuous_a"), "continuous current", "A", 2, reason="no current on the record")), P(cell_v(r.get("i_design_a"), "design current", "A", 2, reason="no current on the record")), P(base_txt), P(amb_txt),
            P(cell_v(r.get("f_temp"), "F_temp", nd=3)), P(ffill_txt), P(cell_v(r.get("ampacity_derated_a"), "derated ampacity", "A", 1)), P(term_txt), P(ocpd_txt), P(le_txt), P(drop_txt),
            P(conduit_txt), P(fill_txt), P(egc_txt), P(_pass_text(r)),
        ])
    if not rows:
        data.append([P("no circuits")] + [P("—") for _ in COLUMNS[1:-1]] + [P("the bill of materials wrote no circuit records: calculate again")])
    t = Table(data, colWidths=[w * mm for _, w in COLUMNS], hAlign="LEFT", repeatRows=1)
    t.setStyle(grid)
    story.append(t)
    story.append(Spacer(1, 2 * mm))

    # ---- the four notes under the table, in three columns so the sheet stays one page: the short-circuit note and the GEC;
    # the tables used with their sources and flags; the assumptions and how to read the Pass column
    sc = da.get("short_circuit") or {}
    gec = da.get("gec") or {}
    left: list = [Paragraph("Short-circuit", h2)]
    if sc:
        inv, bat = sc.get("inverter") or {}, sc.get("battery") or {}
        # the engine writes the word BLANK where a figure is missing; the sheet prints the set's blank line and records each
        utility = str(sc.get("utility_text") or "BLANK")
        if "BLANK" in utility:
            utility = utility.replace("BLANK", blank("the DU's available fault current at the service", "from the DU, typed on the Site step › Service entrance; verify"))
        left.append(Paragraph(f"1. The utility's available fault current at the service: {escape(utility)}.", note))
        left.append(Paragraph("2. The inverter's contribution: " + (escape(str(inv.get("text"))) if inv else "no inverter on the BOM") + ".", note))
        bat_text = str(bat.get("text") or "")
        if "BLANK" in bat_text:
            bat_text = bat_text.replace("BLANK", blank("the battery's short-circuit trip", "not on the battery item (Materials page); verify with the maker"))
        left.append(Paragraph("3. The battery's contribution: " + (escape(bat_text) if bat else "no battery on this job") + ".", note))
        aic = str(sc.get("aic_text") or "BLANK")
        for a in sc.get("aic") or []:
            if a.get("aic_ka") is None and f"{a.get('code')} BLANK" in aic:
                aic = aic.replace(f"{a.get('code')} BLANK", f"{a.get('code')} " + blank(f"interrupting rating (AIC) of {a.get('code')}", "not on the breaker item (Materials page)"), 1)
        if "BLANK" in aic:
            codes = ", ".join(str(a.get("code")) for a in (sc.get("aic") or [])) or "the breakers"
            aic = aic.replace("BLANK", blank(f"interrupting ratings (AIC) of {codes}", "not on the breaker items (Materials page)"))
        left.append(Paragraph("4. " + escape(aic) + ".", note))
    else:
        left.append(Paragraph(f"Not computed: {blank('the short-circuit note', 'no design analysis on this calculation: calculate again')}", note))
    left.append(Paragraph("Grounding electrode conductor", h2))
    gec_text = str(gec.get("text") or "BLANK")
    if "BLANK" in gec_text:
        gec_text = gec_text.replace("BLANK", blank("the grounding electrode conductor", "no grounding run on the BOM (the hard ac_circuit warning)" if gec else "no design analysis on this calculation: calculate again"))
    left.append(Paragraph(escape(gec_text) + ".", note))
    middle: list = [Paragraph("The tables used, with their sources", h2)]
    tbl_rows: list[list] = [[P("Table", cellb), P("Source", cellb), P("Values", cellb), P("Flag", cellb)]]
    for tb in da.get("tables") or []:
        flag = "confirmed in Settings" if tb.get("verified") else "VERIFY"
        tbl_rows.append([P(escape(str(tb.get("label") or ""))), P(escape(str(tb.get("source") or ""))), P(_values_text(tb.get("values"))), P(flag, cellb if not tb.get("verified") else cell)])
    if len(tbl_rows) == 1:
        tbl_rows.append([P("—"), P("no tables recorded with this calculation"), P(""), P("")])
    tt = Table(tbl_rows, colWidths=[26 * mm, 110 * mm, 46 * mm, 18 * mm], hAlign="LEFT")
    tt.setStyle(kv_style)
    middle.append(tt)
    right: list = [Paragraph("Assumptions", h2)]
    assumptions = list(da.get("assumptions") or [])
    if assumptions:
        for a in assumptions:
            right.append(Paragraph("assumption: " + escape(str(a)), note))
    else:
        right.append(Paragraph("none recorded with this calculation", note))
    block = Table([[left, middle, right]], colWidths=[96 * mm, 200 * mm, 96 * mm], hAlign="LEFT")
    block.setStyle(two_col)
    story.append(block)
    # the legend on its own, after the block, so it never drags the block to a second page
    story.append(Paragraph("<b>How to read the Pass column.</b> <b>pass</b>: every check computed and holding; the brackets name each assumption used and each table still to verify, "
                           "so a pass never stands on an assumption alone. <b>FAIL</b>: a check fails; a conductor the breaker does not protect at temperature, a terminal figure "
                           "below the load and a breaker whose interrupting rating is below the DU's fault level (the short-circuit note, aic_below_fault) hold the customer documents "
                           "(the same class as the AC coordination), a conduit over its fill limit and an undersized EGC print without "
                           "holding them. <b>not checked</b>: a figure the app does not hold; the reason names the item field to type (Materials page), the datasheet figure (the "
                           "panel's Isc) or the BOM role missing (the battery rack's EGC). Every table above is a cited stand-in from the NEC edition the PEC follows until the owner or the signing engineer ticks it confirmed under "
                           "Pricing settings › Design analysis; the signing engineer replaces every assumption before sealing.", small))
    return SHEET_NAME, story
