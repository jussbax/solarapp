"""Access to the one-time downloaded weather datasets.

Layout under the data root (default ``data/``):

    pvgis/index.json                 metadata and the list of cells
    pvgis/cells/<lat>_<lon>.parquet  hourly TMY per grid cell
    nasa/climatology.json            NASA POWER monthly climatology (reference only)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

TMY_COLUMNS = ["temp_air", "rh", "ghi", "dni", "dhi", "ir", "wind_speed", "wind_dir", "pressure"]


def haversine_km(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    r = 6371.0
    p1, p2 = math.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


@dataclass
class CellInfo:
    id: str
    lat: float
    lon: float
    elevation_m: float
    file: Path
    radiation_db: str
    distance_km: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "lat": self.lat, "lon": self.lon, "elevation_m": self.elevation_m,
            "radiation_db": self.radiation_db, "distance_km": round(self.distance_km, 2),
        }


def cell_id(lat: float, lon: float) -> str:
    return f"{lat:.2f}_{lon:.2f}"


@lru_cache(maxsize=32)
def _read_parquet(path: str, mtime: float) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "time_utc" in df.columns:
        df = df.set_index("time_utc")
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    df.index = idx
    df.index.name = "time_utc"
    for c in TMY_COLUMNS:
        if c not in df.columns:
            df[c] = 0.0
    return df[TMY_COLUMNS].astype(float)


class PvgisDataset:
    def __init__(self, root: Path):
        self.root = Path(root) / "pvgis"
        self.index_path = self.root / "index.json"
        self._meta: dict = {}
        self._cells: list[CellInfo] = []
        self._lats = np.zeros(0)
        self._lons = np.zeros(0)
        self._index_mtime: Optional[float] = None
        self.reload()

    def reload(self) -> None:
        self._meta, self._cells = {}, []
        if not self.index_path.exists():
            self._lats = self._lons = np.zeros(0)
            self._index_mtime = None
            return
        self._index_mtime = self.index_path.stat().st_mtime
        self._meta = json.loads(self.index_path.read_text())
        cells = []
        for c in self._meta.get("cells", []):
            f = self.root / c["file"]
            if not f.exists():
                continue
            cells.append(CellInfo(
                id=c.get("id") or cell_id(c["lat"], c["lon"]), lat=float(c["lat"]), lon=float(c["lon"]),
                elevation_m=float(c.get("elevation_m") or 0.0), file=f,
                radiation_db=str(c.get("radiation_db") or self._meta.get("radiation_db") or ""),
            ))
        self._cells = cells
        self._lats = np.array([c.lat for c in cells])
        self._lons = np.array([c.lon for c in cells])

    def _maybe_reload(self) -> None:
        if self.index_path.exists():
            if self._index_mtime != self.index_path.stat().st_mtime:
                self.reload()
        elif self._cells:
            self.reload()

    @property
    def available(self) -> bool:
        self._maybe_reload()
        return len(self._cells) > 0

    @property
    def synthetic(self) -> bool:
        return bool(self._meta.get("synthetic", False))

    def info(self) -> dict:
        self._maybe_reload()
        return {
            "available": len(self._cells) > 0,
            "synthetic": self.synthetic,
            "source": self._meta.get("source"),
            "radiation_db": self._meta.get("radiation_db"),
            "downloaded_at": self._meta.get("downloaded_at"),
            "grid_step_deg": self._meta.get("grid_step_deg"),
            "bbox": self._meta.get("bbox"),
            "cell_count": len(self._cells),
            "skipped_count": len(self._meta.get("skipped", [])),
        }

    def nearest_cell(self, lat: float, lon: float) -> Optional[CellInfo]:
        self._maybe_reload()
        if not self._cells:
            return None
        d = haversine_km(lat, lon, self._lats, self._lons)
        i = int(np.argmin(d))
        c = self._cells[i]
        return CellInfo(c.id, c.lat, c.lon, c.elevation_m, c.file, c.radiation_db, float(d[i]))

    def load_tmy(self, cell: CellInfo) -> pd.DataFrame:
        return _read_parquet(str(cell.file), cell.file.stat().st_mtime)


class NasaReference:
    """NASA POWER monthly climatology, reference only (never used in results)."""

    def __init__(self, root: Path):
        self.path = Path(root) / "nasa" / "climatology.json"
        self._points: list[dict] = []
        self._meta: dict = {}
        self._mtime: Optional[float] = None
        self.reload()

    def reload(self) -> None:
        self._points, self._meta = [], {}
        if not self.path.exists():
            self._mtime = None
            return
        self._mtime = self.path.stat().st_mtime
        data = json.loads(self.path.read_text())
        self._meta = {k: v for k, v in data.items() if k != "points"}
        self._points = data.get("points", [])

    def _maybe_reload(self) -> None:
        if self.path.exists() and self._mtime != self.path.stat().st_mtime:
            self.reload()

    @property
    def available(self) -> bool:
        self._maybe_reload()
        return len(self._points) > 0

    def info(self) -> dict:
        self._maybe_reload()
        return {"available": len(self._points) > 0, "point_count": len(self._points), **self._meta}

    def nearest_point(self, lat: float, lon: float) -> Optional[dict]:
        self._maybe_reload()
        if not self._points:
            return None
        lats = np.array([p["lat"] for p in self._points])
        lons = np.array([p["lon"] for p in self._points])
        d = haversine_km(lat, lon, lats, lons)
        i = int(np.argmin(d))
        p = dict(self._points[i])
        p["distance_km"] = round(float(d[i]), 1)
        return p
