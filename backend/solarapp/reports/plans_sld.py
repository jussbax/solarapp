"""The single-line diagram sheet of the plans for the PEE (round 13, docs/audits/round-13/engineer-brief.md, item 1):
one horizontal bus from the array to the two-way meter, every device a balloon-numbered symbol that matches a row of
`pricing.choices.circuits` and of the schedule (C1 …), drawn with ReportLab primitives in the set's frame.

Nothing invented: every figure comes from `pricing.choices` (the string design, the breakers, the gauges, the runs),
the BOM lines by role, the materials list and the survey's service block (`doc.service`); a figure the app does not
hold prints as a blank line with its reason beside it, a device whose role has no item prints its role name and "no
item in the materials list". The symbols are IEC 60617-style simple shapes, each named in the legend, and the legend
says to verify the symbol set against the DU's sample; the placard wording carries "verify the DU's wording"; the 120 %
rule at the point of interconnection prints its arithmetic and PASS or FAIL (a hard warning, never a block).

`sld_sheet` is the one hook `plans_pdf.build_plans_pdf` calls: it returns the sheet's name and its flowables."""
from __future__ import annotations

import re
from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph, Spacer, Table

from ..pricing.service_checks import INTERCONNECTION_LABEL, poi_busbar_check
from . import brand
from .plans_pdf import BLANK, TO_COMPLETE, _amps_in, _f, _g, _line, _lines_by_role

SHEET_NAME = "Single-line diagram"
DRAW_W_MM = 392.0           # the frame's content width (400 mm less the 4 mm paddings)
DRAW_H_MM = 150.0
# line weights the brief fixes: buses and outlines 0.7, symbols 0.5, leaders 0.35 / 0.25
W_BUS, W_SYM, W_LEAD, W_THIN = 0.7, 0.5, 0.35, 0.25
FS = 7.0                    # label text (the brief's 7 pt floor); the tags inside symbols are 6 pt so they fit the symbol
TAG = 6.0
BAL_R = 2.1                 # the balloon's radius, mm
VERIFY_SYMBOLS = "Symbols: IEC 60617-style simple shapes drawn by the office system; verify the symbol set against the DU's sample (the PEC prescribes none)."
VERIFY_WORDING = "verify the DU's wording"
NO_ITEM = "NO-ITEM-"


# ---------------------------------------------------------------- small helpers

def _fit(text: str, font: str, size: float, width: float) -> str:
    if pdfmetrics.stringWidth(text, font, size) <= width:
        return text
    while text and pdfmetrics.stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _wrap(text: str, font: str, size: float, width: float, max_lines: int = 6) -> list[str]:
    """Word-wrap to the width in points; the last line is trimmed with an ellipsis when the text runs past max_lines."""
    words = str(text).split()
    lines: list[str] = []
    cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and pdfmetrics.stringWidth(t, font, size) > width:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [_fit(" ".join(lines[max_lines - 1:]), font, size, width)]
    return [_fit(ln, font, size, width) for ln in lines]


def _volts_in(name: Any) -> Optional[float]:
    """The voltage an item's name states ("DC SPD 2P 600V" → 600); None when none."""
    m = re.findall(r"(\d+(?:\.\d+)?)\s*V\b", str(name or ""))
    return max(float(x) for x in m) if m else None


def _has_item(l: Optional[dict]) -> bool:
    return l is not None and not str(l.get("code") or "").startswith(NO_ITEM) and l.get("found", True)


def _code(l: Optional[dict], role: str) -> str:
    """The item's code for a drawing label, or the role's "no item" line (plain text: the Drawing's String is not XML)."""
    return str(l.get("code")) if _has_item(l) else f"{role}: no item in the materials list"


def _mppt_inputs(inv: dict) -> list[Optional[float]]:
    """The inverter's inputs by current rating from the item: the per-input figures when typed ("18/36/36"), else the
    single maximum over the MPPT count, else one unrated input per MPPT, else one unknown input."""
    text = str(inv.get("mppt_currents_a") or "").strip()
    if text:
        try:
            return [float(x) for x in text.split("/") if x.strip()]
        except ValueError:
            pass
    n = int(inv.get("mppt_count") or 0)
    if n and inv.get("mppt_max_a"):
        return [float(inv["mppt_max_a"])] * n
    if n:
        return [None] * n
    return [None]


class _Sld:
    """The diagram's canvas: a Drawing in millimetres with the brand's fonts and the brief's line weights."""

    def __init__(self, w_mm: float, h_mm: float):
        self.F, self.FS, self.FB = brand.fonts()
        self.d = Drawing(w_mm * mm, h_mm * mm)
        self.d.hAlign = "LEFT"
        self.H = h_mm

    # ---- primitives (coordinates in mm)
    def line(self, x1: float, y1: float, x2: float, y2: float, w: float = W_BUS, dash: Optional[list] = None, color=brand.BLACK) -> None:
        self.d.add(Line(x1 * mm, y1 * mm, x2 * mm, y2 * mm, strokeColor=color, strokeWidth=w, strokeDashArray=dash))

    def vline_jumping(self, x: float, y_top: float, y_bot: float, crossings: list[float], w: float = W_LEAD) -> None:
        """A vertical that breaks 0.9 mm either side of each horizontal line it crosses (a crossing, not a junction)."""
        ys = sorted((c for c in crossings if y_bot + 0.9 < c < y_top - 0.9), reverse=True)
        y = y_top
        for c in ys:
            self.line(x, y, x, c + 0.9, w)
            y = c - 0.9
        self.line(x, y, x, y_bot, w)

    def poly(self, pts: list[tuple[float, float]], w: float = W_SYM, dash: Optional[list] = None, fill=None, color=brand.BLACK) -> None:
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            self.line(x1, y1, x2, y2, w, dash, color)
        if fill is not None:
            self.d.add(Polygon([c * mm for p in pts for c in p], fillColor=fill, strokeColor=None))

    def rect(self, x: float, y: float, w: float, h: float, lw: float = W_SYM, dash: Optional[list] = None, fill=None, color=brand.BLACK) -> None:
        self.d.add(Rect(x * mm, y * mm, w * mm, h * mm, fillColor=fill, strokeColor=color, strokeWidth=lw, strokeDashArray=dash))

    def circle(self, x: float, y: float, r: float, lw: float = W_SYM, fill=colors.white, color=brand.BLACK) -> None:
        self.d.add(Circle(x * mm, y * mm, r * mm, fillColor=fill, strokeColor=color, strokeWidth=lw))

    def dot(self, x: float, y: float, r: float = 0.7) -> None:
        self.d.add(Circle(x * mm, y * mm, r * mm, fillColor=brand.BLACK, strokeColor=None))

    def text(self, x: float, y: float, s: str, size: float = FS, font: Optional[str] = None, color=brand.GRAY, anchor: str = "start") -> None:
        self.d.add(String(x * mm, y * mm, s, fontName=font or self.F, fontSize=size, fillColor=color, textAnchor=anchor))

    def stack(self, x: float, y_top: float, lines: list[str], width_mm: float, size: float = FS, anchor: str = "middle", bold_first: bool = False,
              color=brand.GRAY) -> float:
        """Lines of text downward from y_top (the first baseline), each wrapped to width_mm; returns the next baseline."""
        step = size * 0.42           # mm per line: 2.94 at 7 pt
        y = y_top
        first = True
        for raw in lines:
            font = self.FS if (bold_first and first) else self.F
            for ln in _wrap(raw, font, size, width_mm * mm):
                self.text(x, y, ln, size, font, brand.BLACK if (bold_first and first) else color, anchor)
                y -= step
            first = False
        return y

    def balloon(self, x: float, y: float, label: str) -> None:
        """The circuit balloon: a white circle with the number in bold, matching the schedule's row."""
        self.circle(x, y, BAL_R, W_SYM, colors.white)
        self.text(x, y - 0.75, label, TAG, self.FB, brand.BLACK, "middle")

    # ---- the symbols (IEC 60617-style simple shapes)
    def module(self, x: float, y: float, w: float = 6.2, h: float = 4.2) -> None:
        """The photovoltaic module: a rectangle carrying the cell (long and short plates) and two incoming arrows."""
        self.rect(x, y - h / 2, w, h, W_SYM, fill=colors.white)
        cx = x + w * 0.58
        self.line(cx - 0.6, y - 1.3, cx - 0.6, y + 1.3, W_SYM)          # the long plate
        self.line(cx + 0.6, y - 0.6, cx + 0.6, y + 0.6, W_BUS)          # the short plate
        self.line(x + 0.6, y + h / 2 - 0.6, cx - 1.1, y + 0.4, W_THIN)  # the cell's lead
        for k in (0, 1):                                                # the two arrows of light
            ax, ay = x - 1.6 + k * 1.1, y + h / 2 + 2.0 - k * 1.0
            bx, by = ax + 1.3, ay - 1.3
            self.line(ax, ay, bx, by, W_THIN)
            self.poly([(bx, by), (bx - 0.75, by + 0.1), (bx - 0.1, by + 0.75)], W_THIN, fill=brand.BLACK)

    def breaker(self, x: float, y: float, horizontal: bool = True, poles: int = 2, length: float = 7.0) -> None:
        """A circuit-breaker: the line opens at a contact drawn inclined, a cross at its hinge; two poles side by side
        joined by a dashed link. Centred on (x, y) along the line it sits in."""
        half = length / 2
        off = [0.0] if poles == 1 else [-1.1, 1.1]
        for o in off:
            if horizontal:
                yy = y + o
                self.line(x - half, yy, x - 1.6, yy, W_BUS)
                self.line(x - 1.6, yy, x + 1.4, yy + 2.0, W_SYM)       # the open contact
                self.line(x + 1.6, yy, x + half, yy, W_BUS)
                self.line(x - 2.2, yy - 0.6, x - 1.0, yy + 0.6, W_SYM)  # the cross at the hinge
                self.line(x - 2.2, yy + 0.6, x - 1.0, yy - 0.6, W_SYM)
            else:
                xx = x + o
                self.line(xx, y + half, xx, y + 1.6, W_BUS)
                self.line(xx, y + 1.6, xx + 2.0, y - 1.4, W_SYM)
                self.line(xx, y - 1.6, xx, y - half, W_BUS)
                self.line(xx - 0.6, y + 2.2, xx + 0.6, y + 1.0, W_SYM)
                self.line(xx + 0.6, y + 2.2, xx - 0.6, y + 1.0, W_SYM)
        if poles > 1:   # the mechanical link
            if horizontal:
                self.line(x + 0.2, y - 0.1, x + 0.2, y + 2.1, W_THIN, dash=[0.6, 0.6])
            else:
                self.line(x - 0.1, y + 0.2, x + 2.1, y + 0.2, W_THIN, dash=[0.6, 0.6])

    def isolator(self, x: float, y: float, length: float = 8.0) -> None:
        """A disconnect (isolator): the open contact with the bar at its free end, in a dashed box (lockable)."""
        half = length / 2
        self.rect(x - half - 1.0, y - 3.2, length + 2.0, 6.4, W_THIN, dash=[1.0, 0.8])
        self.line(x - half, y, x - 1.6, y, W_BUS)
        self.line(x - 1.6, y, x + 1.6, y + 2.2, W_SYM)
        self.line(x + 1.6, y - 1.0, x + 1.6, y + 1.0, W_SYM)
        self.line(x + 1.6, y, x + half, y, W_BUS)

    def spd(self, x: float, y_top: float, y_bar: float, crossings: Optional[list[float]] = None) -> None:
        """A surge-protective device between the line and the earth bar: a rectangle with the arrowed diagonal; the
        stub jumps the horizontal lines it crosses."""
        h, w = 5.0, 2.6
        yc = y_bar + 6.5
        self.vline_jumping(x, y_top, yc + h / 2, crossings or [])
        self.rect(x - w / 2, yc - h / 2, w, h, W_SYM, fill=colors.white)
        self.line(x - w / 2 - 0.6, yc - h / 2 - 0.4, x + w / 2 + 0.6, yc + h / 2 + 0.4, W_SYM)
        tx, ty = x + w / 2 + 0.6, yc + h / 2 + 0.4
        self.poly([(tx, ty), (tx - 1.1, ty - 0.1), (tx - 0.3, ty - 1.0)], W_THIN, fill=brand.BLACK)
        self.line(x, yc - h / 2, x, y_bar, W_LEAD)

    def inverter(self, x: float, y: float, side: float = 22.0) -> None:
        """The DC/AC converter: a square split by its diagonal, "=" in the upper-left half and "~" in the lower-right."""
        self.rect(x, y, side, side, W_BUS, fill=colors.white)
        self.line(x, y, x + side, y + side, W_SYM)
        self.text(x + side * 0.24, y + side * 0.62, "=", 11, self.FB, brand.BLACK, "middle")
        self.text(x + side * 0.74, y + side * 0.2, "~", 11, self.FB, brand.BLACK, "middle")

    def battery(self, x: float, y: float, units: int = 1) -> float:
        """A battery: alternating long and short plates between the terminals, one group per unit side by side; returns
        the right-hand end's x."""
        xx = x
        for u in range(max(units, 1)):
            if u:
                self.line(xx, y, xx + 2.2, y, W_BUS)
                xx += 2.2
            for _ in range(2):
                self.line(xx, y - 2.6, xx, y + 2.6, W_SYM)               # long plate
                self.line(xx + 1.4, y - 1.2, xx + 1.4, y + 1.2, W_BUS)   # short plate
                xx += 2.8
        return xx - 1.4

    def earth(self, x: float, y_top: float) -> None:
        """The earth electrode: the line down to three bars of decreasing length."""
        self.line(x, y_top, x, y_top - 3.0, W_SYM)
        for k, half in enumerate((2.4, 1.6, 0.8)):
            yy = y_top - 3.0 - k * 1.1
            self.line(x - half, yy, x + half, yy, W_SYM)

    def meter(self, x: float, y: float, two_way: bool) -> None:
        """The kWh meter: a circle with "kWh"; two arrows for a two-way meter, one for a meter that only reads imports."""
        r = 4.6
        self.circle(x, y, r, W_BUS)
        self.text(x, y - 1.0, "kWh", TAG, self.FB, brand.BLACK, "middle")
        ya = y + r + 1.4
        self.line(x - 3.0, ya, x + 3.0, ya, W_SYM)
        self.poly([(x - 3.0, ya), (x - 1.9, ya + 0.7), (x - 1.9, ya - 0.7)], W_THIN, fill=brand.BLACK)
        if two_way:
            self.poly([(x + 3.0, ya), (x + 1.9, ya + 0.7), (x + 1.9, ya - 0.7)], W_THIN, fill=brand.BLACK)

    def ats(self, x: float, y: float, w: float = 14.0, h: float = 9.0) -> None:
        """A transfer switch: a box with two inputs (the inverter on the line, the bypass from above) and one output; the
        blade drawn to the line's input."""
        self.rect(x - w / 2, y - h / 2, w, h, W_BUS, fill=colors.white)
        self.line(x - w / 2, y, x - w / 2 + 3.0, y, W_SYM)
        self.line(x - w / 2 + 3.0, y, x + w / 2 - 3.5, y + 1.8, W_SYM)
        self.dot(x + w / 2 - 3.5, y, 0.6)
        self.line(x + w / 2 - 3.5, y, x + w / 2, y, W_SYM)
        self.line(x - w / 2 + 3.0, y + h / 2, x - w / 2 + 3.0, y + 2.4, W_SYM)      # the second input, from the top
        self.dot(x - w / 2 + 3.0, y + 2.4, 0.6)
        self.text(x, y - h / 2 + 1.2, "ATS", TAG, self.FB, brand.BLACK, "middle")

    def mc4(self, x: float, y: float) -> None:
        """A connector pair: two small bodies that meet on the lead."""
        self.rect(x - 2.0, y - 0.8, 1.7, 1.6, W_THIN, fill=colors.white)
        self.rect(x + 0.3, y - 0.8, 1.7, 1.6, W_THIN, fill=brand.BLACK)


# ---------------------------------------------------------------- the data behind the sheet

def _figures(doc: Any, results: dict, items: dict[str, dict], cfg: dict) -> dict:
    """Everything the diagram and its tables print, read once from the results, the items and the survey."""
    pricing = results.get("pricing") or {}
    sizing = results.get("sizing") or {}
    choices = pricing.get("choices") or {}
    wiring = cfg.get("wiring") or {}
    roles = cfg.get("roles") or {}
    by_role = _lines_by_role(pricing)
    kind = str(sizing.get("kind") or choices.get("kind") or "")
    panel_l, inv_l, bat_l = _line(by_role, "panel"), _line(by_role, "inverter"), _line(by_role, "battery")
    item = lambda l: items.get(str((l or {}).get("code") or "")) or {}  # noqa: E731
    panel_item, inv_item, bat_item = item(panel_l), item(inv_l), item(bat_l)
    sdn = choices.get("string_design") or {}
    sc = sdn.get("current") or {}
    circuits = {str(c.get("id")): c for c in (choices.get("circuits") or [])}
    service = getattr(doc, "service", None)
    svc = service.model_dump() if hasattr(service, "model_dump") else dict(service or {})
    poi = choices.get("poi_busbar") or poi_busbar_check(svc, choices)[0]
    strings = int(choices.get("strings") or 0)
    per_string = int(choices.get("panels_per_string") or 0)
    panels_n = int(sizing.get("panels") or 0)
    lengths = [per_string] * strings
    if strings > 1 and per_string:
        lengths[-1] = max(panels_n - per_string * (strings - 1), 0) or per_string
    units = int(choices.get("inverter_units") or (inv_l or {}).get("qty") or 1)
    inputs = _mppt_inputs(inv_item) * max(units, 1)
    per_mppt = sdn.get("per_mppt") or []
    return {
        "pricing": pricing, "sizing": sizing, "choices": choices, "wiring": wiring, "roles": roles, "by_role": by_role, "kind": kind,
        "panel_l": panel_l, "inv_l": inv_l, "bat_l": bat_l, "panel_item": panel_item, "inv_item": inv_item, "bat_item": bat_item,
        "sdn": sdn, "sc": sc, "circuits": circuits, "svc": svc, "poi": poi, "strings": strings, "per_string": per_string, "lengths": lengths,
        "units": units, "inputs": inputs, "per_mppt": per_mppt, "panels_n": panels_n,
        "watt": (panel_l or {}).get("rating"), "kwp": float((pricing.get("totals") or {}).get("kwp") or sizing.get("kwp") or 0),
        "items": items,
    }


def _assign_inputs(strings: int, n_inputs: int) -> list[int]:
    """String k (0-based) sits on input k mod n (the BOQ's round-robin, design_checks.mppt_assignment)."""
    n = max(n_inputs, 1)
    return [k % n for k in range(strings)]


def poi_lines(poi: dict) -> list[str]:
    """The 120 % rule as the sheets print it, one short line per step so a wrapped label keeps each figure whole: the
    arithmetic, the limit and PASS or FAIL, or why it is not checked."""
    if not poi.get("checked"):
        return [f"120 % rule: not checked — {poi.get('reason') or 'no figures'}"]
    units = f" × {poi['units']}" if int(poi.get("units") or 1) > 1 else ""
    return [f"120 %: {_g(poi['grid_breaker_a'])} A{units} + {_g(poi['main_breaker_a'])} A = {_g(poi['sum_a'])} A",
            f"limit {_g(poi['factor'])} × {_g(poi['busbar_a'])} A = {_g(poi['limit_a'])} A",
            f"{'PASS' if poi['ok'] else 'FAIL'}; verify the PEC clause"]


# ---------------------------------------------------------------- the drawing

def sld_drawing(fig: dict) -> Drawing:   # noqa: C901  (one function per sheet, as drawings.py does)
    s = _Sld(DRAW_W_MM, DRAW_H_MM)
    F, FB = s.F, s.FB
    ch, svc, poi, sdn, sc = fig["choices"], fig["svc"], fig["poi"], fig["sdn"], fig["sc"]
    pi, ii, bi = fig["panel_item"], fig["inv_item"], fig["bat_item"]
    by_role, circuits, kind = fig["by_role"], fig["circuits"], fig["kind"]
    strings, per_string, lengths, units = fig["strings"], fig["per_string"], fig["lengths"], fig["units"]
    wiring = fig["wiring"]
    items = fig["items"]
    rating_of = lambda l: _amps_in(items.get(str((l or {}).get("code") or ""), {})) if l else None  # noqa: E731

    # ---- the bands (mm): the grid line above, the bus, the battery row and the earth bar below
    BUS, GRID_Y, BAT_Y, EARTH_Y = 96.0, 126.0, 38.0, 11.0
    ROW_STEP = 19.0                        # between drawn string rows

    # ---- 1. the array: one drawn string per distinct length, the rest "alike"
    distinct: list[tuple[int, list[int]]] = []
    for k, n in enumerate(lengths):
        for ln, ks in distinct:
            if ln == n:
                ks.append(k)
                break
        else:
            distinct.append((n, [k]))
    too_many = len(distinct) > 3
    drawn = distinct[:3] if not too_many else distinct[:1]
    if not drawn:
        drawn = [(0, [0])]
    watt_txt = _g(fig["watt"], "W")
    voc, vmp, isc, imp = pi.get("voc_v"), pi.get("vmp_v"), pi.get("isc_a"), pi.get("imp_a")
    t_cold, voc_cold = sdn.get("t_cold_c"), sdn.get("voc_cold_v")
    from_ds = sc.get("source") == "datasheet"
    array_x0, array_x1, lead_x = 3.0, 84.0, 118.0
    row_ys: list[float] = []
    for r, (n, ks) in enumerate(drawn):
        y = BUS - r * ROW_STEP
        row_ys.append(y)
        n_draw = max(n, 1)
        w_m, gap = 6.2, 1.1
        if n_draw * w_m + (n_draw - 1) * gap > array_x1 - array_x0 - 2:
            w_m = (array_x1 - array_x0 - 2 - (n_draw - 1) * gap) / n_draw
        x = array_x0
        for k in range(n_draw):
            s.module(x, y, w_m)
            if k < n_draw - 1:
                s.line(x + w_m, y, x + w_m + gap, y, W_SYM)
            x += w_m + gap
        chain_end = x - gap
        names = ", ".join(f"S{k + 1}" for k in ks[:4]) + (" …" if len(ks) > 4 else "")
        head = f"{names}: {n} × {watt_txt}" if n else f"S1: {BLANK} × {watt_txt} (the system is not sized)"
        if len(ks) > 1:
            head += f" ({len(ks)} alike, one drawn)"
        if not from_ds:
            head += " (rule)"
        s.stack(array_x0, y + 8.8, [head], 84, FS, "start", bold_first=True)
        if r == 0:
            data = (f"Voc {_f(voc, 1, 'V')} STC, {_f(voc_cold, 1, 'V')} at {_g(t_cold, '°C')}; Vmp {_f(vmp, 1, 'V')}; Isc {_f(isc, 2, 'A')}; Imp {_f(imp, 2, 'A')}"
                    if from_ds else f"Voc {BLANK} STC, {BLANK} at {_g(t_cold, '°C')}; Vmp {BLANK}; Isc {BLANK}; Imp {BLANK} (not on the item; string {_f(ch.get('string_voltage_v'), 0, 'V')} by the rule)")
            s.stack(array_x0, y - 4.8, [data], 84, FS, "start")
        # the home-run pair: + from the chain's right end, − from its left end over the top, both to the DC box
        yp, ym = y + 1.2, y - 1.2
        s.line(chain_end, y, chain_end + 1.5, y, W_SYM)
        s.line(chain_end + 1.5, y, chain_end + 1.5, yp, W_SYM)
        s.line(chain_end + 1.5, yp, lead_x, yp, W_BUS)
        s.line(array_x0, y, array_x0 - 1.5, y, W_SYM)
        s.line(array_x0 - 1.5, y, array_x0 - 1.5, y + 5.6, W_SYM)
        s.line(array_x0 - 1.5, y + 5.6, chain_end + 3.5, y + 5.6, W_SYM)
        s.line(chain_end + 3.5, y + 5.6, chain_end + 3.5, ym, W_SYM)
        s.line(chain_end + 3.5, ym, lead_x, ym, W_BUS)
        s.mc4(chain_end + 7.0, yp)
        s.mc4(chain_end + 7.0, ym)
        s.text(chain_end + 10.5, yp + 0.8, "+", TAG, FB, brand.BLACK, "middle")
        s.text(chain_end + 10.5, ym - 2.4, "−", TAG, FB, brand.BLACK, "middle")
    if too_many:
        s.stack(array_x0, row_ys[0] - 13.0, [f"{len(distinct)} distinct string lengths: one drawn; every string is in the table under the diagram"], 84, FS, "start")
    pv_gauge = ch.get("pv_gauge")
    mc4_l = _line(by_role, "mc4_pair")
    run_lbl = [f"per string 2 × {_g(pv_gauge)} mm² PV wire,", f"{_g(ch.get('pv_run_m'), 'm')} per conductor" + (f"; {strings} strings" if strings > 1 else ""),
               f"connector pairs at the array end ({_code(mc4_l, 'mc4_pair')})"]
    s.stack(101.0, BUS + 13.4, run_lbl, 40, FS, "middle")
    # the array bonding conductor: dashed along the strings to the earth bar
    bond_y = row_ys[-1] - 9.0
    bonding = _line(by_role, "array_bonding")
    bond_mm2 = (circuits.get("C1") or {}).get("egc_provided_mm2")
    bond_txt = f"array bonding {_g(bond_mm2)} mm² ({_code(bonding, 'array_bonding')}), dashed"
    s.line(array_x0, bond_y, 121.0, bond_y, W_LEAD, dash=[1.6, 1.0])
    s.line(121.0, bond_y, 121.0, EARTH_Y, W_LEAD, dash=[1.6, 1.0])
    s.text(array_x0, bond_y - 3.2, _fit(bond_txt, F, FS, 110 * mm), FS, F, brand.GRAY)

    # ---- 3. the DC box: a breaker per string, an SPD per MPPT input in use, dashed outline
    n_in = len(fig["inputs"]) or 1
    assign = _assign_inputs(strings, n_in)
    used_inputs = set(assign)
    box_x0, box_x1 = 124.0, 166.0
    n_brk = max(min(strings, 8), 1)
    brk_ys = [BUS + 2.0 - k * 6.0 for k in range(n_brk)]
    box_top = BUS + 11.0
    box_bot = min(brk_ys[-1], BUS - 4.0) - 13.0
    enc = _line(by_role, "enclosure")
    s.rect(box_x0, box_bot, box_x1 - box_x0, box_top - box_bot, W_LEAD, dash=[2.0, 1.2])
    joined = any(int(x.get("strings") or 0) > 1 for x in fig["per_mppt"])
    box_lbl = ("DC box (combiner): " if joined else "DC box: ") + (f"{enc.get('code')} {enc.get('name') or ''}".strip() if _has_item(enc) else "enclosure: no item in the materials list")
    s.stack(box_x0, box_top + 6.6, [box_lbl], 44, FS, "start")
    row_of_string: dict[int, float] = {}
    for (n, ks), y in zip(drawn, row_ys):
        for k in ks:
            row_of_string[k] = y
    dcb = ch.get("dc_breaker") or {}
    dc_l = _line(by_role, "dc_breaker")
    dc_rating = dcb.get("ocpd_a") if dcb else None
    spd_l = _line(by_role, "dc_spd")
    spd_v = _volts_in((spd_l or {}).get("name"))
    in_ys = [BUS + 3.0 - i * 5.0 for i in range(min(n_in, 4))]
    fan_x = box_x0 + 22.0
    for k in range(n_brk):
        yb = brk_ys[k]
        y_row = row_of_string.get(k, row_ys[0])
        s.line(lead_x, y_row, 121.0, y_row, W_BUS)
        s.line(121.0, y_row, 121.0, yb, W_BUS)
        s.line(121.0, yb, box_x0 + 3.0, yb, W_BUS)
        s.breaker(box_x0 + 9.0, yb, True, 2, 8.0)
        s.line(box_x0 + 13.0, yb, fan_x, yb, W_BUS)
        inp = assign[k] if k < len(assign) else 0
        yi = in_ys[min(inp, len(in_ys) - 1)]
        xf = fan_x + 2.5 * inp
        s.line(fan_x, yb, xf, yb, W_BUS)
        s.line(xf, yb, xf, yi, W_BUS)
        if sum(1 for a in assign if a == inp) > 1:
            s.dot(xf, yi)
    if strings > n_brk:
        s.text(box_x0 + 2.0, brk_ys[-1] - 4.0, f"… {strings} breakers, one per string", FS, F, brand.GRAY)
    inv_x, side = 172.0, 22.0
    for i, yi in enumerate(in_ys):
        if i in used_inputs:
            s.line(fan_x + 2.5 * i, yi, inv_x, yi, W_BUS)
        else:
            s.line(inv_x - 4.0, yi, inv_x, yi, W_BUS)
            s.text(inv_x - 4.6, yi + 0.9, "spare", TAG, F, brand.MUTED, "end")
    s.balloon(box_x0 + 9.0, brk_ys[0] + 6.0, "C1")
    if dc_rating:
        brk_lbl = [f"{_f(dc_rating, 0, 'A')} 2P DC breaker per string ({_code(dc_l, 'dc_breaker')}), each string's DC disconnect"]
    else:
        brk_lbl = [f"DC breaker per string, rated {_f(rating_of(dc_l), 0, 'A')} ({_code(dc_l, 'dc_breaker')})", "not checked: no Isc on file", "each string's DC disconnect"]
    y_lbl = s.stack(box_x0 + 3.0, box_bot - 3.4, brk_lbl, 44, FS, "start")
    # the SPDs: one per MPPT input in use, to the box's earth bar; the stubs jump the other inputs' lines
    n_spd = int(ch.get("dc_spds") or 0)
    bar_y = box_bot + 2.5
    s.line(box_x0 + 0.8, bar_y, box_x1 - 2.0, bar_y, W_SYM)
    for i in range(min(n_spd, len(in_ys))):
        s.spd(box_x0 + 28.0 + i * 5.0, in_ys[i], bar_y, [yy for j, yy in enumerate(in_ys) if j != i])
    spd_lbl = f"DC SPD {_f(spd_v, 0, 'V')} × {n_spd}, one per MPPT input in use ({_code(spd_l, 'dc_spd')})" if _has_item(spd_l) else "DC SPD: no item in the materials list (dc_spd)"
    y_lbl = s.stack(box_x0 + 3.0, y_lbl - 0.6, [spd_lbl], 44, FS, "start")
    if joined:
        s.stack(box_x0 + 3.0, y_lbl - 0.6, ["verify a fuse per string where more than two join (no combiner role on the BOM)"], 44, FS, "start")
        s.balloon(box_x0 + 31.0, in_ys[0] + 4.6, "C2")
    s.line(box_x0 + 0.8, bar_y, box_x0 + 0.8, EARTH_Y, W_LEAD)       # the box's earth bar to the EGC bus

    # ---- 4. the inverter
    s.inverter(inv_x, BUS - side / 2 - 1.0, side)
    for i, yi in enumerate(in_ys):
        if i in used_inputs:
            s.text(inv_x - 0.8, yi + 0.9, f"MPPT {i + 1}", TAG, F, brand.MUTED, "end")
    inv_l = fig["inv_l"]
    inv_code = str(inv_l.get("code")) if _has_item(inv_l) else "inverter: no item in the materials list"
    inv_type = {"grid_tie": "grid-tie", "hybrid": "hybrid", "off_grid": "off-grid type", "charge_controller": "charge controller", "ess_set": "ESS set"}.get(str(ii.get("inverter_type") or ""), BLANK)
    phase = f"{_g(ii.get('phase'))}Ø" if ii.get("phase") else BLANK
    in_list = _mppt_inputs(ii)
    inp_txt = "/".join(_g(a) for a in in_list) + " A" if any(a is not None for a in in_list) else BLANK
    grid_flag = ch.get("inverter_grid_interactive")
    cert = str(fig["pricing"].get("inverter_certificate") or "").strip()
    inv_lines = [
        f"{inv_code}: {_g((inv_l or {}).get('rating'), 'kW')} {inv_type}, {phase}" + (f" × {units}" if units > 1 else ""),
        f"{_g(ii.get('mppt_count')) if ii.get('mppt_count') else BLANK} MPPT inputs, {inp_txt}; max PV {_f(ii.get('max_pv_voltage_v'), 0, 'V')}; window {_f(ii.get('mppt_min_v'), 0, 'V')}–{_f(ii.get('mppt_max_v'), 0, 'V')}",
    ]
    s.stack(inv_x + side - 1.0, BUS + 30.0, inv_lines, 44, FS, "end", bold_first=True)
    out_lines = [
        f"AC {_g(wiring.get('ac_voltage'), 'V')} 1Ø; grid-interactive: {'yes' if grid_flag else 'no' if grid_flag is False else 'not marked'}; certificate: {cert if cert else BLANK}",
        f"battery port {ii.get('battery_class') or BLANK}, {_f(ii.get('charge_v_max'), 1, 'V')}, {_f(ii.get('battery_max_a'), 0, 'A')} discharge, {_f(ii.get('charge_a_max'), 0, 'A')} charge",
    ]
    s.stack(inv_x + side + 8.0, BUS - 30.0, out_lines, 44, FS, "start")

    # ---- 5. the battery bank below the inverter (not on net metering)
    bc = ch.get("battery_circuit") or {}
    bat_l = fig["bat_l"]
    if kind != "net_metering" and (bat_l is not None or bc):
        bx = inv_x + side / 2 + 3.0
        s.line(bx, BUS - side / 2 - 1.0, bx, BUS - side / 2 - 7.0, W_BUS)
        s.breaker(bx, BUS - side / 2 - 11.0, False, 2, 8.0)
        s.balloon(bx - 7.0, BUS - side / 2 - 11.0, "C3")
        s.line(bx, BUS - side / 2 - 15.0, bx, BAT_Y + 4.0, W_BUS)
        n_units = int(ch.get("battery_units") or (bat_l or {}).get("qty") or 1)
        bat_end = s.battery(bx - 6.0, BAT_Y, min(n_units, 3))
        s.line(bx, BAT_Y + 4.0, bx - 6.0, BAT_Y + 4.0, W_BUS)
        s.line(bx - 6.0, BAT_Y + 4.0, bx - 6.0, BAT_Y, W_BUS)
        s.line(bat_end, BAT_Y, bat_end + 1.5, BAT_Y, W_BUS)
        if n_units > 3:
            s.text(bat_end + 2.5, BAT_Y - 1.0, f"… × {n_units}", FS, F, brand.GRAY)
        bb_l = _line(by_role, "battery_breaker")
        bat_lines = [
            f"{str(bat_l.get('code')) if _has_item(bat_l) else 'battery: no item in the materials list'}: {n_units} × {_g((bat_l or {}).get('rating'), 'kWh')} = {_f(ch.get('battery_nominal_kwh'), 2, 'kWh')}, "
            f"{_f(bi.get('nominal_v'), 1, 'V')}; max discharge {_f(bi.get('continuous_a'), 0, 'A')} per unit",
            f"battery breaker {_f(bc.get('breaker_a'), 0, 'A')} 2P ({_code(bb_l, 'battery_breaker')}); {bc.get('cable_gauge') or BLANK} mm² lug pairs, {_g(wiring.get('battery_pairs_per_battery'))} per unit; "
            f"inverter battery current {_f(bc.get('current_a'), 0, 'A')}",
        ]
        if n_units > 2:
            bat_lines.append("parallel bus: verify a battery combiner (not a BOM role)")
        s.stack(bx + 12.0, BAT_Y + 12.0, bat_lines, 48, FS, "start")
        s.line(bat_end + 1.5, BAT_Y, bat_end + 1.5, EARTH_Y, W_LEAD, dash=[1.6, 1.0])
        s.text(bat_end + 3.0, EARTH_Y + 3.2, "rack bond: verify", FS, F, brand.MUTED)
    elif kind == "net_metering":
        s.stack(inv_x + side / 2, BUS - side / 2 - 6.0, ["no battery (net metering)"], 30, FS, "middle")

    # ---- 6. the AC side along the bus
    ac_x = inv_x + side
    x_c4, x_ats, x_spd, x_pb0, x_pb1, x_disc, x_poi_s, x_meter = 206.0, 232.0, 254.0, 266.0, 304.0, 322.0, 340.0, 362.0
    s.line(ac_x, BUS, x_c4 - 4.0, BUS, W_BUS)
    s.breaker(x_c4, BUS, True, 2, 8.0)
    s.balloon(x_c4, BUS + 6.4, "C4")
    s.stack(x_c4, BUS - 6.0, [f"{_f(ch.get('ac_breaker_a'), 0, 'A')} 2P ({_code(_line(by_role, 'ac_breaker'), 'ac_breaker')})",
                               f"2 × {_g(ch.get('ac_gauge'))} mm² THHN, {_g(ch.get('ac_run_m'), 'm')}", "inverter output"], 24, FS, "middle")
    ats = ch.get("ats")
    ats_l = _line(by_role, "ats")
    s.line(x_c4 + 4.0, BUS, x_ats - 7.0, BUS, W_BUS)
    built_in = ats == "built-in"
    if built_in:
        s.dot(x_ats, BUS)
        s.line(x_ats - 7.0, BUS, x_ats + 7.0, BUS, W_BUS)
        s.stack(x_ats, BUS - 6.6, ["transfer switch: built into the inverter (its item says so)"], 26, FS, "middle")
    else:
        s.ats(x_ats, BUS)
        ats_txt = f"ATS {_f(rating_of(ats_l), 0, 'A')} ({ats_l.get('code')})" if _has_item(ats_l) else "ATS: no item in the materials list (ats)"
        s.stack(x_ats, BUS - 6.6, [ats_txt, "transfer switch; bypass from above"], 26, FS, "middle")
    s.line(x_ats + 7.0, BUS, x_pb0, BUS, W_BUS)
    # the AC SPD on the board, to the earth bar
    s.dot(x_spd, BUS)
    s.spd(x_spd, BUS, EARTH_Y)
    acspd_l = _line(by_role, "ac_spd")
    acspd_txt = f"AC SPD type 2, {_f(_volts_in(acspd_l.get('name')), 0, 'V')} ({acspd_l.get('code')}), on the AC board" if _has_item(acspd_l) else "AC SPD: no item in the materials list (ac_spd)"
    s.stack(x_spd - 2.0, BUS - 20.0, [acspd_txt], 30, FS, "end")
    # the existing panelboard: the bus bar with the backfeed breaker, the main breaker at the service side
    pb_h = 16.0
    s.rect(x_pb0, BUS - pb_h / 2, x_pb1 - x_pb0, pb_h, W_BUS, fill=colors.white)
    bar_x = x_pb0 + 6.0
    s.line(x_pb0, BUS, bar_x, BUS, W_BUS)
    s.line(bar_x, BUS - 5.5, bar_x, BUS + 5.5, W_BUS)
    s.text(bar_x + 2.0, BUS + 1.2, f"bus {_g(svc.get('busbar_a'), 'A')}", TAG, F, brand.GRAY)
    s.text(bar_x + 2.0, BUS - 5.6, "backfeed brk: C5, C6", TAG, F, brand.MUTED)
    s.line(bar_x, BUS, x_pb1 - 12.0, BUS, W_BUS)
    s.breaker(x_pb1 - 8.0, BUS, True, 2, 7.0)
    s.text(x_pb1 - 8.0, BUS + 4.0, f"main {_g(svc.get('main_breaker_a'), 'A')}", TAG, F, brand.GRAY, "middle")
    s.line(x_pb1 - 4.5, BUS, x_pb1, BUS, W_BUS)
    pb_lines = ["existing panelboard: main " + _g(svc.get("main_breaker_a"), "A") + ", bus " + _g(svc.get("busbar_a"), "A")]
    if not (svc.get("main_breaker_a") and svc.get("busbar_a")):
        pb_lines.append("(not surveyed)")
    if svc.get("panelboard"):
        pb_lines.append(str(svc["panelboard"]))
    s.stack(x_pb1, BUS + 20.8, pb_lines, 30, FS, "end", bold_first=True)   # right-aligned: the grid line drops onto the bus bar at its left
    # the visible, lockable AC disconnect at the service
    s.line(x_pb1, BUS, x_disc - 5.0, BUS, W_BUS)
    s.isolator(x_disc, BUS, 8.0)
    disc_l = _line(by_role, "ac_disconnect")
    disc_txt = f"AC disconnect {_f(rating_of(disc_l), 0, 'A')} ({disc_l.get('code')})" if _has_item(disc_l) else "AC disconnect: no item in the materials list (ac_disconnect)"
    s.stack(x_disc, BUS + 13.0, [disc_txt, "visible, lockable, for the DU (verify its place)"], 30, FS, "middle")
    s.line(x_disc + 5.0, BUS, x_meter - 4.6, BUS, W_BUS)
    # the point of interconnection: on the panelboard's bus for a load-side breaker (or when not chosen), else at the service
    inter = str(svc.get("interconnection") or "")
    load_side = inter in ("load_side_breaker", "")
    x_poi, y_poi = (bar_x, BUS + 5.5) if load_side else (x_poi_s, BUS)
    s.circle(x_poi, y_poi, 1.5, W_SYM, fill=brand.BLACK)
    poi_txt = ["point of interconnection: " + (INTERCONNECTION_LABEL.get(inter) if inter else "not chosen (Site step)")]
    if svc.get("interconnection_note"):
        poi_txt.append(str(svc["interconnection_note"]))
    poi_txt += poi_lines(poi)
    x_poi_lbl = x_poi + 3.0 if load_side else x_poi      # clear of the AC SPD's stub on the left
    y_end = s.stack(x_poi_lbl, BUS - 11.0, poi_txt, 36, FS, "middle", bold_first=True)
    if poi.get("checked") and not poi.get("ok"):
        s.text(x_poi_lbl, y_end - 0.4, "FAIL: poi_busbar (hard warning, prints)", FS, FB, brand.GOLD_DARK, "middle")
    # the meter
    two_way = kind in ("net_metering", "combination")
    s.meter(x_meter, BUS, two_way)
    meter_lines = (["two-way meter: installed by the DU after the CFEI"] if two_way else ["existing meter; nothing exported"]) + [f"meter number: {svc.get('meter_no') or BLANK}"]
    s.stack(x_meter + 2.0, BUS + 15.0, meter_lines, 44, FS, "middle")
    # the service drop and the DU
    s.line(x_meter + 4.6, BUS, DRAW_W_MM - 4.0, BUS, W_BUS, dash=[3.0, 1.5])
    s.text(x_meter + 6.0, BUS - 3.6, "service drop", 6.5, F, brand.MUTED)
    du = str(svc.get("du_name") or "").strip()
    fl = svc.get("fault_level_ka")
    du_lines = [f"{du if du else 'DU ' + BLANK}: fault level at the service {_f(fl, 1, 'kA') if fl not in (None, '') else BLANK}", "(from the DU, verify)",
                _g(svc.get("voltage_v"), "V") if svc.get("voltage_v") else _g(wiring.get("ac_voltage"), "V") + " (assumption)",
                f"{svc.get('phase')}Ø" if svc.get("phase") else f"phase {BLANK}", f"account {svc.get('account_no') or BLANK}"]
    s.stack(DRAW_W_MM - 4.0, BUS + 36.0, du_lines, 46, FS, "end")

    # ---- the grid line above the bus: the grid feed to the inverter's AC input and the maintenance bypass to the ATS
    x_in = inv_x + side
    y_in = BUS + 7.0
    s.line(x_in, y_in, x_in + 6.0, y_in, W_BUS)
    s.line(x_in + 6.0, y_in, x_in + 6.0, GRID_Y, W_BUS)
    s.text(x_in + 7.5, y_in + 1.0, "AC in", TAG, F, brand.MUTED)
    x_c5 = x_c4 + 12.0
    s.line(x_in + 6.0, GRID_Y, x_c5 - 4.0, GRID_Y, W_BUS)
    s.breaker(x_c5, GRID_Y, True, 2, 8.0)
    s.balloon(x_c5, GRID_Y - 6.4, "C5")
    s.line(x_c5 + 4.0, GRID_Y, x_poi, GRID_Y, W_BUS)
    s.line(x_poi, GRID_Y, x_poi, y_poi + 1.5, W_BUS)
    grid_lbl = [f"grid feed to the inverter's AC input: {_f(ch.get('ac_grid_breaker_a'), 0, 'A')} 2P, 2 × {_g(ch.get('ac_grid_gauge'))} mm² THHN, {_g(ch.get('ac_run_m'), 'm')}"
                + ("" if ch.get("ac_grid_rating_known") else " (sized on the output: no AC input rating on the item)")]
    s.stack(x_c5, GRID_Y + 12.0, grid_lbl, 56, FS, "middle")
    # the bypass: down from the grid line into the transfer switch (or the bus when the switch is built in)
    xb = x_ats - 4.0 if not built_in else x_ats
    y_tap = BUS + 4.5 if not built_in else BUS
    s.dot(xb, GRID_Y)
    s.line(xb, GRID_Y, xb, y_tap + 8.0, W_BUS)
    s.breaker(xb, y_tap + 4.0 + (0.0 if not built_in else 2.0), False, 2, 8.0)
    s.line(xb, y_tap + 0.5, xb, y_tap, W_BUS)
    s.balloon(xb + 6.6, y_tap + 6.0, "C6")
    s.stack(xb + 9.0, GRID_Y - 3.0, [f"maintenance bypass {_f(ch.get('ac_grid_breaker_a'), 0, 'A')} 2P"], 30, FS, "start")

    # ---- 7. grounding: the EGC bus along the bottom, the electrode under the panelboard, the bonds
    s.line(box_x0 + 0.8, EARTH_Y, x_disc, EARTH_Y, W_BUS)
    s.balloon(x_disc + 5.0, EARTH_Y, "C7")
    ex = (x_pb0 + x_pb1) / 2
    s.earth(ex, EARTH_Y)
    s.line(inv_x + 3.0, BUS - side / 2 - 1.0, inv_x + 3.0, EARTH_Y, W_LEAD, dash=[1.6, 1.0])   # the inverter's bond
    rod = _line(by_role, "ground_rod")
    c7 = circuits.get("C7") or {}
    gec_gauge = c7.get("egc_provided_mm2") if c7 else ch.get("ac_gauge")
    rod_txt = f"{rod.get('name')} ({rod.get('code')})" if _has_item(rod) else "ground rod: no item in the materials list"
    s.stack(x_disc, EARTH_Y + 3.0 + 3 * FS * 0.42, [
        f"EGC bus: the grounding run {_g(gec_gauge)} mm² THHN, {_g(ch.get('grounding_run_m'), 'm')}; bonds dashed: array, DC box, inverter, battery rack (verify)",
        f"electrode: {rod_txt}; GEC {_g(gec_gauge)} mm² to the rod, required 14 mm² or less for a rod (verify)",
    ], 66, FS, "end")
    return s.d


# ---------------------------------------------------------------- the legend, the placards, the sheet

def legend_drawing(width_mm: float) -> Drawing:
    """Every symbol on the diagram with its name, three to a row."""
    s = _Sld(width_mm, 40.0)
    entries = [
        ("module", "PV module (the cell with the two arrows of light); a chain is a string"),
        ("breaker", "circuit-breaker, 2P (DC in the box, AC on the bus); the cross marks the hinge"),
        ("spd", "surge-protective device to the earth bar"),
        ("inverter", "DC/AC converter (the inverter): = above, ~ below the diagonal"),
        ("battery", "battery: long and short plates, one group per unit"),
        ("ats", "transfer switch: two inputs, one output"),
        ("isolator", "disconnect (isolator); dashed box = lockable"),
        ("panel", "existing panelboard: bus bar and main breaker"),
        ("poi", "point of interconnection"),
        ("meter", "kWh meter; two arrows = two-way (net metering)"),
        ("earth", "earth electrode (the ground rod)"),
        ("bond", "equipment bonding conductor (dashed)"),
        ("mc4", "connector pair at the array end"),
        ("balloon", "circuit number: the row of the circuit schedule and the design analysis"),
        ("enclosure", "enclosure outline (the DC box), dashed"),
    ]
    col_w = width_mm / 3.0
    row_h = 7.6
    for i, (sym, name) in enumerate(entries):
        col, row = i % 3, i // 3
        x = col * col_w + 2.0
        y = 40.0 - 5.0 - row * row_h
        if sym == "module":
            s.module(x + 1.0, y, 6.0, 4.0)
        elif sym == "breaker":
            s.breaker(x + 4.0, y, True, 2, 8.0)
        elif sym == "spd":
            s.spd(x + 4.0, y + 3.5, y - 3.2)
        elif sym == "inverter":
            s.inverter(x, y - 3.2, 6.4)
        elif sym == "battery":
            s.battery(x + 1.0, y, 1)
        elif sym == "ats":
            s.ats(x + 4.0, y, 8.0, 6.0)
        elif sym == "isolator":
            s.isolator(x + 4.0, y, 6.0)
        elif sym == "panel":
            s.rect(x, y - 2.6, 8.0, 5.2, W_BUS, fill=colors.white)
            s.line(x + 2.0, y - 1.8, x + 2.0, y + 1.8, W_BUS)
            s.breaker(x + 5.5, y, True, 1, 4.0)
        elif sym == "poi":
            s.line(x, y, x + 8.0, y, W_BUS)
            s.circle(x + 4.0, y, 1.5, W_SYM, fill=brand.BLACK)
        elif sym == "meter":
            s.meter(x + 4.0, y - 1.5, True)
        elif sym == "earth":
            s.earth(x + 4.0, y + 2.4)
        elif sym == "bond":
            s.line(x, y, x + 8.0, y, W_LEAD, dash=[1.6, 1.0])
        elif sym == "mc4":
            s.line(x, y, x + 8.0, y, W_BUS)
            s.mc4(x + 4.0, y)
        elif sym == "balloon":
            s.balloon(x + 4.0, y, "C4")
        elif sym == "enclosure":
            s.rect(x, y - 2.6, 8.0, 5.2, W_LEAD, dash=[2.0, 1.2])
        for k, ln in enumerate(_wrap(name, s.F, FS, (col_w - 14.0) * mm, 2)):
            s.text(x + 10.5, y + 0.6 - k * 2.94, ln, FS, s.F, brand.GRAY)
    return s.d


def placard_rows(fig: dict) -> list[list[str]]:
    """The labels and placards the DU asks for, the text the app can fill from the figures; every row says to verify
    the DU's wording. The rapid-shutdown label prints only when the BOM carries an RSD item (a role for later)."""
    ch, sdn, kind = fig["choices"], fig["sdn"], fig["kind"]
    per_string, strings = fig["per_string"], fig["strings"]
    voc_cold, t_cold, isc = sdn.get("voc_cold_v"), sdn.get("t_cold_c"), fig["panel_item"].get("isc_a")
    max_voc = per_string * float(voc_cold) if (voc_cold and per_string) else None
    isc_total = strings * float(isc) if (isc and strings) else None
    grid_flag = ch.get("inverter_grid_interactive")
    rows = [
        ["At the service (meter and main)", "WARNING: DUAL POWER SOURCE — PV SYSTEM CONNECTED", VERIFY_WORDING],
        ["The AC disconnect", "PV SYSTEM AC DISCONNECT", VERIFY_WORDING],
        ["The DC box", f"PV DC DISCONNECT: maximum Voc {_f(max_voc, 1, 'V') if max_voc else BLANK} at {_g(t_cold, '°C')} ({per_string or BLANK} × {_f(voc_cold, 2, 'V')}); "
                       f"maximum circuit current: {strings or BLANK} strings × Isc {_f(isc, 2, 'A')} = {_f(isc_total, 2, 'A') if isc_total else BLANK}",
         "the NEC 690.53 placard; verify the PEC 6.90 clause and " + VERIFY_WORDING],
        ["The inverter", f"{_g((fig['inv_l'] or {}).get('rating'), 'kW')} {'GRID-INTERACTIVE' if grid_flag else 'HYBRID'} INVERTER" + ("" if grid_flag else "; grid-interactive: " + ("no" if grid_flag is False else "not marked")), VERIFY_WORDING],
    ]
    if kind != "net_metering":
        rows.append(["The battery", f"ENERGY STORAGE {_f(ch.get('battery_nominal_kwh'), 2, 'kWh')}, {_f(fig['bat_item'].get('nominal_v'), 1, 'V')}", VERIFY_WORDING])
    if _line(fig["by_role"], "rsd") is not None:
        rows.append(["The array and the DC box", "RAPID SHUTDOWN: the BOM carries a rapid-shutdown item", VERIFY_WORDING])
    return rows


def sld_sheet(doc: Any, results: dict, items: dict[str, dict], cfg: dict, st: dict) -> tuple[str, list]:
    """The hook `plans_pdf` calls: (the sheet's name, its flowables). `st` holds the set's paragraph and table styles
    (h1, h2, body, small, cell, cellb, grid, two_col)."""
    fig = _figures(doc, results, items, cfg)
    P = lambda t, style=None: Paragraph(t, style or st["cell"])  # noqa: E731
    flows: list = [Paragraph(SHEET_NAME, st["h1"])]
    strings, per_string = fig["strings"], fig["per_string"]
    intro = (f"Generation to interconnection along one bus; every device's balloon matches a row of the circuit schedule (C1 to C7). {fig['panels_n']} panels, "
             f"{strings} × {per_string} per string; the figures are the current calculation's (the BOM, the string design, the materials list) and the survey's service block; "
             f"a blank line is a figure the app does not hold, with its reason. Not to scale.")
    flows.append(Paragraph(intro, st["body"]))
    flows.append(sld_drawing(fig))
    # beyond three distinct string lengths the array prints as a table beside the one drawn string
    lengths = fig["lengths"]
    if len(set(lengths)) > 3:
        rows = [[f"S{k + 1}", str(n), _f(n * float(fig["sdn"].get("voc_cold_v") or 0), 1, "V") if fig["sdn"].get("voc_cold_v") else BLANK] for k, n in enumerate(lengths)]
        t = Table([[P("String", st["cellb"]), P("Panels", st["cellb"]), P(f"Voc at {_g(fig['sdn'].get('t_cold_c'), '°C')}", st["cellb"])]] + [[P(c) for c in r] for r in rows],
                  colWidths=[18 * mm, 18 * mm, 30 * mm], hAlign="LEFT")
        t.setStyle(st["grid"])
        flows += [Paragraph("Strings (more than three distinct lengths: one drawn)", st["h2"]), t]
    # the legend and the placards side by side
    legend = [Paragraph("Legend", st["h2"]), legend_drawing(190.0), Paragraph(VERIFY_SYMBOLS, st["small"])]
    prow = placard_rows(fig)
    pt = Table([[P("Where", st["cellb"]), P("Label or placard (filled from the figures)", st["cellb"]), P("Note", st["cellb"])]] + [[P(escape(a)), P(escape(b)), P(escape(c))] for a, b, c in prow],
               colWidths=[36 * mm, 100 * mm, 54 * mm], hAlign="LEFT")
    pt.setStyle(st["grid"])
    placards = [Paragraph("Labels and placards", st["h2"]), pt]
    both = Table([[legend, placards]], colWidths=[196 * mm, 194 * mm], hAlign="LEFT")
    both.setStyle(st["two_col"])
    flows.append(both)
    notes = ("DC system grounding: transformerless inverter, no DC conductor grounded, equipment grounding conductor only (assumption; verify on the inverter datasheet). "
             "The AC disconnect's place, the combiner's fuses and the placards' wording are the DU's: verify. Derating, conduit fill, the short-circuit figures and the "
             f"grounding conductor sizes are on the design analysis; where it is not yet in the set: {TO_COMPLETE}.")
    flows.append(Spacer(1, 2))
    flows.append(Paragraph(notes, st["small"]))
    return SHEET_NAME, flows
