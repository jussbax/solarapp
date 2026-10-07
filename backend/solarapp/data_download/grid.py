"""Grid cells over a bounding box, filtered to cells that contain land."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PHILIPPINES_BBOX = (4.0, 21.5, 116.0, 127.0)  # lat_min, lat_max, lon_min, lon_max
DEFAULT_STEP = 0.25


@dataclass(frozen=True)
class GridCell:
    lat: float
    lon: float


def cell_centers(bbox: tuple[float, float, float, float], step: float = DEFAULT_STEP) -> list[GridCell]:
    lat_min, lat_max, lon_min, lon_max = bbox
    lats = np.round(np.arange(lat_min, lat_max + 1e-9, step), 4)
    lons = np.round(np.arange(lon_min, lon_max + 1e-9, step), 4)
    return [GridCell(float(a), float(o)) for a in lats for o in lons]


def land_cells(cells: list[GridCell], step: float = DEFAULT_STEP, sample_step: float = 0.02) -> list[GridCell]:
    """Keep cells where any sample point inside the cell is land.

    Uses the 1 km global land mask bundled with ``global_land_mask``; works
    offline. Coastal cells are kept because they contain some land.
    """
    from global_land_mask import globe

    half = step / 2.0
    offsets = np.arange(-half, half + 1e-9, sample_step)
    keep: list[GridCell] = []
    for c in cells:
        la, lo = np.meshgrid(c.lat + offsets, c.lon + offsets)
        la = np.clip(la, -89.999, 89.999)
        if np.any(globe.is_land(la.ravel(), lo.ravel())):
            keep.append(c)
    return keep
