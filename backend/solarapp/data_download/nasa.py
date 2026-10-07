"""Fetch and parse NASA POWER monthly climatology for a bounding box (reference only)."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx

NASA_REGIONAL_URL = "https://power.larc.nasa.gov/api/temporal/climatology/regional"
PARAMETERS = ["ALLSKY_SFC_SW_DWN", "T2M", "ALLSKY_KT"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
TILE_DEG = 8.0  # the regional endpoint accepts boxes of this size (tested)


def _series(d: Any) -> Optional[list[Optional[float]]]:
    if not isinstance(d, dict):
        return None
    vals: list[Optional[float]] = []
    for m in MONTHS:
        v = d.get(m)
        vals.append(None if v is None or float(v) <= -900 else float(v))
    return vals


def parse_regional_json(payload: dict[str, Any]) -> dict[tuple[float, float], dict]:
    """Per-point parameter series from one regional response (any parameters it holds)."""
    out: dict[tuple[float, float], dict] = {}
    for f in payload.get("features") or []:
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        params = ((f.get("properties") or {}).get("parameter") or {})
        rec = out.setdefault((lat, lon), {"lat": lat, "lon": lon})
        for name, d in params.items():
            series = _series(d)
            if series is not None:
                rec[name] = series
                ann = d.get("ANN") if isinstance(d, dict) else None
                rec[name + "_ANN"] = None if ann is None or float(ann) <= -900 else float(ann)
    return out


def merge_points(raw: dict[tuple[float, float], dict]) -> list[dict]:
    """Keep points that have irradiation and shape them for the app."""
    points = []
    for rec in raw.values():
        ghi = rec.get("ALLSKY_SFC_SW_DWN")
        if ghi is None or all(v is None for v in ghi):
            continue
        points.append({
            "lat": rec["lat"], "lon": rec["lon"],
            "ghi_kwh_m2_day": ghi,
            "ghi_annual_kwh_m2_day": rec.get("ALLSKY_SFC_SW_DWN_ANN"),
            "t2m_c": rec.get("T2M"),
            "clearness_index": rec.get("ALLSKY_KT"),
        })
    return points


MIN_RANGE_DEG = 2.0  # the regional endpoint refuses smaller boxes


def tiles(bbox: tuple[float, float, float, float], size: float = TILE_DEG) -> list[tuple[float, float, float, float]]:
    lat_min, lat_max, lon_min, lon_max = bbox
    if lat_max - lat_min < MIN_RANGE_DEG:
        mid = (lat_min + lat_max) / 2
        lat_min, lat_max = mid - MIN_RANGE_DEG / 2, mid + MIN_RANGE_DEG / 2
    if lon_max - lon_min < MIN_RANGE_DEG:
        mid = (lon_min + lon_max) / 2
        lon_min, lon_max = mid - MIN_RANGE_DEG / 2, mid + MIN_RANGE_DEG / 2
    out = []
    la = lat_min
    while la < lat_max:
        lo = lon_min
        la2 = min(la + size, lat_max)
        la1 = min(la, la2 - MIN_RANGE_DEG)  # a short last row overlaps the previous one
        while lo < lon_max:
            lo2 = min(lo + size, lon_max)
            lo1 = min(lo, lo2 - MIN_RANGE_DEG)
            out.append((la1, la2, lo1, lo2))
            lo = lo2
        la = la2
    return out


async def _fetch_one(client: httpx.AsyncClient, tile: tuple[float, float, float, float], parameter: str, retries: int = 4) -> dict[tuple[float, float], dict]:
    lat_min, lat_max, lon_min, lon_max = tile
    params = {
        "parameters": parameter, "community": "RE", "format": "JSON",
        "latitude-min": f"{lat_min:.2f}", "latitude-max": f"{lat_max:.2f}",
        "longitude-min": f"{lon_min:.2f}", "longitude-max": f"{lon_max:.2f}",
    }
    delay = 3.0
    last: Optional[Exception] = None
    for _ in range(retries + 1):
        try:
            r = await client.get(NASA_REGIONAL_URL, params=params, timeout=180)
            if r.status_code == 200:
                return parse_regional_json(r.json())
            last = RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            if r.status_code == 422:
                raise last
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last = e
        await asyncio.sleep(delay)
        delay *= 2
    assert last is not None
    raise last


async def fetch_regional(client: httpx.AsyncClient, tile: tuple[float, float, float, float]) -> dict[tuple[float, float], dict]:
    """All parameters for one tile. The API allows one parameter per request."""
    merged: dict[tuple[float, float], dict] = {}
    for parameter in PARAMETERS:
        part = await _fetch_one(client, tile, parameter)
        for key, rec in part.items():
            merged.setdefault(key, {"lat": rec["lat"], "lon": rec["lon"]}).update(rec)
        await asyncio.sleep(1.0)
    return merged
