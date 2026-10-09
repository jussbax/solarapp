"""The two engineering drawings as ReportLab flowables: the plan of a roof face (from results["geometry"], contract C3)
and the Gantt chart of the program of works (from program["events"]). Brand black and gold with light fills,
Montserrat like the other reports. The React components draw the same content from the same data."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Optional

from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Path, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from xml.sax.saxutils import escape

from . import brand

PANEL_FILL = colors.HexColor("#E9DAA9")     # the brand gold lightened for a fill; GOLD_DARK strokes carry the edge
SPARE_FILL = colors.white
FACE_FILL = brand.OFF_WHITE
STRIP_FILL = colors.HexColor("#F1EBDD")
XLSX_FILL = "FAF4E1"
# the drawing scales a sheet may state, largest first (1:20 is the largest: 1 m on the roof = 50 mm on paper)
STANDARD_SCALES = (20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200, 250, 300, 400, 500)


def _text(x: float, y: float, text: str, size: float, font: str, color=brand.GRAY, anchor: str = "start") -> String:
    return String(x, y, text, fontName=font, fontSize=size, fillColor=color, textAnchor=anchor)


def _fit(text: str, font: str, size: float, width: float) -> str:
    """Truncate with an ellipsis so the text fits the width."""
    if pdfmetrics.stringWidth(text, font, size) <= width:
        return text
    while text and pdfmetrics.stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _hatch(x: float, y: float, w: float, h: float, spacing: float, color, width: float = 0.3) -> list[Line]:
    """45-degree hatch lines clipped to a rectangle."""
    lines: list[Line] = []
    if w <= 0 or h <= 0:
        return lines
    c = x - h
    while c < x + w:
        t0 = max(0.0, (x - c) / h)
        t1 = min(1.0, (x + w - c) / h)
        if t1 > t0:
            lines.append(Line(c + t0 * h, y + t0 * h, c + t1 * h, y + t1 * h, strokeColor=color, strokeWidth=width))
        c += spacing
    return lines


def _polygon_path(points: list[tuple[float, float]], clip: bool = True) -> Path:
    p = Path(isClipPath=1 if clip else 0, strokeColor=None, fillColor=None)
    p.moveTo(*points[0])
    for pt in points[1:]:
        p.lineTo(*pt)
    p.closePath()
    return p


def _tick(x: float, y: float, t: float, color, width: float) -> Line:
    """The 45-degree tick of an architectural dimension line, centred on the point."""
    return Line(x - t, y - t, x + t, y + t, strokeColor=color, strokeWidth=width)


def _dim_h(d: Drawing, x1: float, x2: float, y_line: float, y_edge: float, text: str, font: str, size: float, color, t: float,
           anchor: str = "centre") -> None:
    """A horizontal dimension between x1 and x2 on the line y_line, its extension lines running from the face edge
    (y_edge). The text sits above the line, centred; a text wider than the segment is anchored at the segment's
    inner end instead (`anchor` "right": it starts at x2 and reads rightwards; "left": it ends at x1)."""
    d.add(Line(x1, y_line, x2, y_line, strokeColor=color, strokeWidth=0.35))
    ext = 0.9 * t
    for x in (x1, x2):
        d.add(Line(x, y_edge, x, y_line - ext if y_line < y_edge else y_line + ext, strokeColor=color, strokeWidth=0.25))
        d.add(_tick(x, y_line, t, color, 0.5))
    tw = pdfmetrics.stringWidth(text, font, size)
    yt = y_line + 0.45 * t + 0.35
    if tw <= abs(x2 - x1) - 1.2 * t or anchor == "centre":
        d.add(_text((x1 + x2) / 2, yt, text, size, font, color, "middle"))
    elif anchor == "right":
        d.add(_text(x2 + 0.9 * t, yt, text, size, font, color, "start"))
    else:
        d.add(_text(x1 - 0.9 * t, yt, text, size, font, color, "end"))


def _dim_v(d: Drawing, y1: float, y2: float, x_line: float, x_edge: float, text: str, font: str, size: float, color, t: float,
           anchor: str = "centre") -> None:
    """A vertical dimension between y1 and y2 on the line x_line (left of the face); the text is turned to read from
    the bottom up and sits to the left of the line. `anchor` "up": a long text starts at y2 and reads upwards; "down":
    it ends at y1."""
    d.add(Line(x_line, y1, x_line, y2, strokeColor=color, strokeWidth=0.35))
    ext = 0.9 * t
    for y in (y1, y2):
        d.add(Line(x_edge, y, x_line - ext, y, strokeColor=color, strokeWidth=0.25))
        d.add(_tick(x_line, y, t, color, 0.5))
    tw = pdfmetrics.stringWidth(text, font, size)
    xt = x_line - 0.45 * t - 0.35
    if tw <= abs(y2 - y1) - 1.2 * t or anchor == "centre":
        cy, ta = (y1 + y2) / 2, "middle"
    elif anchor == "up":
        cy, ta = y2 + 0.9 * t, "start"
    else:
        cy, ta = y1 - 0.9 * t, "end"
    g = Group(String(0, 0, text, fontName=font, fontSize=size, fillColor=color, textAnchor=ta))
    g.translate(xt, cy)
    g.rotate(90)
    d.add(g)


def north_angle_deg(azimuth_deg: float) -> float:
    """Where north points on a plan whose eave is at the bottom: the drawing's "up" is the direction the ridge lies in
    (the face's azimuth + 180), so north sits at 180 - azimuth degrees clockwise from up. A south face has north up;
    an east face has north to the right. The React drawing uses the same rule."""
    return (180.0 - float(azimuth_deg or 0)) % 360.0


def _north_arrow(d: Drawing, cx: float, cy: float, r: float, azimuth_deg: float, font: str, size: float) -> None:
    a = math.radians(north_angle_deg(azimuth_deg))
    dx, dy = math.sin(a), math.cos(a)
    d.add(Circle(cx, cy, r, fillColor=colors.white, strokeColor=brand.GRAY, strokeWidth=0.4))
    tip = (cx + dx * r * 0.82, cy + dy * r * 0.82)
    tail = (cx - dx * r * 0.7, cy - dy * r * 0.7)
    d.add(Line(tail[0], tail[1], tip[0], tip[1], strokeColor=brand.BLACK, strokeWidth=0.6))
    hw, hl = r * 0.22, r * 0.4
    base = (tip[0] - dx * hl, tip[1] - dy * hl)
    d.add(Polygon([tip[0], tip[1], base[0] - dy * hw, base[1] + dx * hw, base[0] + dy * hw, base[1] - dx * hw], fillColor=brand.BLACK, strokeColor=None))
    d.add(_text(cx + dx * (r + size * 0.6), cy + dy * (r + size * 0.6) - size * 0.35, "N", size, font, brand.BLACK, "middle"))


def _plan_margins(dimensions: bool, north_arrow: bool, has_ridge_dim: bool, font_pt: float) -> dict:
    """The frame around the face in points: the dimension rows need room on the left and under the eave, a ridge
    dimension and the north arrow room above. Shared by plan_drawing and fit_scale so a stated scale fits."""
    u = font_pt / 5.5
    side = 2.5 * mm
    top, bottom = 3.5 * mm, 5.5 * mm * u
    left = right = side
    row1 = row2 = 0.0
    if dimensions:
        row1, row2 = 4.2 * mm * u, 9.8 * mm * u          # the near chain (the strips) and the overall figure
        left = row2 + 3.6 * mm * u
        bottom += row2 + 1.6 * mm * u
        if has_ridge_dim:
            top = row1 + 4.0 * mm * u
    arrow_r = 0.0
    if north_arrow:
        arrow_r = 4.2 * mm * u
        top = max(top, 2 * arrow_r + 1.4 * font_pt + 2.4 * mm * u)     # the circle, the N above it when north is up, a gap
        right = max(right, 2 * arrow_r + 1.4 * font_pt + 1.0 * mm * u)
    return {"left": left, "right": right, "top": top, "bottom": bottom, "row1": row1, "row2": row2, "arrow_r": arrow_r, "u": u, "side": side}


def _has_ridge_dim(face: dict) -> bool:
    eave = max(float(face.get("eave_m") or 0), 0.1)
    ridge = float(face.get("ridge_m") or 0)
    return (face.get("shape") or "rect") == "hip" and 0 < ridge < eave - 1e-6


def _font_pt(width_mm: float, font_pt: Optional[float]) -> float:
    return float(font_pt) if font_pt else (5.5 if width_mm < 140 else 7.0)


def fit_scale(face: dict, width_mm: float, height_mm: float, *, dimensions: bool = True, north_arrow: bool = True,
              font_pt: Optional[float] = None, legend_lines: int = 0) -> int:
    """The largest standard scale (1:20 before 1:25 ...) at which the face, its dimension rows and its legend fit a
    box of width_mm × height_mm; the smallest standard scale when none does."""
    fp = _font_pt(width_mm, font_pt)
    m = _plan_margins(dimensions, north_arrow, _has_ridge_dim(face), fp)
    eave, slope = max(float(face.get("eave_m") or 0), 0.1), max(float(face.get("slope_m") or 0), 0.1)
    legend_h = (3.2 * mm * m["u"]) * legend_lines + (1.0 * mm if legend_lines else 0)
    for n in STANDARD_SCALES:
        s = 1000.0 / n * mm
        if eave * s + m["left"] + m["right"] <= width_mm * mm + 1e-6 and slope * s + m["top"] + m["bottom"] + legend_h <= height_mm * mm + 1e-6:
            return n
    return STANDARD_SCALES[-1]


def plan_drawing(face: dict, width_mm: float, highlight_used: bool = False, max_height_mm: Optional[float] = None, *,
                 dimensions: bool = False, scale_denominator: Optional[int] = None, string_labels: bool = False,
                 north_arrow: bool = False, font_pt: Optional[float] = None, legend: bool = True) -> Drawing:
    """Scaled plan of one face: outline, setback, the panels numbered along the rows, the cut strips hatched, trees and
    buildings as lettered markers on the edge they shade from, a 1 m scale bar, the eave labelled at the bottom and the
    direction the face looks toward. With highlight_used, panels the sized system does not use are drawn as spare
    positions (white, dashed).

    The plans for the PEE add, keyword only: `dimensions` (the eave, the slope and a hip's ridge as overall dimension
    lines, and the strips that hold no panels, the setback or a wall strip, as a near chain, all in metres),
    `scale_denominator` (the face drawn at exactly 1:N on paper instead of filling the width; the bottom line then
    states the scale), `string_labels` (S1, S2 ... under the panel number as the current rule numbers them),
    `north_arrow` (top right, from the face azimuth), `font_pt` (the text size; the dimension rows grow with it) and
    `legend=False` (the caller prints the legend itself). Without them the drawing is what the roof check and the
    proposal always printed."""
    F, FS, FB = brand.fonts()
    W = width_mm * mm
    fp = _font_pt(width_mm, font_pt)
    eave, slope = max(float(face["eave_m"]), 0.1), max(float(face["slope_m"]), 0.1)
    ridge_dim = dimensions and _has_ridge_dim(face)
    m = _plan_margins(dimensions, north_arrow, ridge_dim, fp)
    u, side = m["u"], m["side"]
    obstacles = list(face.get("obstacles") or [])
    markers = [o for o in obstacles if o.get("kind") == "shade"]
    walls = [o for o in obstacles if o.get("kind") == "wall"]
    legend_lines = [f"{chr(65 + i)}  {o.get('label', '')}" for i, o in enumerate(markers)] + [f"Hatched: {o.get('label', '')[:1].lower()}{o.get('label', '')[1:]}" for o in walls]
    if highlight_used and any(not p.get("used") for p in face.get("panels") or []):
        legend_lines.append("Dashed: positions your roof can still hold")
    if not legend:
        legend_lines = []
    line_h = 3.2 * mm * u
    legend_h = line_h * len(legend_lines) + (1.0 * mm if legend_lines else 0)
    avail_w = W - m["left"] - m["right"]
    if scale_denominator:
        s = 1000.0 / float(scale_denominator) * mm                     # points per metre at exactly 1:N
    else:
        max_h = (max_height_mm if max_height_mm else width_mm * 0.62) * mm
        s = min(avail_w / eave, max_h / slope)
    plan_w, plan_h = eave * s, slope * s
    H = m["top"] + plan_h + m["bottom"] + legend_h
    d = Drawing(W, H)
    d.hAlign = "LEFT"
    ox = m["left"] + (avail_w - plan_w) / 2.0
    oy = m["bottom"] + legend_h

    def X(x: float) -> float:
        return ox + float(x) * s

    def Y(y: float) -> float:
        return oy + float(y) * s

    outline_m = [(float(x), float(y)) for x, y in (face.get("outline") or [[0, 0], [eave, 0], [eave, slope], [0, slope]])]
    outline = [(X(x), Y(y)) for x, y in outline_m]
    d.add(Polygon([c for pt in outline for c in pt], fillColor=FACE_FILL, strokeColor=brand.BLACK, strokeWidth=0.7))
    # the strips: hatched, clipped to the face
    for o in walls:
        g = Group()
        g.add(_polygon_path(outline))
        x, y, w, h = X(o["x"]), Y(o["y"]), float(o["w"]) * s, float(o["h"]) * s
        g.add(Rect(x, y, w, h, fillColor=STRIP_FILL, strokeColor=None))
        for ln in _hatch(x, y, w, h, 1.6 * mm, brand.GOLD_DARK):
            g.add(ln)
        d.add(g)
    usable = face.get("usable") or []
    if len(usable) >= 3:
        d.add(Polygon([c for x, y in usable for c in (X(x), Y(y))], fillColor=None, strokeColor=brand.MUTED, strokeWidth=0.3, strokeDashArray=[1.2, 1.2]))
    # the panels, numbered from the eave up; the string under the number when asked
    for p in face.get("panels") or []:
        used = (not highlight_used) or bool(p.get("used"))
        x, y, w, h = X(p["x"]), Y(p["y"]), float(p["w"]) * s, float(p["h"]) * s
        if used:
            d.add(Rect(x, y, w, h, fillColor=PANEL_FILL, strokeColor=brand.GOLD_DARK, strokeWidth=0.45))
        else:
            d.add(Rect(x, y, w, h, fillColor=SPARE_FILL, strokeColor=brand.MUTED, strokeWidth=0.35, strokeDashArray=[1.0, 1.0]))
        if min(w, h) >= 3.2 * mm:
            size = max(4.0, min(7.0 * u, min(w, h) * 0.36))
            sub = f"S{p['string']}" if (string_labels and used and p.get("string")) else ""
            if sub and min(w, h) >= 6.5 * mm:
                d.add(_text(x + w / 2, y + h / 2 - size * 0.05, str(p.get("n", "")), size, FS, brand.BLACK, "middle"))
                d.add(_text(x + w / 2, y + h / 2 - size * 0.05 - size * 0.95, sub, size * 0.72, F, brand.GRAY, "middle"))
            else:
                d.add(_text(x + w / 2, y + h / 2 - size * 0.35, str(p.get("n", "")), size, FS if used else F, brand.BLACK if used else brand.MUTED, "middle"))
    # trees and buildings: a lettered marker on the edge they shade from
    r = 1.7 * mm * u
    for i, o in enumerate(markers):
        cx, cy = X(o["x"]), Y(o["y"])
        d.add(Circle(cx, cy, r, fillColor=brand.BLACK, strokeColor=colors.white, strokeWidth=0.5))
        d.add(_text(cx, cy - 1.6 * u, chr(65 + i), 4.8 * u, FB, colors.white, "middle"))
    # the dimension lines: the strips near the face, the overall figures one row out, a hip's ridge above
    if dimensions:
        t = 0.6 * mm * u
        row1, row2 = m["row1"], m["row2"]
        inset = max(float(face.get("setback_m") or 0), 0.0) / 2.0
        usable_pts = [(float(x), float(y)) for x, y in usable] if len(usable) >= 3 else []
        if usable_pts:
            y_lo = min(y for _, y in usable_pts)
            y_hi = max(y for _, y in usable_pts)
            bottom_pts = [x for x, y in usable_pts if abs(y - y_lo) < 1e-6]
            x_lo, x_hi = min(bottom_pts), max(bottom_pts)
        else:
            y_lo, y_hi, x_lo, x_hi = inset, slope - inset, inset, eave - inset
        strips = {o.get("edge"): float((o.get("w") if o.get("edge") in ("left", "right") else o.get("h")) or 0) for o in walls}
        # along the eave: the left and right strips, then the eave itself
        yl1, yl2 = oy - row1, oy - row2
        left_w = strips.get("left") or x_lo
        right_w = strips.get("right") or (eave - x_hi)
        if left_w > 1e-6:
            _dim_h(d, X(0), X(left_w), yl1, oy, f"{left_w:.2f}", F, fp, brand.GRAY, t, anchor="right")
        if right_w > 1e-6:
            _dim_h(d, X(eave - right_w), X(eave), yl1, oy, f"{right_w:.2f}", F, fp, brand.GRAY, t, anchor="left")
        _dim_h(d, X(0), X(eave), yl2, oy, f"{eave:.2f} m", FS, fp, brand.BLACK, t)
        # up the slope: the eave and ridge strips, then the slope
        xl1, xl2 = ox - row1, ox - row2
        bot_h = strips.get("eave") or y_lo
        top_h = strips.get("ridge") or (slope - y_hi)
        if bot_h > 1e-6:
            _dim_v(d, Y(0), Y(bot_h), xl1, ox, f"{bot_h:.2f}", F, fp, brand.GRAY, t, anchor="up")
        if top_h > 1e-6:
            _dim_v(d, Y(slope - top_h), Y(slope), xl1, ox, f"{top_h:.2f}", F, fp, brand.GRAY, t, anchor="down")
        _dim_v(d, Y(0), Y(slope), xl2, ox, f"{slope:.2f} m", FS, fp, brand.BLACK, t)
        if ridge_dim:
            rx = sorted(x for x, y in outline_m if abs(y - slope) < 1e-6)
            if len(rx) >= 2:
                _dim_h(d, X(rx[0]), X(rx[-1]), oy + plan_h + row1, oy + plan_h, f"ridge {rx[-1] - rx[0]:.2f} m", FS, fp, brand.BLACK, t)
    if north_arrow:
        ar = m["arrow_r"]
        _north_arrow(d, W - side - 0.7 * fp - ar, H - 1.4 * fp - ar - 0.8 * mm * u, ar, float(face.get("azimuth_deg") or 0), FB, fp)
    # the bottom line: scale bar, the eave, where the face looks
    yb = oy - m["bottom"] + 2.9 * mm * u
    bar = min(1.0 * s, plan_w)
    d.add(Line(X(0), yb, X(0) + bar, yb, strokeColor=brand.BLACK, strokeWidth=0.8))
    for xx in (X(0), X(0) + bar):
        d.add(Line(xx, yb - 0.8 * mm, xx, yb + 0.8 * mm, strokeColor=brand.BLACK, strokeWidth=0.6))
    bar_text = "1 m" if bar >= 1.0 * s - 1e-6 else f"{bar / s:.1f} m"
    if scale_denominator:
        bar_text += f" · scale 1:{int(scale_denominator)}"
    d.add(_text(X(0) + bar + 1.2 * mm, yb - 1.9 * u, bar_text, fp, F, brand.GRAY))
    eave_x = ox + plan_w / 2
    if dimensions or scale_denominator:
        # a narrow face on a wide sheet: the eave label moves right of the scale text rather than over it
        bar_right = X(0) + bar + 1.2 * mm + pdfmetrics.stringWidth(bar_text, F, fp)
        eave_x = max(eave_x, bar_right + 2.5 * mm + pdfmetrics.stringWidth("Eave (lower edge)", FS, fp) / 2)
    d.add(_text(eave_x, yb - 1.9 * u, "Eave (lower edge)", fp, FS, brand.BLACK, "middle"))
    looks = f"looks {face.get('compass') or ''} ({float(face.get('azimuth_deg') or 0):g}°)"
    if face.get("tilt_deg") is not None:
        looks += f" · pitch {float(face['tilt_deg']):g}°"
    d.add(_text(W - side, yb - 1.9 * u, looks, fp, F, brand.GRAY, "end"))
    for i, line in enumerate(legend_lines):
        d.add(_text(side, legend_h - (i + 1) * line_h + 0.6 * mm, _fit(line, F, fp, W - 2 * side), fp, F, brand.MUTED))
    return d


def plan_blocks(geometry: list[dict], width_mm: float, caption_style, note_style, columns: int = 2,
                highlight_used: bool = False, max_height_mm: Optional[float] = None, gutter_mm: float = 4.0) -> list:
    """Captioned plan drawings for every face that holds panels, `columns` to a row; a face with no panels gets one line
    instead. The caption names the face, its size and its panels. Each row is a one-row table, so a caption never parts
    from its drawing; the rows are plain flowables (not KeepTogether) so the caller may wrap the first one with its
    heading: a KeepTogether reports an unbounded height to its parent, so nesting one would force a page break."""
    out: list = []
    cells: list[list] = []
    notes: list = []
    draw_w = (width_mm - gutter_mm * (columns - 1)) / columns
    for face in geometry or []:
        n = len(face.get("panels") or [])
        name = escape(str(face.get("name") or "Roof"))
        size = f"{float(face['eave_m']):g} × {float(face['slope_m']):g} m"
        if n == 0:
            notes.append(Paragraph(f"{name} ({size}): no panels on this face.", note_style))
            continue
        used = face.get("used")
        if highlight_used and used is not None:
            cap = f"<b>{name}</b> ({size}): {used} of your {'panel' if used == 1 else 'panels'} here" if used else f"<b>{name}</b> ({size}): none of your panels sit here"
            if used and used < n:
                cap += f"; room for {n - used} more"
        else:
            cap = f"<b>{name}</b> ({size}): {n} {'panel' if n == 1 else 'panels'}"
        left_out = int(face.get("left_out") or 0)
        if left_out:
            cap += f"; {left_out} left out for vents or areas we marked on the roof"
        cells.append([Paragraph(cap, caption_style), Spacer(1, 2), plan_drawing(face, draw_w, highlight_used=highlight_used, max_height_mm=max_height_mm)])
    widths = [(draw_w + gutter_mm) * mm] * (columns - 1) + [draw_w * mm]   # the gutter is the right padding of every cell but the last
    for i in range(0, len(cells), columns):
        row = cells[i:i + columns] + [""] * (columns - len(cells[i:i + columns]))
        t = Table([row], colWidths=widths, hAlign="LEFT")
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-2, -1), gutter_mm * mm),
                               ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        out.append(t)
    out += notes
    return out


def _diamond(cx: float, cy: float, r: float, fill, stroke, width: float) -> Polygon:
    return Polygon([cx - r, cy, cx, cy + r, cx + r, cy, cx, cy - r], fillColor=fill, strokeColor=stroke, strokeWidth=width)


def gantt_drawing(events: list[dict], width_mm: float, today: Optional[date] = None) -> Drawing:
    """One bar per schedule event between its date and its end, milestones as black diamonds and payments as hollow
    gold diamonds, labelled, weeks ticked on the top axis, today marked when it falls in the range."""
    F, FS, FB = brand.fonts()
    W = width_mm * mm
    evs = [e for e in events or [] if e.get("date")]
    label_w = min(74 * mm, W * 0.34)
    row_h, axis_h, legend_h = 4.6 * mm, 7.0 * mm, 5.5 * mm
    H = axis_h + row_h * max(len(evs), 1) + legend_h
    d = Drawing(W, H)
    d.hAlign = "LEFT"
    if not evs:
        d.add(_text(0, H / 2, "No schedule yet.", 7, F, brand.MUTED))
        return d
    starts = [date.fromisoformat(str(e["date"])[:10]) for e in evs]
    ends = [date.fromisoformat(str(e["end"])[:10]) if e.get("end") else s for s, e in zip(starts, evs)]
    ends = [max(s, e) for s, e in zip(starts, ends)]
    d0 = min(starts)
    d0 = d0 - timedelta(days=d0.weekday())                               # the Monday on or before the first event
    d1 = max(ends) + timedelta(days=1)
    d1 = d1 + timedelta(days=(7 - d1.weekday()) % 7)                       # the Monday after the last event
    days = max((d1 - d0).days, 7)
    x0, x1 = label_w + 2 * mm, W - 2 * mm
    px = (x1 - x0) / days

    def X(dt: date) -> float:
        return x0 + (dt - d0).days * px

    top = H - axis_h
    # week ticks and the top axis
    d.add(Line(x0, top, x1, top, strokeColor=brand.LINE, strokeWidth=0.5))
    every = 1 if px * 7 >= 9 * mm else 2
    for k, day in enumerate(range(0, days + 1, 7)):
        x = X(d0 + timedelta(days=day))
        d.add(Line(x, legend_h, x, top, strokeColor=brand.LINE, strokeWidth=0.3))
        if k % every == 0 and day < days:
            d.add(_text(x + 0.8 * mm, top + 1.8 * mm, (d0 + timedelta(days=day)).strftime("%-d %b"), 5.5, F, brand.MUTED))
    d.add(_text(1 * mm, H - 2.2 * mm, "Weeks from " + d0.strftime("%-d %b %Y"), 5.5, F, brand.MUTED))   # the label column's top line
    # rows, top down
    for i, (e, s, en) in enumerate(zip(evs, starts, ends)):
        y_top = top - i * row_h
        y_mid = y_top - row_h / 2
        if i % 2 == 1:
            d.add(Rect(0, y_top - row_h, W, row_h, fillColor=brand.OFF_WHITE, strokeColor=None))
        kind = e.get("kind") or "task"
        amount = f" PHP {float(e['amount']):,.0f}" if e.get("amount") else ""
        label = _fit(str(e.get("label") or "") + amount, F, 6.5, label_w - 1 * mm)
        d.add(_text(1 * mm, y_mid - 2.2, label, 6.5, FS if kind == "milestone" else F, brand.GRAY))
        if kind == "task":
            xa, xb = X(s), X(en + timedelta(days=1))
            d.add(Rect(xa, y_mid - 1.4 * mm, max(xb - xa, 1.2 * mm), 2.8 * mm, rx=0.6 * mm, ry=0.6 * mm, fillColor=PANEL_FILL, strokeColor=brand.GOLD_DARK, strokeWidth=0.4))
            when = s.strftime("%-d %b") if en == s else f"{s.strftime('%-d %b')} to {en.strftime('%-d %b')}"
            right = max(xb, xa + 1.2 * mm)
        else:
            cx = X(s) + px / 2
            if kind == "payment_in":
                d.add(_diamond(cx, y_mid, 1.6 * mm, colors.white, brand.GOLD_DARK, 0.8))
            else:
                d.add(_diamond(cx, y_mid, 1.6 * mm, brand.BLACK, colors.white, 0.4))
            when = s.strftime("%-d %b")
            right = cx + 1.6 * mm
        tw = pdfmetrics.stringWidth(when, F, 5.5)
        if right + 1.2 * mm + tw <= x1:
            d.add(_text(right + 1.2 * mm, y_mid - 1.9, when, 5.5, F, brand.MUTED))
        else:
            left = X(s) if kind == "task" else X(s) + px / 2 - 1.6 * mm
            d.add(_text(left - 1.2 * mm, y_mid - 1.9, when, 5.5, F, brand.MUTED, "end"))
    if today is not None and d0 <= today < d1:
        xt = X(today) + px / 2
        d.add(Line(xt, legend_h, xt, H - 3.2 * mm, strokeColor=brand.GOLD_DARK, strokeWidth=0.7, strokeDashArray=[2, 1.5]))
        d.add(_text(xt, H - 2.2 * mm, "today", 5.5, FB, brand.GOLD_DARK, "middle"))   # above the week labels, so the two never touch
    # legend
    ly = 2.2 * mm
    x = x0
    d.add(Rect(x, ly - 1.0 * mm, 6 * mm, 2.0 * mm, rx=0.5 * mm, ry=0.5 * mm, fillColor=PANEL_FILL, strokeColor=brand.GOLD_DARK, strokeWidth=0.4))
    d.add(_text(x + 7.5 * mm, ly - 1.9, "task, from its start to its end", 5.5, F, brand.MUTED))
    x += 48 * mm
    d.add(_diamond(x + 1.6 * mm, ly, 1.4 * mm, brand.BLACK, colors.white, 0.4))
    d.add(_text(x + 4.5 * mm, ly - 1.9, "milestone", 5.5, F, brand.MUTED))
    x += 22 * mm
    d.add(_diamond(x + 1.6 * mm, ly, 1.4 * mm, colors.white, brand.GOLD_DARK, 0.8))
    d.add(_text(x + 4.5 * mm, ly - 1.9, "payment from the customer", 5.5, F, brand.MUTED))
    return d
