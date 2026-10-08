"""Panel fitting on a roof face: rectangle, hip face (trapezoid) or triangle.

After a setback from every edge, panels are fitted row by row from the eave in
both orientations and the larger count is kept. A hip face narrows as it rises,
so each row is limited by the face width at the row's top edge. Shade strips
from walls (see core/shade.py) are cut from the edges before fitting. Ported
from the owner's earlier roof-check tool and kept consistent with the manual
method on rectangles.

Orientation: "portrait" = the panel's long side runs up the slope (short side
along the eave); "landscape" = the long side runs along the eave.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class FaceCuts:
    """No-panel strips cut from each edge, in metres along the slope (eave, ridge) or along the eave (left, right)."""
    eave: float = 0.0
    ridge: float = 0.0
    left: float = 0.0
    right: float = 0.0


@dataclass
class LayoutOption:
    orientation: str
    along_length: int   # panels in the widest row, along the eave
    along_width: int    # rows up the slope
    count: int
    rows: list[int] = field(default_factory=list)  # panels per row from the eave up


@dataclass
class LayoutResult:
    usable_length_m: float
    usable_width_m: float
    options: list[LayoutOption]
    best: LayoutOption
    count: int
    override_applied: bool
    shape: str = "rect"
    gross: int = 0          # fitted before panels left out
    left_out: int = 0       # vents, tanks, areas the surveyor excluded
    cuts: FaceCuts = field(default_factory=FaceCuts)

    def to_dict(self) -> dict:
        return asdict(self)


def _count_along(usable_m: float, size_m: float, gap_m: float) -> int:
    if usable_m <= 0 or size_m <= 0:
        return 0
    return int(math.floor((usable_m + gap_m) / (size_m + gap_m) + 1e-9))


def _inset_h(shape: str, eave_m: float, ridge_m: float, slope_m: float, inset_m: float) -> tuple[float, float]:
    """(horizontal shrink of each side over the full slope, the inset measured horizontally along a sloped side)."""
    off = (eave_m - ridge_m) / 2.0                       # horizontal shrink of each side over the full slope
    side_ang = math.atan2(off, slope_m) if slope_m > 0 else 0.0
    return off, (inset_m if shape == "rect" else inset_m / max(math.cos(side_ang), 1e-9))


def row_spans(shape: str, eave_m: float, ridge_m: float, slope_m: float, row_depth_m: float,
              inset_m: float, gap_m: float, cuts: FaceCuts):
    """(y, x_left, x_right) of every row from the eave up, in metres from the face's bottom-left corner: the band
    each row may use, limited by the face width at the row's top edge. The fitter counts panels in these bands and
    the plan drawing places them in the same bands, so the two never disagree."""
    off, inset_h = _inset_h(shape, eave_m, ridge_m, slope_m, inset_m)
    y_min = max(inset_m, cuts.eave)
    y_max = slope_m - max(inset_m, cuts.ridge)
    y = y_min
    while y + row_depth_m <= y_max + 1e-9:
        yt = y + row_depth_m
        o2 = off * yt / slope_m if slope_m > 0 else 0.0
        x_l = max(o2 + inset_h, cuts.left)
        x_r = min(eave_m - o2 - inset_h, eave_m - cuts.right)
        yield y, x_l, x_r
        y = yt + gap_m


def fit_rows(shape: str, eave_m: float, ridge_m: float, slope_m: float, row_depth_m: float, along_m: float,
             inset_m: float, gap_m: float, cuts: FaceCuts) -> list[int]:
    """Panels per row from the eave up, each row limited by the face width at its top edge."""
    rows: list[int] = []
    for _y, x_l, x_r in row_spans(shape, eave_m, ridge_m, slope_m, row_depth_m, inset_m, gap_m, cuts):
        w = x_r - x_l
        n = int(math.floor((w + gap_m) / (along_m + gap_m) + 1e-9)) if w > 0 else 0
        rows.append(n)
    return rows


def ridge_length(shape: str, eave_m: float, ridge_m: Optional[float]) -> float:
    """The top edge: the eave on a rectangle, nothing on a triangle, the given ridge (capped at the eave) on a hip face."""
    if shape == "rect":
        return eave_m
    if shape == "tri":
        return 0.0
    return min(max(float(ridge_m or 0.0), 0.0), eave_m)


def fit_face(
    shape: str,
    eave_m: float,
    slope_m: float,
    ridge_m: Optional[float],
    panel_length_m: float,
    panel_width_m: float,
    setback_per_dimension_m: float = 0.6,
    gap_m: float = 0.0,
    cuts: Optional[FaceCuts] = None,
    panels_left_out: int = 0,
    count_override: Optional[int] = None,
) -> LayoutResult:
    cuts = cuts or FaceCuts()
    shape = shape if shape in ("rect", "hip", "tri") else "rect"
    inset = max(setback_per_dimension_m, 0.0) / 2.0
    ridge = ridge_length(shape, eave_m, ridge_m)
    usable_l = max(eave_m - setback_per_dimension_m, 0.0)
    usable_w = max(slope_m - setback_per_dimension_m, 0.0)
    options = []
    for orientation, depth, along in (("portrait", panel_length_m, panel_width_m), ("landscape", panel_width_m, panel_length_m)):
        rows = fit_rows(shape, eave_m, ridge, slope_m, depth, along, inset, gap_m, cuts) if eave_m > 0 and slope_m > 0 else []
        rows = [r for r in rows]  # keep empty rows out of the count but in the list only when panels exist above? trim trailing zeros
        while rows and rows[-1] == 0:
            rows.pop()
        options.append(LayoutOption(orientation, max(rows) if rows else 0, len(rows), sum(rows), rows))
    portrait, landscape = options
    best = portrait if portrait.count >= landscape.count else landscape
    gross = best.count
    left_out = max(int(panels_left_out or 0), 0)
    override = count_override is not None and count_override >= 0
    count = int(count_override) if override else max(gross - left_out, 0)
    return LayoutResult(
        usable_length_m=usable_l, usable_width_m=usable_w, options=options, best=best, count=count,
        override_applied=override, shape=shape, gross=gross, left_out=min(left_out, gross) if not override else left_out, cuts=cuts,
    )


def fit_panels(
    face_length_m: float,
    face_width_m: float,
    panel_length_m: float,
    panel_width_m: float,
    setback_per_dimension_m: float = 0.6,
    gap_m: float = 0.0,
    count_override: Optional[int] = None,
) -> LayoutResult:
    """Rectangle face, the original entry point."""
    return fit_face("rect", face_length_m, face_width_m, None, panel_length_m, panel_width_m, setback_per_dimension_m, gap_m, None, 0, count_override)


# ---- geometry for the plan drawing: metres from the face's bottom-left corner, eave at the bottom, slope upwards

COMPASS16 = ["north", "north-northeast", "northeast", "east-northeast", "east", "east-southeast", "southeast", "south-southeast",
             "south", "south-southwest", "southwest", "west-southwest", "west", "west-northwest", "northwest", "north-northwest"]
EDGES = ("eave", "ridge", "left", "right")


def compass_name(azimuth_deg: float) -> str:
    return COMPASS16[int(((azimuth_deg % 360) + 11.25) // 22.5) % 16]


def _r(v: float) -> float:
    return round(float(v), 3)


def face_outline(shape: str, eave_m: float, ridge_m: float, slope_m: float) -> list[list[float]]:
    """The face itself: a rectangle, a trapezoid (hip) or a triangle, counter-clockwise from the bottom-left corner."""
    off = (eave_m - ridge_m) / 2.0
    if shape == "rect":
        return [[0.0, 0.0], [_r(eave_m), 0.0], [_r(eave_m), _r(slope_m)], [0.0, _r(slope_m)]]
    if shape == "tri" or ridge_m <= 1e-9:
        return [[0.0, 0.0], [_r(eave_m), 0.0], [_r(eave_m / 2.0), _r(slope_m)]]
    return [[0.0, 0.0], [_r(eave_m), 0.0], [_r(eave_m - off), _r(slope_m)], [_r(off), _r(slope_m)]]


def usable_outline(shape: str, eave_m: float, ridge_m: float, slope_m: float, inset_m: float) -> list[list[float]]:
    """The face after the setback: the area the fitter may use (the same inset the fitter applies)."""
    off, inset_h = _inset_h(shape, eave_m, ridge_m, slope_m, inset_m)
    y0, y1 = inset_m, slope_m - inset_m
    if y1 <= y0 or eave_m - 2 * inset_h <= 0:
        return []

    def span(y: float) -> tuple[float, float]:
        o2 = off * y / slope_m if slope_m > 0 else 0.0
        return o2 + inset_h, eave_m - o2 - inset_h

    l0, r0 = span(y0)
    l1, r1 = span(y1)
    if r1 <= l1:  # the sides meet below the top: a triangle with its apex where they cross
        y_apex = (eave_m - 2 * inset_h) * slope_m / (2 * off) if off > 0 else y1
        return [[_r(l0), _r(y0)], [_r(r0), _r(y0)], [_r(eave_m / 2.0), _r(y_apex)]]
    return [[_r(l0), _r(y0)], [_r(r0), _r(y0)], [_r(r1), _r(y1)], [_r(l1), _r(y1)]]


def panel_rects(shape: str, eave_m: float, ridge_m: float, slope_m: float, row_depth_m: float, along_m: float,
                inset_m: float, gap_m: float, cuts: FaceCuts, rows: list[int]) -> list[dict]:
    """One rectangle per fitted panel, from the eave up and left to right: each row's panels centred in the band the
    fitter measured for that row, with the same gap. `row` counts from 1 at the eave; `n` numbers the panels on the face."""
    out: list[dict] = []
    for i, (y, x_l, x_r) in enumerate(row_spans(shape, eave_m, ridge_m, slope_m, row_depth_m, inset_m, gap_m, cuts)):
        if i >= len(rows):
            break
        n = int(rows[i])
        if n <= 0:
            continue
        total = n * along_m + (n - 1) * gap_m
        x0 = x_l + (x_r - x_l - total) / 2.0
        for j in range(n):
            out.append({"x": _r(x0 + j * (along_m + gap_m)), "y": _r(y), "w": _r(along_m), "h": _r(row_depth_m), "row": i + 1, "n": len(out) + 1})
    return out


def shade_marker(face_azimuth_deg: float, direction_deg: float, eave_m: float, slope_m: float) -> tuple[str, float, float]:
    """Where a tree or building sits around the face: the edge it shades from and a point on that edge. Bearings are
    taken relative to the direction the face looks toward; the left edge is the side at azimuth + 90 (left as you
    face the roof from the ground), the same convention as the wall strips in core/shade.py."""
    r = (float(direction_deg) - float(face_azimuth_deg)) % 360.0
    if r < 45 or r >= 315:
        rr = r if r < 45 else r - 360.0            # -45 .. 45: beyond the eave; positive turns toward the left edge
        return "eave", eave_m / 2.0 * (1.0 - rr / 45.0), 0.0
    if r < 135:
        return "left", 0.0, slope_m * (r - 45.0) / 90.0
    if r < 225:
        return "ridge", eave_m * (r - 135.0) / 90.0, slope_m
    return "right", eave_m, slope_m * (1.0 - (r - 225.0) / 90.0)


def face_geometry(
    *, face_id: str, name: str, shape: str, eave_m: float, slope_m: float, ridge_m: Optional[float], azimuth_deg: float, tilt_deg: float,
    panel_length_m: float, panel_width_m: float, setback_per_dimension_m: float, gap_m: float, cuts: FaceCuts,
    orientation: str, rows: list[int], count: int, gross: int, left_out: int,
    walls: Optional[list[dict]] = None, obstacles: Optional[list[dict]] = None,
) -> dict:
    """The plan of one face for the drawings (contract C3): outline, panels, cuts and obstacles in metres from the
    face's bottom-left corner. `walls` carry edge, height_m and strip_m (the main-hours strip, None = the whole face);
    `obstacles` carry label, direction_deg, elevation_deg and cls from the shade model. Positions beyond `count`
    (panels left out for vents, tanks or an override) are not drawn: where they sit is the surveyor's call."""
    shape = shape if shape in ("rect", "hip", "tri") else "rect"
    ridge = ridge_length(shape, eave_m, ridge_m)
    inset = max(setback_per_dimension_m, 0.0) / 2.0
    depth, along = (panel_length_m, panel_width_m) if orientation == "portrait" else (panel_width_m, panel_length_m)
    rects = panel_rects(shape, eave_m, ridge, slope_m, depth, along, inset, gap_m, cuts, list(rows or []))
    if count < len(rects):
        rects = rects[:max(int(count), 0)]
    items: list[dict] = []
    for w in walls or []:
        edge = w.get("edge")
        if edge not in EDGES:
            continue
        dim = slope_m if edge in ("eave", "ridge") else eave_m
        strip = w.get("strip_m")
        depth_m = dim if strip is None else min(float(strip), dim)
        if depth_m <= 0:
            continue
        if edge == "eave":
            x, y, ww, hh = 0.0, 0.0, eave_m, depth_m
        elif edge == "ridge":
            x, y, ww, hh = 0.0, slope_m - depth_m, eave_m, depth_m
        elif edge == "left":
            x, y, ww, hh = 0.0, 0.0, depth_m, slope_m
        else:
            x, y, ww, hh = eave_m - depth_m, 0.0, depth_m, slope_m
        height = float(w.get("height_m") or 0.0)
        items.append({
            "kind": "wall", "edge": edge, "x": _r(x), "y": _r(y), "w": _r(ww), "h": _r(hh), "height_m": _r(height), "depth_m": _r(depth_m),
            "label": f"Wall on the {edge} side, {height:g} m above the roof: no panels within {depth_m:.1f} m of it",
        })
    for t in obstacles or []:
        elev = float(t.get("elevation_deg") or 0.0)
        if elev <= 0:
            continue
        direction = float(t.get("direction_deg") or 0.0)
        edge, x, y = shade_marker(azimuth_deg, direction, eave_m, slope_m)
        cls = t.get("cls") or ""
        effect = {"clear": "no shade in the main hours", "small": "small loss early or late in some months", "main": "shade in the main hours in some months"}.get(cls, "")
        label = f"{t.get('label') or 'Obstruction'}, {compass_name(direction)}, {elev:g}° up" + (f": {effect}" if effect else "")
        items.append({"kind": "shade", "edge": edge, "x": _r(x), "y": _r(y), "w": 0.0, "h": 0.0, "cls": cls, "label": label})
    return {
        "face_id": face_id, "name": name, "shape": shape,
        "eave_m": _r(eave_m), "slope_m": _r(slope_m), "ridge_m": _r(ridge), "azimuth_deg": _r(azimuth_deg), "tilt_deg": _r(tilt_deg),
        "compass": compass_name(azimuth_deg), "orientation": orientation,
        "setback_m": _r(setback_per_dimension_m), "gap_m": _r(gap_m), "panel_length_m": _r(panel_length_m), "panel_width_m": _r(panel_width_m),
        "outline": face_outline(shape, eave_m, ridge, slope_m),
        "usable": usable_outline(shape, eave_m, ridge, slope_m, inset),
        "panels": rects,
        "count": int(count), "gross": int(gross), "left_out": int(left_out), "used": None,
        "cuts": {"eave": _r(cuts.eave), "ridge": _r(cuts.ridge), "left": _r(cuts.left), "right": _r(cuts.right)},
        "obstacles": items,
    }


def string_rule(panel_count: int, max_panels_per_string: int, strings_override: Optional[int] = None) -> tuple[int, int]:
    """(strings, panels per string): the BOQ's rule, strings = ceil(count / max per string) unless overridden."""
    n = max(int(panel_count), 0)
    strings = strings_override or int(math.ceil(n / max(int(max_panels_per_string), 1) - 1e-9))
    strings = max(int(strings), 1)
    return strings, (int(math.ceil(n / strings)) if n > 0 else 0)


def mark_used(geometry: list[dict], used_total: int, per_string: Optional[int] = None) -> None:
    """Flag the panels the sized system uses: faces in order, rows from the eave up, left to right (the BOQ fills its
    rows the same way, see pricing/job.py rows_from_layout). With `per_string`, consecutive used panels get their
    string number, 1 upwards; unused panels carry no string."""
    k = 0
    for face in geometry:
        used = 0
        for p in face["panels"]:
            p["used"] = k < used_total
            if p["used"]:
                used += 1
                if per_string:
                    p["string"] = k // per_string + 1
            k += 1
        face["used"] = used
