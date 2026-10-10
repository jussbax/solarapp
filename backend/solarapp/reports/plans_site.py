"""The vicinity map and site plan sheet of the plans for the PEE (round 13, item 4, docs/audits/round-13/engineer-brief.md
4.1 and 4.2). The left half prints the vicinity map on record (the office's upload when present, else the mosaics
composed from map tiles by reports/vicinity.py, else the pin, the address and the reason no map was fetched); the right
half is the site plan drawn to a standard scale with true north up: the roof faces in their true orientation (the slope
foreshortened by cos(tilt), the eave's outward normal pointing to the azimuth) at the offsets the surveyor typed, the
used panels inside, the lot and house outlines when typed (the equirectangular projection from the pin), the setbacks
from each house wall straight out to the property line, the inverter, battery, point-of-interconnection and meter
points, the north arrow and a 1 m / 5 m scale bar.

Nothing invented: an input the record does not hold prints as a note with its reason ("property line: not surveyed",
"relative positions not surveyed; faces shown in true orientation only", "not chosen (Site step)"), never a guess."""
from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

from ..core.towns import nearest_town
from ..schemas import AssessmentDoc
from . import brand
from .drawings import FACE_FILL, PANEL_FILL, STANDARD_SCALES, _north_arrow, _text
from .vicinity import MOSAIC_PX, current_file, is_current, metres_per_pixel

SHEET_NAME = "Vicinity map and site plan"
BOX_W_MM, BOX_H_MM = 190.0, 226.0                       # the site plan's box (the brief's 190 × 230 less the sheet's title row)
MARGIN_MM = {"left": 16.0, "right": 16.0, "top": 10.0, "bottom": 14.0}   # room for the dimension texts, the arrow and the scale bar
MAP_MM, INSET_MM = 140.0, 64.0                          # the main map and the inset on paper
STRIP_GAP_M = 1.0                                       # between faces laid side by side when their positions are not surveyed
M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON_EQUATOR = 111320.0
DASH_DOT = [4.0, 1.5, 0.8, 1.5]

Pt = tuple[float, float]


# ---- geometry in metres east and north of the pin

def to_metres(lat: float, lon: float, lat0: float, lon0: float) -> Pt:
    """The equirectangular projection the brief gives (adequate below 500 m): metres east and north of the pin."""
    east = (float(lon) - float(lon0)) * M_PER_DEG_LON_EQUATOR * math.cos(math.radians(float(lat0)))
    north = (float(lat) - float(lat0)) * M_PER_DEG_LAT
    return east, north


def from_metres(east: float, north: float, lat0: float, lon0: float) -> Pt:
    """The inverse, for the tests that type a lot of known size: (lat, lon)."""
    return float(lat0) + north / M_PER_DEG_LAT, float(lon0) + east / (M_PER_DEG_LON_EQUATOR * math.cos(math.radians(float(lat0))))


def face_axes(azimuth_deg: float) -> tuple[Pt, Pt]:
    """The unit vectors (east, north) of a face's plan: `ex` along the eave from its left end to its right (the left edge
    is the side at azimuth + 90, as the shade model has it), `ey` up the slope toward the ridge (azimuth + 180). A south
    face has ex east and ey north; an east face has its eave running north and its ridge to the west."""
    a = math.radians(float(azimuth_deg or 0))
    return (-math.cos(a), math.sin(a)), (-math.sin(a), -math.cos(a))


def face_plan(g: dict, origin: Pt) -> dict:
    """One face in plan, metres east/north: its outline and used panels rotated into true orientation with the slope
    foreshortened by cos(tilt), the eave midpoint at `origin`; the eave and the right side as segments for the dimension
    lines; the bounding box."""
    eave, slope = float(g.get("eave_m") or 0), float(g.get("slope_m") or 0)
    tilt = float(g.get("tilt_deg") or 0)
    ct = math.cos(math.radians(tilt))
    ex, ey = face_axes(float(g.get("azimuth_deg") or 0))

    def w(x: float, y: float) -> Pt:
        lx, ly = float(x) - eave / 2.0, float(y) * ct
        return origin[0] + lx * ex[0] + ly * ey[0], origin[1] + lx * ex[1] + ly * ey[1]

    outline_local = g.get("outline") or [[0, 0], [eave, 0], [eave, slope], [0, slope]]
    outline = [w(x, y) for x, y in outline_local]
    used_flag = g.get("used")
    panels = []
    for p in g.get("panels") or []:
        if used_flag is not None and not p.get("used"):
            continue
        x, y, pw, ph = float(p["x"]), float(p["y"]), float(p["w"]), float(p["h"])
        panels.append([w(x, y), w(x + pw, y), w(x + pw, y + ph), w(x, y + ph)])
    es = [e for e, _ in outline]
    ns = [n for _, n in outline]
    return {
        "name": str(g.get("name") or "Roof"), "outline": outline, "panels": panels, "n_panels": len(panels),
        "eave_m": eave, "slope_m": slope, "tilt_deg": tilt, "depth_m": slope * ct, "azimuth_deg": float(g.get("azimuth_deg") or 0),
        "eave": (w(0, 0), w(eave, 0)), "side": (w(eave, 0), w(eave, slope)), "ex": ex, "ey": ey,
        "eave_out": (math.sin(math.radians(float(g.get("azimuth_deg") or 0))), math.cos(math.radians(float(g.get("azimuth_deg") or 0)))),
        "bbox": (min(es), min(ns), max(es), max(ns)),
        "centroid": (sum(es) / len(es), sum(ns) / len(ns)),
    }


def _shift(plan: dict, de: float, dn: float) -> dict:
    def s(p: Pt) -> Pt:
        return p[0] + de, p[1] + dn

    out = dict(plan)
    out["outline"] = [s(p) for p in plan["outline"]]
    out["panels"] = [[s(p) for p in quad] for quad in plan["panels"]]
    out["eave"] = (s(plan["eave"][0]), s(plan["eave"][1]))
    out["side"] = (s(plan["side"][0]), s(plan["side"][1]))
    b = plan["bbox"]
    out["bbox"] = (b[0] + de, b[1] + dn, b[2] + de, b[3] + dn)
    out["centroid"] = s(plan["centroid"])
    return out


def _signed_area(poly: list[Pt]) -> float:
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def _edges(poly: list[Pt]) -> list[tuple[Pt, Pt, Pt]]:
    """(p1, p2, outward unit normal) for every edge, whichever way the corners were typed."""
    ccw = _signed_area(poly) > 0
    out = []
    for i in range(len(poly)):
        p1, p2 = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy) or 1.0
        nrm = (dy / length, -dx / length) if ccw else (-dy / length, dx / length)
        out.append((p1, p2, nrm))
    return out


def _ray_to_polygon(start: Pt, direction: Pt, poly: list[Pt]) -> Optional[float]:
    """The distance along `direction` (a unit vector) from `start` to the first edge of `poly` it meets; None when it meets none."""
    best: Optional[float] = None
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ex_, ey_ = b[0] - a[0], b[1] - a[1]
        denom = direction[0] * ey_ - direction[1] * ex_
        if abs(denom) < 1e-12:
            continue
        wx, wy = a[0] - start[0], a[1] - start[1]
        t = (wx * ey_ - wy * ex_) / denom
        u = (wx * direction[1] - wy * direction[0]) / denom
        if t > 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            best = t if best is None else min(best, t)
    return best


def setbacks(house: list[Pt], lot: list[Pt]) -> list[tuple[Pt, Pt, float]]:
    """From each house wall's midpoint straight out (its outward normal) to the property line: (midpoint, foot, metres)."""
    out = []
    for p1, p2, nrm in _edges(house):
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        t = _ray_to_polygon(mid, nrm, lot)
        if t is not None:
            out.append((mid, (mid[0] + nrm[0] * t, mid[1] + nrm[1] * t), t))
    return out


def fit_site_scale(width_m: float, height_m: float, box_w_mm: float = BOX_W_MM, box_h_mm: float = BOX_H_MM) -> int:
    """The largest standard scale at which the extent and the margins fit the box; the smallest when none does."""
    mw = MARGIN_MM["left"] + MARGIN_MM["right"]
    mh = MARGIN_MM["top"] + MARGIN_MM["bottom"]
    for n in STANDARD_SCALES:
        s = 1000.0 / n
        if width_m * s + mw <= box_w_mm + 1e-6 and height_m * s + mh <= box_h_mm + 1e-6:
            return n
    return STANDARD_SCALES[-1]


# ---- the drawing

def _dim_seg(d: Drawing, p1: Pt, p2: Pt, out: Pt, gap: float, text: str, font: str, size: float, color, t: float = 1.7) -> None:
    """An architectural dimension between two paper points: the line `gap` outward from the segment, extension lines
    from the points, 45° ticks, the figure along the line on its outward side, turned so it never reads upside down."""
    ux, uy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(ux, uy)
    if length < 1e-6:
        return
    ux, uy = ux / length, uy / length
    a1 = (p1[0] + out[0] * gap, p1[1] + out[1] * gap)
    a2 = (p2[0] + out[0] * gap, p2[1] + out[1] * gap)
    d.add(Line(a1[0], a1[1], a2[0], a2[1], strokeColor=color, strokeWidth=0.35))
    ext = gap + 0.9 * t
    for p in (p1, p2):
        d.add(Line(p[0] + out[0] * 0.6, p[1] + out[1] * 0.6, p[0] + out[0] * ext, p[1] + out[1] * ext, strokeColor=color, strokeWidth=0.25))
    tx, ty = (ux - uy) / math.sqrt(2) * t, (uy + ux) / math.sqrt(2) * t      # the tick at 45° to the line
    for a in (a1, a2):
        d.add(Line(a[0] - tx, a[1] - ty, a[0] + tx, a[1] + ty, strokeColor=color, strokeWidth=0.5))
    angle = math.degrees(math.atan2(uy, ux))
    if angle > 90 + 1e-6 or angle <= -90 + 1e-6:
        angle += 180.0                       # read it the other way round rather than upside down
    rad = math.radians(angle)
    up = (-math.sin(rad), math.cos(rad))     # where the glyphs rise after the rotation
    lift = 0.45 * t + 0.35
    # the glyphs sit beyond the line, away from the object: when they would rise toward it, the baseline moves out by their height
    base = lift if up[0] * out[0] + up[1] * out[1] >= 0 else lift + 0.72 * size
    mid = ((a1[0] + a2[0]) / 2 + out[0] * base, (a1[1] + a2[1]) / 2 + out[1] * base)
    g = Group(String(0, 0, text, fontName=font, fontSize=size, fillColor=color, textAnchor="middle"))
    g.translate(mid[0], mid[1])
    g.rotate(angle)
    d.add(g)


def _label(d: Drawing, x: float, y: float, lines: list[str], font: str, size: float, color=brand.BLACK) -> tuple[float, float, float, float]:
    """Centred text lines on a white pad, so a label reads over panels or hatching; returns the pad's box."""
    widths = [pdfmetrics.stringWidth(s, font, size) for s in lines]
    w, h = max(widths) + 2 * mm, len(lines) * size * 1.25 + 1.2 * mm
    pad = Rect(x - w / 2, y - h / 2, w, h, fillColor=colors.white, strokeColor=None)
    pad.fillOpacity = 0.78
    d.add(pad)
    top = y + h / 2 - 0.6 * mm - size
    for i, s in enumerate(lines):
        d.add(_text(x, top - i * size * 1.25, s, size, font, color, "middle"))
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def _symbol(d: Drawing, kind: str, x: float, y: float, font: str, size: float) -> None:
    """The site plan's equipment symbols: inverter a square, battery plates, the POI a filled circle, the meter an M in a circle."""
    r = 1.3 * mm
    if kind == "inverter":
        d.add(Rect(x - r, y - r, 2 * r, 2 * r, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.6))
        d.add(Line(x - r, y - r, x + r, y + r, strokeColor=brand.BLACK, strokeWidth=0.4))
    elif kind == "battery":
        d.add(Rect(x - r, y - r * 0.75, 2 * r, 1.5 * r, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.6))
        for k in (-0.45, 0.0, 0.45):
            d.add(Line(x + k * r, y - r * 0.45, x + k * r, y + r * 0.45, strokeColor=brand.BLACK, strokeWidth=0.6 if k else 1.1))
    elif kind == "poi":
        d.add(Circle(x, y, r * 0.8, fillColor=brand.BLACK, strokeColor=colors.white, strokeWidth=0.5))
    else:
        d.add(Circle(x, y, r, fillColor=colors.white, strokeColor=brand.BLACK, strokeWidth=0.6))
        d.add(_text(x, y - size * 0.36, "M", size, font, brand.BLACK, "middle"))


POINT_KINDS = (("inverter", "Inverter"), ("battery", "Battery"), ("poi", "POI"), ("meter", "Meter"))


def site_plan_drawing(doc: AssessmentDoc, geometry: list[dict], box_w_mm: float = BOX_W_MM, box_h_mm: float = BOX_H_MM) -> tuple[Drawing, int, list[str]]:
    """The site plan at a standard scale in a box: (the drawing, the scale denominator, the notes that say what is
    missing). True north up; the faces at their typed offsets, the rest side by side in a strip below."""
    F, FS, FB = brand.fonts()
    fp = 7.0
    lat0, lon0 = float(doc.lat or 0), float(doc.lon or 0)
    site = doc.site
    notes: list[str] = []
    offsets = {f.id: f.plan_offset_m for f in doc.faces}
    placed: list[dict] = []
    loose: list[dict] = []
    for g in geometry:
        off = offsets.get(str(g.get("face_id")))
        if off is not None:
            placed.append(face_plan(g, (float(off[0]), float(off[1]))))
        else:
            loose.append(face_plan(g, (0.0, 0.0)))
    lot = [to_metres(la, lo, lat0, lon0) for la, lo in site.lot_polygon] if len(site.lot_polygon) >= 3 else []
    house = [to_metres(la, lo, lat0, lon0) for la, lo in site.house_polygon] if len(site.house_polygon) >= 3 else []
    points = [(kind, label, to_metres(*getattr(site, f"{kind}_point"), lat0, lon0)) for kind, label in POINT_KINDS if getattr(site, f"{kind}_point") is not None]
    pts: list[Pt] = list(lot) + list(house) + [p for _, _, p in points]
    for fpn in placed:
        pts += fpn["outline"]
    anchored = bool(pts)
    if anchored:
        pts.append((0.0, 0.0))        # the pin, the origin of every offset
    if loose:
        if anchored:
            e_min, n_min = min(p[0] for p in pts), min(p[1] for p in pts)
        else:
            e_min, n_min = 0.0, 0.0
        row_h = max(f["bbox"][3] - f["bbox"][1] for f in loose)
        top = n_min - STRIP_GAP_M if anchored else row_h
        cursor = e_min
        for f in loose:
            b = f["bbox"]
            placed.append(_shift(f, cursor - b[0], top - b[3]))
            cursor += (b[2] - b[0]) + STRIP_GAP_M
            pts += placed[-1]["outline"]
        if not anchored:
            e_min = 0.0
        notes.append("relative positions not surveyed; " + ("these faces are shown in true orientation only, side by side below the site: " if anchored else "faces shown in true orientation only, side by side: ")
                     + ", ".join(f["name"] for f in loose))
    if not pts:
        pts = [(-1.0, -1.0), (1.0, 1.0)]
    e0, e1 = min(p[0] for p in pts), max(p[0] for p in pts)
    n0, n1 = min(p[1] for p in pts), max(p[1] for p in pts)
    if e1 - e0 < 2.0:
        e0, e1 = (e0 + e1) / 2 - 1.0, (e0 + e1) / 2 + 1.0
    if n1 - n0 < 2.0:
        n0, n1 = (n0 + n1) / 2 - 1.0, (n0 + n1) / 2 + 1.0
    scale_n = fit_site_scale(e1 - e0, n1 - n0, box_w_mm, box_h_mm)
    s = 1000.0 / scale_n * mm
    W, H = box_w_mm * mm, box_h_mm * mm
    d = Drawing(W, H)
    d.hAlign = "LEFT"
    inner_w = W - (MARGIN_MM["left"] + MARGIN_MM["right"]) * mm
    inner_h = H - (MARGIN_MM["top"] + MARGIN_MM["bottom"]) * mm
    ox = MARGIN_MM["left"] * mm + (inner_w - (e1 - e0) * s) / 2.0
    oy = MARGIN_MM["bottom"] * mm + (inner_h - (n1 - n0) * s) / 2.0

    def P(p: Pt) -> Pt:
        return ox + (p[0] - e0) * s, oy + (p[1] - n0) * s

    d.add(Rect(0, 0, W, H, fillColor=None, strokeColor=brand.LINE, strokeWidth=0.3))
    gap = 3.2 * mm
    # the lot: dash-dot, its edges' lengths outside
    if lot:
        d.add(Polygon([c for p in lot for c in P(p)], fillColor=None, strokeColor=brand.BLACK, strokeWidth=0.5, strokeDashArray=DASH_DOT))
        for p1, p2, nrm in _edges(lot):
            _dim_seg(d, P(p1), P(p2), nrm, gap, f"{math.dist(p1, p2):.2f} m", F, fp, brand.GRAY)
    else:
        notes.append("property line: not surveyed")
    # the house: solid, its overall width and depth
    if house:
        d.add(Polygon([c for p in house for c in P(p)], fillColor=None, strokeColor=brand.BLACK, strokeWidth=0.7))
        # the overall width along the north side and the depth along the west side (the main roof's eave is usually south or east)
        he0, he1 = min(p[0] for p in house), max(p[0] for p in house)
        hn0, hn1 = min(p[1] for p in house), max(p[1] for p in house)
        _dim_seg(d, P((he1, hn1)), P((he0, hn1)), (0.0, 1.0), gap * 0.6, f"house {he1 - he0:.2f} m", F, fp * 0.9, brand.GRAY)
        _dim_seg(d, P((he0, hn1)), P((he0, hn0)), (-1.0, 0.0), gap * 0.6, f"house {hn1 - hn0:.2f} m", F, fp * 0.9, brand.GRAY)
    else:
        notes.append("house outline: not surveyed")
    if lot and house:
        for mid_pt, foot, metres in setbacks(house, lot):
            a, b = P(mid_pt), P(foot)
            ux, uy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(ux, uy) or 1.0
            _dim_seg(d, a, b, (-uy / ln, ux / ln), 1.2 * mm, f"{metres:.2f}", F, fp * 0.85, brand.MUTED, t=1.3)
        notes.append("setback figures: from each house wall straight out to the property line; verify the zoning setback")
    else:
        notes.append("setbacks: not computed (the lot and the house outline are both needed)")
    # the faces: outline, used panels, name; the eave and the plan depth as dimensions
    face_boxes: list[tuple[float, float, float, float]] = []
    for f in placed:
        d.add(Polygon([c for p in f["outline"] for c in P(p)], fillColor=FACE_FILL, strokeColor=brand.BLACK, strokeWidth=0.7))
        for quad in f["panels"]:
            d.add(Polygon([c for p in quad for c in P(p)], fillColor=PANEL_FILL, strokeColor=brand.GOLD_DARK, strokeWidth=0.4))
        e1p, e2p = f["eave"]
        _dim_seg(d, P(e1p), P(e2p), f["eave_out"], gap, f"{f['eave_m']:.2f} m", FS, fp, brand.BLACK)
        s1p, s2p = f["side"]
        _dim_seg(d, P(s1p), P(s2p), f["ex"], gap, f"{f['depth_m']:.2f} m", F, fp, brand.GRAY)
        cx, cy = P(f["centroid"])
        face_boxes.append(_label(d, cx, cy, [f["name"], f"{f['n_panels']} panels · slope {f['slope_m']:g} m at {f['tilt_deg']:g}°, looks {f['azimuth_deg']:g}°"], FS, fp * 0.86))
    # the pin and the points: every symbol first, then each label where it overlaps no symbol and no label placed before it
    taken: list[tuple[float, float, float, float]] = face_boxes + [(cx - 1.5 * mm, cy - 1.5 * mm, cx + 1.5 * mm, cy + 1.5 * mm) for cx, cy in (P(p) for _, _, p in points)]
    labels: list[tuple[float, float, str, str, Any]] = []
    if anchored:
        px, py = P((0.0, 0.0))
        d.add(Line(px - 1.6 * mm, py, px + 1.6 * mm, py, strokeColor=brand.GOLD_DARK, strokeWidth=0.6))
        d.add(Line(px, py - 1.6 * mm, px, py + 1.6 * mm, strokeColor=brand.GOLD_DARK, strokeWidth=0.6))
        d.add(Circle(px, py, 0.9 * mm, fillColor=None, strokeColor=brand.GOLD_DARK, strokeWidth=0.6))
        taken.append((px - 1.6 * mm, py - 1.6 * mm, px + 1.6 * mm, py + 1.6 * mm))
        labels.append((px, py, "pin", F, brand.GOLD_DARK))
    for kind, label, p in points:
        x, y = P(p)
        _symbol(d, kind, x, y, FB, fp * 0.8)
        labels.append((x, y, label, FS, brand.BLACK))
    for x, y, label, font, color in labels:
        tw, th = pdfmetrics.stringWidth(label, font, fp * 0.85), fp * 0.85
        near = ((x + 2.0 * mm, y - th * 0.35, "start"), (x, y - 2.2 * mm - th, "middle"), (x, y + 2.4 * mm, "middle"), (x - 2.0 * mm, y - th * 0.35, "end"))
        far = ((x, y - 6.0 * mm - th, "middle"), (x, y + 6.0 * mm, "middle"), (x + 6.0 * mm, y - th * 0.35, "start"), (x - 6.0 * mm, y - th * 0.35, "end"))
        for lx, ly, anchor in near + far:
            x0 = lx if anchor == "start" else lx - tw / 2 if anchor == "middle" else lx - tw
            box = (x0, ly, x0 + tw, ly + th)
            if not any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in taken):
                break
        taken.append(box)
        d.add(_text(lx, ly, label, fp * 0.85, font, color, anchor))
    missing_pts = [label for kind, label in POINT_KINDS if getattr(site, f"{kind}_point") is None]
    if missing_pts:
        notes.append(", ".join(missing_pts).lower().replace("poi", "point of interconnection") + " location: not chosen (Site step)")
    # the north arrow (true north up: a south face's rule), the scale bar, the caption
    ar = 3.6 * mm
    _north_arrow(d, W - MARGIN_MM["right"] * mm / 2, H - MARGIN_MM["top"] * mm / 2 - 0.4 * mm, ar, 180.0, FB, fp)
    yb = 4.0 * mm
    x0 = MARGIN_MM["left"] * mm
    bar5 = 5.0 * s
    d.add(Line(x0, yb, x0 + bar5, yb, strokeColor=brand.BLACK, strokeWidth=0.8))
    for k, metres in ((0, 0.0), (1, 1.0), (2, 5.0)):
        xx = x0 + metres * s
        d.add(Line(xx, yb - 0.8 * mm, xx, yb + 0.8 * mm, strokeColor=brand.BLACK, strokeWidth=0.6))
        d.add(_text(xx, yb - 1.0 * mm - fp, "0" if k == 0 else f"{metres:g} m", fp * 0.85, F, brand.GRAY, "middle"))
    d.add(_text(x0 + bar5 + 3 * mm, yb - fp * 0.3, f"scale 1:{scale_n}", fp, F, brand.GRAY))
    d.add(_text(2.5 * mm, H - 2.5 * mm - fp, f"Site plan · scale 1:{scale_n} · true north up · metres east and north of the pin", fp, FS, brand.BLACK))
    return d, scale_n, notes


# ---- the sheet

def _d(s: Optional[str]) -> str:
    try:
        return datetime.fromisoformat(str(s)).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return str(s or "")[:10]


def site_sheet(doc: AssessmentDoc, geometry: list[dict], *, styles: dict, vicinity: Optional[dict], project_dir: Optional[Path],
               blank: str) -> tuple[str, list, Optional[int]]:
    """(the sheet's name, its flowables after the sheet marker, the site plan's scale denominator). `styles` carries the
    builder's paragraph styles and helpers (h1, h2, body, small, cell, cellb, P, two_col)."""
    h1, h2, body, small, P, two_col = styles["h1"], styles["h2"], styles["body"], styles["small"], styles["P"], styles["two_col"]
    lat, lon = doc.lat, doc.lon
    town_line = ""
    if lat is not None and lon is not None:
        (name, province, _la, _lo), km = nearest_town(lat, lon)
        town_line = f"nearest town centre {escape(name)}, {escape(province)} ({km:.1f} km)"
    pin_txt = f"pin {lat:.5f}, {lon:.5f}" if lat is not None and lon is not None else "no map pin"
    left: list = [Paragraph(SHEET_NAME, h1), Paragraph(" · ".join(x for x in (escape(doc.address or blank), pin_txt, town_line) if x), body), Paragraph("Vicinity map", h2)]
    state = vicinity or {}
    upload, osm, err = state.get("upload") or {}, state.get("osm") or {}, state.get("error") or {}
    up_file = current_file(state, project_dir, "upload") if upload else None
    z16 = current_file(state, project_dir, "z16") if osm else None
    z12 = current_file(state, project_dir, "z12") if osm else None
    caption: list[str] = []
    inset = None
    if up_file is not None:
        from PIL import Image as PilImage

        with PilImage.open(up_file) as im:
            w_px, h_px = im.size
        k = min(196.0 * mm / w_px, MAP_MM * mm / h_px)
        left.append(Image(str(up_file), width=w_px * k, height=h_px * k, hAlign="LEFT"))
        caption.append(f"vicinity map: uploaded by the office on {_d(upload.get('uploaded_at'))}" + (f"; {escape(str(upload.get('note') or ''))}" if upload.get("note") else "; no attribution typed"))
        if osm:
            caption.append("the mosaics fetched from map tiles are also on record; the upload is printed because it is present")
    elif z16 is not None:
        left.append(Image(str(z16), width=MAP_MM * mm, height=MAP_MM * mm, hAlign="LEFT"))
        if z12 is not None:
            inset = Image(str(z12), width=INSET_MM * mm, height=INSET_MM * mm, hAlign="LEFT")
        across16 = MOSAIC_PX * metres_per_pixel(float(lat or 0), 16) / 1000.0
        across12 = MOSAIC_PX * metres_per_pixel(float(lat or 0), 12) / 1000.0
        caption.append(f"{escape(str(osm.get('attribution') or ''))} — {escape(str(osm.get('host') or ''))}, fetched {_d(osm.get('fetched_at'))}; "
                       f"main map zoom 16, about {across16:.2f} km across; inset zoom 12, about {across12:.0f} km across; the marker is the project pin")
        if not is_current(state, lat, lon):
            caption.append(f"the map was made for pin {osm.get('pin', [0, 0])[0]:.5f}, {osm.get('pin', [0, 0])[1]:.5f} and the pin has since moved: press Prepare the map again (Site plan card)")
    else:
        reason = str(err.get("reason") or "not prepared yet: press Prepare the map on the Site plan card")
        caption.append(f"vicinity map: not fetched ({escape(reason)}); the office may upload a screen grab (Site plan card › Vicinity map). "
                       f"The pin {pin_txt.removeprefix('pin ')}, {escape(doc.address or blank)}; {town_line or 'no town behind the pin'}.")
    drawing, scale_n, notes = site_plan_drawing(doc, geometry)
    site = doc.site
    legend: list[str] = []
    for kind, label in POINT_KINDS:
        where = str(getattr(site, f"{kind}_location") or "").strip()
        pt = getattr(site, f"{kind}_point")
        if where or pt is not None:
            legend.append(f"<b>{label}</b>: {escape(where) if where else 'location not typed'}" + (f" ({pt[0]:.5f}, {pt[1]:.5f})" if pt is not None else " (point not chosen)"))
    text_block: list = [Paragraph(c, small) for c in caption]
    text_block.append(Paragraph("Site plan", h2))
    text_block += [Paragraph(x, small) for x in legend]
    text_block += [Paragraph(f"{escape(n)}.", small) for n in notes]
    text_block.append(Paragraph("Faces: the eave is the black figure, the plan depth (the slope × cos tilt) the grey one; solid gold panels belong to this system. "
                                "Dash-dot: the property line (corners as typed, projected from the pin). Solid: the house. Symbols: inverter a square, battery plates, POI a filled circle, M the meter.", small))
    if inset is not None:
        row = Table([[inset, text_block]], colWidths=[INSET_MM * mm + 3 * mm, 196 * mm - INSET_MM * mm - 3 * mm], hAlign="LEFT")
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                 ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        left += [Spacer(1, 1.5 * mm), row]
    else:
        left += [Spacer(1, 1.5 * mm)] + text_block
    sheet = Table([[left, [drawing]]], colWidths=[196 * mm, 194 * mm], hAlign="LEFT")
    sheet.setStyle(two_col)
    return SHEET_NAME, [sheet], scale_n
