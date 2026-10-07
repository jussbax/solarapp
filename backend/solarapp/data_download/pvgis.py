"""Fetch and parse PVGIS typical meteorological year (TMY) data."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import pandas as pd

PVGIS_TMY_URL = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"

COLUMN_MAP = {
    "T2m": "temp_air", "RH": "rh", "G(h)": "ghi", "Gb(n)": "dni", "Gd(h)": "dhi",
    "IR(h)": "ir", "WS10m": "wind_speed", "WD10m": "wind_dir", "SP": "pressure",
}


class NoDataError(Exception):
    """PVGIS has no data for this location (for example over the sea)."""


@dataclass
class TmyPayload:
    frame: pd.DataFrame
    lat: float
    lon: float
    elevation_m: float
    radiation_db: str
    meteo_db: str
    year_min: Optional[int]
    year_max: Optional[int]
    months_selected: list[dict]
    time_offset_h: float = 0.0  # hours from the label to the centre of the irradiance averaging interval


def parse_tmy_json(payload: dict[str, Any]) -> TmyPayload:
    rows = payload["outputs"]["tmy_hourly"]
    df = pd.DataFrame(rows)
    time_col = next(c for c in df.columns if c.lower().startswith("time"))
    idx = pd.to_datetime(df[time_col], format="%Y%m%d:%H%M", utc=True)
    df = df.drop(columns=[time_col]).rename(columns=COLUMN_MAP)
    df.index = pd.DatetimeIndex(idx)
    df.index.name = "time_utc"
    for col in COLUMN_MAP.values():
        if col not in df.columns:
            df[col] = 0.0
    df = df[list(COLUMN_MAP.values())].astype(float)
    inputs = payload.get("inputs", {})
    loc = inputs.get("location", {})
    meteo = inputs.get("meteo_data", {})
    return TmyPayload(
        frame=df,
        lat=float(loc.get("latitude", float("nan"))),
        lon=float(loc.get("longitude", float("nan"))),
        elevation_m=float(loc.get("elevation") or 0.0),
        radiation_db=str(meteo.get("radiation_db", "")),
        meteo_db=str(meteo.get("meteo_db", "")),
        year_min=meteo.get("year_min"),
        year_max=meteo.get("year_max"),
        months_selected=list(payload["outputs"].get("months_selected", [])),
        time_offset_h=float(loc.get("irradiance_time_offset") or 0.0),
    )


async def fetch_tmy(client: httpx.AsyncClient, lat: float, lon: float, retries: int = 4) -> TmyPayload:
    params = {"lat": f"{lat:.4f}", "lon": f"{lon:.4f}", "outputformat": "json"}
    delay = 2.0
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            r = await client.get(PVGIS_TMY_URL, params=params, timeout=120)
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last_exc = e
        else:
            if r.status_code == 200:
                return parse_tmy_json(r.json())
            if r.status_code == 400:
                try:
                    msg = r.json().get("message", r.text)
                except ValueError:
                    msg = r.text
                raise NoDataError(str(msg)[:200])
            last_exc = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            if r.status_code not in (429, 500, 502, 503, 504):
                raise last_exc
        await asyncio.sleep(delay)
        delay *= 2
    assert last_exc is not None
    raise last_exc
