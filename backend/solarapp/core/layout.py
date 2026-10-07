"""Panel fitting on a rectangular roof face.

Owner's method: subtract a setback from each dimension, then rows times
columns. Both panel orientations are tried and the larger count is kept. The
owner's rule of thumb (longer roof side divided by the shorter panel side) is
reported alongside for continuity. Gap between panels defaults to zero, which
matches the current manual method.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict


@dataclass
class LayoutOption:
    orientation: str  # "portrait" (panel length along face length) or "landscape"
    along_length: int
    along_width: int
    count: int


@dataclass
class LayoutResult:
    usable_length_m: float
    usable_width_m: float
    options: list[LayoutOption]
    best: LayoutOption
    rule_of_thumb_count: int
    count: int
    override_applied: bool

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def _count_along(usable_m: float, size_m: float, gap_m: float) -> int:
    if usable_m <= 0 or size_m <= 0:
        return 0
    return int(math.floor((usable_m + gap_m) / (size_m + gap_m) + 1e-9))


def fit_panels(
    face_length_m: float,
    face_width_m: float,
    panel_length_m: float,
    panel_width_m: float,
    setback_per_dimension_m: float = 0.6,
    gap_m: float = 0.0,
    count_override: int | None = None,
) -> LayoutResult:
    usable_l = max(face_length_m - setback_per_dimension_m, 0.0)
    usable_w = max(face_width_m - setback_per_dimension_m, 0.0)

    portrait = LayoutOption(
        "portrait",
        _count_along(usable_l, panel_length_m, gap_m),
        _count_along(usable_w, panel_width_m, gap_m),
        0,
    )
    portrait.count = portrait.along_length * portrait.along_width
    landscape = LayoutOption(
        "landscape",
        _count_along(usable_l, panel_width_m, gap_m),
        _count_along(usable_w, panel_length_m, gap_m),
        0,
    )
    landscape.count = landscape.along_length * landscape.along_width
    best = portrait if portrait.count >= landscape.count else landscape

    big_roof, small_roof = max(usable_l, usable_w), min(usable_l, usable_w)
    big_panel, small_panel = max(panel_length_m, panel_width_m), min(panel_length_m, panel_width_m)
    rule = _count_along(big_roof, small_panel, gap_m) * _count_along(small_roof, big_panel, gap_m)

    override = count_override is not None and count_override >= 0
    count = int(count_override) if override else best.count
    return LayoutResult(
        usable_length_m=usable_l,
        usable_width_m=usable_w,
        options=[portrait, landscape],
        best=best,
        rule_of_thumb_count=rule,
        count=count,
        override_applied=override,
    )
