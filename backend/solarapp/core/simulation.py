"""Hourly production simulation over a typical meteorological year.

Per roof face: Perez transposition to the face's tilt and facing, Martin-Ruiz
reflection losses, Huld module model (PVGIS 5 coefficients, crystalline
silicon), module temperature from the site-measured rise or the PVGIS Faiman
model, times panel count and Wp, times the site factor ``k_site``.

Results are grouped by local (Asia/Manila) month using the hours of that month,
so months have their actual number of days (S3), and in-plane irradiation is
computed per face (S4).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
import pandas as pd
import pvlib
from pvlib.pvarray import huld

LOCAL_TZ = "Asia/Manila"
PVGIS_FAIMAN_U0 = 26.9
PVGIS_FAIMAN_U1 = 6.2
ALBEDO = 0.2


@dataclass
class FaceSpec:
    id: str
    name: str
    tilt_deg: float
    azimuth_deg: float  # compass, 0 = north, 90 = east, 180 = south, 270 = west
    panel_count: int


@dataclass
class ThermalModel:
    kind: str = "faiman"  # "faiman" (PVGIS default) or "site_rise"
    rise_c_per_kw: Optional[float] = None
    u0: float = PVGIS_FAIMAN_U0
    u1: float = PVGIS_FAIMAN_U1

    def describe(self) -> str:
        if self.kind == "site_rise" and self.rise_c_per_kw is not None:
            return f"site-measured rise of {self.rise_c_per_kw:.1f} C per kW/m2 above ambient"
        return f"PVGIS Faiman model (u0={self.u0}, u1={self.u1})"


@dataclass
class SkyContext:
    """Solar geometry for one TMY, independent of roof faces. Reusable."""
    index_utc: pd.DatetimeIndex
    month: np.ndarray
    hour: np.ndarray  # local hour of the interval centre
    days_in_month: list[int]
    zenith: pd.Series
    apparent_zenith: pd.Series
    azimuth: pd.Series
    dni_extra: pd.Series
    airmass: pd.Series


def prepare_sky(tmy: pd.DataFrame, lat: float, lon: float, elevation_m: float, time_offset_h: float = 0.0) -> SkyContext:
    """Solar geometry at the centre of each averaging interval.

    PVGIS labels each hour by its start and reports ``irradiance_time_offset``
    (0.5 h for ERA5), so the sun position is evaluated at label + offset.
    """
    idx = tmy.index
    centre = idx + pd.Timedelta(hours=float(time_offset_h))
    solpos = pvlib.solarposition.get_solarposition(centre, lat, lon, altitude=elevation_m, temperature=float(tmy["temp_air"].mean()))
    solpos.index = idx
    dni_extra = pvlib.irradiance.get_extra_radiation(centre)
    airmass = pvlib.atmosphere.get_relative_airmass(solpos["apparent_zenith"]).fillna(0)
    local = centre.tz_convert(LOCAL_TZ)
    month = local.month.values
    # Count month-day pairs, not full dates: a composite TMY spans several
    # calendar years and the UTC to local shift moves a few hours across years.
    monthday = pd.Series(local.strftime("%m-%d"), index=idx)
    days = [int(monthday[month == m].nunique()) for m in range(1, 13)]
    return SkyContext(
        index_utc=idx, month=month, hour=local.hour.values, days_in_month=days,
        zenith=solpos["zenith"], apparent_zenith=solpos["apparent_zenith"], azimuth=solpos["azimuth"],
        dni_extra=pd.Series(np.asarray(dni_extra), index=idx), airmass=airmass,
    )


def module_temperature(poa_global: pd.Series, temp_air: pd.Series, wind_speed: pd.Series, thermal: ThermalModel) -> pd.Series:
    if thermal.kind == "site_rise" and thermal.rise_c_per_kw is not None:
        return temp_air + poa_global / 1000.0 * thermal.rise_c_per_kw
    return pvlib.temperature.faiman(poa_global, temp_air, wind_speed, u0=thermal.u0, u1=thermal.u1)


@dataclass
class FaceSimulation:
    face_id: str
    name: str
    tilt_deg: float
    azimuth_deg: float
    panel_count: int
    monthly_kwh: list[float]
    annual_kwh: float
    monthly_poa_kwh_m2: list[float]
    psh_per_day: list[float]
    annual_poa_kwh_m2: float
    avg_psh_per_day: float
    specific_yield_kwh_per_kwp: float
    hourly_profile_kw: list[list[float]]  # [12][24] average kW by local hour

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SimulationResult:
    faces: list[FaceSimulation]
    monthly_kwh: list[float]
    annual_kwh: float
    avg_monthly_kwh: float
    days_in_month: list[int]
    monthly_ghi_kwh_m2: list[float]
    ghi_psh_per_day: list[float]
    annual_ghi_kwh_m2: float
    total_panels: int
    system_kwp: float
    k_site: float
    thermal: str
    hourly_profile_kw: list[list[float]]  # [12][24] average kW by local hour, all faces

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def hourly_profile(values_w: pd.Series, month: np.ndarray, hour: np.ndarray) -> list[list[float]]:
    """Average kW by (month, local hour) over the typical year."""
    arr = np.asarray(values_w, dtype=float)
    out = np.zeros((12, 24))
    for m in range(12):
        sel = month == m + 1
        for h in range(24):
            cell = arr[sel & (hour == h)]
            out[m, h] = cell.mean() / 1000.0 if cell.size else 0.0
    return out.round(5).tolist()


def _diffuse_iam(tilt: float) -> tuple[float, float]:
    """Martin-Ruiz diffuse factors (sky, ground); pvlib's return type varies by version."""
    r = pvlib.iam.martin_ruiz_diffuse(tilt)
    try:
        return float(r["sky"]), float(r["ground"])
    except (KeyError, TypeError, IndexError):
        sky, ground = r
        return float(sky), float(ground)


def _monthly_sum(values: pd.Series, month: np.ndarray) -> list[float]:
    arr = np.asarray(values, dtype=float)
    return [float(np.nansum(arr[month == m])) for m in range(1, 13)]


def simulate_face(tmy: pd.DataFrame, sky: SkyContext, face: FaceSpec, panel_wp: float, k_site: float, thermal: ThermalModel) -> FaceSimulation:
    tilt = float(face.tilt_deg)
    az = float(face.azimuth_deg) % 360.0
    irr = pvlib.irradiance.get_total_irradiance(
        tilt, az, sky.zenith, sky.azimuth,
        dni=tmy["dni"], ghi=tmy["ghi"], dhi=tmy["dhi"],
        dni_extra=sky.dni_extra, airmass=sky.airmass, albedo=ALBEDO, model="perez",
    ).fillna(0.0)
    aoi = pvlib.irradiance.aoi(tilt, az, sky.zenith, sky.azimuth)
    iam_beam = pvlib.iam.martin_ruiz(aoi).fillna(0.0)
    iam_sky, iam_ground = _diffuse_iam(tilt)
    g_eff = (
        irr["poa_direct"] * iam_beam
        + irr["poa_sky_diffuse"] * iam_sky
        + irr["poa_ground_diffuse"] * iam_ground
    ).clip(lower=0.0)
    poa_global = irr["poa_global"].clip(lower=0.0)
    t_mod = module_temperature(poa_global, tmy["temp_air"], tmy["wind_speed"], thermal)
    power_per_wp = pd.Series(np.asarray(huld(g_eff, t_mod, 1.0, cell_type="csi")), index=tmy.index).fillna(0.0).clip(lower=0.0)
    power_w = power_per_wp * panel_wp * face.panel_count * k_site

    monthly_kwh = [v / 1000.0 for v in _monthly_sum(power_w, sky.month)]
    monthly_poa = [v / 1000.0 for v in _monthly_sum(poa_global, sky.month)]
    psh = [p / d if d else 0.0 for p, d in zip(monthly_poa, sky.days_in_month)]
    annual = float(sum(monthly_kwh))
    annual_poa = float(sum(monthly_poa))
    kwp = panel_wp * face.panel_count / 1000.0
    return FaceSimulation(
        face_id=face.id, name=face.name, tilt_deg=tilt, azimuth_deg=az, panel_count=face.panel_count,
        monthly_kwh=monthly_kwh, annual_kwh=annual,
        monthly_poa_kwh_m2=monthly_poa, psh_per_day=psh, annual_poa_kwh_m2=annual_poa,
        avg_psh_per_day=annual_poa / max(sum(sky.days_in_month), 1),
        specific_yield_kwh_per_kwp=(annual / kwp) if kwp > 0 else 0.0,
        hourly_profile_kw=hourly_profile(power_w, sky.month, sky.hour),
    )


def simulate(
    tmy: pd.DataFrame,
    lat: float,
    lon: float,
    elevation_m: float,
    faces: list[FaceSpec],
    panel_wp: float,
    k_site: float,
    thermal: ThermalModel,
    sky: Optional[SkyContext] = None,
    time_offset_h: float = 0.0,
) -> SimulationResult:
    sky = sky or prepare_sky(tmy, lat, lon, elevation_m, time_offset_h)
    face_results = [simulate_face(tmy, sky, f, panel_wp, k_site, thermal) for f in faces]
    monthly = [sum(f.monthly_kwh[i] for f in face_results) for i in range(12)]
    annual = float(sum(monthly))
    ghi_monthly = [v / 1000.0 for v in _monthly_sum(tmy["ghi"].clip(lower=0), sky.month)]
    total_panels = sum(f.panel_count for f in faces)
    profile = np.zeros((12, 24))
    for f in face_results:
        profile += np.array(f.hourly_profile_kw)
    return SimulationResult(
        faces=face_results,
        monthly_kwh=monthly,
        annual_kwh=annual,
        avg_monthly_kwh=annual / 12.0,
        days_in_month=sky.days_in_month,
        monthly_ghi_kwh_m2=ghi_monthly,
        ghi_psh_per_day=[g / d if d else 0.0 for g, d in zip(ghi_monthly, sky.days_in_month)],
        annual_ghi_kwh_m2=float(sum(ghi_monthly)),
        total_panels=total_panels,
        system_kwp=total_panels * panel_wp / 1000.0,
        k_site=k_site,
        thermal=thermal.describe(),
        hourly_profile_kw=profile.round(5).tolist(),
    )


def typical_air_temperature(tmy: pd.DataFrame, month: int, hour_local: int) -> Optional[float]:
    """Mean air temperature in the TMY for a local month and hour."""
    local = tmy.index.tz_convert(LOCAL_TZ)
    mask = (local.month == month) & (local.hour == hour_local)
    if not mask.any():
        return None
    return float(tmy.loc[mask, "temp_air"].mean())
