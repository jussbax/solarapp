"""The mounting detail sheet of the plans for the PEE (round 13, item 3; docs/audits/round-13/engineer-brief.md 3.3 to
3.6): the two standard details at 1:5 (A: rib-type metal sheet on steel C-purlins, B: corrugated sheet on purlins; the
tile detail waits on the owner's word and prints as a line), each a section along the rail at an L-foot with callouts
numbered to the BOM roles, a plan key of a 2 × 3 patch with the rail lines, the feet on the purlin lines, the splice and
the clamps, and the uplift check per face as pricing.choices.uplift computed it (pricing/uplift.py): every figure with its
source, every blank with its reason, the assumptions labelled, PASS, FAIL (in red) or NOT CHECKED with what is missing.

Drawn with ReportLab primitives as drawings.py draws the layouts: section cuts 0.7, outlines 0.5, hatching 0.3, leaders
0.25, text 6 to 8.5 pt, black and the brand gold. The details are drawn at 1:5 with typical proportions; the purlin
section, the sheet profile, the screw and the spacings are the typed figures in the callouts, never the drawing's own
sizes, and the sheet says so. Nothing here reaches the customer documents."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Ellipse, Group, Line, PolyLine, Polygon, Rect
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from ..pricing.uplift import DETAILS, PURLIN_WORDS, ROOF_TYPE_WORDS, SETTINGS_WHERE, TILE_TYPES
from ..schemas import AssessmentDoc
from . import brand
from .drawings import PANEL_FILL, STANDARD_SCALES, _hatch, _polygon_path, _text

BLANK = "__________"
FAIL_RED = colors.HexColor("#b3261e")
SHEET_NAME = "Mounting detail and uplift check"
SCALE = 5                                   # the details at 1:5
K = mm / SCALE                              # points per real millimetre at 1:5
SECTION_W = 380.0                           # the window of each detail, real mm
CALLOUT_R = 2.1 * mm


@dataclass
class MountingSheet:
    name: str
    flowables: list
    missing: list[tuple[str, str]] = field(default_factory=list)   # entries for the last sheet's "not yet in this set"


# ---------------------------------------------------------------- formatting

def _g(v: Any, unit: str = "", nd: Optional[int] = None) -> str:
    if v is None or v == "":
        return BLANK
    try:
        x = float(v)
    except (TypeError, ValueError):
        return escape(str(v))
    s = f"{x:,.{nd}f}" if nd is not None else f"{x:g}"
    return s + (f" {unit}" if unit else "")


def _sm(text: str) -> str:
    """The provenance in smaller type beside a figure."""
    return f"<font size='6'>({text})</font>"


def _fig_text(f: Optional[dict], unit: str = "", nd: Optional[int] = None, with_source: bool = True) -> str:
    """A figure with its provenance as the sheet prints it: the value and unit, then its source or assumption in small
    type; a missing figure is the blank line and its reason."""
    if not f:
        return BLANK
    if f.get("missing"):
        return f"{BLANK} {_sm(escape(str(f['missing'])))}"
    text = _g(f.get("value"), unit, nd)
    tail = []
    if f.get("note"):
        tail.append(escape(str(f["note"])))
    if with_source and f.get("source"):
        tail.append("source: " + escape(str(f["source"])))
    return text + (" " + _sm("; ".join(tail)) if tail else "")


def _styles(st: dict) -> tuple[ParagraphStyle, ParagraphStyle, TableStyle]:
    """The sheet's own table type: 7 pt cells (the chain and the legend hold more than the schedule's rows)."""
    F, FS, FB = brand.fonts()
    c7 = ParagraphStyle("mcell", parent=st["cell"], fontSize=7, leading=8.4)
    c7b = ParagraphStyle("mcellb", parent=c7, fontName=FS, textColor=brand.BLACK)
    grid = TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 7), ("FONTNAME", (0, 0), (-1, -1), F), ("FONTNAME", (0, 0), (-1, 0), FB),
        ("BACKGROUND", (0, 0), (-1, 0), brand.OFF_WHITE), ("GRID", (0, 0), (-1, -1), 0.25, brand.LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ])
    return c7, c7b, grid


def _table7(head: list[str], rows: list[list], widths: list[float], c7: ParagraphStyle, c7b: ParagraphStyle, grid: TableStyle) -> Table:
    data = [[Paragraph(h, c7b) for h in head]] + [[c if isinstance(c, Paragraph) else Paragraph(str(c), c7) for c in r] for r in rows]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(grid)
    return t


# ---------------------------------------------------------------- the section details

def _callout(d: Drawing, X, Y, cx: float, cy: float, ax: float, ay: float, label: str, font: str) -> None:
    """A numbered circle at (cx, cy) with a leader to the element at (ax, ay), real mm."""
    d.add(Line(X(cx), Y(cy), X(ax), Y(ay), strokeColor=brand.GRAY, strokeWidth=0.25))
    d.add(Circle(X(cx), Y(cy), CALLOUT_R, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.5))
    d.add(_text(X(cx), Y(cy) - 2.0, label, 5.8, font, brand.BLACK, "middle"))


def _dim_break_h(d: Drawing, X, Y, x1: float, x2: float, y: float, text: str, font: str) -> None:
    """A horizontal dimension with a break (the figure stands for a length longer than drawn)."""
    d.add(Line(X(x1), Y(y), X(x2), Y(y), strokeColor=brand.GRAY, strokeWidth=0.35))
    for x in (x1, x2):
        d.add(Line(X(x) - 1.1, Y(y) - 1.1, X(x) + 1.1, Y(y) + 1.1, strokeColor=brand.GRAY, strokeWidth=0.5))
    xb = (x1 + x2) * 0.72
    d.add(Line(X(xb) - 1.5, Y(y) - 1.8, X(xb) + 1.5, Y(y) + 1.8, strokeColor=colors.white, strokeWidth=1.6))
    d.add(PolyLine([X(xb) - 2.2, Y(y), X(xb) - 0.8, Y(y) + 2.0, X(xb) + 0.8, Y(y) - 2.0, X(xb) + 2.2, Y(y)], strokeColor=brand.GRAY, strokeWidth=0.4))
    d.add(_text((X(x1) + X(x2)) / 2, Y(y) + 1.6, text, 6.0, font, brand.GRAY, "middle"))


def detail_drawing(profile: str, width_mm: float, title: str, foot_text: str, font_names: tuple[str, str, str]) -> Drawing:
    """One standard detail at 1:5: a section along the rail at an L-foot. `profile` is "rib" (a trapezoidal rib on
    the crest of which the foot sits) or "corrugated" (a sine profile, the foot on a crest). The callouts are numbered
    to the legend beside the plan key; the two dimensions are S (the foot spacing along the rail, from the check) and C
    (the clearance under the panel, blank: the L-foot height is not on the item)."""
    F, FS, FB = font_names
    W = width_mm * mm
    crest = 130.0 if profile == "rib" else 117.0        # the sheet rests on the purlin's top flange at y = 100
    x_left, x_right = -40.0, 420.0                       # the callout columns, real mm
    y_bottom, y_top = -48.0, crest + 178.0
    H = (y_top - y_bottom) * K + 9 * mm                  # the title line above
    d = Drawing(W, H)
    d.hAlign = "LEFT"
    ox = (W - (x_right - x_left) * K) / 2.0 - x_left * K

    def X(x: float) -> float:
        return ox + x * K

    def Y(y: float) -> float:
        return (y - y_bottom) * K

    d.add(_text(X(x_left) - CALLOUT_R, H - 6.5, title, 7.2, FS, brand.BLACK))
    # the purlin: a C-section, cut, hatched (exaggerated thickness so the hatch reads at 1:5); it opens to the right
    t = 5.0
    px, pw, ph, lip = 165.0, 50.0, 100.0, 15.0
    c_pts = [(px, 0), (px + pw, 0), (px + pw, lip), (px + pw - t, lip), (px + pw - t, t), (px + t, t), (px + t, ph - t), (px + pw - t, ph - t),
             (px + pw - t, ph - lip), (px + pw, ph - lip), (px + pw, ph), (px, ph)]
    g = Group()
    g.add(_polygon_path([(X(x), Y(y)) for x, y in c_pts]))
    for ln in _hatch(X(px), Y(0), pw * K, ph * K, 1.2 * mm, brand.GRAY, 0.3):
        g.add(ln)
    d.add(g)
    d.add(Polygon([c for x, y in c_pts for c in (X(x), Y(y))], fillColor=None, strokeColor=brand.BLACK, strokeWidth=0.7))
    # the roof sheet, crest to valley to crest, resting on the purlin
    if profile == "rib":
        pts = [(0, crest), (15, crest), (30, 100), (160, 100), (175, crest), (205, crest), (220, 100), (350, 100), (365, crest), (380, crest)]
    else:
        pts = [(x, 100 + 8.5 + 8.5 * math.cos(2 * math.pi * (x - 190) / 76.0)) for x in range(0, 381, 4)]
    d.add(PolyLine([c for x, y in pts for c in (X(x), Y(y))], strokeColor=brand.BLACK, strokeWidth=0.7))
    # the sealant beads at the plate's edges, the EPDM washer under the screw head
    for sx in (160.0, 220.0):
        d.add(Ellipse(X(sx), Y(crest + 1.5), 6 * K, 3.5 * K, fillColor=brand.GOLD, strokeColor=brand.GOLD_DARK, strokeWidth=0.3))
    # the L-foot: the base plate on the crest, the leg up the right side
    foot = [(160, crest), (220, crest), (220, crest + 90), (215, crest + 90), (215, crest + 5), (160, crest + 5)]
    d.add(Polygon([c for x, y in foot for c in (X(x), Y(y))], fillColor=brand.OFF_WHITE, strokeColor=brand.BLACK, strokeWidth=0.7))
    # the screw: the washer and the head on the plate, the shank through the crest into the purlin's top flange
    d.add(Rect(X(190 - 2.75), Y(crest + 5 - 75), 5.5 * K, 75 * K, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.5))
    for k in range(6):
        yy = crest + 5 - 70 + k * 9
        d.add(Line(X(190 - 2.75), Y(yy), X(190 + 2.75), Y(yy + 3), strokeColor=brand.BLACK, strokeWidth=0.3))
    d.add(Polygon([X(190 - 2.75), Y(crest + 5 - 75), X(190 + 2.75), Y(crest + 5 - 75), X(190), Y(crest + 5 - 80)], fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.5))
    d.add(Rect(X(190 - 8), Y(crest + 5), 16 * K, 2.5 * K, fillColor=brand.GOLD, strokeColor=brand.GOLD_DARK, strokeWidth=0.3))
    d.add(Rect(X(190 - 5), Y(crest + 7.5), 10 * K, 6 * K, fillColor=brand.OFF_WHITE, strokeColor=brand.BLACK, strokeWidth=0.5))
    # the rail, in profile along its length, on the foot's leg; the bolt through the leg
    d.add(Rect(X(0), Y(crest + 40), 380 * K, 40 * K, fillColor=brand.OFF_WHITE, strokeColor=brand.BLACK, strokeWidth=0.7))
    d.add(Line(X(0), Y(crest + 44), X(380), Y(crest + 44), strokeColor=brand.MUTED, strokeWidth=0.3))
    d.add(Line(X(0), Y(crest + 76), X(380), Y(crest + 76), strokeColor=brand.MUTED, strokeWidth=0.3))
    d.add(Rect(X(215), Y(crest + 40), 5 * K, 40 * K, fillColor=brand.OFF_WHITE, strokeColor=brand.BLACK, strokeWidth=0.7))
    d.add(Circle(X(217.5), Y(crest + 60), 5 * K, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.5))
    d.add(Line(X(214), Y(crest + 56.5), X(221), Y(crest + 63.5), strokeColor=brand.BLACK, strokeWidth=0.4))
    # the bonding lug on the rail with its conductor
    d.add(Line(X(0), Y(crest + 84), X(36), Y(crest + 84), strokeColor=brand.GOLD_DARK, strokeWidth=1.1))
    d.add(Rect(X(36), Y(crest + 80), 16 * K, 8 * K, fillColor=brand.GOLD, strokeColor=brand.BLACK, strokeWidth=0.5))
    # the panels: the left panel's frame, the mid clamp, the right panel's frame, its glass (shortened: a break), its far frame, the end clamp
    ft = crest + 80
    for fx in (80.0, 135.0, 320.0):
        d.add(Rect(X(fx), Y(ft), 35 * K, 35 * K, fillColor=PANEL_FILL, strokeColor=brand.BLACK, strokeWidth=0.7))
        d.add(Rect(X(fx + 4), Y(ft + 4), 27 * K, 27 * K, fillColor=colors.white, strokeColor=brand.GOLD_DARK, strokeWidth=0.3))
    d.add(Line(X(0), Y(ft + 33), X(80), Y(ft + 33), strokeColor=brand.GOLD_DARK, strokeWidth=1.2))          # the left panel's glass line
    d.add(Line(X(170), Y(ft + 33), X(320), Y(ft + 33), strokeColor=brand.GOLD_DARK, strokeWidth=1.2))       # the right panel's glass line
    d.add(PolyLine([X(243), Y(ft + 28), X(246), Y(ft + 38), X(250), Y(ft + 28), X(253), Y(ft + 38)], strokeColor=brand.GRAY, strokeWidth=0.4))   # the break
    d.add(Line(X(0), Y(ft + 1), X(80), Y(ft + 1), strokeColor=brand.MUTED, strokeWidth=0.3))
    d.add(Line(X(170), Y(ft + 1), X(320), Y(ft + 1), strokeColor=brand.MUTED, strokeWidth=0.3))
    # the mid clamp between the frames: a plate over both lips, its bolt into the rail's channel
    d.add(Rect(X(113), Y(ft + 35), 24 * K, 6 * K, fillColor=brand.OFF_WHITE, strokeColor=brand.BLACK, strokeWidth=0.6))
    d.add(Rect(X(122), Y(ft), 6 * K, 35 * K, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.4))
    d.add(Rect(X(120), Y(ft + 41), 10 * K, 5 * K, fillColor=brand.OFF_WHITE, strokeColor=brand.BLACK, strokeWidth=0.5))
    # the end clamp at the far frame: an L over the lip
    end = [(355, ft), (361, ft), (361, ft + 35), (338, ft + 35), (338, ft + 41), (355, ft + 41)]
    d.add(Polygon([c for x, y in end for c in (X(x), Y(y))], fillColor=brand.OFF_WHITE, strokeColor=brand.BLACK, strokeWidth=0.6))
    d.add(Rect(X(352), Y(ft + 41), 10 * K, 5 * K, fillColor=brand.OFF_WHITE, strokeColor=brand.BLACK, strokeWidth=0.5))
    # the dimensions: S the foot spacing along the rail (broken: longer than drawn), C the clearance under the panel (blank)
    _dim_break_h(d, X, Y, 190, 380, -28, foot_text, F)
    d.add(Line(X(190), Y(-5), X(190), Y(-28) + 0.9 * 1.1, strokeColor=brand.GRAY, strokeWidth=0.25))
    d.add(Line(X(380), Y(95), X(380), Y(-28) + 0.9 * 1.1, strokeColor=brand.GRAY, strokeWidth=0.25))
    cx = 232.0
    d.add(Line(X(cx), Y(crest), X(cx), Y(ft), strokeColor=brand.GRAY, strokeWidth=0.35))
    for yy in (crest, ft):
        d.add(Line(X(cx) - 1.1, Y(yy) - 1.1, X(cx) + 1.1, Y(yy) + 1.1, strokeColor=brand.GRAY, strokeWidth=0.5))
        d.add(Line(X(220), Y(yy), X(cx) + 1.0, Y(yy), strokeColor=brand.GRAY, strokeWidth=0.25))
    d.add(_text(X(cx) + 1.6, Y((crest + ft) / 2) - 2.0, "C", 6.0, FS, brand.GRAY))
    d.add(_text(X(190), Y(-42), "S", 6.0, FS, brand.GRAY, "middle"))
    # the callouts, numbered to the legend
    _callout(d, X, Y, x_left, crest + 60, 30, crest + 60, "1", FB)
    _callout(d, X, Y, x_right, crest + 25, 218, crest + 25, "2", FB)
    _callout(d, X, Y, 125, crest + 160, 125, ft + 46, "3", FB)
    _callout(d, X, Y, x_right, crest + 160, 352, ft + 44, "4", FB)
    _callout(d, X, Y, x_left, crest + 100, 44, crest + 88, "6", FB)
    _callout(d, X, Y, x_right, crest - 8, 222, crest + 1, "7", FB)
    _callout(d, X, Y, x_right, crest - 46, 192.5, crest - 40, "8", FB)
    _callout(d, X, Y, 262, crest + 160, 262, ft + 34, "9", FB)
    _callout(d, X, Y, x_left, 50, 167, 50, "P", FB)
    _callout(d, X, Y, x_left, 112, 60, 100 if profile == "rib" else 108.5, "S", FB)
    # the scale bar: 100 mm real
    yb = -44.0
    d.add(Line(X(240), Y(yb), X(340), Y(yb), strokeColor=brand.BLACK, strokeWidth=0.8))
    for xx in (240, 340):
        d.add(Line(X(xx), Y(yb) - 0.8 * mm, X(xx), Y(yb) + 0.8 * mm, strokeColor=brand.BLACK, strokeWidth=0.6))
    d.add(_text(X(345), Y(yb) - 2.0, "100 mm · 1:5", 6.0, F, brand.GRAY))
    return d


# ---------------------------------------------------------------- the plan key

def plan_key_drawing(width_mm: float, height_mm: float, panel_l: float, panel_w: float, orientation: str, purlin_m: Optional[float], s_foot_m: Optional[float],
                     rule_spacing_m: float, rail_len_m: float, rail_frac: float, font_names: tuple[str, str, str]) -> tuple[Drawing, int]:
    """A 2 × 3 patch of panels in plan: the two rail lines per row, the purlin lines dashed across them (when the spacing
    is typed), the feet where a rail crosses a purlin at the check's spacing (else at the rule's), the splices, the mid
    and end clamps. Returns the drawing and the scale it is drawn at."""
    F, FS, FB = font_names
    along, across = (panel_w, panel_l) if orientation == "portrait" else (panel_l, panel_w)
    patch_w, patch_h = 3 * along, 2 * across
    margin = 6 * mm
    scale = STANDARD_SCALES[-1]
    for n in STANDARD_SCALES:
        s = 1000.0 / n * mm
        if patch_w * s + 2 * margin <= width_mm * mm and patch_h * s + 2 * margin + 4 * mm <= height_mm * mm:
            scale = n
            break
    s = 1000.0 / scale * mm
    W, H = patch_w * s + 2 * margin, patch_h * s + 2 * margin + 4 * mm
    d = Drawing(W, H)
    d.hAlign = "LEFT"
    ox, oy = margin, margin

    def X(x: float) -> float:
        return ox + x * s

    def Y(y: float) -> float:
        return oy + y * s

    for r in range(2):
        for c in range(3):
            d.add(Rect(X(c * along), Y(r * across), along * s, across * s, fillColor=PANEL_FILL, strokeColor=brand.GOLD_DARK, strokeWidth=0.45))
    # the purlin lines, dashed, across the rails
    if purlin_m:
        x = purlin_m
        while x < patch_w - 1e-9:
            d.add(Line(X(x), Y(-0.15), X(x), Y(patch_h + 0.15), strokeColor=brand.GRAY, strokeWidth=0.35, strokeDashArray=[2.0, 1.4]))
            x += purlin_m
    spacing = s_foot_m or rule_spacing_m
    for r in range(2):
        for frac in (rail_frac, 1.0 - rail_frac):
            y = r * across + frac * across
            d.add(Line(X(-0.1), Y(y), X(patch_w + 0.1), Y(y), strokeColor=brand.BLACK, strokeWidth=0.8))
            # the feet
            x = 0.0 if not purlin_m else purlin_m
            while x <= patch_w + 1e-9:
                d.add(Rect(X(x) - 1.1 * mm, Y(y) - 1.1 * mm, 2.2 * mm, 2.2 * mm, fillColor=brand.BLACK, strokeColor=None))
                x += spacing
            # the splices at the rail joints
            x = rail_len_m
            while x < patch_w - 1e-9:
                d.add(Rect(X(x) - 0.5 * mm, Y(y) - 2.0 * mm, 1.0 * mm, 4.0 * mm, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.5))
                x += rail_len_m
            # the mid clamps at the panel gaps, the end clamps at the row ends
            for c in (1, 2):
                d.add(Circle(X(c * along), Y(y), 0.9 * mm, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.5))
            for xx in (0.0, patch_w):
                d.add(Line(X(xx), Y(y) - 1.6 * mm, X(xx), Y(y) + 1.6 * mm, strokeColor=brand.BLACK, strokeWidth=0.9))
    d.add(_text(ox, H - 3.2 * mm, f"Plan key, 1:{scale}: 2 × 3 panels, {orientation}", 6.0, FS, brand.BLACK))
    return d, scale


# ---------------------------------------------------------------- the sheet

def mounting_sheet(doc: AssessmentDoc, results: dict, cfg: dict, items: dict[str, dict], st: dict) -> MountingSheet:
    """The sheet's flowables: the two details and the plan key with the callout legend on the left, the uplift table per
    face and the notes on the right. `st` carries the plans' styles and helpers (h1, h2, body, small, cell, cellb,
    grid, kv_style, two_col, P, table). Returns the sheet with the entries the last sheet lists as still missing."""
    F, FS, FB = brand.fonts()
    h1, h2, body, small = st["h1"], st["h2"], st["body"], st["small"]
    two_col = st["two_col"]
    c7, c7b, grid7 = _styles(st)

    def P(t: str) -> Paragraph:
        return Paragraph(t, c7)

    pricing = results.get("pricing") or {}
    choices = pricing.get("choices") or {}
    up = choices.get("uplift")
    mounting = cfg.get("mounting") or {}
    roles = cfg.get("roles") or {}
    by_role: dict[str, dict] = {}
    for l in pricing.get("lines") or []:
        by_role.setdefault(str(l.get("role") or ""), l)

    def item_text(role: str) -> str:
        l = by_role.get(role)
        if l is None:
            return f"{BLANK} (no {role.replace('_', ' ')} line on the BOM)"
        code = str(l.get("code") or "")
        if code.startswith("NO-ITEM-") or not l.get("found", True):
            return f"no item in the materials list yet ({escape(role)})"
        qty = float(l.get("qty") or 0)
        return f"{int(qty) if qty.is_integer() else round(qty, 1):g} {escape(str(l.get('unit') or ''))} {escape(str(l.get('name') or code))} ({escape(code)})"

    faces = list((up or {}).get("faces") or [])
    status = (up or {}).get("status") or "not checked"
    first = next((f for f in faces if f.get("status") == "pass"), faces[0] if faces else None)
    missing_entries: list[tuple[str, str]] = []

    # ---- the details (left column, top)
    fastener = str(mounting.get("fastener_description") or "").strip()
    foot_text = (f"S = {first['s_foot_m']:g} m (every {_ordinal(int(first['k_foot']))} purlin)" if first and first.get("s_foot_m") and first.get("k_foot")
                 else f"S = {BLANK} (not checked)")
    det_w = 97.0
    det_a = detail_drawing("rib", det_w, "Detail A: rib-type metal sheet on steel C-purlins, 1:5", foot_text, (F, FS, FB))
    det_b = detail_drawing("corrugated", det_w, "Detail B: corrugated sheet on purlins, 1:5", foot_text, (F, FS, FB))
    details = Table([[det_a, det_b]], colWidths=[det_w * mm + 2 * mm, det_w * mm], hAlign="LEFT")
    details.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                 ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))

    # ---- the plan key and the callout legend
    panel_l = float((first or {}).get("panel", {}).get("length_m") or 0) if first else 0.0
    panel_w = float((first or {}).get("panel", {}).get("width_m") or 0) if first else 0.0
    if not (panel_l and panel_w):
        geometry = [g for g in (results.get("geometry") or []) if g.get("panels")]
        panel_l = float(geometry[0].get("panel_length_m") or 2.0) if geometry else 2.0
        panel_w = float(geometry[0].get("panel_width_m") or 1.0) if geometry else 1.0
    orientation = str((first or {}).get("orientation") or "portrait")
    rail_len = float(roles.get("rail_length_m") or 2.4)
    lfr = int(roles.get("l_feet_per_rail") or 3)
    rule_spacing = rail_len / max(lfr - 1, 1)
    rail_frac = float(mounting.get("rail_position_fraction") or 0.25)
    purlin_m = (first or {}).get("purlin_spacing_m", {}).get("value") if first else None
    s_foot = (first or {}).get("s_foot_m") if first and first.get("status") == "pass" else None
    key, key_scale = plan_key_drawing(78.0, 62.0, panel_l, panel_w, orientation, purlin_m, s_foot, rule_spacing, rail_len, rail_frac, (F, FS, FB))
    if first and first.get("status") == "pass":
        key_note = (f"Feet (black squares) on every {_ordinal(int(first['k_foot']))} purlin, {first['s_foot_m']:g} m along the rail; purlins at {purlin_m:g} m (dashed), "
                    f"from the check on {escape(str(first['name']))}.")
    elif purlin_m:
        key_note = f"Purlins at {purlin_m:g} m (dashed); the feet are drawn at the BOQ rule's {rule_spacing:g} m ({lfr} per {rail_len:g} m rail) because the check is not passed."
    else:
        key_note = f"Purlin spacing: not surveyed, so no purlin lines; the feet are drawn at the BOQ rule's {rule_spacing:g} m ({lfr} per {rail_len:g} m rail)."
    key_note += f" Rail lines at {rail_frac:g} of the panel's dimension up the slope from each edge (assumption). Splices: white bars at every {rail_len:g} m; mid clamps: circles at the panel gaps; end clamps: bars at the row ends."
    screws = int(mounting.get("screws_per_foot") or 2)
    legend_rows = [
        ["1", P("<b>Rail</b>: " + item_text("rail")), P(escape(str((by_role.get("rail") or {}).get("note") or "two lines per row")))],
        ["2", P("<b>L-foot</b>: " + item_text("l_foot")), P("on the crest, screwed into the purlin; the count: the uplift table")],
        ["3", P("<b>Mid clamp</b>: " + item_text("mid_clamp")), P("two per panel gap")],
        ["4", P("<b>End clamp</b>: " + item_text("end_clamp")), P("four per row")],
        ["5", P("<b>Splice</b>: " + item_text("splice")), P("one per rail joint (plan key)")],
        ["6", P("<b>Bonding lug and conductor</b>: " + item_text("earth_lug") + "; " + item_text("array_bonding")), P("a lug per rail line and per panel frame")],
        ["7", P("<b>Sealant</b>: " + item_text("sealant")), P("a bead at the penetration; the EPDM washer under the head")],
        ["8", P("<b>Fastener</b>: " + (escape(fastener) if fastener else f"{BLANK} (not typed under {SETTINGS_WHERE})") + ", into the purlin"),
         P(f"{screws} per foot" + (" (assumption)" if screws == 2 else "") + "; with the L-foot set")],
        ["9", P("<b>Panel</b>: " + escape(str((by_role.get("panel") or {}).get("name") or BLANK)) + f", {_g(panel_l)} × {_g(panel_w)} m"), P("the frame on the rail")],
        ["P", P("<b>Purlin</b>: " + _construction_words(first, "purlin")), P("as surveyed; drawn typical")],
        ["S", P("<b>Roof sheet</b>: " + _construction_words(first, "sheet")), P("as surveyed; drawn typical")],
    ]
    legend_t = _table7(["No.", "Role and item (the BOM)", "Note"], legend_rows, [8 * mm, 74 * mm, 36 * mm], c7, c7b, grid7)

    key_block = Table([[[key, Paragraph(key_note, c7)], legend_t]], colWidths=[(196 - 118) * mm, 118 * mm], hAlign="LEFT")
    key_block.setStyle(two_col)
    dims_note = Paragraph(
        f"<b>Dimensions.</b> S: the foot spacing along the rail, from the uplift check (a multiple of the purlin spacing, at or under the rail maker's maximum span); "
        f"C: the clearance under the panel, {BLANK} (the L-foot height is not on the item). Rail lines {_g(first['rail_to_rail_m']['value'] if first else None, 'm', 2)} apart, "
        f"the panel edge {_g(rail_frac * (panel_l if orientation == 'portrait' else panel_w), 'm', 2)} beyond each rail (assumption: the rails at the quarter points; the maker's clamping zone: verify). "
        "Drawn along the rail with the purlin under the foot shown cut; the chain puts a foot at a purlin crossing (the rails across the purlins): where the rails run with "
        "the purlins the feet are screwed into that purlin at the spacing shown, and the signing engineer verifies.", c7)
    method = Paragraph(
        "<b>Method.</b> V, the exposure constants alpha and zg, Kd and GCp are typed by the signing engineer with their sources (the app ships none); Kz = 2.01 × (max(h, 4.6 m) / zg)^(2/alpha); "
        "qh = 0.613 × Kz × Kzt × Kd × V² (V in m/s); p_up = qh × |GCp| (the array above the roof surface, no internal pressure on it; the rooftop-solar method of ASCE 7-16 29.4.3 "
        "and 29.4.4 may replace this when the office adopts it); 0.6D + 0.6W; each rail line carries half the panel; the feet sit on purlins at a multiple of the purlin spacing, at or "
        "under the rail maker's maximum span; a screw's share against the maker's allowable withdrawal for the purlin material and thickness typed. A FAIL means more screws per foot "
        "or a stronger fastener: the signing engineer's call. The clause numbers are the brief's, to be verified.", c7)
    left_col: list = [Paragraph("Standard details", h2), details, dims_note, Spacer(1, 1.5 * mm), Paragraph("Plan key and callouts", h2), key_block, Spacer(1, 1.5 * mm), method]

    tile_faces = [f for f in faces if f.get("roof_type") in TILE_TYPES]
    other_faces = [f for f in faces if f.get("roof_type") and f.get("roof_type") not in DETAILS and f.get("roof_type") not in TILE_TYPES]
    if tile_faces:
        names = ", ".join(escape(str(f["name"])) for f in tile_faces)
        left_col.append(Paragraph(f"<b>Detail C, tile roof ({names}): not drawn.</b> The tile hook or bracket under the tile and its screw into the rafter wait on the owner's word; "
                                  "the rafter spacing as surveyed is on the uplift table. The structural check is the signing engineer's.", c7))
        missing_entries.append(("Tile roof mounting detail (Detail C)", f"Not drawn for {names}: the tile bracket and its screw wait on the owner's word; the mounting detail sheet says so."))
    for f in other_faces:
        words = ROOF_TYPE_WORDS.get(str(f["roof_type"]), str(f["roof_type"]))
        left_col.append(Paragraph(f"<b>{escape(str(f['name']))}:</b> mounting detail not drawn for {escape(words)}; the structural check is the engineer's.", c7))
        missing_entries.append((f"Mounting detail for {escape(words)} ({escape(str(f['name']))})", "Not drawn: the roof type is out of scope (a concrete deck needs the deck's structural check and a different mounting set); the structural check is the signing engineer's."))

    # ---- the uplift table (right column)
    right_col: list = [Paragraph("Uplift check per face (NSCP 2015 Section 207, allowable stress design; every figure verify)", h2)]
    if up is None:
        right_col.append(Paragraph("The uplift check is not in these results: Calculate the project again.", body))
    elif not faces:
        right_col.append(Paragraph("No row of panels sits on a surveyed face, so there is nothing to check.", body))
    else:
        for chunk_start in range(0, len(faces), 3):
            chunk = faces[chunk_start:chunk_start + 3]
            right_col.append(_uplift_table(chunk, up, c7, c7b, grid7))
            right_col.append(Spacer(1, 1.5 * mm))
        lf = up.get("l_foot") or {}
        if status == "not checked":
            right_col.append(Paragraph(f"<b>L-feet on the BOM:</b> {_g(lf.get('bom'))}, the BOQ rule's {_g(roles.get('l_feet_per_rail'))} per {_g(rail_len)} m rail: the check is not "
                                       "checked (the blank lines above say what is missing), so the rule's count stands.", c7))
        else:
            right_col.append(Paragraph(f"<b>L-feet on the BOM:</b> {_g(lf.get('bom'))} ({escape(str(lf.get('note') or ''))}). "
                                       + (f"By the check: {_g(lf.get('checked'))} feet, {_g(lf.get('screws'))} screws; the BOQ rule's {_g(lf.get('rule'))}." if lf.get("checked") is not None
                                          else f"The BOQ rule's {_g(lf.get('rule'))} ({_g(roles.get('l_feet_per_rail'))} per {_g(rail_len)} m rail) until the check passes."), c7))
        if up.get("assumptions") and status != "not checked":
            right_col.append(Paragraph("<b>Assumptions</b> (the signing engineer replaces each before sealing): " + "; ".join(escape(str(a)) for a in up["assumptions"]) + ".", c7))
        if up.get("missing"):
            missing_entries.append(("Uplift check inputs", "Not checked: " + "; ".join(escape(str(x)) for x in up["missing"]) + f". Type them under {SETTINGS_WHERE} and on the project's roof construction and wind; the mounting detail sheet prints the chain with the blanks."))
        notes = [n for f in faces for n in (f.get("notes") or [])]
        conditions = [f"{f['name']}: condition {f['construction'].get('condition_flag')}" + (f" ({f['construction'].get('condition')})" if f['construction'].get('condition') else "") + "; verify the roof carries the array"
                      for f in faces if f.get("construction", {}).get("condition_flag") not in ("", "sound", None)]
        if notes or conditions:
            right_col.append(Paragraph("<b>Notes:</b> " + "; ".join(escape(str(n)) for n in conditions + notes) + ".", c7))
    head = [
        Paragraph(SHEET_NAME, h1),
        Paragraph("The standard details the crews mount with, drawn at 1:5 with typical proportions (the roof's own purlin section, sheet profile, screw and spacings are the typed "
                  "figures in the callouts and the table, never the drawing's sizes), and the uplift check on each face that holds panels. Nothing is invented: a figure the app does "
                  "not hold is a blank line with its reason, and a default prints as a labelled assumption.", body),
    ]
    sheet = Table([[left_col, right_col]], colWidths=[196 * mm, 194 * mm], hAlign="LEFT")
    sheet.setStyle(two_col)
    # the two columns side by side when they fit the sheet; else one under the other, the chain's table splitting over the sheets it needs
    avail = (297 - 2 * 10 - 30) * mm - 5 * mm - sum(f.wrap(390 * mm, 10000)[1] for f in head) - 8
    flow: list = head + ([sheet] if sheet.wrap(390 * mm, 10000)[1] <= avail else left_col + [Spacer(1, 3 * mm)] + right_col)
    return MountingSheet(SHEET_NAME, flow, missing_entries)


def _ordinal(k: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(k, f"{k}th")


def _construction_words(face: Optional[dict], what: str) -> str:
    """The purlin or the roof sheet as surveyed, the blank fields named once with "not surveyed"."""
    c = (face or {}).get("construction") or {}
    if what == "purlin":
        mat = PURLIN_WORDS.get(str(c.get("purlin_material") or ""), "")
        have = [escape(str(c.get("purlin_section"))) if c.get("purlin_section") else "", escape(mat), f"{_g(c.get('purlin_thickness_mm'))} mm" if c.get("purlin_thickness_mm") else "",
                f"at {_g(c.get('purlin_spacing_m'))} m" if c.get("purlin_spacing_m") else ""]
        blank = [n for n, v in zip(("section", "material", "thickness", "spacing"), have) if not v]
        text = ", ".join(v for v in have if v)
        return text + (f"; {', '.join(blank)} {BLANK} (not surveyed)" if blank and text else f"{BLANK} (not surveyed)" if blank else "")
    rt = ROOF_TYPE_WORDS.get(str(c.get("roof_type") or ""), "")
    prof = escape(str(c.get("sheet_profile"))) if c.get("sheet_profile") else ""
    if rt and prof:
        return f"{escape(rt)}; {prof}"
    if rt or prof:
        return (escape(rt) or prof) + f"; {'profile' if rt else 'roof type'} {BLANK} (not surveyed)"
    return f"{BLANK} (roof type and profile not surveyed)"


def _uplift_table(faces: list[dict], up: dict, c7: ParagraphStyle, c7b: ParagraphStyle, grid: TableStyle) -> Table:
    """The chain as rows and the faces as columns: the step with its formula or clause (verify) in the first column, then
    per face the figure and, in small type, its source or assumption."""
    wind = up.get("wind") or {}
    n = len(faces)
    label_w = 50 * mm
    face_w = (194 * mm - label_w) / n

    def P(t: str) -> Paragraph:
        return Paragraph(t, c7)

    def step(label: str, how: str) -> Paragraph:
        return Paragraph(f"<b>{label}</b><br/>{_sm(how)}", c7)

    def num(v: Any, unit: str = "", nd: int = 3) -> str:
        return BLANK if v is None else _g(v, unit, nd)

    def per_face(fn) -> list:
        return [P(fn(f)) for f in faces]

    def construction(f: dict) -> str:
        c = f.get("construction") or {}
        rt = ROOF_TYPE_WORDS.get(str(c.get("roof_type") or ""), "")
        det = f.get("detail")
        h = (f.get("h_m") or {}).get("value")
        parts = [(escape(rt) + (f" (Detail {det})" if det else " (no detail drawn)")) if rt else f"roof type {BLANK}",
                 _construction_words(f, "purlin"),
                 f"h {_g(h)} m" if h else f"h {BLANK}"]
        if c.get("rafter_spacing_m"):
            parts.append(f"rafters at {_g(c['rafter_spacing_m'])} m")
        flag = c.get("condition_flag")
        parts.append(f"condition {escape(str(flag))}" + (": verify the roof carries the array" if flag and flag != "sound" else "") if flag else f"condition {BLANK}")
        blanks = [n for n, v in (("roof type", rt), ("h", h), ("condition", flag)) if not v]
        return "; ".join(parts) + (" " + _sm(f"{', '.join(blanks)}: not surveyed") if blanks else "")

    def v_text(f: dict) -> str:
        v = wind.get("v_kmh") or {}
        if v.get("missing"):
            return _fig_text(v)
        zone = wind.get("zone") or BLANK
        return f"{_g(v['value'])} km/h = {_g(float(v['value']) / 3.6, 'm/s', 2)}; zone {escape(str(zone))}, {escape(str(up.get('province') or BLANK))} " + _sm("source: " + escape(str(v.get("source") or "")))

    def exposure_text(f: dict) -> str:
        e = wind.get("exposure") or {}
        a, z = wind.get("alpha") or {}, wind.get("zg_m") or {}
        head = f"{escape(str(e.get('value') or BLANK))}" + (" " + _sm(escape(str(e.get("note")))) if e.get("assumed") else "")
        if a.get("missing"):
            return head + f"; alpha, zg {BLANK} " + _sm(escape(str(a["missing"])))
        return head + f"; alpha {_g(a.get('value'))}, zg {_g(z.get('value'), 'm')} " + _sm("source: " + escape(str(a.get("source") or "")))

    def result_text(f: dict) -> str:
        s = f.get("status")
        if s == "pass":
            tag = "PASS" + (" (on assumptions: see below)" if f.get("assumptions") else "")
            return f"<b>{tag}</b>: feet on every {_ordinal(int(f['k_foot']))} purlin ({_g(f['s_foot_m'])} m), {num(f.get('t_screw_kn'), 'kN', 3)} per screw, ratio {num(f.get('ratio'), '', 2)}"
        if s == "fail":
            return (f"<font color='#b3261e'><b>FAIL</b></font>: even a foot on every purlin ({_g(f.get('s_foot_m'))} m) puts {num(f.get('t_screw_kn'), 'kN', 3)} on each screw against "
                    f"{_fig_text(f.get('pullout_kn'), 'kN', with_source=False)}; more screws per foot or a stronger fastener: the signing engineer's")
        n = len(f.get("missing") or [])
        return f"<b>NOT CHECKED</b>: {n} input{'s' if n != 1 else ''} blank (the blank lines above say which and why); the L-feet stay the BOQ rule's"

    def per_screw(f: dict) -> str:
        if f.get("t_screw_std_kn") is None:
            return f"{BLANK} (not computed)"
        holds = f.get("holds_std")
        return (f"T_foot {num(f['t_foot_std_kn'], 'kN')} = {num(f['net_kpa'], 'kPa')} × {_g(f['s_std_m'])} m × {_g(f['strip_m']['value'], 'm', 3)}; "
                f"{_g(f['screws_per_foot']['value'])} screws gives <b>{num(f['t_screw_std_kn'], 'kN')}</b> per screw against {_fig_text(f.get('pullout_kn'), 'kN')}: "
                + (f"holds (ratio {num(f['ratio_std'], '', 2)})" if holds else f"<b>does not hold</b> (ratio {num(f['ratio_std'], '', 2)})"))

    def spacing_text(f: dict) -> str:
        if f.get("s_foot_m") is None:
            return f"{BLANK} (not computed)"
        sa = f"s_allow {num(f['s_allow_m'], 'm')}" if f.get("s_allow_m") is not None else "no net uplift"
        return (f"{sa} gives every {_ordinal(int(f['k_foot']))} purlin = {_g(f['s_foot_m'])} m: {num(f['t_screw_kn'], 'kN')} per screw, ratio {num(f['ratio'], '', 2)}; "
                f"{_g(f.get('feet_per_rail'))} feet per rail piece")

    def feet_text(f: dict) -> str:
        rows = f.get("rows") or []
        if f.get("feet") is None:
            return f"{BLANK} (not computed); the rule's {_g(f.get('l_foot_rule'))} on {len(rows)} row{'s' if len(rows) != 1 else ''} ({', '.join(_g(r['length_m'], 'm', 2) for r in rows)})"
        return (f"{', '.join(str(r['feet_per_line']) for r in rows)} per rail line on the {len(rows)} row{'s' if len(rows) != 1 else ''} "
                f"({', '.join(_g(r['length_m'], 'm', 2) for r in rows)}, two lines each): <b>{f['feet']} feet, {f['screws']} screws</b>; the BOQ rule's {_g(f.get('l_foot_rule'))}")

    def cap_text(f: dict) -> str:
        c = f.get("cap_m") or {}
        if f.get("s_std_m") is None:
            return _fig_text(c, "m") + f"; purlins at {_fig_text(f.get('purlin_spacing_m'), 'm', with_source=False)}"
        return _fig_text(c, "m") + f"; purlins at {_g(f['purlin_spacing_m']['value'])} m gives every {_ordinal(int(f['k_std']))} purlin = {_g(f['s_std_m'])} m"

    rows = [
        [step("Roof construction", "surveyed per face; a blank reads the project's default")] + per_face(construction),
        [step("Basic wind speed V", "NSCP 2015 Fig. 207A.5-1A, 3-s gust at 10 m, Occupancy II (verify); the province's row, or the project's")] + per_face(v_text),
        [step("Exposure; alpha, zg", "NSCP Table 207A.9-1 (ASCE 7-10 26.9-1): verify")] + per_face(exposure_text),
        [step("Mean roof height h", "surveyed, ground to mid-slope")] + per_face(lambda f: _fig_text(f.get("h_m"), "m")),
        [step("Kz", "2.01 × (max(h, 4.6 m) / zg)^(2/alpha): verify")] + per_face(lambda f: num(f.get("kz"))),
        [step("Kzt", "topographic factor, NSCP 207A.8: verify")] + per_face(lambda f: _fig_text(wind.get("kzt"))),
        [step("Kd", "directionality, C&amp;C, NSCP Table 207A.6-1: verify")] + per_face(lambda f: _fig_text(wind.get("kd"))),
        [step("qh", "0.613 Kz Kzt Kd V² (V in m/s), NSCP 207B.3-1: verify")] + per_face(lambda f: num(f.get("qh_pa"), "N/m²", 0)),
        [step("GCp", "C&amp;C, the roof zone (1 interior, 2 edge, 3 corner), one panel's area; NSCP 207E.4-2: verify")] + per_face(lambda f: _fig_text(wind.get("gcp"))),
        [step("Uplift on the panel p_up", "qh × |GCp|; no internal pressure on an array above the roof (assumption)")] + per_face(lambda f: num(f.get("p_up_kpa"), "kPa")),
        [step("Panel and dead load D", "weight × 9.81 + the rail share, over the panel's area")]
        + per_face(lambda f: f"{_g(f['panel']['length_m'])} × {_g(f['panel']['width_m'])} = {_g(f['panel']['area_m2'], 'm²', 3)}; {_fig_text(f.get('weight_kg'), 'kg')} + rail {_fig_text(f.get('rail_kg'), 'kg', 2)} gives {_fig_text(f.get('d_kpa'), 'kPa', 3, with_source=False)}"),
        [step("Net uplift", "0.6D + 0.6W, NSCP 203.4: verify; zero when the dead load wins")] + per_face(lambda f: f"T_panel {num(f.get('t_panel_kn'), 'kN', 2)}; {num(f.get('net_kpa'), 'kPa')} on the panel"),
        [step("Rail lines", "each line carries half the panel across the rails")]
        + per_face(lambda f: f"{escape(str(f.get('orientation') or ''))}: strip {_fig_text(f.get('strip_m'), 'm', 3, with_source=False)}; rails {_fig_text(f.get('rail_to_rail_m'), 'm', 2, with_source=False)} apart"),
        [step("Foot spacing cap", "the rail maker's maximum span (or the BOQ rule's); a multiple of the purlin spacing")] + per_face(cap_text),
        [step("Per screw at the cap", "T_foot = net × S × strip; T_screw = T_foot / screws per foot, against the allowable withdrawal")] + per_face(per_screw),
        [step("Spacing that holds", "s_allow = screws × pull-out / (net × strip); S = the largest multiple of the purlin spacing at or under min(s_allow, cap)")] + per_face(spacing_text),
        [step("Feet and screws", "per line floor(line / S) + 1, two lines per row; the screws come with the L-foot set")] + per_face(feet_text),
        [step("Result", "PASS: the BOM follows. FAIL: hard, prints, not blocking. NOT CHECKED: an input is blank")] + per_face(result_text),
    ]
    return _table7(["Step (formula or source: verify)"] + [escape(str(f.get("name") or "face")) for f in faces], rows, [label_w] + [face_w] * n, c7, c7b, grid)
