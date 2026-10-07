"""Fetch and parse NASA POWER monthly climatology for a bounding box (reference only)."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx

NASA_REGIONAL_URL = "https://power.larc.nasa.gov/api/temporal/climatology/regional"
PARAMETERS = ["ALLSKY_SFC_SW_DWN", "T2M", "ALLSKY_KT"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
TILE_DEG = 4.0  # the regional endpoint limits the box size


def parse_regional_json(payload: dict[str, Any]) -> list[dict]:
    points: list[dict] = []
    features = payload.get("features") or []
    for f in features:
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        params = ((f.get("properties") or {}).get("parameter") or {})

        def series(name: str) -> Optional[list[float]]:
            d = params.get(name)
            if not isinstance(d, dict):
                return None
            vals = []
            for m in MONTHS:
                v = d.get(m)
                vals.append(None if v is None or float(v) <= -900 else float(v))
            return vals

        ghi = series("ALLSKY_SFC_SW_DWN")
        if ghi is None or all(v is None for v in ghi):
            continue
        ann = (params.get("ALLSKY_SFC_SW_DWN") or {}).get("ANN")
        points.append({
            "lat": lat, "lon": lon,
            "ghi_kwh_m2_day": ghi,
            "ghi_annual_kwh_m2_day": None if ann is None or float(ann) <= -900 else float(ann),
            "t2m_c": series("T2M"),
            "clearness_index": series("ALLSKY_KT"),
        })
    return points


def tiles(bbox: tuple[float, float, float, float], size: float = TILE_DEG) -> list[tuple[float, float, float, float]]:
    lat_min, lat_max, lon_min, lon_max = bbox
    out = []
    la = lat_min
    while la < lat_max:
        lo = lon_min
        la2 = min(la + size, lat_max)
        while lo < lon_max:
            lo2 = min(lo + size, lon_max)
            out.append((la, la2, lo, lo2))
            lo = lo2
        la = la2
    return out


async def fetch_regional(client: httpx.AsyncClient, tile: tuple[float, float, float, float], retries: int = 4) -> list[dict]:
    lat_min, lat_max, lon_min, lon_max = tile
    params = {
        "parameters": ",".join(PARAMETERS), "community": "RE", "format": "JSON",
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
