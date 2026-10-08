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


def fit_rows(shape: str, eave_m: float, ridge_m: float, slope_m: float, row_depth_m: float, along_m: float,
             inset_m: float, gap_m: float, cuts: FaceCuts) -> list[int]:
    """Panels per row from the eave up, each row limited by the face width at its top edge."""
    off = (eave_m - ridge_m) / 2.0                       # horizontal shrink of each side over the full slope
    side_ang = math.atan2(off, slope_m) if slope_m > 0 else 0.0
    inset_h = inset_m if shape == "rect" else inset_m / max(math.cos(side_ang), 1e-9)
    y_min = max(inset_m, cuts.eave)
    y_max = slope_m - max(inset_m, cuts.ridge)
    rows: list[int] = []
    y = y_min
    while y + row_depth_m <= y_max + 1e-9:
        yt = y + row_depth_m
        o2 = off * yt / slope_m if slope_m > 0 else 0.0
        x_l = max(o2 + inset_h, cuts.left)
        x_r = min(eave_m - o2 - inset_h, eave_m - cuts.right)
        w = x_r - x_l
        n = int(math.floor((w + gap_m) / (along_m + gap_m) + 1e-9)) if w > 0 else 0
        rows.append(n)
        y = yt + gap_m
    return rows


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
    if shape == "rect":
        ridge = eave_m
    elif shape == "tri":
        ridge = 0.0
    else:
        ridge = min(max(float(ridge_m or 0.0), 0.0), eave_m)
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
