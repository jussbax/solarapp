"""Synthetic typical-year weather for tests and for trying the app offline.

Clearly NOT PVGIS data. Built from the pvlib Ineichen clear-sky model with a
seasonal cloud factor and the Erbs decomposition. The dataset index marks it
``synthetic`` and the app refuses to produce a customer PDF from it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib

# Rough wet/dry seasonality for the Philippines (fraction of clear-sky GHI).
MONTHLY_CLOUD_FACTOR = {
    1: 0.74, 2: 0.78, 3: 0.80, 4: 0.80, 5: 0.70, 6: 0.58,
    7: 0.52, 8: 0.52, 9: 0.55, 10: 0.60, 11: 0.64, 12: 0.68,
}


def synthetic_tmy(lat: float, lon: float, elevation_m: float = 10.0, year: int = 2019, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed + int(abs(lat) * 100) + int(abs(lon) * 100))
    times = pd.date_range(f"{year}-01-01 00:30", f"{year}-12-31 23:30", freq="1h", tz="UTC")
    loc = pvlib.location.Location(lat, lon, tz="UTC", altitude=elevation_m)
    solpos = loc.get_solarposition(times)
    cs = loc.get_clearsky(times, model="ineichen", solar_position=solpos)
    factor = np.array([MONTHLY_CLOUD_FACTOR[m] for m in times.month])
    noise = np.clip(rng.normal(1.0, 0.25, len(times)), 0.2, 1.3)
    ghi = (cs["ghi"] * factor * noise).clip(lower=0)
    erbs = pvlib.irradiance.erbs(ghi, solpos["zenith"], times)
    dni = erbs["dni"].fillna(0).clip(lower=0)
    dhi = erbs["dhi"].fillna(0).clip(lower=0)
    local_hour = ((times.hour + 8) % 24) + times.minute / 60
    temp_air = 28.0 + 4.0 * np.sin((local_hour - 9) / 24 * 2 * np.pi) + 1.0 * np.sin((times.dayofyear - 110) / 365 * 2 * np.pi)
    df = pd.DataFrame(
        {
            "temp_air": temp_air,
            "rh": 75.0,
            "ghi": ghi.values,
            "dni": dni.values,
            "dhi": dhi.values,
            "ir": 400.0,
            "wind_speed": 1.5,
            "wind_dir": 90.0,
            "pressure": 101000.0,
        },
        index=times,
    )
    df.index.name = "time_utc"
    return df
