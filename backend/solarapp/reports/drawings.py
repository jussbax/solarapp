"""The two engineering drawings as ReportLab flowables: the plan of a roof face (from results["geometry"], contract C3)
and the Gantt chart of the program of works (from program["events"]). Brand black and gold with light fills,
Montserrat like the other reports. The React components draw the same content from the same data."""
from __future__ import annotations

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


def plan_drawing(face: dict, width_mm: float, highlight_used: bool = False, max_height_mm: Optional[float] = None) -> Drawing:
    """Scaled plan of one face: outline, setback, the panels numbered along the rows, the cut strips hatched, trees and
    buildings as lettered markers on the edge they shade from, a 1 m scale bar, the eave labelled at the bottom and the
    direction the face looks toward. With highlight_used, panels the sized system does not use are drawn as spare
    positions (white, dashed)."""
    F, FS, FB = brand.fonts()
    W = width_mm * mm
    eave, slope = max(float(face["eave_m"]), 0.1), max(float(face["slope_m"]), 0.1)
    obstacles = list(face.get("obstacles") or [])
    markers = [o for o in obstacles if o.get("kind") == "shade"]
    walls = [o for o in obstacles if o.get("kind") == "wall"]
    legend = [f"{chr(65 + i)}  {o.get('label', '')}" for i, o in enumerate(markers)] + [f"Hatched: {o.get('label', '')[:1].lower()}{o.get('label', '')[1:]}" for o in walls]
    if highlight_used and any(not p.get("used") for p in face.get("panels") or []):
        legend.append("Dashed: positions your roof can still hold")
    side, top, bottom, line_h = 2.5 * mm, 3.5 * mm, 5.5 * mm, 3.2 * mm
    legend_h = line_h * len(legend) + (1.0 * mm if legend else 0)
    max_h = (max_height_mm if max_height_mm else width_mm * 0.62) * mm
    s = min((W - 2 * side) / eave, max_h / slope)          # points per metre
    plan_w, plan_h = eave * s, slope * s
    H = top + plan_h + bottom + legend_h
    d = Drawing(W, H)
    d.hAlign = "LEFT"
    ox = side + (W - 2 * side - plan_w) / 2.0
    oy = bottom + legend_h

    def X(x: float) -> float:
        return ox + float(x) * s

    def Y(y: float) -> float:
        return oy + float(y) * s

    outline = [(X(x), Y(y)) for x, y in (face.get("outline") or [[0, 0], [eave, 0], [eave, slope], [0, slope]])]
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
    # the panels, numbered from the eave up
    for p in face.get("panels") or []:
        used = (not highlight_used) or bool(p.get("used"))
        x, y, w, h = X(p["x"]), Y(p["y"]), float(p["w"]) * s, float(p["h"]) * s
        if used:
            d.add(Rect(x, y, w, h, fillColor=PANEL_FILL, strokeColor=brand.GOLD_DARK, strokeWidth=0.45))
        else:
            d.add(Rect(x, y, w, h, fillColor=SPARE_FILL, strokeColor=brand.MUTED, strokeWidth=0.35, strokeDashArray=[1.0, 1.0]))
        if min(w, h) >= 3.2 * mm:
            size = max(4.0, min(7.0, min(w, h) * 0.36))
            d.add(_text(x + w / 2, y + h / 2 - size * 0.35, str(p.get("n", "")), size, FS if used else F, brand.BLACK if used else brand.MUTED, "middle"))
    # trees and buildings: a lettered marker on the edge they shade from
    r = 1.7 * mm
    for i, o in enumerate(markers):
        cx, cy = X(o["x"]), Y(o["y"])
        d.add(Circle(cx, cy, r, fillColor=brand.BLACK, strokeColor=colors.white, strokeWidth=0.5))
        d.add(_text(cx, cy - 1.6, chr(65 + i), 4.8, FB, colors.white, "middle"))
    # the bottom line: scale bar, the eave, where the face looks
    yb = oy - 2.6 * mm
    bar = min(1.0 * s, plan_w)
    d.add(Line(X(0), yb, X(0) + bar, yb, strokeColor=brand.BLACK, strokeWidth=0.8))
    for xx in (X(0), X(0) + bar):
        d.add(Line(xx, yb - 0.8 * mm, xx, yb + 0.8 * mm, strokeColor=brand.BLACK, strokeWidth=0.6))
    d.add(_text(X(0) + bar + 1.2 * mm, yb - 1.9, "1 m" if bar >= 1.0 * s - 1e-6 else f"{bar / s:.1f} m", 5.5, F, brand.GRAY))
    d.add(_text(ox + plan_w / 2, yb - 1.9, "Eave (lower edge)", 5.5, FS, brand.BLACK, "middle"))
    looks = f"looks {face.get('compass') or ''} ({float(face.get('azimuth_deg') or 0):g}°)"
    if face.get("tilt_deg") is not None:
        looks += f" · pitch {float(face['tilt_deg']):g}°"
    d.add(_text(W - side, yb - 1.9, looks, 5.5, F, brand.GRAY, "end"))
    for i, line in enumerate(legend):
        d.add(_text(side, legend_h - (i + 1) * line_h + 0.6 * mm, _fit(line, F, 5.5, W - 2 * side), 5.5, F, brand.MUTED))
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
